"""
Carga y armonización de la Medición de Pobreza Monetaria y Desigualdad: un hogar por fila.

El archivo de hogares de cada año trae el ingreso per cápita de la unidad de gasto (``INGPCUG``), las líneas de pobreza
(``LP``) y de pobreza extrema (``LI``) de su dominio y mes, y el factor de expansión (``FEX_C``). Un hogar es pobre si su
ingreso per cápita está por debajo de la línea, y cada persona del hogar (``NPER``, también las que no son de la unidad
de gasto, como el servicio doméstico) cuenta con ese ingreso: el peso de cada hogar en los indicadores de personas es
``fex * personas``. Así reproduce el DANE sus cifras publicadas.

Hay dos metodologías que no se pueden comparar:

* ``mesep``, 2012–2018: líneas de la ENIG 2006–2007 (Misión para el Empalme de las Series de Empleo, Pobreza y
  Desigualdad).
* ``actualizacion``, desde 2019: líneas de la ENPH 2016–2017.

Con ``empalme=True`` la serie 2012–2021 queda comparable con la de 2022 en adelante, como la que publica el DANE: factor
de empalme al marco 2018 (``FEX_G``) en 2012–2020, líneas actualizadas en 2012–2018 y el ingreso empalmado de 2021.

Lo que el DANE escribe distinto según el año (ver la tabla de diferencias del README):

* El departamento es ``DPTO`` o ``DEPTO``; en 2014 es un número de 1 a 24 que no es el código DANE, y en 2025 viene el
  nombre en vez del código.
* ``DOMINIO`` en 2017 va con tildes y en tipo título (``Bogotá``); los demás años en mayúscula sin tildes.
* El ingreso con arriendo imputado es ``INGTOTUGARR`` hasta 2022 e ``INGTOTARR`` desde 2023; el factor departamental es
  ``FEX_DPTO_C`` en 2012–2014.

Convención, como en la GEIH: en minúscula las variables armonizadas, en MAYÚSCULA las originales del DANE.
"""

from __future__ import annotations

import logging
import numbers
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from .._io import read_table
from ..geih.loader import CATEGORIAS as _CATEGORIAS_GEIH
from ..referencias import DEPARTAMENTOS, strip_accents
from .downloader import ARCHIVOS_EMPALME, EXTENSIONES

log = logging.getLogger("dane_data.pobreza")

LLAVES = ["DIRECTORIO", "SECUENCIA_P"]
# Variables del DANE que necesita la armonización (con todos los nombres que han tenido)
CORE = ["DIRECTORIO", "SECUENCIA_P", "MES", "CLASE", "DOMINIO", "DPTO", "DEPTO", "NPER", "NPERSUG", "INGTOTUG",
        "INGTOTUGARR", "INGTOTARR", "INGPCUG", "LI", "LP", "FEX_C", "FEX_DPTO", "FEX_DPTO_C"]

# Nombre sin tildes y en mayúscula del DANE -> nombre en la tabla
DOMINIOS = {
    "ARMENIA": "Armenia", "BARRANQUILLA": "Barranquilla", "BOGOTA": "Bogotá", "BUCARAMANGA": "Bucaramanga", "CALI": "Cali",
    "CARTAGENA": "Cartagena", "CUCUTA": "Cúcuta", "FLORENCIA": "Florencia", "IBAGUE": "Ibagué", "MANIZALES": "Manizales",
    "MEDELLIN": "Medellín", "MONTERIA": "Montería", "NEIVA": "Neiva", "PASTO": "Pasto", "PEREIRA": "Pereira",
    "POPAYAN": "Popayán", "QUIBDO": "Quibdó", "RIOHACHA": "Riohacha", "SANTA MARTA": "Santa Marta",
    "SINCELEJO": "Sincelejo", "TUNJA": "Tunja", "VALLEDUPAR": "Valledupar", "VILLAVICENCIO": "Villavicencio",
    "RESTO URBANO": "Resto urbano", "RURAL": "Rural",
}
# Los grandes dominios del DANE: las 13 ciudades con su área metropolitana, el resto de las cabeceras y la zona rural
TRECE_CIUDADES = ("Bogotá", "Medellín", "Cali", "Barranquilla", "Bucaramanga", "Manizales", "Pasto", "Pereira", "Cúcuta",
                  "Ibagué", "Montería", "Cartagena", "Villavicencio")
GRUPOS_DOMINIO = ("13 ciudades y áreas metropolitanas", "Otras cabeceras", "Centros poblados y rural disperso")
# En 2014 el departamento del archivo de hogares es un número de 1 a 24 (el de personas sí trae el código). Se deduce de
# las ciudades capitales; el 24, el único sin capital entre los dominios, es Cundinamarca.
_DPTO_2014 = {1: 15, 2: 41, 3: 18, 4: 76, 5: 17, 6: 20, 7: 66, 8: 52, 9: 68, 10: 50, 11: 63, 12: 54, 13: 73, 14: 13,
              15: 47, 16: 27, 17: 70, 18: 44, 19: 19, 20: 8, 21: 5, 22: 23, 23: 11, 24: 25}
_DPTO_POR_NOMBRE = {strip_accents(n): c for c, n in DEPARTAMENTOS.items()}

METODOLOGIAS = ("mesep", "actualizacion")
CATEGORIAS = {
    "zona": _CATEGORIAS_GEIH["zona"],
    "departamento": _CATEGORIAS_GEIH["departamento"],
    "dominio": pd.CategoricalDtype(list(DOMINIOS.values())),
    "grupo_dominio": pd.CategoricalDtype(list(GRUPOS_DOMINIO)),
    "metodologia": pd.CategoricalDtype(list(METODOLOGIAS)),
}

ETIQUETAS = {
    "anio": "Año de la encuesta",
    "mes": "Mes de la encuesta (MES)",
    "zona": "Urbano (cabecera) o rural (centros poblados y disperso) (CLASE)",
    "dominio": "Dominio de la medición: 23 ciudades con su área metropolitana, resto urbano y rural (DOMINIO)",
    "grupo_dominio": "Gran dominio del DANE: 13 ciudades y áreas metropolitanas, otras cabeceras o centros poblados y rural "
                     "disperso",
    "departamento": "Departamento (DPTO; 23 departamentos y Bogotá)",
    "personas": "Personas del hogar, también las que no son de la unidad de gasto (NPER)",
    "personas_ug": "Personas de la unidad de gasto: sin servicio doméstico ni pensionistas (NPERSUG)",
    "ingreso_ug": "Ingreso total de la unidad de gasto, pesos al mes (INGTOTUG)",
    "ingreso_ug_arriendo": "Ingreso total de la unidad de gasto con arriendo imputado (INGTOTUGARR, INGTOTARR)",
    "ingreso_pc": "Ingreso per cápita de la unidad de gasto con arriendo imputado (INGPCUG)",
    "ingreso_pc_dpto": "Ingreso per cápita para las cifras departamentales: el mismo, salvo 2021 con empalme (INGPUG_EMP)",
    "linea_pobreza": "Línea de pobreza monetaria del dominio y mes, pesos por persona al mes (LP)",
    "linea_pobreza_extrema": "Línea de pobreza monetaria extrema del dominio y mes (LI)",
    "pobre": "El hogar está en pobreza monetaria: ingreso_pc < linea_pobreza",
    "pobre_extremo": "El hogar está en pobreza monetaria extrema: ingreso_pc < linea_pobreza_extrema",
    "fex": "Factor de expansión del hogar (FEX_C; con empalme, FEX_C × FEX_G)",
    "fex_dpto": "Factor de expansión departamental del hogar (FEX_DPTO, FEX_DPTO_C); con empalme, vacío antes de 2021",
    "metodologia": "Metodología de las líneas: 'mesep' (2012–2018) o 'actualizacion' (desde 2019 y con empalme)",
    "empalmado": "Si es la serie empalmada al marco 2018 (load con empalme=True), comparable en toda 2012–2025",
}


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("pobreza")


def _anios(years) -> set[int] | None:
    if years is None:
        return None
    # numbers.Integral: también un año de numpy (df.anio.max())
    return {int(y) for y in ([years] if isinstance(years, (numbers.Integral, str)) else years)}


def _archivo(carpeta: Path, nombre: str) -> Path | None:
    for extension in EXTENSIONES:
        if (ruta := carpeta / f"{nombre}{extension}").is_file():
            return ruta
    return None


def find_files(years: Iterable[int] | int | None = None, root=None) -> dict[int, Path]:
    """
    Archivo de hogares de cada año descargado.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("pobreza")``).

    Devuelve
    --------
    dict
        ``{año: ruta}``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.pobreza.find_files(2025)  # doctest: +SKIP
    {2025: PosixPath('/home/ana/dane_data_datos/pobreza/datos/2025/hogares.csv')}
    """
    base = _root(root) / "datos"
    if not base.is_dir():
        return {}
    pedidos = _anios(years)
    out = {}
    # Solo carpetas de año: datos/empalme/ no es un año
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir() and len(p.name) == 4 and p.name.isdigit()):
        anio = int(carpeta.name)
        if (pedidos is None or anio in pedidos) and (ruta := _archivo(carpeta, "hogares")):
            out[anio] = ruta
    return out


def available(root=None) -> pd.DataFrame:
    """
    Tabla de lo descargado de la pobreza monetaria.

    Parámetros
    ----------
    root
        Carpeta raíz. Por defecto, la configurada.

    Devuelve
    --------
    DataFrame
        Una fila por año con ``anio``, ``hogares`` y ``personas`` (si están) y ``tamano_mb``. Los archivos de empalme
        (``empalme_2012_2020``…) aparecen con ``anio`` vacío.

    Véase también
    -------------
    download : Descargar lo que falta.
    load : Cargar lo descargado.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.pobreza.available().tail(2)  # doctest: +SKIP
        anio            archivo  hogares  personas  tamano_mb
    13  2025               2025     True      True      260.1
    14  <NA>  empalme_2012_2020    False     False       75.7
    """
    base = _root(root) / "datos"
    filas = []
    for anio, ruta in find_files(root=root).items():
        personas = _archivo(ruta.parent, "personas")
        filas.append({"anio": anio, "archivo": str(anio), "hogares": True, "personas": personas is not None,
                      "tamano_mb": round(sum(f.stat().st_size for f in (ruta, personas) if f) / 1e6, 1)})
    for nombre in ARCHIVOS_EMPALME:
        if ruta := _archivo(base / "empalme", nombre):
            filas.append({"anio": pd.NA, "archivo": nombre, "hogares": False, "personas": False,
                          "tamano_mb": round(ruta.stat().st_size / 1e6, 1)})
    tabla = pd.DataFrame(filas, columns=["anio", "archivo", "hogares", "personas", "tamano_mb"])
    return tabla.astype({"anio": "Int64"})


# --------------------------------------------------------------------------- #
# Armonización
# --------------------------------------------------------------------------- #
def _numero(df: pd.DataFrame, *columnas: str) -> pd.Series:
    """La primera de ``columnas`` que trae el archivo, como número decimal."""
    for c in columnas:
        if c in df.columns:
            return pd.to_numeric(df[c], errors="coerce").astype("float64")
    raise ValueError(f"El archivo no trae {' ni '.join(columnas)}.")


def _sin_tildes(valores: pd.Series) -> pd.Series:
    return valores.astype(str).map(lambda v: strip_accents(v).upper().strip())


def _dominio(df: pd.DataFrame, anio: int) -> pd.Series:
    norm = _sin_tildes(df["DOMINIO"])
    if faltan := sorted(set(norm) - set(DOMINIOS)):
        raise ValueError(f"Dominios desconocidos en {anio}: {faltan}.")
    return pd.Categorical(norm.map(DOMINIOS), dtype=CATEGORIAS["dominio"])


def _departamento(df: pd.DataFrame, anio: int) -> pd.Series:
    columna = next((c for c in ("DPTO", "DEPTO") if c in df.columns), None)
    if columna is None:
        raise ValueError(f"El archivo de hogares de {anio} no trae el departamento (DPTO ni DEPTO).")
    valores = df[columna]
    numeros = pd.to_numeric(valores, errors="coerce")
    if numeros.notna().all():
        codigo = numeros.astype(int)
        if anio == 2014:
            codigo = codigo.map(_DPTO_2014)
    else:  # 2025: el nombre del departamento
        codigo = _sin_tildes(valores).str.lower().map(_DPTO_POR_NOMBRE)
    nombre = codigo.map(DEPARTAMENTOS)
    if nombre.isna().any():
        raise ValueError(f"Departamentos desconocidos en {anio}: {sorted(set(valores[nombre.isna()].astype(str)))}.")
    return pd.Categorical(nombre, dtype=CATEGORIAS["departamento"])


def harmonize(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """
    Agrega las variables armonizadas a un archivo de hogares leído con los nombres del DANE en mayúscula.

    Parámetros
    ----------
    df
        El archivo de hogares de un año, como lo deja ``dane_data._io.read_table``.
    anio
        El año del archivo.

    Devuelve
    --------
    DataFrame
        Una copia con las variables de ``ETIQUETAS`` agregadas. ``pobre`` y ``pobre_extremo`` se calculan del ingreso y
        las líneas, no se toman de ``POBRE`` e ``INDIGENTE`` (que coinciden en todos los años publicados).

    Lanza
    -----
    ValueError
        Si un dominio o un departamento no se reconoce, o si a algún hogar le falta el ingreso o las líneas.
    """
    df = df.drop(columns=[c for c in df.columns if c.startswith("UNNAMED")])
    for c in [*LLAVES, "MES"]:
        df[c] = _numero(df, c).astype("int64")  # 2022 trae DIRECTORIO como decimal
    df["anio"] = anio
    df["mes"] = df["MES"]
    clase = _numero(df, "CLASE")
    df["zona"] = pd.Categorical(clase.map({1: "Urbano (cabecera)", 2: "Rural (centros poblados y disperso)"}),
                                dtype=CATEGORIAS["zona"])
    df["dominio"] = _dominio(df, anio)
    df["grupo_dominio"] = pd.Categorical(
        np.where(df["zona"].eq("Rural (centros poblados y disperso)"), GRUPOS_DOMINIO[2],
                 np.where(df["dominio"].isin(TRECE_CIUDADES), GRUPOS_DOMINIO[0], GRUPOS_DOMINIO[1])),
        dtype=CATEGORIAS["grupo_dominio"])
    df["departamento"] = _departamento(df, anio)
    for nombre, original in (("personas", "NPER"), ("personas_ug", "NPERSUG")):
        conteo = _numero(df, original)
        df[nombre] = conteo.astype("int64") if conteo.notna().all() else conteo  # vacíos: los reporta _clasificar
    df["ingreso_ug"] = _numero(df, "INGTOTUG")
    df["ingreso_ug_arriendo"] = _numero(df, "INGTOTUGARR", "INGTOTARR")
    df["ingreso_pc"] = _numero(df, "INGPCUG")
    df["ingreso_pc_dpto"] = df["ingreso_pc"]
    df["linea_pobreza"] = _numero(df, "LP")
    df["linea_pobreza_extrema"] = _numero(df, "LI")
    df["fex"] = _numero(df, "FEX_C")
    df["fex_dpto"] = _numero(df, "FEX_DPTO", "FEX_DPTO_C")
    df["metodologia"] = pd.Categorical([METODOLOGIAS[anio >= 2019]] * len(df), dtype=CATEGORIAS["metodologia"])
    df["empalmado"] = False
    return _clasificar(df, anio)


def _clasificar(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """``pobre`` y ``pobre_extremo`` del ingreso y las líneas. Un dato faltante es un error: como False sesgaría la incidencia."""
    faltan = df[["ingreso_pc", "linea_pobreza", "linea_pobreza_extrema", "fex", "personas"]].isna().sum()
    if faltan.any():
        raise ValueError(f"Hogares sin dato en {anio}: {faltan[faltan > 0].to_dict()}.")
    df["pobre"] = df["ingreso_pc"] < df["linea_pobreza"]
    df["pobre_extremo"] = df["ingreso_pc"] < df["linea_pobreza_extrema"]
    return df


# --------------------------------------------------------------------------- #
# Empalme al marco 2018
# --------------------------------------------------------------------------- #
def _leer_empalme(nombre: str, root) -> pd.DataFrame:
    ruta = _archivo(_root(root) / "datos" / "empalme", nombre)
    if ruta is None:
        raise FileNotFoundError(
            f"Falta {nombre} en {_root(root) / 'datos' / 'empalme'}. Descárguelo con "
            "dane_data.pobreza.download(empalme=True)."
        )
    tabla = read_table(ruta)
    tabla.columns = ["ANIO" if strip_accents(c) == "ano" else c for c in tabla.columns]  # AÑO
    for c in ("DIRECTORIO", "SECUENCIA_P", "MES", "ANIO"):
        if c in tabla.columns:
            tabla[c] = pd.to_numeric(tabla[c], errors="coerce").astype("int64")
    return tabla


def _unir_1a1(df: pd.DataFrame, otra: pd.DataFrame, llaves: list[str], que: str, anio: int) -> pd.DataFrame:
    """Une ``otra`` por ``llaves`` exigiendo una fila por hogar en las dos y que todos los hogares encuentren la suya."""
    if otra.duplicated(llaves).any():
        raise ValueError(f"{que} tiene llaves repetidas en {anio}.")
    unido = df.merge(otra, on=llaves, how="left", validate="m:1", indicator="_union")
    if (sin := int((unido.pop("_union") != "both").sum())):
        raise ValueError(f"{sin} hogares de {anio} no están en {que}: el empalme no se puede aplicar.")
    return unido


def _empalmar(df: pd.DataFrame, anio: int, fuentes: dict) -> pd.DataFrame:
    """Lleva un año al marco 2018 como el DANE (ver el docstring del módulo). Los años desde 2022 ya están en él."""
    if anio <= 2020:
        fex_g = fuentes["empalme_2012_2020"]
        fex_g = fex_g.loc[fex_g["ANIO"] == anio, ["MES", *LLAVES, "FEX_G"]]
        df = _unir_1a1(df, fex_g, ["MES", *LLAVES], "el factor de empalme 2012–2020", anio)
        df["fex"] = df["fex"] * pd.to_numeric(df.pop("FEX_G"))
    if anio <= 2018:
        lineas = fuentes["lineas_2012_2018"]
        lineas = lineas.loc[lineas["ANIO"] == anio].assign(_dom=lambda t: _sin_tildes(t["DOMINIO"]))
        lineas = lineas[["MES", "_dom", "LP", "LI"]].rename(columns={"LP": "_lp", "LI": "_li"})
        df = _unir_1a1(df.assign(_dom=_sin_tildes(df["DOMINIO"])), lineas, ["MES", "_dom"],
                       "las líneas actualizadas 2012–2018", anio).drop(columns="_dom")
        df["linea_pobreza"] = pd.to_numeric(df.pop("_lp"))
        df["linea_pobreza_extrema"] = pd.to_numeric(df.pop("_li"))
    if anio == 2021:
        emp = fuentes["hogares_empalmado_2021"][["MES", *LLAVES, "INGPCUG_EMP", "FEX_C"]]
        emp = emp.rename(columns={"INGPCUG_EMP": "_ing", "FEX_C": "_fex"})
        df = _unir_1a1(df, emp, ["MES", *LLAVES], "los hogares empalmados de 2021", anio)
        df["ingreso_pc"] = pd.to_numeric(df.pop("_ing"))
        df["fex"] = pd.to_numeric(df.pop("_fex"))
        # Las cifras departamentales de 2021 tienen su propio ingreso y factor empalmados (el anexo departamental)
        if (dpto := fuentes.get("hogares_empalmado_dpto_2021")) is not None:
            dpto = dpto[["MES", *LLAVES, "INGPUG_EMP", "FEX_DPTO"]].rename(columns={"INGPUG_EMP": "_ing", "FEX_DPTO": "_fex"})
            df = _unir_1a1(df, dpto, ["MES", *LLAVES], "los hogares empalmados departamentales de 2021", anio)
            df["ingreso_pc_dpto"] = pd.to_numeric(df.pop("_ing"))
            df["fex_dpto"] = pd.to_numeric(df.pop("_fex"))
        else:
            df["ingreso_pc_dpto"], df["fex_dpto"] = df["ingreso_pc"], np.nan
    if anio <= 2020:
        # El DANE no publica cifras departamentales empalmadas antes de 2021: sin factor, nadie las calcula por error
        df["ingreso_pc_dpto"], df["fex_dpto"] = df["ingreso_pc"], np.nan
    if anio <= 2021:
        df["metodologia"] = pd.Categorical(["actualizacion"] * len(df), dtype=CATEGORIAS["metodologia"])
    df["empalmado"] = True
    return _clasificar(df, anio)


def _avisar_metodologias(anios: Iterable[int], empalme: bool) -> None:
    anios = set(anios)
    if not empalme and min(anios) <= 2018 < max(anios):
        warnings.warn(
            "Los años hasta 2018 usan las líneas de pobreza de la MESEP y los de 2019 en adelante las actualizadas: no "
            "son comparables. Para una serie comparable use empalme=True (la serie que publica el DANE).",
            UserWarning, stacklevel=3,
        )
    elif not empalme and min(anios) <= 2021 < max(anios):
        warnings.warn(
            "Hasta 2021 la encuesta usa el marco del censo 2005 y desde 2022 el del CNPV 2018: los niveles cambian. Para "
            "una serie comparable use empalme=True.", UserWarning, stacklevel=3,
        )


def load(
    years: Iterable[int] | int | None = None,
    empalme: bool = False,
    columns="core",
    harmonize_vars: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Carga la Medición de Pobreza Monetaria y Desigualdad: un hogar por fila, con las variables armonizadas.

    Parámetros
    ----------
    years
        Año, lista o rango de años (2012–2025). ``None`` para todos los descargados.
    empalme
        Llevar 2012–2021 al marco 2018 para comparar con 2022 en adelante, como la serie que publica el DANE: factor de
        empalme en 2012–2020, líneas actualizadas en 2012–2018 e ingreso empalmado en 2021. Necesita los archivos de
        ``download(empalme=True)``. Los años desde 2022 no cambian.
    columns
        ``"core"`` (solo las variables armonizadas y las llaves; por defecto), ``"all"`` (también todas las del DANE) o
        una lista de variables del DANE para agregar, por ejemplo ``["P5090", "NINDIGENTES"]``.
    harmonize_vars
        Agregar las variables armonizadas. Si False, solo las del DANE y ``anio`` (no compatible con ``empalme``).
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Una fila por hogar con ``DIRECTORIO``, ``SECUENCIA_P`` y las variables de ``ETIQUETAS``.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años, o faltan los archivos de empalme.
    ValueError
        Si un dominio o departamento no se reconoce, a un hogar le falta el ingreso o las líneas, o el empalme no
        encuentra a todos los hogares.

    Avisos
    ------
    UserWarning
        Si sin empalme se juntan años de metodologías o marcos distintos.

    Véase también
    -------------
    indicadores : Incidencia, brecha, severidad y Gini.
    serie_indicadores : Lo mismo, año por año y guardado en disco.
    unir_geih : Pegar estas variables a las personas de la GEIH.
    ETIQUETAS : Qué es cada variable armonizada.

    Notas
    -----
    Las cifras de personas se calculan con el peso ``fex * personas``: cada persona del hogar cuenta con el ingreso
    per cápita de su unidad de gasto. Es lo que hace :func:`indicadores`.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> hog = dd.pobreza.load(2025)  # doctest: +SKIP
    >>> peso = hog.fex * hog.personas  # doctest: +SKIP
    >>> round(float((peso * hog.pobre).sum() / peso.sum() * 100), 1)  # doctest: +SKIP
    28.0
    """
    archivos = find_files(years, root=root)
    if not archivos:
        raise FileNotFoundError(
            f"No hay datos de pobreza para años={years} en {_root(root)}. "
            "Descárguelos con dane_data.pobreza.download(...) o revise dane_data.set_paths(...)."
        )
    if empalme and not harmonize_vars:
        raise ValueError("empalme=True necesita harmonize_vars=True.")
    _avisar_metodologias(archivos, empalme)
    if isinstance(columns, str) and columns not in ("core", "all"):
        columns = [columns]  # un solo nombre: list("P5090") lo partiría en letras
    extras = [] if isinstance(columns, str) else [c.upper() for c in columns]
    leer = None if columns == "all" else set(CORE) | set(extras)
    fuentes = {}
    if empalme:  # solo los archivos que usan los años pedidos (el factor 2012–2020 pesa 75 MB)
        necesarios = {"empalme_2012_2020": min(archivos) <= 2020, "lineas_2012_2018": min(archivos) <= 2018,
                      "hogares_empalmado_2021": 2021 in archivos}
        fuentes = {n: _leer_empalme(n, root) for n, hace_falta in necesarios.items() if hace_falta}
        if 2021 in archivos and _archivo(_root(root) / "datos" / "empalme", "hogares_empalmado_dpto_2021"):
            fuentes["hogares_empalmado_dpto_2021"] = _leer_empalme("hogares_empalmado_dpto_2021", root)  # opcional

    partes = []
    for i, (anio, ruta) in enumerate(sorted(archivos.items())):
        if progress:
            progress(i / len(archivos), f"Leyendo pobreza {anio}")
        crudo = read_table(ruta, columns=None if leer is None else (lambda c: c in leer))
        if not harmonize_vars:
            partes.append(crudo.assign(anio=anio))
            continue
        d = harmonize(crudo, anio)
        if empalme and anio <= 2021:
            d = _empalmar(d, anio, fuentes)
        d["empalmado"] = empalme  # desde 2022 ya está en el marco 2018: con empalme=True es la misma serie
        if columns != "all":
            d = d[[*LLAVES, *ETIQUETAS, *[c for c in extras if c in d.columns and c not in LLAVES]]]
        partes.append(d)
    if progress:
        progress(1.0, "Listo")
    return pd.concat(partes, ignore_index=True)
