import json

from prisma.validate import validate


def write(tmp, groups, version=1):
    (tmp / "groups.json").write_text(json.dumps({"schema_version": version, "groups": groups}))
    (tmp / "pool.json").write_text("{}")
    (tmp / "meta.json").write_text("{}")


def grp(i, sources=("A", "B"), ref=True):
    return {"id": i, "headline": "x", "first_published": "2026-11-06T10:00:00Z", "last_published": "2026-11-06T11:00:00Z",
            "articles": [{"source": s, "url": "https://e.es/1" + ("?ref=prisma" if ref else "")} for s in sources]}


def test_valido(tmp_path):
    write(tmp_path, [grp("g1"), grp("g2")])
    assert validate(str(tmp_path)) == []


def test_detecta_problemas(tmp_path):
    write(tmp_path, [grp("g1", sources=("A", "A")), grp("g1"), grp("g3", ref=False)])
    msgs = " ".join(validate(str(tmp_path)))
    assert "menos de 2 medios" in msgs and "repetidos" in msgs and "?ref=prisma" in msgs


def test_vacio_y_version(tmp_path):
    write(tmp_path, [], version=2)
    msgs = " ".join(validate(str(tmp_path)))
    assert "schema_version" in msgs and "ningún grupo" in msgs


def test_json_ilegible(tmp_path):
    assert "ilegible" in validate(str(tmp_path))[0]
