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
    assert g["source_count"] == 2 and g["editions"] == ["espana", "canarias"]
    assert g["first_published"] < g["last_published"]
    assert all("ref=prisma" in a["url"] for a in g["articles"])
    assert g["articles"][0]["url"] == "https://a.es/x?id=1&ref=prisma"


def test_vectores_mezclan_resumen(fake):
    a = [mk("A", "Plan de vivienda", summary="medidas para jóvenes"), mk("B", "Otro asunto")]
    v = article_vectors(a, fake, 0.7, 0.3)
    assert v.shape == (2, 256) and abs(np.linalg.norm(v[0]) - 1) < 1e-5
