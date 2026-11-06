#!/usr/bin/env python3
"""Informe para revisar la regla de la edición Canarias sobre datos reales publicados.

Uso: python scripts/canarias_report.py groups.json
Lista los grupos con algún medio canario o con términos canarios y dice qué decide la regla y por qué.
"""
import json
import sys

sys.path.insert(0, "pipeline")
from prisma.canarias import canary_hits  # noqa: E402

d = json.load(open(sys.argv[1], encoding="utf-8"))
yes, no = [], []
for g in d["groups"]:
    hits, cs = set(), set()
    for a in g["articles"]:
        h = canary_hits(a["title"]) + canary_hits(a.get("summary") or "")
        hits |= set(h)
        if a["scope"] == "canario":
            cs.add(a["source"])
    if hits or cs:
        (yes if hits else no).append((g, sorted(hits), sorted(cs)))
print(f"## {len(d['groups'])} grupos; con términos canarios: {len(yes)}; con medio canario pero SIN términos: {len(no)}")
print("\n## SÍ son de Canarias (hay términos canarios)")
for g, h, cs in yes:
    print(f"S {g['source_count']:>2}m hits={','.join(h)[:40]:<40} can={','.join(cs)[:30]:<30} {g['headline'][:85]}")
print("\n## NO (medio canario pero sin términos canarios)")
for g, h, cs in no:
    print(f"N {g['source_count']:>2}m can={','.join(cs)[:40]:<40} {g['headline'][:95]}")
