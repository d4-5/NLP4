import re
from typing import Iterable

LEGAL_ENTITY_PREFIXES = (
    "ТОВ",
    "ПАТ",
    "ПрАТ",
    "АТ",
    "ДП",
    "КП",
    "ВАТ",
    "НАК",
    "ФОП",
    "ПП",
    "ГО",
    "ОСББ",
)

ORG_ACRONYMS = {
    "АМКУ",
    "НАЗК",
    "ДСНС",
    "МВС",
    "КМДА",
    "ОДА",
    "НАН України",
    "СБУ",
    "Держпраці",
    "Держгеокадастру",
}

MONTHS = (
    "січня",
    "лютого",
    "березня",
    "квітня",
    "травня",
    "червня",
    "липня",
    "серпня",
    "вересня",
    "жовтня",
    "листопада",
    "грудня",
)

MONEY_PATTERN = re.compile(
    r"(?<!\w)(?:[$€₴]\s*)?\d{1,3}(?:[ \u00A0]\d{3})*(?:[.,]\d+)?(?:\s*(?:млн|мільйона|мільйонів|тис|тисяч|млрд))?\s*(?:грн\.?|гривень|гривні|доларів|долари|USD|EUR|UAH|₴|\$|€)",
    flags=re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    rf"(?<!\d)(?:\d{{1,2}}\s+(?:{'|'.join(MONTHS)})|(?:у\s+)?\d{{4}}\s+року|\d{{4}}\s*р\.?|(?:{'|'.join(MONTHS)})\s+\d{{4}}\s+року)",
    flags=re.IGNORECASE,
)

LEGAL_FORM_PATTERN = re.compile(
    r"(?P<full>(?:ТОВ|ПАТ|ПрАТ|АТ|ДП|КП|ВАТ|НАК|ФОП|ПП|ГО|ОСББ)\s+[\"«][^\n\"»]{2,120}[\"»])"
)

TITLE_CASE_ORG_PATTERN = re.compile(
    r"(?P<full>(?:Громадська організація|Міністерство|Департамент|Аеропорт|Інститут|Управління|Верховна Рада|Апеляційний суд|Служба безпеки України|Європейський банк реконструкції та розвитку)[^\n,.]{0,120})"
)


def _make_entity(text: str, label: str, start: int, end: int, rule_id: str) -> dict[str, object]:
    return {
        "text": text[start:end],
        "label": label,
        "start_char": start,
        "end_char": end,
        "source": f"rule:{rule_id}",
    }


def money_rule(text: str) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []
    for match in MONEY_PATTERN.finditer(text):
        start, end = match.span()
        entities.append(_make_entity(text, "MON", start, end, "money_regex_v1"))
    return entities



def date_rule(text: str) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []
    for match in DATE_PATTERN.finditer(text):
        start, end = match.span()
        entities.append(_make_entity(text, "DATE", start, end, "date_regex_v1"))
    return entities



def legal_form_org_rule(text: str) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []
    for match in LEGAL_FORM_PATTERN.finditer(text):
        start, end = match.span("full")
        entities.append(_make_entity(text, "ORG", start, end, "org_legal_form_v1"))

    for match in TITLE_CASE_ORG_PATTERN.finditer(text):
        start, end = match.span("full")
        entities.append(_make_entity(text, "ORG", start, end, "org_title_case_v1"))

    for acronym in sorted(ORG_ACRONYMS, key=len, reverse=True):
        for match in re.finditer(rf"(?<!\w){re.escape(acronym)}(?!\w)", text):
            start, end = match.span()
            entities.append(_make_entity(text, "ORG", start, end, "org_acronym_v1"))
    return entities



def _is_quoted_org_char(ch: str) -> bool:
    return ch in {'"', '«', '»'}



def expand_org_boundaries(text: str, entities: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    expanded: list[dict[str, object]] = []
    for entity in entities:
        if entity.get("label") != "ORG":
            expanded.append(dict(entity))
            continue

        start = int(entity["start_char"])
        end = int(entity["end_char"])

        prefix_window_start = max(0, start - 8)
        prefix_window = text[prefix_window_start:start]
        prefix_match = re.search(r"(?:ТОВ|ПАТ|ПрАТ|АТ|ДП|КП|ВАТ|НАК|ФОП|ПП|ГО|ОСББ)\s*$", prefix_window)
        if prefix_match:
            start = prefix_window_start + prefix_match.start()

        while start > 0 and _is_quoted_org_char(text[start - 1]):
            start -= 1
        while end < len(text) and _is_quoted_org_char(text[end]):
            end += 1

        new_entity = dict(entity)
        new_entity["start_char"] = start
        new_entity["end_char"] = end
        new_entity["text"] = text[start:end]
        new_entity["source"] = f"{entity.get('source', 'baseline')}+boundary_expand_v1"
        expanded.append(new_entity)
    return expanded



def collect_rule_entities(text: str) -> list[dict[str, object]]:
    entities: list[dict[str, object]] = []
    entities.extend(money_rule(text))
    entities.extend(date_rule(text))
    entities.extend(legal_form_org_rule(text))
    return entities
