"""Indicadores de la EMICRON por grupo, con las definiciones de los anexos del DANE."""

from __future__ import annotations

import warnings
from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _con_categorias

GLOSARIO = {
    "Micronegocio": "Unidad económica con hasta 9 personas ocupadas que desarrolla una actividad productiva de bienes o "
                    "servicios para obtener un ingreso, como propietario o arrendatario de los medios de producción. La "
                    "EMICRON entrevista a los dueños, patrones o trabajadores por cuenta propia encontrados en la GEIH.",
    "Personal ocupado": "El propietario más los trabajadores remunerados, los socios y los trabajadores o familiares sin "
                        "remuneración (preguntas P3032_1 a P3032_3).",
    "Ventas o ingresos": "Ventas de mercancías y productos, ingresos por servicios y otros ingresos del mes de referencia "
                         "(VENTAS_MES_ANTERIOR). En los indicadores, anuales: el mes por 12.",
    "Consumo intermedio": "Bienes y servicios consumidos en la producción (materias primas, mercancías para la venta, "
                          "arriendo, servicios públicos, transporte y otros gastos).",
    "Valor agregado": "Ventas o ingresos menos consumo intermedio.",
    "Ingreso mixto": "Valor agregado menos la remuneración del personal ocupado: lo que le queda al propietario, que es a la "
                     "vez trabajador y dueño del capital.",
    "Coeficiente técnico": "Consumo intermedio sobre ventas o ingresos, en %.",
    "Informalidad empresarial": "La EMICRON la aproxima con la tenencia de RUT, el registro en una Cámara de Comercio y el "
                                "aporte del propietario a salud y pensión.",
    "Factor de expansión": "fex: cuántos micronegocios representa cada registro en el año. Es anual: la suma de los 12 "
                           "meses es el total del año. fex_dpto es el de las cifras por departamento.",
}

# Montos mensuales en pesos de load -> nombre del indicador (anual, en miles de pesos, como el cuadro I.1)
_MONTOS = {"ventas_mes_anterior": "ventas", "consumo_intermedio": "consumo_intermedio",
           "valor_agregado": "valor_agregado", "remuneracion_total": "remuneracion", "sueldos": "sueldos",
           "prestaciones": "prestaciones", "ingreso_mixto": "ingreso_mixto"}
_CONTEOS = ["personal_ocupado", "trabajadores_remunerados", "socios", "familiares_sin_remuneracion"]


def a_miles_anuales(mensual_por_peso: pd.Series | float) -> pd.Series | float:
    """Un total mensual en pesos, expandido, como lo publica el DANE: anual y en miles de pesos."""
    return mensual_por_peso * 12 / 1000


def _lista(por) -> list[str]:
    if por is None:
        return []
    return [por] if isinstance(por, str) else list(por)


def indicadores(df: pd.DataFrame, por: str | Iterable[str] | None = "anio", peso: str = "fex",
                dropna: bool = True) -> pd.DataFrame:
    """
    Micronegocios, personal ocupado, ventas, valor agregado e informalidad, por grupo.

    Las cifras son las del cuadro I.1 de los anexos del DANE («Resumen de las principales variables»), más tres
    indicadores de informalidad.

    Parámetros
    ----------
    df
        Datos de :func:`load`.
    por
        Columna o lista de columnas para agrupar, por ejemplo ``["anio", "clase"]``. Por defecto, ``"anio"``: cada año
        es un total, y sumar años no tiene sentido. ``None`` da una sola fila.
    peso
        ``"fex"`` (por defecto) o ``"fex_dpto"``, el factor de las cifras por departamento.
    dropna
        Quitar los micronegocios sin dato en ``por``, como los de fuera de las 24 ciudades al agrupar por ``ciudad``.
        Con False, los grupos suman el total.

    Devuelve
    --------
    DataFrame
        Una fila por grupo con:

        * ``micronegocios``, ``personal_ocupado``, ``trabajadores_remunerados``, ``socios`` y
          ``familiares_sin_remuneracion``: expandidos.
        * ``ventas``, ``consumo_intermedio``, ``valor_agregado``, ``remuneracion``, ``sueldos``, ``prestaciones`` e
          ``ingreso_mixto``: en miles de pesos corrientes del año (el mes de referencia por 12), como el cuadro I.1.
          Vacíos si el grupo no tiene el dato (2019 solo trae ventas).
        * ``coeficiente_tecnico``: consumo intermedio sobre ventas, en %.
        * ``pct_rut``, ``pct_camara_comercio`` y ``pct_salud_pension`` (el propietario aporta a salud y a pensión): en %
          de los micronegocios con el dato.
        * ``n_muestra``: micronegocios encuestados, sin expandir.

    Lanza
    -----
    KeyError
        Si falta ``peso`` o alguna columna de ``por``.

    Véase también
    -------------
    GLOSARIO : Definiciones del DANE.
    dane_data.tabla : Distribución ponderada de cualquier variable.

    Notas
    -----
    Sin intervalos de confianza ni coeficientes de variación: los anexos los publican, pero los microdatos no traen el
    diseño muestral con el que se calculan.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> df = pd.DataFrame({"anio": 2024, "fex": [100.0, 50.0], "personal_ocupado": [1, 3],
    ...                    "trabajadores_remunerados": [0, 2], "socios": 0, "familiares_sin_remuneracion": 0,
    ...                    "ventas_mes_anterior": [1e6, 4e6], "consumo_intermedio": [5e5, 1e6],
    ...                    "rut": pd.array([False, True], dtype="boolean")})
    >>> r = dd.emicron.indicadores(df)
    >>> r[["anio", "micronegocios", "personal_ocupado", "ventas"]]
       anio  micronegocios  personal_ocupado     ventas
    0  2024          150.0             250.0  3600000.0
    >>> r[["coeficiente_tecnico", "pct_rut"]].round(1)
       coeficiente_tecnico  pct_rut
    0                 33.3     33.3
    """
    por = _lista(por)
    if faltan := [c for c in [peso, *por] if c not in df.columns]:
        raise KeyError(f"Faltan columnas en los datos: {', '.join(faltan)}.")
    if "anio" not in por and "anio" in df.columns and df["anio"].nunique() > 1:
        warnings.warn("Los datos tienen varios años y `por` no incluye 'anio': cada micronegocio se cuenta en cada año, "
                      "así que la suma no es un total.", UserWarning, stacklevel=2)
    w = pd.to_numeric(df[peso], errors="coerce").fillna(0.0)
    d = pd.DataFrame({"micronegocios": w, "n_muestra": 1.0}, index=df.index)
    for c in _CONTEOS:
        d[c] = pd.to_numeric(df[c], errors="coerce") * w if c in df.columns else np.nan
    for origen, nombre in _MONTOS.items():
        d[nombre] = pd.to_numeric(df[origen], errors="coerce") * w if origen in df.columns else np.nan
    pct = {"pct_rut": "rut", "pct_camara_comercio": "camara_comercio"}
    for nombre, origen in pct.items():
        si = df[origen].astype("boolean") if origen in df.columns else pd.Series(pd.NA, index=df.index, dtype="boolean")
        d[f"_{nombre}_si"], d[f"_{nombre}_con"] = w.where(si.fillna(False), 0.0), w.where(si.notna(), 0.0)
    sp = df["salud_pension"] if "salud_pension" in df.columns else pd.Series(pd.NA, index=df.index)
    d["_pct_salud_pension_si"] = w.where(sp.astype("string").eq("Salud y pensión").fillna(False), 0.0)
    d["_pct_salud_pension_con"] = w.where(sp.notna(), 0.0)

    if por:
        g = d.groupby([df[c] for c in por], observed=True, dropna=dropna, sort=True)
        res = g.sum(min_count=1).reset_index()  # min_count: un monto que nadie del grupo tiene queda vacío, no cero
    else:
        res = d.sum(min_count=1).to_frame().T
    for nombre in _MONTOS.values():
        res[nombre] = a_miles_anuales(res[nombre])
    res["coeficiente_tecnico"] = 100 * res["consumo_intermedio"] / res["ventas"].where(res["ventas"] > 0)
    for nombre in ("pct_rut", "pct_camara_comercio", "pct_salud_pension"):
        res[nombre] = 100 * res.pop(f"_{nombre}_si") / res.pop(f"_{nombre}_con").where(lambda s: s > 0)
    res["n_muestra"] = res["n_muestra"].astype("int64")
    if "anio" in df.columns and "valor_agregado" in df.columns:
        vacio = pd.to_numeric(df["valor_agregado"], errors="coerce").isna().groupby(df["anio"]).all()
        if sin := vacio[vacio].index.tolist():
            warnings.warn(f"EMICRON {', '.join(map(str, sin))}: sin consumo intermedio, valor agregado ni remuneraciones "
                          "en los microdatos; quedan vacíos.", UserWarning, stacklevel=2)
    columnas = [*por, "micronegocios", *_CONTEOS, *_MONTOS.values(), "coeficiente_tecnico", "pct_rut",
                "pct_camara_comercio", "pct_salud_pension", "n_muestra"]
    res = res[columnas]
    return _con_categorias(res, df, por) if por else res
