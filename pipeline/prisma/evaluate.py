"""Evaluación de la agrupación sobre pares etiquetados a mano (tests/fixtures/pairs.jsonl)."""
from __future__ import annotations

import json
from collections import Counter

import numpy as np

from . import cluster as cl
from . import rules


def load_pairs(path: str) -> list[dict]:
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def load_bin_weights(pairs: list[dict], bins_path: str | None) -> dict[int, float]:
    """Peso de cada par = pares disponibles en su tramo / pares etiquetados de ese tramo."""
    if not bins_path:
        return {p["bin"]: 1.0 for p in pairs}
    avail = [b[2] for b in json.load(open(bins_path, encoding="utf-8"))["bins"]]
    n = Counter(p["bin"] for p in pairs)
    return {b: avail[b] / n[b] for b in n}


def metrics(y_true: list[int], y_pred: list[int], w: list[float]) -> dict:
    tp = sum(wi for t, p, wi in zip(y_true, y_pred, w) if t and p)
    fp = sum(wi for t, p, wi in zip(y_true, y_pred, w) if not t and p)
    fn = sum(wi for t, p, wi in zip(y_true, y_pred, w) if t and not p)
    prec = tp / (tp + fp) if tp + fp else 1.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    return {"precision": prec, "recall": rec, "f1": f1}


class CachedEmbedder:
    """Memoiza los embeddings por texto (el barrido de umbrales los reutiliza)."""

    def __init__(self, inner):
        self.inner, self.cache = inner, {}

    def encode(self, texts):
        miss = [t for t in dict.fromkeys(texts) if t not in self.cache]
        if miss:
            for t, v in zip(miss, self.inner.encode(miss)):
                self.cache[t] = v
        return np.array([self.cache[t] for t in texts])


def predict(pairs: list[dict], embedder, threshold: float, rules_cfg: dict | None, mode: str,
            linkage_method: str = "average") -> list[int]:
    """mode='coseno': solo similitud; mode='cluster': el clustering real (con reglas si rules_cfg)."""
    keys = sorted({(s["source"], s["title"]) for p in pairs for s in (p["a"], p["b"])})
    pos = {k: i for i, k in enumerate(keys)}
    emb = embedder.encode([k[1] for k in keys])
    titles = [k[1] for k in keys]
    if mode == "coseno":
        out = []
        for p in pairs:
            i, j = pos[(p["a"]["source"], p["a"]["title"])], pos[(p["b"]["source"], p["b"]["title"])]
            out.append(int(float(emb[i] @ emb[j]) >= threshold))
        return out
    labels = cl.cluster_titles(emb, titles, threshold, rules_cfg, linkage_method)
    return [int(labels[pos[(p["a"]["source"], p["a"]["title"])]] == labels[pos[(p["b"]["source"], p["b"]["title"])]])
            for p in pairs]


def sweep(pairs, embedder, rules_cfg, bins_path=None, lo=0.60, hi=0.96, step=0.02, linkage_method="average"):
    embedder = embedder if isinstance(embedder, CachedEmbedder) else CachedEmbedder(embedder)
    weights = load_bin_weights(pairs, bins_path)
    w = [weights[p["bin"]] for p in pairs]
    y = [p["label"] for p in pairs]
    rows = []
    for t in np.arange(lo, hi + 1e-9, step):
        row = {"threshold": round(float(t), 2)}
        for name, mode, rc in (("coseno", "coseno", None), ("cluster", "cluster", None), ("cluster+reglas", "cluster", rules_cfg)):
            pred = predict(pairs, embedder, float(t), rc, mode, linkage_method)
            m = metrics(y, pred, w)
            mu = metrics(y, pred, [1.0] * len(y))
            row[name] = {**m, "precision_sin_ponderar": mu["precision"], "recall_sin_ponderar": mu["recall"]}
        rows.append(row)
    return rows


def recommend(rows: list[dict], key: str = "cluster+reglas", min_precision: float = 0.95) -> dict | None:
    """Umbral con mayor cobertura que mantenga la precisión ponderada >= min_precision."""
    ok = [r for r in rows if r[key]["precision"] >= min_precision]
    return max(ok, key=lambda r: (r[key]["recall"], -r["threshold"])) if ok else None
