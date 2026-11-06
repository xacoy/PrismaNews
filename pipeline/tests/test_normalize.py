from datetime import datetime, timezone

from prisma.models import Article
from prisma.normalize import (article_id, canonical_url, clean_summary, clean_text,
                              clean_title, dedupe, title_key, with_ref)


def art(i, source, title, url, h=0):
    return Article(id=article_id(url), source=source, scope="nacional", title=title, url=canonical_url(url),
                   published=datetime(2026, 11, 5, 10 + h, tzinfo=timezone.utc))


def test_clean_text_quita_html_y_entidades():
    assert clean_text("<p>Hola&nbsp;<b>mundo</b> &amp; más</p>\n") == "Hola mundo & más"


def test_clean_summary_trunca_en_palabra():
    s = clean_summary("palabra " * 100, limit=50)
    assert len(s) <= 51 and s.endswith("…") and "palabr…" not in s


def test_clean_summary_vacio_es_none():
    assert clean_summary("  <p> </p> ") is None


def test_clean_title_quita_sufijo_del_medio():
    assert clean_title("Sube el paro | El País", "El País") == "Sube el paro"
    assert clean_title("Sube el paro - elDiario.es", "elDiario.es") == "Sube el paro"
    assert clean_title("El País gana el premio", "El País") == "El País gana el premio"


def test_canonical_url_quita_seguimiento_y_fragmento():
    u = "HTTPS://WWW.Ejemplo.es/a/b.html?utm_source=x&id=3&fbclid=zz#c"
    assert canonical_url(u) == "https://www.ejemplo.es/a/b.html?id=3"


def test_with_ref_anade_ref_una_sola_vez():
    assert with_ref("https://e.es/a") == "https://e.es/a?ref=prisma"
    assert with_ref("https://e.es/a?id=1") == "https://e.es/a?id=1&ref=prisma"
    assert with_ref("https://e.es/a?ref=otro&id=1") == "https://e.es/a?id=1&ref=prisma"


def test_title_key_ignora_acentos_mayusculas_y_signos():
    assert title_key("¡Sánchez, ANUNCIA…!") == title_key("sanchez anuncia")


def test_dedupe_misma_url_y_mismo_titular_mismo_medio():
    a = art(1, "A", "Titular uno", "https://a.es/1")
    b = art(2, "A", "Titular uno", "https://a.es/1?utm_source=x", 1)      # misma URL canónica
    c = art(3, "A", "TITULAR  uno!", "https://a.es/otra", 2)              # mismo titular, mismo medio
    d = art(4, "B", "Titular uno", "https://b.es/1", 3)                    # otro medio: se conserva
    out = dedupe([d, c, b, a])
    assert [x.source for x in out] == ["A", "B"]
    assert out[0].published < out[1].published
