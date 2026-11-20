"""
Carga de la Encuesta Nacional de Calidad de Vida (ECV) ya descargada.

Un capítulo del cuestionario por carpeta, en ``<raíz>/datos/<año>/<módulo>/``. El DANE publica cada capítulo en CSV
(``;``, coma decimal), Stata y SPSS; se usa el CSV y, si no está, el Stata.
"""

from __future__ import annotations

import numbers
from pathlib import Path
from typing import Iterable

import pandas as pd

from .. import config
from .._hooks import archivos_datos

# Capítulos que se descargan y se cargan: los que usan las variables armonizadas, los indicadores y el IPM
MODULOS = ("vivienda", "servicios", "tenencia", "condiciones", "caracteristicas", "salud", "primera_infancia",
           "educacion", "fuerza_trabajo", "tic", "trabajo_infantil")
# Los factores de expansión de 2018 basados en el CNPV 2018, que el DANE publicó aparte: no son un capítulo
_FACTORES = "factores"
EXTENSIONES = (".csv", ".dta")


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("ecv")


def _modulo_valido(modulo: str) -> str:
    if modulo not in (*MODULOS, _FACTORES):
        raise ValueError(f"Módulo desconocido {modulo!r}. Opciones: {list(MODULOS)}")
    return modulo


def find_files(years: Iterable[int] | int | None = None, modulo: str = "caracteristicas", root=None) -> dict[int, Path]:
    """
    Archivo de datos de un capítulo en cada año descargado.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    modulo
        Uno de ``dd.ecv.MODULOS``.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("ecv")``).

    Devuelve
    --------
    dict
        ``{año: ruta}``.

    Lanza
    -----
    ValueError
        Si ``modulo`` no es uno de ``dd.ecv.MODULOS``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.find_files(2025, modulo="salud")  # doctest: +SKIP
    {2025: PosixPath('/home/ana/dane_data_datos/ecv/datos/2025/salud/Salud.CSV')}
    """
    _modulo_valido(modulo)
    base = _root(root) / "datos"
    if not base.is_dir():
        return {}
    if years is not None:
        # numbers.Integral: también un año de numpy (df.anio.max())
        years = {int(y) for y in ([years] if isinstance(years, (numbers.Integral, str)) else years)}
    out = {}
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(carpeta.name)
        if (years is None or anio in years) and (archivos := archivos_datos(carpeta / modulo, EXTENSIONES)):
            out[anio] = max(archivos, key=lambda f: (f.suffix.lower() != ".dta", f.stat().st_size))
    return out


def available(root=None) -> pd.DataFrame:
    """
    Qué capítulos de cada año están descargados.

    Parámetros
    ----------
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("ecv")``).

    Devuelve
    --------
    pandas.DataFrame
        Una fila por año y capítulo: ``anio``, ``modulo``, ``archivo`` y ``tamano_mb``. En 2018 aparecen también los
        ``factores`` de expansión basados en el CNPV 2018.

    Véase también
    -------------
    download : Descargar lo que falta.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.available().head(2)  # doctest: +SKIP
       anio    modulo                  archivo  tamano_mb
    0  2025  vivienda  Datos de la vivienda.CSV       10.2
    1  2025  servicios  Servicios del hogar.CSV       20.9
    """
    filas = [{"anio": anio, "modulo": modulo, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
             for modulo in (*MODULOS, _FACTORES) for anio, f in find_files(modulo=modulo, root=root).items()]
    tabla = pd.DataFrame(filas, columns=["anio", "modulo", "archivo", "tamano_mb"])
    return tabla.sort_values("anio", kind="stable").reset_index(drop=True)
