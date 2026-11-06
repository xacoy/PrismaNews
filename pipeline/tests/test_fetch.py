from datetime import datetime, timezone
from pathlib import Path

import requests

from prisma.fetch import Robots, fetch_all, fetch_source, load_sources, parse_feed

FX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "feeds"
NOW = datetime(2026, 11, 6, 12, 0, tzinfo=timezone.utc)
SRC = {"name": "Diario de Prueba", "scope": "nacional", "url": "https://www.ejemplo.es/rss", "status": "activo"}


def test_parse_feed_rss():
    arts = parse_feed((FX / "rss_medio.xml").read_bytes(), SRC, NOW)
    titles = [a.title for a in arts]
    # sin fecha y sin titular se descartan; el sufijo del medio se quita
    assert "Noticia sin fecha" not in titles and "" not in titles
    first = arts[0]
    assert first.title == "El Gobierno aprueba el decreto & las ayudas"
    assert first.url == "https://www.ejemplo.es/politica/decreto.html?id=7"
    assert first.author == "Ana Pérez"
    assert first.summary == "Resumen corto del decreto."
    assert first.image == "https://img.ejemplo.es/decreto.jpg"
    assert first.source == "Diario de Prueba" and first.scope == "nacional"


def test_parse_feed_fecha_futura_se_recorta_y_enclosure_es_imagen():
    arts = {a.title: a for a in parse_feed((FX / "rss_medio.xml").read_bytes(), SRC, NOW)}
    fut = arts["Noticia del futuro"]
    assert fut.published == NOW and fut.image == "https://img.ejemplo.es/futuro.png"


def test_parse_feed_atom_trunca_resumen():
    arts = parse_feed((FX / "atom_medio.xml").read_bytes(), {**SRC, "name": "Atom"}, NOW)
    assert len(arts) == 1 and arts[0].author == "Redacción"
    assert len(arts[0].summary) <= 281 and arts[0].summary.endswith("…")


class Resp:
    def __init__(self, status=200, content=b"", text=""):
        self.status_code, self.content, self.text = status, content, text


class FakeSession:
    def __init__(self, routes):
        self.routes, self.calls = routes, []

    def get(self, url, headers=None, timeout=None):
        self.calls.append((url, headers))
        r = self.routes[url]
        if isinstance(r, Exception):
            raise r
        return r


def test_fetch_source_respeta_robots_y_usa_user_agent():
    xml = (FX / "rss_medio.xml").read_bytes()
    s = FakeSession({"https://www.ejemplo.es/robots.txt": Resp(200, text="User-agent: *\nDisallow: /rss\n"),
                     SRC["url"]: Resp(200, xml)})
    arts, rep = fetch_source(SRC, s, Robots(s), NOW)
    assert arts == [] and rep["error"] == "bloqueado por robots.txt"
    assert all(u.endswith("robots.txt") for u, _ in s.calls)  # el feed no se pidió


def test_fetch_source_ok_y_errores():
    xml = (FX / "rss_medio.xml").read_bytes()
    s = FakeSession({"https://www.ejemplo.es/robots.txt": Resp(404), SRC["url"]: Resp(200, xml)})
    arts, rep = fetch_source(SRC, s, Robots(s), NOW)
    assert rep["ok"] and rep["articles"] == len(arts) > 0
    assert "PrismaBot" in s.calls[-1][1]["User-Agent"]

    s = FakeSession({"https://www.ejemplo.es/robots.txt": Resp(404), SRC["url"]: Resp(500)})
    assert fetch_source(SRC, s, Robots(s), NOW)[1]["error"] == "HTTP 500"

    s = FakeSession({"https://www.ejemplo.es/robots.txt": Resp(404), SRC["url"]: requests.ConnectTimeout()})
    assert fetch_source(SRC, s, Robots(s), NOW)[1]["error"] == "ConnectTimeout"

    s = FakeSession({"https://www.ejemplo.es/robots.txt": Resp(404), SRC["url"]: Resp(200, b"<html>no es un feed</html>")})
    assert fetch_source(SRC, s, Robots(s), NOW)[1]["error"] == "sin entradas válidas"


def test_fetch_all_filtra_ventana_de_48h_y_deduplica(monkeypatch):
    monkeypatch.setattr("prisma.fetch.HOST_DELAY", 0)
    xml = (FX / "rss_medio.xml").read_bytes()
    s = FakeSession({"https://www.ejemplo.es/robots.txt": Resp(404), SRC["url"]: Resp(200, xml)})
    arts, reps = fetch_all([SRC], now=NOW, session=s)
    titles = [a.title for a in arts]
    assert "Noticia antigua" not in titles                     # fuera de 48 h
    assert titles.count("El Gobierno aprueba el decreto & las ayudas") == 1   # repetición del mismo medio
    assert reps[0]["ok"]


def test_load_sources_solo_activas():
    srcs = load_sources(str(FX.parents[2] / "config" / "sources.yml"))
    assert len(srcs) == 20 and all(s["status"] == "activo" for s in srcs)
    assert {s["scope"] for s in srcs} == {"nacional", "canario"}


def test_url_de_imagen_con_amp_doble_escapado():
    xml = b"""<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/"><channel><item>
    <title>Titular de prueba largo</title><link>https://e.es/a</link><pubDate>Thu, 05 Nov 2026 10:00:00 +0000</pubDate>
    <media:content url="https://img.e.es/a.jpg?w=1200&amp;amp;h=675&amp;amp;f=webp" medium="image"/></item></channel></rss>"""
    a = parse_feed(xml, SRC, NOW)[0]
    assert a.image == "https://img.e.es/a.jpg?w=1200&h=675&f=webp"
