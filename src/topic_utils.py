import re
from collections import Counter

import pandas as pd

TOKEN_PATTERN = re.compile(r"[0-9A-Za-zА-Яа-яІіЇїЄєҐґ']+")


def count_tokens(text: str) -> int:
    if not isinstance(text, str):
        return 0
    return len(TOKEN_PATTERN.findall(text.lower()))


def prepare_corpus_frame(df: pd.DataFrame, text_col: str = "text_clean") -> pd.DataFrame:
    if text_col not in df.columns:
        raise ValueError(f"Column '{text_col}' was not found in the corpus frame.")

    prepared = df.copy()
    prepared[text_col] = prepared[text_col].fillna("").astype(str).str.strip()
    prepared["char_len"] = prepared[text_col].str.len()
    prepared["token_len"] = prepared[text_col].map(count_tokens)
    return prepared


def filter_corpus(
    df: pd.DataFrame,
    text_col: str = "text_clean",
    min_tokens: int = 5,
    min_chars: int = 20,
) -> tuple[pd.DataFrame, dict]:
    prepared = prepare_corpus_frame(df=df, text_col=text_col)

    empty_mask = prepared[text_col].eq("")
    short_mask = (prepared["token_len"] < min_tokens) | (prepared["char_len"] < min_chars)
    keep_mask = ~(empty_mask | short_mask)

    filtered = prepared.loc[keep_mask].copy()
    stats = {
        "documents_before": int(len(prepared)),
        "documents_after": int(len(filtered)),
        "dropped_total": int((~keep_mask).sum()),
        "dropped_empty": int(empty_mask.sum()),
        "dropped_short": int((~empty_mask & short_mask).sum()),
        "min_tokens": int(min_tokens),
        "min_chars": int(min_chars),
    }
    return filtered, stats


def collect_short_examples(
    df: pd.DataFrame,
    text_col: str = "text_clean",
    limit: int = 10,
) -> pd.DataFrame:
    prepared = prepare_corpus_frame(df=df, text_col=text_col)
    sort_cols = ["token_len", "char_len", text_col]
    view_cols = [col for col in ["text_id", text_col, "token_len", "char_len"] if col in prepared.columns]
    return prepared.loc[:, view_cols].sort_values(sort_cols).head(limit).reset_index(drop=True)


def top_token_counts(
    df: pd.DataFrame,
    text_col: str = "text_clean",
    top_n: int = 30,
) -> pd.DataFrame:
    prepared = prepare_corpus_frame(df=df, text_col=text_col)
    counter = Counter()

    for text in prepared[text_col]:
        counter.update(token.lower() for token in TOKEN_PATTERN.findall(text))

    top_items = counter.most_common(top_n)
    return pd.DataFrame(top_items, columns=["token", "count"])
