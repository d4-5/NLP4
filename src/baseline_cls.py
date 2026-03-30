from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.pipeline import Pipeline

from src.classification_baseline import (
    BaselineConfig,
    attach_labels,
    build_pipeline,
    build_dominant_labels,
    evaluate_split,
    filter_by_ids,
    full_report,
    get_confusion,
    load_labels,
    load_processed,
    load_split_ids,
    top_features,
)


def run_logreg_baseline(
    x_train,
    y_train,
    x_val,
    y_val,
    x_test,
    y_test,
    cfg: BaselineConfig | None = None,
    model_name: str = "LogReg baseline",
) -> tuple[Pipeline, pd.DataFrame]:
    cfg = cfg or BaselineConfig(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)
    model = build_pipeline(cfg)
    model.fit(x_train, y_train)

    metrics = pd.DataFrame(
        [
            {"model": model_name, "split": "train", **evaluate_split(model, x_train, y_train)},
            {"model": model_name, "split": "val", **evaluate_split(model, x_val, y_val)},
            {"model": model_name, "split": "test", **evaluate_split(model, x_test, y_test)},
        ]
    )
    return model, metrics


def plot_confusion_matrix(cm_df: pd.DataFrame, title: str) -> None:
    plt.figure(figsize=(7, 6))
    plt.imshow(cm_df.values, cmap="Blues")
    plt.xticks(range(len(cm_df.columns)), cm_df.columns, rotation=45, ha="right")
    plt.yticks(range(len(cm_df.index)), cm_df.index)
    plt.title(title)
    plt.colorbar()

    for i in range(len(cm_df.index)):
        for j in range(len(cm_df.columns)):
            plt.text(j, i, str(cm_df.iloc[i, j]), ha="center", va="center", fontsize=8)

    plt.xlabel("Predicted")
    plt.ylabel("Gold")
    plt.tight_layout()
    plt.show()
