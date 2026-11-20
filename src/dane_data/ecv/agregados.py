"""
Indicadores y privaciones del IPM de la ECV calculados año por año y guardados en disco.

Un año de la ECV con los capítulos que piden los indicadores pasa de 230 000 personas y 200 columnas: así no hace falta
tener la serie en memoria. La caché vive en ``~/.cache/dane_data/ecv/`` y se invalida sola si cambian los archivos o el
código.
"""

from __future__ import annotations

import hashlib
import json
import logging
import numbers
import warnings
from pathlib import Path
from typing import Callable, Iterable

import pandas as pd

from .. import config
from ..eevv.loader import _unir
from ..geih.agregados import _clave_json, _firma_codigo, _mascara
from ..geih.loader import _borrar_cache, _guardar_parquet, _usado
from .indicadores import _lista, indicadores
from .ipm import COLUMNAS_IPM, MODULOS_IPM, ipm, privaciones
from .loader import _EDUCACION, _FACTORES, MODULOS, _root, find_files, load

log = logging.getLogger("dane_data.ecv")

# Lo que produce los resultados (para _firma_codigo)
_CODIGO = ("ecv/loader.py", "ecv/indicadores.py", "ecv/ipm.py", "ecv/agregados.py", "_io.py", "referencias.py", "stats.py",
           "geih/agregados.py", "eevv/loader.py")
# Capítulos y variables del DANE que necesitan los indicadores
_MODULOS_INDICADORES = ("vivienda", "servicios", "tenencia", "condiciones", "salud", "educacion", "tic")
_COLUMNAS_INDICADORES = ("P8520S1", "P8520S3", "P8520S4", "P8520S5", "P5666", "P1075", "P5095", "P5230", "P6090",
                         "P6100", *_EDUCACION, "P1910", "P1911", "P1912", "P1084", "P1082", "P5504")


def clear_cache(dias: float | None = None) -> int:
    """
    Borra la caché de la ECV.

    Nunca hace falta para tener resultados correctos, porque se invalida sola cuando cambian los datos o el código: sirve
    para liberar espacio.

    Parámetros
    ----------
    dias
        Borrar solo lo que no se usa hace más de esos días. Por defecto, todo.

    Devuelve
    --------
    int
        Número de archivos borrados.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.clear_cache()  # doctest: +SKIP
    8
    """
    return _borrar_cache("ecv", dias)


def _firma_anio(anio: int, root) -> str:
    """Nombre, tamaño y fecha de cada archivo del año: si el DANE corrige uno, el resultado se recalcula."""
    partes = []
    for modulo in (*MODULOS, _FACTORES):
        if (ruta := find_files(anio, modulo=modulo, root=root).get(anio)) is not None:
            estado = ruta.stat()
            partes.append(f"{modulo}|{ruta.name}|{estado.st_size}|{estado.st_mtime_ns}")
    return ";".join(partes)


def _desde_cache(ruta: Path, calcular: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    if ruta.exists():
        try:
            tabla = pd.read_parquet(ruta)
            _usado(ruta)
            return tabla
        except Exception:  # caché corrupta: se regenera
            pass
    tabla = calcular()
    try:
        _guardar_parquet(tabla, ruta, "ecv")
    except Exception as e:  # disco lleno, sin permisos, etc.
        log.debug(f"No se pudo guardar caché {ruta}: {e}")
    return tabla


def _anios_lista(anios) -> list[int] | None:
    if anios is None:
        return None
    return [int(anios)] if isinstance(anios, (numbers.Integral, str)) else [int(a) for a in anios]


def serie_indicadores(
    anios: Iterable[int] | int | None = None,
    por: str | Iterable[str] | None = None,
    filtros: dict | None = None,
    dropna: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Indicadores de la serie de la ECV por año, sin tener toda la serie en memoria.

    Da lo mismo que ``indicadores(load(anios, modulos=[...]), por=["anio", *por])`` con los capítulos que piden los
    indicadores, pero lee un año a la vez, solo las columnas necesarias, y guarda cada resultado en disco.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    por
        Columna o lista de columnas para desagregar, además del año, por ejemplo ``"area"`` o ``"departamento"``.
    filtros
        Solo estas filas: ``{columna: [valores]}`` o ``{columna: (mínimo, máximo)}``. Con un filtro de personas (por
        ejemplo ``{"sexo": ["Mujer"]}``) los indicadores de hogares quedan sobre los hogares con jefa.
    dropna
        Quitar las filas sin dato en ``por``.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Las columnas de :func:`indicadores`, con ``anio`` y las de ``por``. Si a un año le falta un capítulo, sus
        indicadores quedan vacíos ese año (y se avisa).

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.

    Véase también
    -------------
    indicadores : Lo mismo sobre unos datos ya cargados.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> r = dd.ecv.serie_indicadores([2018, 2025])  # doctest: +SKIP
    >>> r[["anio", "hogares", "pct_internet_hogar", "pct_afiliados"]].round(1)  # doctest: +SKIP
       anio     hogares  pct_internet_hogar  pct_afiliados
    0  2018  15403086.0                52.3           93.6
    1  2025  18952206.0                73.9           97.2
    >>> dd.ecv.serie_indicadores(2025, por="departamento")  # doctest: +SKIP
    """
    anios = _anios_lista(anios)
    llaves = ["anio", *_lista(por)]
    archivos = find_files(anios, modulo="caracteristicas", root=root)
    if not archivos:
        raise FileNotFoundError(f"No hay datos de la ECV para años={anios} en {_root(root)}. "
                                "Descárguelos con dane_data.ecv.download(...) o revise dane_data.set_paths(...).")
    solicitud = json.dumps(_clave_json({"por": llaves, "filtros": filtros, "dropna": dropna}), sort_keys=True,
                           default=str, ensure_ascii=False)
    codigo = _firma_codigo(_CODIGO)
    partes, avisos = [], []
    for i, anio in enumerate(sorted(archivos)):
        if progress:
            progress(i / len(archivos), f"Calculando la ECV {anio} (solo la primera vez)")
        digest = hashlib.sha1("|".join([codigo, _firma_anio(anio, root), solicitud]).encode()).hexdigest()[:16]

        def calcular(a=anio) -> pd.DataFrame:
            with warnings.catch_warnings(record=True) as capturados:
                warnings.simplefilter("always", UserWarning)
                d = load(a, modulos=_MODULOS_INDICADORES, columns=_COLUMNAS_INDICADORES, root=root)
            avisos.extend(str(w.message) for w in capturados)
            return indicadores(d[_mascara(d, filtros)] if filtros else d, por=llaves, dropna=dropna)

        partes.append(_desde_cache(config.CACHE_DIR / "ecv" / "indicadores" / f"{anio}_{digest}.parquet", calcular))
    for aviso in dict.fromkeys(avisos):  # los de load, una vez cada uno
        warnings.warn(aviso, UserWarning, stacklevel=2)
    if progress:
        progress(1.0, "Listo")
    return _unir(partes).sort_values(llaves, ignore_index=True)


def serie_ipm(
    anios: Iterable[int] | int | None = None,
    por: str | Iterable[str] | None = None,
    muestra: str | None = None,
    dropna: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    El IPM por año, sin tener toda la serie en memoria.

    Da lo mismo que ``ipm(load(anios, modulos=MODULOS_IPM), por=["anio", *por])``, pero lee un año a la vez, solo las
    columnas necesarias, y guarda en disco las privaciones de cada hogar: otra desagregación del mismo año no vuelve a
    leer los datos.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    por
        Columna o lista de columnas para desagregar, además del año: ``"area"``, ``"region_ipm"`` (las regiones de los
        anexos del DANE), ``"region"`` (las de la ECV), ``"departamento"`` o ``"sexo_jefe"``.
    muestra
        ``"nacional"`` o ``"completa"``; por defecto, como el DANE (vea :func:`ipm`).
    dropna
        Quitar los hogares sin dato en ``por``.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Las columnas de :func:`ipm`, con ``anio`` y las de ``por``.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.
    ValueError
        Si a un año le falta un capítulo que necesita el IPM.

    Véase también
    -------------
    ipm : Lo mismo sobre unos datos ya cargados.
    privaciones : Las privaciones de cada hogar.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.serie_ipm([2018, 2025])[["anio", "incidencia", "ipm"]].round(3)  # doctest: +SKIP
       anio  incidencia    ipm
    0  2018      19.120  0.080
    1  2025       9.912  0.040
    >>> dd.ecv.serie_ipm(2025, por="departamento")  # doctest: +SKIP
    """
    anios = _anios_lista(anios)
    archivos = find_files(anios, modulo="caracteristicas", root=root)
    if not archivos:
        raise FileNotFoundError(f"No hay datos de la ECV para años={anios} en {_root(root)}. "
                                "Descárguelos con dane_data.ecv.download(...) o revise dane_data.set_paths(...).")
    codigo = _firma_codigo(_CODIGO)
    partes = []
    for i, anio in enumerate(sorted(archivos)):
        if progress:
            progress(i / len(archivos), f"Calculando el IPM {anio} (solo la primera vez)")
        faltan = [m for m in MODULOS_IPM if anio not in find_files(anio, modulo=m, root=root)]
        if faltan:
            raise ValueError(f"Al IPM de {anio} le faltan los capítulos {faltan}: bájelos con "
                             f"dd.ecv.download({anio}, modulos={faltan}).")
        digest = hashlib.sha1("|".join([codigo, _firma_anio(anio, root)]).encode()).hexdigest()[:16]

        def calcular(a=anio) -> pd.DataFrame:
            return privaciones(load(a, modulos=MODULOS_IPM, columns=COLUMNAS_IPM, root=root))

        partes.append(_desde_cache(config.CACHE_DIR / "ecv" / "privaciones" / f"{anio}_{digest}.parquet", calcular))
    if progress:
        progress(1.0, "Listo")
    llaves = ["anio", *_lista(por)]
    return ipm(_unir(partes), por=llaves, muestra=muestra, dropna=dropna).sort_values(llaves, ignore_index=True)
