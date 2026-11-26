"""Encuesta Nacional de Calidad de Vida (ECV), 2018–2025, y su Índice de Pobreza Multidimensional
(IPM).
"""

from __future__ import annotations

from typing import Iterable

from .agregados import clear_cache, serie_indicadores, serie_ipm
from .downloader import _CATALOGOS, ECVDownloader
from .indicadores import GLOSARIO, indicadores
from .ipm import COLUMNAS_IPM, MODULOS_IPM, PRIVACIONES, ipm, privaciones
from .loader import (
    CATEGORIAS,
    ETIQUETAS,
    KEYS_HOGAR,
    KEYS_PERSONA,
    MODULOS,
    NIVELES,
    UNIDADES,
    _root,
    available,
    find_files,
    harmonize,
    load,
)
from ..stats import _enteros, _opciones

ANIOS_DISPONIBLES = sorted(_CATALOGOS)


def download(
    years: Iterable[int] | int | None = None,
    modulos: Iterable[str] | str | None = None,
    raiz=None,
    borrar_zips: bool = False,
    progreso=None,
    detener=None,
    forzar: bool = False,
) -> list[str]:
    """
    Descarga los microdatos de la Encuesta Nacional de Calidad de Vida del ANDA del DANE.

    Un capítulo del cuestionario por carpeta, en ``<carpeta>/datos/<año>/<módulo>/``. Es
    incremental: lo ya extraído se salta. Con cualquier capítulo de 2018 baja también los factores
    del CNPV 2018, y con 2020 la base complementaria del IPM: sin ellos las cifras no son las
    oficiales.

    Ocupa espacio: los 11 capítulos de un año son unos 1,4 GB en ZIP en 2025 (menos en los años
    anteriores), más lo extraído; ``borrar_zips=True`` borra los ZIP. Una descarga cortada vuelve a
    empezar ese ZIP.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` descarga 2018–2025; una lista vacía, ninguno. Los años que no
        están en el ANDA se saltan y quedan en la lista que se devuelve.
    modulos
        Capítulo o lista de capítulos de ``dd.ecv.MODULOS``. ``None`` para todos: los usan las
        variables armonizadas, los indicadores y el IPM.
    raiz
        Carpeta de destino. Por defecto, la de ``dd.get_path("ecv")``.
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
        Lo que no se pudo descargar o extraer, con el capítulo, el año y el motivo; vacía si todo
        salió bien.

    Lanza
    -----
    ValueError
        Si algún capítulo no es de ``dd.ecv.MODULOS``.
    DownloadCancelled
        Si ``detener()`` devolvió True.

    Véase también
    -------------
    available : Qué años y capítulos hay en disco.

    Notas
    -----
    Los ZIP de 2024 y 2025 pesan mucho más que los de antes: los once capítulos de 2025 son unos
    1,4 GB (TIC, fuerza de trabajo y características, más de 300 MB cada uno), contra 100 a 200 MB
    por año en 2018–2023. Con 2018 se bajan también los factores de expansión basados en el CNPV
    2018, que el DANE publicó aparte.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.download(2025)  # doctest: +SKIP
    >>> dd.ecv.download(range(2018, 2026), modulos=["caracteristicas", "salud"])  # doctest: +SKIP
    """
    years = _enteros(years)
    modulos = _opciones(modulos, MODULOS, "Módulo")
    dl = ECVDownloader(
        base_dir=_root(raiz),
        keep_zips=not borrar_zips,
        progress=progreso,
        should_stop=detener,
        forzar=forzar,
    )
    return dl.run_pipeline(target_years=years, modulos=modulos)


__all__ = [
    "download",
    "available",
    "find_files",
    "load",
    "harmonize",
    "indicadores",
    "serie_indicadores",
    "privaciones",
    "ipm",
    "serie_ipm",
    "clear_cache",
    "MODULOS",
    "UNIDADES",
    "NIVELES",
    "KEYS_HOGAR",
    "KEYS_PERSONA",
    "ETIQUETAS",
    "CATEGORIAS",
    "GLOSARIO",
    "PRIVACIONES",
    "MODULOS_IPM",
    "COLUMNAS_IPM",
    "ANIOS_DISPONIBLES",
]
