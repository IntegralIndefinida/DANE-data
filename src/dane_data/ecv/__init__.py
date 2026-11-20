"""Encuesta Nacional de Calidad de Vida (ECV), 2018–2025."""

from __future__ import annotations

import numbers
from typing import Iterable

from .downloader import _CATALOGOS, ECVDownloader
from .loader import MODULOS, _root, available, find_files

ANIOS_DISPONIBLES = sorted(_CATALOGOS)


def download(
    years: Iterable[int] | int | None = None,
    modulos: Iterable[str] | str | None = None,
    root=None,
    delete_zips: bool = False,
    progress=None,
    should_stop=None,
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de la Encuesta Nacional de Calidad de Vida del ANDA del DANE.

    Un capítulo del cuestionario por carpeta, en ``<carpeta>/datos/<año>/<módulo>/``. Es incremental: lo ya extraído se
    salta.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` descarga 2018–2025; una lista vacía, ninguno. Los años que no están en el ANDA se
        saltan y quedan en la lista que se devuelve.
    modulos
        Capítulo o lista de capítulos de ``dd.ecv.MODULOS``. ``None`` para todos: los usan las variables armonizadas,
        los indicadores y el IPM.
    root
        Carpeta de destino. Por defecto, la de ``dd.get_path("ecv")``.
    delete_zips
        Borrar cada ZIP después de extraerlo.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.
    should_stop
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.
    forzar
        Volver a bajar y extraer aunque ya esté en disco, por ejemplo si el DANE corrigió los archivos. Lo extraído
        antes se reemplaza solo si el ZIP nuevo se extrajo bien; si no, se conserva.

    Devuelve
    --------
    list[str]
        Lo que no se pudo descargar o extraer, con el capítulo, el año y el motivo; vacía si todo salió bien.

    Lanza
    -----
    ValueError
        Si algún capítulo no es de ``dd.ecv.MODULOS``.
    DownloadCancelled
        Si ``should_stop()`` devolvió True.

    Véase también
    -------------
    available : Qué años y capítulos hay en disco.

    Notas
    -----
    Los ZIP de 2024 y 2025 pesan mucho más que los de antes: los once capítulos de 2025 son unos 1,4 GB (TIC, fuerza de
    trabajo y características, más de 300 MB cada uno), contra 100 a 200 MB por año en 2018–2023. Con 2018 se bajan
    también los factores de expansión basados en el CNPV 2018, que el DANE publicó aparte.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.download(2025)  # doctest: +SKIP
    >>> dd.ecv.download(range(2018, 2026), modulos=["caracteristicas", "salud"])  # doctest: +SKIP
    """
    if isinstance(years, (numbers.Integral, str)):
        years = [years]
    if modulos is None:
        modulos = MODULOS
    elif isinstance(modulos, str):
        modulos = (modulos,)
    modulos = tuple(modulos)
    if desconocidos := [m for m in modulos if m not in MODULOS]:
        raise ValueError(f"Módulo desconocido {desconocidos[0]!r}. Opciones: {list(MODULOS)}")
    dl = ECVDownloader(
        base_dir=_root(root),
        keep_zips=not delete_zips,
        progress=progress,
        should_stop=should_stop,
        forzar=forzar,
    )
    return dl.run_pipeline(target_years=years, modulos=modulos)


__all__ = ["download", "available", "find_files", "MODULOS", "ANIOS_DISPONIBLES"]
