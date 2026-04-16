from dataclasses import dataclass
from typing import Any, Iterable, Sequence

import pandas as pd
from sklearn.decomposition import LatentDirichletAllocation, TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer

DEFAULT_TOPIC_COUNTS = (5, 8)

DEFAULT_UA_STOP_WORDS = {
    "а",
    "або",
    "але",
    "аж",
    "без",
    "би",
    "був",
    "була",
    "були",
    "було",
    "бути",
    "в",
    "вам",
    "вас",
    "вже",
    "він",
    "вона",
    "вони",
    "воно",
    "все",
    "всі",
    "всю",
    "від",
    "де",
    "для",
    "до",
    "дуже",
    "ж",
    "за",
    "з",
    "зі",
    "й",
    "його",
    "її",
    "їм",
    "їх",
    "і",
    "із",
    "коли",
    "лише",
    "ми",
    "мене",
    "мені",
    "може",
    "можна",
    "моя",
    "моє",
    "мої",
    "на",
    "над",
    "нам",
    "нас",
    "наче",
    "наш",
    "наша",
    "наше",
    "наші",
    "не",
    "неї",
    "нема",
    "нею",
    "них",
    "ні",
    "ніби",
    "ніж",
    "об",
    "однак",
    "ось",
    "от",
    "перед",
    "після",
    "по",
    "поки",
    "при",
    "про",
    "сам",
    "сама",
    "саме",
    "самі",
    "свій",
    "свою",
    "себе",
    "собі",
    "та",
    "так",
    "також",
    "там",
    "те",
    "ти",
    "то",
    "того",
    "тоді",
    "той",
    "тому",
    "треба",
    "трохи",
    "тут",
    "у",
    "уже",
    "усе",
    "усі",
    "ця",
    "це",
    "цей",
    "цим",
    "цих",
    "чи",
    "чим",
    "що",
    "щоб",
    "як",
    "яка",
    "яке",
    "який",
    "які",
    "якщо",
}

DEFAULT_NOISE_STOP_WORDS = {
    "url",
    "email",
    "phone",
    "https",
    "http",
    "www",
}


@dataclass(slots=True)
class TopicModelRun:
    model_name: str
    topic_count: int
    vectorizer_name: str
    vectorizer: Any
    model: Any
    doc_term_matrix: Any
    doc_topic_matrix: Any
    feature_names: Any
    metrics: dict[str, Any]


def build_topic_stop_words(extra_stop_words: Iterable[str] | None = None) -> list[str]:
    stop_words = set(DEFAULT_UA_STOP_WORDS) | set(DEFAULT_NOISE_STOP_WORDS)
    if extra_stop_words is not None:
        stop_words.update(str(word).strip().lower() for word in extra_stop_words if str(word).strip())
    return sorted(stop_words)


def make_vectorizer_params(
    base_params: dict[str, Any] | None = None,
    stop_words: Sequence[str] | None = None,
) -> dict[str, Any]:
    params = {
        "analyzer": "word",
        "ngram_range": (1, 1),
        "min_df": 3,
        "max_df": 0.9,
        "lowercase": True,
        "token_pattern": r"(?u)\b[\w']+\b",
    }
    if base_params:
        params.update(base_params)
    if stop_words is not None:
        params["stop_words"] = list(stop_words)
    return params


def build_lsa_run(
    texts: Sequence[str],
    topic_count: int,
    vectorizer_params: dict[str, Any] | None = None,
    stop_words: Sequence[str] | None = None,
    random_state: int = 42,
    svd_params: dict[str, Any] | None = None,
) -> TopicModelRun:
    params = make_vectorizer_params(base_params=vectorizer_params, stop_words=stop_words)
    vectorizer = TfidfVectorizer(**params)
    doc_term_matrix = vectorizer.fit_transform(texts)

    model_params = {"n_components": topic_count, "random_state": random_state, "n_iter": 15}
    if svd_params:
        model_params.update(svd_params)
    model = TruncatedSVD(**model_params)
    doc_topic_matrix = model.fit_transform(doc_term_matrix)
    feature_names = vectorizer.get_feature_names_out()

    density = doc_term_matrix.nnz / (doc_term_matrix.shape[0] * doc_term_matrix.shape[1])
    metrics = {
        "model": "LSA",
        "k": int(topic_count),
        "vectorizer": "TfidfVectorizer",
        "documents": int(doc_term_matrix.shape[0]),
        "vocab_size": int(doc_term_matrix.shape[1]),
        "matrix_density": float(density),
        "explained_variance_ratio_sum": float(model.explained_variance_ratio_.sum()),
    }
    return TopicModelRun(
        model_name="LSA",
        topic_count=topic_count,
        vectorizer_name="TfidfVectorizer",
        vectorizer=vectorizer,
        model=model,
        doc_term_matrix=doc_term_matrix,
        doc_topic_matrix=doc_topic_matrix,
        feature_names=feature_names,
        metrics=metrics,
    )


def build_lda_run(
    texts: Sequence[str],
    topic_count: int,
    vectorizer_params: dict[str, Any] | None = None,
    stop_words: Sequence[str] | None = None,
    random_state: int = 42,
    lda_params: dict[str, Any] | None = None,
) -> TopicModelRun:
    params = make_vectorizer_params(base_params=vectorizer_params, stop_words=stop_words)
    vectorizer = CountVectorizer(**params)
    doc_term_matrix = vectorizer.fit_transform(texts)

    model_params = {
        "n_components": topic_count,
        "random_state": random_state,
        "learning_method": "batch",
        "max_iter": 10,
        "n_jobs": -1,
    }
    if lda_params:
        model_params.update(lda_params)
    model = LatentDirichletAllocation(**model_params)
    doc_topic_matrix = model.fit_transform(doc_term_matrix)
    feature_names = vectorizer.get_feature_names_out()

    density = doc_term_matrix.nnz / (doc_term_matrix.shape[0] * doc_term_matrix.shape[1])
    metrics = {
        "model": "LDA",
        "k": int(topic_count),
        "vectorizer": "CountVectorizer",
        "documents": int(doc_term_matrix.shape[0]),
        "vocab_size": int(doc_term_matrix.shape[1]),
        "matrix_density": float(density),
        "n_iter": int(model.n_iter_),
        "training_bound": float(model.bound_),
    }
    return TopicModelRun(
        model_name="LDA",
        topic_count=topic_count,
        vectorizer_name="CountVectorizer",
        vectorizer=vectorizer,
        model=model,
        doc_term_matrix=doc_term_matrix,
        doc_topic_matrix=doc_topic_matrix,
        feature_names=feature_names,
        metrics=metrics,
    )


def run_lsa_experiments(
    texts: Sequence[str],
    topic_counts: Sequence[int] = DEFAULT_TOPIC_COUNTS,
    vectorizer_params: dict[str, Any] | None = None,
    stop_words: Sequence[str] | None = None,
    random_state: int = 42,
    svd_params: dict[str, Any] | None = None,
) -> list[TopicModelRun]:
    return [
        build_lsa_run(
            texts=texts,
            topic_count=topic_count,
            vectorizer_params=vectorizer_params,
            stop_words=stop_words,
            random_state=random_state,
            svd_params=svd_params,
        )
        for topic_count in topic_counts
    ]


def run_lda_experiments(
    texts: Sequence[str],
    topic_counts: Sequence[int] = DEFAULT_TOPIC_COUNTS,
    vectorizer_params: dict[str, Any] | None = None,
    stop_words: Sequence[str] | None = None,
    random_state: int = 42,
    lda_params: dict[str, Any] | None = None,
) -> list[TopicModelRun]:
    return [
        build_lda_run(
            texts=texts,
            topic_count=topic_count,
            vectorizer_params=vectorizer_params,
            stop_words=stop_words,
            random_state=random_state,
            lda_params=lda_params,
        )
        for topic_count in topic_counts
    ]


def summarize_topic_runs(runs: Sequence[TopicModelRun]) -> pd.DataFrame:
    if not runs:
        return pd.DataFrame()
    return pd.DataFrame([run.metrics for run in runs]).sort_values(["model", "k"]).reset_index(drop=True)


def _normalize_preview_text(text: Any, max_chars: int = 240) -> str:
    normalized = " ".join(str(text).split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + "..."


def topic_words_table(run: TopicModelRun, top_n: int = 10) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    components = run.model.components_

    for topic_id, weights in enumerate(components):
        top_indices = weights.argsort()[::-1][:top_n]
        words = [run.feature_names[idx] for idx in top_indices]
        weight_values = [float(weights[idx]) for idx in top_indices]
        records.append(
            {
                "model": run.model_name,
                "k": int(run.topic_count),
                "topic_id": int(topic_id),
                "top_words": ", ".join(words),
                "top_word_weights": ", ".join(f"{value:.4f}" for value in weight_values),
            }
        )

    return pd.DataFrame(records)


def topic_words_long_table(run: TopicModelRun, top_n: int = 10) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    components = run.model.components_

    for topic_id, weights in enumerate(components):
        top_indices = weights.argsort()[::-1][:top_n]
        for rank, feature_idx in enumerate(top_indices, start=1):
            records.append(
                {
                    "model": run.model_name,
                    "k": int(run.topic_count),
                    "topic_id": int(topic_id),
                    "rank": int(rank),
                    "word": run.feature_names[feature_idx],
                    "weight": float(weights[feature_idx]),
                }
            )

    return pd.DataFrame(records)


def top_documents_table(
    run: TopicModelRun,
    corpus_df: pd.DataFrame,
    text_col: str = "text_clean",
    id_col: str = "text_id",
    top_n: int = 2,
    preview_chars: int = 240,
) -> pd.DataFrame:
    if len(corpus_df) != run.doc_topic_matrix.shape[0]:
        raise ValueError("Corpus size does not match the document-topic matrix.")

    scores = run.doc_topic_matrix
    records: list[dict[str, Any]] = []

    for topic_id in range(scores.shape[1]):
        topic_scores = scores[:, topic_id]
        ranked_indices = topic_scores.argsort()[::-1]

        if run.model_name == "LSA":
            positive_ranked = [idx for idx in ranked_indices if float(topic_scores[idx]) > 0]
            ranked_indices = positive_ranked or ranked_indices.tolist()
        else:
            ranked_indices = ranked_indices.tolist()

        for rank, doc_idx in enumerate(ranked_indices[:top_n], start=1):
            row = corpus_df.iloc[doc_idx]
            records.append(
                {
                    "model": run.model_name,
                    "k": int(run.topic_count),
                    "topic_id": int(topic_id),
                    "doc_rank": int(rank),
                    "topic_score": float(topic_scores[doc_idx]),
                    id_col: row[id_col] if id_col in row else doc_idx,
                    "text_preview": _normalize_preview_text(row[text_col], max_chars=preview_chars),
                }
            )

    return pd.DataFrame(records)
