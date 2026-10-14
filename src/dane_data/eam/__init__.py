"""Encuesta Anual Manufacturera (EAM) — industria, microdatos de establecimientos."""

from __future__ import annotations

from typing import Iterable

from .. import config
from .downloader import EAM_KNOWN_CATALOGS, EAM_TIC_CATALOGS, EAMDownloader
from .indicadores import GLOSARIO, crecimiento, deflactar, panel, participacion, resumen, supervivencia
from .loader import (CORE, ETIQUETAS, SECTORES, VARIABLES_COMUNES, available, find_files, harmonize,
                     load)

ANIOS_DISPONIBLES = sorted(int(y) for y in EAM_KNOWN_CATALOGS)


def download(
    years: Iterable[int] | int | None = None,
    root=None,
    include_tic: bool = False,
    delete_zips: bool = False,
    progress=None,
    should_stop=None,
) -> None:
    """
    Descarga los microdatos de la EAM del ANDA del DANE.

    Un archivo por año en ``<carpeta>/datos/<año>/``. Es incremental: los años ya extraídos se saltan.

    Parámetros
    ----------
    years
        Año o lista de años entre 1992 y 2024. ``None`` descarga toda la serie (unos 330 MB).
    root
        Carpeta de destino. Por defecto, la de ``dd.get_path("eam")``.
    include_tic
        Bajar también el módulo de tecnologías de la información (TIC), 2008–2018.
    delete_zips
        Borrar cada ZIP después de extraerlo.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.
    should_stop
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.

    Lanza
    -----
    DownloadCancelled
        Si ``should_stop()`` devolvió True.

    Véase también
    -------------
    available : Qué años hay en disco.
    load : Cargar lo descargado.

    Notas
    -----
    Cuando el ANDA no publica un CSV para un año, se usa el TXT (2023) o se convierte el archivo de Stata a
    texto (2024).

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eam.download([2022, 2023, 2024])  # doctest: +SKIP
    >>> dd.eam.download()  # toda la serie, 1992–2024  # doctest: +SKIP
    """
    if isinstance(years, (int, str)):
        years = [years]
    dl = EAMDownloader(
        base_dir=root or config.get_path("eam"),
        keep_zips=not delete_zips,
        extract_data=True,
        include_tic=include_tic,
        progress=progress,
        should_stop=should_stop,
    )
    dl.run_pipeline(target_years=years)


__all__ = [
    "download", "load", "available", "find_files", "harmonize", "resumen", "participacion",
    "crecimiento", "deflactar", "panel", "supervivencia", "GLOSARIO", "ETIQUETAS", "SECTORES",
    "CORE", "VARIABLES_COMUNES", "ANIOS_DISPONIBLES",
]
