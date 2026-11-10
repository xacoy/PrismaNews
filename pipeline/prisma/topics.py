"""Temas: deportes (se excluyen), Tecnología (incluye videojuegos) y Finanzas.

Igual que `canarias.py`, se decide por el contenido con listas de términos sencillas y revisables:
- Un artículo «encaja» si su titular, su URL o (con dos términos distintos) su resumen encajan.
- Un grupo es de un tema si al menos la mitad de sus artículos encajan.
- Los deportes no se publican: se descartan los artículos antes de agrupar.

Los términos se buscan sin acentos, en minúsculas y con límites de palabra. Si falta o sobra alguno,
se edita aquí y se ejecutan las pruebas.
"""
from __future__ import annotations

import re

from .normalize import strip_accents

TECH = "tecnologia"
FINANCE = "finanzas"

SPORT_TERMS = [
    "deporte", "deportes", "deportista", "deportistas", "futbol", "futbolista", "futbolistas", "laliga",
    "liga de campeones", "champions league", "europa league", "copa del rey", "supercopa", "primera division",
    "segunda division", "premier league", "serie a", "bundesliga", "mundial de futbol", "eurocopa", "seleccion espanola",
    "real madrid", "fc barcelona", "barca", "atletico de madrid", "athletic club", "real sociedad", "betis", "sevilla fc",
    "villarreal", "valencia cf", "celta de vigo", "ud las palmas", "cd tenerife", "el clasico", "fichaje", "fichajes",
    "gol", "goles", "portero", "delantero", "centrocampista", "entrenador", "arbitro", "var", "balon de oro",
    "baloncesto", "acb", "nba", "euroliga", "balonmano", "voleibol", "rugby", "tenis", "tenista", "atp", "wta",
    "roland garros", "wimbledon", "us open", "open de australia", "rafa nadal", "alcaraz", "formula 1", "f1",
    "gran premio", "motogp", "moto gp", "rally", "ciclismo", "ciclista", "tour de francia", "vuelta a espana",
    "giro de italia", "atletismo", "natacion", "juegos olimpicos", "olimpicos", "paralimpicos", "boxeo", "ufc",
    "golf", "padel", "surf", "liga endesa", "copa davis",
]
# Segmentos de URL propios de secciones de deportes
SPORT_PATH = re.compile(r"/(deportes?|futbol|baloncesto|tenis|motor|motociclismo|ciclismo|sports?|soccer)/")

TECH_TERMS = [
    "tecnologia", "tecnologico", "tecnologica", "tecnologicas", "inteligencia artificial", "chatgpt", "openai", "anthropic",
    "gemini", "copilot", "llm", "algoritmo", "robot", "robots", "robotica", "chip", "chips", "semiconductores",
    "nvidia", "intel", "amd", "apple", "iphone", "ipad", "macbook", "android", "google", "microsoft", "windows",
    "samsung", "xiaomi", "huawei", "amazon web services", "meta ai", "tiktok", "instagram", "whatsapp", "telegram",
    "youtube", "netflix", "spotify", "starlink", "spacex", "software", "aplicacion movil", "app", "apps", "smartphone",
    "smartphones", "movil", "moviles", "ordenador", "portatil", "tablet", "wearable", "realidad virtual",
    "realidad aumentada", "internet", "wifi", "5g", "6g", "fibra optica", "ciberseguridad", "ciberataque",
    "ciberataques", "hacker", "hackers", "hackeo", "ransomware", "malware", "phishing", "brecha de datos", "startup",
    "startups", "big tech", "computacion cuantica", "ordenador cuantico", "centro de datos", "centros de datos",
    "redes sociales", "streaming", "dron", "drones", "coche electrico", "bateria", "gadget",
    # videojuegos
    "videojuego", "videojuegos", "consola", "consolas", "playstation", "ps5", "xbox", "nintendo", "switch 2", "steam",
    "valve", "epic games", "fortnite", "minecraft", "pokemon", "zelda", "mario", "call of duty", "grand theft auto",
    "gta", "gamer", "gamers", "gaming", "esports", "e-sports", "twitch", "ubisoft", "electronic arts", "activision",
    "blizzard", "riot games", "league of legends", "mando", "lanzamiento del juego",
]
# Términos ambiguos o cortos: solo cuentan con mayúscula (siglas o nombres propios)
_TECH_CASE_STRICT = re.compile(r"\b(IA|AI|TIC|CES|MWC|GPU|CPU|iOS|PS4)\b")
TECH_PATH = re.compile(r"/(tecnologia|tecnologias|tech|videojuegos|juegos|gaming|ciberseguridad|ciencia-y-tecnologia)/")

FINANCE_TERMS = [
    "finanzas", "financiero", "financiera", "financieros", "financieras", "bolsa", "bolsas", "ibex", "ibex 35",
    "dow jones", "nasdaq", "s&p 500", "wall street", "cotiza", "cotizacion", "cotizaciones", "cotizada", "cotizadas",
    "euribor", "hipoteca", "hipotecas", "tipos de interes", "banco central europeo", "reserva federal", "banco de espana",
    "banco de inglaterra", "inflacion", "deflacion", "prima de riesgo", "deuda publica", "bono", "bonos", "bono espanol",
    "bitcoin", "ethereum", "criptomoneda", "criptomonedas", "cripto", "criptoactivos", "stablecoin", "blockchain",
    "santander", "bbva", "caixabank", "sabadell", "bankinter", "unicaja", "abanca", "ibercaja", "kutxabank", "bankia",
    "banco", "bancos", "banca", "entidades financieras", "dividendo", "dividendos", "accionista", "accionistas",
    "inversor", "inversores", "inversion", "fondo de inversion", "fondos de inversion", "fondo de pensiones",
    "fondos de pensiones", "plan de pensiones", "planes de pensiones", "capitalizacion", "ebitda", "resultados trimestrales",
    "beneficio neto", "beneficios", "cnmv", "opa", "fusion", "adquisicion", "salida a bolsa", "ipo", "divisa", "divisas",
    "euro dolar", "tipo de cambio", "petroleo", "brent", "barril", "oro", "materias primas", "mercados financieros",
    "mercados", "ahorro", "ahorradores", "cuenta remunerada", "deposito", "depositos", "prestamo", "prestamos",
    "credito", "creditos", "seguros", "aseguradora", "aseguradoras", "impuesto", "impuestos", "irpf", "declaracion de la renta",
    "hacienda", "presupuestos", "pib", "ipc", "deficit", "superavit", "recesion", "fmi", "fondo monetario internacional",
    "ocde", "aranceles", "arancel", "concurso de acreedores", "quiebra", "bancarrota", "rating", "agencia de calificacion",
]
# Siglas que solo cuentan en mayúsculas (en minúsculas son palabras corrientes o nombres de persona)
FINANCE_CASE = re.compile(r"\b(BCE|Fed|FMI|OPA|PIB|IPC|OCDE|IBEX|ETF|CNMV)\b")
FINANCE_PATH = re.compile(r"/(finanzas|mercados|bolsa|cripto|criptomonedas|cinco-?dias|mis-finanzas|inversion|fondos)/")

# Palabras ambiguas que no se buscan sueltas: «oro» (medallas), «bono» (bono social), «app», «mando»,
# «mario», «switch», «valve», «hacienda» (finca), «seguros», «credito» (créditos de película)…
# se quedan fuera de las búsquedas por defecto y solo cuentan junto a otro término del mismo tema.
_WEAK_TECH = {"app", "apps", "mando", "mario", "valve", "pokemon", "zelda", "meta ai", "intel", "amd", "windows", "gaming",
              "steam", "twitch", "robot", "robots", "bateria", "dron", "drones", "internet", "chip", "chips", "movil",
              "moviles", "streaming", "netflix", "spotify", "youtube", "amazon web services", "lanzamiento del juego"}
_WEAK_FINANCE = {"oro", "bono", "bonos", "hacienda", "seguros", "credito", "creditos", "banco", "bancos", "banca",
                 "inversion", "mercados", "ahorro", "deposito", "depositos", "prestamo", "prestamos", "impuesto",
                 "impuestos", "presupuestos", "deficit", "superavit", "petroleo", "barril", "fusion", "adquisicion",
                 "beneficios", "bolsa", "bolsas", "cotiza", "rating", "quiebra", "opa", "cripto", "santander"}
_WEAK_SPORT = {"var", "barca", "betis", "serie a", "rally", "surf", "entrenador", "portero", "delantero", "arbitro",
               "atp", "wta", "us open", "acb", "f1", "valencia cf", "villarreal"}


def _compile(terms: list[str], skip: set[str] = frozenset()) -> re.Pattern:
    words = sorted({t for t in terms if t not in skip}, key=len, reverse=True)
    return re.compile(r"(?<![\w])(" + "|".join(re.escape(t) for t in words) + r")(?![\w])")


# Cada tema tiene un patrón «fuerte» (basta uno en el titular) y otro «débil» (palabras ambiguas:
# solo cuentan si aparecen al menos dos términos distintos o si se combinan con uno fuerte).
_STRONG = {
    "sport": _compile(SPORT_TERMS, _WEAK_SPORT),
    TECH: _compile(TECH_TERMS, _WEAK_TECH),
    FINANCE: _compile(FINANCE_TERMS, _WEAK_FINANCE),
}
_WEAK = {
    "sport": _compile(sorted(_WEAK_SPORT)),
    TECH: _compile(sorted(_WEAK_TECH)),
    FINANCE: _compile(sorted(_WEAK_FINANCE)),
}
_CASE = {"sport": None, TECH: _TECH_CASE_STRICT, FINANCE: FINANCE_CASE}
_PATH = {"sport": SPORT_PATH, TECH: TECH_PATH, FINANCE: FINANCE_PATH}


def _hits(topic: str, text: str) -> set[str]:
    """Términos fuertes y débiles (marcados con «~») de un texto para un tema."""
    if not text:
        return set()
    folded = strip_accents(text.lower())
    out = set(_STRONG[topic].findall(folded))
    out |= {"~" + w for w in _WEAK[topic].findall(folded)}
    cs = _CASE[topic]
    if cs:
        out |= {m for m in cs.findall(text)}
    return out


def _score(hits: set[str]) -> int:
    strong = sum(1 for h in hits if not h.startswith("~"))
    weak = len(hits) - strong
    return strong * 2 + weak


def _get(a, name: str):
    return getattr(a, name, None) if hasattr(a, name) else a.get(name)


def matches(topic: str, article) -> bool:
    """¿Encaja este artículo (objeto o dict) con el tema? Titular, URL o resumen."""
    url = (_get(article, "url") or "").lower()
    if _PATH[topic].search(url):
        return True
    if _score(_hits(topic, _get(article, "title") or "")) >= 2:
        return True  # un término fuerte, o dos débiles distintos
    # resumen: hace falta más evidencia (dos términos fuertes, o uno fuerte más uno débil)
    # y el titular debe aportar algo, para que una mención de pasada no cambie el tema
    summary_score = _score(_hits(topic, _get(article, "summary") or ""))
    title_score = _score(_hits(topic, _get(article, "title") or ""))
    return summary_score >= 4 or (summary_score >= 2 and title_score >= 1)


def is_sport(article) -> bool:
    return matches("sport", article)


def topics_of_group(arts) -> list[str]:
    """Temas de un grupo: los que cumplen al menos la mitad de sus artículos."""
    out = []
    for topic in (TECH, FINANCE):
        n = sum(1 for a in arts if matches(topic, a))
        if n and n * 2 >= len(arts):
            out.append(topic)
    return out


def is_sport_group(arts) -> bool:
    n = sum(1 for a in arts if is_sport(a))
    return bool(arts) and n * 2 >= len(arts)
