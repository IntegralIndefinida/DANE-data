"""Estadísticas ponderadas por factor de expansión."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


def _as_list(x) -> list:
    if x is None:
        return []
    return [x] if isinstance(x, str) else list(x)


def peso_mensual_promedio(df: pd.DataFrame, peso: str = "fex") -> pd.Series:
    """
    Peso que convierte totales de varios meses en un *promedio mensual*.

    El factor de expansión de la GEIH es mensual: si se juntan 12 meses, la
    suma de ``fex`` es 12 veces la población. Este peso divide ``fex`` por el
    número de meses distintos de cada año presentes en ``df``. Sumarlo
    equivale al promedio de los totales mensuales (método DANE para
    agregados trimestrales/anuales).

    Parámetros
    ----------
    df
        Microdatos con ``anio``, ``mes`` y la columna del peso. Sin ``anio`` o ``mes`` se devuelve el
        peso tal cual.
    peso
        Columna del factor de expansión.

    Devuelve
    --------
    Series
        El peso dividido por el número de meses de cada año.

    Notas
    -----
    Los meses se cuentan en ``df``: si un filtro deja un mes sin ninguna fila (un grupo pequeño), el
    promedio se toma sobre los meses restantes. Para promediar sobre los meses que se cargaron, ponga
    ``df.attrs["meses_por_anio"] = {anio: número de meses}``; así lo hacen ``geih.serie_indicadores``,
    ``geih.serie_tabla`` y ``geih.serie_frecuencias``.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> from dane_data.stats import peso_mensual_promedio
    >>> df = pd.DataFrame({"anio": [2024, 2024, 2024], "mes": [1, 2, 2], "fex": [100.0, 90.0, 30.0]})
    >>> peso_mensual_promedio(df).tolist()
    [50.0, 45.0, 15.0]
    >>> df.attrs["meses_por_anio"] = {2024: 4}  # se cargaron 4 meses; en dos no quedó nadie
    >>> peso_mensual_promedio(df).tolist()
    [25.0, 22.5, 7.5]
    """
    if "mes" not in df.columns or "anio" not in df.columns:
        return df[peso]
    n_meses = df.groupby("anio", observed=True)["mes"].transform("nunique")
    if meses := df.attrs.get("meses_por_anio"):
        n_meses = df["anio"].astype("int64").map(meses).fillna(n_meses)
    return df[peso] / n_meses


def weighted_quantile(values, weights, q: float) -> float:
    """
    Cuantil ponderado.

    Es el menor valor cuya masa acumulada alcanza la fracción ``q`` del peso total, la misma definición
    de ``_pctile`` en Stata. Siempre devuelve uno de los valores observados (no interpola).

    Parámetros
    ----------
    values
        Valores (cualquier secuencia numérica).
    weights
        Pesos, del mismo largo que ``values``. Se ignoran los pares con algún NaN y los pesos que no son
        positivos.
    q
        Fracción entre 0 y 1: 0.5 es la mediana.

    Devuelve
    --------
    float
        El cuantil, o NaN si no queda ningún valor.

    Véase también
    -------------
    weighted_mean : Media ponderada.
    tabla : Medianas ponderadas por grupo.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.weighted_quantile([10, 20, 30], [1, 1, 1], 0.5)
    20.0
    >>> dd.weighted_quantile([10, 20, 30], [5, 1, 1], 0.5)
    10.0
    """
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = ~(np.isnan(v) | np.isnan(w)) & (w > 0)
    v, w = v[mask], w[mask]
    if v.size == 0:
        return np.nan
    order = np.argsort(v, kind="stable")
    v, w = v[order], w[order]
    # CDF inversa: el menor valor cuya masa acumulada alcanza q (como _pctile de Stata).
    cum = np.cumsum(w)
    return float(v[np.searchsorted(cum, q * cum[-1], side="left")])


def weighted_mean(values, weights) -> float:
    """
    Media ponderada.

    Parámetros
    ----------
    values
        Valores (cualquier secuencia numérica).
    weights
        Pesos, del mismo largo que ``values``. Se ignoran los pares con algún NaN.

    Devuelve
    --------
    float
        La media, o NaN si no quedan valores o los pesos suman 0.

    Véase también
    -------------
    weighted_quantile : Cuantiles ponderados (por ejemplo, la mediana).
    tabla : Medias ponderadas por grupo.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.weighted_mean([10, 20, 30], [1, 1, 2])
    22.5
    >>> dd.weighted_mean([10, None, 30], [1, 1, 1])
    20.0
    """
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    mask = ~(np.isnan(v) | np.isnan(w))
    return float(np.average(v[mask], weights=w[mask])) if mask.any() and w[mask].sum() > 0 else np.nan


def tabla(
    df: pd.DataFrame,
    por: str | Iterable[str] | None = None,
    variable: str | None = None,
    estadistico: str = "total",
    peso: str | None = "fex",
) -> pd.DataFrame:
    """
    Tabla ponderada de cualquier variable.

    Expande la muestra con el factor de expansión y, si hay varios meses de un mismo año, convierte los
    totales en promedios mensuales, como el DANE. Sirve para la GEIH y para cualquier otra tabla con
    pesos.

    Parámetros
    ----------
    df
        Microdatos, una fila por persona (por ejemplo, de ``dd.geih.load``).
    por
        Variable o lista de variables que definen los grupos. Sin ``por``, una sola fila con todo
        ``df``.
    variable
        Variable numérica para ``"media"`` y ``"mediana"``. Las filas donde está vacía se descartan
        también con ``"total"`` y ``"porcentaje"``.
    estadistico
        ``"total"``: personas (promedio mensual) en cada grupo.
        ``"porcentaje"``: distribución de la *última* variable de ``por`` dentro de las demás; por
        ejemplo, con ``por=["anio", "sexo"]``, el porcentaje de cada sexo en cada año.
        ``"media"`` o ``"mediana"``: de ``variable``, ponderadas, en cada grupo.
    peso
        Columna del factor de expansión. ``None`` cuenta observaciones sin expandir.

    Devuelve
    --------
    DataFrame
        Una fila por grupo con las columnas de ``por``, el estadístico (``total``, ``porcentaje``,
        ``media`` o ``mediana``; ``"porcentaje"`` trae también ``total``) y ``n_muestra``, el número de
        observaciones sin expandir.

    Lanza
    -----
    ValueError
        Si ``estadistico`` no es uno de los cuatro, o falta ``variable`` para la media o la mediana.

    Véase también
    -------------
    dane_data.geih.serie_tabla : La misma tabla para muchos años, sin cargarlos en memoria.
    weighted_mean : Media ponderada de una sola serie.
    weighted_quantile : Cuantil ponderado de una sola serie.

    Notas
    -----
    Con pocas observaciones las cifras expandidas no son confiables: revise ``n_muestra`` y desconfíe de
    los grupos con menos de unas 30 a 100 personas.

    La mediana es la de ``weighted_quantile`` (el menor valor que acumula la mitad del peso).

    Ejemplos
    --------
    Dos meses de una muestra con seis personas. Cada total es el promedio de los dos meses:

    >>> import pandas as pd
    >>> import dane_data as dd
    >>> df = pd.DataFrame({
    ...     "anio": 2024, "mes": [1, 1, 1, 2, 2, 2],
    ...     "sexo": ["Mujer", "Hombre", "Mujer", "Mujer", "Hombre", "Hombre"],
    ...     "ingreso": [1.2, 2.0, 1.5, 1.3, 2.2, 1.8],
    ...     "fex": [100.0, 150.0, 50.0, 120.0, 90.0, 110.0],
    ... })
    >>> dd.tabla(df, por="sexo")
         sexo  total  n_muestra
    0  Hombre  175.0          3
    1   Mujer  135.0          3
    >>> dd.tabla(df, por="sexo", estadistico="porcentaje").round(1)
         sexo  total  n_muestra  porcentaje
    0  Hombre  175.0          3        56.5
    1   Mujer  135.0          3        43.5
    >>> dd.tabla(df, por="sexo", variable="ingreso", estadistico="mediana")
         sexo  mediana  n_muestra
    0  Hombre      2.0          3
    1   Mujer      1.3          3

    Con la GEIH:

    >>> df = dd.geih.load(2024)  # doctest: +SKIP
    >>> dd.tabla(df, por=["anio", "nivel_educativo"], estadistico="porcentaje")  # doctest: +SKIP
    >>> dd.tabla(df[df.ocupado == 1], por="sexo", variable="ingreso_laboral", estadistico="mediana")  # doctest: +SKIP
    """
    por = _as_list(por)
    d = df.copy()
    if peso is None:
        d["_w"] = 1.0
    else:
        d["_w"] = peso_mensual_promedio(d, peso)
    if variable is not None:
        d = d[d[variable].notna()]
    g = d.groupby(por, observed=True, dropna=False) if por else None

    if estadistico in ("total", "porcentaje"):
        if g is None:
            res = pd.DataFrame({"total": [d["_w"].sum()], "n_muestra": [len(d)]})
        else:
            res = g.agg(total=("_w", "sum"), n_muestra=("_w", "size")).reset_index()
        if estadistico == "porcentaje":
            outer = por[:-1]
            denom = res.groupby(outer, observed=True)["total"].transform("sum") if outer else res["total"].sum()
            res["porcentaje"] = 100 * res["total"] / denom
        return res

    if variable is None:
        raise ValueError("Indique `variable` para media/mediana.")
    if estadistico == "media":
        fn = lambda x: weighted_mean(x[variable], x["_w"])  # noqa: E731
    elif estadistico == "mediana":
        fn = lambda x: weighted_quantile(x[variable], x["_w"], 0.5)  # noqa: E731
    else:
        raise ValueError("estadistico debe ser 'total', 'porcentaje', 'media' o 'mediana'.")
    if g is None:
        return pd.DataFrame({estadistico: [fn(d)], "n_muestra": [len(d)]})
    stat = g[[variable, "_w"]].apply(fn).rename(estadistico)
    n = g.size().rename("n_muestra")
    return pd.concat([stat, n], axis=1).reset_index()
