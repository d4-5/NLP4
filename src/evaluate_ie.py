import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.ie_rules import extract_all


def _norm_value(field_type: str, value: Any) -> Any:
    if field_type == "AMOUNT":
        if isinstance(value, dict):
            return {
                "value": float(value.get("value")) if value.get("value") is not None else None,
                "currency": value.get("currency", "UNKNOWN"),
            }
        return value
    if field_type == "DOC_ID":
        if isinstance(value, dict):
            return {"type": value.get("type"), "value": value.get("value")}
        return value
    return value


def _gold_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["text_id"],
        row["field_type"],
        int(row["start_char"]),
        int(row["end_char"]),
        json.dumps(_norm_value(row["field_type"], row["normalized_value"]), ensure_ascii=False, sort_keys=True),
    )


def _pred_key(text_id: str, ent: dict[str, Any]) -> tuple[Any, ...]:
    field_type = ent["field_type"]
    if field_type == "AMOUNT":
        value = {"value": ent.get("value"), "currency": ent.get("currency", "UNKNOWN")}
    elif field_type == "DOC_ID":
        value = {"type": ent.get("type"), "value": ent.get("value")}
    else:
        value = ent.get("value")
    return (
        text_id,
        field_type,
        int(ent["start_char"]),
        int(ent["end_char"]),
        json.dumps(_norm_value(field_type, value), ensure_ascii=False, sort_keys=True),
    )


def evaluate(gold_path: Path) -> dict[str, dict[str, float | int]]:
    gold_rows: list[dict[str, Any]] = []
    with gold_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                gold_rows.append(json.loads(line))

    texts_by_id: dict[str, str] = {}
    gold_by_type: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    for row in gold_rows:
        texts_by_id[row["text_id"]] = row["text"]
        gold_by_type[row["field_type"]].add(_gold_key(row))

    pred_by_type: dict[str, set[tuple[Any, ...]]] = defaultdict(set)
    for text_id, text in texts_by_id.items():
        extracted = extract_all(text)
        for field_type, entities in extracted.items():
            for ent in entities:
                pred_by_type[field_type].add(_pred_key(text_id, ent))

    metrics: dict[str, dict[str, float | int]] = {}
    for field_type in sorted(set(gold_by_type) | set(pred_by_type)):
        gold_set = gold_by_type.get(field_type, set())
        pred_set = pred_by_type.get(field_type, set())
        correct = len(gold_set & pred_set)
        total_pred = len(pred_set)
        precision = (correct / total_pred) if total_pred else 0.0
        metrics[field_type] = {
            "correct_extractions": correct,
            "all_extractions": total_pred,
            "precision": round(precision, 4),
            "gold_size": len(gold_set),
        }
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate rule-based IE precision on gold subset.")
    parser.add_argument(
        "--gold-path",
        default="data/sample/lab4_gold_ie.jsonl",
        help="Path to gold JSONL file.",
    )
    args = parser.parse_args()
    metrics = evaluate(Path(args.gold_path))
    print(json.dumps(metrics, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

