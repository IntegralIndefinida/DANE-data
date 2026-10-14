"""
Resultados de la GEIH calculados año por año y guardados en disco.

Las funciones ``serie_*`` dan lo mismo que cargar todos los años con ``load`` y calcular
encima, pero leen un año a la vez: la memoria no depende de cuántos años se pidan. Cada
año queda en ``~/.cache/dane_data/geih/<tipo>/`` y se recalcula solo si cambian sus
archivos, la solicitud (filtros, meses, variables) o el código de dane-data. ``exportar``
escribe los microdatos armonizados mes a mes, por la misma razón.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from .. import config
from ..referencias import MESES
from ..stats import _as_list, peso_mensual_promedio, weighted_quantile
from .indicadores import _COLUMNAS, indicadores
from .loader import _HARMONIZE_VERSION, CATEGORIAS, MesGEIH, _firma_archivos, _root, find_months, load

log = logging.getLogger("dane_data.geih")

# Lo que lee `indicadores` más las desagregaciones y filtros de la app.
VARIABLES_INDICADORES = ["anio", "mes", "fex", "pet", "fuerza_trabajo", "ocupado", "desocupado", "inactivo",
                         "formal", "ingreso_laboral", "sexo", "zona", "edad", "grupo_edad", "nivel_educativo",
                         "departamento"]
POR_PRECALCULADOS = (None, "sexo", "zona", "grupo_edad", "nivel_educativo", "departamento")
POBLACIONES = ("pet", "fuerza_trabajo", "ocupado", "desocupado", "inactivo")


def filtrar(df: pd.DataFrame, filtros: dict | None = None, poblacion: str | None = None) -> pd.DataFrame:
    """
    Filas que cumplen ``filtros`` y pertenecen a ``poblacion``.

    ``filtros``: ``{columna: [valores]}``, o ``{columna: (mínimo, máximo)}`` para un rango
    (con los extremos), p. ej. ``{"sexo": ["Mujer"], "edad": (15, 28)}``. Si la columna no
    existe (una variable que ese año no trae), nadie cumple el filtro.
    ``poblacion``: una de ``POBLACIONES`` (``"ocupado"``, ``"pet"``...).
    """
    mask = pd.Series(True, index=df.index)
    for col, cond in (filtros or {}).items():
        if col not in df.columns:
            mask &= False
        elif isinstance(cond, tuple):
            mask &= df[col].between(*cond)
        else:
            mask &= df[col].isin(list(cond))
    if poblacion:
        mask &= df[poblacion].eq(1).fillna(False).astype(bool)
    return df if mask.all() else df[mask]


# --------------------------------------------------------------------------- #
# Caché por año
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _firma_codigo() -> str:
    """Hash del código que produce los resultados: si cambia, la caché se recalcula sola."""
    from .. import __version__

    base = Path(__file__).resolve().parent.parent
    h = hashlib.sha1(__version__.encode())
    for rel in ("geih/loader.py", "geih/indicadores.py", "geih/agregados.py", "stats.py", "referencias.py",
                "_io.py"):
        try:
            h.update((base / rel).read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:16]


def _meses(meses) -> list[int] | None:
    if meses is None:
        return None
    return sorted({int(m) for m in ([meses] if isinstance(meses, (int, str)) else meses)})


def _meses_por_anio(anios, meses, empalme: bool, root) -> dict[int, list[MesGEIH]]:
    """Meses completos en disco (los que usa ``load``), agrupados por año."""
    meses = _meses(meses)
    por_anio: dict[int, list[MesGEIH]] = {}
    for m in find_months(anios, empalme=empalme, root=root):
        if m.completo and (meses is None or m.mes in meses):
            por_anio.setdefault(m.anio, []).append(m)
    if not por_anio:
        raise FileNotFoundError(
            f"No hay datos GEIH para años={anios}, meses={meses} en {_root(empalme, root)}. "
            "Descárguelos con dane_data.geih.download(...) o revise dane_data.set_paths(...)."
        )
    return por_anio


def _por_anio(tipo: str, anios, solicitud: dict, calcular: Callable[[int], pd.DataFrame], *, meses=None,
              empalme: bool = False, root=None, progress=None) -> list[pd.DataFrame]:
    """``calcular(anio)`` para cada año, leído de la caché si ya se hizo con los mismos archivos y solicitud."""
    por_anio = _meses_por_anio(anios, meses, empalme, root)
    texto = json.dumps(solicitud, sort_keys=True, default=str, ensure_ascii=False)
    serie = "empalme" if empalme else "principal"
    partes = []
    for i, (anio, ms) in enumerate(sorted(por_anio.items())):
        firma = [_HARMONIZE_VERSION, _firma_codigo(), texto, *(s for m in ms for s in _firma_archivos(m))]
        digest = hashlib.sha1("|".join(firma).encode()).hexdigest()[:16]
        ruta = config.CACHE_DIR / "geih" / tipo / f"{serie}_{anio}_{digest}.parquet"
        tabla = None
        if ruta.exists():
            try:
                tabla = pd.read_parquet(ruta)
            except Exception:  # caché corrupta: se regenera
                tabla = None
        if tabla is None:
            if progress:
                progress(i / len(por_anio), f"Calculando {anio} (solo la primera vez)")
            tabla = calcular(anio)
            try:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                tmp = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")  # varias sesiones de la app a la vez
                tabla.to_parquet(tmp, index=False)
                tmp.replace(ruta)
            except Exception as e:  # disco lleno, sin permisos, etc.
                log.debug(f"No se pudo guardar caché {ruta}: {e}")
        partes.append(tabla)
    if progress:
        progress(1.0, "Listo")
    return partes


# --------------------------------------------------------------------------- #
# Indicadores laborales
# --------------------------------------------------------------------------- #
def serie_indicadores(
    anios: Iterable[int] | int,
    por: str | None = None,
    anual: bool = True,
    empalme: bool = False,
    root=None,
    progress=None,
    filtros: dict | None = None,
    meses: Iterable[int] | int | None = None,
) -> pd.DataFrame:
    """
    Lo mismo que ``indicadores(filtrar(load(anios, months=meses), filtros), por=por, anual=anual)``,
    pero sin juntar los microdatos de todos los años en memoria.

    Cada año se calcula por separado (con todas las desagregaciones de
    ``POR_PRECALCULADOS``, anual y mensual) y se guarda. La primera vez tarda unos
    segundos por año; después es instantáneo, también al cambiar ``por`` o ``anual``.
    Para desagregar por otras variables use ``indicadores`` sobre
    ``load(..., variables=VARIABLES_INDICADORES)``.

    >>> dd.geih.serie_indicadores(range(2007, 2026))                 # TD, TGP... por año
    >>> dd.geih.serie_indicadores(range(2021, 2026), por="sexo", anual=False)
    >>> dd.geih.serie_indicadores(range(2015, 2026), filtros={"edad": (15, 28)})   # jóvenes
    """
    if por not in POR_PRECALCULADOS:
        raise ValueError(f"por={por!r} no está precalculado (opciones: {list(POR_PRECALCULADOS)}). Use "
                         "dd.geih.indicadores(dd.geih.load(..., variables=dd.geih.VARIABLES_INDICADORES), por=...).")
    variables = list(dict.fromkeys([*VARIABLES_INDICADORES, *(filtros or {})]))

    def calcular(anio):
        df = filtrar(load(anio, months=meses, empalme=empalme, root=root, variables=variables), filtros)
        partes = []
        for p in POR_PRECALCULADOS:
            for a in (True, False):
                r = indicadores(df, por=p, anual=a)
                if p:
                    r = r.rename(columns={p: "grupo"}).astype({"grupo": object})
                partes.append(r.assign(desagregacion=p or "total", anual=a))
        return pd.concat(partes, ignore_index=True)

    tablas = _por_anio("indicadores", anios, {"filtros": filtros or {}, "meses": _meses(meses)}, calcular,
                       meses=meses, empalme=empalme, root=root, progress=progress)
    res = pd.concat([t[(t["desagregacion"] == (por or "total")) & (t["anual"] == anual)] for t in tablas],
                    ignore_index=True)
    keys = ["anio"] + ([] if anual else ["mes"])
    if not anual:
        res["mes"] = res["mes"].astype("int64")
    if por:
        res[por] = res["grupo"].astype(CATEGORIAS[por])
        keys.append(por)
    return res[keys + _COLUMNAS]


# --------------------------------------------------------------------------- #
# Tablas ponderadas
# --------------------------------------------------------------------------- #
def serie_frecuencias(
    anios: Iterable[int] | int,
    variable: str | None = None,
    por: str | Iterable[str] | None = None,
    poblacion: str | None = None,
    filtros: dict | None = None,
    meses: Iterable[int] | int | None = None,
    columns="core",
    empalme: bool = False,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Distribución ponderada: una fila por año, combinación de ``por`` y valor de ``variable``,
    con ``peso`` (personas, promedio mensual de cada año) y ``n_muestra``.

    Es la base de ``serie_tabla``: de ella salen totales, porcentajes, medias y medianas
    exactas aunque se junten varios años. ``columns`` son las variables DANE extra que
    hay que leer (como en ``load``).

    >>> f = dd.geih.serie_frecuencias(range(2015, 2026), "ingreso_laboral", poblacion="ocupado")
    >>> dd.weighted_quantile(f["ingreso_laboral"], f["peso"], 0.5)   # mediana de todos esos años
    """
    por = [p for p in _as_list(por) if p != "anio"]
    claves = ["anio", *por] + ([variable] if variable else [])
    necesarias = list(dict.fromkeys(["fex", *claves, *(filtros or {}), *([poblacion] if poblacion else [])]))

    def calcular(anio):
        df = load(anio, months=meses, columns=columns, empalme=empalme, root=root, variables=necesarias)
        for c in claves:  # una variable DANE que ese año no existe
            if c not in df.columns:
                df[c] = np.nan
        d = filtrar(df, filtros, poblacion)
        x = d[claves].assign(peso=peso_mensual_promedio(d).to_numpy(), n_muestra=1)
        if variable:
            x = x[x[variable].notna()]
        return x.groupby(claves, observed=True, dropna=False).agg(
            peso=("peso", "sum"), n_muestra=("n_muestra", "sum")).reset_index()

    solicitud = {"variable": variable, "por": sorted(por), "poblacion": poblacion, "filtros": filtros or {},
                 "meses": _meses(meses), "columns": columns}
    tablas = _por_anio("frecuencias", anios, solicitud, calcular, meses=meses, empalme=empalme, root=root,
                       progress=progress)
    return pd.concat(tablas, ignore_index=True)


def serie_tabla(
    anios: Iterable[int] | int,
    por: str | Iterable[str] | None = None,
    variable: str | None = None,
    estadistico: str = "total",
    poblacion: str | None = None,
    filtros: dict | None = None,
    meses: Iterable[int] | int | None = None,
    dropna: bool = False,
    columns="core",
    empalme: bool = False,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Lo mismo que ``dd.tabla(filtrar(load(anios, months=meses), filtros, poblacion), por, variable,
    estadistico)``, calculado año por año y guardado en disco.

    ``dropna=True`` deja fuera a las personas con valor vacío en alguna variable de ``por``
    (p. ej. la rama de actividad de quien no trabaja).

    >>> dd.geih.serie_tabla(range(2015, 2026), por=["anio", "nivel_educativo"], estadistico="porcentaje",
    ...                     poblacion="ocupado")
    >>> dd.geih.serie_tabla([2024, 2025], por="sexo", variable="ingreso_laboral", estadistico="mediana",
    ...                     filtros={"zona": ["Urbano (cabecera)"]})
    """
    por = _as_list(por)
    if estadistico not in ("total", "porcentaje", "media", "mediana"):
        raise ValueError("estadistico debe ser 'total', 'porcentaje', 'media' o 'mediana'.")
    if estadistico in ("media", "mediana") and variable is None:
        raise ValueError("Indique `variable` para media/mediana.")
    f = serie_frecuencias(anios, variable, por, poblacion, filtros, meses, columns, empalme, root, progress)
    if dropna and por:
        f = f.dropna(subset=por)
    return tabla_de_frecuencias(f, por, variable, estadistico)


def tabla_de_frecuencias(f: pd.DataFrame, por: str | Iterable[str] | None = None, variable: str | None = None,
                         estadistico: str = "total") -> pd.DataFrame:
    """Tabla de ``dd.tabla`` a partir de las frecuencias ponderadas de ``serie_frecuencias``."""
    por = _as_list(por)
    if estadistico in ("total", "porcentaje"):
        if not por:
            res = pd.DataFrame({"total": [f["peso"].sum()], "n_muestra": [int(f["n_muestra"].sum())]})
        else:
            res = f.groupby(por, observed=True, dropna=False).agg(
                total=("peso", "sum"), n_muestra=("n_muestra", "sum")).reset_index()
        if estadistico == "porcentaje":
            outer = por[:-1]
            denom = res.groupby(outer, observed=True)["total"].transform("sum") if outer else res["total"].sum()
            res["porcentaje"] = 100 * res["total"] / denom
        return res

    if estadistico == "media":
        def fn(x):
            return float(np.average(x[variable], weights=x["peso"])) if x["peso"].sum() > 0 else np.nan
    else:
        def fn(x):
            return weighted_quantile(x[variable], x["peso"], 0.5)
    if not por:
        return pd.DataFrame({estadistico: [fn(f)], "n_muestra": [int(f["n_muestra"].sum())]})
    g = f.groupby(por, observed=True, dropna=False)
    stat = g[[variable, "peso"]].apply(fn).rename(estadistico)
    n = g["n_muestra"].sum().rename("n_muestra")
    return pd.concat([stat, n], axis=1).reset_index()


# --------------------------------------------------------------------------- #
# Exportar microdatos
# --------------------------------------------------------------------------- #
def exportar(
    anios: Iterable[int] | int,
    ruta,
    variables: Iterable[str] | None = None,
    poblacion: str | None = None,
    filtros: dict | None = None,
    meses: Iterable[int] | int | None = None,
    columns="core",
    empalme: bool = False,
    root=None,
    progress=None,
) -> int:
    """
    Escribe en ``ruta`` (CSV) los microdatos armonizados, una persona por fila, un mes a la vez:
    sirve para muchos años aunque no quepan en memoria. Devuelve el número de filas.

    ``variables``: columnas a escribir (por defecto, las armonizadas). Las variables DANE
    que no están en ``CORE_RAW`` deben pedirse también en ``columns``.

    >>> dd.geih.exportar(range(2015, 2026), "ocupados.csv", poblacion="ocupado")
    """
    ruta = Path(ruta)
    por_anio = _meses_por_anio(anios, meses, empalme, root)
    lista = [m for _, ms in sorted(por_anio.items()) for m in ms]
    necesarias = None
    if variables is not None:
        necesarias = list(dict.fromkeys(["anio", "mes", *variables]))
    leer = list(dict.fromkeys([*(necesarias or []), *(filtros or {}), *([poblacion] if poblacion else [])])) or None
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f"{ruta.name}.{os.getpid()}.tmp")
    filas = 0
    try:
        for i, m in enumerate(lista):
            if progress:
                progress(i / len(lista), f"Exportando {MESES[m.mes]} {m.anio}")
            df = filtrar(load(m.anio, months=m.mes, columns=columns, empalme=empalme, root=root, variables=leer),
                         filtros, poblacion)
            if necesarias is None:  # las armonizadas (minúscula), iguales en todos los meses
                necesarias = [c for c in df.columns if c == c.lower()]
            df.reindex(columns=necesarias).to_csv(tmp, mode="w" if i == 0 else "a", header=i == 0, index=False,
                                                  encoding="utf-8-sig" if i == 0 else "utf-8")
            filas += len(df)
        tmp.replace(ruta)
    finally:
        tmp.unlink(missing_ok=True)
    if progress:
        progress(1.0, "Listo")
    return filas
