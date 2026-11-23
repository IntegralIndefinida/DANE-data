"""Indicadores de la ECV como los publica el DANE en la serie 2018–2025, por grupo."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _as_list as _lista, _con_categorias

GLOSARIO = {
    "ECV": "Encuesta Nacional de Calidad de Vida del DANE: anual desde 2010, por muestreo, con un capítulo del "
           "cuestionario por tema (vivienda, servicios, salud, educación, etc.).",
    "Jefe del hogar": "La persona que los demás miembros reconocen como jefe o jefa. Hay exactamente uno por hogar: los "
                      "indicadores de hogares se calculan sobre los jefes.",
    "Años de educación": "Años aprobados desde primero de primaria. La media cuenta hasta 13 (con la normal) y la "
                         "superior suma sus años a 11.",
    "Asistencia escolar": "Personas que actualmente estudian (asisten al preescolar, la escuela, el colegio o la "
                          "universidad), sobre todas las de ese rango de edad.",
    "Régimen contributivo": "En la serie del DANE incluye el régimen especial (fuerzas armadas, Ecopetrol, magisterio, "
                            "universidades públicas). Los porcentajes del régimen son sobre los afiliados.",
    "Percepción de pobreza": "Hogares cuyo jefe o cónyuge responde que se considera pobre (P5230).",
}

# Rangos de edad de la serie del DANE (Cuadros 17 y 18): (sufijo, mínimo, máximo)
_ASISTENCIA = (("6_21", 6, 21), ("6_10", 6, 10), ("11_14", 11, 14), ("15_16", 15, 16), ("17_21", 17, 21))
_EDUCACION = (("5_mas", 5, None), ("5_14", 5, 14), ("15_24", 15, 24), ("25_34", 25, 34), ("35_mas", 35, None))
_TENENCIAS = {"Propia, totalmente pagada": "propia_pagada", "Propia, la están pagando": "propia_pagando",
              "En arriendo o subarriendo": "arriendo", "Usufructo (con permiso, sin pago)": "usufructo",
              "Posesión sin título (ocupante de hecho)": "ocupante_de_hecho", "Propiedad colectiva": "propiedad_colectiva"}
_DE_HOGAR = ("energia", "acueducto", "alcantarillado", "recoleccion_basuras", "gas_natural", "internet_hogar",
             "se_considera_pobre")


def indicadores(df: pd.DataFrame, por: str | Iterable[str] | None = None, dropna: bool = True) -> pd.DataFrame:
    """
    Indicadores de la serie de la ECV del DANE, por grupo, expandidos con ``fex``.

    Parámetros
    ----------
    df
        Datos de :func:`load`, de personas o de hogares. Cada indicador sale si están las variables armonizadas que
        necesita; por ejemplo, la afiliación a salud pide ``load(..., modulos="salud")``.
    por
        Columna o lista de columnas para agrupar, por ejemplo ``"anio"`` o ``["anio", "area"]``. ``None`` da una sola
        fila.
    dropna
        Quitar las filas sin dato en ``por``. Con False, los grupos suman el total.

    Devuelve
    --------
    DataFrame
        Una fila por grupo, con lo que se pueda calcular:

        * ``hogares`` y, con personas, ``personas`` y ``personas_por_hogar`` (Cuadro 1 de la serie del DANE).
        * Hogares con cada servicio, en % de los hogares: ``pct_energia``, ``pct_gas_natural``, ``pct_acueducto``,
          ``pct_alcantarillado``, ``pct_recoleccion_basuras`` (Cuadro 4) y ``pct_internet_hogar`` (Cuadro 7).
        * Tenencia de la vivienda, en % de los hogares: ``pct_propia_pagada``, ``pct_propia_pagando``,
          ``pct_arriendo``, ``pct_usufructo``, ``pct_ocupante_de_hecho``, ``pct_propiedad_colectiva`` (Cuadro 8).
        * ``pct_se_considera_pobre``: hogares cuyo jefe o cónyuge se considera pobre (Cuadro 22).
        * ``pct_afiliados`` a salud, sobre las personas, y ``pct_contributivo`` (con el especial) y ``pct_subsidiado``,
          sobre los afiliados (Cuadro 12).
        * ``pct_asistencia_6_21`` y por rangos de edad (``_6_10``, ``_11_14``, ``_15_16``, ``_17_21``) (Cuadro 17).
        * ``anios_educacion_5_mas``: promedio de años de educación de 5 años y más, y por rangos (``_5_14``,
          ``_15_24``, ``_25_34``, ``_35_mas``) (Cuadro 18).
        * ``pct_usa_computador``, ``pct_usa_internet``, ``pct_usa_celular``: personas de 5 años y más (Cuadro 20).

    Lanza
    -----
    ValueError
        Si los datos no tienen ``fex`` (no salen de :func:`load`).

    Véase también
    -------------
    serie_indicadores : Lo mismo, año por año y sin tener todo en memoria.

    Notas
    -----
    En una tabla de personas, los indicadores de hogares se calculan sobre los jefes: hay exactamente uno por hogar.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> df = pd.DataFrame({"fex": [10.0, 10.0, 5.0], "edad": [40, 12, 30],
    ...                    "parentesco": ["Jefe(a) del hogar", "Hijo(a) o hijastro(a)", "Jefe(a) del hogar"],
    ...                    "internet_hogar": pd.array([True, True, False], dtype="boolean")})
    >>> dd.ecv.indicadores(df)[["hogares", "personas", "personas_por_hogar", "pct_internet_hogar"]].round(1)
       hogares  personas  personas_por_hogar  pct_internet_hogar
    0     15.0      25.0                 1.7                66.7
    """
    if "fex" not in df.columns:
        raise ValueError("Faltan las variables armonizadas (fex): use datos de dd.ecv.load(...).")
    llaves = _lista(por)
    # Sin grupos, un solo grupo con todo. Con dropna, se quitan aquí y no en cada suma: así todas ven las mismas filas.
    base = df.dropna(subset=llaves) if llaves and dropna else df
    grupos = [base[k] for k in llaves] if llaves else [pd.Series(0, index=base.index)]
    fex = base["fex"].astype("float64")

    def suma(mascara) -> pd.Series:
        return (fex * mascara).groupby(grupos, observed=True, dropna=False, sort=True).sum()

    def pct(numerador, denominador) -> pd.Series:
        return 100 * suma(numerador) / suma(denominador).where(lambda v: v > 0)

    def verdad(columna: str) -> pd.Series:
        return base[columna].fillna(False).astype(bool)

    personas = "parentesco" in base.columns
    hogar = base["parentesco"].eq("Jefe(a) del hogar").fillna(False).astype(bool) if personas else pd.Series(True, index=base.index)
    res = pd.DataFrame({"hogares": suma(hogar)})
    if personas:
        res["personas"] = suma(pd.Series(True, index=base.index))
        res["personas_por_hogar"] = res["personas"] / res["hogares"].where(lambda v: v > 0)
    # Del hogar: sobre todos los hogares, como el DANE (un hogar sin respuesta cuenta en el total)
    for columna in _DE_HOGAR:
        if columna in base.columns:
            res[f"pct_{columna}"] = pct(hogar & verdad(columna), hogar)
    if "tenencia_vivienda" in base.columns:
        for valor, nombre in _TENENCIAS.items():
            res[f"pct_{nombre}"] = pct(hogar & base["tenencia_vivienda"].eq(valor).fillna(False).astype(bool), hogar)
    if personas and "afiliado_salud" in base.columns:
        todos = pd.Series(True, index=base.index)
        afiliado = verdad("afiliado_salud")
        res["pct_afiliados"] = pct(afiliado, todos)
        if "regimen_salud" in base.columns:
            regimen = base["regimen_salud"]
            res["pct_contributivo"] = pct(afiliado & regimen.isin(["Contributivo", "Especial"]), afiliado)
            res["pct_subsidiado"] = pct(afiliado & regimen.eq("Subsidiado").fillna(False).astype(bool), afiliado)
    if personas and "edad" in base.columns:
        edad = base["edad"].astype("float64")

        def rango(minimo, maximo) -> pd.Series:
            return edad.ge(minimo) & (edad.le(maximo) if maximo is not None else True)

        if "asiste" in base.columns:
            for sufijo, minimo, maximo in _ASISTENCIA:
                res[f"pct_asistencia_{sufijo}"] = pct(rango(minimo, maximo) & verdad("asiste"), rango(minimo, maximo))
        if "anios_educacion" in base.columns:
            anios = base["anios_educacion"].astype("float64")
            for sufijo, minimo, maximo in _EDUCACION:
                con_dato = rango(minimo, maximo) & anios.notna()
                res[f"anios_educacion_{sufijo}"] = suma(anios.where(con_dato, 0)) / suma(con_dato).where(lambda v: v > 0)
        for columna in ("usa_computador", "usa_internet", "usa_celular"):
            if columna in base.columns:
                res[f"pct_{columna}"] = pct(rango(5, None) & verdad(columna), rango(5, None))

    res = res.replace([np.inf, -np.inf], np.nan)
    if llaves:
        res.index.names = llaves
        return _con_categorias(res.reset_index(), base, llaves)
    return res.reset_index(drop=True)
