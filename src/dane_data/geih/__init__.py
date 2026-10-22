"""Gran Encuesta Integrada de Hogares (GEIH) — mercado laboral, microdatos de personas."""

from __future__ import annotations

import numbers
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
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de la GEIH del ANDA del DANE.

    Baja los ZIP mensuales de cada año y extrae los módulos en
    ``<carpeta>/datos_csv/<año>/<mes>/``. Es incremental: los meses que ya están completos se saltan, así
    que se puede interrumpir y volver a correr.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` descarga todos los de la serie (``ANIOS_DISPONIBLES``, o
        ``ANIOS_EMPALME`` con ``empalme=True``); una lista vacía, ninguno. Los años que no están en el
        ANDA se ignoran con un aviso.
    modules
        Módulo o lista de módulos a extraer, con los nombres de ``DEFAULT_MODULES``: ``vivienda``,
        ``caracteristicas``, ``fuerza_trabajo``, ``ocupados``, ``desocupados``, ``inactivos``,
        ``otras_formas_trabajo``. Por defecto, todos.
    empalme
        Descargar la serie de empalme (2010–2020, con proyecciones del CNPV 2018) en vez de la principal.
    root
        Carpeta de destino. Por defecto, la de ``dd.get_path("geih")`` o ``dd.get_path("geih_empalme")``.
    delete_zips
        Borrar cada ZIP después de extraerlo. Por defecto se conservan.
    limit_files
        Máximo de meses por año; útil para probar con uno solo.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance (``fraccion`` entre 0 y 1, o None).
    should_stop
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.
    forzar
        Volver a bajar y extraer aunque ya esté en disco, por ejemplo si el DANE corrigió los archivos. Lo
        nuevo se extrae aparte y reemplaza los archivos de los ``modules`` pedidos solo si salió completo;
        los de otros módulos, y todo si algo falló, quedan como estaban.

    Devuelve
    --------
    list[str]
        Lo que no se pudo descargar o extraer, con el año y el motivo; vacía si todo salió bien. Al volver
        a descargar los mismos años, lo que ya está completo se salta y se reintenta lo demás.

    Lanza
    -----
    DownloadCancelled
        Si ``should_stop()`` devolvió True.
    ValueError
        Si ``modules`` está vacío o tiene un nombre que no es de ``DEFAULT_MODULES``.

    Véase también
    -------------
    available : Qué meses hay en disco y si están completos.
    load : Cargar lo descargado.
    dane_data.eam.download : Descargar la EAM.

    Notas
    -----
    En algunos meses los CSV que publica el ANDA están dañados (2008 y 2011: el factor de expansión sin
    punto decimal; septiembre de 2021: separado por espacios). Para esos meses se baja otro formato del
    mismo catálogo (TXT o Stata). Un año extraído ocupa unos 500 MB en disco, más los ZIP si se
    conservan.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> fallidos = dd.geih.download([2024, 2025])  # doctest: +SKIP
    >>> fallidos  # doctest: +SKIP
    []
    >>> dd.geih.download(2016, empalme=True)  # doctest: +SKIP
    >>> dd.geih.download(2025, limit_files=1)  # solo enero, para probar  # doctest: +SKIP
    >>> dd.geih.download(2024, forzar=True)  # el DANE volvió a publicar 2024  # doctest: +SKIP
    """
    if isinstance(years, (numbers.Integral, str)):
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
        forzar=forzar,
    )
    return dl.run_pipeline(target_years=years, limit_files=limit_files)


__all__ = [
    "download", "load", "load_month", "available", "find_months", "harmonize", "indicadores",
    "serie_indicadores", "serie_tabla", "serie_frecuencias", "tabla_de_frecuencias", "exportar", "filtrar",
    "POBLACIONES", "marco_muestral", "MARCOS", "clear_cache", "GLOSARIO", "MODULOS", "CORE_RAW", "CONDICIONES", "NIVELES_EDUC",
    "GRUPOS_EDAD", "CATEGORIAS", "VARIABLES_INDICADORES", "POR_PRECALCULADOS",
    "ANIOS_DISPONIBLES", "ANIOS_EMPALME", "MODULE_PATTERNS", "DEFAULT_MODULES",
]
