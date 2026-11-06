#!/usr/bin/env python3
"""Barre umbrales y muestra precisión y cobertura sobre los pares etiquetados a mano.

Uso: python scripts/eval_threshold.py [--min-precision 0.95]
Necesita el modelo real (corre en GitHub Actions: workflow 'evaluacion').
"""
import argparse
import os
import sys

import yaml

sys.path.insert(0, "pipeline")
from prisma import evaluate as ev  # noqa: E402
from prisma.embed import Embedder  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--pairs", default="tests/fixtures/pairs.jsonl")
ap.add_argument("--bins", default="tests/fixtures/pairs_bins.json")
ap.add_argument("--config", default="config/clustering.yml")
ap.add_argument("--min-precision", type=float, default=0.95)
a = ap.parse_args()

cfg = yaml.safe_load(open(a.config, encoding="utf-8"))
pairs = ev.load_pairs(a.pairs)
pos = sum(p["label"] for p in pairs)
print(f"{len(pairs)} pares etiquetados ({pos} mismo asunto, {len(pairs) - pos} distinto)")
emb = Embedder(cfg["embedding"]["model"], cache_dir=os.environ.get("FASTEMBED_CACHE"))
rows = ev.sweep(pairs, emb, cfg["rules"], a.bins)

print("\nMétricas PONDERADAS por tramo (estimación sobre todos los pares entre medios distintos)")
print(f"{'umbral':>6} | {'coseno P/C':>13} | {'cluster P/C':>13} | {'cluster+reglas P/C/F1':>23} | sin ponderar P/C")
for r in rows:
    c, k, kr = r["coseno"], r["cluster"], r["cluster+reglas"]
    print(f"{r['threshold']:>6.2f} | {c['precision']:.2f} / {c['recall']:.2f} | {k['precision']:.2f} / {k['recall']:.2f} | "
          f"{kr['precision']:.2f} / {kr['recall']:.2f} / {kr['f1']:.2f} | {kr['precision_sin_ponderar']:.2f} / {kr['recall_sin_ponderar']:.2f}")
best = ev.recommend(rows, "cluster+reglas", a.min_precision)
print(f"\nConfig actual: umbral {cfg['threshold']}")
if best:
    k = best["cluster+reglas"]
    print(f"Recomendado (máx. cobertura con precisión ponderada >= {a.min_precision}): umbral {best['threshold']} "
          f"-> precisión {k['precision']:.3f}, cobertura {k['recall']:.3f}, F1 {k['f1']:.3f}")
else:
    print("Ningún umbral alcanza la precisión pedida.")

# Errores del umbral actual, para revisar a mano
from prisma.evaluate import predict  # noqa: E402
pred = predict(pairs, emb, cfg["threshold"], cfg["rules"], "cluster")
print("\nFalsos positivos (agrupados sin deber) con el umbral actual:")
for p, y in zip(pairs, pred):
    if y and not p["label"]:
        print(f"  {p['id']} [{p['a']['source']}] {p['a']['title'][:90]} || [{p['b']['source']}] {p['b']['title'][:90]}")
print("Falsos negativos (separados sin deber) con el umbral actual:")
for p, y in zip(pairs, pred):
    if not y and p["label"]:
        print(f"  {p['id']} [{p['a']['source']}] {p['a']['title'][:90]} || [{p['b']['source']}] {p['b']['title'][:90]}")
