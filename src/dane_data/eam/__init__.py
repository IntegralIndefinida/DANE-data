"""Encuesta Anual Manufacturera (EAM) — industria, microdatos de establecimientos."""

from __future__ import annotations

from typing import Iterable

from .downloader import EAM_KNOWN_CATALOGS, EAMDownloader
from .indicadores import (
    GLOSARIO,
    crecimiento,
    deflactar,
    panel,
    participacion,
    resumen,
    supervivencia,
)

from .loader import (
    CORE,
    ETIQUETAS,
    SECTORES,
    VARIABLES_COMUNES,
    available,
    find_files,
    harmonize,
    load,
    _root,
)
from ..stats import _enteros

# Las demás encuestas tienen dd.<encuesta>.indicadores(df); dd.eam.indicadores era el submódulo y
# daba «'module' object is not callable». El submódulo sigue en sys.modules (import
# dane_data.eam.indicadores).
indicadores = resumen

ANIOS_DISPONIBLES = sorted(int(y) for y in EAM_KNOWN_CATALOGS)


def download(
    years: Iterable[int] | int | None = None,
    raiz=None,
    incluir_tic: bool = False,
    borrar_zips: bool = False,
    progreso=None,
    detener=None,
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de la EAM del ANDA del DANE.

    Un archivo por año en ``<carpeta>/datos/<año>/``. Es incremental: los años ya extraídos se
    saltan.

    Parámetros
    ----------
    years
        Año o lista de años entre 1992 y 2024. ``None`` descarga toda la serie (unos 330 MB); una
        lista vacía, ninguno. Los años que no están en el ANDA se saltan y quedan en la lista que
        se devuelve.
    raiz
        Carpeta de destino. Por defecto, la de ``dd.get_path("eam")``.
    incluir_tic
        Bajar también el módulo de tecnologías de la información (TIC), 2008–2018.
    borrar_zips
        Borrar cada ZIP después de extraerlo.
    progreso
        Función ``progreso(fraccion, mensaje)`` que recibe el avance.
    detener
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.
    forzar
        Volver a bajar y extraer aunque ya esté en disco, por ejemplo si el DANE corrigió los
        archivos. Lo extraído antes se reemplaza solo si el ZIP nuevo se extrajo bien; si no, se
        conserva.

    Devuelve
    --------
    list[str]
        Lo que no se pudo descargar o extraer, con el año y el motivo; vacía si todo salió bien. Al
        volver a descargar los mismos años, lo que ya está completo se salta y se reintenta lo
        demás.

    Lanza
    -----
    DownloadCancelled
        Si ``detener()`` devolvió True.

    Véase también
    -------------
    available : Qué años hay en disco.
    load : Cargar lo descargado.

    Notas
    -----
    Cuando el ANDA no publica un CSV para un año, se usa el TXT (2023) o el archivo de Stata
    (2024).

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eam.download([2022, 2023, 2024])  # doctest: +SKIP
    >>> dd.eam.download()  # toda la serie, 1992–2024  # doctest: +SKIP
    """
    years = _enteros(years)
    descargador = EAMDownloader(
        base_dir=_root(raiz),
        keep_zips=not borrar_zips,
        include_tic=incluir_tic,
        progress=progreso,
        should_stop=detener,
        forzar=forzar,
    )
    return descargador.run_pipeline(target_years=years)


__all__ = [
    "download",
    "load",
    "available",
    "find_files",
    "harmonize",
    "resumen",
    "participacion",
    "crecimiento",
    "deflactar",
    "panel",
    "supervivencia",
    "indicadores",
    "GLOSARIO",
    "ETIQUETAS",
    "SECTORES",
    "CORE",
    "VARIABLES_COMUNES",
    "ANIOS_DISPONIBLES",
]
