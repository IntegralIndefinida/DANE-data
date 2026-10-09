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


def indicadores(df: pd.DataFrame, por: str | Iterable[str] | None = None, anual: bool = True) -> pd.DataFrame:
    """
    Indicadores de mercado laboral ponderados.

    Parámetros
    ----------
    df : DataFrame de ``dane_data.geih.load`` (con variables armonizadas).
    por : variable(s) para desagregar, p. ej. ``"sexo"`` o ``["zona", "nivel_educativo"]``.
    anual : si True, promedia los meses de cada año; si False, un resultado por mes.

    Devuelve niveles (personas, promedio mensual) y tasas en %:
    ``pet, fuerza_trabajo, ocupados, desocupados, inactivos, tgp, to, td,
    tasa_informalidad, ingreso_medio, ingreso_mediano, n_muestra``.
    """
    por = _as_list(por)
    time_keys = ["anio"] if anual else ["anio", "mes"]
    keys = time_keys + por

    d = df[[c for c in set(keys) | {"anio", "mes", "fex", "pet", "fuerza_trabajo", "ocupado",
                                    "desocupado", "inactivo", "formal", "ingreso_laboral"} if c in df.columns]].copy()
    d["_w"] = peso_mensual_promedio(d) if anual else d["fex"]
    for c in ("pet", "fuerza_trabajo", "ocupado", "desocupado", "inactivo"):
        d[f"_{c}"] = d["_w"] * d[c].fillna(0).astype(float)
    d["_informal"] = d["_w"] * ((d["ocupado"] == 1) & (d["formal"] == 0)).astype(float)

    g = d.groupby(keys, observed=True, dropna=False)
    res = g.agg(
        pet=("_pet", "sum"),
        fuerza_trabajo=("_fuerza_trabajo", "sum"),
        ocupados=("_ocupado", "sum"),
        desocupados=("_desocupado", "sum"),
        inactivos=("_inactivo", "sum"),
        informales=("_informal", "sum"),
        n_muestra=("_w", "size"),
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        res["tgp"] = 100 * res["fuerza_trabajo"] / res["pet"]
        res["to"] = 100 * res["ocupados"] / res["pet"]
        res["td"] = 100 * res["desocupados"] / res["fuerza_trabajo"]
        res["tasa_informalidad"] = 100 * res["informales"] / res["ocupados"]

    ocup = d[(d["ocupado"] == 1) & (d["ingreso_laboral"] > 0)]
    if len(ocup):
        gi = ocup.groupby(keys, observed=True, dropna=False)
        res["ingreso_medio"] = gi.apply(lambda x: weighted_mean(x["ingreso_laboral"], x["_w"]))
        res["ingreso_mediano"] = gi.apply(lambda x: weighted_quantile(x["ingreso_laboral"], x["_w"], 0.5))
    else:
        res["ingreso_medio"] = np.nan
        res["ingreso_mediano"] = np.nan

    res = res.replace([np.inf, -np.inf], np.nan).reset_index()
    cols = keys + ["pet", "fuerza_trabajo", "ocupados", "desocupados", "inactivos", "tgp", "to", "td",
                   "tasa_informalidad", "ingreso_medio", "ingreso_mediano", "n_muestra"]
    return res[cols]
