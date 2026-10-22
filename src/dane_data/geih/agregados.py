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
import numbers
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from .. import config
from ..referencias import MESES
from ..stats import _as_list, _meses_anotados, peso_mensual_promedio, weighted_quantile
from .indicadores import _COLUMNAS, indicadores
from .loader import (_HARMONIZE_VERSION, CATEGORIAS, MesGEIH, _firma_archivos, _guardar_parquet, _root, _usado,
                     find_months, load)

log = logging.getLogger("dane_data.geih")

# Lo que lee `indicadores` más las desagregaciones y filtros de la app.
VARIABLES_INDICADORES = ["anio", "mes", "fex", "pet", "fuerza_trabajo", "ocupado", "desocupado", "inactivo",
                         "formal", "ingreso_laboral", "sexo", "zona", "edad", "grupo_edad", "nivel_educativo",
                         "departamento"]
POR_PRECALCULADOS = (None, "sexo", "zona", "grupo_edad", "nivel_educativo", "departamento")
POBLACIONES = ("pet", "fuerza_trabajo", "ocupado", "desocupado", "inactivo")


def filtrar(df: pd.DataFrame, filtros: dict | None = None, poblacion: str | None = None) -> pd.DataFrame:
    """
    Filas que cumplen los filtros y pertenecen a una población.

    Es el formato de filtros que aceptan ``serie_indicadores``, ``serie_tabla``, ``serie_frecuencias`` y
    ``exportar``.

    Parámetros
    ----------
    df
        Microdatos armonizados.
    filtros
        ``{columna: [valores]}`` para conservar esos valores, o ``{columna: (mínimo, máximo)}`` para un
        rango con los extremos incluidos. Por ejemplo, ``{"sexo": ["Mujer"], "edad": (15, 28)}``. Si la
        columna no existe (una variable que ese año no trae), ninguna fila cumple el filtro.
    poblacion
        Una de ``POBLACIONES``: ``"pet"``, ``"fuerza_trabajo"``, ``"ocupado"``, ``"desocupado"`` o
        ``"inactivo"``.

    Devuelve
    --------
    DataFrame
        Las filas que cumplen todo, o ``df`` mismo si todas cumplen.

    Notas
    -----
    El resultado anota en ``attrs["meses_por_anio"]`` cuántos meses tenía cada año antes de filtrar (si se
    filtra por ``mes``, solo esos). Así, si el filtro deja un mes sin nadie, ``dd.tabla`` e ``indicadores``
    lo cuentan como 0 en el promedio mensual de los niveles, como el DANE, y dan lo mismo que las
    funciones ``serie_*``. Si después se toma un subconjunto (``df[df.mes <= 3]``), la anotación deja de
    valer y se cuentan los meses que quedan.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> df = pd.DataFrame({"sexo": ["Mujer", "Hombre", "Mujer"], "edad": [17, 30, 45], "ocupado": [1, 1, 0]})
    >>> dd.geih.filtrar(df, {"sexo": ["Mujer"], "edad": (15, 28)})
        sexo  edad  ocupado
    0  Mujer    17        1
    >>> dd.geih.filtrar(df, poblacion="ocupado")
         sexo  edad  ocupado
    0   Mujer    17        1
    1  Hombre    30        1
    """
    mask = _mascara(df, filtros, poblacion)
    if mask.all():
        return df
    res = df[mask]
    if {"anio", "mes"} <= set(df.columns):
        # Los meses de antes de filtrar (o los de un filtrar anterior), para peso_mensual_promedio
        previos = None if filtros and "mes" in filtros else _meses_anotados(df)
        res.attrs = {**res.attrs, "meses_por_anio": previos or _meses_cargados(df, filtros),
                     "meses_por_anio_filas": len(res)}
    return res


def _mascara(df: pd.DataFrame, filtros: dict | None, poblacion: str | None = None) -> pd.Series:
    mask = pd.Series(True, index=df.index)
    for col, cond in (filtros or {}).items():
        if col not in df.columns:
            mask &= False
        elif isinstance(cond, tuple):
            mask &= df[col].between(*cond)
        else:
            # Un solo valor ("Mujer", 11) cuenta como lista: list("Mujer") lo partiría en letras
            mask &= df[col].isin([cond] if isinstance(cond, str) or not hasattr(cond, "__iter__") else list(cond))
    if poblacion:
        mask &= df[poblacion].eq(1).fillna(False).astype(bool)
    return mask


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
    return sorted({int(m) for m in ([meses] if isinstance(meses, (numbers.Integral, str)) else meses)})


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


def _meses_cargados(df: pd.DataFrame, filtros: dict | None) -> dict[int, int]:
    """
    ``{año: meses}`` sobre los que se promedian los niveles: los cargados, aunque un filtro deje
    alguno sin filas (ese mes cuenta como 0, como en el promedio de los totales mensuales del DANE).
    Si se filtra por ``mes``, solo esos meses.
    """
    d = df[["anio", "mes"]]
    if filtros and "mes" in filtros:
        d = d[_mascara(d, {"mes": filtros["mes"]})]
    return {int(a): int(n) for a, n in d.groupby("anio", observed=True)["mes"].nunique().items()}


def _clave_json(obj):
    """La solicitud lista para ``json.dumps``, que convierte las tuplas en listas: en ``filtros`` una
    tupla es un rango (``between``) y una lista son valores (``isin``), así que se marcan distinto."""
    if isinstance(obj, dict):
        return {str(k): _clave_json(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return {"__rango__": [_clave_json(v) for v in obj]}
    if isinstance(obj, list):
        return [_clave_json(v) for v in obj]
    return obj


def _por_anio(tipo: str, anios, solicitud: dict, calcular: Callable[[int], pd.DataFrame], *, meses=None,
              empalme: bool = False, root=None, progress=None) -> list[pd.DataFrame]:
    """``calcular(anio)`` para cada año, leído de la caché si ya se hizo con los mismos archivos y solicitud."""
    por_anio = _meses_por_anio(anios, meses, empalme, root)
    texto = json.dumps(_clave_json(solicitud), sort_keys=True, default=str, ensure_ascii=False)
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
                _usado(ruta)
            except Exception:  # caché corrupta: se regenera
                tabla = None
        if tabla is None:
            if progress:
                progress(i / len(por_anio), f"Calculando {anio} (solo la primera vez)")
            tabla = calcular(anio)
            try:
                _guardar_parquet(tabla, ruta)
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
    dropna: bool = True,
) -> pd.DataFrame:
    """
    Indicadores del mercado laboral de muchos años, sin cargar los microdatos en memoria.

    Da exactamente lo mismo que
    ``indicadores(filtrar(load(anios, months=meses), filtros), por=por, anual=anual, dropna=dropna)``,
    pero carga un año a la vez y guarda el resultado de cada año en disco.

    Parámetros
    ----------
    anios
        Año o lista de años, por ejemplo ``range(2007, 2027)``.
    por
        Desagregación: una de ``POR_PRECALCULADOS`` (``None``, ``"sexo"``, ``"zona"``,
        ``"grupo_edad"``, ``"nivel_educativo"``, ``"departamento"``).
    anual
        Si True, un resultado por año (promedio de los meses); si False, uno por mes.
    empalme
        Usar la serie de empalme (2010–2020).
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.
    filtros
        Filtros con el formato de ``filtrar``, por ejemplo ``{"edad": (15, 28)}``.
    meses
        Mes o lista de meses de cada año. Por defecto, todos los que haya.
    dropna
        Dejar fuera la fila de las personas con ``por`` vacío (por ejemplo, el ``nivel_educativo`` de
        los menores que no responden educación, casi todos fuera de la PET). Con False se conserva, como en
        ``indicadores``, y los grupos suman el total.

    Devuelve
    --------
    DataFrame
        Las mismas columnas de ``indicadores``: ``anio`` (y ``mes`` si ``anual=False``), la variable de
        ``por``, niveles, tasas, ingresos y ``n_muestra``.

    Lanza
    -----
    ValueError
        Si ``por`` no es una de ``POR_PRECALCULADOS``.
    FileNotFoundError
        Si no hay datos para esos años.

    Véase también
    -------------
    indicadores : El cálculo, sobre microdatos ya cargados.
    serie_tabla : Tablas ponderadas de muchos años.

    Notas
    -----
    Cada año se calcula una vez, con todas las desagregaciones de ``POR_PRECALCULADOS``, anual y
    mensual, y se guarda en ``~/.cache/dane_data/geih/indicadores/``. La primera vez tarda unos segundos
    por año; después es instantáneo, también al cambiar ``por`` o ``anual``. Se recalcula solo si cambian
    los archivos del año, los filtros o meses, o el código de ``dane-data``.

    Para desagregar por otras variables use ``indicadores`` sobre
    ``load(..., variables=[*VARIABLES_INDICADORES, "mi_variable"])``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.geih.serie_indicadores(2024)[["anio", "tgp", "to", "td", "tasa_informalidad"]].round(1)  # doctest: +SKIP
       anio   tgp    to    td  tasa_informalidad
    0  2024  63.9  57.4  10.2               57.1

    Desempleo juvenil (15 a 28 años):

    >>> dd.geih.serie_indicadores([2023, 2024, 2025], filtros={"edad": (15, 28)})[["anio", "td"]].round(1)  # doctest: +SKIP
       anio    td
    0  2023  17.2
    1  2024  17.4
    2  2025  15.3

    Mes a mes y por sexo:

    >>> dd.geih.serie_indicadores(range(2021, 2026), por="sexo", anual=False)  # doctest: +SKIP
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
        if dropna:  # la caché guarda también el grupo vacío: se quita aquí
            res = res[res[por].notna()].reset_index(drop=True)
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
    Distribución ponderada de una variable en muchos años, calculada año por año.

    Cuenta, para cada año y cada combinación de ``por``, cuántas personas (expandidas) tienen cada valor
    de ``variable``. Es la base de ``serie_tabla``: de estas frecuencias salen totales, porcentajes,
    medias y medianas exactas, también al juntar varios años.

    Parámetros
    ----------
    anios
        Año o lista de años.
    variable
        Variable cuya distribución se cuenta. Las filas donde está vacía se descartan. ``None`` cuenta
        solo los grupos de ``por``.
    por
        Variable o lista de variables de agrupación (``anio`` siempre se incluye).
    poblacion
        Restringir a una de ``POBLACIONES`` (por ejemplo ``"ocupado"``).
    filtros
        Filtros con el formato de ``filtrar``.
    meses
        Mes o lista de meses de cada año.
    columns
        Variables del DANE que no están en ``CORE_RAW`` y hay que leer, como en ``load``.
    empalme
        Usar la serie de empalme.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Una fila por año, grupo y valor, con ``peso`` (personas, promedio mensual del año) y
        ``n_muestra``.

    Véase también
    -------------
    tabla_de_frecuencias : Convertir las frecuencias en una tabla.
    serie_tabla : Las dos cosas en un paso.

    Ejemplos
    --------
    Mediana del ingreso laboral de los ocupados de 2024 y 2025 juntos:

    >>> import dane_data as dd
    >>> f = dd.geih.serie_frecuencias([2024, 2025], "ingreso_laboral", poblacion="ocupado")  # doctest: +SKIP
    >>> dd.weighted_quantile(f["ingreso_laboral"], f["peso"], 0.5)  # doctest: +SKIP
    1300000.0
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
    Tabla ponderada de muchos años, sin cargar los microdatos en memoria.

    Da exactamente lo mismo que
    ``dd.tabla(filtrar(load(anios, months=meses), filtros, poblacion), por, variable, estadistico)``,
    pero calcula las frecuencias de un año a la vez y las guarda en disco.

    Parámetros
    ----------
    anios
        Año o lista de años.
    por
        Variable o lista de variables que definen los grupos. Incluya ``"anio"`` para una fila por año;
        sin él, los años se juntan.
    variable
        Variable numérica para ``"media"`` y ``"mediana"``.
    estadistico
        ``"total"``, ``"porcentaje"``, ``"media"`` o ``"mediana"``, como en ``dd.tabla``.
    poblacion
        Restringir a una de ``POBLACIONES`` (por ejemplo ``"ocupado"``).
    filtros
        Filtros con el formato de ``filtrar``.
    meses
        Mes o lista de meses de cada año.
    dropna
        Dejar fuera a las personas con valor vacío en alguna variable de ``por`` (por ejemplo, la rama de
        actividad de quien no trabaja).
    columns
        Variables del DANE que no están en ``CORE_RAW`` y hay que leer, como en ``load``.
    empalme
        Usar la serie de empalme.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Igual que ``dd.tabla``: los grupos, el estadístico y ``n_muestra``.

    Lanza
    -----
    ValueError
        Si ``estadistico`` no es uno de los cuatro, o falta ``variable`` para la media o la mediana.

    Véase también
    -------------
    dane_data.tabla : La misma tabla sobre microdatos cargados.
    serie_frecuencias : Las frecuencias de las que sale la tabla.

    Notas
    -----
    Los totales de cada año son promedios mensuales; si ``por`` no incluye ``anio``, el total junta los
    años (es la suma de los promedios de cada año). Las medias y medianas que juntan años son exactas,
    porque salen de la distribución completa y no de promedios de cada año.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.geih.serie_tabla([2024, 2025], por="sexo", variable="ingreso_laboral",
    ...                     estadistico="mediana", poblacion="ocupado")  # doctest: +SKIP
         sexo    mediana  n_muestra
    0  Hombre  1300000.0     385000
    1   Mujer  1300000.0     303382

    Distribución de los ocupados por nivel educativo, año por año:

    >>> dd.geih.serie_tabla(range(2015, 2026), por=["anio", "nivel_educativo"], estadistico="porcentaje",
    ...                     poblacion="ocupado", dropna=True)  # doctest: +SKIP
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
    """
    Tabla ponderada a partir de frecuencias.

    Es el segundo paso de ``serie_tabla``: convierte la salida de ``serie_frecuencias`` (o cualquier
    tabla con ``peso`` y ``n_muestra``) en la tabla que daría ``dd.tabla``.

    Parámetros
    ----------
    f
        Frecuencias con las columnas de ``por``, ``variable``, ``peso`` y ``n_muestra``.
    por
        Variable o lista de variables que definen los grupos.
    variable
        Variable numérica para ``"media"`` y ``"mediana"``.
    estadistico
        ``"total"``, ``"porcentaje"``, ``"media"`` o ``"mediana"``.

    Devuelve
    --------
    DataFrame
        Los grupos, el estadístico y ``n_muestra``.

    Véase también
    -------------
    serie_frecuencias : De dónde salen las frecuencias.
    serie_tabla : Los dos pasos juntos.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> f = pd.DataFrame({"anio": [2023, 2023, 2024, 2024], "sexo": ["Hombre", "Mujer", "Hombre", "Mujer"],
    ...                   "peso": [60.0, 40.0, 70.0, 30.0], "n_muestra": [6, 4, 7, 3]})
    >>> dd.geih.tabla_de_frecuencias(f, por=["anio", "sexo"], estadistico="porcentaje")
       anio    sexo  total  n_muestra  porcentaje
    0  2023  Hombre   60.0          6        60.0
    1  2023   Mujer   40.0          4        40.0
    2  2024  Hombre   70.0          7        70.0
    3  2024   Mujer   30.0          3        30.0

    Una mediana que junta años sale de la distribución completa:

    >>> f = pd.DataFrame({"anio": [2023, 2023, 2024], "ingreso": [1.0, 2.0, 3.0],
    ...                   "peso": [10.0, 30.0, 20.0], "n_muestra": [1, 3, 2]})
    >>> dd.geih.tabla_de_frecuencias(f, variable="ingreso", estadistico="mediana")
       mediana  n_muestra
    0      2.0          6
    """
    por = _as_list(por)
    if estadistico in ("total", "porcentaje"):
        if not por:
            res = pd.DataFrame({"total": [f["peso"].sum()], "n_muestra": [int(f["n_muestra"].sum())]})
        else:
            res = f.groupby(por, observed=True, dropna=False).agg(
                total=("peso", "sum"), n_muestra=("n_muestra", "sum")).reset_index()
        if estadistico == "porcentaje":
            outer = por[:-1]
            # dropna=False como en la agregación: un grupo exterior vacío (NaN) también suma 100 %
            denom = (res.groupby(outer, observed=True, dropna=False)["total"].transform("sum") if outer
                     else res["total"].sum())
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
    sep: str = ",",
    decimal: str = ".",
) -> int:
    """
    Exporta los microdatos armonizados a un CSV, un mes a la vez.

    Escribe una persona por fila y mes. Como lee y escribe un mes a la vez, sirve para muchos años
    aunque no quepan en memoria. El archivo se escribe primero con otro nombre y se renombra al
    terminar, así que nunca queda un CSV a medias.

    Parámetros
    ----------
    anios
        Año o lista de años.
    ruta
        Archivo CSV de destino (UTF-8 con BOM, para que Excel lea bien las tildes).
    variables
        Columnas a escribir (``anio`` y ``mes`` siempre). Por defecto, todas las armonizadas.
    poblacion
        Restringir a una de ``POBLACIONES`` (por ejemplo ``"ocupado"``).
    filtros
        Filtros con el formato de ``filtrar``.
    meses
        Mes o lista de meses de cada año.
    columns
        Variables del DANE que no están en ``CORE_RAW``: hay que pedirlas aquí además de en
        ``variables``.
    empalme
        Usar la serie de empalme.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.
    sep
        Separador de columnas. Un Excel con la configuración regional de Colombia (coma decimal) abre todo
        en una sola columna un CSV separado por comas: para abrirlo con doble clic use ``sep=";"`` y
        ``decimal=","``.
    decimal
        Separador decimal.

    Devuelve
    --------
    int
        Número de filas escritas.

    Véase también
    -------------
    load : Cargar los mismos datos en memoria.
    filtrar : El formato de ``filtros``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.geih.exportar(range(2015, 2026), "ocupados.csv", poblacion="ocupado")  # doctest: +SKIP
    >>> dd.geih.exportar(2024, "salarios.csv", variables=["fex", "sexo", "ingreso_laboral", "P6500"],
    ...                  columns=["P6500"], poblacion="ocupado")  # doctest: +SKIP
    >>> dd.geih.exportar(2024, "para_excel.csv", sep=";", decimal=",")  # doctest: +SKIP
    """
    ruta = Path(ruta)
    por_anio = _meses_por_anio(anios, meses, empalme, root)
    lista = [m for _, ms in sorted(por_anio.items()) for m in ms]
    necesarias = leer = None  # sin variables: se leen y escriben todas las armonizadas
    if variables is not None:
        necesarias = list(dict.fromkeys(["anio", "mes", *_as_list(variables)]))
        leer = list(dict.fromkeys([*necesarias, *(filtros or {}), *([poblacion] if poblacion else [])]))
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f"{ruta.name}.{uuid.uuid4().hex}.tmp")
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
                                                  encoding="utf-8-sig" if i == 0 else "utf-8", sep=sep,
                                                  decimal=decimal)
            filas += len(df)
        tmp.replace(ruta)
    finally:
        tmp.unlink(missing_ok=True)
    if progress:
        progress(1.0, "Listo")
    return filas
