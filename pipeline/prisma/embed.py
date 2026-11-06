"""Embeddings multilingües locales (ONNX vía fastembed; sin PyTorch ni APIs de pago)."""
from __future__ import annotations

import hashlib
from pathlib import Path

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


class VectorCache:
    """Caché de vectores por artículo (npz con float16). La clave incluye modelo, pesos y texto,
    así que si cambia cualquiera de ellos el vector se recalcula solo."""

    def __init__(self, path: str | None = None):
        self.path = Path(path) if path else None
        self.vectors: dict[str, np.ndarray] = {}
        if self.path and self.path.exists():
            try:
                z = np.load(self.path, allow_pickle=False)
                self.vectors = dict(zip(z["keys"].tolist(), z["vecs"].astype(np.float32)))
            except Exception:  # caché ilegible: se descarta, no pasa nada
                self.vectors = {}

    def save(self, keep: set[str]) -> None:
        if not self.path:
            return
        keys = [k for k in self.vectors if k in keep]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        vecs = np.array([self.vectors[k] for k in keys], dtype=np.float16) if keys else np.zeros((0, 384), np.float16)
        np.savez_compressed(self.path, keys=np.array(keys), vecs=vecs)


def vector_key(a, model: str, tw: float, sw: float) -> str:
    raw = f"{model}|{tw}|{sw}|{a.title}|{a.summary or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def article_vectors(articles, embedder, title_weight: float = 0.7, summary_weight: float = 0.3,
                    cache: VectorCache | None = None, model: str = "") -> tuple[np.ndarray, dict]:
    """Vector por artículo: mezcla del embedding del titular y del de titular+resumen.

    Con `cache`, solo se calculan los artículos que no estén ya. Devuelve (matriz, estadísticas).
    """
    if not articles:
        return np.zeros((0, 384), dtype=np.float32), {"new": 0, "cached": 0}
    keys = [vector_key(a, model, title_weight, summary_weight) for a in articles]
    cache = cache or VectorCache()
    todo = [i for i, k in enumerate(keys) if k not in cache.vectors]
    if todo:
        sub = [articles[i] for i in todo]
        et = embedder.encode([a.title for a in sub])
        idx = [j for j, a in enumerate(sub) if a.summary]
        vec = et.copy()
        if idx and summary_weight > 0:
            es = embedder.encode([f"{sub[j].title}. {sub[j].summary}" for j in idx])
            vec[idx] = title_weight * et[idx] + summary_weight * es
        vec = normalize_rows(vec)
        for i, v in zip(todo, vec):
            cache.vectors[keys[i]] = v
    out = np.array([cache.vectors[k] for k in keys], dtype=np.float32)
    cache.save(set(keys))
    return out, {"new": len(todo), "cached": len(articles) - len(todo)}
