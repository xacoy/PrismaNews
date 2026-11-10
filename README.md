# PrismaNews
Web de noticias personal

---

# Prisma

Agregador de noticias en español al estilo de Ground News: **agrupa los titulares de distintos medios que hablan de lo mismo** y muestra qué medios cubren cada noticia y cómo la titulan. Prisma **no etiqueta ni juzga a los medios** (sin orientación política ni puntuaciones de fiabilidad).

- Ediciones **España** y **Canarias**, y secciones temáticas **Tecnología** (incluye videojuegos; además de la prensa general usa medios especializados marcados con `topic: tecnologia` en `config/candidates.yml`) y **Finanzas**. Las **noticias deportivas se excluyen** del pipeline. Los temas y los deportes se deciden por listas de términos en `pipeline/prisma/topics.py` (titular, resumen y sección de la URL); si falta o sobra alguno, se edita ahí y se ejecutan las pruebas.
- La edición de Canarias son las noticias **que hablan de Canarias** (por contenido, no por el medio que las publica): se mira si algún titular o resumen del grupo menciona una isla, un municipio, una institución, un equipo o un asunto canario. La lista de términos está en `pipeline/prisma/canarias.py` (`TERMS`, con sus falsos amigos en `EXCLUDE`); si falta alguno, se añade ahí y se ejecutan las pruebas. Para revisar la regla sobre los datos publicados: workflow *Informe edición Canarias (puntual)*.
- Solo RSS/Atom públicos. Se guarda titular, enlace, medio, fecha, autor y resumen corto del feed; nunca el cuerpo. Todos los enlaces salen al original con `?ref=prisma`.
- **Coste cero**: Python + modelo de embeddings local (ONNX), web estática Astro, GitHub Actions (repo público: minutos gratis e ilimitados) y GitHub Pages. Sin APIs de pago.

## Cómo está montado

```
config/sources.yml       medios verificados (nombre, URL, ámbito, estado)
config/candidates.yml    candidatos a feed, de donde sale sources.yml
config/clustering.yml    umbral, ventana de 48 h, reglas, enlace del clustering
pipeline/prisma/         recogida, normalización, embeddings, clustering, reglas, titular, histórico
pipeline/tests/          pruebas (pytest)
tests/fixtures/          feeds de ejemplo y 140 pares de titulares etiquetados a mano
scripts/                 check_sources.py, eval_threshold.py, make_candidates.py, make_icons.cjs
web/                     Astro + TypeScript + Tailwind (salida 100 % estática, PWA)
docs/evaluacion.md       cifras de precisión y cobertura de la agrupación
.github/workflows/       pipeline.yml (actualizar y publicar) y workflows puntuales de comprobación
```

Cada ejecución recoge los feeds, agrupa en una ventana móvil de 48 h, fusiona con el histórico, valida, compila la web y publica. El histórico de 14 días **no se guarda en git**: cada ejecución descarga `data/groups.json` y `data/pool.json` ya publicados en el sitio, los combina con lo nuevo, recorta lo que pasa de 14 días y vuelve a publicar (con copia de respaldo en la caché de Actions y sin desplegar si no se puede recuperar el histórico).

## Ejecutarlo en local

Necesita Python 3.12 o superior y Node 22 o superior.

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r pipeline/requirements-dev.txt
```

```bash
python -m pytest -q
```

Generar datos reales (descarga los feeds y el modelo la primera vez, unos 220 MB):

```bash
PYTHONPATH=pipeline python -m prisma.run --out-dir web/public/data && PYTHONPATH=pipeline python -m prisma.validate web/public/data
```

Ver la web (sin datos reales usa una muestra en `web/src/data/sample-groups.json`):

```bash
cd web && npm ci && npm run dev
```

Compilar y previsualizar como en producción, bajo `/PrismaNews/` (útil para probar la PWA):

```bash
cd web && npm run build && npm run preview
```

Medir la agrupación con los pares etiquetados (necesita el modelo):

```bash
python scripts/eval_threshold.py --min-precision 0.95
```

## Añadir una fuente nueva

1. Añade una línea a `config/candidates.yml` con `name`, `scope` (`nacional` o `canario`), `home` y una o varias URLs en `feeds` (se prueban en orden y se usa la primera que responde). No inventes URLs: si no la conoces, busca el icono RSS de la web o `<link rel="alternate" type="application/rss+xml">` en su portada.
2. Comprueba los feeds y regenera la lista (hace una petición real a cada uno, respeta `robots.txt` y descarta los que no respondan, estén vacíos o inactivos más de 72 h):

```bash
python scripts/check_sources.py config/candidates.yml config/sources.yml
```

3. Revisa `config/sources.yml` (`status: activo` o `descartado`, con el motivo) y ejecuta las pruebas. Si no tienes salida a internet, haz push y el workflow *Comprobar fuentes (puntual)* lo ejecuta en GitHub y muestra el resultado en el log.
4. Un medio que devuelve 406/403 a clientes automáticos o prohíbe la ruta en `robots.txt` **no se añade**: Prisma se identifica como `PrismaBot` y no esconde su identidad.

## Publicar en GitHub Pages (pasos que debe hacer usted)

Ya está publicado y programado (cada 2 horas). Para repetirlo desde cero en otro repositorio:

1. Fusione la rama de trabajo en `main` (el despliegue solo corre en `main`).
2. En GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions** (si estuviera en «Deploy from a branch», cámbielo).
3. **Actions → «Prisma (actualizar y publicar)» → Run workflow** sobre `main`. La primera vez no hay histórico y empieza de cero.
4. El bloque `schedule` de `.github/workflows/pipeline.yml` (`17 */2 * * *`) ya lo programa cada 2 horas; para pausarlo, coméntelo.

La URL será `https://xacoy.github.io/PrismaNews/`. El workflow mide el tiempo de cada paso y lo deja en el resumen de cada ejecución. Medido en GitHub Actions (6 nov 2026, 20 feeds, ~1.300 titulares): **~50 s por ejecución en régimen normal** (el pipeline en sí, 9,5 s: los vectores de los titulares ya vistos se guardan en la caché de Actions y solo se calculan los nuevos) y 95–120 s en frío (primera ejecución o caché caducada; ahí los embeddings tardan unos 48 s). El sitio pesa ~0,8 MB. Aviso: en repos públicos GitHub **desactiva los workflows programados tras 60 días sin actividad** en el repositorio; un push de vez en cuando lo evita (si se desactiva, se reactiva a mano en Actions).

## Límites de los servicios gratuitos que condicionan el diseño

| Servicio | Límite | Cómo nos afecta |
|---|---|---|
| GitHub Actions (repo público) | runners estándar gratis e ilimitados | el repo debe seguir público |
| Caché de Actions | 10 GB por repo; se borra lo no usado en 7 días | el modelo (~220 MB) cabe y se mantiene caliente con ejecuciones cada 2 h |
| GitHub Pages | sitio ≤ 1 GB; 100 GB/mes de ancho de banda (blando); despliegue ≤ 10 min; el límite de 10 builds/hora no aplica con workflow propio | la web pesa unos pocos MB |
| Hugging Face | 3.000 peticiones de descarga cada 5 min por IP (anónimo) | solo se descarga el modelo cuando caduca la caché |

## Calidad de la agrupación y límites

Resumen en [`docs/evaluacion.md`](docs/evaluacion.md): sobre 140 pares reales etiquetados a mano, con el umbral y las reglas actuales, precisión estimada ≈ 0,98 y cobertura ≈ 0,70. Son cifras optimistas (muestra pequeña, umbral ajustado sobre la misma muestra). La página «Cómo funciona» de la web explica la metodología y los errores posibles.
