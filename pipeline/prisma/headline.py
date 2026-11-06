"""Titular representativo de un grupo: el menos dramático y, a igualdad, el más central.

Regla (documentada también en la página "Cómo funciona"):
1. Cada titular recibe una puntuación de dramatismo (más alta = más llamativo).
2. Se descartan los que tengan más puntuación que el mínimo del grupo.
3. Entre los que quedan, se elige el más cercano al centro semántico del grupo.
"""
from __future__ import annotations

import re

import numpy as np

_CLICKBAIT = re.compile(
    r"(última hora|ultima hora|increíble|increible|alucinante|bomba|escándalo|escandalo|brutal|terrible|"
    r"dramático|dramatico|urgente|impactante|no te lo vas a creer|lo que nadie|esto es lo que|"
    r"así es|asi es|las claves|todo lo que|por qué|por que|zasca|machaca|arrasa|destroza|estalla|revienta)",
    re.I,
)
_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def sensationalism(title: str) -> int:
    s = 0
    letters = [c for c in title if c.isalpha()]
    if letters and sum(c.isupper() for c in letters) / len(letters) > 0.3:
        s += 2
    s += 2 * title.count("!")
    s += 1 if "?" in title or "¿" in title else 0
    s += 1 if title[:1] in "\"“«'" else 0
    s += 1 if any(q in title for q in "“”«»") else 0
    s += 2 * len(_CLICKBAIT.findall(title))
    s += 2 if _EMOJI.search(title) else 0
    s += 1 if "…" in title or "..." in title else 0
    s += 1 if len(title) < 30 or len(title) > 140 else 0
    return s


def pick_headline(titles: list[str], vectors: np.ndarray) -> int:
    """Índice del titular representativo."""
    scores = [sensationalism(t) for t in titles]
    best = min(scores)
    cand = [i for i, s in enumerate(scores) if s == best]
    if len(cand) == 1:
        return cand[0]
    centroid = vectors.mean(axis=0)
    centroid /= max(np.linalg.norm(centroid), 1e-9)
    return max(cand, key=lambda i: float(vectors[i] @ centroid))
