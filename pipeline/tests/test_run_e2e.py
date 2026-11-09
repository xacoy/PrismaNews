import json
from types import SimpleNamespace

from conftest import NOW, mk

from prisma import run as runmod


def setup(monkeypatch, fake, fresh):
    monkeypatch.setattr(runmod, "Embedder", lambda *a, **k: fake)
    monkeypatch.setattr(runmod, "fetch_all", lambda *a, **k: (fresh, [{"name": "x", "ok": True, "articles": 1, "error": None}]))
    monkeypatch.setattr(runmod, "load_sources", lambda p: [{"name": "A", "scope": "nacional"}, {"name": "B", "scope": "canario"}])


def args(tmp_path, prev=None, name="out"):
    return SimpleNamespace(sources="x", config="config/clustering.yml", prev_dir=prev, out_dir=str(tmp_path / name), snapshot=None, emb_cache=None)


def test_dos_ejecuciones_conservan_id_y_pool(tmp_path, monkeypatch, fake):
    f1 = [mk("A", "Sánchez anuncia plan de vivienda para jóvenes", 3), mk("B", "Plan de vivienda de Sánchez para jóvenes", 2, "canario"),
          mk("A", "Erupción volcánica en La Palma esta noche", 1)]
    setup(monkeypatch, fake, f1)
    m1 = runmod.run(args(tmp_path), now=NOW)
    g1 = json.loads((tmp_path / "out" / "groups.json").read_text())
    assert len(g1["groups"]) == 1 and g1["groups"][0]["source_count"] == 2
    gid = g1["groups"][0]["id"]
    pool1 = json.loads((tmp_path / "out" / "pool.json").read_text())
    assert [a["title"] for a in pool1["articles"]] == ["Erupción volcánica en La Palma esta noche"]  # suelto, se conserva

    # segunda pasada: el feed ya no trae las noticias viejas, pero llega un tercer medio y el otro medio cubre la erupción
    f2 = [mk("C", "Sánchez presenta su plan de vivienda para jóvenes", 0.5),
          mk("B", "Erupción volcánica en La Palma esta noche", 0.4, "canario")]
    setup(monkeypatch, fake, f2)
    runmod.run(args(tmp_path, prev=str(tmp_path / "out"), name="out2"), now=NOW)
    g2 = {g["id"]: g for g in json.loads((tmp_path / "out2" / "groups.json").read_text())["groups"]}
    assert gid in g2 and g2[gid]["source_count"] == 3          # id estable y grupo crecido
    assert len(g2) == 2                                         # la erupción ya tiene 2 medios gracias al pool
    assert all(a["url"].endswith("ref=prisma") for g in g2.values() for a in g["articles"])


def test_aborta_si_no_hay_nada(tmp_path, monkeypatch, fake):
    import pytest
    setup(monkeypatch, fake, [])
    with pytest.raises(SystemExit):
        runmod.run(args(tmp_path), now=NOW)
