#!/usr/bin/env python3
"""Recorta groups.json a una muestra pequeña para desarrollar la web sin red.

Uso: python scripts/make_sample.py web/public/data/groups.json [n_grupos]
Imprime el JSON recortado entre marcadores (para copiarlo desde el log de Actions).
"""
import json
import sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
n = int(sys.argv[2]) if len(sys.argv) > 2 else 24
groups = d["groups"]
canarias = [g for g in groups if "canarias" in g["editions"]][:6]
rest = [g for g in groups if g not in canarias][: n - len(canarias)]
sel = []
for g in rest + canarias:
    g = dict(g)
    g["articles"] = [dict(a, summary=(a.get("summary") or None)) for a in g["articles"][:6]]
    for a in g["articles"][1:]:
        a["image"] = None
    sel.append(g)
d["groups"] = sel
print("=====SAMPLE-BEGIN=====")
print(json.dumps(d, ensure_ascii=False, separators=(",", ":")))
print("=====SAMPLE-END=====")
