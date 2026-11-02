"""Estadísticas Vitales (EEVV) — certificados de nacimiento y de defunción."""

from __future__ import annotations

import numbers
from typing import Iterable

from .. import config
from .downloader import EEVV_KNOWN_FILES, EEVVDownloader
from .loader import TIPOS, _tipo_valido, available, find_files

ANIOS_DISPONIBLES = {tipo: sorted(a for a, t in EEVV_KNOWN_FILES if t == tipo) for tipo in TIPOS}


def download(
    years: Iterable[int] | int | None = None,
    tipos: Iterable[str] | str | None = None,
    root=None,
    delete_zips: bool = False,
    progress=None,
    should_stop=None,
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de las Estadísticas Vitales del ANDA del DANE.

    Un archivo por año y tipo en ``<carpeta>/datos/<tipo>/<año>/``. Es incremental: lo ya extraído se salta.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` descarga toda la serie (unos 1,6 GB de ZIP); una lista vacía, ninguno. Los
        años que no están en el ANDA se ignoran con un aviso.
    tipos
        ``"defunciones"`` (1979–2025), ``"nacimientos"`` o ``"fetales"`` (ambos 1998–2025), o una lista. ``None``
        para los tres.
    root
        Carpeta de destino. Por defecto, la de ``dd.get_path("eevv")``.
    delete_zips
        Borrar cada ZIP después de extraerlo.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.
    should_stop
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.
    forzar
        Volver a bajar y extraer aunque ya esté en disco, por ejemplo si el DANE corrigió los archivos. Lo
        extraído antes se reemplaza solo si el ZIP nuevo se extrajo bien; si no, se conserva.

    Devuelve
    --------
    list[str]
        Lo que no se pudo descargar o extraer, con el tipo, el año y el motivo; vacía si todo salió bien.

    Lanza
    -----
    ValueError
        Si algún tipo no es uno de los tres.
    DownloadCancelled
        Si ``should_stop()`` devolvió True.

    Véase también
    -------------
    available : Qué años hay en disco.

    Notas
    -----
    Algunos ZIP del ANDA traen varios años (2008–2011, 2012–2013, 2017–2018), así que pedir un solo año baja el
    paquete entero: los nacimientos de 2008–2011 pesan 192 MB. Se extrae solo el año pedido y el ZIP queda para
    los demás, salvo con ``delete_zips``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eevv.download(2025)  # doctest: +SKIP
    >>> dd.eevv.download(range(2015, 2026), tipos="nacimientos")  # doctest: +SKIP
    """
    if isinstance(years, (numbers.Integral, str)):
        years = [years]
    if tipos is None:
        tipos = TIPOS
    elif isinstance(tipos, str):
        tipos = (tipos,)
    tipos = tuple(_tipo_valido(t) for t in tipos)
    dl = EEVVDownloader(
        base_dir=root or config.get_path("eevv"),
        keep_zips=not delete_zips,
        progress=progress,
        should_stop=should_stop,
        forzar=forzar,
    )
    return dl.run_pipeline(target_years=years, tipos=tipos)


__all__ = ["download", "available", "find_files", "TIPOS", "ANIOS_DISPONIBLES"]
