"""Construcción de grupos: ids estables, titular representativo, tendencia y exportación."""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta

import numpy as np

from .canarias import is_canary_group
from .headline import pick_headline
from .models import Article, iso
from .normalize import canonical_url, with_ref

MAX_PER_SOURCE = 3  # titulares como máximo por medio en un grupo


def new_group_id(articles: list[Article]) -> str:
    """Id inicial: hash del artículo más antiguo del grupo (id de artículo estable)."""
    oldest = min(articles, key=lambda a: (a.published, a.id))
    return "g" + hashlib.sha1(oldest.id.encode()).hexdigest()[:10]


def assign_ids(new: list[list[Article]], prev: list[dict], min_overlap: float = 0.5) -> list[str]:
    """Hereda el id del grupo previo con más artículos en común (coeficiente de solapamiento >= 0.5).

    Cada id previo se usa una sola vez (emparejamiento voraz por solapamiento descendente).
    Si dos grupos previos se fusionan, hereda el id el más antiguo.
    """
    prev_sets = [({a["id"] for a in g["articles"]}, g["id"], g["first_published"]) for g in prev]
    cands = []
    for ni, arts in enumerate(new):
        ids = {a.id for a in arts}
        for pi, (pset, pid, first) in enumerate(prev_sets):
            inter = len(ids & pset)
            if inter:
                ov = inter / min(len(ids), len(pset))
                if ov >= min_overlap:
                    cands.append((-ov, -inter, first, ni, pi))
    cands.sort()
    out: list[str | None] = [None] * len(new)
    used: set[int] = set()
    for _, _, _, ni, pi in cands:
        if out[ni] is None and pi not in used:
            out[ni] = prev_sets[pi][1]
            used.add(pi)
    return [o or new_group_id(new[i]) for i, o in enumerate(out)]


def trend(arts: list[Article], now: datetime, hours: int) -> dict:
    """Compara los artículos de las últimas `hours` horas con los de las `hours` previas."""
    recent = sum(1 for a in arts if a.published > now - timedelta(hours=hours))
    before = sum(1 for a in arts if now - timedelta(hours=2 * hours) < a.published <= now - timedelta(hours=hours))
    if recent > before:
        state = "sube"
    elif recent < before and before >= 2:
        state = "baja"
    else:
        state = "estable"
    return {"state": state, "recent": recent, "previous": before}


def editions_for(arts: list[Article]) -> list[str]:
    """Todos los grupos van en España; en Canarias solo los que hablan de Canarias (por contenido, no por medio)."""
    return ["espana"] + (["canarias"] if is_canary_group(arts) else [])


def make_group(gid: str, arts: list[Article], vectors: np.ndarray, now: datetime, trend_hours: int) -> dict:
    arts = sorted(arts, key=lambda a: a.published)
    h = pick_headline([a.title for a in arts], vectors)
    per_source: dict[str, int] = {}
    kept = []
    for i, a in enumerate(arts):
        if per_source.get(a.source, 0) < MAX_PER_SOURCE or i == h:
            per_source[a.source] = per_source.get(a.source, 0) + 1
            kept.append(a)
    sources = sorted({a.source for a in kept})
    image = next((a.image for a in [arts[h]] + arts if a.image), None)
    return {
        "id": gid,
        "headline": arts[h].title,
        "headline_source": arts[h].source,
        "image": image,
        "editions": editions_for(arts),
        "source_count": len(sources),
        "sources": sources,
        "article_count": len(kept),
        "first_published": iso(arts[0].published),
        "last_published": iso(arts[-1].published),
        "trend": trend(arts, now, trend_hours),
        "articles": [
            {**a.to_dict(), "url": with_ref(a.url)}  # todos los enlaces salen con ?ref=prisma
            for a in kept
        ],
    }


def articles_of(group: dict) -> list[Article]:
    out = []
    for d in group["articles"]:
        a = Article.from_dict(d)
        a.url = canonical_url(a.url)  # quita ?ref=prisma al releer el histórico
        out.append(a)
    return out


def refresh_editions(group: dict) -> dict:
    """Recalcula las ediciones de un grupo ya guardado (si cambia la regla, el histórico se corrige solo)."""
    group["editions"] = editions_for(articles_of(group))
    return group
