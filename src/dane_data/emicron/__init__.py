"""Encuesta de Micronegocios (EMICRON) — unidades económicas de hasta 9 personas ocupadas."""

from __future__ import annotations

from typing import Iterable

from .downloader import EMICRON_KNOWN_FILES, EMICRONDownloader
from .indicadores import GLOSARIO, a_miles_anuales, indicadores
from .loader import (CATEGORIAS, CIUDADES, CLAVE, CORE, ETIQUETAS, FACTORES, MODULOS, MONTOS, _root,
                     available, find_files, harmonize, load, load_personal)
from ..stats import _con_nombres_viejos, _enteros, _opciones

ANIOS_DISPONIBLES = sorted({a for a, _ in EMICRON_KNOWN_FILES})


@_con_nombres_viejos
def download(
    anios: Iterable[int] | int | None = None,
    modulos: Iterable[str] | str | None = None,
    raiz=None,
    borrar_zips: bool = False,
    progreso=None,
    detener=None,
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de la EMICRON del ANDA del DANE.

    Un CSV por año y módulo en ``<carpeta>/datos/<año>/<módulo>.csv``. Es incremental: lo ya extraído se salta.

    Parámetros
    ----------
    anios
        Año o lista de años entre 2019 y 2025. ``None`` descarga toda la serie (unos 300 MB de ZIP); una lista vacía,
        ninguno. Los años que no están en el ANDA se saltan y quedan en la lista que se devuelve.
    modulos
        Módulo o lista de módulos (claves de ``MODULOS``). ``None`` para todos. La identificación y los factores de
        expansión se bajan siempre: sin ellos no se puede cargar.
    raiz
        Carpeta de destino. Por defecto, la de ``dd.get_path("emicron")``.
    borrar_zips
        Borrar cada ZIP después de extraerlo.
    progreso
        Función ``progreso(fraccion, mensaje)`` que recibe el avance.
    detener
        Función sin argumentos; si devuelve True, la descarga se detiene con ``DownloadCancelled``.
    forzar
        Volver a bajar y extraer aunque ya esté en disco, por ejemplo si el DANE corrigió los archivos. Un CSV se
        reemplaza solo si el nuevo se extrajo completo; si no, se conserva el anterior.

    Devuelve
    --------
    list[str]
        Lo que no se pudo descargar o extraer, con el año, el módulo y el motivo; vacía si todo salió bien.

    Lanza
    -----
    ValueError
        Si algún módulo no es una clave de ``MODULOS``.
    DownloadCancelled
        Si ``detener()`` devolvió True.

    Véase también
    -------------
    available : Qué años y módulos hay en disco.

    Notas
    -----
    No todos los módulos existen todos los años: 2020 no trae inclusión financiera ni capital social, 2021 no trae
    capital social y el módulo COVID solo existe en 2020. Pedir uno de ellos para esos años deja un aviso en el
    registro. Los microdatos de 2025 solo cubren las 24 ciudades principales.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.emicron.download(2024)  # doctest: +SKIP
    >>> dd.emicron.download(range(2019, 2025), modulos=["ventas", "costos"])  # doctest: +SKIP
    """
    anios = _enteros(anios)
    if modulos is not None:  # None: el descargador decide (todos)
        modulos = list(_opciones(modulos, MODULOS, "Módulo"))
    dl = EMICRONDownloader(
        base_dir=_root(raiz),
        keep_zips=not borrar_zips,
        progress=progreso,
        should_stop=detener,
        forzar=forzar,
    )
    return dl.run_pipeline(target_years=anios, modulos=modulos)


__all__ = [
    "download", "available", "find_files", "load", "load_personal", "harmonize", "indicadores", "a_miles_anuales",
    "GLOSARIO", "MODULOS", "FACTORES", "CORE",
    "ETIQUETAS", "CATEGORIAS", "CIUDADES", "CLAVE", "MONTOS", "ANIOS_DISPONIBLES",
]
