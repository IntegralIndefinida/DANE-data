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
    """
    if "mes" not in df.columns or "anio" not in df.columns:
        return df[peso]
    n_meses = df.groupby("anio", observed=True)["mes"].transform("nunique")
    return df[peso] / n_meses


def weighted_quantile(values, weights, q: float) -> float:
    """Cuantil ``q`` (0–1) ponderado: el menor valor cuya masa acumulada alcanza ``q`` (como ``_pctile`` de
    Stata). Ignora los NaN y los pesos no positivos."""
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
    """Media ponderada. Ignora los NaN de ``values`` y de ``weights``."""
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
    Tabla ponderada para cualquier variable.

    estadistico:
      * ``"total"``      población expandida (promedio mensual) por grupo.
      * ``"porcentaje"`` distribución porcentual de la *última* columna de ``por``
        dentro de las demás (p. ej. ``por=["anio", "sexo"]`` → % por sexo en cada año).
      * ``"media"``, ``"mediana"``  de ``variable`` (numérica) por grupo.

    Siempre agrega ``n_muestra`` (observaciones sin expandir). Grupos con
    menos de ~30 observaciones no son confiables.

    >>> dd.tabla(df, por=["anio", "nivel_educativo"], estadistico="porcentaje")
    >>> dd.tabla(df[df.ocupado == 1], por="sexo", variable="ingreso_laboral", estadistico="mediana")
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
