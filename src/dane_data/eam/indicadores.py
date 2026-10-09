"""Indicadores industriales y utilidades de panel para la EAM."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _as_list

GLOSARIO = {
    "Producción bruta": "Valor total de lo producido por el establecimiento en el año (prodbr2).",
    "Consumo intermedio": "Insumos, materias primas, energía y servicios usados en la producción (consin2).",
    "Valor agregado": "Producción bruta − consumo intermedio (valagri). Es la contribución al PIB.",
    "Personal ocupado": "pertotal: permanentes + propietarios + temporales directos + temporales por agencia.",
    "Productividad laboral": "Valor agregado por persona ocupada (valagri / pertotal).",
    "Remuneración media": "(Salarios + prestaciones de permanentes y temporales) / empleados permanentes y temporales.",
    "Participación laboral": "Remuneraciones / valor agregado × 100: qué parte del valor agregado se paga al trabajo.",
    "Panel": "Seguimiento del mismo establecimiento (nordest) a través de los años.",
}


def resumen(df: pd.DataFrame, por: str | Iterable[str] | None = ("anio",)) -> pd.DataFrame:
    """
    Agregados industriales por grupo (sumas sobre establecimientos).
    Montos en miles de pesos corrientes; ``productividad_laboral`` y
    ``remuneracion_media`` en miles de pesos por persona.

    >>> dd.eam.resumen(eam, por=["anio", "sector"])
    """
    por = _as_list(por)
    d = df.copy()
    num = lambda c: pd.to_numeric(d[c], errors="coerce") if c in d.columns else np.nan  # noqa: E731
    d["_rem"] = num("salpeyte") + num("prespyte")
    sums = {
        "produccion_bruta": "prodbr2", "consumo_intermedio": "consin2", "valor_agregado": "valagri",
        "ventas": "valorven", "personal_total": "pertotal", "empleados_perm_temp": "pperytem",
        "remuneraciones": "_rem", "activos_fijos": "activfi", "inversion_bruta": "invebrta",
        "energia_kwh": "eelec",
    }
    agg = {k: (v, "sum") for k, v in sums.items() if v in d.columns}
    agg["establecimientos"] = ("nordest", "nunique") if "nordest" in d.columns else ("anio", "size")
    if "nordemp" in d.columns:
        agg["empresas"] = ("nordemp", "nunique")
    for v in set(sums.values()):
        if v in d.columns:
            d[v] = pd.to_numeric(d[v], errors="coerce")

    res = (d.groupby(por, observed=True, dropna=False).agg(**agg) if por
           else d.agg(**agg).T.reset_index(drop=True))
    with np.errstate(divide="ignore", invalid="ignore"):
        if {"valor_agregado", "personal_total"} <= set(res.columns):
            res["productividad_laboral"] = res["valor_agregado"] / res["personal_total"]
        if {"remuneraciones", "empleados_perm_temp"} <= set(res.columns):
            res["remuneracion_media"] = res["remuneraciones"] / res["empleados_perm_temp"]
        if {"remuneraciones", "valor_agregado"} <= set(res.columns):
            res["participacion_laboral"] = 100 * res["remuneraciones"] / res["valor_agregado"]
        if {"valor_agregado", "produccion_bruta"} <= set(res.columns):
            res["tasa_valor_agregado"] = 100 * res["valor_agregado"] / res["produccion_bruta"]
    res = res.replace([np.inf, -np.inf], np.nan)
    return res.reset_index() if por else res


def participacion(df: pd.DataFrame, variable: str = "valagri", por: str = "sector", tiempo: str = "anio") -> pd.DataFrame:
    """Participación % de cada grupo en el total de ``variable`` por año."""
    d = df.groupby([tiempo, por], observed=True)[variable].sum().reset_index()
    d["participacion"] = 100 * d[variable] / d.groupby(tiempo)[variable].transform("sum")
    return d


def crecimiento(df: pd.DataFrame, valor: str, por: str | Iterable[str] | None = None, tiempo: str = "anio") -> pd.DataFrame:
    """Agrega la tasa de crecimiento anual (%) de ``valor`` dentro de cada grupo."""
    por = _as_list(por)
    d = df.sort_values(por + [tiempo]).copy()
    prev = d.groupby(por)[valor].shift() if por else d[valor].shift()
    d[f"crec_{valor}"] = 100 * (d[valor] / prev - 1)
    return d


def deflactar(df: pd.DataFrame, columnas: Iterable[str], deflactor: pd.DataFrame | pd.Series,
              on: str | list[str] = "anio", base: float = 100.0, sufijo: str = "_real") -> pd.DataFrame:
    """
    Convierte valores corrientes a constantes: ``valor_real = valor / deflactor × base``.

    ``deflactor`` puede ser una Serie indexada por año o un DataFrame con las
    columnas de ``on`` (p. ej. ``["anio", "division"]``) y una columna ``deflactor``.
    """
    on = _as_list(on)
    d = df.copy()
    if isinstance(deflactor, pd.Series):
        deflactor = deflactor.rename("deflactor").rename_axis(on[0]).reset_index()
    d = d.merge(deflactor[on + ["deflactor"]], on=on, how="left")
    for c in columnas:
        d[f"{c}{sufijo}"] = pd.to_numeric(d[c], errors="coerce") / d["deflactor"] * base
    faltan = d["deflactor"].isna().mean()
    if faltan > 0:
        import warnings
        warnings.warn(f"{faltan:.1%} de las filas no encontraron deflactor.")
    return d


def panel(df: pd.DataFrame, balanceado: bool = False, anios: Iterable[int] | None = None) -> pd.DataFrame:
    """
    Panel establecimiento-año indexado por (``nordest``, ``anio``).

    ``balanceado=True`` conserva solo establecimientos observados en todos los
    años de ``anios`` (por defecto, todos los años presentes en ``df``).

    Ojo: la anonimización de ANDA puede cambiar los identificadores entre
    catálogos; revise la persistencia con ``dd.eam.supervivencia``.
    """
    d = df.dropna(subset=["nordest"]).copy()
    anios = sorted(set(anios) if anios is not None else d["anio"].unique())
    d = d[d["anio"].isin(anios)]
    d = d.drop_duplicates(subset=["nordest", "anio"])
    if balanceado:
        n = d.groupby("nordest")["anio"].nunique()
        d = d[d["nordest"].isin(n[n == len(anios)].index)]
    return d.set_index(["nordest", "anio"]).sort_index()


def supervivencia(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cuántos establecimientos de cada año reaparecen al año siguiente.
    Caídas bruscas indican cambios de identificador (no cierres reales).
    """
    ids = df.dropna(subset=["nordest"]).groupby("anio")["nordest"].apply(set).sort_index()
    rows = []
    for (y0, a), (y1, b) in zip(ids.items(), list(ids.items())[1:]):
        rows.append({"anio": y0, "siguiente": y1, "establecimientos": len(a),
                     "siguen_al_anio_siguiente": len(a & b), "pct_siguen": 100 * len(a & b) / max(len(a), 1)})
    return pd.DataFrame(rows)
