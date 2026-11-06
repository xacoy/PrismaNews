from conftest import mk

from prisma.canarias import canary_hits, is_canary_group


def test_detecta_topónimos_e_instituciones():
    assert canary_hits("Un fallecido entre los más de 1.000 migrantes rescatados en Canarias")
    assert canary_hits("Detenido en La Laguna por apuñalar a un vecino")
    assert canary_hits("Ramírez y los capitanes de la UD Las Palmas acudirán al homenaje")
    assert canary_hits("El Cabildo de Lanzarote aprueba el presupuesto")
    assert canary_hits("Llega un cayuco con 150 personas a El Hierro")
    assert canary_hits("TENERIFE: alerta por lluvias")          # mayúsculas
    assert canary_hits("Alerta amarilla en Fuerteventura")


def test_falsos_amigos_no_cuentan():
    assert not canary_hits("Fallece Julio Díaz, exconcejal del PSOE en La Palma del Condado")
    assert not canary_hits("Concierto en Palma de Mallorca")
    assert not canary_hits("El hierro y el acero suben en bolsa")
    assert not canary_hits("Santa Cruz de Mudela: tractorada")


def test_noticias_nacionales_no_cuentan():
    for t in ["La Fiscalía Europea abre una investigación por un posible fraude en el AVE tras la tragedia de Urda",
              "La Policía lanza una operación contra el grupo neonazi Núcleo Nacional",
              "El Gobierno decreta la retirada del 12% de la producción de aceite de oliva",
              "La Junta Electoral vuelve a permitir el uso del DNI digital para votar"]:
        assert not canary_hits(t), t


def test_ambiguos_solo_con_mayuscula_de_nombre_propio():
    assert canary_hits("Llegan 30 migrantes a El Hierro")
    assert not canary_hits("Sube el hierro en los mercados")
    assert not canary_hits("Valverde marca el gol del Real Madrid")          # futbolista, no el municipio
    assert not canary_hits("Candelaria Delgado reclama explicaciones")        # nombre de persona


def test_grupo_canario_por_cualquier_articulo_aunque_sea_nacional():
    nac = mk("El País", "La borrasca Bruna deja lluvias en Canarias", 2)
    assert is_canary_group([nac, mk("ABC", "La borrasca Bruna llega a España", 1)])


def test_grupo_nacional_cubierto_por_medio_canario_no_cuenta():
    g = [mk("Canarias7", "La Fiscalía Europea investiga fraude en el AVE", 2, scope="canario"),
         mk("El País", "La Fiscalía Europea investiga un fraude en la alta velocidad", 1)]
    assert not is_canary_group(g)


def test_resumen_tambien_cuenta():
    a = mk("ABC", "Accidente de tráfico con dos heridos", 1, summary="Ocurrió en la GC-1, en Gran Canaria")
    assert is_canary_group([a])
