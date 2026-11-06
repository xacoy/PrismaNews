"""Clustering jerárquico (enlace medio, distancia coseno) con reglas de veto."""
from __future__ import annotations

import numpy as np
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform

from . import rules

VETO_DISTANCE = 1.5  # distancia asignada a pares vetados (la distancia coseno normal está en [0, 2])


def cluster_titles(emb: np.ndarray, titles: list[str], threshold: float, rules_cfg: dict | None = None) -> list[int]:
    """Etiqueta de cluster por elemento. Los titulares de directos/crónicas quedan solos."""
    n = len(titles)
    if n == 0:
        return []
    if n == 1:
        return [1]
    rules_cfg = rules_cfg or {}
    sim = emb @ emb.T
    dist = np.clip(1.0 - sim, 0.0, 2.0)
    np.fill_diagonal(dist, 0.0)

    if rules_cfg:
        live = np.array([rules_cfg.get("exclude_live", True) and rules.is_live(t) for t in titles])
        dist[live, :] = VETO_DISTANCE
        dist[:, live] = VETO_DISTANCE
        # solo se miran las reglas en pares ya parecidos (los lejanos no se agruparían de todos modos)
        ii, jj = np.where(np.triu(sim >= threshold - 0.25, k=1))
        for i, j in zip(ii, jj):
            if live[i] or live[j]:
                continue
            if rules.veto(titles[i], titles[j], float(sim[i, j]), rules_cfg):
                dist[i, j] = dist[j, i] = VETO_DISTANCE
        np.fill_diagonal(dist, 0.0)

    z = linkage(squareform(dist, checks=False), method="average")
    return fcluster(z, t=1.0 - threshold, criterion="distance").tolist()


def groups_from_labels(labels: list[int]) -> list[list[int]]:
    by: dict[int, list[int]] = {}
    for i, l in enumerate(labels):
        by.setdefault(l, []).append(i)
    return list(by.values())
