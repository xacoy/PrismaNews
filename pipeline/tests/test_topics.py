from conftest import mk

from prisma.groups import editions_for, make_group
from prisma.topics import is_sport, is_sport_group, topics_of_group
import numpy as np


def test_deportes_por_titular():
    for t in ["El Real Madrid golea al Valencia en la jornada de LaLiga",
              "Alcaraz gana en Roland Garros",
              "Fichaje bomba del Barça: el delantero llega en enero",
              "Verstappen domina el Gran Premio de Brasil de Fórmula 1",
              "Triunfo del Granca en la Euroliga de baloncesto"]:
        assert is_sport(mk("Marca", t)), t


def test_deportes_por_url():
    assert is_sport(mk("El País", "Una historia increíble", url="https://elpais.com/deportes/2026-11-10/historia.html"))


def test_no_son_deportes():
    for t in ["El Gobierno aprueba el decreto de vivienda",
              "Valverde, alcalde del municipio, inaugura el centro de salud",
              "Un barco llega con 150 personas a El Hierro",
              "La liga árabe condena el ataque",
              "El Santander gana 2.000 millones hasta septiembre"]:
        assert not is_sport(mk("ABC", t)), t


def test_resumen_solo_con_mucha_evidencia():
    assert not is_sport(mk("ABC", "Dimite el consejero", summary="Dijo que fue un gol de la oposición"))


def test_tecnologia_incluye_videojuegos():
    for t in ["OpenAI presenta un nuevo modelo de inteligencia artificial",
              "Apple lanza el nuevo iPhone con un chip más rápido",
              "Nintendo anuncia el lanzamiento de un nuevo videojuego de Zelda",
              "Nvidia lanza una nueva tarjeta gráfica GeForce",
              "Nuevo tráiler de GTA VI para PlayStation 5 y Xbox"]:
        assert "tecnologia" in topics_of_group([mk("ABC", t)]), t
    assert "tecnologia" not in topics_of_group([mk("ABC", "El Gobierno aprueba el decreto de vivienda")])


def test_politica_y_sucesos_sobre_tecnologia_no_cuentan():
    for t in ["Bruselas multa a Google con 2.000 millones",
              "Un ciberataque paraliza los sistemas del hospital",
              "La IA cambia el trabajo de los programadores",
              "El Gobierno regula las redes sociales para menores",
              "Sánchez y Huawei: polémica por los contratos de las escuchas",
              "TikTok, Instagram y WhatsApp, bajo la lupa de la Fiscalía"]:
        assert "tecnologia" not in topics_of_group([mk("ABC", t)]), t


def test_medio_especializado_cuenta_siempre_y_va_solo_a_su_seccion():
    xa = mk("Xataka", "Cómo elegir un buen router", 2); xa.topic = "tecnologia"
    ge = mk("Genbeta", "Cinco trucos para tu router", 1); ge.topic = "tecnologia"
    assert editions_for([xa, ge]) == ["tecnologia"]
    gen = mk("ABC", "Cinco trucos para tu router", 1)
    assert editions_for([xa, gen]) == ["espana", "tecnologia"]


def test_finanzas():
    for t in ["El Ibex 35 cierra en máximos y la bolsa española sube un 1%",
              "El Euribor baja y abarata la hipoteca",
              "El BCE mantiene los tipos de interés",
              "El bitcoin supera los 100.000 dólares",
              "BBVA y Sabadell: resultados trimestrales y dividendo"]:
        assert "finanzas" in topics_of_group([mk("ABC", t)]), t
    for t in ["Gana el oro olímpico", "El bono social eléctrico se amplía"]:
        assert "finanzas" not in topics_of_group([mk("ABC", t)]), t


def test_grupo_de_varios_temas_y_edicion():
    arts = [mk("ABC", "El Ibex 35 sube con las tecnológicas", 2), mk("El País", "La bolsa española sube con Nvidia", 1)]
    assert editions_for(arts) == ["espana", "tecnologia", "finanzas"]


def test_grupo_deportivo_se_detecta_por_mayoria():
    assert is_sport_group([mk("A", "Real Madrid gana la Champions League"), mk("B", "El Madrid vence en la Champions")])
    assert not is_sport_group([mk("A", "Real Madrid gana la Champions League"), mk("B", "Sube el IPC"), mk("C", "Cierra una fábrica")])


def test_make_group_guarda_las_secciones():
    arts = [mk("ABC", "Sony presenta la PlayStation 6", 2), mk("El País", "Nueva consola PlayStation de Sony", 1)]
    g = make_group("gx", arts, np.ones((2, 4), dtype=np.float32), arts[1].published, 6)
    assert g["editions"] == ["espana", "tecnologia"]
