"""Modelo de datos. Solo se guarda lo imprescindible: nunca el cuerpo del artículo."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


@dataclass
class Article:
    id: str            # sha1 corto de la URL canónica
    source: str        # nombre del medio
    scope: str         # "nacional" | "canario"
    title: str
    url: str           # URL canónica original (sin ?ref=prisma; se añade al exportar)
    published: datetime
    author: str | None = None
    summary: str | None = None   # resumen corto del feed (<= 280 caracteres)
    image: str | None = None     # URL de la imagen del feed (solo enlazada)
    topic: str | None = None     # tema del medio si es especializado ("tecnologia"); None si es generalista

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = iso(self.published)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Article":
        d = dict(d)
        d["published"] = parse_iso(d["published"])
        keys = cls.__dataclass_fields__.keys()
        return cls(**{k: d.get(k) for k in keys})
