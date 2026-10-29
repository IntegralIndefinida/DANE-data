# Desarrollo

`dane-data` es software libre (MIT). Los errores y las propuestas se reportan en
[GitHub](https://github.com/IntegralIndefinida/DANE-data/issues).

## Entorno

El proyecto usa [uv](https://docs.astral.sh/uv/):

```bash
git clone https://github.com/IntegralIndefinida/DANE-data
cd DANE-data
uv run --extra dev --extra app pytest -q      # todas las pruebas
uv run --extra app dane-data app              # la aplicación con el código local
```

## Organización del código

```text
src/dane_data/
├── config.py          carpetas de datos (set_paths, variables de entorno, config.json)
├── _io.py             lectura robusta de los archivos del DANE (separador, codificación, coma decimal)
├── stats.py           tablas, medias y cuantiles ponderados
├── referencias.py     salario mínimo, departamentos, diccionarios DDI (data/*.json)
├── geih/              downloader.py · loader.py · indicadores.py · agregados.py
├── eam/               downloader.py · loader.py · indicadores.py
├── cli.py             comando dane-data
└── app/               aplicación Streamlit (Inicio.py + paginas/)
```

Todo lo que ve el usuario está en español: nombres, docstrings, mensajes y textos de la aplicación. Las
variables armonizadas van en minúscula y las originales del DANE en mayúscula.

## Pruebas

* `tests/conftest.py` construye carpetas **sintéticas** de la GEIH y la EAM con las rarezas de cada época.
  Cuando aparezca una rareza nueva en los archivos del DANE, agréguela a estos datos.
* Las pruebas de los descargadores usan ZIP en memoria: nunca se conectan a internet.
* GitHub Actions (`.github/workflows/pruebas.yml`) corre todas las pruebas en cada push a `main` y en cada
  pull request, con Python 3.10 (pandas 2) y 3.12 (las versiones de `uv.lock`).
* `tests/test_docs.py` revisa que la referencia de la API cubra todo `__all__` y ejecuta los ejemplos de los
  docstrings (los que necesitan microdatos llevan `# doctest: +SKIP`).
* Si hay datos reales en `$DANE_DATA_TEST_GEIH`, `$DANE_DATA_TEST_GEIH_EMPALME` o en las carpetas
  configuradas, las pruebas comparan cada mes con las cifras publicadas por el DANE
  (`tests/datos/dane_publicado.csv`, vea {doc}`guia/validacion`). Cuando el DANE publica meses nuevos:

  ```bash
  uv run --extra app python tests/datos/actualizar_publicado.py sep2026
  ```

## Documentación

```bash
uv run --extra docs sphinx-build -W -b html docs docs/_build/html
```

* Los docstrings siguen el estilo de NumPy con las secciones en español (`Parámetros`, `Devuelve`,
  `Véase también`, `Notas`, `Ejemplos`).
* Las páginas de `docs/api/` listan cada función pública; `tests/test_docs.py` falla si falta alguna.
* Los notebooks (primeros pasos y ejemplos) se publican con sus salidas, porque el servidor de la
  documentación no tiene los microdatos. Después de cambiar uno, o cuando haya datos nuevos, vuelva a
  ejecutarlos con los datos locales:

  ```bash
  uv run --extra docs python docs/ejecutar_notebooks.py
  ```

  El script también actualiza las miniaturas de la galería (`docs/_static/galeria/`).
* La documentación se publica sola en GitHub Pages con cada cambio en `main`.

## Diferencias con la documentación del DANE

Cuando los datos contradicen lo que publica el DANE (diccionarios, etiquetas, notas metodológicas):

1. Se sigue a los datos, después de verificarlo con los datos reales o en el ANDA.
2. Se agrega una fila a la tabla de {doc}`guia/diferencias` (en el README), con lo que dice el ANDA, lo que
   muestran los datos, lo que hace `dane-data` y los años afectados.
3. Los diccionarios de `data/*.json` se dejan como los publica el DANE.
4. Se deja un comentario en el código donde se aparta de la documentación.

## Publicar una versión

1. Actualice la versión en `pyproject.toml`, en `src/dane_data/__init__.py` y en `CITATION.cff` (con
   `date-released`), y corra `uv lock`.
2. Escriba las notas en `.github/NOTAS_RELEASE.md` y en {doc}`novedades`.
3. `git tag vX.Y.Z && git push origin vX.Y.Z`.

El flujo de GitHub Actions corre las pruebas, compila el lanzador de Windows, publica el paquete en PyPI
y crea la versión en GitHub con el zip para estudiantes, `dane-data.zip`. El zip no trae el código: lleva
los lanzadores y `estudiantes/pyproject.toml`, con un `uv.lock` que instala desde PyPI la versión recién
publicada (por eso se arma después). El nombre es fijo para que
`https://github.com/IntegralIndefinida/DANE-data/releases/latest/download/dane-data.zip` sea siempre la última.

### El lanzador de Windows

`Abrir dane-data.exe` es un programa corto en C (`lanzador/lanzador.c`) que hace lo mismo que el `.bat`.
`lanzador/compilar.sh` lo compila desde Linux o macOS con zig, que uv descarga de PyPI; la versión del
ejecutable sale de `pyproject.toml`. Para probarlo sin Windows sirve [Wine](https://www.winehq.org).

El release lo firma con [SignPath](https://signpath.org) (certificado gratuito de SignPath Foundation para
proyectos de código abierto) cuando el repositorio tiene la variable `SIGNPATH_ORGANIZATION_ID` y el
secreto `SIGNPATH_API_TOKEN`; sin ellos el `.exe` va sin firmar. Si el proyecto o la política de firma de
SignPath no se llaman `dane-data` y `release-signing`, defina también `SIGNPATH_PROJECT_SLUG` y
`SIGNPATH_POLICY_SLUG`. La configuración del artefacto en SignPath es `lanzador/signpath.xml`. Cada firma
se aprueba a mano en signpath.io mientras el release espera (hasta una hora).
