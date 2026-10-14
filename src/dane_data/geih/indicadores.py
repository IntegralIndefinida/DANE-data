"""Indicadores de mercado laboral a partir de la GEIH armonizada."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _as_list, peso_mensual_promedio, weighted_mean, weighted_quantile

GLOSARIO = {
    "PET": "Población en edad de trabajar. Desde 2022 (marco 2018): 15 años o más. "
           "Antes: 12+ en zonas urbanas y 10+ en rurales.",
    "FT": "Fuerza de trabajo (antes PEA): personas ocupadas + desocupadas.",
    "TGP": "Tasa global de participación = FT / PET × 100. ¿Qué parte de quienes pueden trabajar participa en el mercado laboral?",
    "TO": "Tasa de ocupación = Ocupados / PET × 100.",
    "TD": "Tasa de desocupación = Desocupados / FT × 100. El 'desempleo'.",
    "Informalidad": "Ocupados que NO están afiliados a salud y cotizando a pensión, sobre el total de ocupados × 100. "
                    "Es una definición por seguridad social; la oficial del DANE usa además tamaño de empresa.",
    "Ingreso laboral": "INGLABO: ingresos laborales mensuales (pesos corrientes) imputados por el DANE.",
}
_COLUMNAS = ["pet", "fuerza_trabajo", "ocupados", "desocupados", "inactivos", "tgp", "to", "td",
             "tasa_informalidad", "ingreso_medio", "ingreso_mediano", "n_muestra"]


def indicadores(df: pd.DataFrame, por: str | Iterable[str] | None = None, anual: bool = True) -> pd.DataFrame:
    """
    Indicadores de mercado laboral ponderados.

    Parámetros
    ----------
    df
        DataFrame de ``dane_data.geih.load`` (con variables armonizadas).
    por
        Variable(s) para desagregar, p. ej. ``"sexo"`` o ``["zona", "nivel_educativo"]``.
    anual
        Si True, promedia los meses de cada año; si False, un resultado por mes.

    Devuelve
    --------
    DataFrame
        Niveles (personas, promedio mensual) y tasas en %:
        ``pet, fuerza_trabajo, ocupados, desocupados, inactivos, tgp, to, td,
        tasa_informalidad, ingreso_medio, ingreso_mediano, n_muestra``.
    """
    por = _as_list(por)
    time_keys = ["anio"] if anual else ["anio", "mes"]
    keys = time_keys + por

    # Solo las sumas ponderadas que hacen falta: copiar el frame entero duplica la memoria
    # con muchos años.
    w = (peso_mensual_promedio(df) if anual else df["fex"]).to_numpy("float64")

    def es(col: str) -> np.ndarray:
        return df[col].to_numpy("float64", na_value=0) == 1

    ocupado = es("ocupado")
    sumas = pd.DataFrame({
        "pet": np.where(es("pet"), w, 0.0),
        "fuerza_trabajo": np.where(es("fuerza_trabajo"), w, 0.0),
        "ocupados": np.where(ocupado, w, 0.0),
        "desocupados": np.where(es("desocupado"), w, 0.0),
        "inactivos": np.where(es("inactivo"), w, 0.0),
        "informales": np.where(ocupado & (df["formal"].to_numpy("float64", na_value=np.nan) == 0), w, 0.0),
    }, index=df.index)
    g = sumas.groupby([df[k] for k in keys], observed=True, dropna=False)
    res = g.sum()
    res["n_muestra"] = g.size()
    with np.errstate(divide="ignore", invalid="ignore"):
        res["tgp"] = 100 * res["fuerza_trabajo"] / res["pet"]
        res["to"] = 100 * res["ocupados"] / res["pet"]
        res["td"] = 100 * res["desocupados"] / res["fuerza_trabajo"]
        res["tasa_informalidad"] = 100 * res["informales"] / res["ocupados"]

    ingreso = df["ingreso_laboral"].to_numpy("float64", na_value=np.nan)
    con_ingreso = ocupado & (ingreso > 0)
    if con_ingreso.any():
        ocup = df.loc[con_ingreso, keys].assign(_y=ingreso[con_ingreso], _w=w[con_ingreso])
        gi = ocup.groupby(keys, observed=True, dropna=False)
        res["ingreso_medio"] = gi.apply(lambda x: weighted_mean(x["_y"], x["_w"]))
        res["ingreso_mediano"] = gi.apply(lambda x: weighted_quantile(x["_y"], x["_w"], 0.5))
    else:
        res["ingreso_medio"] = np.nan
        res["ingreso_mediano"] = np.nan

    res = res.replace([np.inf, -np.inf], np.nan).reset_index()
    return res[keys + _COLUMNAS]
