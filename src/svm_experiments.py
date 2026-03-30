from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.svm import LinearSVC


@dataclass
class LinearSVCConfig:
    analyzer: str = "word"
    ngram_range: tuple[int, int] = (1, 2)
    sublinear_tf: bool = True
    C: float = 1.0
    class_weight: str | dict[str, float] | None = None
    max_features: int | None = None
    dual: str | bool = "auto"


@dataclass
class WordCharLinearSVCConfig:
    word_ngram_range: tuple[int, int] = (1, 2)
    char_analyzer: str = "char_wb"
    char_ngram_range: tuple[int, int] = (3, 5)
    sublinear_tf: bool = True
    C: float = 1.0
    class_weight: str | dict[str, float] | None = None
    word_max_features: int | None = None
    char_max_features: int | None = None
    dual: str | bool = "auto"


def build_linear_svc_pipeline(cfg: LinearSVCConfig) -> Pipeline:
    vectorizer = TfidfVectorizer(
        analyzer=cfg.analyzer,
        ngram_range=cfg.ngram_range,
        sublinear_tf=cfg.sublinear_tf,
        max_features=cfg.max_features,
    )
    clf = LinearSVC(
        C=cfg.C,
        class_weight=cfg.class_weight,
        dual=cfg.dual,
        random_state=42,
    )
    return Pipeline([("tfidf", vectorizer), ("linearsvc", clf)])


def build_word_char_linear_svc_pipeline(cfg: WordCharLinearSVCConfig) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    analyzer="word",
                    ngram_range=cfg.word_ngram_range,
                    sublinear_tf=cfg.sublinear_tf,
                    max_features=cfg.word_max_features,
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer=cfg.char_analyzer,
                    ngram_range=cfg.char_ngram_range,
                    sublinear_tf=cfg.sublinear_tf,
                    max_features=cfg.char_max_features,
                ),
            ),
        ]
    )
    clf = LinearSVC(
        C=cfg.C,
        class_weight=cfg.class_weight,
        dual=cfg.dual,
        random_state=42,
    )
    return Pipeline([("features", features), ("linearsvc", clf)])


def evaluate_split(model: Pipeline, x: Iterable[str], y: Iterable[str]) -> Mapping[str, float]:
    preds = model.predict(x)
    return {
        "accuracy": accuracy_score(y, preds),
        "macro_f1": f1_score(y, preds, average="macro"),
    }


def full_report(model: Pipeline, x: Iterable[str], y: Iterable[str]) -> str:
    preds = model.predict(x)
    return classification_report(y, preds, zero_division=0)


def classification_report_df(model: Pipeline, x: Iterable[str], y: Iterable[str]) -> pd.DataFrame:
    preds = model.predict(x)
    report = classification_report(y, preds, output_dict=True, zero_division=0)
    return pd.DataFrame(report).transpose().rename_axis("label").reset_index()


def get_confusion(model: Pipeline, x: Iterable[str], y: Iterable[str]) -> tuple[pd.DataFrame, list[str]]:
    preds = model.predict(x)
    labels = list(model.named_steps["linearsvc"].classes_)
    matrix = confusion_matrix(y, preds, labels=labels)
    return pd.DataFrame(matrix, index=labels, columns=labels), labels


def top_features(
    model: Pipeline, top_k: int = 10, negative: bool = False
) -> dict[str, list[tuple[str, float]]]:
    vectorizer = _get_feature_transformer(model)
    clf: LinearSVC = model.named_steps["linearsvc"]
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


def decision_function_df(model: Pipeline, x: Iterable[str], index=None) -> pd.DataFrame:
    clf: LinearSVC = model.named_steps["linearsvc"]
    scores = model.decision_function(x)
    classes = list(clf.classes_)

    if getattr(scores, "ndim", 1) == 1:
        return pd.DataFrame({classes[1]: scores}, index=index)

    return pd.DataFrame(scores, columns=classes, index=index)


def _get_feature_transformer(model: Pipeline):
    if "tfidf" in model.named_steps:
        return model.named_steps["tfidf"]
    if "features" in model.named_steps:
        return model.named_steps["features"]
    raise KeyError("Expected `tfidf` or `features` step in the pipeline.")


def _fit_and_collect_metrics(
    model: Pipeline,
    model_name: str,
    x_train: Iterable[str],
    y_train: Iterable[str],
    x_val: Iterable[str],
    y_val: Iterable[str],
    x_test: Iterable[str],
    y_test: Iterable[str],
) -> tuple[Pipeline, pd.DataFrame]:
    model.fit(x_train, y_train)

    metrics = pd.DataFrame(
        [
            {"model": model_name, "split": "train", **evaluate_split(model, x_train, y_train)},
            {"model": model_name, "split": "val", **evaluate_split(model, x_val, y_val)},
            {"model": model_name, "split": "test", **evaluate_split(model, x_test, y_test)},
        ]
    )
    return model, metrics


def run_linear_svc(
    x_train: Iterable[str],
    y_train: Iterable[str],
    x_val: Iterable[str],
    y_val: Iterable[str],
    x_test: Iterable[str],
    y_test: Iterable[str],
    cfg: LinearSVCConfig,
    model_name: str = "LinearSVC",
) -> tuple[Pipeline, pd.DataFrame]:
    model = build_linear_svc_pipeline(cfg)
    return _fit_and_collect_metrics(
        model=model,
        model_name=model_name,
        x_train=x_train,
        y_train=y_train,
        x_val=x_val,
        y_val=y_val,
        x_test=x_test,
        y_test=y_test,
    )


def run_word_char_linear_svc(
    x_train: Iterable[str],
    y_train: Iterable[str],
    x_val: Iterable[str],
    y_val: Iterable[str],
    x_test: Iterable[str],
    y_test: Iterable[str],
    cfg: WordCharLinearSVCConfig,
    model_name: str = "LinearSVC word+char",
) -> tuple[Pipeline, pd.DataFrame]:
    model = build_word_char_linear_svc_pipeline(cfg)
    return _fit_and_collect_metrics(
        model=model,
        model_name=model_name,
        x_train=x_train,
        y_train=y_train,
        x_val=x_val,
        y_val=y_val,
        x_test=x_test,
        y_test=y_test,
    )
