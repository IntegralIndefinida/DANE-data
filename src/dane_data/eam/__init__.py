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
    Descarga microdatos EAM (1992–2024) del ANDA (DANE).

    >>> dd.eam.download([2022, 2023, 2024])
    >>> dd.eam.download()                       # serie completa (~330 MB)

    Es incremental: los años ya extraídos se saltan.
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
