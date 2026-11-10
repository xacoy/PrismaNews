#!/usr/bin/env python3
"""Comprueba con peticiones reales los feeds candidatos y genera config/sources.yml.

Uso: python scripts/check_sources.py [candidates.yml] [sources.yml]
Solo RSS/Atom públicos; respeta robots.txt; User-Agent identificable.
"""
import re
import sys
import time
import urllib.robotparser
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import yaml

UA = "PrismaBot/0.1 (+https://github.com/xacoy/PrismaNews)"
HEADERS = {"User-Agent": UA, "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.5"}
_robots = {}


def allowed(url: str) -> bool:
    p = urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(base + "/robots.txt", headers=HEADERS, timeout=15)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)


def probe(url: str) -> dict:
    out = {"url": url, "ok": False}
    if not allowed(url):
        out["error"] = "bloqueado por robots.txt"
        return out
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
        if r.status_code == 406:  # algunos servidores no aceptan nuestro Accept
            r = requests.get(url, headers={**HEADERS, "Accept": "*/*"}, timeout=20, allow_redirects=True)
    except requests.RequestException as e:
        out["error"] = f"{type(e).__name__}"
        return out
    out["http"] = r.status_code
    out["final_url"] = r.url
    if r.status_code != 200:
        out["error"] = f"HTTP {r.status_code}"
        return out
    d = feedparser.parse(r.content)
    n = len(d.entries)
    out["entries"] = n
    if n == 0:
        out["error"] = "sin entradas"
        return out
    dates = [time.mktime(e.published_parsed) for e in d.entries if getattr(e, "published_parsed", None)]
    if dates:
        out["newest"] = datetime.fromtimestamp(max(dates), timezone.utc).isoformat(timespec="minutes")
        age_h = (time.time() - max(dates)) / 3600
        out["newest_age_h"] = round(age_h, 1)
        if age_h > 72:
            out["error"] = f"feed inactivo (último hace {age_h:.0f} h)"
            return out
    else:
        out["error"] = "entradas sin fecha"
        return out
    out["ok"] = True
    return out


def discover(home: str) -> list[str]:
    """Busca <link rel=alternate type=rss/atom> en la portada (sin leer artículos)."""
    if not allowed(home):
        return []
    try:
        r = requests.get(home, headers=HEADERS, timeout=20)
    except requests.RequestException:
        return []
    found = []
    for m in re.finditer(r"<link[^>]+>", r.text[:200_000], re.I):
        tag = m.group(0)
        if re.search(r'type=["\']application/(rss|atom)\+xml', tag, re.I):
            h = re.search(r'href=["\']([^"\']+)', tag, re.I)
            if h:
                found.append(urljoin(home, h.group(1)))
    return found


def main():
    cand_path = sys.argv[1] if len(sys.argv) > 1 else "config/candidates.yml"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "config/sources.yml"
    cands = yaml.safe_load(open(cand_path, encoding="utf-8"))
    today = datetime.now(timezone.utc).date().isoformat()
    result = []
    for c in cands:
        tried, best = [], None
        for u in c["feeds"]:
            p = probe(u)
            tried.append(p)
            if p["ok"]:
                best = p
                break
            time.sleep(1)
        if not best:
            for u in discover(c["home"])[:3]:
                if u in c["feeds"]:
                    continue
                p = probe(u)
                p["discovered"] = True
                tried.append(p)
                if p["ok"]:
                    best = p
                    break
                time.sleep(1)
        entry = {
            "name": c["name"],
            "url": (best or tried[-1] if tried else {"url": c["feeds"][0]})["url"],
            "scope": c["scope"],
            **({"topic": c["topic"]} if c.get("topic") else {}),
            "status": "activo" if best else "descartado",
            "checked": today,
        }
        if best:
            entry["entries_seen"] = best["entries"]
            entry["newest_age_h"] = best["newest_age_h"]
        else:
            entry["reason"] = "; ".join(f'{t["url"]} -> {t.get("error")}' for t in tried) or "sin candidatos"
        result.append(entry)
        print(f'{entry["status"]:11} {c["name"]:24} {entry["url"]}  {entry.get("reason", "")}', flush=True)
        time.sleep(1)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Generado por scripts/check_sources.py. No editar a mano las comprobaciones.\n")
        yaml.safe_dump(result, f, allow_unicode=True, sort_keys=False, width=200)
    ok = sum(1 for e in result if e["status"] == "activo")
    print(f"\n{ok}/{len(result)} feeds activos")
    print("----- sources.yml -----")
    print(open(out_path, encoding="utf-8").read())


if __name__ == "__main__":
    main()
