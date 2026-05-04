from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import requests
except ModuleNotFoundError:  # pragma: no cover - handled at runtime for lightweight imports.
    requests = None

from src.json_schema import EXTRACTION_TASK_NAME, SCHEMA_VERSION, schema_as_pretty_json, schema_rules_text
from src.validator import ValidationResult, validate_output


GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
DEFAULT_MODEL = "llama-3.1-8b-instant"


@dataclass
class LLMResponse:
    raw_text: str
    model: str
    prompt_kind: str
    validation: ValidationResult
    usage: dict[str, Any] | None


def load_eval_set(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def build_extraction_messages(text: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an information extraction engine. "
                "Return only JSON. "
                f"Task={EXTRACTION_TASK_NAME}. Schema version={SCHEMA_VERSION}. "
                f"{schema_rules_text()}"
            ),
        },
        {
            "role": "user",
            "content": (
                "Extract the first relevant document/date/amount signals in reading order from the Ukrainian text. "
                "If a field is absent, return null. "
                "Keep date_text exactly as in the source when present.\n\n"
                "JSON schema:\n"
                f"{schema_as_pretty_json()}\n\n"
                "Text:\n"
                f"{text}"
            ),
        },
    ]


def build_repair_messages(text: str, broken_output: str, error_messages: list[str]) -> list[dict[str, str]]:
    error_block = "\n".join(f"- {msg}" for msg in error_messages) or "- unknown validation issue"
    return [
        {
            "role": "system",
            "content": (
                "You repair invalid JSON extraction outputs. "
                "Return only a corrected JSON object with no extra text. "
                f"Task={EXTRACTION_TASK_NAME}. Schema version={SCHEMA_VERSION}. "
                f"{schema_rules_text()}"
            ),
        },
        {
            "role": "user",
            "content": (
                "The previous extraction result is invalid. "
                "Fix it so that it parses as JSON and passes the schema.\n\n"
                "Original text:\n"
                f"{text}\n\n"
                "Broken output:\n"
                f"{broken_output}\n\n"
                "Validation errors:\n"
                f"{error_block}\n\n"
                "Return only the repaired JSON object."
            ),
        },
    ]


def groq_chat_completion(
    messages: list[dict[str, str]],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 400,
    timeout: int = 60,
    max_retries: int = 5,
) -> tuple[str, dict[str, Any] | None]:
    if requests is None:
        raise RuntimeError("requests is not installed. Run: pip install -r labs/lab13/requirements.txt")

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "messages": messages,
                },
                timeout=timeout,
            )
            if response.status_code == 429 and attempt < max_retries - 1:
                retry_after = response.headers.get("Retry-After")
                sleep_seconds = float(retry_after) if retry_after else min(20, 2 ** attempt)
                time.sleep(sleep_seconds)
                continue
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            usage = payload.get("usage")
            return content.strip(), usage
        except requests.RequestException as exc:
            last_error = exc
            if attempt >= max_retries - 1:
                break
            time.sleep(min(20, 2 ** attempt))

    raise RuntimeError(f"Groq request failed after {max_retries} attempts: {last_error}") from last_error


def extract_once(text: str, model: str = DEFAULT_MODEL, temperature: float = 0.2) -> LLMResponse:
    raw_text, usage = groq_chat_completion(
        messages=build_extraction_messages(text),
        model=model,
        temperature=temperature,
    )
    validation = validate_output(raw_text)
    return LLMResponse(
        raw_text=raw_text,
        model=model,
        prompt_kind="extract",
        validation=validation,
        usage=usage,
    )


def repair_once(
    text: str,
    broken_output: str,
    error_messages: list[str],
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
) -> LLMResponse:
    raw_text, usage = groq_chat_completion(
        messages=build_repair_messages(text, broken_output, error_messages),
        model=model,
        temperature=temperature,
    )
    validation = validate_output(raw_text)
    return LLMResponse(
        raw_text=raw_text,
        model=model,
        prompt_kind="repair",
        validation=validation,
        usage=usage,
    )
