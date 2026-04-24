import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

from src.ner_pipeline import normalize_label, read_jsonl

FOCUS_LABELS = {"PERS", "ORG", "DATE", "MON", "LOC"}
DOMAIN_ORG_HINTS = (
    "ТОВ",
    "ПАТ",
    "ДП",
    "ПрАТ",
    "АТ",
    "КП",
    "ГО",
    "НАЗК",
    "АМКУ",
    "ОДА",
    "КМДА",
)


def _norm_entity(entity: dict[str, object]) -> dict[str, object]:
    item = dict(entity)
    item["label"] = normalize_label(str(item["label"]))
    item["start_char"] = int(item["start_char"])
    item["end_char"] = int(item["end_char"])
    return item


def _filter_entities(entities: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [
        _norm_entity(entity)
        for entity in entities
        if normalize_label(str(entity["label"])) in FOCUS_LABELS
    ]


def _entity_key(entity: dict[str, object]) -> tuple[int, int, str, str]:
    return (
        int(entity["start_char"]),
        int(entity["end_char"]),
        str(entity["label"]),
        str(entity["text"]),
    )


def _overlap(a: dict[str, object], b: dict[str, object]) -> bool:
    return int(a["start_char"]) < int(b["end_char"]) and int(b["start_char"]) < int(
        a["end_char"]
    )


def compute_metrics(
    records: list[dict[str, object]],
) -> dict[str, dict[str, float | int]]:
    stats = {
        label: {"gold": 0, "pred": 0, "correct": 0} for label in sorted(FOCUS_LABELS)
    }
    for record in records:
        gold = _filter_entities(record["expected_entities"])
        pred = _filter_entities(record["predicted_entities"])
        gold_keys = {_entity_key(entity) for entity in gold}
        pred_keys = {_entity_key(entity) for entity in pred}
        for label in FOCUS_LABELS:
            stats[label]["gold"] += sum(
                1 for entity in gold if entity["label"] == label
            )
            stats[label]["pred"] += sum(
                1 for entity in pred if entity["label"] == label
            )
            stats[label]["correct"] += sum(
                1
                for entity in gold
                if entity["label"] == label and _entity_key(entity) in pred_keys
            )

    metrics: dict[str, dict[str, float | int]] = {}
    for label, values in stats.items():
        pred = int(values["pred"])
        gold = int(values["gold"])
        correct = int(values["correct"])
        precision = correct / pred if pred else 0.0
        recall = correct / gold if gold else 0.0
        metrics[label] = {
            "gold": gold,
            "predicted": pred,
            "correct": correct,
            "missed": gold - correct,
            "false_positive": pred - correct,
            "rough_precision": round(precision, 4),
            "rough_recall": round(recall, 4),
        }
    return metrics


def compare_runs(
    baseline_records: list[dict[str, object]], hybrid_records: list[dict[str, object]]
) -> dict[str, object]:
    baseline_metrics = compute_metrics(baseline_records)
    hybrid_metrics = compute_metrics(hybrid_records)
    delta: dict[str, dict[str, float | int]] = {}
    for label in sorted(FOCUS_LABELS):
        delta[label] = {
            "correct_delta": int(hybrid_metrics[label]["correct"])
            - int(baseline_metrics[label]["correct"]),
            "missed_delta": int(hybrid_metrics[label]["missed"])
            - int(baseline_metrics[label]["missed"]),
            "false_positive_delta": int(hybrid_metrics[label]["false_positive"])
            - int(baseline_metrics[label]["false_positive"]),
            "precision_delta": round(
                float(hybrid_metrics[label]["rough_precision"])
                - float(baseline_metrics[label]["rough_precision"]),
                4,
            ),
            "recall_delta": round(
                float(hybrid_metrics[label]["rough_recall"])
                - float(baseline_metrics[label]["rough_recall"]),
                4,
            ),
        }
    return {
        "baseline_metrics": baseline_metrics,
        "hybrid_metrics": hybrid_metrics,
        "delta": delta,
    }


def _error_category(
    gold: dict[str, object] | None, pred: dict[str, object] | None
) -> str:
    if gold and pred:
        if gold["label"] != pred["label"] and _overlap(gold, pred):
            return "type error"
        if gold["label"] == pred["label"] and _overlap(gold, pred):
            return "boundary error"
    if (
        gold
        and gold["label"] == "ORG"
        and any(hint in str(gold["text"]) for hint in DOMAIN_ORG_HINTS)
    ):
        return "missed domain entity"
    if gold and gold["label"] in {"DATE", "MON"}:
        return "normalization issue"
    if (
        pred
        and pred["label"] in {"DATE", "MON"}
        and any(ch in str(pred["text"]) for ch in [".", ",", "$", "грн"])
    ):
        return "tokenization / normalization issue"
    if pred and not gold:
        return "false positive"
    return "ambiguous case"


def collect_errors(
    records: list[dict[str, object]], limit: int | None = None
) -> list[dict[str, object]]:
    errors: list[dict[str, object]] = []
    for record in records:
        gold = _filter_entities(record["expected_entities"])
        pred = _filter_entities(record["predicted_entities"])
        gold_matched: set[int] = set()
        pred_matched: set[int] = set()

        for g_idx, gold_entity in enumerate(gold):
            for p_idx, pred_entity in enumerate(pred):
                if _entity_key(gold_entity) == _entity_key(pred_entity):
                    gold_matched.add(g_idx)
                    pred_matched.add(p_idx)
                    break

        for g_idx, gold_entity in enumerate(gold):
            if g_idx in gold_matched:
                continue
            overlap_pred = next(
                (
                    pred[p_idx]
                    for p_idx in range(len(pred))
                    if _overlap(gold_entity, pred[p_idx])
                ),
                None,
            )
            errors.append(
                {
                    "text_id": record["text_id"],
                    "text_snippet": record["text"][:280],
                    "expected_entity": gold_entity,
                    "predicted_entity": overlap_pred,
                    "category": _error_category(gold_entity, overlap_pred),
                    "explanation": _explain_error(gold_entity, overlap_pred),
                }
            )

        for p_idx, pred_entity in enumerate(pred):
            if p_idx in pred_matched:
                continue
            if any(_overlap(pred_entity, gold_entity) for gold_entity in gold):
                continue
            errors.append(
                {
                    "text_id": record["text_id"],
                    "text_snippet": record["text"][:280],
                    "expected_entity": None,
                    "predicted_entity": pred_entity,
                    "category": _error_category(None, pred_entity),
                    "explanation": _explain_error(None, pred_entity),
                }
            )

    if limit is not None:
        return errors[:limit]
    return errors


def _explain_error(
    gold: dict[str, object] | None, pred: dict[str, object] | None
) -> str:
    if gold and pred:
        if gold["label"] != pred["label"]:
            return f"Є overlap по span, але тип розійшовся: expected={gold['label']}, predicted={pred['label']}."
        return "Модель знайшла близький span, але межі сутності не збіглися з gold-розміткою."
    if gold and not pred:
        if gold["label"] == "ORG":
            return "Сутність пропущена повністю; це типовий кейс для доменної організації або складної назви."
        if gold["label"] in {"DATE", "MON"}:
            return "Сутність має регулярний патерн, але baseline її не покрив або покрив неповністю."
        return "Gold-сутність не була знайдена жодним pred span у цьому фрагменті."
    if pred and not gold:
        return "Pipeline згенерував зайву сутність без відповідника в gold set."
    return "Потребує ручного перегляду: випадок неоднозначний."


def error_summary(errors: Iterable[dict[str, object]]) -> dict[str, int]:
    counter = Counter(error["category"] for error in errors)
    return dict(counter.most_common())
