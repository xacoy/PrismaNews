# Evaluación de la agrupación

Conjunto: `tests/fixtures/pairs.jsonl`, 140 pares de titulares reales (6 nov 2026) de medios distintos, etiquetados a mano
(76 «mismo asunto», 64 «distinto»). Se tomaron por **muestreo estratificado** según la similitud coseno (7 tramos, de 0,55 a 1,0),
porque los pares realmente parecidos son rarísimos frente al total. `tests/fixtures/pairs_bins.json` guarda cuántos pares
había en cada tramo para **ponderar** y estimar precisión y cobertura sobre la población completa (los pares por debajo de
0,55 no se muestrearon y se asumen «distintos»).

Reproducir: `python scripts/eval_threshold.py` (necesita el modelo; corre en el workflow *Evaluación de la agrupación*).

## Configuración final (`config/clustering.yml`)

| Parámetro | Valor |
|---|---|
| modelo | `paraphrase-multilingual-MiniLM-L12-v2` (ONNX vía fastembed) |
| enlace | average (distancia coseno) |
| umbral de similitud | 0,72 |
| bonus por entidades compartidas | 0,20 (máx. con 3 entidades) |
| titulares de menos de 5 palabras | solo si similitud ≥ 0,95 |

**Resultado (ponderado):** precisión 0,983 · cobertura 0,697 · F1 0,816.
**Sin ponderar (sobre los 140 pares):** precisión 0,971 · cobertura 0,895 · F1 0,932. Errores: 2 falsos positivos, 8 falsos negativos.

## Cómo se llegó ahí

| Variante (enlace medio) | Precisión pond. | Cobertura pond. |
|---|---|---|
| Solo coseno, umbral 0,78 (inicial, a ojo) | 0,89 | 0,29 |
| Cluster + reglas, umbral 0,78 | 0,99 | 0,22 |
| Cluster + reglas, mejor umbral (0,72) | 0,97 | 0,41 |
| + bonus de entidades 0,10, umbral 0,70 | 0,95 | 0,71 |
| + bonus de entidades 0,20, umbral 0,72 (final) | 0,98 | 0,70 |

El enlace `single` con bonus 0,05–0,10 daba ~0,76 de cobertura con precisión 0,96, pero encadena grupos distintos en
producción y este conjunto de pares no puede detectarlo; se descartó.

## Limitaciones

- Muestra pequeña y un solo día de noticias. El umbral y el bonus se eligieron **sobre esta misma muestra** (sin conjunto de
  validación aparte), así que las cifras son optimistas.
- La evaluación es por pares; en producción un grupo grande puede encadenar errores que aquí no se ven.
- El criterio «mismo asunto» es estricto (mismo hecho concreto); reportajes del mismo tema se etiquetaron como «distinto».
- No se evalúa todavía la ventana de 14 días ni la estabilidad de ids más allá de las pruebas automáticas.
