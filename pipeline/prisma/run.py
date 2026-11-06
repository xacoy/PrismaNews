"""Orquestador: recoge, agrupa, fusiona con el histórico y escribe los JSON.

Uso: python -m prisma.run --sources config/sources.yml --config config/clustering.yml \
        --prev-dir /tmp/prev --out-dir web/public/data
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from . import cluster as cl
from .embed import DEFAULT_MODEL, Embedder, VectorCache, article_vectors
from .fetch import fetch_all, load_sources
from .groups import articles_of, assign_ids, make_group, refresh_editions
from .models import Article, iso, parse_iso
from .normalize import dedupe, strip_accents

SCHEMA_VERSION = 1


def slug(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", strip_accents(name.lower())).strip("-")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def merge_history(prev_groups: list[dict], prev_pool: list[Article], fresh: list[Article],
                  now: datetime, window_h: int):
    """Separa el histórico en grupos 'congelados' (sin actividad en la ventana) y artículos activos."""
    cutoff = now - timedelta(hours=window_h)
    frozen, active_groups = [], []
    for g in prev_groups:
        (active_groups if parse_iso(g["last_published"]) >= cutoff else frozen).append(g)
    pool: dict[str, Article] = {}
    for a in prev_pool:
        pool[a.id] = a
    for g in active_groups:
        for a in articles_of(g):
            pool[a.id] = a
    for a in fresh:
        pool[a.id] = a  # los datos recién descargados mandan
    return frozen, active_groups, dedupe(list(pool.values()))


def run(args) -> dict:
    t0 = time.time()
    timings: dict[str, float] = {}
    cfg = yaml.safe_load(open(args.config, encoding="utf-8"))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    prev_dir = Path(args.prev_dir) if args.prev_dir else None

    sources = load_sources(args.sources)
    t = time.time()
    fresh, reports = fetch_all(sources, now=now, window_hours=cfg["window_hours"])
    timings["recogida_s"] = round(time.time() - t, 1)
    print(f"recogida: {len(fresh)} artículos de {sum(r['ok'] for r in reports)}/{len(reports)} feeds "
          f"({timings['recogida_s']} s)", flush=True)
    if args.snapshot:
        Path(args.snapshot).write_text(json.dumps([a.to_dict() for a in fresh], ensure_ascii=False), encoding="utf-8")
        return {}
    if len(fresh) == 0:
        raise SystemExit("No se pudo descargar ningún artículo: se aborta sin tocar el histórico.")

    prev_groups, prev_pool = [], []
    if prev_dir:
        pg = read_json(prev_dir / "groups.json")
        pp = read_json(prev_dir / "pool.json")
        prev_groups = (pg or {}).get("groups", [])
        prev_pool = [Article.from_dict(d) for d in (pp or {}).get("articles", [])]
    print(f"histórico previo: {len(prev_groups)} grupos, {len(prev_pool)} artículos sueltos", flush=True)

    frozen, active_groups, pool = merge_history(prev_groups, prev_pool, fresh, now, cfg["window_hours"])

    t = time.time()
    embedder = Embedder(cfg["embedding"].get("model", DEFAULT_MODEL), cache_dir=os.environ.get("FASTEMBED_CACHE"))
    timings["modelo_carga_s"] = round(time.time() - t, 1)
    t = time.time()
    vcache = VectorCache(str(Path(args.emb_cache) / "vectors.npz") if getattr(args, "emb_cache", None) else None)
    vecs, estats = article_vectors(pool, embedder, cfg["embedding"]["title_weight"], cfg["embedding"]["summary_weight"],
                                   cache=vcache, model=cfg["embedding"]["model"])
    timings["embeddings_s"] = round(time.time() - t, 1)
    print(f"embeddings: {estats['new']} nuevos + {estats['cached']} en caché ({timings['embeddings_s']} s, "
          f"carga del modelo {timings['modelo_carga_s']} s)", flush=True)

    t = time.time()
    labels = cl.cluster_titles(vecs, [a.title for a in pool], cfg["threshold"], cfg["rules"], cfg.get("linkage", "average"))
    clusters = cl.groups_from_labels(labels)
    timings["clustering_s"] = round(time.time() - t, 1)

    publish, loose = [], []
    for idxs in clusters:
        if len({pool[i].source for i in idxs}) >= cfg["min_sources"]:
            publish.append(idxs)
        else:
            loose += idxs
    new_arts = [[pool[i] for i in idxs] for idxs in publish]
    ids = assign_ids(new_arts, active_groups)
    new_groups = [make_group(gid, [pool[i] for i in idxs], vecs[idxs], now, cfg["trend"]["window_hours"])
                  for gid, idxs in zip(ids, publish)]

    keep_after = now - timedelta(days=cfg["history_days"])
    frozen = [refresh_editions(g) for g in frozen]
    groups = [g for g in frozen + new_groups if parse_iso(g["last_published"]) >= keep_after]
    groups.sort(key=lambda g: (g["source_count"], g["last_published"]), reverse=True)

    pool_cut = now - timedelta(hours=cfg["window_hours"])
    pool_out = [pool[i].to_dict() for i in loose if pool[i].published >= pool_cut]

    src_info = [{"name": s["name"], "slug": slug(s["name"]), "scope": s["scope"]} for s in sources]
    (out / "groups.json").write_text(json.dumps({
        "schema_version": SCHEMA_VERSION, "generated_at": iso(now),
        "window_hours": cfg["window_hours"], "history_days": cfg["history_days"],
        "sources": src_info, "groups": groups,
    }, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (out / "pool.json").write_text(json.dumps({"generated_at": iso(now), "articles": pool_out},
                                              ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    timings["total_s"] = round(time.time() - t0, 1)
    meta = {
        "schema_version": SCHEMA_VERSION, "generated_at": iso(now), "model": cfg["embedding"]["model"],
        "threshold": cfg["threshold"], "timings": timings,
        "counts": {"articles_fresh": len(fresh), "pool": len(pool), "groups": len(groups),
                   "groups_new_or_updated": len(new_groups), "groups_frozen": len(frozen),
                   "embeddings_new": estats["new"], "embeddings_cached": estats["cached"]},
        "feeds": reports,
    }
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"timings": timings, "counts": meta["counts"]}, ensure_ascii=False), flush=True)
    return meta


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--sources", default="config/sources.yml")
    p.add_argument("--config", default="config/clustering.yml")
    p.add_argument("--prev-dir", default=None, help="carpeta con groups.json y pool.json de la ejecución anterior")
    p.add_argument("--out-dir", default="web/public/data")
    p.add_argument("--emb-cache", default=None, help="carpeta donde guardar/leer vectors.npz (caché de embeddings)")
    p.add_argument("--snapshot", default=None, help="solo descarga y vuelca los artículos a este JSON")
    run(p.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())
