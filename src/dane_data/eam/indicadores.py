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
    "Código de reserva": "Código CIIU residual («otras industrias manufactureras»: 3909, 3699 o 3290) con el que el "
                         "ANDA publica muchos establecimientos grandes para ocultar su actividad. Infla esa división y "
                         "subestima las demás; los totales no cambian.",
}


def resumen(df: pd.DataFrame, por: str | Iterable[str] | None = ("anio",)) -> pd.DataFrame:
    """
    Agregados industriales por grupo.

    Suma las variables de los establecimientos de cada grupo y calcula los indicadores derivados.

    Parámetros
    ----------
    df
        Microdatos de ``load``.
    por
        Variable o lista de variables de agrupación, por ejemplo ``["anio", "sector"]``. ``None`` para
        un solo total.

    Devuelve
    --------
    DataFrame
        Una fila por grupo con las sumas que existan en los datos (``produccion_bruta``,
        ``consumo_intermedio``, ``valor_agregado``, ``ventas``, ``personal_total``,
        ``empleados_perm_temp``, ``remuneraciones``, ``activos_fijos``, ``inversion_bruta``,
        ``energia_kwh``), ``establecimientos`` y ``empresas`` (distintos), y:

        * ``productividad_laboral``: valor agregado por persona ocupada.
        * ``remuneracion_media``: remuneraciones por empleado permanente o temporal.
        * ``participacion_laboral``: remuneraciones / valor agregado, en %.
        * ``tasa_valor_agregado``: valor agregado / producción bruta, en %.

    Véase también
    -------------
    participacion : Participación de cada grupo en el total.
    crecimiento : Tasas de crecimiento anual.
    deflactar : Pasar a precios constantes.
    GLOSARIO : Definiciones de cada agregado.

    Notas
    -----
    Los montos están en miles de pesos corrientes; ``productividad_laboral`` y ``remuneracion_media``, en
    miles de pesos por persona. Las remuneraciones son salarios más prestaciones de los empleados
    permanentes y temporales (``salpeyte + prespyte``).

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> eam = pd.DataFrame({
    ...     "anio": [2023, 2023, 2024], "sector": ["Alimentos", "Químicos", "Alimentos"],
    ...     "nordest": [1, 2, 1], "nordemp": [10, 20, 10],
    ...     "prodbr2": [500.0, 800.0, 550.0], "consin2": [300.0, 500.0, 320.0], "valagri": [200.0, 300.0, 230.0],
    ...     "pertotal": [10, 20, 11], "pperytem": [9, 18, 10], "salpeyte": [50.0, 90.0, 55.0],
    ...     "prespyte": [20.0, 30.0, 22.0],
    ... })
    >>> res = dd.eam.resumen(eam, por="anio")
    >>> res[["anio", "valor_agregado", "productividad_laboral", "participacion_laboral"]].round(1)
       anio  valor_agregado  productividad_laboral  participacion_laboral
    0  2023           500.0                   16.7                   38.0
    1  2024           230.0                   20.9                   33.5

    Con la EAM:

    >>> eam = dd.eam.load(range(2022, 2025))  # doctest: +SKIP
    >>> dd.eam.resumen(eam, por="anio")[["anio", "establecimientos", "participacion_laboral"]].round(1)  # doctest: +SKIP
       anio  establecimientos  participacion_laboral
    0  2022              6775                   16.7
    1  2023              6714                   19.2
    2  2024              6583                   21.7
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

    if por:
        res = d.groupby(por, observed=True, dropna=False).agg(**agg)
    else:  # un solo grupo con todos los establecimientos
        res = d.groupby(np.zeros(len(d), dtype=int)).agg(**agg).reset_index(drop=True)
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
    """
    Participación de cada grupo en el total de una variable, año por año.

    Parámetros
    ----------
    df
        Microdatos de ``load`` (o cualquier tabla con ``tiempo``, ``por`` y ``variable``).
    variable
        Variable a repartir, por ejemplo ``"valagri"`` (valor agregado) o ``"pertotal"`` (empleo).
    por
        Variable de agrupación.
    tiempo
        Variable de tiempo.

    Devuelve
    --------
    DataFrame
        Una fila por año y grupo con la suma de ``variable`` y ``participacion`` en %.

    Véase también
    -------------
    resumen : Agregados por grupo.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> eam = pd.DataFrame({
    ...     "anio": [2023, 2023, 2024], "sector": ["Alimentos", "Químicos", "Alimentos"],
    ...     "nordest": [1, 2, 1], "nordemp": [10, 20, 10],
    ...     "prodbr2": [500.0, 800.0, 550.0], "consin2": [300.0, 500.0, 320.0], "valagri": [200.0, 300.0, 230.0],
    ...     "pertotal": [10, 20, 11], "pperytem": [9, 18, 10], "salpeyte": [50.0, 90.0, 55.0],
    ...     "prespyte": [20.0, 30.0, 22.0],
    ... })
    >>> dd.eam.participacion(eam, variable="valagri", por="sector")
       anio     sector  valagri  participacion
    0  2023  Alimentos    200.0           40.0
    1  2023   Químicos    300.0           60.0
    2  2024  Alimentos    230.0          100.0
    """
    d = df.groupby([tiempo, por], observed=True)[variable].sum().reset_index()
    d["participacion"] = 100 * d[variable] / d.groupby(tiempo)[variable].transform("sum")
    return d


def crecimiento(df: pd.DataFrame, valor: str, por: str | Iterable[str] | None = None, tiempo: str = "anio") -> pd.DataFrame:
    """
    Tasa de crecimiento de una variable de un año al siguiente, dentro de cada grupo.

    Parámetros
    ----------
    df
        Tabla con una fila por año y grupo, por ejemplo la salida de ``resumen``.
    valor
        Columna cuya variación se calcula.
    por
        Variable o lista de variables de grupo. ``None`` para una sola serie.
    tiempo
        Variable de tiempo.

    Devuelve
    --------
    DataFrame
        ``df`` ordenado, con la columna ``crec_<valor>`` en % (vacía en el primer año de cada grupo y en el
        año que sigue a uno que falta: de 2015 a 2018 no es un crecimiento anual).

    Véase también
    -------------
    deflactar : Para que el crecimiento sea real y no nominal.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> eam = pd.DataFrame({
    ...     "anio": [2023, 2023, 2024], "sector": ["Alimentos", "Químicos", "Alimentos"],
    ...     "nordest": [1, 2, 1], "nordemp": [10, 20, 10],
    ...     "prodbr2": [500.0, 800.0, 550.0], "consin2": [300.0, 500.0, 320.0], "valagri": [200.0, 300.0, 230.0],
    ...     "pertotal": [10, 20, 11], "pperytem": [9, 18, 10], "salpeyte": [50.0, 90.0, 55.0],
    ...     "prespyte": [20.0, 30.0, 22.0],
    ... })
    >>> res = dd.eam.resumen(eam, por="anio")
    >>> dd.eam.crecimiento(res, "valor_agregado")[["anio", "valor_agregado", "crec_valor_agregado"]]
       anio  valor_agregado  crec_valor_agregado
    0  2023           500.0                  NaN
    1  2024           230.0                -54.0
    """
    por = _as_list(por)
    d = df.sort_values(por + [tiempo]).copy()
    previo = d.groupby(por)[[valor, tiempo]].shift() if por else d[[valor, tiempo]].shift()
    consecutivo = (d[tiempo] - previo[tiempo]) == 1        # sin el año anterior no hay tasa anual
    d[f"crec_{valor}"] = (100 * (d[valor] / previo[valor] - 1)).where(consecutivo)
    return d


def deflactar(df: pd.DataFrame, columnas: Iterable[str], deflactor: pd.DataFrame | pd.Series,
              on: str | list[str] = "anio", base: float = 100.0, sufijo: str = "_real") -> pd.DataFrame:
    """
    Convierte valores corrientes a precios constantes.

    Calcula ``valor_real = valor / deflactor × base`` para cada columna.

    Parámetros
    ----------
    df
        Microdatos o tabla con valores corrientes.
    columnas
        Columnas a deflactar.
    deflactor
        Una Serie indexada por año, o un DataFrame con las columnas de ``on`` (por ejemplo
        ``["anio", "division"]``, para un deflactor por sector) y una columna ``deflactor``.
    on
        Columna o columnas con que se une el deflactor.
    base
        Valor del índice en el año base (100 si el deflactor es un índice base 100).
    sufijo
        Sufijo de las columnas nuevas.

    Devuelve
    --------
    DataFrame
        ``df`` con la columna ``deflactor`` y una columna ``<columna><sufijo>`` por cada columna. Si ``df``
        ya tenía una columna ``deflactor`` (de una llamada anterior), se reemplaza.

    Lanza
    -----
    ValueError
        Si el deflactor repite un año (o una combinación de ``on``): duplicaría filas de ``df``.

    Avisos
    ------
    UserWarning
        Si algunas filas no encontraron deflactor (quedan vacías).

    Notas
    -----
    ``dane-data`` no trae deflactores. Para la industria se suele usar el índice de precios del
    productor (IPP) del DANE, por año o por división CIIU.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> eam = pd.DataFrame({
    ...     "anio": [2023, 2023, 2024], "sector": ["Alimentos", "Químicos", "Alimentos"],
    ...     "nordest": [1, 2, 1], "nordemp": [10, 20, 10],
    ...     "prodbr2": [500.0, 800.0, 550.0], "consin2": [300.0, 500.0, 320.0], "valagri": [200.0, 300.0, 230.0],
    ...     "pertotal": [10, 20, 11], "pperytem": [9, 18, 10], "salpeyte": [50.0, 90.0, 55.0],
    ...     "prespyte": [20.0, 30.0, 22.0],
    ... })
    >>> ipp = pd.Series({2023: 100.0, 2024: 110.0})
    >>> dd.eam.deflactar(eam, ["valagri"], ipp)[["anio", "valagri", "valagri_real"]].round(1)
       anio  valagri  valagri_real
    0  2023    200.0         200.0
    1  2023    300.0         300.0
    2  2024    230.0         209.1
    """
    on = _as_list(on)
    d = df.drop(columns="deflactor", errors="ignore")      # de una llamada anterior: se reemplaza
    if isinstance(deflactor, pd.Series):
        deflactor = deflactor.rename("deflactor").rename_axis(on[0]).reset_index()
    if deflactor.duplicated(subset=on).any():
        repetidos = deflactor.loc[deflactor.duplicated(subset=on, keep=False), on].drop_duplicates()
        raise ValueError(f"El deflactor repite {', '.join(on)}: {repetidos.to_dict('records')}. Cada fila de "
                         "df se uniría con varios valores y quedaría duplicada.")
    d = d.merge(deflactor[on + ["deflactor"]], on=on, how="left")
    for c in _as_list(columnas):  # una sola columna ("valagri") no se parte en letras
        d[f"{c}{sufijo}"] = pd.to_numeric(d[c], errors="coerce") / d["deflactor"] * base
    faltan = d["deflactor"].isna().mean()
    if faltan > 0:
        import warnings
        warnings.warn(f"{faltan:.1%} de las filas no encontraron deflactor.")
    return d


def panel(df: pd.DataFrame, balanceado: bool = False, anios: Iterable[int] | None = None) -> pd.DataFrame:
    """
    Panel de establecimientos: una fila por establecimiento y año.

    Parámetros
    ----------
    df
        Microdatos de ``load``.
    balanceado
        Conservar solo los establecimientos observados en todos los años de ``anios``.
    anios
        Años del panel. Por defecto, todos los de ``df``.

    Devuelve
    --------
    DataFrame
        Indexado por (``nordest``, ``anio``) y ordenado, listo para modelos de panel (por ejemplo
        ``linearmodels.PanelOLS``). Si un establecimiento aparece dos veces en un año, se conserva la
        primera.

    Véase también
    -------------
    supervivencia : Cuántos establecimientos siguen de un año al siguiente.

    Notas
    -----
    La anonimización del ANDA puede cambiar los identificadores entre catálogos; revise la persistencia
    con ``supervivencia`` antes de usar un panel largo.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> eam = pd.DataFrame({
    ...     "anio": [2023, 2023, 2024], "sector": ["Alimentos", "Químicos", "Alimentos"],
    ...     "nordest": [1, 2, 1], "nordemp": [10, 20, 10],
    ...     "prodbr2": [500.0, 800.0, 550.0], "consin2": [300.0, 500.0, 320.0], "valagri": [200.0, 300.0, 230.0],
    ...     "pertotal": [10, 20, 11], "pperytem": [9, 18, 10], "salpeyte": [50.0, 90.0, 55.0],
    ...     "prespyte": [20.0, 30.0, 22.0],
    ... })
    >>> dd.eam.panel(eam, balanceado=True).index.tolist()
    [(1, 2023), (1, 2024)]
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

    Parámetros
    ----------
    df
        Microdatos de ``load``.

    Devuelve
    --------
    DataFrame
        Una fila por par de años consecutivos con ``establecimientos``, ``siguen_al_anio_siguiente`` y
        ``pct_siguen``.

    Véase también
    -------------
    panel : Panel de establecimientos.

    Notas
    -----
    Una caída brusca de ``pct_siguen`` suele indicar que cambiaron los identificadores (``nordest``)
    entre catálogos del ANDA, no que hayan cerrado plantas.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> eam = pd.DataFrame({
    ...     "anio": [2023, 2023, 2024], "sector": ["Alimentos", "Químicos", "Alimentos"],
    ...     "nordest": [1, 2, 1], "nordemp": [10, 20, 10],
    ...     "prodbr2": [500.0, 800.0, 550.0], "consin2": [300.0, 500.0, 320.0], "valagri": [200.0, 300.0, 230.0],
    ...     "pertotal": [10, 20, 11], "pperytem": [9, 18, 10], "salpeyte": [50.0, 90.0, 55.0],
    ...     "prespyte": [20.0, 30.0, 22.0],
    ... })
    >>> dd.eam.supervivencia(eam)
       anio  siguiente  establecimientos  siguen_al_anio_siguiente  pct_siguen
    0  2023       2024                 2                         1        50.0

    Con la EAM:

    >>> dd.eam.supervivencia(dd.eam.load(range(2022, 2025))).round(1)  # doctest: +SKIP
       anio  siguiente  establecimientos  siguen_al_anio_siguiente  pct_siguen
    0  2022       2023              6775                      6605        97.5
    1  2023       2024              6714                      6420        95.6
    """
    ids = df.dropna(subset=["nordest"]).groupby("anio")["nordest"].apply(set).sort_index()
    rows = []
    for (y0, a), (y1, b) in zip(ids.items(), list(ids.items())[1:]):
        rows.append({"anio": y0, "siguiente": y1, "establecimientos": len(a),
                     "siguen_al_anio_siguiente": len(a & b), "pct_siguen": 100 * len(a & b) / max(len(a), 1)})
    return pd.DataFrame(rows)
