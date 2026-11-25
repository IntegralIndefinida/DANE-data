"""
Indicadores de pobreza año por año, con cada año armonizado guardado en disco.

Leer y armonizar un año (y unirle el empalme) es lo que tarda; los indicadores se calculan en una fracción de segundo.
Por eso la caché guarda el año armonizado, en ``~/.cache/dane_data/pobreza/``, y se invalida sola si cambian los
archivos que usa ese año o el código.
"""

from __future__ import annotations

import hashlib
import warnings
from pathlib import Path
from typing import Iterable

import pandas as pd

from .. import config
from ..geih.agregados import _firma_codigo, _mascara
from ..geih.loader import _borrar_cache, _desde_cache
from ..stats import _as_list, _con_nombres_viejos, _enteros
from .indicadores import indicadores
from .loader import _archivo, _avisar_metodologias, _root, find_files, load

# Lo que produce el año armonizado (para _firma_codigo). indicadores.py y stats.py no: se recalculan en cada llamada.
_CODIGO = ("pobreza/loader.py", "pobreza/agregados.py", "_io.py", "referencias.py")


def clear_cache(dias: float | None = None) -> int:
    """
    Borra la caché de la pobreza monetaria.

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
    >>> dd.pobreza.clear_cache()  # doctest: +SKIP
    14
    """
    return _borrar_cache("pobreza", dias)


def _firma(ruta: Path) -> str:
    estado = ruta.stat()
    return f"{ruta.resolve()}|{estado.st_size}|{estado.st_mtime_ns}"


def _usados(anio: int, ruta: Path, empalme: bool, raiz) -> list[Path]:
    """Los archivos de los que sale el año armonizado: el de hogares y, con empalme, los de empalme de ese año."""
    usados = [ruta]
    if empalme and anio <= 2021:
        nombres = (["empalme_2012_2020"] if anio <= 2020 else []) + (["lineas_2012_2018"] if anio <= 2018 else []) \
                  + (["hogares_empalmado_2021", "hogares_empalmado_dpto_2021"] if anio == 2021 else [])
        carpeta = _root(raiz) / "datos" / "empalme"
        usados += [r for n in nombres if (r := _archivo(carpeta, n))]  # si falta, load lo reporta
    return usados


def _armonizado(anio: int, ruta: Path, empalme: bool, raiz) -> pd.DataFrame:
    """Un año de :func:`load`, leído de la caché si ya se armonizó con los mismos archivos y el mismo código."""
    partes = [_firma_codigo(_CODIGO), f"empalme={empalme}", *map(_firma, _usados(anio, ruta, empalme, raiz))]
    digest = hashlib.sha1("|".join(partes).encode()).hexdigest()[:16]

    def leer() -> pd.DataFrame:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # serie_indicadores avisa una sola vez
            return load(anio, empalme=empalme, raiz=raiz)

    return _desde_cache(config.CACHE_DIR / "pobreza" / "anios" / f"{anio}_{digest}.parquet", leer, "pobreza")


@_con_nombres_viejos
def serie_indicadores(
    anios: Iterable[int] | int | None = None,
    por: str | Iterable[str] | None = None,
    empalme: bool = False,
    filtros: dict | None = None,
    dropna: bool = True,
    raiz=None,
    progreso=None,
    departamental: bool = False,
) -> pd.DataFrame:
    """
    Indicadores de pobreza por año sin tener toda la serie en memoria.

    Da lo mismo que ``indicadores(load(anios, empalme=empalme), por=["anio", *por])``, pero lee un año a la vez y guarda
    cada año armonizado en disco: la segunda vez no vuelve a leer los archivos del DANE.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    por
        Columna o lista de columnas para desagregar, además del año, por ejemplo ``"grupo_dominio"``.
    empalme
        La serie empalmada al marco 2018, comparable en 2012–2025 (vea :func:`load`).
    filtros
        Solo estos hogares: ``{columna: [valores]}`` o ``{columna: (mínimo, máximo)}``.
    dropna
        Quitar los hogares sin dato en ``por``.
    raiz
        Carpeta raíz. Por defecto, la configurada.
    progreso
        Función ``progreso(fraccion, mensaje)`` que recibe el avance.
    departamental
        Con el factor y el ingreso departamentales, como el anexo departamental del DANE (vea :func:`indicadores`).

    Devuelve
    --------
    DataFrame
        Las columnas de :func:`indicadores`, con ``anio`` y las de ``por``.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años, o faltan los archivos de empalme.

    Avisos
    ------
    UserWarning
        Si sin empalme se juntan años de metodologías o marcos distintos.

    Véase también
    -------------
    indicadores : Lo mismo sobre unos hogares ya cargados.
    clear_cache : Liberar el espacio de la caché.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> r = dd.pobreza.serie_indicadores(range(2022, 2026), empalme=True)  # doctest: +SKIP
    >>> r[["anio", "incidencia", "incidencia_extrema", "gini"]].round(3)  # doctest: +SKIP
       anio  incidencia  incidencia_extrema   gini
    0  2022      36.634              13.798  0.556
    1  2023      34.617              12.641  0.553
    2  2024      31.786              11.690  0.551
    3  2025      28.003               9.638  0.531
    """
    archivos = find_files(_enteros(anios), raiz=raiz)
    if not archivos:
        raise FileNotFoundError(
            f"No hay datos de pobreza para años={anios} en {_root(raiz)}. "
            "Descárguelos con dane_data.pobreza.download(...) o revise dane_data.set_paths(...)."
        )
    _avisar_metodologias(archivos, empalme)
    llaves = ["anio", *_as_list(por)]
    partes = []
    for i, (anio, ruta) in enumerate(sorted(archivos.items())):
        if progreso:
            progreso(i / len(archivos), f"Pobreza {anio} (la primera vez lee los archivos del DANE)")
        d = _armonizado(anio, ruta, empalme, raiz)
        partes.append(indicadores(d[_mascara(d, filtros)] if filtros else d, por=llaves, dropna=dropna,
                                  departamental=departamental))
    if progreso:
        progreso(1.0, "Listo")
    return pd.concat(partes, ignore_index=True)
