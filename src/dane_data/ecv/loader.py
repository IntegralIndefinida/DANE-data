"""
Carga y armonización de la Encuesta Nacional de Calidad de Vida (ECV) ya descargada.

Un capítulo del cuestionario por carpeta, en ``<raíz>/datos/<año>/<módulo>/``. El DANE publica cada capítulo en CSV
(``;``, coma decimal), Stata y SPSS; se usa el CSV y, si no está, el Stata.

Cada capítulo es una tabla de viviendas, de hogares o de personas. Las llaves, según la *Estructura de la base de datos*
del DANE:

* vivienda: ``DIRECTORIO``.
* hogar: ``DIRECTORIO`` y ``SECUENCIA_ENCUESTA`` (el número del hogar en la vivienda; ``SECUENCIA_P`` es siempre 1).
* persona: ``DIRECTORIO``, ``SECUENCIA_P`` (el hogar) y ``SECUENCIA_ENCUESTA`` (la persona en el hogar, igual a ``ORDEN``).

``load`` lleva todas las tablas a las mismas llaves: en las de hogar, el número del hogar queda en ``SECUENCIA_P``, como
en las de personas. El factor de expansión ``FEX_C`` es el mismo en todas las tablas de una vivienda. En 2018 se
reemplaza por el del CNPV 2018, que el DANE publicó aparte y que usa la serie oficial 2018–2025.
"""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from .._hooks import archivos_datos
from .._io import read_table
from ..stats import _enteros
from ..eevv.loader import _categoria, _unir
from ..referencias import DEPARTAMENTOS

# Capítulos que se descargan y se cargan: los que usan las variables armonizadas, los indicadores y el IPM
MODULOS = ("vivienda", "servicios", "tenencia", "condiciones", "caracteristicas", "salud", "primera_infancia",
           "educacion", "fuerza_trabajo", "tic", "trabajo_infantil")
# Los factores de expansión de 2018 basados en el CNPV 2018, que el DANE publicó aparte: no son un capítulo
_FACTORES = "factores"
# La base complementaria del IPM 2020 (catálogo del IPM, no de la ECV): estrategias de estudio en casa de cada niño que
# estudia, con las que el DANE armó la inasistencia escolar de 2020 («integra información del SIMAT»)
_COMPLEMENTARIA = "complementaria"
_INTERNOS = (_FACTORES, _COMPLEMENTARIA)
EXTENSIONES = (".csv", ".dta")

UNIDADES = {"vivienda": "vivienda", "servicios": "hogar", "tenencia": "hogar", "condiciones": "hogar",
            **{m: "persona" for m in ("caracteristicas", "salud", "primera_infancia", "educacion", "fuerza_trabajo",
                                      "tic", "trabajo_infantil")}}
KEYS_HOGAR = ["DIRECTORIO", "SECUENCIA_P"]
KEYS_PERSONA = ["DIRECTORIO", "SECUENCIA_P", "SECUENCIA_ENCUESTA"]
_BASE = {"persona": "caracteristicas", "hogar": "servicios"}  # el capítulo que trae a todas las personas u hogares
# De la vivienda se toma siempre la geografía. El departamento es DPTO en 2018 y P1_DEPARTAMENTO desde 2019.
_GEOGRAFIA = ["CLASE", "REGION", "P1_DEPARTAMENTO", "DPTO", "P1_MUNICIPIO"]
_ARMONIZAR = ["P6020", "P6040", "P6051", "P6080"]  # sexo, edad, parentesco y etnia, de Características

_AREAS = {1: "Cabecera", 2: "Centros poblados y rural disperso"}
_REGIONES = {1: "Caribe", 2: "Oriental", 3: "Central", 4: "Pacífica", 5: "Bogotá D.C.", 6: "Antioquia",
             7: "Valle del Cauca", 8: "San Andrés", 9: "Orinoquía-Amazonía"}
# Región de cada departamento, para los años que no traen REGION (tomada de 2018 y 2025, que sí la traen). Pacífica es
# sin el Valle del Cauca, y la parte rural de Bogotá va en Oriental.
_REGION_DPTO = {5: 6, 8: 1, 11: 5, 13: 1, 15: 2, 17: 3, 18: 3, 19: 4, 20: 1, 23: 1, 25: 2, 27: 4, 41: 3, 44: 1, 47: 1,
                50: 2, 52: 4, 54: 2, 63: 3, 66: 3, 68: 2, 70: 1, 73: 3, 76: 7, 81: 9, 85: 9, 86: 9, 88: 8, 91: 9,
                94: 9, 95: 9, 97: 9, 99: 9}
_SEXO = {1: "Hombre", 2: "Mujer"}
_PARENTESCO = {1: "Jefe(a) del hogar", 2: "Pareja o cónyuge", 3: "Hijo(a) o hijastro(a)", 4: "Nieto(a)",
               5: "Padre, madre, padrastro o madrastra", 6: "Suegro(a)", 7: "Hermano(a) o hermanastro(a)",
               8: "Yerno o nuera", 9: "Otro pariente", 10: "Empleado(a) del servicio doméstico",
               11: "Pariente del servicio doméstico", 12: "Trabajador(a)", 13: "Pensionista", 14: "Otro no pariente"}
_ETNIA = {1: "Indígena", 2: "Gitano(a) o Rom", 3: "Raizal", 4: "Palenquero(a)",
          5: "Negro(a), mulato(a), afrodescendiente", 6: "Ningún grupo étnico"}
_REGIMEN = {1: "Contributivo", 2: "Especial", 3: "Subsidiado", 9: "No sabe"}
_TENENCIA = {1: "Propia, totalmente pagada", 2: "Propia, la están pagando", 3: "En arriendo o subarriendo",
             4: "Usufructo (con permiso, sin pago)", 5: "Posesión sin título (ocupante de hecho)", 6: "Propiedad colectiva"}
# Servicios de la vivienda (P8520Sx, Datos de la vivienda) y del hogar: (columna armonizada, variable del DANE)
_SERVICIOS = (("energia", "P8520S1"), ("acueducto", "P8520S5"), ("alcantarillado", "P8520S3"),
              ("recoleccion_basuras", "P8520S4"), ("gas_natural", "P5666"))

# Tipos fijos: así se conservan al unir años con pd.concat
CATEGORIAS = {
    "area": _categoria(_AREAS.values()),
    "region": _categoria(_REGIONES.values()),
    "departamento": _categoria(sorted(DEPARTAMENTOS.values())),
    "sexo": _categoria(_SEXO.values()),
    "parentesco": _categoria(_PARENTESCO.values()),
    "etnia": _categoria(_ETNIA.values()),
    "regimen_salud": _categoria(_REGIMEN.values()),
    "tenencia_vivienda": _categoria(_TENENCIA.values()),
}
_COMUNES = {
    "anio": "Año de la encuesta",
    "fex": "Factor de expansión (FEX_C; en 2018, el del CNPV 2018)",
    "area": "Cabecera o centros poblados y rural disperso (CLASE)",
    "region": "Región de la ECV (REGION): Caribe, Oriental, Central, Pacífica (sin el Valle), Bogotá D.C., Antioquia, "
              "Valle del Cauca, San Andrés u Orinoquía-Amazonía",
    "departamento": "Departamento (P1_DEPARTAMENTO; DPTO en 2018)",
}
# Del hogar y de la vivienda: están en la tabla de hogares y, repetidas en cada miembro, en la de personas
_DEL_HOGAR = {
    "energia": "La vivienda tiene energía eléctrica (P8520S1; capítulo vivienda)",
    "acueducto": "La vivienda tiene acueducto (P8520S5; vivienda)",
    "alcantarillado": "La vivienda tiene alcantarillado (P8520S3; vivienda)",
    "recoleccion_basuras": "La vivienda tiene recolección de basuras (P8520S4; vivienda)",
    "gas_natural": "El hogar tiene gas natural conectado a red pública (P5666; servicios)",
    "internet_hogar": "El hogar tiene conexión a internet (P1075; condiciones)",
    "tenencia_vivienda": "La vivienda que ocupa el hogar es propia, en arriendo, etc. (P5095; tenencia)",
    "se_considera_pobre": "El jefe o el cónyuge se considera pobre (P5230; condiciones)",
}
# Variables armonizadas de cada nivel y su contenido. Las que dependen de un capítulo aparecen si se carga.
ETIQUETAS = {
    "persona": {**_COMUNES, "sexo": "Sexo al nacer (P6020)", "edad": "Años cumplidos (P6040)",
                "parentesco": "Parentesco con el jefe o la jefa del hogar (P6051)",
                "etnia": "Autorreconocimiento étnico (P6080)",
                "afiliado_salud": "Afiliado(a) al sistema de seguridad social en salud (P6090; salud). «No sabe» cuenta "
                                  "como no afiliado, como en el DANE",
                "regimen_salud": "Régimen de los afiliados: contributivo, especial o subsidiado (P6100; salud)",
                "asiste": "Actualmente estudia (P8586; educación, 5 años y más)",
                "anios_educacion": "Años de educación aprobados, de primero de primaria en adelante (educación, 5 años y "
                                   "más). Se cuentan como en el DANE; vea la guía",
                "usa_computador": "Usa computador de escritorio, portátil o tableta (P1910, P1911, P1912; tic, 5 años y "
                                  "más)",
                "usa_internet": "Usa internet en cualquier lugar (P1084; tic)",
                "usa_celular": "Tiene o usa teléfono celular (P1082, P5504; tic)",
                **_DEL_HOGAR},
    "hogar": {**_COMUNES, **_DEL_HOGAR},
}
NIVELES = tuple(ETIQUETAS)


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("ecv")


def _modulo_valido(modulo: str) -> str:
    if modulo not in (*MODULOS, *_INTERNOS):
        raise ValueError(f"Módulo desconocido {modulo!r}. Opciones: {list(MODULOS)}")
    return modulo


def find_files(years: Iterable[int] | int | None = None, modulo: str = "caracteristicas", root=None) -> dict[int, Path]:
    """
    Archivo de datos de un capítulo en cada año descargado.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    modulo
        Uno de ``dd.ecv.MODULOS``.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("ecv")``).

    Devuelve
    --------
    dict
        ``{año: ruta}``.

    Lanza
    -----
    ValueError
        Si ``modulo`` no es uno de ``dd.ecv.MODULOS``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.find_files(2025, modulo="salud")  # doctest: +SKIP
    {2025: PosixPath('/home/ana/dane_data_datos/ecv/datos/2025/salud/Salud.CSV')}
    """
    _modulo_valido(modulo)
    base = _root(root) / "datos"
    if not base.is_dir():
        return {}
    years = _enteros(years)  # también un año de numpy (df.anio.max())
    out = {}
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(carpeta.name)
        if (years is None or anio in years) and (archivos := archivos_datos(carpeta / modulo, EXTENSIONES)):
            out[anio] = max(archivos, key=lambda f: (f.suffix.lower() != ".dta", f.stat().st_size))
    return out


def available(root=None) -> pd.DataFrame:
    """
    Qué capítulos de cada año están descargados.

    Parámetros
    ----------
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("ecv")``).

    Devuelve
    --------
    pandas.DataFrame
        Una fila por año y capítulo: ``anio``, ``modulo``, ``archivo`` y ``tamano_mb``. En 2018 aparecen también los
        ``factores`` de expansión basados en el CNPV 2018, y en 2020 la base ``complementaria`` del IPM.

    Véase también
    -------------
    download : Descargar lo que falta.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.ecv.available().head(2)  # doctest: +SKIP
       anio    modulo                  archivo  tamano_mb
    0  2025  vivienda  Datos de la vivienda.CSV       10.2
    1  2025  servicios  Servicios del hogar.CSV       20.9
    """
    filas = [{"anio": anio, "modulo": modulo, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
             for modulo in (*MODULOS, *_INTERNOS) for anio, f in find_files(modulo=modulo, root=root).items()]
    tabla = pd.DataFrame(filas, columns=["anio", "modulo", "archivo", "tamano_mb"])
    return tabla.sort_values("anio", kind="stable").reset_index(drop=True)


def _modulos_validos(modulos, nivel: str) -> tuple[str, ...]:
    if nivel not in NIVELES:
        raise ValueError(f"Nivel desconocido {nivel!r}. Opciones: {list(NIVELES)}")
    if modulos is None:
        modulos = ()
    elif isinstance(modulos, str):
        modulos = (modulos,)
    for m in modulos:
        if m not in MODULOS:
            raise ValueError(f"Módulo desconocido {m!r}. Opciones: {list(MODULOS)}")
        if nivel == "hogar" and UNIDADES[m] == "persona":
            raise ValueError(f"{m!r} es un capítulo de personas: cárguelo con nivel=\"persona\".")
    # La base primero y la vivienda al final: su geografía se agrega aparte
    return tuple(dict.fromkeys([_BASE[nivel], *modulos]))


# Las variables de la base complementaria de 2020 (P1075 y P1077Sx también están en Condiciones de vida)
_COLUMNAS_COMPLEMENTARIA = ("ESTRATEGIAS", "EST_RADIO", "EST_TELEVISION", "EST_PLATAFORMAS", "EST_GUIAS", "EST_VISITA",
                            "EST_LLAMADA", "ESCUCHA_RADIO", "P1077S7", "P1077S8", "CELULAR_INTELIGENTE", "P5305", "CELULAR")


def _leer(ruta: Path, modulo: str, columns) -> pd.DataFrame:
    """Un capítulo con las llaves de ``load``: en las tablas de hogar, el número del hogar pasa a ``SECUENCIA_P``."""
    unidad = UNIDADES.get(modulo, "vivienda")
    llaves = {"vivienda": ["DIRECTORIO"], "hogar": ["DIRECTORIO", "SECUENCIA_ENCUESTA"], "persona": KEYS_PERSONA}[unidad]
    pedir = None if columns is None else [*llaves, "FEX_C", *columns]
    df = read_table(ruta, columns=pedir)
    if unidad == "hogar":
        df = df.drop(columns=["SECUENCIA_P", "ORDEN"], errors="ignore").rename(columns={"SECUENCIA_ENCUESTA": "SECUENCIA_P"})
    elif unidad == "vivienda":
        df = df.drop(columns=["SECUENCIA_P", "SECUENCIA_ENCUESTA", "ORDEN"], errors="ignore")
    return df


def _unir_capitulo(base: pd.DataFrame, otro: pd.DataFrame, llaves: list[str]) -> pd.DataFrame:
    """Agrega a ``base`` las columnas nuevas de ``otro`` (el factor y las llaves no se repiten)."""
    nuevas = [c for c in otro.columns if c not in base.columns and c != "FEX_C"]
    return base.merge(otro[llaves + nuevas], on=llaves, how="left", validate="many_to_one" if llaves != KEYS_PERSONA
                      else "one_to_one") if nuevas else base


def _factores_2018(df: pd.DataFrame, root) -> pd.DataFrame:
    """En 2018, el FEX_C del CNPV 2018 (por vivienda) en lugar del de los capítulos, que queda en FEX_C_ORIGINAL."""
    archivo = find_files(2018, modulo=_FACTORES, root=root).get(2018)
    if archivo is None:
        warnings.warn("ECV 2018: faltan los factores de expansión basados en el CNPV 2018, así que se usa el FEX_C de "
                      "los capítulos y los totales no son los de la serie oficial. Bájelos con dd.ecv.download(2018).",
                      UserWarning, stacklevel=3)
        return df
    factores = read_table(archivo, columns=["DIRECTORIO", "FEX_C"]).rename(columns={"FEX_C": "_FEX_CNPV"})
    df = df.rename(columns={"FEX_C": "FEX_C_ORIGINAL"}).merge(factores, on="DIRECTORIO", how="left", validate="many_to_one")
    return df.rename(columns={"_FEX_CNPV": "FEX_C"})


def _categorica(codigos: pd.Series, mapa: dict, nombre: str) -> pd.Series:
    return pd.to_numeric(codigos, errors="coerce").map(mapa).astype(CATEGORIAS[nombre])


def _num(df: pd.DataFrame, columna: str) -> pd.Series:
    return pd.to_numeric(df[columna], errors="coerce")


def _si(df: pd.DataFrame, columna: str, si=(1,)) -> pd.Series:
    """True si la respuesta es una de ``si``; vacía donde no hay respuesta."""
    valores = _num(df, columna)
    return valores.isin(si).astype("boolean").mask(valores.isna())


def anios_educacion(df: pd.DataFrame) -> pd.Series:
    """
    Años de educación aprobados, como los cuenta el DANE en la ECV (Cuadro 18 de la serie y el IPM).

    Se cuenta desde primero de primaria. Quien no estudia: el grado aprobado de primaria, secundaria o media (P8587S1;
    la media va de 10 a 13, con la normal) o, en la educación superior, 11 más los años aprobados en ella (P6211).
    Quien estudia: el grado anterior al que cursa (P1088S1) o, en la superior, 11 más los años aprobados (P6216).
    Ninguno y preescolar son 0. Vacía para quien no tiene el capítulo de educación (menores de 5 años).
    """
    estudia = _num(df, "P8586").eq(1)
    nivel, grado = _num(df, "P8587"), _num(df, "P8587S1")
    no_estudia = np.select([nivel.isin([1, 2]), nivel.between(3, 5), nivel >= 6],
                           [0, grado, 11 + _num(df, "P6211").fillna(0)], np.nan)
    matricula, cursa = _num(df, "P1088"), _num(df, "P1088S1")
    estudiante = np.select([matricula.eq(1), matricula.between(2, 4), matricula >= 5],
                           [0, cursa - 1, 11 + _num(df, "P6216").fillna(0)], np.nan)
    return pd.Series(np.where(estudia, estudiante, no_estudia), index=df.index, dtype="float64")


_EDUCACION = ("P8586", "P8587", "P8587S1", "P6211", "P1088", "P1088S1", "P6216")


def _por_capitulo(df: pd.DataFrame) -> dict[str, pd.Series]:
    """Las armonizadas de los capítulos distintos de Características, si están sus columnas."""
    nuevas = {}
    if "P6090" in df:
        nuevas["afiliado_salud"] = _si(df, "P6090")
        if "P6100" in df:
            nuevas["regimen_salud"] = _categorica(df["P6100"].where(_num(df, "P6090").eq(1)), _REGIMEN, "regimen_salud")
    if "P8586" in df:
        nuevas["asiste"] = _si(df, "P8586")
    if all(c in df for c in _EDUCACION):
        nuevas["anios_educacion"] = anios_educacion(df)
    if usos := [c for c in ("P1910", "P1911", "P1912") if c in df]:
        frecuencias = pd.concat([_num(df, c) for c in usos], axis=1)  # 1 a 4: con alguna frecuencia; 5: no lo usa
        nuevas["usa_computador"] = frecuencias.isin([1, 2, 3, 4]).any(axis=1).astype("boolean").mask(
            frecuencias.isna().all(axis=1))
    if "P1084" in df:
        nuevas["usa_internet"] = _si(df, "P1084", si=(1, 2, 3, 4))
    if "P1082" in df:
        celular = _si(df, "P1082")
        if "P5504" in df:  # no tiene celular, pero usa uno
            celular = celular | _num(df, "P5504").eq(1)
        nuevas["usa_celular"] = celular
    for nombre, columna in _SERVICIOS:
        if columna in df:
            nuevas[nombre] = _si(df, columna)
    if "P1075" in df:
        nuevas["internet_hogar"] = _si(df, "P1075")
    if "P5095" in df:
        nuevas["tenencia_vivienda"] = _categorica(df["P5095"], _TENENCIA, "tenencia_vivienda")
    if "P5230" in df:
        nuevas["se_considera_pobre"] = _si(df, "P5230")
    return nuevas


def harmonize(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega las variables armonizadas (en minúscula) a una tabla de la ECV con las variables originales del DANE.

    Las que se pueden calcular con las columnas que hay (``dd.ecv.ETIQUETAS``): ``fex``, ``area``, ``region`` y
    ``departamento`` con la geografía de la vivienda; ``sexo``, ``edad``, ``parentesco`` y ``etnia`` con Características;
    y las de los demás capítulos si están sus columnas, como ``afiliado_salud`` (Salud) o ``anios_educacion``
    (Educación). ``load`` la llama sola; sirve para una tabla leída por fuera de ``load``.

    Parámetros
    ----------
    df
        Tabla con las variables originales en MAYÚSCULA (``CLASE``, ``REGION``, ``P1_DEPARTAMENTO`` o ``DPTO``,
        ``FEX_C``, ``P6020``, ``P6040``, ...).

    Devuelve
    --------
    pandas.DataFrame
        Una copia con las variables armonizadas al final. Las categóricas tienen las categorías de
        ``dd.ecv.CATEGORIAS``.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> crudo = pd.DataFrame({"CLASE": [1, 2], "P1_DEPARTAMENTO": [11, 11], "FEX_C": [10.5, 3.0], "P6020": [2, 1]})
    >>> dd.ecv.harmonize(crudo)[["area", "region", "departamento", "sexo"]]
                                    area       region departamento    sexo
    0                           Cabecera  Bogotá D.C.  Bogotá D.C.   Mujer
    1  Centros poblados y rural disperso     Oriental  Bogotá D.C.  Hombre
    """
    nuevas = {}
    if "FEX_C" in df:
        nuevas["fex"] = pd.to_numeric(df["FEX_C"], errors="coerce")
    if "CLASE" in df:
        nuevas["area"] = _categorica(df["CLASE"], _AREAS, "area")
    dpto = next((pd.to_numeric(df[c], errors="coerce") for c in ("P1_DEPARTAMENTO", "DPTO") if c in df), None)
    if "REGION" in df:
        nuevas["region"] = _categorica(df["REGION"], _REGIONES, "region")
    elif dpto is not None:
        codigo = dpto.map(_REGION_DPTO)
        if "CLASE" in df:  # la parte rural de Bogotá es de la región Oriental
            codigo = codigo.mask(dpto.eq(11) & pd.to_numeric(df["CLASE"], errors="coerce").eq(2), 2)
        nuevas["region"] = _categorica(codigo, _REGIONES, "region")
    if dpto is not None:
        nuevas["departamento"] = dpto.map(DEPARTAMENTOS).astype(CATEGORIAS["departamento"])
    if "P6020" in df:
        nuevas["sexo"] = _categorica(df["P6020"], _SEXO, "sexo")
    if "P6040" in df:
        nuevas["edad"] = pd.to_numeric(df["P6040"], errors="coerce").astype("Int16")
    if "P6051" in df:
        nuevas["parentesco"] = _categorica(df["P6051"], _PARENTESCO, "parentesco")
    if "P6080" in df:
        nuevas["etnia"] = _categorica(df["P6080"], _ETNIA, "etnia")
    nuevas.update(_por_capitulo(df))
    return pd.concat([df, pd.DataFrame(nuevas, index=df.index)], axis=1)


def load(
    years: Iterable[int] | int | None = None,
    modulos: Iterable[str] | str | None = None,
    nivel: str = "persona",
    columns: Iterable[str] | None = None,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Carga la ECV descargada: una fila por persona (o por hogar), con los capítulos pedidos unidos por sus llaves.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos los descargados.
    modulos
        Capítulos de ``dd.ecv.MODULOS`` que se agregan. Siempre va el que trae a todas las personas
        (``caracteristicas``) o a todos los hogares (``servicios``), y la geografía de la vivienda.
    nivel
        ``"persona"`` o ``"hogar"``. Con ``"hogar"`` solo se pueden pedir capítulos de hogar (``servicios``,
        ``tenencia``, ``condiciones``) y la ``vivienda``.
    columns
        Variables originales que se leen de cada capítulo, además de las llaves y de las que necesitan las
        armonizadas. ``None`` para todas.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("ecv")``).
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    pandas.DataFrame
        Las llaves ``DIRECTORIO``, ``SECUENCIA_P`` (el hogar) y, con personas, ``SECUENCIA_ENCUESTA``; las variables
        originales en MAYÚSCULA y las armonizadas en minúscula (``dd.ecv.ETIQUETAS[nivel]``).

    Lanza
    -----
    ValueError
        Si un capítulo o el nivel no existen, o si se pide un capítulo de personas con ``nivel="hogar"``.
    FileNotFoundError
        Si no hay ningún año descargado del capítulo base.

    Notas
    -----
    Un capítulo que falta en un año descargado deja sus columnas vacías en ese año y avisa. Los capítulos de personas
    no son de todas las personas (Educación es de 5 años y más, Fuerza de trabajo de 12 y más, etc.): las demás quedan
    con sus columnas vacías.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> df = dd.ecv.load(2025, modulos=["salud", "educacion"])  # doctest: +SKIP
    >>> hogares = dd.ecv.load(2025, modulos="tenencia", nivel="hogar")  # doctest: +SKIP
    """
    modulos = _modulos_validos(modulos, nivel)
    columns = None if columns is None else [*dict.fromkeys([*columns, *_ARMONIZAR])]
    bases = find_files(years, modulo=modulos[0], root=root)
    if not bases:
        raise FileNotFoundError(f"No hay {modulos[0]} de la ECV para años={years} en {_root(root)}. "
                                "Descárguela con dane_data.ecv.download(...) o revise dane_data.set_paths(...).")
    faltan: dict[str, list[int]] = {}
    partes = []
    for i, (anio, ruta) in enumerate(sorted(bases.items())):
        if progress:
            progress(i / len(bases), f"Leyendo la ECV {anio}")
        df = _leer(ruta, modulos[0], columns)
        llaves = KEYS_PERSONA if nivel == "persona" else KEYS_HOGAR
        for modulo in [m for m in modulos[1:] if m != "vivienda"]:
            if (otro := find_files(anio, modulo=modulo, root=root).get(anio)) is None:
                faltan.setdefault(modulo, []).append(anio)
                continue
            df = _unir_capitulo(df, _leer(otro, modulo, columns), llaves if UNIDADES[modulo] == nivel else KEYS_HOGAR)
        vivienda = find_files(anio, modulo="vivienda", root=root).get(anio)
        if vivienda is None:
            faltan.setdefault("vivienda", []).append(anio)
        else:
            cols_viv = None if "vivienda" in modulos and columns is None else [*_GEOGRAFIA, *(columns or [])]
            df = _unir_capitulo(df, _leer(vivienda, "vivienda", cols_viv), ["DIRECTORIO"])
        if anio == 2018:
            df = _factores_2018(df, root)
        if anio == 2020 and nivel == "persona" and (columns is None and "educacion" in modulos
                                                     or columns is not None and set(columns) & set(_COLUMNAS_COMPLEMENTARIA)):
            if (complementaria := find_files(2020, modulo=_COMPLEMENTARIA, root=root).get(2020)) is None:
                faltan.setdefault(_COMPLEMENTARIA, []).append(2020)
            else:
                pedidas = None if columns is None else ["DIRECTORIO", "SECUENCIA_P", "ORDEN", *columns]
                extra = read_table(complementaria, columns=pedidas).rename(columns={"ORDEN": "SECUENCIA_ENCUESTA"})
                df = _unir_capitulo(df, extra, KEYS_PERSONA)
        # concat y no assign: tras unir varios capítulos, insertar una columna fragmenta la tabla
        partes.append(harmonize(pd.concat([df, pd.Series(np.int16(anio), index=df.index, name="anio")], axis=1)))
    if faltan:
        warnings.warn("ECV: faltan capítulos descargados, que quedan vacíos: "
                      + "; ".join(f"{m} en {', '.join(map(str, a))}" for m, a in faltan.items())
                      + ". Bájelos con dd.ecv.download(años, modulos=[...]).", UserWarning, stacklevel=2)
    if progress:
        progress(1.0, "Listo")
    return _unir(partes)
