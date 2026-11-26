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

El código sigue PEP 8 con líneas de hasta 99 caracteres, revisado con [ruff](https://docs.astral.sh/ruff/)
(la configuración está en `pyproject.toml` y las pruebas de GitHub también lo revisan):

```bash
uv run --extra dev ruff format .     # da formato, también a los ejemplos de los docstrings
uv run --extra dev ruff check .      # revisa PEP 8 (reglas E, W y N)
```

Las tablas de códigos del DANE (`CORE_RAW`, `COLUMNAS_IPM`…) están agrupadas a mano entre `# fmt: off` y
`# fmt: on`, para que el formateador no las ponga una por línea.

## Organización del código

```text
src/dane_data/
├── config.py          carpetas de datos (set_paths, variables de entorno, config.json)
├── _io.py             lectura robusta de los archivos del DANE (separador, codificación, coma decimal)
├── stats.py           tablas, medias y cuantiles ponderados
├── referencias.py     salario mínimo, departamentos, diccionarios DDI (data/*.json)
├── proyecciones.py    proyecciones de población del DANE (data/proyecciones_poblacion.parquet)
├── geih/              downloader.py · loader.py · indicadores.py · agregados.py
├── eam/               downloader.py · loader.py · indicadores.py
├── eevv/              downloader.py · loader.py · indicadores.py · agregados.py
├── emicron/           downloader.py · loader.py · indicadores.py
├── ecv/               downloader.py · loader.py · indicadores.py · ipm.py · agregados.py
├── pobreza/           downloader.py · loader.py · indicadores.py · agregados.py · union.py
├── cli.py             comando dane-data
└── app/               aplicación Streamlit (Inicio.py + paginas/)
```

Todo lo que ve el usuario está en español: nombres, docstrings, mensajes y textos de la aplicación. Las
variables armonizadas van en minúscula y las originales del DANE en mayúscula. Los parámetros de las funciones
públicas se llaman igual en todas las encuestas y van en español (`meses`, `columnas`, `modulos`, `raiz`,
`progreso`…), salvo `years`. Los avisos se emiten con
`stats._avisar`, no con `warnings.warn`: así apuntan a la línea de quien llamó, sin ajustar `stacklevel` a mano.

## Pruebas

* `tests/conftest.py` construye carpetas **sintéticas** de la GEIH, la EAM, las Estadísticas Vitales, la EMICRON y la ECV
  con las rarezas de cada época.
  Cuando aparezca una rareza nueva en los archivos del DANE, agréguela a estos datos.
  Las de la pobreza monetaria se arman en `tests/test_pobreza.py` (fixture `pobreza_root`).
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

* Las Estadísticas Vitales se comparan con los cuadros del DANE si hay datos en `$DANE_DATA_TEST_EEVV` o en la carpeta
  configurada. Cuando el DANE publica un año nuevo, agréguelo al descargador (`eevv/downloader.py`) y actualice las cifras:

  ```bash
  uv run --extra app --with xlrd --with msoffcrypto-tool python tests/datos/actualizar_eevv_publicado.py
  uv run --extra app python tests/datos/actualizar_eevv_causas.py
  uv run python tests/datos/actualizar_eevv_diccionario.py
  uv run --extra app python tests/datos/actualizar_proyecciones.py
  ```

* La EMICRON se compara con los anexos del DANE si hay datos en `$DANE_DATA_TEST_EMICRON` o en la carpeta configurada.
  Cuando el DANE publica un año nuevo, agregue su catálogo al descargador (`_CATALOGOS` en `emicron/downloader.py`) y su
  anexo a `ANEXOS`, y actualice las cifras y el diccionario:

  ```bash
  uv run --extra app python tests/datos/actualizar_emicron_publicado.py --cache metodologia/emicron/resultados
  uv run python tests/datos/actualizar_emicron_diccionario.py
  ```

* La ECV y el IPM se comparan con los anexos del DANE si hay datos en `$DANE_DATA_TEST_ECV` o en la carpeta configurada.
  Cuando el DANE publica un año nuevo, agréguelo a `_CATALOGOS` en `ecv/downloader.py`, baje los anexos de series de la ECV
  y de pobreza multidimensional a una carpeta y actualice las cifras y el diccionario:

  ```bash
  uv run --extra app python tests/datos/actualizar_ecv_publicado.py CARPETA_DE_LOS_ANEXOS
  uv run python tests/datos/actualizar_ecv_diccionario.py
  ```

  Las reglas del IPM se infirieron de la base oficial del DANE: `tests/test_ecv.py` las compara hogar por hogar con ella si
  `$DANE_DATA_TEST_IPM` apunta a una carpeta con una subcarpeta por año y, adentro, el CSV de hogares departamental de
  `BDATOS-IPM` (catálogos del IPM en el ANDA). Corra esa prueba al cambiar `ecv/ipm.py` o al agregar un año.

* La pobreza monetaria se compara con los anexos del DANE si hay datos en `$DANE_DATA_TEST_POBREZA` o en la carpeta
  configurada. Cuando el DANE publica un año nuevo, agregue su catálogo a `_CATALOGOS` en `pobreza/downloader.py`, cambie las
  URL de `ANEXOS` en el script y actualice las cifras:

  ```bash
  uv run --extra app python tests/datos/actualizar_pobreza_publicado.py
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
