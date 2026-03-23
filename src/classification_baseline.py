from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import Pipeline


@dataclass
class BaselineConfig:
    ngram_range: tuple[int, int] = (1, 1)
    max_iter: int = 400
    class_weight: str | None = None
    analyzer: str = "word"
    sublinear_tf: bool = True


def load_processed(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def load_labels(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def build_dominant_labels(labels_df: pd.DataFrame) -> pd.DataFrame:
    counts = (
        labels_df.groupby(["text_id", "label"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
    )
    idx = counts.groupby("text_id")["count"].idxmax()
    dominant = counts.loc[idx, ["text_id", "label"]].rename(
        columns={"label": "dominant_label"}
    )
    return dominant


def attach_labels(processed_df: pd.DataFrame, labels_df: pd.DataFrame) -> pd.DataFrame:
    dominant = build_dominant_labels(labels_df)
    merged = processed_df.merge(dominant, on="text_id", how="left")
    merged["dominant_label"] = merged["dominant_label"].fillna("NO_ENTITY")
    return merged


def load_split_ids(split_dir: str | Path) -> dict[str, list[str]]:
    split_dir = Path(split_dir)
    splits: dict[str, list[str]] = {}
    for split_name in ("train", "val", "test"):
        path = split_dir / f"splits_{split_name}_ids.txt"
        with path.open("r", encoding="utf-8") as f:
            splits[split_name] = [line.strip() for line in f if line.strip()]
    return splits


def filter_by_ids(df: pd.DataFrame, ids: Iterable[str]) -> pd.DataFrame:
    id_set = set(ids)
    return df[df["text_id"].isin(id_set)].copy()


def build_pipeline(cfg: BaselineConfig) -> Pipeline:
    vectorizer = TfidfVectorizer(
        analyzer=cfg.analyzer,
        ngram_range=cfg.ngram_range,
        sublinear_tf=cfg.sublinear_tf,
    )
    clf = LogisticRegression(
        max_iter=cfg.max_iter,
        class_weight=cfg.class_weight,
        random_state=42,
    )
    return Pipeline([("tfidf", vectorizer), ("logreg", clf)])


def evaluate_split(model: Pipeline, x, y) -> Mapping[str, float]:
    preds = model.predict(x)
    return {
        "accuracy": accuracy_score(y, preds),
        "macro_f1": f1_score(y, preds, average="macro"),
    }


def full_report(model: Pipeline, x, y) -> str:
    preds = model.predict(x)
    return classification_report(y, preds)


def get_confusion(model: Pipeline, x, y) -> tuple[pd.DataFrame, list[str]]:
    preds = model.predict(x)
    labels = list(model.named_steps["logreg"].classes_)
    matrix = confusion_matrix(y, preds, labels=labels)
    return pd.DataFrame(matrix, index=labels, columns=labels), labels


def top_features(
    model: Pipeline, top_k: int = 10, negative: bool = False
) -> dict[str, list[tuple[str, float]]]:
    vectorizer: TfidfVectorizer = model.named_steps["tfidf"]
    clf: LogisticRegression = model.named_steps["logreg"]
    feature_names = vectorizer.get_feature_names_out()
    coefs = clf.coef_

    results: dict[str, list[tuple[str, float]]] = {}
    classes = list(clf.classes_)

    if coefs.shape[0] == 1:
        target_classes = [classes[1]]
        coef_rows = [coefs[0]]
    else:
        target_classes = classes
        coef_rows = coefs

    for label, weights in zip(target_classes, coef_rows):
        if negative:
            top_idx = weights.argsort()[:top_k]
        else:
            top_idx = weights.argsort()[::-1][:top_k]
        results[label] = [(feature_names[i], float(weights[i])) for i in top_idx]

    return results
