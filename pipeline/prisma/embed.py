"""Embeddings multilingües locales (ONNX vía fastembed; sin PyTorch ni APIs de pago)."""
from __future__ import annotations

import numpy as np

DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def normalize_rows(m: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(m, axis=1, keepdims=True)
    return (m / np.clip(n, 1e-9, None)).astype(np.float32)


class Embedder:
    def __init__(self, model: str = DEFAULT_MODEL, cache_dir: str | None = None):
        from fastembed import TextEmbedding  # import perezoso: las pruebas no lo necesitan

        self.model_name = model
        self.model = TextEmbedding(model_name=model, cache_dir=cache_dir)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 384), dtype=np.float32)
        return normalize_rows(np.array(list(self.model.embed(texts, batch_size=64))))


def article_vectors(articles, embedder, title_weight: float = 0.7, summary_weight: float = 0.3) -> np.ndarray:
    """Vector por artículo: mezcla del embedding del titular y del de titular+resumen."""
    et = embedder.encode([a.title for a in articles])
    idx = [i for i, a in enumerate(articles) if a.summary]
    if not idx or summary_weight <= 0:
        return et
    es = embedder.encode([f"{articles[i].title}. {articles[i].summary}" for i in idx])
    vec = et.copy()
    vec[idx] = title_weight * et[idx] + summary_weight * es
    return normalize_rows(vec)
