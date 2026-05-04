from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from src.crew_workflow import CrewRun, MultiAgentCrew, save_crew_logs
from src.llm_extract import DEFAULT_MODEL, extract_once
from src.validator import validate_output


DEFAULT_CASES_PATH = Path("data/sample/lab13_test_cases.jsonl")
DEFAULT_LOGS_PATH = Path("docs/crew_logs_lab13.jsonl")
DEFAULT_AUDIT_PATH = Path("docs/audit_summary_lab13.md")


@dataclass
class BaselineRun:
    case_id: str
    raw_output: str
    valid: bool
    errors: list[str]
    prediction: dict[str, Any] | None


def load_cases(path: str | Path = DEFAULT_CASES_PATH) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def run_single_agent_baseline(cases: list[dict[str, Any]], model: str = DEFAULT_MODEL) -> list[BaselineRun]:
    runs: list[BaselineRun] = []
    for case in cases:
        response = extract_once(case["input"], model=model, temperature=0.2)
        runs.append(
            BaselineRun(
                case_id=case["case_id"],
                raw_output=response.raw_text,
                valid=response.validation.is_valid,
                errors=response.validation.error_messages(),
                prediction=response.validation.parsed_json if response.validation.is_valid else None,
            )
        )
    return runs


def run_crew(cases: list[dict[str, Any]], model: str = DEFAULT_MODEL) -> list[CrewRun]:
    crew = MultiAgentCrew(model=model)
    return [crew.run_case(case["case_id"], case["input"]) for case in cases]


def _schema_valid_final(run: CrewRun) -> bool:
    extraction = run.final_output.get("extraction")
    if not isinstance(extraction, dict):
        return False
    return validate_output(json.dumps(extraction, ensure_ascii=False)).is_valid


def _issue_count(run: CrewRun, needle: str) -> int:
    issues = run.reviewer_output.get("issues", [])
    return sum(needle in str(issue).lower() for issue in issues)


def compute_metrics(
    cases: list[dict[str, Any]],
    baseline_runs: list[BaselineRun],
    crew_runs: list[CrewRun],
) -> dict[str, Any]:
    total = len(cases)
    fallback_count = sum(run.fallback_triggered for run in crew_runs)
    fallback_success = sum(
        run.fallback_triggered
        and isinstance(run.fallback_output, dict)
        and bool(run.fallback_output.get("success"))
        for run in crew_runs
    )
    manual_review = sum(bool(run.final_output.get("needs_manual_review")) for run in crew_runs)
    reviewer_caught = sum(run.reviewer_output.get("verdict") != "accept" for run in crew_runs)
    crew_valid = sum(_schema_valid_final(run) for run in crew_runs)
    baseline_valid = sum(run.valid for run in baseline_runs)
    hallucination_issues = sum(_issue_count(run, "not grounded") for run in crew_runs)
    missing_issues = sum(_issue_count(run, "missed field") + _issue_count(run, "missing") for run in crew_runs)

    return {
        "total_cases": total,
        "single_agent_valid_output_rate": round(baseline_valid / total, 4) if total else 0.0,
        "crew_valid_final_output_rate": round(crew_valid / total, 4) if total else 0.0,
        "reviewer_catch_rate": round(reviewer_caught / total, 4) if total else 0.0,
        "fallback_activation_rate": round(fallback_count / total, 4) if total else 0.0,
        "fallback_success_rate": round(fallback_success / fallback_count, 4) if fallback_count else 0.0,
        "manual_review_rate": round(manual_review / total, 4) if total else 0.0,
        "hallucination_issue_count": hallucination_issues,
        "missing_required_field_issue_count": missing_issues,
        "average_agents_called_per_case": round(mean(len(run.agents_called) for run in crew_runs), 4) if total else 0.0,
        "average_repair_attempts_per_case": round(mean(1 if "repair" in run.agents_called else 0 for run in crew_runs), 4)
        if total
        else 0.0,
    }


def build_error_analysis(cases: list[dict[str, Any]], crew_runs: list[CrewRun]) -> list[dict[str, Any]]:
    cases_by_id = {case["case_id"]: case for case in cases}
    rows: list[dict[str, Any]] = []
    for run in crew_runs:
        case = cases_by_id[run.case_id]
        rows.append(
            {
                "case_id": run.case_id,
                "input": run.input,
                "expected_behavior": case.get("expected_behavior"),
                "triager_output": run.triager_output,
                "extractor_output": run.extractor_output,
                "reviewer_verdict": run.reviewer_output,
                "fallback_action": run.fallback_output.get("action") if isinstance(run.fallback_output, dict) else "none",
                "final_output": run.final_output,
                "error_category": case.get("error_category"),
                "possible_fix": _possible_fix(case.get("error_category", ""), run),
            }
        )
    return rows


def _possible_fix(error_category: str, run: CrewRun) -> str:
    if run.status == "accepted":
        return "No fix needed for this run; keep as regression coverage."
    if error_category in {"ambiguous_entity", "reviewer_rejection"}:
        return "Tighten grounding rules for document_id and require explicit legal context."
    if error_category == "relative_date":
        return "Add optional current-date-aware normalization policy for relative dates."
    if error_category in {"fallback_required", "repair_succeeds"}:
        return "Keep rule-based fallback for short IDs, dates, and currency normalization."
    if error_category == "manual_review_after_failed_repair":
        return "Return safe partial output and route to manual review."
    return "Inspect reviewer issues and add a targeted rule or prompt constraint."


def write_audit_summary(
    path: str | Path,
    metrics: dict[str, Any],
    cases: list[dict[str, Any]],
    crew_runs: list[CrewRun],
    error_analysis: list[dict[str, Any]],
) -> None:
    accepted = [run for run in crew_runs if run.status in {"accepted", "accepted_after_repair"}][:3]
    problematic = [run for run in crew_runs if run.final_output.get("needs_manual_review") or run.fallback_triggered][:3]
    lines = [
        "# Lab 13 Audit Summary",
        "",
        "## 1. Use case",
        "- Multi-agent document signal extraction for Ukrainian legal/news text.",
        "- Fields: `document_id`, `document_type`, `date_iso`, `date_text`, `amount_value`, `amount_currency`.",
        "",
        "## 2. Agents implemented",
        "- Triager: selects route, expected fields, difficulty and special handling.",
        "- Extractor: returns schema-only JSON.",
        "- Reviewer: checks JSON validity, schema, grounding and consistency.",
        "- Repair/Fallback: repairs reviewer issues and applies rule-based partial extraction when repair fails.",
        "",
        f"## 3. Test cases: `{len(cases)}`",
        "",
        "## 4. Metrics",
        f"- Valid final output rate: `{metrics['crew_valid_final_output_rate']:.2%}`",
        f"- Reviewer catch rate: `{metrics['reviewer_catch_rate']:.2%}`",
        f"- Fallback activation rate: `{metrics['fallback_activation_rate']:.2%}`",
        f"- Fallback success rate: `{metrics['fallback_success_rate']:.2%}`",
        f"- Manual review rate: `{metrics['manual_review_rate']:.2%}`",
        "",
        "## 5. Single-agent vs crew comparison",
        "| Variant | Valid output rate | Notes |",
        "|---|---:|---|",
        f"| Single-agent baseline | {metrics['single_agent_valid_output_rate']:.2%} | One Groq extraction call, no independent review. |",
        f"| Multi-agent crew | {metrics['crew_valid_final_output_rate']:.2%} | Triager + Extractor + Reviewer + fallback. |",
        "",
        "## 6. Good crew examples",
    ]
    lines.extend(f"- `{run.case_id}`: status=`{run.status}`, fallback={run.fallback_triggered}" for run in accepted)
    lines.extend(
        [
            "",
            "## 7. Problematic examples",
        ]
    )
    lines.extend(f"- `{run.case_id}`: status=`{run.status}`, review=`{run.reviewer_output.get('verdict')}`" for run in problematic)
    lines.extend(
        [
            "",
            "## 8. Error analysis",
        ]
    )
    for row in error_analysis:
        lines.append(
            f"- `{row['case_id']}` | category=`{row['error_category']}` | "
            f"fallback=`{row['fallback_action']}` | fix: {row['possible_fix']}"
        )
    lines.extend(
        [
            "",
            "## 9. Next improvements",
            "- Add stronger span-level grounding for values selected by the LLM.",
            "- Add current-date-aware handling if relative dates become in scope.",
            "- Track token/cost metrics per agent call for operational comparison.",
        ]
    )
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Lab 13 Groq multi-agent crew evaluation.")
    parser.add_argument("--cases-path", default=str(DEFAULT_CASES_PATH))
    parser.add_argument("--logs-path", default=str(DEFAULT_LOGS_PATH))
    parser.add_argument("--audit-path", default=str(DEFAULT_AUDIT_PATH))
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()

    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("GROQ_API_KEY is not set. Export it before running Lab 13 Groq evaluation.")

    cases = load_cases(args.cases_path)
    baseline_runs = run_single_agent_baseline(cases, model=args.model)
    crew_runs = run_crew(cases, model=args.model)
    metrics = compute_metrics(cases, baseline_runs, crew_runs)
    error_analysis = build_error_analysis(cases, crew_runs)

    save_crew_logs(args.logs_path, crew_runs)
    write_audit_summary(args.audit_path, metrics, cases, crew_runs, error_analysis)
    print(json.dumps({"metrics": metrics, "logs_path": args.logs_path, "audit_path": args.audit_path}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
