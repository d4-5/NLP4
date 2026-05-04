from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.agents import ExtractorAgent, GroqLLMClient, RepairAgent, ReviewerAgent, TriagerAgent
from src.fallback import run_fallback
from src.llm_extract import DEFAULT_MODEL
from src.reviewer import review_extraction
from src.validator import validate_output


@dataclass
class CrewRun:
    case_id: str
    input: str
    triager_output: dict[str, Any]
    extractor_output: dict[str, Any] | None
    reviewer_output: dict[str, Any]
    fallback_triggered: bool
    fallback_output: dict[str, Any] | None
    final_output: dict[str, Any]
    status: str
    agents_called: list[str]


def _coerce_agent_json(parsed: dict[str, Any] | None, fallback: dict[str, Any]) -> dict[str, Any]:
    return parsed if isinstance(parsed, dict) else fallback


def _final_output(
    status: str,
    extraction: dict[str, Any] | None,
    needs_manual_review: bool,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": status,
        "extraction": extraction,
        "needs_manual_review": needs_manual_review,
        "warnings": warnings or [],
    }


class MultiAgentCrew:
    def __init__(self, model: str = DEFAULT_MODEL) -> None:
        client = GroqLLMClient(model=model)
        self.triager = TriagerAgent(client)
        self.extractor = ExtractorAgent(client)
        self.reviewer = ReviewerAgent(client)
        self.repair = RepairAgent(client)

    def run_case(self, case_id: str, text: str) -> CrewRun:
        agents_called: list[str] = []

        triage_result = self.triager.run(text)
        agents_called.append("triager")
        triage = _coerce_agent_json(
            triage_result.parsed_json,
            {
                "task_type": "document_signal_extraction",
                "route": "manual_review_route",
                "expected_fields": [],
                "difficulty": "unknown",
                "special_handling": "triager_invalid_json",
                "notes": triage_result.raw_text,
            },
        )

        extraction_result = self.extractor.run(text, triage)
        agents_called.append("extractor")
        extraction_validation = validate_output(extraction_result.raw_text)
        extraction = extraction_validation.parsed_json if isinstance(extraction_validation.parsed_json, dict) else None

        llm_review_result = self.reviewer.run(
            text=text,
            triage=triage,
            extraction=extraction,
            validation_errors=extraction_validation.error_messages(),
        )
        agents_called.append("reviewer")
        reviewer_output = review_extraction(
            text=text,
            raw_extraction=extraction_result.raw_text,
            llm_review=llm_review_result.parsed_json,
        )

        fallback_triggered = reviewer_output["verdict"] != "accept"
        fallback_output: dict[str, Any] | None = None

        if not fallback_triggered:
            status = "accepted"
            final = _final_output(
                status=status,
                extraction=extraction,
                needs_manual_review=False,
            )
        else:
            fallback_output = run_fallback(
                text=text,
                triage=triage,
                extraction=extraction,
                review=reviewer_output,
                repair_agent=self.repair,
            )
            agents_called.append("repair")
            repaired = fallback_output.get("output")

            if fallback_output.get("success") and not fallback_output.get("needs_manual_review"):
                status = "accepted_after_repair"
                final = _final_output(status=status, extraction=repaired, needs_manual_review=False)
            elif fallback_output.get("success"):
                status = "partial_manual_review"
                final = _final_output(
                    status=status,
                    extraction=repaired,
                    needs_manual_review=True,
                    warnings=fallback_output.get("errors", []),
                )
            else:
                status = "failed_manual_review"
                final = _final_output(
                    status=status,
                    extraction=repaired.get("partial_output") if isinstance(repaired, dict) else None,
                    needs_manual_review=True,
                    warnings=fallback_output.get("errors", []),
                )

        return CrewRun(
            case_id=case_id,
            input=text,
            triager_output=triage,
            extractor_output=extraction,
            reviewer_output=reviewer_output,
            fallback_triggered=fallback_triggered,
            fallback_output=fallback_output,
            final_output=final,
            status=status,
            agents_called=agents_called,
        )


def save_crew_logs(path: str | Path, runs: list[CrewRun]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for run in runs:
            f.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")


def load_crew_logs(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows
