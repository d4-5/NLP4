from __future__ import annotations

import re
from typing import Any

from src.ie_rules import extract_all
from src.json_schema import LAB11_SCHEMA
from src.validator import ValidationResult, validate_output


REQUIRED_FIELDS = list(LAB11_SCHEMA["required"])


def validation_for_extraction(raw_text: str) -> ValidationResult:
    return validate_output(raw_text)


def _issue(field: str, problem: str, severity: str = "medium") -> dict[str, str]:
    return {"field": field, "problem": problem, "severity": severity}


def _contains_loose(text: str, value: Any) -> bool:
    if value is None:
        return True
    value_s = str(value).strip()
    if not value_s:
        return True
    compact_text = re.sub(r"\s+", "", text.lower())
    compact_value = re.sub(r"\s+", "", value_s.lower())
    return compact_value in compact_text


def _amount_supported_by_rules(text: str, value: Any, currency: Any) -> bool:
    if value is None:
        return True
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return False
    for amount in extract_all(text)["AMOUNT"]:
        if abs(float(amount["value"]) - numeric) < 0.001:
            if currency is None or amount.get("currency") == currency or amount.get("currency") == "UNKNOWN":
                return True
    return False


def _field_presence_hints(text: str) -> dict[str, bool]:
    rule_hits = extract_all(text)
    return {
        "document_id": bool(rule_hits["DOC_ID"]),
        "date_iso": bool(rule_hits["DATE"]),
        "date_text": bool(rule_hits["DATE"]),
        "amount_value": bool(rule_hits["AMOUNT"]),
        "amount_currency": bool(rule_hits["AMOUNT"]),
    }


def review_extraction(
    text: str,
    raw_extraction: str,
    llm_review: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validation_for_extraction(raw_extraction)
    issues: list[dict[str, str]] = []

    if not validation.parse_success:
        issues.append(_issue("<root>", "extractor returned invalid JSON", "critical"))
    elif not validation.schema_success:
        for msg in validation.schema_errors:
            issues.append(_issue("<schema>", msg, "critical"))

    extraction = validation.parsed_json if validation.is_valid or validation.parsed_json else None
    if isinstance(extraction, dict):
        for field in REQUIRED_FIELDS:
            if field not in extraction:
                issues.append(_issue(field, "required field is missing", "critical"))

        if extraction.get("document_id") is not None and not _contains_loose(text, extraction["document_id"]):
            issues.append(_issue("document_id", "value is not grounded in source text", "critical"))
        if extraction.get("date_text") is not None and not _contains_loose(text, extraction["date_text"]):
            issues.append(_issue("date_text", "date_text is not an exact source span", "medium"))
        if not _amount_supported_by_rules(text, extraction.get("amount_value"), extraction.get("amount_currency")):
            issues.append(_issue("amount_value", "amount is not supported by rule evidence in source text", "critical"))

        if extraction.get("document_id") is None and extraction.get("document_type") is not None:
            issues.append(_issue("document_type", "document_type present without document_id", "critical"))
        if extraction.get("amount_value") is None and extraction.get("amount_currency") is not None:
            issues.append(_issue("amount_currency", "currency present without amount_value", "critical"))
        if extraction.get("date_iso") is None and extraction.get("date_text") is not None:
            issues.append(_issue("date_text", "date_text present without normalized date_iso", "medium"))

        hints = _field_presence_hints(text)
        for field, present in hints.items():
            if present and extraction.get(field) is None:
                issues.append(_issue(field, "likely missed field according to rule evidence", "medium"))

    llm_issues = []
    if llm_review:
        llm_issues = llm_review.get("issues") or []
        for item in llm_issues:
            if isinstance(item, dict):
                field = str(item.get("field", "<llm_review>"))
                problem = str(item.get("problem", item))
            else:
                field = "<llm_review>"
                problem = str(item)
            if problem and not any(existing["problem"] == problem and existing["field"] == field for existing in issues):
                issues.append(_issue(field, problem, "medium"))

    valid_json = validation.parse_success
    schema_ok = validation.parse_success and validation.schema_success
    critical = any(issue["severity"] == "critical" for issue in issues)
    consistency_ok = not critical and not any("not grounded" in issue["problem"] for issue in issues)

    if not valid_json or not schema_ok:
        verdict = "repair_needed"
        recommended_action = "run_repair_with_schema_errors"
    elif critical:
        verdict = "fallback_needed"
        recommended_action = "run_repair_then_rule_fallback"
    elif issues:
        verdict = "repair_needed"
        recommended_action = "run_repair_for_consistency_warnings"
    else:
        verdict = "accept"
        recommended_action = "accept"

    return {
        "verdict": verdict,
        "valid_json": valid_json,
        "schema_ok": schema_ok,
        "consistency_ok": consistency_ok,
        "issues": issues,
        "recommended_action": recommended_action,
        "validator_errors": validation.error_messages(),
        "llm_review": llm_review,
    }
