import numpy as np
from conftest import NOW, mk

from prisma import cluster as cl
from prisma.groups import assign_ids, make_group, new_group_id, trend
from prisma.embed import article_vectors

RULES = {"entity_veto_below": 0.88, "number_veto_below": 0.93, "exclude_live": True}


def labels(titles, fake, thr=0.6, rules=RULES):
    return cl.cluster_titles(fake.encode(titles), titles, thr, rules)


def test_agrupa_mismo_asunto_y_separa_distinto(fake):
    t = ["Sánchez anuncia un plan de vivienda para jóvenes",
         "El plan de vivienda de Sánchez para jóvenes",
         "Un volcán entra en erupción en La Palma"]
    l = labels(t, fake)
    assert l[0] == l[1] != l[2]


def test_cifras_distintas_no_se_agrupan(fake):
    t = ["Mueren 3 personas en un accidente en la A-6", "Mueren 5 personas en un accidente en la A-6"]
    assert labels(t, fake, rules=RULES)[0] != labels(t, fake, rules=RULES)[1]
    assert labels(t, fake, rules={})[0] == labels(t, fake, rules={})[1]   # sin reglas sí se juntarían


def test_directos_no_actuan_de_puente(fake):
    t = ["Última hora: Sánchez anuncia plan de vivienda en directo", "Sánchez anuncia plan de vivienda para jóvenes",
         "El plan de vivienda de Sánchez para jóvenes"]
    l = labels(t, fake)
    assert l[1] == l[2] and l[0] != l[1]


def test_ids_estables_entre_ejecuciones(fake):
    a1 = [mk("A", "Sánchez anuncia plan de vivienda", 5), mk("B", "Plan de vivienda de Sánchez", 4)]
    g1 = make_group(new_group_id(a1), a1, fake.encode([a.title for a in a1]), NOW, 6)
    # llega un tercer medio: el grupo crece pero conserva el id
    a2 = a1 + [mk("C", "Sánchez presenta su plan de vivienda", 1)]
    ids = assign_ids([a2], [g1])
    assert ids == [g1["id"]]
    # un grupo sin relación recibe id nuevo
    b = [mk("A", "Erupción en La Palma", 2), mk("B", "Volcán de La Palma en erupción", 2)]
    assert assign_ids([a2, b], [g1])[0] == g1["id"] and assign_ids([a2, b], [g1])[1] != g1["id"]


def test_fusion_de_grupos_hereda_el_mas_antiguo(fake):
    a = [mk("A", "plan vivienda uno", 30), mk("B", "plan vivienda dos", 29)]
    b = [mk("C", "plan vivienda tres", 10), mk("D", "plan vivienda cuatro", 9)]
    ga = make_group(new_group_id(a), a, fake.encode([x.title for x in a]), NOW, 6)
    gb = make_group(new_group_id(b), b, fake.encode([x.title for x in b]), NOW, 6)
    ids = assign_ids([a + b], [gb, ga])
    assert ids == [ga["id"]]


def test_trend():
    arts = [mk("A", "x", 1), mk("B", "x", 2), mk("C", "x", 3), mk("D", "x", 8)]
    assert trend(arts, NOW, 6)["state"] == "sube"
    arts = [mk("A", "x", 1), mk("B", "x", 7), mk("C", "x", 8), mk("D", "x", 9)]
    assert trend(arts, NOW, 6)["state"] == "baja"
    assert trend([mk("A", "x", 1), mk("B", "x", 8)], NOW, 6)["state"] == "estable"


def test_make_group_campos_y_enlaces(fake):
    arts = [mk("A", "Plan de vivienda", 5, scope="canario", url="https://a.es/x?id=1"), mk("B", "Plan de vivienda ya", 2)]
    g = make_group("g1", arts, fake.encode([a.title for a in arts]), NOW, 6)
    assert g["source_count"] == 2 and g["editions"] == ["espana"]      # medio canario, noticia sin nada de Canarias
    arts[1].title = "Plan de vivienda en Tenerife"
    g = make_group("g1", arts, fake.encode([a.title for a in arts]), NOW, 6)
    assert g["editions"] == ["espana", "canarias"]
    assert g["first_published"] < g["last_published"]
    assert all("ref=prisma" in a["url"] for a in g["articles"])
    assert g["articles"][0]["url"] == "https://a.es/x?id=1&ref=prisma"


def test_vectores_mezclan_resumen(fake):
    a = [mk("A", "Plan de vivienda", summary="medidas para jóvenes"), mk("B", "Otro asunto")]
    v, st = article_vectors(a, fake, 0.7, 0.3)
    assert st == {"new": 2, "cached": 0}
    assert v.shape == (2, 256) and abs(np.linalg.norm(v[0]) - 1) < 1e-5


def test_bonus_de_entidades_une_titulares_con_pocas_palabras_comunes(fake):
    t = ["La Fiscalía Europea investiga fraude Adif Urda", "Operación de la UCO por Urda: reclaman documentación a Adif"]
    sin = cl.cluster_titles(fake.encode(t), t, 0.55, {})
    con = cl.cluster_titles(fake.encode(t), t, 0.55, {"entity_boost": 0.6})
    assert sin[0] != sin[1] and con[0] == con[1]


def test_enlace_configurable(fake):
    t = ["plan vivienda joven uno", "plan vivienda joven dos", "plan vivienda joven tres"]
    for m in ("average", "weighted", "single"):
        assert len(set(cl.cluster_titles(fake.encode(t), t, 0.5, {}, m))) == 1


def test_cache_de_vectores_solo_calcula_lo_nuevo(fake, tmp_path):
    from prisma.embed import VectorCache

    class Contador:
        def __init__(self, inner): self.inner, self.n = inner, 0
        def encode(self, texts):
            self.n += len(texts)
            return self.inner.encode(texts)

    emb = Contador(fake)
    path = str(tmp_path / "vectors.npz")
    a = [mk("A", "Plan de vivienda", summary="medidas"), mk("B", "Otro asunto")]
    v1, s1 = article_vectors(a, emb, 0.7, 0.3, cache=VectorCache(path), model="m")
    assert s1 == {"new": 2, "cached": 0}
    n1 = emb.n
    # segunda ejecución con un artículo nuevo: solo se calcula ese
    b = a + [mk("C", "Erupción en La Palma")]
    v2, s2 = article_vectors(b, emb, 0.7, 0.3, cache=VectorCache(path), model="m")
    assert s2 == {"new": 1, "cached": 2} and emb.n == n1 + 1
    assert np.allclose(v1, v2[:2], atol=1e-2)            # float16: pequeña pérdida de precisión
    # si cambia el modelo (o los pesos), se recalcula todo
    _, s3 = article_vectors(b, emb, 0.7, 0.3, cache=VectorCache(path), model="otro")
    assert s3["new"] == 3
    # la caché se poda: solo conserva lo que está en el pool actual
    article_vectors(a[:1], emb, 0.7, 0.3, cache=VectorCache(path), model="otro")
    assert len(VectorCache(path).vectors) == 1


def test_cache_ilegible_se_descarta(tmp_path):
    from prisma.embed import VectorCache
    p = tmp_path / "vectors.npz"
    p.write_bytes(b"no es un npz")
    assert VectorCache(str(p)).vectors == {}


def test_refresh_editions_corrige_el_historico(fake):
    from prisma.groups import refresh_editions
    arts = [mk("A", "Aviso por lluvias en Lanzarote", 3), mk("B", "Lluvias en Lanzarote: alerta", 2)]
    g = make_group("g1", arts, fake.encode([a.title for a in arts]), NOW, 6)
    g["editions"] = ["espana"]                                          # grupo guardado con una regla antigua
    assert refresh_editions(g)["editions"] == ["espana", "canarias"]
