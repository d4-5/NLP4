from __future__ import annotations

import json
from typing import Any

from src.agents import RepairAgent
from src.ie_rules import extract_all
from src.json_schema import LAB11_SCHEMA
from src.validator import validate_output


def empty_extraction() -> dict[str, Any]:
    return {field: None for field in LAB11_SCHEMA["required"]}


def rule_based_partial(text: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
    output = empty_extraction()
    if base:
        for field in output:
            output[field] = base.get(field)

    hits = extract_all(text)
    if output["document_id"] is None and hits["DOC_ID"]:
        first_doc = hits["DOC_ID"][0]
        output["document_id"] = first_doc["value"]
        output["document_type"] = first_doc["type"]

    if output["date_iso"] is None and hits["DATE"]:
        first_date = hits["DATE"][0]
        output["date_iso"] = first_date.get("value")
        output["date_text"] = first_date.get("raw_date")

    if output["amount_value"] is None and hits["AMOUNT"]:
        first_amount = hits["AMOUNT"][0]
        output["amount_value"] = first_amount.get("value")
        output["amount_currency"] = first_amount.get("currency")

    return output


def safe_failure(
    reason: str,
    partial_output: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "status": "failed",
        "reason": reason,
        "partial_output": partial_output or empty_extraction(),
        "needs_manual_review": True,
        "warnings": warnings or [],
    }


def _clean_rejected_fields(base: dict[str, Any] | None, review: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(base, dict):
        return None
    cleaned = dict(base)
    for issue in review.get("issues", []):
        if not isinstance(issue, dict):
            continue
        field = issue.get("field")
        problem = str(issue.get("problem", "")).lower()
        if field in cleaned and any(token in problem for token in ["not grounded", "hallucinated", "contradiction"]):
            cleaned[field] = None
            if field == "document_id":
                cleaned["document_type"] = None
            if field == "amount_value":
                cleaned["amount_currency"] = None
            if field == "date_iso":
                cleaned["date_text"] = None
    return cleaned


def run_fallback(
    text: str,
    triage: dict[str, Any],
    extraction: dict[str, Any] | None,
    review: dict[str, Any],
    repair_agent: RepairAgent,
) -> dict[str, Any]:
    repair_result = repair_agent.run(text=text, triage=triage, extraction=extraction, review=review)
    repair_validation = validate_output(repair_result.raw_text)

    if repair_validation.is_valid:
        return {
            "action": "repair_agent",
            "success": True,
            "raw_repair_output": repair_result.raw_text,
            "output": repair_validation.parsed_json,
            "needs_manual_review": False,
            "errors": [],
        }

    clean_base = _clean_rejected_fields(extraction, review)
    rule_output = rule_based_partial(text, clean_base)
    rule_validation = validate_output(json.dumps(rule_output, ensure_ascii=False))
    issue_text = [
        *review.get("validator_errors", []),
        *repair_validation.error_messages(),
    ]

    if rule_validation.is_valid and any(value is not None for value in rule_output.values()):
        return {
            "action": "rule_based_partial",
            "success": True,
            "raw_repair_output": repair_result.raw_text,
            "output": rule_output,
            "needs_manual_review": True,
            "errors": issue_text,
        }

    return {
        "action": "safe_failure",
        "success": False,
        "raw_repair_output": repair_result.raw_text,
        "output": safe_failure(
            reason="repair and rule-based fallback did not produce a safe schema-valid extraction",
            partial_output=rule_output,
            warnings=issue_text,
        ),
        "needs_manual_review": True,
        "errors": issue_text,
    }
