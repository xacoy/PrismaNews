import json

from prisma import evaluate as ev


def test_metrics_ponderadas():
    y, p, w = [1, 1, 0, 0], [1, 0, 1, 0], [1, 1, 1, 1]
    m = ev.metrics(y, p, w)
    assert m["precision"] == 0.5 and m["recall"] == 0.5 and abs(m["f1"] - 0.5) < 1e-9
    # un falso positivo que pesa 3 veces más baja la precisión
    m = ev.metrics(y, p, [1, 1, 3, 1])
    assert abs(m["precision"] - 0.25) < 1e-9


def test_pesos_por_tramo(tmp_path):
    bins = tmp_path / "b.json"
    bins.write_text(json.dumps({"bins": [[0.9, 1, 10], [0.8, 0.9, 40]]}))
    pairs = [{"bin": 0}, {"bin": 1}, {"bin": 1}]
    assert ev.load_bin_weights(pairs, str(bins)) == {0: 10.0, 1: 20.0}


def test_sweep_con_fake_y_recomendacion(fake, tmp_path):
    pairs = [
        {"id": "a", "bin": 0, "label": 1, "a": {"source": "A", "title": "Sánchez anuncia plan de vivienda para jóvenes"},
         "b": {"source": "B", "title": "Plan de vivienda de Sánchez para jóvenes"}},
        {"id": "b", "bin": 0, "label": 0, "a": {"source": "A", "title": "Erupción en La Palma"},
         "b": {"source": "B", "title": "Final de la Copa del Rey en Sevilla"}},
    ]
    rows = ev.sweep(pairs, fake, {"entity_veto_below": 0.88, "number_veto_below": 0.93, "exclude_live": True})
    best = ev.recommend(rows, "cluster+reglas", 0.95)
    assert best is not None and best["cluster+reglas"]["precision"] >= 0.95
