import json
import re
from datetime import date
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
RESOURCES_DIR = BASE_DIR / "resources"


DEFAULT_CURRENCY_MAP = {
    "грн": "UAH",
    "гривень": "UAH",
    "гривня": "UAH",
    "гривні": "UAH",
    "₴": "UAH",
    "uah": "UAH",
    "$": "USD",
    "usd": "USD",
    "доларів": "USD",
    "долари": "USD",
    "€": "EUR",
    "eur": "EUR",
    "євро": "EUR",
}

DEFAULT_DOC_CONTEXT_WORDS = [
    "договір",
    "договору",
    "провадження",
    "постанова",
    "розпорядження",
    "справа",
    "наказ",
    "рахунок",
    "рішення",
    "ухвала",
]

DOC_CONTEXT_BLOCKLIST = [
    "табор",
    "ст.",
    "статт",
    "випуск",
    "номер журналу",
]


DATE_PATTERN = re.compile(
    r"(?<!\d)(?P<day>0?[1-9]|[12]\d|3[01])[./-](?P<month>0?[1-9]|1[0-2])[./-](?P<year>19\d{2}|20\d{2})(?!\d)"
)

AMOUNT_PATTERN = re.compile(
    r"(?<!\w)"
    r"(?P<full>"
    r"(?P<symbol>[$€₴])\s*(?P<num1>\d{1,3}(?:[ \u00A0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)"
    r"|"
    r"(?P<num2>\d{1,3}(?:[ \u00A0]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?)\s*(?P<curr>грн|гривень|гривня|гривні|uah|usd|eur|доларів|долари|євро|₴)"
    r")",
    flags=re.IGNORECASE,
)

DOC_ID_PATTERN = re.compile(
    r"№\s*(?P<docid>[A-Za-zА-Яа-яІіЇїЄє0-9][A-Za-zА-Яа-яІіЇїЄє0-9\-/]{0,30})"
)


def _load_currency_map() -> dict[str, str]:
    path = RESOURCES_DIR / "currencies.json"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        return {k.lower(): v for k, v in data.items()}
    return DEFAULT_CURRENCY_MAP.copy()


def _load_doc_context_words() -> list[str]:
    path = RESOURCES_DIR / "doc_id_context_words.txt"
    if path.exists():
        words = [line.strip().lower() for line in path.read_text(encoding="utf-8").splitlines()]
        return [w for w in words if w and not w.startswith("#")]
    return DEFAULT_DOC_CONTEXT_WORDS[:]


CURRENCY_MAP = _load_currency_map()
DOC_CONTEXT_WORDS = _load_doc_context_words()


def _parse_date(day_s: str, month_s: str, year_s: str) -> str | None:
    try:
        normalized = date(int(year_s), int(month_s), int(day_s))
        return normalized.isoformat()
    except ValueError:
        return None


def _normalize_number(raw_num: str) -> float | None:
    s = raw_num.replace("\u00A0", " ").strip()
    s = re.sub(r"\s+", "", s)

    if "," in s and "." in s:
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "")
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "," in s:
        comma_count = s.count(",")
        after = len(s) - s.rfind(",") - 1
        if comma_count == 1 and 1 <= after <= 2:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")

    try:
        return float(s)
    except ValueError:
        return None


def _currency_to_iso(token: str | None) -> str:
    if not token:
        return "UNKNOWN"
    return CURRENCY_MAP.get(token.lower(), "UNKNOWN")


def _has_doc_context(text: str, start: int, end: int) -> bool:
    left = max(0, start - 60)
    right = min(len(text), end + 60)
    window = text[left:right].lower()
    return any(keyword in window for keyword in DOC_CONTEXT_WORDS)


def _is_doc_context_blocked(text: str, start: int, end: int) -> bool:
    left = max(0, start - 30)
    right = min(len(text), end + 30)
    window = text[left:right].lower()
    return any(blocked in window for blocked in DOC_CONTEXT_BLOCKLIST)


def _infer_doc_type(text: str, start: int, end: int) -> str:
    left = max(0, start - 70)
    right = min(len(text), end + 70)
    window = text[left:right].lower()
    if "провадження" in window or "справа" in window:
        return "CASE_ID"
    if "догов" in window:
        return "CONTRACT_ID"
    if "наказ" in window or "розпорядження" in window:
        return "ORDER_ID"
    return "GENERIC_DOC_ID"


def extract_dates(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in DATE_PATTERN.finditer(text):
        start, end = match.span()
        raw_date = match.group(0)
        normalized = _parse_date(match.group("day"), match.group("month"), match.group("year"))
        if normalized is None:
            results.append(
                {
                    "field_type": "DATE",
                    "value": raw_date,
                    "raw_date": raw_date,
                    "parsed_date": None,
                    "start_char": start,
                    "end_char": end,
                    "method": "regex_date_v1_unparsed",
                }
            )
            continue
        results.append(
            {
                "field_type": "DATE",
                "value": normalized,
                "raw_date": raw_date,
                "start_char": start,
                "end_char": end,
                "method": "regex_date_v1",
            }
        )
    return results


def extract_amounts(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in AMOUNT_PATTERN.finditer(text):
        full = match.group("full")
        start, end = match.span("full")

        if end < len(text) and text[end] == "%":
            continue

        num = match.group("num1") or match.group("num2")
        if not num:
            continue
        value = _normalize_number(num)
        if value is None:
            continue

        symbol = match.group("symbol")
        curr = match.group("curr")
        currency_token = symbol or curr
        currency = _currency_to_iso(currency_token)

        results.append(
            {
                "field_type": "AMOUNT",
                "value": value,
                "currency": currency,
                "raw_value": full,
                "start_char": start,
                "end_char": end,
                "method": "regex_amount_v1",
            }
        )
    return results


def extract_doc_ids(text: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for match in DOC_ID_PATTERN.finditer(text):
        start, end = match.span()
        doc_id_raw = match.group("docid")
        doc_id_clean = doc_id_raw.strip(".,;:()[]{}")

        if len(doc_id_clean) < 2:
            continue
        if _is_doc_context_blocked(text, start, end):
            continue
        if not _has_doc_context(text, start, end):
            continue

        doc_type = _infer_doc_type(text, start, end)
        results.append(
            {
                "field_type": "DOC_ID",
                "type": doc_type,
                "value": doc_id_clean,
                "raw_value": match.group(0),
                "start_char": start,
                "end_char": end,
                "method": "context_doc_id_v1",
            }
        )
    return results


def extract_all(text: str) -> dict[str, list[dict[str, Any]]]:
    return {
        "DATE": extract_dates(text),
        "AMOUNT": extract_amounts(text),
        "DOC_ID": extract_doc_ids(text),
    }

