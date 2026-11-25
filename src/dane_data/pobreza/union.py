"""Unión de la pobreza monetaria con las personas de la GEIH."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

from ..stats import _avisar
from .loader import LLAVES, load

_LLAVES = ["anio", "mes", *LLAVES]
VARIABLES_GEIH = ("ingreso_pc", "linea_pobreza", "linea_pobreza_extrema", "pobre", "pobre_extremo", "personas",
                  "personas_ug", "dominio", "grupo_dominio", "metodologia", "empalmado")


def _llaves_enteras(df: pd.DataFrame, que: str) -> pd.DataFrame:
    if faltan := [k for k in _LLAVES if k not in df.columns]:
        raise ValueError(
            f"{que} no trae {faltan}. Si cargó la GEIH con variables=[...], agregue "
            "'DIRECTORIO' y 'SECUENCIA_P' a la lista."
        )
    llaves = df[_LLAVES].apply(pd.to_numeric, errors="coerce")
    if llaves.isna().any().any():
        raise ValueError(f"{que} tiene llaves vacías o que no son números en {list(llaves.columns[llaves.isna().any()])}.")
    return llaves.astype("int64")


def unir_geih(
    geih: pd.DataFrame,
    hogares: pd.DataFrame | None = None,
    variables: Iterable[str] | None = None,
    empalme: bool = False,
    root=None,
    minimo: float = 0.95,
) -> pd.DataFrame:
    """
    Pega a cada persona de la GEIH las variables de pobreza monetaria de su hogar.

    La medición de pobreza sale de la GEIH: cada hogar del archivo de pobreza es un hogar de la GEIH del mismo año y mes, y
    el DANE asigna el ingreso per cápita de la unidad de gasto a todas sus personas. Así se puede ver, por ejemplo, la
    pobreza de los ocupados informales o de los jóvenes.

    Parámetros
    ----------
    geih
        Personas de :func:`dane_data.geih.load` (la serie principal, no la de empalme), con ``anio``, ``mes``,
        ``DIRECTORIO`` y ``SECUENCIA_P``.
    hogares
        Hogares de :func:`load`. Por defecto se cargan los años de ``geih``.
    variables
        Variables de ``hogares`` que se pegan. Por defecto ``VARIABLES_GEIH``: ingreso per cápita, líneas, pobre, pobre
        extremo, personas, dominio, metodología y empalme. Siempre se pega ``fex_pobreza``.
    empalme
        Si se cargan los hogares, cargarlos con el empalme de la pobreza al marco 2018 (vea :func:`load`). No es la serie
        de empalme de la GEIH (``dd.geih.load(empalme=True)``), que es otra cosa.
    root
        Carpeta de la pobreza, si se cargan los hogares.
    minimo
        Avisar si menos de esta fracción de las personas de la GEIH, en los departamentos que mide la pobreza, encuentra
        su hogar.

    Devuelve
    --------
    DataFrame
        ``geih`` con las variables pegadas y ``fex_pobreza`` (el factor anual del hogar en la medición de pobreza), en el
        mismo orden. Las personas sin hogar en la medición quedan vacías. ``attrs["union_pobreza"]`` tiene la cobertura:
        personas y hogares de la GEIH unidos, por año y mes, y los departamentos que la pobreza no mide.

    Lanza
    -----
    ValueError
        Si faltan las llaves, alguna variable ya existe en ``geih``, los hogares repiten llave o ninguna persona encuentra
        hogar.

    Avisos
    ------
    UserWarning
        Si la cobertura en los departamentos que mide la pobreza es menor que ``minimo``.

    Notas
    -----
    La pobreza monetaria se mide en 23 departamentos y Bogotá; las personas de los otros departamentos de la GEIH (San
    Andrés, Arauca, Casanare, Putumayo y los de la Amazonía y la Orinoquía) quedan sin dato, y no cuentan para el aviso.

    Para cifras de pobreza por características de las personas, el peso de cada persona es ``fex_pobreza``, no ``fex`` (el
    factor mensual de la GEIH): ya reparte la población del año entre los 12 meses, así que no hay que dividirlo, y no se
    multiplica por ``personas`` (eso es solo con un hogar por fila, en :func:`indicadores`).

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> per = dd.pobreza.unir_geih(dd.geih.load(2025))  # doctest: +SKIP
    >>> per.groupby("sexo").apply(lambda d: dd.weighted_mean(d.pobre, d.fex_pobreza))  # doctest: +SKIP
    """
    variables = list(VARIABLES_GEIH if variables is None else variables)
    if choque := sorted(set(variables + ["fex_pobreza"]) & set(geih.columns)):
        raise ValueError(f"La GEIH ya tiene {choque}: quítelas antes de unir o elija otras variables.")
    llaves_geih = _llaves_enteras(geih, "La GEIH")
    if hogares is None:
        hogares = load(sorted(llaves_geih["anio"].unique()), empalme=empalme, root=root)
    if faltan := [v for v in [*variables, "fex"] if v not in hogares.columns]:
        raise ValueError(f"Los hogares no traen {faltan}.")
    llaves_hog = _llaves_enteras(hogares, "Los hogares")
    pegar = pd.concat([llaves_hog, hogares[variables], hogares["fex"].rename("fex_pobreza")], axis=1)
    if pegar.duplicated(_LLAVES).any():
        raise ValueError("Los hogares repiten llave (anio, mes, DIRECTORIO, SECUENCIA_P).")

    unido = llaves_geih.merge(pegar, on=_LLAVES, how="left", validate="m:1")
    unido.index = geih.index
    encontrado = unido["fex_pobreza"].notna()
    # Departamentos que la pobreza no mide: no cuentan para la cobertura
    medidos = pd.Series(True, index=geih.index)
    fuera = []
    if "departamento" in geih.columns and "departamento" in hogares.columns:
        medidos = geih["departamento"].isin(set(hogares["departamento"].dropna()))
        fuera = sorted(set(geih.loc[~medidos, "departamento"].dropna().astype(str)))
    hog_geih = llaves_geih.drop_duplicates()
    cobertura = {
        "personas": float(encontrado[medidos].mean()) if medidos.any() else float("nan"),
        "hogares": float(unido.loc[encontrado, _LLAVES].drop_duplicates().shape[0] / max(len(hog_geih), 1)),
        "por_mes": encontrado[medidos].groupby([llaves_geih.loc[medidos, "anio"], llaves_geih.loc[medidos, "mes"]]).mean()
                   .to_dict(),
        "anios_sin_pobreza": sorted(set(llaves_geih["anio"]) - set(llaves_hog["anio"])),
        "departamentos_no_medidos": fuera,
        "denominador": "personas de la GEIH en los departamentos que mide la pobreza",
    }
    if not encontrado.any():
        raise ValueError("Ninguna persona de la GEIH encontró su hogar en la pobreza: revise que sean los mismos años y "
                         "meses, y que la GEIH sea la serie principal.")
    if cobertura["personas"] < minimo:
        sin = f"; años sin datos de pobreza: {cobertura['anios_sin_pobreza']}" if cobertura["anios_sin_pobreza"] else ""
        _avisar(
            f"Solo {cobertura['personas']:.1%} de las personas de la GEIH encontró su hogar en la pobreza{sin}. Revise "
            "los años y meses, que la GEIH sea la serie principal y que no se haya filtrado una parte de los hogares. "
            "El detalle por mes está en attrs['union_pobreza'].", UserWarning,
        )
    out = pd.concat([geih, unido[[*variables, "fex_pobreza"]]], axis=1)
    out.attrs = {**geih.attrs, "union_pobreza": cobertura}  # merge y concat pierden los attrs de la GEIH
    return out
