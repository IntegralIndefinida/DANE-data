"""Conteos y porcentajes de las Estadísticas Vitales, por grupo."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _con_categorias

GLOSARIO = {
    "Estadísticas Vitales": "Registro de los certificados de nacimiento y de defunción, no una encuesta: no tiene "
                            "factor de expansión y cada fila es un hecho registrado.",
    "Defunción no fetal": "Muerte de una persona nacida viva, a cualquier edad.",
    "Defunción fetal": "Muerte antes de la expulsión completa del producto de la concepción, cualquiera que sea la "
                       "duración del embarazo.",
    "Causa básica": "Enfermedad o lesión que inició la cadena de hechos que llevó a la muerte (C_BAS1). Se codifica con "
                    "la CIE: CIE-9 hasta 1996 y CIE-10 desde 1997.",
    "Lista 105": "Agrupación colombiana de la causa básica en 105 causas (causa_105). Es la única disponible en toda la "
                 "serie, 1979–2025.",
    "Lista 6/67": "Agrupación de la OPS en 67 causas (causa_667), con seis grandes grupos más las mal definidas.",
    "Bajo peso al nacer": "Menos de 2.500 gramos. El porcentaje se calcula sobre los nacidos con peso conocido.",
    "Prematuro": "Menos de 37 semanas de gestación. Solo se puede saber con T_GES_AGRU_CIE, que no está en 2012, 2013, "
                 "2020 ni antes de 2008: T_GES agrupa «de 28 a 37» semanas.",
    "Madre adolescente": "Madre de menos de 20 años al momento del parto.",
    "Atención institucional del parto": "Nacidos vivos en una institución de salud, sobre el total de nacidos vivos (ficha "
                                        "metodológica del DANE).",
    "Cuatro o más controles prenatales": "Nacidos vivos cuya madre tuvo cuatro o más consultas prenatales, sobre el total "
                                         "de nacidos vivos, también los que no tienen el dato (ficha metodológica del DANE).",
    "Causas mal definidas": "Defunciones con causa básica del grupo de signos, síntomas y afecciones mal definidas de la "
                            "lista 6/67, sobre el total de defunciones: el indicador de calidad del registro de la ficha "
                            "metodológica del DANE.",
    "Razón de sexo al nacer": "Nacidos hombres por cada 100 nacidas mujeres.",
    "Tasa bruta de natalidad": "Nacimientos por cada 1.000 habitantes.",
    "Tasa bruta de mortalidad": "Defunciones por cada 1.000 habitantes.",
    "Tasa global de fecundidad": "Hijos que tendría una mujer si viviera sus años fértiles (15 a 49) con las tasas por edad "
                                 "del año: 5 por la suma de los nacimientos por mujer de cada grupo quinquenal.",
    "Tasa específica": "Hechos de un grupo de edad por cada 1.000 personas de ese grupo.",
    "Mortalidad infantil registrada": "Defunciones de menores de un año por cada 1.000 nacidos vivos del mismo año, tal "
                                      "como se registraron, sin ajustar por subregistro.",
    "Muerte materna": "Muerte de una mujer durante el embarazo o hasta 42 días después, por una causa relacionada con el "
                      "embarazo o su atención. En los datos, causa básica del capítulo O de la CIE-10 salvo O96 y O97, como "
                      "en la ficha técnica del DANE.",
    "Muerte materna tardía": "Por causas obstétricas, de 43 días a un año después del embarazo (O96). No entra en la razón de "
                             "mortalidad materna, aunque los cuadros de defunciones maternas del DANE sí la cuentan.",
    "Razón de mortalidad materna": "Muertes maternas (hasta 42 días) por cada 100.000 nacidos vivos.",
    "Mortinato": "Defunción fetal de 22 semanas o más de gestación o de 500 gramos o más (ficha técnica del DANE). Los "
                 "microdatos agrupan el peso desde «menos de 1.000 gramos», así que dane-data solo puede confirmar el peso "
                 "desde 1.000. Las de menos de 22 semanas y 500 gramos son abortos.",
    "Mortalidad neonatal": "Defunciones de 0 a 27 días completos de vida por cada 1.000 nacidos vivos. La precoz, de 0 a 6 días.",
    "Mortalidad perinatal": "Mortinatos y defunciones de 0 a 6 días por cada 1.000 nacidos vivos más mortinatos.",
}


def _lista(por) -> list[str]:
    if por is None:
        return []
    return [por] if isinstance(por, str) else list(por)


def _tipo_de(df: pd.DataFrame) -> str:
    """El tipo de certificado de unos datos armonizados, por sus columnas."""
    if "cesarea" in df.columns:
        return "nacimientos"
    if "grupo_edad" in df.columns:
        return "defunciones"
    if "causa_cie" in df.columns:
        return "fetales"
    raise ValueError("Los datos no están armonizados: use dd.eevv.load(...) con harmonize_vars=True.")


def _sumar(grupos, mascara: pd.Series) -> pd.Series:
    return mascara.astype("float64").groupby(grupos, observed=True, dropna=False, sort=True).sum()


def indicadores(df: pd.DataFrame, por: str | Iterable[str] | None = None, dropna: bool = True) -> pd.DataFrame:
    """
    Conteos y porcentajes de un tipo de certificado, por grupo.

    El tipo se reconoce por las columnas de ``df``.

    Parámetros
    ----------
    df
        Datos de :func:`load`.
    por
        Columna o lista de columnas para agrupar, por ejemplo ``"anio"`` o ``["anio", "departamento_residencia"]``.
        ``None`` da una sola fila.
    dropna
        Quitar las filas de los registros sin dato en ``por``, como los residentes en el extranjero al agrupar por
        departamento de residencia. Con False, los grupos suman el total.

    Devuelve
    --------
    DataFrame
        Una fila por grupo. En todos: ``hombres`` y ``mujeres``, salvo en fetales, donde casi siempre es
        indeterminado.

        * Defunciones: ``defunciones``, ``menores_un_anio``, ``neonatales`` (0 a 27 días), ``neonatales_precoces``
          (0 a 6 días), ``pct_menores_un_anio``, ``maternas`` (hasta 42 días), ``maternas_tardias``, ``homicidios``,
          ``suicidios``, ``accidentes``, ``pct_mal_definidas``.
        * Nacimientos: ``nacimientos``, ``razon_sexo``, ``pct_bajo_peso``, ``pct_prematuro``, ``pct_cesarea``,
          ``pct_parto_multiple``, ``pct_madre_adolescente``, ``pct_parto_institucional``, ``pct_cuatro_consultas``,
          ``consultas_promedio``.
        * Fetales: ``fetales``, ``mortinatos`` (22 semanas o 1.000 gramos o más), ``pct_bajo_peso``, ``pct_prematuro``,
          ``pct_madre_adolescente``.

        Los porcentajes se calculan sobre quienes tienen el dato, salvo los tres de la ficha metodológica del DANE, que
        van sobre el total como en ella: ``pct_parto_institucional`` y ``pct_cuatro_consultas`` sobre todos los nacidos
        vivos, y ``pct_mal_definidas`` sobre todas las defunciones. ``pct_bajo_peso`` también es de la ficha, y ella
        misma lo calcula sobre los nacidos con peso. Un valor queda vacío si el dato no existe en esos años; por
        ejemplo, ``pct_prematuro`` en 2012.

    Lanza
    -----
    ValueError
        Si los datos no están armonizados.

    Véase también
    -------------
    serie_indicadores : Lo mismo, año por año y sin tener todo en memoria.
    tasas : Tasas sobre la población.

    Notas
    -----
    ``menores_un_anio`` queda vacía en los grupos con registros de enero–junio de 1991, en que no se pueden separar las
    edades de los menores de 10 años.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> df = pd.DataFrame({"anio": [2025, 2025, 2025], "sexo": ["Hombre", "Mujer", "Mujer"],
    ...                    "cesarea": pd.array([True, False, None], dtype="boolean"),
    ...                    "bajo_peso": pd.array([False, False, True], dtype="boolean")})
    >>> dd.eevv.indicadores(df)[["nacimientos", "mujeres", "pct_cesarea", "pct_bajo_peso"]].round(1)
       nacimientos  mujeres  pct_cesarea  pct_bajo_peso
    0            3        2         50.0           33.3
    """
    tipo = _tipo_de(df)
    llaves = _lista(por)
    # Sin grupos, un solo grupo con todo. Con dropna, se quitan aquí y no en cada suma: así todas ven las mismas filas.
    if llaves:
        base = df.dropna(subset=llaves) if dropna else df
        grupos = [base[k] for k in llaves]
    else:
        base = df
        grupos = [pd.Series(0, index=df.index)]

    def contar(mascara: pd.Series) -> pd.Series:
        return _sumar(grupos, mascara)

    def tiene(columna: str) -> bool:
        return columna in base.columns

    def valido(columna: str) -> pd.Series:
        return contar(base[columna].notna())

    def verdaderos(columna: str) -> pd.Series:
        """Cuántos True; vacío en los grupos donde la columna no tiene ningún dato."""
        return contar(base[columna].fillna(False).astype(bool)).where(valido(columna) > 0)

    def pct(columna: str) -> pd.Series:
        return 100 * verdaderos(columna) / valido(columna).where(lambda v: v > 0)

    total = contar(pd.Series(True, index=base.index))
    res = pd.DataFrame({tipo: total.astype("int64")})
    if tipo != "fetales" and tiene("sexo"):
        res["hombres"] = contar(base["sexo"].eq("Hombre").fillna(False).astype(bool)).astype("int64")
        res["mujeres"] = contar(base["sexo"].eq("Mujer").fillna(False).astype(bool)).astype("int64")

    if tipo == "defunciones":
        # Un grupo con edades de menores de 10 sin detalle (1991) contaría de menos los menores de un año y los neonatales
        sin_detalle = (contar(base["grupo_edad"].eq("Menor de 10 años, sin detalle").fillna(False).astype(bool))
                       if tiene("grupo_edad") else None)
        for columna, nombre in (("menor_un_anio", "menores_un_anio"), ("neonatal", "neonatales"),
                                ("neonatal_precoz", "neonatales_precoces")):
            if tiene(columna):
                res[nombre] = verdaderos(columna) if sin_detalle is None else verdaderos(columna).where(sin_detalle == 0)
        if "menores_un_anio" in res.columns:
            res["pct_menores_un_anio"] = 100 * res["menores_un_anio"] / total
        for columna, nombre in (("materna", "maternas"), ("materna_tardia", "maternas_tardias")):
            if tiene(columna):
                res[nombre] = verdaderos(columna)
        if tiene("manera_muerte"):
            con_manera = valido("manera_muerte").where(lambda v: v > 0)
            for nombre, valor in (("homicidios", "Homicidio"), ("suicidios", "Suicidio"), ("accidentes", "Accidente")):
                res[nombre] = contar(base["manera_muerte"].eq(valor).fillna(False).astype(bool)).where(con_manera.notna())
        if tiene("gran_causa"):
            # Indicador de calidad de la ficha metodológica del DANE: mal definidas sobre el total de defunciones
            mal = contar(base["gran_causa"].eq("Signos y síntomas mal definidos").fillna(False).astype(bool))
            res["pct_mal_definidas"] = (100 * mal / total).where(valido("gran_causa") > 0)
    elif tipo == "nacimientos":
        if "hombres" in res.columns:
            res["razon_sexo"] = 100 * res["hombres"] / res["mujeres"].where(lambda v: v > 0)
    if tipo == "fetales" and tiene("mortinato"):
        res["mortinatos"] = verdaderos("mortinato")
    if tipo in ("nacimientos", "fetales"):
        for columna, nombre in (("bajo_peso", "pct_bajo_peso"), ("prematuro", "pct_prematuro")):
            if tiene(columna):
                res[nombre] = pct(columna)
    if tipo == "nacimientos":
        for columna, nombre in (("cesarea", "pct_cesarea"), ("parto_multiple", "pct_parto_multiple")):
            if tiene(columna):
                res[nombre] = pct(columna)
    if tipo in ("nacimientos", "fetales") and tiene("madre_adolescente"):
        res["pct_madre_adolescente"] = pct("madre_adolescente")
    # Ficha metodológica del DANE: atención institucional del parto (AIP) y cuatro o más controles prenatales (CP), sobre
    # el total de nacidos vivos. Desde 2022 entran registros de la Registraduría sin estos datos (TIPOFORMULARIO).
    if tipo == "nacimientos" and tiene("sitio_parto"):
        institucional = contar(base["sitio_parto"].eq("Institución de salud").fillna(False).astype(bool))
        res["pct_parto_institucional"] = (100 * institucional / total).where(valido("sitio_parto") > 0)
    if tipo == "nacimientos" and tiene("consultas"):
        con_consultas = valido("consultas").where(lambda v: v > 0)
        cuatro = contar(base["consultas"].ge(4).fillna(False).astype(bool))
        res["pct_cuatro_consultas"] = (100 * cuatro / total).where(con_consultas.notna())
        res["consultas_promedio"] = contar(base["consultas"].fillna(0).astype("float64")) / con_consultas

    res = res.replace([np.inf, -np.inf], np.nan)
    if llaves:
        res.index.names = llaves
        return _con_categorias(res.reset_index(), base, llaves)
    return res.reset_index(drop=True)
