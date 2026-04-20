import pandas as pd
import re
from gensim.models import Word2Vec, FastText
import os


def tokenize(text):
    if not isinstance(text, str):
        return []
    text = text.lower()
    tokens = re.findall(r"\w+", text)
    return tokens


def train_embeddings(data_path, model_dir="models"):
    print(f"Loading data from {data_path}...")
    df = pd.read_csv(data_path)

    df = df[df["text_clean"].notna()]
    df["tokens"] = df["text_clean"].apply(tokenize)
    df = df[df["tokens"].map(len) > 2]

    sentences = df["tokens"].tolist()
    total_tokens = sum(len(s) for s in sentences)
    print(f"Corpus size: {len(sentences)} documents, {total_tokens} tokens.")

    if not os.path.exists(model_dir):
        os.makedirs(model_dir)

    params = {
        "vector_size": 100,
        "window": 5,
        "min_count": 3,
        "sg": 1,
        "workers": 4,
        "seed": 42,
    }

    w2v_model = Word2Vec(sentences, **params)
    w2v_model.save(os.path.join(model_dir, "word2vec.model"))

    ft_model = FastText(sentences, **params)
    ft_model.save(os.path.join(model_dir, "fasttext.model"))

    return len(sentences), total_tokens


if __name__ == "__main__":
    train_embeddings("data/processed_v2.csv")
