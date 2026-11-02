"""
Proyecciones de población del DANE, empaquetadas con la librería (sin descargar nada).

Son los archivos vigentes de la página del DANE (2018 en adelante, actualizados el 30 de julio de 2025, y la
retroproyección 1950–2017): por departamento 1985–2050 y total nacional 1950–2070, por sexo y edad simple (hasta 100
años o más). Se regeneran con ``tests/datos/actualizar_proyecciones.py``.
"""

from __future__ import annotations

import numbers
import warnings
from functools import lru_cache
from importlib import resources
from typing import Iterable

import pandas as pd

from .referencias import DEPARTAMENTOS, strip_accents

_POR = ("departamento", "dpto", "area", "sexo", "edad")
_NACIONAL = 0  # Valor de dpto en los años que solo tienen total nacional


@lru_cache(maxsize=1)
def _datos() -> pd.DataFrame:
    with resources.files("dane_data.data").joinpath("proyecciones_poblacion.parquet").open("rb") as f:
        return pd.read_parquet(f)


def _dpto(valor) -> int:
    if isinstance(valor, numbers.Integral):
        if int(valor) in DEPARTAMENTOS:
            return int(valor)
    else:
        buscado = strip_accents(str(valor))
        for codigo, nombre in DEPARTAMENTOS.items():
            if strip_accents(nombre) == buscado:
                return codigo
    raise ValueError(f"Departamento desconocido {valor!r}. Opciones: {list(DEPARTAMENTOS.values())}")


def poblacion(
    anios: Iterable[int] | int | None = None,
    por: Iterable[str] | str | None = None,
    sexo: str | None = None,
    edades: int | tuple[int, int] | None = None,
    departamento=None,
    area: str | None = None,
) -> pd.DataFrame:
    """
    Población proyectada por el DANE.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos (1950–2070).
    por
        Desagregar, además de por año: ``"departamento"`` (nombre), ``"dpto"`` (código), ``"area"``, ``"sexo"`` o
        ``"edad"``. Un nombre o una lista.
    sexo
        ``"Hombre"`` o ``"Mujer"``. Por defecto, ambos.
    edades
        Una edad o un rango ``(mínima, máxima)``, incluidos los extremos. La edad 100 es «100 años o más».
    departamento
        Nombre o código de un departamento, o una lista de ellos.
    area
        ``"Cabecera"`` o ``"Centros poblados y rural disperso"``.

    Devuelve
    --------
    DataFrame
        ``anio``, las columnas de ``por`` y ``poblacion``.

    Lanza
    -----
    ValueError
        Si ``por``, ``sexo``, ``departamento`` o ``area`` no son válidos.

    Avisos
    ------
    UserWarning
        Si algún año pedido no tiene datos con esa desagregación. Se devuelven los demás.

    Véase también
    -------------
    dane_data.eevv.tasas : Tasas de natalidad y mortalidad con esta población.

    Notas
    -----
    Es una serie continua: los archivos del DANE empalman sin saltos y la suma de los departamentos da
    exactamente el total nacional en cada año. Los años tienen distinto detalle:

    * Por departamento: 1985–2050. Antes y después solo hay total nacional.
    * Por área: 1950–2045. En los años siguientes no se parte por área, y con ``por="area"`` esas filas salen
      como ``"Total"``.

    No es el marco de la GEIH de 2007–2019 y 2021, que usa las proyecciones anteriores, con base en el censo 2005.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.poblacion(2018)
       anio  poblacion
    0  2018   48258494
    >>> dd.poblacion(2025, sexo="Mujer", edades=(15, 49))
       anio  poblacion
    0  2025   14052801
    >>> dd.poblacion([2024, 2025], departamento="Chocó", por="sexo")
       anio    sexo  poblacion
    0  2024  Hombre     289966
    1  2024   Mujer     296162
    2  2025  Hombre     293515
    3  2025   Mujer     299591
    """
    por = [por] if isinstance(por, str) else list(por or [])
    if desconocidas := [c for c in por if c not in _POR]:
        raise ValueError(f"No se puede desagregar por {desconocidas}. Opciones: {list(_POR)}")
    d = _datos()
    mascara = pd.Series(True, index=d.index)
    pedidos = None
    if anios is not None:
        pedidos = sorted({int(a) for a in ([anios] if isinstance(anios, (numbers.Integral, str)) else anios)})
        mascara &= d["anio"].isin(pedidos)
    if sexo is not None:
        if sexo not in d["sexo"].cat.categories:
            raise ValueError(f"Sexo desconocido {sexo!r}. Opciones: {list(d['sexo'].cat.categories)}")
        mascara &= d["sexo"] == sexo
    if edades is not None:
        minima, maxima = (edades, edades) if isinstance(edades, numbers.Integral) else edades
        mascara &= d["edad"].between(minima, maxima)
    if area is not None:
        areas = [a for a in d["area"].cat.categories if a != "Total"]
        if area not in areas:
            raise ValueError(f"Área desconocida {area!r}. Opciones: {areas}")
        mascara &= d["area"] == area
    if departamento is not None:
        lista = [departamento] if isinstance(departamento, (str, numbers.Integral)) else departamento
        mascara &= d["dpto"].isin([_dpto(v) for v in lista])
    elif "departamento" in por or "dpto" in por:
        mascara &= d["dpto"] != _NACIONAL

    res = d[mascara]
    if pedidos and (sin_datos := sorted(set(pedidos) - set(res["anio"].unique()))):
        warnings.warn(f"Sin proyecciones con esa desagregación para: {', '.join(map(str, sin_datos))}. "
                      "Por departamento hay 1985–2050, por área hasta 2045 (y total nacional 1950–2070).",
                      UserWarning, stacklevel=2)
    if "departamento" in por:
        res = res.assign(departamento=res["dpto"].map(DEPARTAMENTOS))
    llaves = ["anio", *por]
    res = res.groupby(llaves, observed=True, sort=True)["poblacion"].sum().reset_index()
    res["poblacion"] = res["poblacion"].astype("int64")
    for columna in ("anio", "dpto", "edad"):
        if columna in res.columns:
            res[columna] = res[columna].astype("int64")
    for columna in ("area", "sexo"):
        if columna in res.columns:
            res[columna] = res[columna].astype(str)
    return res
