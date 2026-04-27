from __future__ import annotations

import json
from copy import deepcopy


EXTRACTION_TASK_NAME = "document_signal_extraction"

SCHEMA_VERSION = "1.0"

ALLOWED_DOC_TYPES = ["CASE_ID", "CONTRACT_ID", "ORDER_ID", "GENERIC_DOC_ID"]
ALLOWED_CURRENCIES = ["UAH", "USD", "EUR", "UNKNOWN"]

LAB11_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Lab 11 document signal extraction schema",
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "document_id": {
            "type": ["string", "null"],
            "minLength": 1,
            "description": "Document or case identifier without the leading number sign.",
        },
        "document_type": {
            "type": ["string", "null"],
            "enum": ALLOWED_DOC_TYPES + [None],
            "description": "Normalized document type or null if there is no document id.",
        },
        "date_iso": {
            "type": ["string", "null"],
            "pattern": r"^\d{4}-\d{2}-\d{2}$",
            "description": "Normalized date in ISO format YYYY-MM-DD.",
        },
        "date_text": {
            "type": ["string", "null"],
            "minLength": 1,
            "description": "Original date expression as it appears in the text.",
        },
        "amount_value": {
            "type": ["number", "null"],
            "minimum": 0,
            "description": "Normalized numeric amount.",
        },
        "amount_currency": {
            "type": ["string", "null"],
            "enum": ALLOWED_CURRENCIES + [None],
            "description": "Normalized ISO-like currency code.",
        },
    },
    "required": [
        "document_id",
        "document_type",
        "date_iso",
        "date_text",
        "amount_value",
        "amount_currency",
    ],
}


def get_schema() -> dict:
    return deepcopy(LAB11_SCHEMA)


def schema_as_pretty_json() -> str:
    return json.dumps(LAB11_SCHEMA, ensure_ascii=False, indent=2)


def schema_rules_text() -> str:
    return (
        "Return exactly one JSON object with these required keys: "
        "document_id, document_type, date_iso, date_text, amount_value, amount_currency. "
        "Use null when a value is absent. "
        "If document_id is null then document_type must also be null. "
        "If amount_value is null then amount_currency must also be null. "
        "date_iso must use YYYY-MM-DD when present. "
        "Allowed document_type values: CASE_ID, CONTRACT_ID, ORDER_ID, GENERIC_DOC_ID, null. "
        "Allowed amount_currency values: UAH, USD, EUR, UNKNOWN, null. "
        "Do not include explanations, markdown, comments, or extra keys."
    )
