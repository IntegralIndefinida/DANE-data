"""Indicadores de mercado laboral a partir de la GEIH armonizada."""

from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from ..stats import _as_list, peso_mensual_promedio, weighted_mean, weighted_quantile
from .loader import _HARMONIZE_VERSION, CATEGORIAS, _firma_archivos, _root, find_months, load

log = logging.getLogger("dane_data.geih")

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


# --------------------------------------------------------------------------- #
# Serie precalculada (caché en disco por año)
# --------------------------------------------------------------------------- #
# Lo que lee `indicadores` más las desagregaciones y filtros de la app.
VARIABLES_INDICADORES = ["anio", "mes", "fex", "pet", "fuerza_trabajo", "ocupado", "desocupado", "inactivo",
                         "formal", "ingreso_laboral", "sexo", "zona", "edad", "grupo_edad", "nivel_educativo",
                         "departamento"]
POR_PRECALCULADOS = (None, "sexo", "zona", "grupo_edad", "nivel_educativo", "departamento")


@lru_cache(maxsize=1)
def _firma_codigo() -> str:
    """Hash del código que produce los indicadores: si cambia, la caché se recalcula sola."""
    from .. import __version__

    base = Path(__file__).resolve().parent.parent
    h = hashlib.sha1(__version__.encode())
    for rel in ("geih/loader.py", "geih/indicadores.py", "stats.py", "referencias.py", "_io.py"):
        try:
            h.update((base / rel).read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:16]


def _ruta_serie(anio: int, meses: list, empalme: bool) -> Path:
    firma = [_HARMONIZE_VERSION, _firma_codigo(), *(s for m in meses for s in _firma_archivos(m))]
    digest = hashlib.sha1("|".join(firma).encode()).hexdigest()[:16]
    serie = "empalme" if empalme else "principal"
    return config.CACHE_DIR / "geih" / "indicadores" / f"{serie}_{anio}_{digest}.parquet"


def _calcular_anio(anio: int, empalme: bool, root) -> pd.DataFrame:
    """Todas las desagregaciones de un año en formato largo (``desagregacion``, ``anual``, ``grupo``)."""
    df = load(anio, empalme=empalme, root=root, variables=VARIABLES_INDICADORES)
    partes = []
    for por in POR_PRECALCULADOS:
        for anual in (True, False):
            r = indicadores(df, por=por, anual=anual)
            if por:
                r = r.rename(columns={por: "grupo"}).astype({"grupo": object})
            partes.append(r.assign(desagregacion=por or "total", anual=anual))
    return pd.concat(partes, ignore_index=True)


def serie_indicadores(
    anios: Iterable[int] | int,
    por: str | None = None,
    anual: bool = True,
    empalme: bool = False,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Lo mismo que ``indicadores(load(anios), por=por, anual=anual)``, pero sin
    juntar los microdatos de todos los años en memoria.

    Cada año se calcula por separado (con todos sus meses completos y todas las
    desagregaciones de ``POR_PRECALCULADOS``) y se guarda en
    ``~/.cache/dane_data/geih/indicadores``. La primera vez tarda unos segundos
    por año; después es instantáneo. Se recalcula solo si cambian los archivos
    del año (p. ej. un mes nuevo) o el código de dane-data.

    Para filtrar (sexo, edad, meses...) o desagregar por otras variables, use
    ``indicadores`` sobre ``load(..., variables=VARIABLES_INDICADORES)``.

    >>> dd.geih.serie_indicadores(range(2007, 2026))                 # TD, TGP... por año
    >>> dd.geih.serie_indicadores(range(2021, 2026), por="sexo", anual=False)
    """
    if por not in POR_PRECALCULADOS:
        raise ValueError(f"por={por!r} no está precalculado (opciones: {list(POR_PRECALCULADOS)}). Use "
                         "dd.geih.indicadores(dd.geih.load(..., variables=dd.geih.VARIABLES_INDICADORES), por=...).")
    por_anio: dict[int, list] = {}
    for m in find_months(anios, empalme=empalme, root=root):
        if m.completo:  # load omite los incompletos
            por_anio.setdefault(m.anio, []).append(m)
    if not por_anio:
        raise FileNotFoundError(
            f"No hay datos GEIH para años={anios} en {_root(empalme, root)}. "
            "Descárguelos con dane_data.geih.download(...) o revise dane_data.set_paths(...)."
        )

    partes = []
    for i, (anio, meses) in enumerate(sorted(por_anio.items())):
        ruta = _ruta_serie(anio, meses, empalme)
        tabla = None
        if ruta.exists():
            try:
                tabla = pd.read_parquet(ruta)
            except Exception:  # caché corrupta: se regenera
                tabla = None
        if tabla is None:
            if progress:
                progress(i / len(por_anio), f"Calculando indicadores de {anio} (solo la primera vez)")
            tabla = _calcular_anio(anio, empalme, root)
            try:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                tmp = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")  # varias sesiones de la app a la vez
                tabla.to_parquet(tmp, index=False)
                tmp.replace(ruta)
            except Exception as e:  # disco lleno, sin permisos, etc.
                log.debug(f"No se pudo guardar caché {ruta}: {e}")
        partes.append(tabla[(tabla["desagregacion"] == (por or "total")) & (tabla["anual"] == anual)])
    if progress:
        progress(1.0, "Listo")

    res = pd.concat(partes, ignore_index=True)
    keys = ["anio"] + ([] if anual else ["mes"])
    if not anual:
        res["mes"] = res["mes"].astype("int64")
    if por:
        res[por] = res["grupo"].astype(CATEGORIAS[por])
        keys.append(por)
    return res[keys + _COLUMNAS]
