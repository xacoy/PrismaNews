"""Descarga y lectura de feeds RSS/Atom públicos. No se lee el contenido de los artículos."""
from __future__ import annotations

import html
import time
import urllib.robotparser
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import feedparser
import requests
import yaml

from .models import Article
from .normalize import article_id, canonical_url, clean_summary, clean_text, clean_title, dedupe

USER_AGENT = "PrismaBot/0.1 (+https://github.com/xacoy/PrismaNews)"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5",
}
HOST_DELAY = 1.0   # segundos entre peticiones al mismo host
TIMEOUT = 20


def load_sources(path: str, only_active: bool = True) -> list[dict]:
    sources = yaml.safe_load(open(path, encoding="utf-8"))
    return [s for s in sources if s["status"] == "activo"] if only_active else sources


class Robots:
    """Caché de robots.txt por host."""

    def __init__(self, session):
        self.session = session
        self._cache: dict[str, urllib.robotparser.RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        p = urlparse(url)
        base = f"{p.scheme}://{p.netloc}"
        if base not in self._cache:
            rp = urllib.robotparser.RobotFileParser()
            try:
                r = self.session.get(base + "/robots.txt", headers=HEADERS, timeout=TIMEOUT)
                rp.parse(r.text.splitlines() if r.status_code == 200 else [])
            except requests.RequestException:
                rp.parse([])
            self._cache[base] = rp
        return self._cache[base].can_fetch(USER_AGENT, url)


def _image(entry) -> str | None:
    url = _image_raw(entry)
    # algunos feeds escapan dos veces los "&" de las URL (&amp;amp;)
    return html.unescape(url).strip() if url else None


def _image_raw(entry) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for m in entry.get(key, []) or []:
            url = m.get("url")
            if url and (m.get("medium") in (None, "image") or key == "media_thumbnail"):
                return url
    for enc in entry.get("enclosures", []) or []:
        if (enc.get("type") or "").startswith("image/") and enc.get("href"):
            return enc["href"]
    for link in entry.get("links", []) or []:
        if (link.get("type") or "").startswith("image/") and link.get("href"):
            return link["href"]
    return None


def _published(entry, now: datetime) -> datetime | None:
    t = entry.get("published_parsed") or entry.get("updated_parsed")
    if not t:
        return None
    dt = datetime(*t[:6], tzinfo=timezone.utc)
    return min(dt, now)  # una fecha futura se recorta a "ahora"


def parse_feed(content: bytes, source: dict, now: datetime) -> list[Article]:
    """Convierte el XML de un feed en artículos. Descarta entradas sin titular, enlace o fecha."""
    d = feedparser.parse(content)
    out = []
    for e in d.entries:
        title = clean_title(e.get("title"), source["name"])
        link = html.unescape((e.get("link") or "").strip())
        pub = _published(e, now)
        if not title or not link.startswith("http") or pub is None:
            continue
        author = clean_text(e.get("author")) or None
        out.append(
            Article(
                id=article_id(link),
                source=source["name"],
                scope=source["scope"],
                title=title,
                url=canonical_url(link),
                published=pub,
                author=author,
                summary=clean_summary(e.get("summary") or e.get("description")),
                image=_image(e),
            )
        )
    return out


def fetch_source(source: dict, session, robots: Robots, now: datetime) -> tuple[list[Article], dict]:
    report = {"name": source["name"], "ok": False, "articles": 0, "error": None}
    url = source["url"]
    if not robots.allowed(url):
        report["error"] = "bloqueado por robots.txt"
        return [], report
    try:
        r = session.get(url, headers=HEADERS, timeout=TIMEOUT)
        if r.status_code == 406:
            r = session.get(url, headers={**HEADERS, "Accept": "*/*"}, timeout=TIMEOUT)
    except requests.RequestException as ex:
        report["error"] = type(ex).__name__
        return [], report
    if r.status_code != 200:
        report["error"] = f"HTTP {r.status_code}"
        return [], report
    arts = parse_feed(r.content, source, now)
    report.update(ok=bool(arts), articles=len(arts), error=None if arts else "sin entradas válidas")
    return arts, report


def fetch_all(sources: list[dict], now: datetime | None = None, window_hours: int = 48,
              workers: int = 6, session=None) -> tuple[list[Article], list[dict]]:
    """Descarga todos los feeds. Las peticiones al mismo host se hacen en serie y espaciadas."""
    now = now or datetime.now(timezone.utc)
    session = session or requests.Session()
    robots = Robots(session)
    by_host = defaultdict(list)
    for s in sources:
        by_host[urlparse(s["url"]).netloc].append(s)

    def run_host(group):
        res = []
        for i, s in enumerate(group):
            if i:
                time.sleep(HOST_DELAY)
            res.append(fetch_source(s, session, robots, now))
        return res

    arts, reports = [], []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(run_host, by_host.values()):
            for a, r in res:
                arts += a
                reports.append(r)
    cutoff = now - timedelta(hours=window_hours)
    arts = dedupe([a for a in arts if a.published >= cutoff])
    return arts, reports
