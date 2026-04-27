from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from jsonschema import Draft202012Validator

from src.json_schema import get_schema


@dataclass
class ValidationResult:
    raw_text: str
    parsed_json: dict[str, Any] | None
    parse_success: bool
    schema_success: bool
    parse_error: str | None
    schema_errors: list[str]
    consistency_errors: list[str]

    @property
    def is_valid(self) -> bool:
        return self.parse_success and self.schema_success and not self.consistency_errors

    def error_messages(self) -> list[str]:
        messages: list[str] = []
        if self.parse_error:
            messages.append(f"JSON parse error: {self.parse_error}")
        messages.extend(f"Schema error: {msg}" for msg in self.schema_errors)
        messages.extend(f"Consistency error: {msg}" for msg in self.consistency_errors)
        return messages


_SCHEMA_VALIDATOR = Draft202012Validator(get_schema())


def _format_path(path_parts: list[Any]) -> str:
    if not path_parts:
        return "<root>"
    return ".".join(str(part) for part in path_parts)


def _check_consistency(parsed: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    if parsed.get("document_id") is None and parsed.get("document_type") is not None:
        errors.append("document_type must be null when document_id is null")

    if parsed.get("amount_value") is None and parsed.get("amount_currency") is not None:
        errors.append("amount_currency must be null when amount_value is null")

    if parsed.get("date_iso") is None and parsed.get("date_text") is not None:
        errors.append("date_text must be null when date_iso is null")

    return errors


def validate_output(raw_text: str) -> ValidationResult:
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            raw_text=raw_text,
            parsed_json=None,
            parse_success=False,
            schema_success=False,
            parse_error=str(exc),
            schema_errors=[],
            consistency_errors=[],
        )

    if not isinstance(parsed, dict):
        return ValidationResult(
            raw_text=raw_text,
            parsed_json=parsed,
            parse_success=True,
            schema_success=False,
            parse_error=None,
            schema_errors=["Top-level JSON value must be an object"],
            consistency_errors=[],
        )

    schema_errors = [
        f"{_format_path(list(error.path))}: {error.message}"
        for error in sorted(_SCHEMA_VALIDATOR.iter_errors(parsed), key=lambda e: list(e.path))
    ]
    consistency_errors = [] if schema_errors else _check_consistency(parsed)

    return ValidationResult(
        raw_text=raw_text,
        parsed_json=parsed,
        parse_success=True,
        schema_success=not schema_errors,
        parse_error=None,
        schema_errors=schema_errors,
        consistency_errors=consistency_errors,
    )
