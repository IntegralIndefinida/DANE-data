# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`dane-data` (package `src/dane_data`) downloads, loads, harmonizes and analyzes DANE microdata for Colombia: the household survey **GEIH** (2007–2026, plus the 2010–2020 "empalme" series) and the manufacturing survey **EAM** (1992–2024). It ships as a Python library (`import dane_data as dd`), a CLI (`dane-data`), and a Streamlit app for students.

Everything user-facing is in **Spanish**: identifiers, docstrings, comments, log messages, CLI help and UI text (`anio`, `mes`, `cargar_geih`, `faltantes`…). Keep new code in Spanish too.

## Commands

The project uses `uv` (`uv.lock`, Python 3.12 in `.python-version`; `requires-python >= 3.10`).

```bash
uv run --extra dev --extra app pytest -q                       # full suite (same as CI)
uv run --extra dev pytest tests/test_geih.py::test_classify_file -q   # a single test
uv run --extra dev pytest -k cache -q                          # by keyword

uv run --extra app dane-data app                # Streamlit app (opens the browser)
uv run --extra app dane-data app --no-browser
uv run dane-data estado                         # configured paths + downloaded years/months
uv run dane-data descargar geih --anios 2025 --limite 1   # real download, 1 month only
```

No linter or formatter is configured.

## Architecture

### Two surveys with the same shape

`geih/` and `eam/` each have `downloader.py` → `loader.py` → `indicadores.py`. Each `__init__.py` re-exports the public API and defines a `download()` wrapper that resolves the target folder through `config.get_path()` and builds the downloader class. The top-level `__init__.py` re-exports the shared helpers (`tabla`, `set_paths`, `SMLV`, `buscar_variable`…).

### Data location (`config.py`)

On disk: GEIH at `<root>/datos_csv/<año>/<carpeta-mes>/*.csv`, EAM at `<root>/datos/<año>/*.csv|*.txt`. Each root (`geih`, `geih_empalme`, `eam`) is resolved in this order: `set_paths()` in the session → env vars `DANE_DATA_GEIH` / `DANE_DATA_GEIH_EMPALME` / `DANE_DATA_EAM` → `~/.config/dane_data/config.json` → `~/dane_data_datos/`. Every loader/downloader also takes an explicit `root=`, and the tests rely on that.

### GEIH loading pipeline (`geih/loader.py`)

1. `find_months` walks year/month folders. Month names are parsed from messy folder names (`month_from_folder`), and files are found with `rglob` because some DANE ZIPs nest folders.
2. `classify_file` maps each DANE filename to a logical module (`caracteristicas`, `fuerza`, `ocupados`, `no_ocupados`, `otras`, `vivienda`) and a domain (`area`/`cabecera`/`resto`). `_pick_files` builds the national total as **Cabecera + Resto**. Area is a subset of Cabecera and must never be added.
3. `MesGEIH.faltantes` checks whether the modules needed for the labor indicators are present. Before 2022 and in 2020/empalme, the OCI/DSI/INI flags may come from the characteristics header instead. `load()` skips incomplete months with a warning and records them in `df.attrs["meses_omitidos"]`.
4. `load_month` reads the modules with `_io.read_table` and left-merges them onto `caracteristicas`, using the person keys (`DIRECTORIO, SECUENCIA_P, ORDEN`) or the household keys for `vivienda`. Older years have no OCI/DSI flags, so `_markers` adds temporary `_EN_OCU`/`_EN_DSI`/… columns that mark which file a row came from.
5. Each month is cached as parquet under `~/.cache/dane_data/geih/`. `harmonize()` runs **after** the cache, on the concatenated frame. The cache key covers file size and mtime, the extra columns, the modules and `_HARMONIZE_VERSION`. **Bump `_HARMONIZE_VERSION` whenever `load_month`'s output changes** (`CORE_RAW`, `read_table`, merge or marker logic), or stale caches will be served.

Column convention: **lowercase = harmonized** variables created by dane-data (`fex`, `sexo`, `condicion`, `formal`, `ingreso_laboral`…), **UPPERCASE = original DANE** variables. EAM is all lowercase and gets `ciiu`, `ciiu_rev`, `division`, `sector` and `departamento` from the many CIIU variable names used across years.

`_io.read_table` detects the separator (`; , \t |`), the encoding (UTF-8-sig/Latin-1), decimal commas, and blank `" "` cells. Use it for every DANE file read.

### Weighting

`fex` is a **monthly** expansion factor. When several months are pooled, levels must be monthly averages, as DANE publishes them. `stats.peso_mensual_promedio` divides `fex` by the number of distinct months per year, and `stats.tabla` and `geih.indicadores` use it. Keep this in mind for any new aggregate.

### Downloaders

They scrape DANE's ANDA portal with requests and BeautifulSoup. `KNOWN_CATALOGS` / `EMPALME_CATALOGS` (GEIH) and `EAM_KNOWN_CATALOGS` map each year to its ANDA catalog id and serve as the fallback for dynamic discovery. **A new survey year needs its catalog id added there**, plus a new entry in `referencias.SMLV`.

Downloads are incremental. A `.dane_data_ok` marker (`MARCADOR`) is written after a successful extraction and records which modules were requested. It only lets a folder be skipped if it covers the modules being requested now. Otherwise, and for older markers that don't record modules, the folder is checked with `faltantes_mes`, which reuses the loader's `_pick_files`/`MesGEIH`. Both downloaders inherit `_hooks.ProgressMixin`: the `progress(fraction, msg)` and `should_stop()` callbacks drive the app's progress bar and cancel button (by raising `DownloadCancelled`).

### Streamlit app (`app/`)

- `dane-data app` (`cli._cmd_app`) starts `streamlit run app/Inicio.py` as a headless subprocess with `cwd=app/`, so that `app/.streamlit/config.toml` is read. It picks a free port and opens the browser once `/_stcore/health` responds.
- `Inicio.py` registers the pages in `paginas/` through `st.navigation`. A new page must be added there.
- `_ui.py` contains the shared sidebar selectors `selector_geih`/`selector_eam`. They return `(df, descripcion, params)`, where `params["carga"]` is a **Python code string** that reproduces the load and filters. Pages show it via `codigo()` ("código Python equivalente"), so update these strings whenever the library API changes.
- Loads are cached with `st.cache_resource`/`st.cache_data`, keyed on `rutas_actuales()`, so changing a data folder triggers a reload. Charts go through `linea`/`barras`/`grafico`, which apply the fixed palette `PALETA` and Spanish number formatting. Tables are exported to CSV/Excel/Stata with `botones_descarga`.
- `pyproject.toml` `package-data` globs decide which non-package files get installed (`data/*.json`, `app/**/*.py`, `.streamlit/*.toml`). Extend them for any new asset type.

### Reference data

`referencias.py` holds `SMLV` (minimum wage by year), `DEPARTAMENTOS` and `MESES`. `data/geih_diccionario.json` and `data/eam_diccionario.json` are the official DDI dictionaries behind `buscar_variable`/`describir`.

## Tests

- `tests/conftest.py` builds **synthetic** GEIH and EAM trees that reproduce each era's quirks: Area/Cabecera/Resto, `;` with decimal comma, Latin-1, nested `CSV 13/` folder, an incomplete month, `.txt` tab-separated EAM. When supporting a new DANE file quirk, add it to these fixtures.
- `tests/test_downloader.py` subclasses `GEIHDownloader` and `EAMDownloader` (`FakeDownloader`, `FakeEAMDownloader`) and feeds them in-memory ZIPs. Tests never hit the network.
- `tests/test_app.py` drives app pages with `streamlit.testing.v1.AppTest`, pointing the data paths to `tmp_path` and replacing `dd.*.download`. It is skipped when the `app` extra is not installed.
- `test_real_td_matches_dane` checks the computed unemployment rate against DANE's published figures. It runs only if real GEIH data exists at `$DANE_DATA_TEST_GEIH` or the configured `geih` path, and is skipped otherwise.

## Release

Pushing a `v*` tag triggers `.github/workflows/release.yml`. The workflow runs the tests, builds `dane-data-<ver>.zip` with `git archive`, and creates a GitHub Release using `.github/NOTAS_RELEASE.md` as the notes. What goes into the zip is controlled by `export-ignore` in `.gitattributes`. Bump the version in **both** `pyproject.toml` and `src/dane_data/__init__.py` (`__version__`) before tagging.

The student launchers (`abrir-dane-data.sh`, `Abrir dane-data (Mac).command`, `Abrir dane-data (Windows).bat`) install `uv` if it is missing, then run `uv run --extra app dane-data app`. `.gitattributes` forces CRLF line endings for `.bat` and LF for `.sh`/`.command`; keep it that way.
