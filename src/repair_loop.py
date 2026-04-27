from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Any

from src.llm_extract import DEFAULT_MODEL, extract_once, load_eval_set, repair_once


@dataclass
class ExampleRun:
    text_id: str
    text: str
    gold: dict[str, Any]
    comment: str
    raw_output: str
    raw_parse_success: bool
    raw_schema_success: bool
    raw_valid: bool
    final_output: str
    final_parse_success: bool
    final_schema_success: bool
    final_valid: bool
    repairs_used: int
    repair_attempts: list[dict[str, Any]]
    raw_errors: list[str]
    final_errors: list[str]
    raw_prediction: dict[str, Any] | None
    final_prediction: dict[str, Any] | None
    semantic_exact_match: bool
    semantic_mismatches: list[str]


def _semantic_compare(gold: dict[str, Any], prediction: dict[str, Any] | None) -> list[str]:
    if prediction is None:
        return ["prediction is null because JSON parsing or validation failed"]

    mismatches: list[str] = []
    for field in [
        "document_id",
        "document_type",
        "date_iso",
        "date_text",
        "amount_value",
        "amount_currency",
    ]:
        gold_value = gold.get(field)
        pred_value = prediction.get(field)
        if gold_value != pred_value:
            mismatches.append(f"{field}: expected={gold_value!r}, predicted={pred_value!r}")
    return mismatches


def run_single_example(
    example: dict[str, Any],
    model: str = DEFAULT_MODEL,
    max_repairs: int = 2,
) -> ExampleRun:
    raw_response = extract_once(example["text"], model=model)
    current_response = raw_response
    repair_attempts: list[dict[str, Any]] = []

    for attempt_idx in range(max_repairs):
        if current_response.validation.is_valid:
            break
        repaired = repair_once(
            text=example["text"],
            broken_output=current_response.raw_text,
            error_messages=current_response.validation.error_messages(),
            model=model,
        )
        repair_attempts.append(
            {
                "attempt": attempt_idx + 1,
                "output": repaired.raw_text,
                "errors_after_attempt": repaired.validation.error_messages(),
                "parse_success": repaired.validation.parse_success,
                "schema_success": repaired.validation.schema_success,
                "valid": repaired.validation.is_valid,
            }
        )
        current_response = repaired

    final_prediction = current_response.validation.parsed_json if current_response.validation.is_valid else None
    semantic_mismatches = _semantic_compare(example["gold"], final_prediction)

    return ExampleRun(
        text_id=example["text_id"],
        text=example["text"],
        gold=example["gold"],
        comment=example.get("comment", ""),
        raw_output=raw_response.raw_text,
        raw_parse_success=raw_response.validation.parse_success,
        raw_schema_success=raw_response.validation.schema_success,
        raw_valid=raw_response.validation.is_valid,
        final_output=current_response.raw_text,
        final_parse_success=current_response.validation.parse_success,
        final_schema_success=current_response.validation.schema_success,
        final_valid=current_response.validation.is_valid,
        repairs_used=len(repair_attempts),
        repair_attempts=repair_attempts,
        raw_errors=raw_response.validation.error_messages(),
        final_errors=current_response.validation.error_messages(),
        raw_prediction=raw_response.validation.parsed_json if raw_response.validation.is_valid else None,
        final_prediction=final_prediction,
        semantic_exact_match=not semantic_mismatches,
        semantic_mismatches=semantic_mismatches,
    )


def run_evaluation(
    eval_path: str | Path,
    output_path: str | Path | None = None,
    model: str = DEFAULT_MODEL,
    max_repairs: int = 2,
) -> tuple[list[ExampleRun], dict[str, Any]]:
    eval_rows = load_eval_set(eval_path)
    runs: list[ExampleRun] = []
    if output_path is not None:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text("", encoding="utf-8")

    for idx, row in enumerate(eval_rows, start=1):
        print(f"[lab11] processing {idx}/{len(eval_rows)} {row['text_id']}", flush=True)
        run = run_single_example(row, model=model, max_repairs=max_repairs)
        runs.append(run)
        if output_path is not None:
            with Path(output_path).open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")

    metrics = compute_metrics(runs)
    return runs, metrics


def compute_metrics(runs: list[ExampleRun]) -> dict[str, Any]:
    total = len(runs)
    raw_valid = sum(run.raw_valid for run in runs)
    post_repair_valid = sum(run.final_valid for run in runs)
    raw_parse_failures = sum(not run.raw_parse_success for run in runs)
    raw_schema_failures = sum(run.raw_parse_success and not run.raw_schema_success for run in runs)
    repair_needed = sum(not run.raw_valid for run in runs)
    repair_failed = sum((not run.raw_valid) and (not run.final_valid) for run in runs)
    semantic_exact = sum(run.semantic_exact_match for run in runs)

    return {
        "total_examples": total,
        "raw_valid_json_rate": round(raw_valid / total, 4) if total else 0.0,
        "post_repair_valid_json_rate": round(post_repair_valid / total, 4) if total else 0.0,
        "schema_valid_json_rate": round(post_repair_valid / total, 4) if total else 0.0,
        "raw_parse_failure_rate": round(raw_parse_failures / total, 4) if total else 0.0,
        "raw_schema_failure_rate": round(raw_schema_failures / total, 4) if total else 0.0,
        "repair_needed_rate": round(repair_needed / total, 4) if total else 0.0,
        "repair_failure_rate": round(repair_failed / total, 4) if total else 0.0,
        "average_repairs_per_example": round(mean(run.repairs_used for run in runs), 4) if total else 0.0,
        "semantic_exact_match_rate": round(semantic_exact / total, 4) if total else 0.0,
    }


def save_runs(output_path: str | Path, runs: list[ExampleRun]) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for run in runs:
            f.write(json.dumps(asdict(run), ensure_ascii=False) + "\n")


def load_runs(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows
