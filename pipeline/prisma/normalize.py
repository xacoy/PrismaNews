"""Normalización de texto y URLs, y eliminación de duplicados."""
from __future__ import annotations

import hashlib
import html
import re
import unicodedata
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .models import Article

SUMMARY_MAX = 280
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_TRACKING = re.compile(r"^(utm_.*|fbclid|gclid|mc_.*|ref|ito|ns_.*|at_.*|outputtype|s_kw|xtor|cmpid)$", re.I)


def clean_text(s: str | None) -> str:
    """Quita HTML, entidades y espacios repetidos."""
    if not s:
        return ""
    s = html.unescape(_TAG.sub(" ", s))
    s = unicodedata.normalize("NFC", s).replace("\xa0", " ")
    return _WS.sub(" ", s).strip()


def clean_summary(s: str | None, limit: int = SUMMARY_MAX) -> str | None:
    s = clean_text(s)
    if not s:
        return None
    if len(s) <= limit:
        return s
    cut = s[:limit].rsplit(" ", 1)[0].rstrip(" ,;:.-")
    return cut + "…"


def clean_title(title: str | None, source: str = "") -> str:
    """Limpia el titular y quita sufijos tipo ' - El País' o ' | ABC'."""
    t = clean_text(title)
    if source:
        t = re.sub(rf"\s*[|\-–—:]\s*{re.escape(source)}\s*$", "", t, flags=re.I)
    return t


def canonical_url(url: str) -> str:
    """Esquema y host en minúsculas, sin fragmento ni parámetros de seguimiento."""
    p = urlsplit(url.strip())
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not _TRACKING.match(k)]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, urlencode(query), ""))


def with_ref(url: str, ref: str = "prisma") -> str:
    """Añade ?ref=prisma (o &ref=prisma) al enlace de salida."""
    p = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != "ref"]
    query.append(("ref", ref))
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(query), p.fragment))


def article_id(url: str) -> str:
    return hashlib.sha1(canonical_url(url).encode("utf-8")).hexdigest()[:16]


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def title_key(title: str) -> str:
    """Clave para detectar titulares repetidos: minúsculas, sin acentos ni puntuación."""
    t = strip_accents(title.lower())
    t = re.sub(r"[^a-z0-9ñ ]+", " ", t)
    return _WS.sub(" ", t).strip()


def dedupe(articles: list[Article]) -> list[Article]:
    """Elimina duplicados exactos (misma URL) y repeticiones del mismo medio (mismo titular).

    Se queda con la primera publicación de cada uno.
    """
    seen_ids: set[str] = set()
    seen_titles: set[tuple[str, str]] = set()
    out = []
    for a in sorted(articles, key=lambda x: x.published):
        k = (a.source, title_key(a.title))
        if a.id in seen_ids or k in seen_titles:
            continue
        seen_ids.add(a.id)
        seen_titles.add(k)
        out.append(a)
    return out
