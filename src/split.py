from __future__ import annotations

import random
from collections import defaultdict
from pathlib import Path
from typing import Iterable, List, Mapping, MutableMapping, Sequence


def _to_rows(df) -> List[Mapping[str, object]]:
    if isinstance(df, list):
        return df
    if hasattr(df, "to_dict"):
        return df.to_dict(orient="records")
    raise TypeError("df must be a list of dicts or a pandas DataFrame-like object")


def _split_counts(n: int, ratios: Sequence[float]) -> tuple[int, int, int]:
    train_r, val_r, test_r = ratios
    n_val = int(round(n * val_r))
    n_test = int(round(n * test_r))
    n_val = max(0, n_val)
    n_test = max(0, n_test)

    if n >= 3:
        n_val = max(1, n_val)
        n_test = max(1, n_test)

    if n_val + n_test >= n:
        overflow = (n_val + n_test) - (n - 1)
        while overflow > 0 and (n_val > 1 or n_test > 1):
            if n_val >= n_test and n_val > 1:
                n_val -= 1
            elif n_test > 1:
                n_test -= 1
            overflow -= 1

    n_train = n - n_val - n_test
    if n_train == 0 and n > 0:
        n_train = 1
        if n_val > n_test and n_val > 0:
            n_val -= 1
        elif n_test > 0:
            n_test -= 1

    while n_train + n_val + n_test > n and n_train > 0:
        n_train -= 1
    while n_train + n_val + n_test < n:
        n_train += 1

    return n_train, n_val, n_test


def make_splits(
    df,
    seed: int,
    id_col: str = "text_id",
    stratify_col: str | None = None,
    ratios: Sequence[float] = (0.8, 0.1, 0.1),
) -> dict[str, list[str]]:
    rows = _to_rows(df)
    rng = random.Random(seed)

    if not stratify_col:
        raise ValueError("stratify_col is required for stratified split")
    by_label: MutableMapping[str, list[str]] = defaultdict(list)
    for row in rows:
        label = str(row.get(stratify_col, ""))
        by_label[label].append(str(row[id_col]))

    splits = {"train": [], "val": [], "test": []}
    for label in sorted(by_label.keys()):
        ids = by_label[label]
        rng.shuffle(ids)
        n_train, n_val, _ = _split_counts(len(ids), ratios)
        splits["train"].extend(ids[:n_train])
        splits["val"].extend(ids[n_train : n_train + n_val])
        splits["test"].extend(ids[n_train + n_val :])

    for key in splits:
        rng.shuffle(splits[key])
    return splits


def save_splits(splits: Mapping[str, Iterable[str]], out_dir: str | Path) -> None:
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    for split_name in ("train", "val", "test"):
        ids = splits.get(split_name, [])
        target = out_path / f"splits_{split_name}_ids.txt"
        with target.open("w", encoding="utf-8") as f:
            for item_id in ids:
                f.write(f"{item_id}\n")
