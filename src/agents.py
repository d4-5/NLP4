from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from src.json_schema import schema_as_pretty_json, schema_rules_text
from src.llm_extract import DEFAULT_MODEL, groq_chat_completion


def _json_block(title: str, payload: Any) -> str:
    return f"{title}:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"


@dataclass
class AgentResult:
    role: str
    raw_text: str
    parsed_json: dict[str, Any] | None
    usage: dict[str, Any] | None


class GroqLLMClient:
    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.1,
        max_tokens: int = 700,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete_json(
        self,
        role: str,
        messages: list[dict[str, str]],
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AgentResult:
        raw_text, usage = groq_chat_completion(
            messages=messages,
            model=self.model,
            temperature=self.temperature if temperature is None else temperature,
            max_tokens=self.max_tokens if max_tokens is None else max_tokens,
        )
        try:
            parsed = json.loads(raw_text)
        except json.JSONDecodeError:
            parsed = None
        return AgentResult(role=role, raw_text=raw_text, parsed_json=parsed, usage=usage)


class TriagerAgent:
    def __init__(self, client: GroqLLMClient) -> None:
        self.client = client

    def run(self, text: str) -> AgentResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Triager in a multi-agent extraction crew. "
                    "Read the Ukrainian input and choose the extraction route. "
                    "Do not extract final field values. Return only JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Choose one route: document_signal_schema, amount_only_schema, date_only_schema, "
                    "generic_document_schema, manual_review_route. Return exactly these keys: "
                    "task_type, route, expected_fields, difficulty, special_handling, notes. "
                    "expected_fields must be the Lab 11 schema keys when document signals may be present.\n\n"
                    f"Schema rules:\n{schema_rules_text()}\n\nText:\n{text}"
                ),
            },
        ]
        return self.client.complete_json("triager", messages, temperature=0.0, max_tokens=450)


class ExtractorAgent:
    def __init__(self, client: GroqLLMClient) -> None:
        self.client = client

    def run(self, text: str, triage: dict[str, Any]) -> AgentResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Extractor in a multi-agent crew. "
                    "Extract only the requested schema as JSON. Do not invent values. "
                    "Use null when a field is absent. Return only one JSON object."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Use the triage route and expected schema below. "
                    "Return exactly the Lab 11 extraction JSON keys and no extra keys.\n\n"
                    f"{_json_block('Triager output', triage)}\n\n"
                    f"JSON schema:\n{schema_as_pretty_json()}\n\n"
                    f"Text:\n{text}"
                ),
            },
        ]
        return self.client.complete_json("extractor", messages, temperature=0.1, max_tokens=500)


class ReviewerAgent:
    def __init__(self, client: GroqLLMClient) -> None:
        self.client = client

    def run(
        self,
        text: str,
        triage: dict[str, Any],
        extraction: dict[str, Any] | None,
        validation_errors: list[str],
    ) -> AgentResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Reviewer in a multi-agent extraction crew. "
                    "Check schema, completeness, hallucinations, and consistency against the source text. "
                    "Do not rewrite the extraction unless you recommend repair. Return only JSON."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Review the extraction. Return exactly these keys: verdict, valid_json, schema_ok, "
                    "consistency_ok, issues, recommended_action. verdict must be one of "
                    "accept, repair_needed, fallback_needed, manual_review.\n\n"
                    f"{_json_block('Triager output', triage)}\n\n"
                    f"{_json_block('Extractor output', extraction)}\n\n"
                    f"{_json_block('Validator errors', validation_errors)}\n\n"
                    f"Source text:\n{text}"
                ),
            },
        ]
        return self.client.complete_json("reviewer", messages, temperature=0.0, max_tokens=600)


class RepairAgent:
    def __init__(self, client: GroqLLMClient) -> None:
        self.client = client

    def run(
        self,
        text: str,
        triage: dict[str, Any],
        extraction: dict[str, Any] | None,
        review: dict[str, Any],
    ) -> AgentResult:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are the Repair/Fallback agent in a multi-agent extraction crew. "
                    "Fix only fields identified by the Reviewer. Do not change correct fields. "
                    "Return only the Lab 11 schema JSON with no metadata and no extra keys."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Repair the extraction so it parses as JSON, follows the schema, and is grounded in the text. "
                    "Use null for missing or unsafe values.\n\n"
                    f"{_json_block('Triager output', triage)}\n\n"
                    f"{_json_block('Current extraction', extraction)}\n\n"
                    f"{_json_block('Reviewer verdict', review)}\n\n"
                    f"JSON schema:\n{schema_as_pretty_json()}\n\n"
                    f"Source text:\n{text}"
                ),
            },
        ]
        return self.client.complete_json("repair", messages, temperature=0.0, max_tokens=500)
