from __future__ import annotations

from typing import Iterable, Mapping, Sequence

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_recall_curve,
    precision_recall_fscore_support,
)


def build_pr_curve_df(
    y_true: Iterable[str], scores: Iterable[float], positive_label: str
) -> tuple[pd.DataFrame, float]:
    y_true_series = pd.Series(list(y_true)).reset_index(drop=True)
    score_series = pd.Series(list(scores)).reset_index(drop=True)
    y_true_binary = (y_true_series == positive_label).astype(int)

    precision, recall, thresholds = precision_recall_curve(y_true_binary, score_series)
    pr_df = pd.DataFrame(
        {
            "threshold": thresholds,
            "precision": precision[:-1],
            "recall": recall[:-1],
        }
    )
    avg_precision = float(average_precision_score(y_true_binary, score_series))
    return pr_df, avg_precision


def plot_pr_curve(
    y_true: Iterable[str],
    scores: Iterable[float],
    positive_label: str,
    title: str,
    threshold_points: Mapping[str, float] | None = None,
):
    pr_df, avg_precision = build_pr_curve_df(y_true, scores, positive_label)

    plt.figure(figsize=(7, 5))
    plt.plot(pr_df["recall"], pr_df["precision"], linewidth=2)
    plt.xlabel("Recall")
    plt.ylabel("Precision")
    plt.title(f"{title} | AP={avg_precision:.3f}")
    plt.xlim(0, 1.02)
    plt.ylim(0, 1.02)
    plt.grid(alpha=0.25)

    if threshold_points:
        for label, threshold in threshold_points.items():
            nearest_idx = (pr_df["threshold"] - threshold).abs().idxmin()
            point = pr_df.loc[nearest_idx]
            plt.scatter(point["recall"], point["precision"], s=60, label=f"{label}: {threshold:.3f}")

        plt.legend()

    plt.tight_layout()
    plt.show()
    return pr_df, avg_precision


def apply_ovr_threshold(
    scores_df: pd.DataFrame, target_label: str, threshold: float
) -> pd.Series:
    if target_label not in scores_df.columns:
        raise KeyError(f"Target label `{target_label}` is not present in score columns.")

    scores_df = scores_df.reset_index(drop=True)
    base_pred = scores_df.idxmax(axis=1)
    preds = base_pred.copy()

    target_scores = scores_df[target_label]
    non_target_scores = scores_df.drop(columns=[target_label])
    fallback_pred = non_target_scores.idxmax(axis=1)

    force_target = target_scores >= threshold
    demote_target = (~force_target) & (base_pred == target_label)

    preds[force_target] = target_label
    preds[demote_target] = fallback_pred[demote_target]
    return preds


def evaluate_thresholds(
    y_true: Iterable[str],
    scores_df: pd.DataFrame,
    target_label: str,
    thresholds: Mapping[str, float] | Sequence[float],
) -> pd.DataFrame:
    y_true_series = pd.Series(list(y_true)).reset_index(drop=True)
    rows = [
        _threshold_metrics(
            y_true=y_true_series,
            preds=scores_df.idxmax(axis=1),
            target_label=target_label,
            threshold_label="default_argmax",
            threshold_value=None,
        )
    ]

    if isinstance(thresholds, Mapping):
        iterator = thresholds.items()
    else:
        iterator = [(f"threshold_{idx + 1}", threshold) for idx, threshold in enumerate(thresholds)]

    for label, threshold in iterator:
        preds = apply_ovr_threshold(scores_df=scores_df, target_label=target_label, threshold=threshold)
        rows.append(
            _threshold_metrics(
                y_true=y_true_series,
                preds=preds,
                target_label=target_label,
                threshold_label=label,
                threshold_value=float(threshold),
            )
        )

    return pd.DataFrame(rows)


def _threshold_metrics(
    y_true: pd.Series,
    preds: pd.Series,
    target_label: str,
    threshold_label: str,
    threshold_value: float | None,
) -> dict[str, float | int | str | None]:
    y_true = pd.Series(list(y_true)).reset_index(drop=True)
    preds = pd.Series(list(preds)).reset_index(drop=True)

    y_true_binary = (y_true == target_label).astype(int)
    pred_binary = (preds == target_label).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true_binary,
        pred_binary,
        average="binary",
        zero_division=0,
    )
    support = int(y_true_binary.sum())

    tp = int(((y_true_binary == 1) & (pred_binary == 1)).sum())
    fp = int(((y_true_binary == 0) & (pred_binary == 1)).sum())
    fn = int(((y_true_binary == 1) & (pred_binary == 0)).sum())

    return {
        "setting": threshold_label,
        "threshold": threshold_value,
        "target_label": target_label,
        "accuracy": accuracy_score(y_true, preds),
        "macro_f1": f1_score(y_true, preds, average="macro"),
        "target_precision": precision,
        "target_recall": recall,
        "target_f1": f1,
        "target_support": support,
        "predicted_target": int(pred_binary.sum()),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }
