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
    r"""
    Indicadores del mercado laboral, ponderados como los calcula el DANE.

    Parámetros
    ----------
    df
        Microdatos armonizados de ``load``. Necesita ``anio``, ``mes``, ``fex``, ``pet``,
        ``fuerza_trabajo``, ``ocupado``, ``desocupado``, ``inactivo``, ``formal`` e ``ingreso_laboral``
        (las de ``VARIABLES_INDICADORES``), más las variables de ``por``.
    por
        Variable o lista de variables para desagregar, por ejemplo ``"sexo"`` o
        ``["zona", "nivel_educativo"]``.
    anual
        Si True, un resultado por año: los niveles son el promedio de los meses del año. Si False, uno por
        mes.

    Devuelve
    --------
    DataFrame
        Una fila por año (o mes) y grupo, con:

        * ``pet``, ``fuerza_trabajo``, ``ocupados``, ``desocupados``, ``inactivos``: personas (promedio
          mensual si ``anual=True``).
        * ``tgp``, ``to``, ``td``: tasas global de participación, de ocupación y de desocupación, en %.
        * ``tasa_informalidad``: % de los ocupados sin afiliación a salud y cotización a pensión.
        * ``ingreso_medio``, ``ingreso_mediano``: ingreso laboral mensual de los ocupados con ingreso
          positivo, en pesos corrientes.
        * ``n_muestra``: personas encuestadas (sin expandir) en el grupo.

    Véase también
    -------------
    serie_indicadores : Lo mismo para muchos años, calculado año por año y guardado.
    load : Cargar los microdatos.
    GLOSARIO : Definiciones de cada indicador.

    Notas
    -----
    Cada nivel es la suma del factor de expansión :math:`w_i` de las personas del grupo. Si
    ``anual=True``, :math:`w_i` se divide por el número de meses del año en ``df``, así que el nivel es el
    promedio de los niveles mensuales:

    .. math::

       \mathrm{TGP} = 100\,\frac{FT}{PET}, \qquad
       \mathrm{TO} = 100\,\frac{O}{PET}, \qquad
       \mathrm{TD} = 100\,\frac{D}{FT}

    donde :math:`FT = O + D` es la fuerza de trabajo, :math:`O` los ocupados y :math:`D` los
    desocupados. Las tasas anuales son entonces cocientes de promedios mensuales, como las publica el
    DANE, y no promedios de las tasas mensuales.

    La informalidad es una definición por seguridad social (ver ``formal`` en la guía de variables); la
    oficial del DANE usa además el tamaño de la empresa. La mediana es la de
    ``dane_data.weighted_quantile``.

    Ejemplos
    --------
    Cinco personas con el mismo peso: dos ocupadas (una formal), una desocupada, una inactiva y una
    menor de la edad de trabajar.

    >>> import pandas as pd
    >>> import dane_data as dd
    >>> df = pd.DataFrame({
    ...     "anio": 2024, "mes": 1, "fex": 100.0,
    ...     "pet":            [1, 1, 1, 1, 0],
    ...     "fuerza_trabajo": [1, 1, 1, 0, 0],
    ...     "ocupado":        [1, 1, 0, 0, 0],
    ...     "desocupado":     [0, 0, 1, 0, 0],
    ...     "inactivo":       [0, 0, 0, 1, 0],
    ...     "formal":         [1, 0, None, None, None],
    ...     "ingreso_laboral": [2.0e6, 1.2e6, None, None, None],
    ... })
    >>> dd.geih.indicadores(df)[["anio", "pet", "ocupados", "tgp", "to", "td", "tasa_informalidad"]].round(1)
       anio    pet  ocupados   tgp    to    td  tasa_informalidad
    0  2024  400.0     200.0  75.0  50.0  33.3               50.0

    Con la GEIH de 2024:

    >>> df = dd.geih.load(2024, variables=dd.geih.VARIABLES_INDICADORES)  # doctest: +SKIP
    >>> dd.geih.indicadores(df, por="sexo")[["anio", "sexo", "tgp", "td"]].round(1)  # doctest: +SKIP
       anio    sexo   tgp    td
    0  2024  Hombre  76.4   8.2
    1  2024   Mujer  52.4  12.7
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
