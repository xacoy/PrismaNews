from prisma import rules
from prisma.headline import pick_headline, sensationalism
import numpy as np

CFG = {"entity_veto_below": 0.88, "number_veto_below": 0.93}


def test_entities_ignora_primera_palabra_y_detecta_propios_y_siglas():
    e = rules.entities("El presidente Pedro Sánchez viaja a Marruecos con la UE")
    assert {"pedro", "sanchez", "marruecos", "ue"} <= e or {"pedro", "sanchez", "marruecos"} <= e
    assert "presidente" not in e and "el" not in e


def test_entities_overlap_por_prefijo():
    assert rules.entities_overlap({"canarias"}, {"canario"})
    assert not rules.entities_overlap({"madrid"}, {"sevilla"})


def test_numbers_normaliza_separadores():
    assert rules.numbers("Mueren 3 personas y 1.200 heridos") == {"3", "1200"}


def test_veto_por_entidades_y_cifras():
    assert rules.veto("Incendio en Tenerife obliga a evacuar", "Incendio en Galicia obliga a evacuar", 0.8, CFG) == "entidades"
    assert rules.veto("Mueren 3 personas en un accidente", "Mueren 5 personas en un accidente", 0.85, CFG) == "cifras"
    # con similitud muy alta no se veta
    assert rules.veto("Mueren 3 personas en un accidente", "Mueren 5 personas en un accidente", 0.97, CFG) is None
    # una cifra compartida (A-6) no oculta el conflicto 3 frente a 5
    assert rules.veto("Mueren 3 personas en la A-6", "Mueren 5 personas en la A-6", 0.85, CFG) == "cifras"
    # una cifra incluida en la otra no es conflicto
    assert rules.veto("Aprueba 5 medidas", "Aprueba 5 medidas y 3 ayudas", 0.85, CFG) is None
    # misma cifra: sin veto
    assert rules.veto("Mueren 3 personas en Lugo", "Tres muertos, 3 en total, en Lugo", 0.85, CFG) is None


def test_is_live():
    assert rules.is_live("Última hora: así te lo contamos en directo")
    assert rules.is_live("Las noticias de hoy, miércoles")
    assert not rules.is_live("El Gobierno aprueba la ley de vivienda")


def test_sensationalism_ordena_titulares():
    sobrio = "El Gobierno aprueba el decreto de ayudas a la vivienda"
    drama = "¡BOMBA! Escándalo brutal en el Gobierno por el decreto"
    assert sensationalism(drama) > sensationalism(sobrio)


def test_pick_headline_evita_el_dramatico_y_prefiere_el_central():
    titles = ["¡ESCÁNDALO! El Gobierno arrasa con el decreto", "El Gobierno aprueba el decreto", "Gobierno aprueba decreto de ayudas"]
    v = np.array([[1, 0], [0.8, 0.6], [0.9, 0.44]], dtype=float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    assert pick_headline(titles, v) in (1, 2)
    assert pick_headline(titles, v) != 0
