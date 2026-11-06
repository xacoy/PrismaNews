#!/usr/bin/env python3
"""Genera pares candidatos de titulares REALES (medios distintos) para etiquetarlos a mano.

Corre en GitHub Actions (necesita red y el modelo). Imprime una muestra estratificada por similitud
coseno para cubrir tanto parecidos obvios como negativos difíciles. También mide tiempos del modelo.
"""
import json
import os
import random
import sys
import time
from datetime import datetime, timezone

import numpy as np

sys.path.insert(0, "pipeline")
from prisma.embed import Embedder  # noqa: E402
from prisma.fetch import fetch_all, load_sources  # noqa: E402

N_PER_BIN = int(sys.argv[1]) if len(sys.argv) > 1 else 22
BINS = [(0.92, 1.01), (0.86, 0.92), (0.80, 0.86), (0.74, 0.80), (0.68, 0.74), (0.62, 0.68), (0.55, 0.62)]

arts, reps = fetch_all(load_sources("config/sources.yml"))
print(f"## {len(arts)} artículos de {sum(r['ok'] for r in reps)} feeds", flush=True)
titles = [a.title for a in arts]

t = time.time()
emb = Embedder(os.environ.get("MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"),
               cache_dir=os.environ.get("FASTEMBED_CACHE"))
t_load = time.time() - t
t = time.time()
v = emb.encode(titles)
t_enc = time.time() - t
print(f"## modelo: carga {t_load:.1f} s; {len(titles)} titulares en {t_enc:.1f} s ({len(titles)/t_enc:.0f}/s); dim {v.shape[1]}", flush=True)

sim = v @ v.T
src = np.array([a.source for a in arts])
iu, ju = np.triu_indices(len(arts), k=1)
mask = src[iu] != src[ju]
iu, ju = iu[mask], ju[mask]
s = sim[iu, ju]
rnd = random.Random(42)
n = 0
for lo, hi in BINS:
    idx = np.where((s >= lo) & (s < hi))[0]
    pick = rnd.sample(list(idx), min(N_PER_BIN, len(idx)))
    print(f"\n## bin {lo:.2f}-{hi:.2f}: {len(idx)} pares disponibles", flush=True)
    for k in pick:
        i, j = iu[k], ju[k]
        n += 1
        print(f"P{n:03d} {s[k]:.3f} | [{arts[i].source}] {arts[i].title} || [{arts[j].source}] {arts[j].title}", flush=True)
