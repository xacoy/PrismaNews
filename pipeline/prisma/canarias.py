"""¿Es una noticia de Canarias? Se decide por el contenido (titulares y resúmenes), no por el medio.

Un medio canario también cubre noticias nacionales; esas no son «noticias de Canarias».
Un grupo pertenece a la edición Canarias si algún titular o resumen menciona un topónimo, una
institución, un equipo o un asunto típicamente canario. Es una lista de reglas sencilla y revisable:
cualquiera puede añadir un término en TERMS.
"""
from __future__ import annotations

import re

from .normalize import strip_accents

# Términos que se buscan ya sin acentos y en minúsculas (con límites de palabra).
TERMS = [
    # archipiélago e islas
    "canarias", "canario", "canaria", "canarios", "canarias", "islas canarias", "archipielago canario",
    "tenerife", "gran canaria", "lanzarote", "fuerteventura", "la gomera", "el hierro", "la graciosa",
    "la palma",  # ver EXCLUDE: La Palma del Condado (Huelva)
    "archipielago", "cumbre vieja", "teide", "timanfaya",
    # ciudades y municipios
    "las palmas de gran canaria", "las palmas", "santa cruz de tenerife", "la laguna", "san cristobal de la laguna",
    "telde", "arucas", "galdar", "agaete", "agüimes", "aguimes", "ingenio", "santa lucia de tirajana",
    "san bartolome de tirajana", "maspalomas", "playa del ingles", "mogan", "puerto rico de gran canaria",
    "arrecife", "teguise", "yaiza", "tias", "costa teguise", "puerto del carmen", "playa blanca",
    "puerto del rosario", "corralejo", "la oliva", "morro jable", "pajara", "tuineje", "betancuria",
    "arona", "adeje", "los cristianos", "las americas", "costa adeje", "granadilla de abona", "candelaria",
    "puerto de la cruz", "la orotava", "los realejos", "icod de los vinos", "garachico", "guimar", "tacoronte",
    "el sauzal", "la matanza", "santa ursula", "los llanos de aridane", "santa cruz de la palma", "tazacorte",
    "san sebastian de la gomera", "valverde", "vallehermoso",
    # instituciones y política
    "cabildo", "cabildos", "gobierno de canarias", "parlamento de canarias", "fernando clavijo", "coalicion canaria",
    "nueva canarias", "audiencia de las palmas", "universidad de la laguna", "ull", "ulpgc", "diputado del comun",
    "consejeria de", "elecciones canarias",
    # deporte
    "ud las palmas", "cd tenerife", "heliodoro", "gran canaria arena", "gran canaria", "granca", "dreamland",
    # asuntos típicos
    "cayuco", "cayucos", "el hierro",
    "loro parque", "siam park", "carnaval de santa cruz", "carnaval de las palmas",
]
# Falsos amigos conocidos (se descartan aunque aparezca el término)
EXCLUDE = [
    r"la palma del condado",
    r"palma de mallorca",
    r"palma del rio",
    r"santa cruz de mudela",
    r"santa cruz de la sierra",
    r"santa cruz de bezana",
    r"hierro y acero",
]
# Términos ambiguos que solo cuentan escritos con mayúscula (nombre propio)
CASE_SENSITIVE = {"El Hierro": r"\bEl Hierro\b", "Arona": r"\bArona\b"}

_AMBIGUOUS = {"el hierro", "candelaria", "arona", "ingenio", "tias", "valverde", "vallehermoso", "ull", "consejeria de", "archipielago",
              "la oliva", "las americas", "playa blanca", "guimar", "granca"}

_RE_TERMS = re.compile(
    r"\b(" + "|".join(re.escape(t) for t in sorted({t for t in TERMS if t not in _AMBIGUOUS}, key=len, reverse=True)) + r")\b"
)
_RE_EXCLUDE = re.compile("|".join(EXCLUDE))
_RE_CS = [re.compile(p) for p in CASE_SENSITIVE.values()]


def canary_hits(text: str) -> list[str]:
    """Términos canarios encontrados en un texto (vacío si no hay o son falsos amigos)."""
    if not text:
        return []
    folded = strip_accents(text.lower())
    folded = _RE_EXCLUDE.sub(" ", folded)
    hits = _RE_TERMS.findall(folded)
    for name, rx in zip(CASE_SENSITIVE, _RE_CS):
        if rx.search(text) and not _RE_EXCLUDE.search(strip_accents(text.lower())):
            hits.append(name.lower())
    return hits


def is_canary_group(articles) -> bool:
    """True si algún titular o resumen del grupo habla de Canarias."""
    for a in articles:
        title = a.title if hasattr(a, "title") else a["title"]
        summary = (a.summary if hasattr(a, "summary") else a.get("summary")) or ""
        if canary_hits(title) or canary_hits(summary):
            return True
    return False
