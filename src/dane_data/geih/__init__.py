"""Gran Encuesta Integrada de Hogares (GEIH) — mercado laboral, microdatos de personas."""

from __future__ import annotations

from typing import Iterable

from .. import config
from .downloader import (DEFAULT_MODULES, EMPALME_CATALOGS, KNOWN_CATALOGS, MODULE_PATTERNS,
                         GEIHDownloader)
from .agregados import (POBLACIONES, POR_PRECALCULADOS, VARIABLES_INDICADORES, exportar, filtrar, serie_frecuencias,
                        serie_indicadores, serie_tabla, tabla_de_frecuencias)
from .indicadores import GLOSARIO, indicadores
from .loader import (CATEGORIAS, CONDICIONES, CORE_RAW, GRUPOS_EDAD, MARCOS, MODULOS, NIVELES_EDUC, available,
                     clear_cache, find_months, harmonize, load, load_month, marco_muestral)

ANIOS_DISPONIBLES = sorted(int(y) for y in KNOWN_CATALOGS)
ANIOS_EMPALME = sorted(int(y) for y in EMPALME_CATALOGS)


def download(
    years: Iterable[int] | int | None = None,
    modules: Iterable[str] | None = None,
    empalme: bool = False,
    root=None,
    delete_zips: bool = False,
    limit_files: int | None = None,
    progress=None,
    should_stop=None,
) -> None:
    """
    Descarga microdatos GEIH del ANDA (DANE) a la carpeta configurada.

    >>> dd.geih.download([2024, 2025])                    # serie principal
    >>> dd.geih.download(2016, empalme=True)              # serie de empalme
    >>> dd.geih.download(2025, limit_files=1)             # solo enero (prueba)

    ``modules`` acepta: vivienda, caracteristicas, fuerza_trabajo, ocupados,
    desocupados, inactivos, otras_formas_trabajo (por defecto todos).
    Es incremental: los meses ya extraídos se saltan.
    """
    if isinstance(years, (int, str)):
        years = [years]
    root = root or config.get_path("geih_empalme" if empalme else "geih")
    dl = GEIHDownloader(
        base_dir=root,
        keep_zips=not delete_zips,
        extract_csv=True,
        is_empalme=empalme,
        modules=modules,
        progress=progress,
        should_stop=should_stop,
    )
    dl.run_pipeline(target_years=years, limit_files=limit_files)


__all__ = [
    "download", "load", "load_month", "available", "find_months", "harmonize", "indicadores",
    "serie_indicadores", "serie_tabla", "serie_frecuencias", "tabla_de_frecuencias", "exportar", "filtrar",
    "POBLACIONES", "marco_muestral", "MARCOS", "clear_cache", "GLOSARIO", "MODULOS", "CORE_RAW", "CONDICIONES", "NIVELES_EDUC",
    "GRUPOS_EDAD", "CATEGORIAS", "VARIABLES_INDICADORES", "POR_PRECALCULADOS",
    "ANIOS_DISPONIBLES", "ANIOS_EMPALME", "MODULE_PATTERNS", "DEFAULT_MODULES",
]
