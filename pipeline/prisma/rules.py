"""Reglas contra falsos positivos: entidades, cifras/fechas y titulares de directos o crónicas."""
from __future__ import annotations

import re

from .normalize import strip_accents

# Palabras que suelen ir en mayúscula sin ser entidades (inicio de cita, días, etc.)
_NOT_ENTITY = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo", "al", "del", "de", "en", "con", "por", "para",
    "sin", "sobre", "tras", "ante", "entre", "hasta", "desde", "que", "como", "cuando", "donde", "y", "o", "e", "a",
    "lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre",
    "diciembre", "hoy", "ayer", "espana", "gobierno", "ultima", "hora", "directo", "video", "fotos", "opinion",
}
_TOKEN = re.compile(r"[\wÁÉÍÓÚÜÑáéíóúüñ'’\-\.]+", re.UNICODE)
_NUM = re.compile(r"\d[\d\.,]*")
_LIVE = re.compile(
    r"\b(en directo|última hora|ultima hora|minuto a minuto|en vivo|directo[: ]|crónica|cronica|"
    r"resumen del día|resumen de la jornada|las noticias de hoy|noticias de hoy|titulares de hoy|"
    r"claves del día|lo que hay que saber hoy|boletín|buenos días|buenas noches|newsletter|"
    r"lotería|loteria|horóscopo|horoscopo|quiniela|bonoloto|primitiva|once de hoy|cupón|cupon|"
    r"el tiempo en|previsión del tiempo|prevision del tiempo)\b",
    re.I,
)


def _strip(tok: str) -> str:
    return tok.strip(".'’-")


def entities(title: str) -> set[str]:
    """Entidades aproximadas: palabras en mayúscula que no abren frase, y siglas.

    Heurística sin modelos: en titulares en español solo se capitaliza la primera palabra y los
    nombres propios, así que el resto de mayúsculas son casi siempre personas, lugares u organizaciones.
    """
    out = set()
    after_break = True  # la primera palabra y la que sigue a ':' o '¿' abren frase
    for raw in re.split(r"(\s+)", title):
        if raw.isspace() or not raw:
            continue
        tok = _strip("".join(_TOKEN.findall(raw)))
        if tok:
            low = strip_accents(tok.lower())
            is_acr = tok.isupper() and len(tok) >= 2 and not tok.isdigit()
            is_cap = tok[0].isupper() and not tok.isupper()
            if (is_acr or (is_cap and not after_break)) and low not in _NOT_ENTITY and len(low) >= 3:
                out.add(low)
        after_break = raw.endswith((":", "?", "¿", ".", "«", '"', "“")) or raw.startswith(("¿", "«", '"', "“"))
    return out


def entities_overlap(a: set[str], b: set[str]) -> bool:
    """Coinciden si comparten una entidad exacta o un prefijo de 5 letras (singular/plural, género)."""
    for x in a:
        for y in b:
            if x == y or (len(x) >= 5 and len(y) >= 5 and x[:5] == y[:5]):
                return True
    return False


def shared_entities(a: set[str], b: set[str]) -> int:
    """Cuántas entidades de `a` aparecen también en `b` (exactas o con el mismo prefijo de 5 letras)."""
    return sum(1 for x in a if any(x == y or (len(x) >= 5 and len(y) >= 5 and x[:5] == y[:5]) for y in b))


def numbers(title: str) -> set[str]:
    out = set()
    for m in _NUM.findall(title):
        n = re.sub(r"[\.,]+$", "", m)
        out.add(re.sub(r"[\.,]", "", n))
    return out


def is_live(title: str) -> bool:
    return bool(_LIVE.search(title))


def veto(title_a: str, title_b: str, sim: float, cfg: dict) -> str | None:
    """Devuelve el motivo por el que dos titulares NO deben agruparse, o None."""
    if cfg.get("short_title_words") and sim < 0.95 and min(len(title_a.split()), len(title_b.split())) < cfg["short_title_words"]:
        return "titular_corto"
    ea, eb = entities(title_a), entities(title_b)
    if ea and eb and sim < cfg.get("entity_veto_below", 0.0) and not entities_overlap(ea, eb):
        return "entidades"
    na, nb = numbers(title_a), numbers(title_b)
    if na and nb and sim < cfg.get("number_veto_below", 0.0) and not (na <= nb or nb <= na):
        return "cifras"
    return None
