"""Medición de Pobreza Monetaria y Desigualdad: ingreso de la unidad de gasto, líneas de pobreza y quién es pobre."""

from __future__ import annotations

import numbers
from typing import Iterable

from .agregados import clear_cache, serie_indicadores
from .downloader import ARCHIVOS, ARCHIVOS_EMPALME, POBREZA_KNOWN_FILES, PobrezaDownloader
from .indicadores import GLOSARIO, indicadores
from .loader import (CATEGORIAS, CORE, DOMINIOS, ETIQUETAS, GRUPOS_DOMINIO, METODOLOGIAS, TRECE_CIUDADES, _root,
                     available, find_files, harmonize, load)

ANIOS_DISPONIBLES = sorted({a for a, _ in POBREZA_KNOWN_FILES if a != "empalme"})


def download(
    years: Iterable[int] | int | None = None,
    archivos: Iterable[str] | str | None = None,
    empalme: bool = False,
    root=None,
    delete_zips: bool = False,
    progress=None,
    should_stop=None,
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de la Medición de Pobreza Monetaria y Desigualdad del ANDA del DANE.

    Cada año queda en ``<carpeta>/datos/<año>/hogares.<ext>`` y ``personas.<ext>``. Es incremental: lo ya extraído se
    salta.

    Parámetros
    ----------
    years
        Año o lista de años (2012–2025). ``None`` descarga toda la serie (unos 1,4 GB de ZIP); una lista vacía, ninguno.
        Los años que no están en el ANDA quedan en la lista que se devuelve.
    archivos
        ``"hogares"`` (el ingreso per cápita, las líneas de pobreza y quién es pobre: lo que necesitan los
        indicadores), ``"personas"`` (los componentes del ingreso de cada persona), o los dos (``None``, por defecto).
    empalme
        Bajar también, a ``<carpeta>/datos/empalme/``, los archivos para comparar 2012–2021 con las cifras del marco
        2018: el factor de empalme 2012–2020, los hogares empalmados de 2021 y las líneas actualizadas de 2012–2018.
        Se bajan una sola vez, cualquiera que sea ``years``.
    root
        Carpeta de destino. Por defecto, la de ``dd.get_path("pobreza")``.
    delete_zips
        Borrar cada ZIP después de extraerlo.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.
    should_stop
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.
    forzar
        Volver a bajar y extraer aunque ya esté en disco, por ejemplo si el DANE corrigió los archivos. Lo extraído
        antes se reemplaza solo si el ZIP nuevo se extrajo bien.

    Devuelve
    --------
    list[str]
        Lo que no se pudo descargar o extraer, con el archivo, el año y el motivo; vacía si todo salió bien.

    Lanza
    -----
    ValueError
        Si algún archivo no es ``"hogares"`` ni ``"personas"``.
    DownloadCancelled
        Si ``should_stop()`` devolvió True.

    Notas
    -----
    Desde 2023 el DANE publica hogares y personas en un solo ZIP (unos 120 MB): pedir solo ``"hogares"`` lo baja
    entero. El ZIP queda en ``<carpeta>/raw_zips/`` salvo con ``delete_zips``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.pobreza.download(2025)  # doctest: +SKIP
    >>> dd.pobreza.download(range(2012, 2026), archivos="hogares", empalme=True)  # doctest: +SKIP
    """
    if isinstance(years, (numbers.Integral, str)):
        years = [years]
    if archivos is None:
        archivos = ARCHIVOS
    elif isinstance(archivos, str):
        archivos = (archivos,)
    if desconocidos := [a for a in archivos if a not in ARCHIVOS]:
        raise ValueError(f"Archivo desconocido {desconocidos}. Opciones: {list(ARCHIVOS)}")
    dl = PobrezaDownloader(base_dir=_root(root), keep_zips=not delete_zips, progress=progress,
                           should_stop=should_stop, forzar=forzar)
    return dl.run_pipeline(target_years=years, archivos=tuple(archivos), empalme=empalme)


__all__ = [
    "download", "available", "find_files", "load", "harmonize", "ARCHIVOS", "ARCHIVOS_EMPALME", "ANIOS_DISPONIBLES",
    "indicadores", "serie_indicadores", "clear_cache", "CORE", "ETIQUETAS", "CATEGORIAS", "DOMINIOS", "GRUPOS_DOMINIO", "TRECE_CIUDADES", "METODOLOGIAS",
    "GLOSARIO",
]
