"""Validación de los JSON generados: si algo falla, el workflow no despliega."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .models import parse_iso


def validate(out_dir: str, min_sources: int = 2) -> list[str]:
    errs: list[str] = []
    d = Path(out_dir)
    try:
        data = json.loads((d / "groups.json").read_text(encoding="utf-8"))
        json.loads((d / "pool.json").read_text(encoding="utf-8"))
        json.loads((d / "meta.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return [f"JSON ilegible: {e}"]
    if data.get("schema_version") != 1:
        errs.append("schema_version desconocido")
    groups = data.get("groups")
    if not isinstance(groups, list):
        return errs + ["'groups' no es una lista"]
    if not groups:
        errs.append("no hay ningún grupo (¿falló la agrupación?)")
    ids = [g.get("id") for g in groups]
    if len(ids) != len(set(ids)):
        errs.append("ids de grupo repetidos")
    for g in groups:
        try:
            if len({a["source"] for a in g["articles"]}) < min_sources:
                errs.append(f"{g['id']}: menos de {min_sources} medios")
            parse_iso(g["first_published"]), parse_iso(g["last_published"])
            if not g["headline"]:
                errs.append(f"{g['id']}: sin titular")
            for a in g["articles"]:
                if not a["url"].startswith("http") or "ref=prisma" not in a["url"]:
                    errs.append(f"{g['id']}: enlace sin ?ref=prisma")
                    break
        except (KeyError, ValueError) as e:
            errs.append(f"{g.get('id')}: campo inválido ({e})")
    return errs[:20]


if __name__ == "__main__":
    problems = validate(sys.argv[1] if len(sys.argv) > 1 else "web/public/data")
    for p in problems:
        print("ERROR:", p)
    sys.exit(1 if problems else 0)
