"""Indicadores de pobreza monetaria y desigualdad por grupo, como los publica el DANE."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _as_list, _con_categorias, weighted_gini

GLOSARIO = {
    "Unidad de gasto": "Las personas del hogar que comparten el gasto: todas menos el servicio doméstico, sus hijos y los "
                       "pensionistas.",
    "Ingreso per cápita": "Ingreso total de la unidad de gasto, con el arriendo imputado a quien vive en vivienda propia, "
                          "dividido por sus personas (ingreso_pc, INGPCUG). Cada persona del hogar, también las que no son "
                          "de la unidad de gasto, cuenta con ese ingreso.",
    "Línea de pobreza": "Costo por persona al mes de una canasta de bienes y servicios básicos, por dominio y mes. Quien "
                        "tiene un ingreso per cápita menor está en pobreza monetaria.",
    "Línea de pobreza extrema": "Costo por persona al mes de una canasta de alimentos que cubre los requerimientos "
                                "nutricionales. Quien tiene un ingreso per cápita menor está en pobreza monetaria extrema.",
    "Incidencia": "Porcentaje de las personas en pobreza (o pobreza extrema): el FGT(0) de Foster, Greer y Thorbecke.",
    "Brecha": "Cuánto falta en promedio para salir de la pobreza, como porcentaje de la línea, contando con 0 a quienes no "
              "son pobres: promedio de max(0, (línea − ingreso) / línea), el FGT(1).",
    "Severidad": "Como la brecha, pero con la distancia a la línea al cuadrado: pesa más a los más pobres, el FGT(2).",
    "Coeficiente de Gini": "Desigualdad del ingreso per cápita entre las personas, de 0 (todos tienen lo mismo) a 1 (una "
                           "tiene todo).",
    "Peso de las personas": "Factor de expansión del hogar por sus personas (fex × personas). Las personas y los pobres "
                            "están en personas, no en miles. Por departamento se usa el mismo factor: el departamental "
                            "(fex_dpto) todavía no se usa.",
}

_NECESARIAS = ("ingreso_pc", "linea_pobreza", "linea_pobreza_extrema", "pobre", "pobre_extremo", "fex", "personas")
# Lo que no se puede promediar entre sí: si hay más de un valor, tiene que estar en ``por``
_CONTEXTO = ("anio", "metodologia", "empalmado")


def _fgt(y: np.ndarray, z: np.ndarray, w: np.ndarray, alfa: int) -> float:
    """FGT(alfa) en %: solo cuentan los que están por debajo de la línea (con alfa=0, 0**0 sería 1 para todos)."""
    pobre = y < z
    return float(np.sum(w[pobre] * ((z[pobre] - y[pobre]) / z[pobre]) ** alfa) / np.sum(w) * 100)


def _grupo(d: pd.DataFrame) -> dict:
    y, w = d["ingreso_pc"].to_numpy(float), (d["fex"] * d["personas"]).to_numpy(float)
    z, zi = d["linea_pobreza"].to_numpy(float), d["linea_pobreza_extrema"].to_numpy(float)
    total = float(np.sum(w))
    return {
        "personas": total,
        "hogares": float(d["fex"].sum()),
        "hogares_muestra": len(d),
        "pobres": float(np.sum(w * d["pobre"])),
        "pobres_extremos": float(np.sum(w * d["pobre_extremo"])),
        "incidencia": _fgt(y, z, w, 0),
        "incidencia_extrema": _fgt(y, zi, w, 0),
        "brecha": _fgt(y, z, w, 1),
        "brecha_extrema": _fgt(y, zi, w, 1),
        "severidad": _fgt(y, z, w, 2),
        "severidad_extrema": _fgt(y, zi, w, 2),
        "gini": weighted_gini(y, w),
        "ingreso_pc": float(np.sum(w * y) / total),
        "linea_pobreza": float(np.sum(w * z) / total),
        "linea_pobreza_extrema": float(np.sum(w * zi) / total),
    }


def indicadores(df: pd.DataFrame, por: str | Iterable[str] | None = None, dropna: bool = True) -> pd.DataFrame:
    """
    Incidencia, brecha y severidad de la pobreza y la pobreza extrema, Gini e ingreso per cápita, por grupo.

    Las cifras son de personas: cada hogar pesa ``fex * personas``, y cada persona cuenta con el ingreso per cápita de su
    unidad de gasto. Con los datos de :func:`load` reproduce los anexos del DANE.

    Parámetros
    ----------
    df
        Hogares de :func:`load`.
    por
        Columna o lista de columnas para agrupar, por ejemplo ``"anio"`` o ``["anio", "grupo_dominio"]``. ``None`` da una
        sola fila.
    dropna
        Quitar los hogares sin dato en ``por``. Con False, los grupos suman el total.

    Devuelve
    --------
    DataFrame
        Una fila por grupo con ``personas`` y ``hogares`` (expandidos), ``hogares_muestra`` (encuestados), ``pobres``,
        ``pobres_extremos`` (personas), ``incidencia``, ``incidencia_extrema``, ``brecha``, ``brecha_extrema``,
        ``severidad``, ``severidad_extrema`` (en %), ``gini``, ``ingreso_pc``, ``linea_pobreza`` y
        ``linea_pobreza_extrema`` (promedios por persona, pesos al mes). Vea ``GLOSARIO``.

    Lanza
    -----
    ValueError
        Si faltan las variables armonizadas, a un hogar le falta un dato, o ``df`` junta varios años, metodologías o
        datos con y sin empalme sin que estén en ``por``: un promedio de ellos no es ninguna cifra publicada.

    Véase también
    -------------
    serie_indicadores : Lo mismo, año por año y guardado en disco.
    load : Los hogares.

    Notas
    -----
    El factor de expansión del archivo anual ya reparte la población entre los 12 meses: con ``por="mes"``, ``personas``
    es lo que aporta cada mes (cerca de un doceavo) y las tasas son las del mes.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> hog = pd.DataFrame({"anio": 2025, "ingreso_pc": [100.0, 300.0], "linea_pobreza": 200.0,
    ...                     "linea_pobreza_extrema": 120.0, "pobre": [True, False], "pobre_extremo": [True, False],
    ...                     "fex": [10.0, 10.0], "personas": [3, 1]})
    >>> dd.pobreza.indicadores(hog)[["personas", "incidencia", "brecha", "gini"]]
       personas  incidencia  brecha  gini
    0      40.0        75.0    37.5  0.25
    """
    faltan = [c for c in _NECESARIAS if c not in df.columns]
    if faltan:
        raise ValueError(f"Faltan {faltan}: use dd.pobreza.load(...) con harmonize_vars=True.")
    llaves = _as_list(por)
    base = df.dropna(subset=llaves) if (llaves and dropna) else df
    if (vacios := base[list(_NECESARIAS)].isna().sum()).any():
        raise ValueError(f"Hogares sin dato: {vacios[vacios > 0].to_dict()}.")
    for c in _CONTEXTO:
        if c in base.columns and c not in llaves and base[c].nunique() > 1:
            raise ValueError(f"Los datos tienen varios valores de {c} ({sorted(base[c].unique().tolist())}): agregue "
                             f"{c!r} a por.")
    if not llaves:
        return pd.DataFrame([_grupo(base)])
    filas = {clave: _grupo(d) for clave, d in base.groupby(llaves, observed=True, dropna=False, sort=True)}
    res = pd.DataFrame.from_dict(filas, orient="index")
    res.index = pd.MultiIndex.from_tuples([k if isinstance(k, tuple) else (k,) for k in res.index], names=llaves)
    return _con_categorias(res.reset_index(), base, llaves)
