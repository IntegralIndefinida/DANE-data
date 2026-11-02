"""
Carga y armonización de las Estadísticas Vitales: un certificado por fila.

Hay tres tipos de certificado (``TIPOS``): defunciones no fetales desde 1979, nacidos vivos y defunciones fetales
desde 1998. No es una encuesta sino un registro: no hay factor de expansión y los agregados son conteos.

Los códigos cambian con los años, y varias veces contradicen el DDI (ver la tabla de diferencias del README):

* ``GRU_ED1``: 25 grupos en 1979–1997, 26 en 1998–2007 y 30 desde 2008. ``grupo_edad`` los lleva a los grupos que se
  pueden comparar en toda la serie.
* Área, sitio, estado civil, régimen de salud y educación tienen varias codificaciones, por época.
* La causa básica (``C_BAS1``) está en CIE-9 hasta 1996 y en CIE-10 desde 1997.
* La manera de muerte está en ``PMAN_MUER`` y ``MAN_MUER`` hasta 2018 y en ``P_PMAN_IRIS`` desde 2019.

Convención, como en la GEIH: en minúscula las variables armonizadas, en MAYÚSCULA las originales del DANE.
"""

from __future__ import annotations

import json
import logging
import numbers
import warnings
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from .._hooks import archivos_datos
from .._io import read_table
from ..referencias import DEPARTAMENTOS

log = logging.getLogger("dane_data.eevv")

# Los tres certificados: defunciones no fetales (desde 1979), nacidos vivos y defunciones fetales (desde 1998)
TIPOS = ("defunciones", "nacimientos", "fetales")

# En orden de preferencia, leídos con _io.read_table
EXTENSIONES = (".csv", ".txt", ".dta")

_COMUNES = ["ANO", "MES", "COD_DPTO", "COD_MUNIC", "CODPTORE", "CODMUNRE", "AREA_RES", "SEXO", "SEG_SOCIAL"]
_CAUSAS = ["C_BAS1", "CAU_HOMOL", "CAUSA_666", "CAUSA_667"]
# Variables del DANE que necesita la armonización, por tipo de certificado
CORE = {
    "defunciones": _COMUNES + _CAUSAS + ["A_DEFUN", "SIT_DEFUN", "GRU_ED1", "EST_CIVIL", "NIVEL_EDU", "IDPERTET",
                                         "PMAN_MUER", "MAN_MUER", "P_PMAN_IRIS"],
    "nacimientos": _COMUNES + ["AREANAC", "SIT_PARTO", "PESO_NAC", "T_GES", "T_GES_AGRU_CIE", "NUMCONSUL", "TIPO_PARTO",
                               "MUL_PARTO", "ATEN_PAR", "EDAD_MADRE", "EST_CIVM", "NIV_EDUM", "N_HIJOSV", "N_EMB",
                               "EDAD_PADRE", "IDPERTET"],
    "fetales": _COMUNES + _CAUSAS + ["A_DEFUN", "SIT_DEFUN", "PESO_NAC", "T_GES", "T_GES_AGRU_CIE", "EDAD_MADRE",
                                     "EST_CIVM", "NIV_EDUM", "REGSOCIALMADRE"],
}

_COMUNES_ETIQUETAS = {
    "anio": "Año de ocurrencia (ANO)",
    "mes": "Mes de ocurrencia (MES)",
    "sexo": "Hombre, Mujer o Indeterminado (SEXO)",
    "dpto_ocurrencia": "Código del departamento donde ocurrió (COD_DPTO)",
    "departamento_ocurrencia": "Nombre del departamento donde ocurrió",
    "mpio_ocurrencia": "Código del municipio donde ocurrió, 5 dígitos (COD_DPTO y COD_MUNIC)",
    "area_ocurrencia": "Área donde ocurrió (A_DEFUN o AREANAC)",
    "dpto_residencia": "Código del departamento de residencia (CODPTORE); de la madre en nacimientos y fetales",
    "departamento_residencia": "Nombre del departamento de residencia; vacío si no se sabe o vive en el extranjero",
    "mpio_residencia": "Código del municipio de residencia, 5 dígitos (CODPTORE y CODMUNRE)",
    "area_residencia": "Área de residencia (AREA_RES), desde 1992",
    "regimen_salud": "Régimen de seguridad social en salud (SEG_SOCIAL o REGSOCIALMADRE), desde 1998",
}
_CAUSA_ETIQUETAS = {
    "causa_cie": "Causa básica (C_BAS1), como texto",
    "cie_rev": "Revisión de la CIE de causa_cie: 9 hasta 1996, 10 desde 1997",
    "causa_105": "Código de la lista Colombia 105 (CAU_HOMOL), toda la serie",
    "causa_105_nombre": "Nombre de la causa en la lista 105",
    "causa_667": "Código de la lista 6/67 de la OPS (CAUSA_667), solo en 2008–2011 y 2014–2025",
    "causa_667_nombre": "Nombre de la causa en la lista 6/67",
    "gran_causa": "Gran grupo de la lista de la OPS, desde 1998",
}
_MADRE_ETIQUETAS = {
    "edad_madre": "Grupo de edad de la madre (EDAD_MADRE)",
    "madre_adolescente": "True si la madre tiene menos de 20 años; vacío sin edad",
    "peso_grupo": "Grupo de peso al nacer, en gramos (PESO_NAC)",
    "bajo_peso": "True si pesó menos de 2.500 gramos; vacío sin peso",
    "gestacion_grupo": "Semanas de gestación, agrupadas (T_GES)",
    "prematuro": "True si duró menos de 37 semanas (T_GES_AGRU_CIE); vacío en 2012, 2013, 2020 y antes de 2008",
    "nivel_educativo_madre": "Nivel educativo de la madre (NIV_EDUM)",
    "estado_civil_madre": "Estado civil de la madre (EST_CIVM)",
}
# Qué es cada variable armonizada, por tipo de certificado
ETIQUETAS = {
    "defunciones": {
        **_COMUNES_ETIQUETAS, **_CAUSA_ETIQUETAS,
        "grupo_edad": "Grupo de edad, comparable en toda la serie (GRU_ED1)",
        "grupo_edad_amplio": "Grupo de edad amplio: menor de 1, 1–4, 5–14, 15–44, 45–64 y 65 o más",
        "menor_un_anio": "True si tenía menos de un año; vacío sin edad y en el primer semestre de 1991",
        "neonatal": "True si murió en los primeros 27 días completos de vida; vacío sin edad, en el primer semestre de "
                    "1991 y antes de 1998 (GRU_ED1 junta de 7 a 29 días)",
        "neonatal_precoz": "True si murió en los primeros 6 días completos de vida; vacío sin edad y en el primer "
                           "semestre de 1991",
        "sitio": "Sitio de la defunción (SIT_DEFUN)",
        "estado_civil": "Estado civil (EST_CIVIL)",
        "nivel_educativo": "Nivel educativo (NIVEL_EDU), desde 1998",
        "etnia": "Pertenencia étnica (IDPERTET), desde 2008",
        "manera_muerte": "Manera de muerte (PMAN_MUER y MAN_MUER, o P_PMAN_IRIS desde 2019), desde 1997",
        "materna": "True si es una muerte materna según el DANE: causa básica del capítulo O de la CIE-10 salvo O96 (tardía) "
                   "y O97 (secuelas), es decir, hasta 42 días después del embarazo; vacío antes de 1997",
        "materna_tardia": "True si la causa básica es O96, muerte materna tardía (de 43 días a un año después del embarazo); "
                          "vacío antes de 1997",
    },
    "nacimientos": {
        **_COMUNES_ETIQUETAS, **_MADRE_ETIQUETAS,
        "sitio_parto": "Sitio del parto (SIT_PARTO)",
        "atencion_parto": "Quién atendió el parto (ATEN_PAR)",
        "tipo_parto": "Tipo de parto (TIPO_PARTO)",
        "cesarea": "True si fue por cesárea; vacío sin información",
        "parto_multiple": "True si fue de dos o más; vacío sin información",
        "consultas": "Número de consultas prenatales (NUMCONSUL)",
        "hijos_nacidos_vivos": "Hijos nacidos vivos de la madre, incluido este (N_HIJOSV)",
        "embarazos": "Embarazos de la madre (N_EMB)",
        "edad_padre": "Edad del padre (EDAD_PADRE)",
        "etnia": "Pertenencia étnica (IDPERTET), desde 2008 salvo 2012 y 2013",
    },
    "fetales": {
        **_COMUNES_ETIQUETAS, **_CAUSA_ETIQUETAS, **_MADRE_ETIQUETAS,
        "sitio": "Sitio de la defunción (SIT_DEFUN)",
        "mortinato": "True si tenía 22 semanas o más de gestación o pesaba 1.000 gramos o más; vacío sin gestación y con "
                     "menos de 1.000 gramos (el DANE cuenta desde 500, pero los microdatos agrupan el peso)",
    },
}

_SIN = "Sin información"
_SEXO = {1: "Hombre", 2: "Mujer", 3: "Indeterminado"}

_CABECERA, _CENTRO, _RURAL, _RESTO = "Cabecera", "Centro poblado", "Rural disperso", "Resto"
_AREA_ANTES_1998 = {1: _CABECERA, 2: _RESTO, 3: _SIN}
_AREA = {1: _CABECERA, 2: _CENTRO, 3: _RURAL, 9: _SIN}

_SITIO_ANTES_1998 = {1: "Hospital o clínica", 2: "Casa", 3: "Otro", 4: _SIN}
_SITIO = {1: "Hospital o clínica", 2: "Centro o puesto de salud", 3: "Casa", 4: "Lugar de trabajo", 5: "Vía pública",
          6: "Otro", 9: _SIN}

_SOLTERO, _CASADO, _VIUDO, _LIBRE, _SEPARADO = "Soltero(a)", "Casado(a)", "Viudo(a)", "Unión libre", "Separado(a) o divorciado(a)"
_LIBRE_U_OTRO = "Unión libre, divorciado(a) u otro"
_CIVIL_1979 = {1: _SOLTERO, 2: _CASADO, 3: _VIUDO, 4: _LIBRE_U_OTRO, 5: _SIN}
_CIVIL_1998 = {1: _SOLTERO, 2: _CASADO, 3: _VIUDO, 4: _LIBRE, 5: _SEPARADO, 9: _SIN}
_CIVIL_2008 = {1: _LIBRE, 2: _LIBRE, 3: _SEPARADO, 4: _VIUDO, 5: _SOLTERO, 6: _CASADO, 9: _SIN}

_NINGUNO, _PREESCOLAR, _PRIMARIA, _SECUNDARIA, _SUPERIOR = "Ninguno", "Preescolar", "Primaria", "Secundaria y media", "Superior"
_EDUCACION_1998 = {1: _PREESCOLAR, 2: _PRIMARIA, 3: _PRIMARIA, 4: _SECUNDARIA, 5: _SECUNDARIA, 6: _SUPERIOR,
                   7: _SUPERIOR, 8: _NINGUNO, 9: _SIN}
_EDUCACION_2008 = {1: _PREESCOLAR, 2: _PRIMARIA, 3: _SECUNDARIA, 4: _SECUNDARIA, 5: _SECUNDARIA, 6: _SECUNDARIA,
                   7: _SUPERIOR, 8: _SUPERIOR, 9: _SUPERIOR, 10: _SUPERIOR, 11: _SUPERIOR, 12: _SUPERIOR, 13: _NINGUNO,
                   99: _SIN}

_CONTRIBUTIVO, _SUBSIDIADO, _VINCULADO = "Contributivo", "Subsidiado", "Vinculado"
_REGIMEN_1998 = {1: _CONTRIBUTIVO, 2: _SUBSIDIADO, 3: _VINCULADO, 4: _SIN, 9: _SIN}
_REGIMEN_2001 = {1: _CONTRIBUTIVO, 2: _SUBSIDIADO, 3: _VINCULADO, 4: "Particular", 5: "Otro", 6: _SIN, 9: _SIN}
_REGIMEN_2008 = {1: _CONTRIBUTIVO, 2: _SUBSIDIADO, 3: "Excepción", 4: "Especial", 5: "No asegurado", 9: _SIN}

_ETNIA = {1: "Indígena", 2: "Rom", 3: "Raizal", 4: "Palenquero", 5: "Negro, mulato o afrodescendiente", 6: "Ninguna",
          9: _SIN}

_MENOR_1, _1_A_4 = "Menor de 1 año", "De 1 a 4 años"
_85 = "De 85 años y más"
_DESCONOCIDA = "Edad desconocida"
_SIN_DETALLE = "Menor de 10 años, sin detalle"
_QUINQUENIOS = [f"De {i} a {i + 4} años" for i in range(5, 85, 5)]
GRUPOS_EDAD = [_MENOR_1, _1_A_4, *_QUINQUENIOS, _85, _DESCONOCIDA, _SIN_DETALLE]
GRUPOS_EDAD_AMPLIOS = [_MENOR_1, _1_A_4, "De 5 a 14 años", "De 15 a 44 años", "De 45 a 64 años", "De 65 años y más",
                       _DESCONOCIDA, _SIN_DETALLE]
# Código de GRU_ED1 -> grupo comparable. El código de «De 5 a 9 años» depende de cuántos grupos hay antes.
_EDAD_1979 = {**dict.fromkeys(range(1, 6), _MENOR_1), 6: _1_A_4, 7: _1_A_4,
              **{8 + i: g for i, g in enumerate(_QUINQUENIOS)}, 24: _85, 25: _DESCONOCIDA}
_EDAD_1998 = {**dict.fromkeys(range(1, 7), _MENOR_1), 7: _1_A_4, 8: _1_A_4,
              **{9 + i: g for i, g in enumerate(_QUINQUENIOS)}, 25: _85, 26: _DESCONOCIDA}
_EDAD_2008 = {**dict.fromkeys(range(0, 7), _MENOR_1), 7: _1_A_4, 8: _1_A_4,
              **{9 + i: g for i, g in enumerate(_QUINQUENIOS)}, **dict.fromkeys(range(25, 29), _85), 29: _DESCONOCIDA}

_MANERAS = ["Natural", "Homicidio", "Suicidio", "Accidente", "Violenta sin detalle", "En estudio", "Otra", "Sin determinar"]
_IRIS = {0: "Natural", 1: "Homicidio", 2: "Accidente", 3: "En estudio", 4: "Suicidio", 5: "Sin determinar",
         6: "Sin determinar", 8: "Otra", 9: "Otra"}
_MAN_MUER = {1: "Suicidio", 2: "Homicidio", 3: "Accidente", 4: "Accidente", 5: "En estudio", 9: "Sin determinar"}

_PESOS = ["Menos de 1.000", "1.000 a 1.499", "1.500 a 1.999", "2.000 a 2.499", "2.500 a 2.999", "3.000 a 3.499",
          "3.500 a 3.999", "4.000 y más", _SIN]
_PESO = {i + 1: p for i, p in enumerate(_PESOS[:8])} | {9: _SIN}

_GESTACIONES = ["Menos de 22", "De 22 a 27", "De 28 a 37", "De 38 a 41", "De 42 y más", "De 28 y más", "Ignorado", _SIN]
_GESTACION = {1: "Menos de 22", 2: "De 22 a 27", 3: "De 28 a 37", 4: "De 38 a 41", 5: "De 42 y más", 6: "Ignorado", 9: _SIN}
# Fetales 1998–2007: el certificado solo separaba hasta 28 semanas
_GESTACION_FETAL_ANTIGUA = {1: "Menos de 22", 2: "De 22 a 27", 3: "De 28 y más", 4: "Ignorado", 9: _SIN}
_GESTACION_22_O_MAS = ["De 22 a 27", "De 28 a 37", "De 38 a 41", "De 42 y más", "De 28 y más"]

# Códigos de GRU_ED1 de 0 a 6 días y de 0 a 27 días, por época. En 1979–1997 el 3 es «de 7 a 29 días»: no se puede
# separar el período neonatal (0 a 27 días), así que queda vacío.
_NEONATAL = {1979: ({1, 2}, None), 1998: ({1, 2}, {1, 2, 3}), 2008: ({0, 1, 2}, {0, 1, 2, 3})}

_EDADES_MADRE = [f"De {i} a {i + 4} años" for i in range(10, 55, 5)] + [_SIN]
_EDAD_MADRE = {i + 1: e for i, e in enumerate(_EDADES_MADRE[:9])} | {99: _SIN}

_TIPO_PARTO = {1: "Espontáneo", 2: "Cesárea", 3: "Instrumentado", 4: "Ignorado", 9: _SIN}
_SITIO_PARTO = {1: "Institución de salud", 2: "Domicilio", 3: "Otro", 9: _SIN}
_ATENCION = {1: "Médico", 2: "Enfermero(a)", 3: "Auxiliar de enfermería", 4: "Promotor(a) de salud", 5: "Partera",
             6: "Otra persona", 9: _SIN}

# Primer dígito de las listas de la OPS. El 7 de la 6/66 (hasta 2018) es el 0 de la 6/67: «mal definidas».
GRANDES_CAUSAS = {0: "Signos y síntomas mal definidos", 1: "Enfermedades transmisibles", 2: "Neoplasias",
                  3: "Enfermedades del sistema circulatorio", 4: "Afecciones del período perinatal",
                  5: "Causas externas", 6: "Las demás causas", 7: "Signos y síntomas mal definidos"}


def _categoria(valores, ordenada: bool = False) -> pd.CategoricalDtype:
    return pd.CategoricalDtype(list(dict.fromkeys(valores)), ordered=ordenada)


# Tipos fijos: así se conservan al unir años con pd.concat
CATEGORIAS = {
    "sexo": _categoria(_SEXO.values()),
    "area_ocurrencia": _categoria([_CABECERA, _CENTRO, _RURAL, _RESTO, _SIN]),
    "area_residencia": _categoria([_CABECERA, _CENTRO, _RURAL, _RESTO, _SIN]),
    "regimen_salud": _categoria([_CONTRIBUTIVO, _SUBSIDIADO, _VINCULADO, "Particular", "Otro", "Excepción", "Especial",
                                 "No asegurado", _SIN]),
    "sitio": _categoria([*_SITIO.values(), *_SITIO_ANTES_1998.values()]),
    "estado_civil": _categoria([_SOLTERO, _CASADO, _LIBRE, _SEPARADO, _VIUDO, _LIBRE_U_OTRO, _SIN]),
    "estado_civil_madre": _categoria([_SOLTERO, _CASADO, _LIBRE, _SEPARADO, _VIUDO, _SIN]),
    "nivel_educativo": _categoria([_NINGUNO, _PREESCOLAR, _PRIMARIA, _SECUNDARIA, _SUPERIOR, _SIN], ordenada=True),
    "nivel_educativo_madre": _categoria([_NINGUNO, _PREESCOLAR, _PRIMARIA, _SECUNDARIA, _SUPERIOR, _SIN], ordenada=True),
    "etnia": _categoria(_ETNIA.values()),
    "grupo_edad": _categoria(GRUPOS_EDAD, ordenada=True),
    "grupo_edad_amplio": _categoria(GRUPOS_EDAD_AMPLIOS, ordenada=True),
    "manera_muerte": _categoria(_MANERAS),
    "gran_causa": _categoria(GRANDES_CAUSAS.values()),
    "peso_grupo": _categoria(_PESOS, ordenada=True),
    "gestacion_grupo": _categoria(_GESTACIONES, ordenada=True),
    "edad_madre": _categoria(_EDADES_MADRE, ordenada=True),
    "tipo_parto": _categoria(_TIPO_PARTO.values()),
    "sitio_parto": _categoria(_SITIO_PARTO.values()),
    "atencion_parto": _categoria(_ATENCION.values()),
    "departamento_ocurrencia": _categoria(DEPARTAMENTOS.values()),
    "departamento_residencia": _categoria(DEPARTAMENTOS.values()),
}

_CODIGO_ANTIGUO_CAQUETA = 83  # 1979–1981; desde 1982 los archivos usan 18, el código actual
_CAQUETA = 18


@lru_cache(maxsize=1)
def causas() -> dict[str, dict[str, str]]:
    """Nombres de las causas: ``{"667": {código: nombre}, "105": {código: nombre}}``, de los cuadros del DANE."""
    with resources.files("dane_data.data").joinpath("eevv_causas.json").open(encoding="utf-8") as f:
        return json.load(f)


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("eevv")


def _tipo_valido(tipo: str) -> str:
    if tipo not in TIPOS:
        raise ValueError(f"Tipo desconocido {tipo!r}. Opciones: {list(TIPOS)}")
    return tipo


def find_files(years: Iterable[int] | int | None = None, tipo: str = "defunciones", root=None) -> dict[int, Path]:
    """
    Archivo de datos de cada año descargado de un tipo de certificado.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    tipo
        ``"defunciones"``, ``"nacimientos"`` o ``"fetales"``.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("eevv")``).

    Devuelve
    --------
    dict
        ``{año: ruta}``.

    Lanza
    -----
    ValueError
        Si ``tipo`` no es uno de los tres.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eevv.find_files(2025, tipo="nacimientos")  # doctest: +SKIP
    {2025: PosixPath('/home/ana/dane_data_datos/eevv/datos/nacimientos/2025/BD-EEVV-Nacimientos-2025.csv')}
    """
    base = _root(root) / "datos" / _tipo_valido(tipo)
    if not base.is_dir():
        return {}
    if years is not None:
        # numbers.Integral: también un año de numpy (df.anio.max())
        years = {int(y) for y in ([years] if isinstance(years, (numbers.Integral, str)) else years)}
    out = {}
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(carpeta.name)
        if (years is None or anio in years) and (archivos := archivos_datos(carpeta, EXTENSIONES)):
            out[anio] = max(archivos, key=lambda f: (f.suffix.lower() != ".dta", f.stat().st_size))
    return out


def available(root=None) -> pd.DataFrame:
    """
    Tabla de los años descargados de las Estadísticas Vitales.

    Parámetros
    ----------
    root
        Carpeta raíz. Por defecto, la configurada.

    Devuelve
    --------
    DataFrame
        Una fila por tipo y año con ``tipo``, ``anio``, ``archivo`` y ``tamano_mb``.

    Véase también
    -------------
    download : Descargar lo que falta.
    load : Cargar lo descargado.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eevv.available().tail(2)  # doctest: +SKIP
            tipo  anio                              archivo  tamano_mb
    101  fetales  2024  BD-EEVV-Defuncionesfetales-2024.csv        4.1
    102  fetales  2025  BD-EEVV-Defuncionesfetales-2025.csv        3.8
    """
    filas = [{"tipo": tipo, "anio": anio, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
             for tipo in TIPOS for anio, f in find_files(tipo=tipo, root=root).items()]
    return pd.DataFrame(filas, columns=["tipo", "anio", "archivo", "tamano_mb"])


# --------------------------------------------------------------------------- #
# Armonización
# --------------------------------------------------------------------------- #
def _numero(df: pd.DataFrame, columna: str) -> pd.Series:
    """La columna como número; vacía si el archivo no la trae. Lo que no es número queda vacío (ver ``N_HIJOSM``)."""
    if columna not in df.columns:
        return pd.Series(np.nan, index=df.index, dtype="float64")
    return pd.to_numeric(df[columna], errors="coerce")


def _etiquetar(df: pd.DataFrame, columna: str, mapa: dict, nombre: str) -> pd.Series:
    return _numero(df, columna).map(mapa).astype(CATEGORIAS[nombre])


def _booleana(valores: pd.Series, si, no) -> pd.Series:
    """True en ``si``, False en ``no`` y vacía en lo demás."""
    return valores.map(dict.fromkeys(si, True) | dict.fromkeys(no, False)).astype("boolean")


def _conteo(df: pd.DataFrame, columna: str, sin_dato=(99,)) -> pd.Series:
    """Un número entero pequeño, sin los códigos de «sin información»."""
    return _numero(df, columna).where(lambda v: ~v.isin(sin_dato)).astype("Float32")


def _lugar(df: pd.DataFrame, col_dpto: str, col_mpio: str) -> tuple[pd.Series, pd.Series, pd.Series]:
    """``(código de departamento, nombre, municipio de 5 dígitos)``."""
    # El DDI no trae el 83, pero 1979–1981 tienen miles de registros con él y ninguno en 18, y desde 1982 al revés:
    # es Caquetá con su código antiguo (ver README).
    dpto = _numero(df, col_dpto).replace(_CODIGO_ANTIGUO_CAQUETA, _CAQUETA)
    # 1 es «sin información» y 75 «residente en el extranjero», según el DDI: no son departamentos
    valido = dpto.isin(list(DEPARTAMENTOS))
    nombre = dpto.where(valido).map(DEPARTAMENTOS).astype(CATEGORIAS["departamento_ocurrencia"])
    municipio = _numero(df, col_mpio)
    codigo = (dpto * 1000 + municipio).where(valido & municipio.notna())
    texto = codigo.astype("Int64").astype("string").str.zfill(5).astype("category")
    return dpto.astype("Int8"), nombre, texto


def _grupo_edad(df: pd.DataFrame, anio: int) -> pd.Series:
    codigos = _numero(df, "GRU_ED1")
    mapa = _EDAD_1979 if anio <= 1997 else _EDAD_1998 if anio <= 2007 else _EDAD_2008
    grupos = codigos.map(mapa)
    if anio == 1991:
        # Enero–junio de 1991 no sigue el DDI: casi no hay códigos del 1 al 5, y las muertes de menores de 10 años
        # (también las perinatales) están en el 6, 7 y 8. No se pueden separar (ver README).
        grupos = grupos.mask(_numero(df, "MES").le(6) & codigos.le(8), _SIN_DETALLE)
    return grupos.astype(CATEGORIAS["grupo_edad"])


def _grupo_amplio(grupo: pd.Series) -> pd.Series:
    mapa = {_MENOR_1: _MENOR_1, _1_A_4: _1_A_4, _85: "De 65 años y más", _DESCONOCIDA: _DESCONOCIDA,
            _SIN_DETALLE: _SIN_DETALLE}
    for g, amplio in zip(_QUINQUENIOS, ["De 5 a 14 años"] * 2 + ["De 15 a 44 años"] * 6 + ["De 45 a 64 años"] * 4
                         + ["De 65 años y más"] * 4):
        mapa[g] = amplio
    return grupo.astype("object").map(mapa).astype(CATEGORIAS["grupo_edad_amplio"])


def _manera_muerte(df: pd.DataFrame, anio: int) -> pd.Series:
    if anio >= 2019:
        return _numero(df, "P_PMAN_IRIS").map(_IRIS).astype(CATEGORIAS["manera_muerte"])
    if anio < 1997:
        return pd.Series(pd.NA, index=df.index, dtype=CATEGORIAS["manera_muerte"])
    probable = _numero(df, "PMAN_MUER")
    # 1997 solo tiene natural o violenta; desde 1998, MAN_MUER dice de qué tipo fue la violenta
    violenta = _numero(df, "MAN_MUER").map(_MAN_MUER).fillna("Sin determinar") if anio >= 1998 else "Violenta sin detalle"
    resultado = pd.Series(pd.NA, index=df.index, dtype="object")
    resultado = resultado.mask(probable.eq(1), "Natural").mask(probable.eq(3), "En estudio")
    resultado = resultado.where(~probable.eq(2), violenta)
    return resultado.astype(CATEGORIAS["manera_muerte"])


def _causas_armonizadas(df: pd.DataFrame, anio: int) -> dict[str, pd.Series]:
    # read_table pasa a número las columnas sin letras: los códigos CIE-9 perderían sus ceros a la izquierda
    texto = df["C_BAS1"].astype("string").str.strip().str.upper() if "C_BAS1" in df.columns \
        else pd.Series(pd.NA, index=df.index, dtype="string")
    if anio <= 1996:
        texto = texto.str.replace(r"\.0$", "", regex=True).str.zfill(4)
    nombres = causas()
    lista105 = _numero(df, "CAU_HOMOL").astype("Int64").astype("string").str.zfill(3)
    # CAUSA_666 no es la misma lista que CAUSA_667: el 407 de una es el 406 de la otra. Solo el primer dígito empata.
    lista667 = _numero(df, "CAUSA_667")
    primer_digito = (lista667 if "CAUSA_667" in df.columns else _numero(df, "CAUSA_666")) // 100
    codigo667 = lista667.astype("Int64").astype("string").str.zfill(3)
    return {
        "causa_cie": texto.astype("category"),
        "cie_rev": pd.Series(9 if anio <= 1996 else 10, index=df.index, dtype="int8"),
        "causa_105": lista105.astype("category"),
        "causa_105_nombre": lista105.map(nombres["105"]).astype("category"),
        "causa_667": codigo667.astype("category"),
        "causa_667_nombre": codigo667.map(nombres["667"]).astype("category"),
        "gran_causa": primer_digito.map(GRANDES_CAUSAS).astype(CATEGORIAS["gran_causa"]),
    }


def _maternas(causa: pd.Series, anio: int) -> dict[str, pd.Series]:
    """
    ``materna`` y ``materna_tardia``, como en la ficha técnica de la razón de mortalidad materna del DANE (2026).

    Los cuadros de defunciones maternas del DANE (7 y 8) cuentan todo el capítulo O, pero la razón solo las de hasta 42
    días: sin O96 (tardía, de 43 días a un año) ni O97 (secuelas, después de un año). La CIE-9 (hasta 1996) no se usa.
    """
    if anio < 1997:
        return {c: pd.Series(pd.NA, index=causa.index, dtype="boolean") for c in ("materna", "materna_tardia")}
    texto = causa.astype("string")
    categoria = texto.str[:3]
    return {"materna": (texto.str.startswith("O") & ~categoria.isin(["O96", "O97"])).astype("boolean"),
            "materna_tardia": categoria.eq("O96").astype("boolean")}


def _neonatales(df: pd.DataFrame, anio: int, grupo: pd.Series) -> dict[str, pd.Series]:
    """``neonatal`` (0 a 27 días) y ``neonatal_precoz`` (0 a 6 días), como en las fichas técnicas de la mortalidad
    neonatal y perinatal del DANE (2026). Vacías sin edad o en el primer semestre de 1991 (sin detalle)."""
    codigos = _numero(df, "GRU_ED1")
    sin_dato = grupo.isna() | grupo.isin([_DESCONOCIDA, _SIN_DETALLE])
    precoz, neonatal = _NEONATAL[1979 if anio <= 1997 else 1998 if anio <= 2007 else 2008]

    def marcar(incluidos) -> pd.Series:
        if incluidos is None:
            return pd.Series(pd.NA, index=df.index, dtype="boolean")
        return codigos.isin(incluidos).astype("boolean").mask(sin_dato)

    return {"neonatal": marcar(neonatal), "neonatal_precoz": marcar(precoz)}


def _mortinato(gestacion: pd.Series, peso: pd.Series) -> pd.Series:
    """
    Mortinato según la ficha técnica de la mortalidad perinatal del DANE (2026): 22 semanas o más **o** 500 gramos o más.

    Los microdatos agrupan el peso desde «menos de 1.000 gramos», así que solo se puede confirmar con 1.000 gramos o más.
    Sin gestación y con menos de 1.000 gramos queda vacío: el DANE, con el peso exacto, sabe si pesaba 500 o más. Con
    menos de 22 semanas y de 1.000 gramos se toma como aborto, aunque el DANE contaría como mortinato el que pesara de
    500 a 999 gramos (ver README). Sin gestación ni peso no cumple ningún criterio, y no es mortinato.
    """
    gestacion, peso = gestacion.astype("object"), peso.astype("object")
    si = gestacion.isin(_GESTACION_22_O_MAS) | peso.isin(_PESOS[1:8])
    dudoso = ~si & ~gestacion.isin(["Menos de 22"]) & peso.eq("Menos de 1.000")
    return si.astype("boolean").mask(dudoso)


def _madre(df: pd.DataFrame, anio: int, tipo: str) -> dict[str, pd.Series]:
    gestacion = _GESTACION_FETAL_ANTIGUA if tipo == "fetales" and anio <= 2007 else _GESTACION
    peso, edad = _numero(df, "PESO_NAC"), _numero(df, "EDAD_MADRE")
    educacion = _EDUCACION_1998 if anio <= 2007 else _EDUCACION_2008
    if tipo == "fetales" and anio == 2009:
        # Fetales 2009 no sigue el DDI: casi sin 99 ni 13 y 7 005 registros con 9. No se sabe qué es cada código.
        educacion = {}
    return {
        "edad_madre": edad.map(_EDAD_MADRE).astype(CATEGORIAS["edad_madre"]),
        "madre_adolescente": _booleana(edad, si=(1, 2), no=range(3, 10)),
        "peso_grupo": peso.map(_PESO).astype(CATEGORIAS["peso_grupo"]),
        "bajo_peso": _booleana(peso, si=range(1, 5), no=range(5, 9)),
        "gestacion_grupo": _etiquetar(df, "T_GES", gestacion, "gestacion_grupo"),
        # T_GES no sirve: agrupa «de 28 a 37» semanas, y la semana 37 ya es a término. Sí sirve T_GES_AGRU_CIE.
        "prematuro": _booleana(_numero(df, "T_GES_AGRU_CIE"), si=(1, 2, 3), no=(4, 5)),
        "nivel_educativo_madre": _etiquetar(df, "NIV_EDUM", educacion, "nivel_educativo_madre"),
        "estado_civil_madre": _etiquetar(df, "EST_CIVM", _CIVIL_1998 if anio <= 2007 else _CIVIL_2008,
                                         "estado_civil_madre"),
    }


def harmonize(df: pd.DataFrame, tipo: str, anio: int) -> pd.DataFrame:
    """
    Agrega las variables armonizadas a los datos de un año y un tipo de certificado.

    Parámetros
    ----------
    df
        Datos de un año, con los nombres en mayúscula.
    tipo
        ``"defunciones"``, ``"nacimientos"`` o ``"fetales"``.
    anio
        Año de los datos.

    Devuelve
    --------
    DataFrame
        Una copia de ``df`` con las variables de ``ETIQUETAS[tipo]``.

    Lanza
    -----
    ValueError
        Si ``tipo`` no es uno de los tres.

    Véase también
    -------------
    load : Carga y armoniza.

    Ejemplos
    --------
    >>> import pandas as pd
    >>> import dane_data as dd
    >>> crudo = pd.DataFrame({"ANO": [2025], "MES": [3], "SEXO": [2], "GRU_ED1": [8], "COD_DPTO": [5], "COD_MUNIC": [1],
    ...                       "C_BAS1": ["O149"], "P_PMAN_IRIS": [0]})
    >>> d = dd.eevv.harmonize(crudo, "defunciones", 2025)
    >>> d[["sexo", "grupo_edad", "mpio_ocurrencia", "manera_muerte"]].iloc[0].tolist()
    ['Mujer', 'De 1 a 4 años', '05001', 'Natural']
    >>> bool(d["materna"].iloc[0])
    True
    """
    _tipo_valido(tipo)
    antiguo = anio <= 1997
    area = _AREA_ANTES_1998 if antiguo else _AREA
    regimen = _REGIMEN_1998 if anio <= 2000 else _REGIMEN_2001 if anio <= 2007 else _REGIMEN_2008
    dpto_o, nombre_o, mpio_o = _lugar(df, "COD_DPTO", "COD_MUNIC")
    dpto_r, nombre_r, mpio_r = _lugar(df, "CODPTORE", "CODMUNRE")
    area_ocurrencia = "AREANAC" if tipo == "nacimientos" else "A_DEFUN"
    nuevas: dict[str, pd.Series] = {
        "anio": pd.Series(anio, index=df.index, dtype="int16"),
        "mes": _numero(df, "MES").astype("Int8"),
        "sexo": _etiquetar(df, "SEXO", _SEXO, "sexo"),
        "dpto_ocurrencia": dpto_o, "departamento_ocurrencia": nombre_o, "mpio_ocurrencia": mpio_o,
        "area_ocurrencia": _etiquetar(df, area_ocurrencia, area, "area_ocurrencia"),
        "dpto_residencia": dpto_r, "departamento_residencia": nombre_r, "mpio_residencia": mpio_r,
        "area_residencia": _etiquetar(df, "AREA_RES", area, "area_residencia"),
        # En fetales, desde 2024 se llama REGSOCIALMADRE, con los mismos códigos
        "regimen_salud": _etiquetar(df, "SEG_SOCIAL" if "SEG_SOCIAL" in df.columns else "REGSOCIALMADRE", regimen,
                                    "regimen_salud"),
    }
    if tipo == "defunciones":
        grupo = _grupo_edad(df, anio)
        civil = _CIVIL_1979 if antiguo else _CIVIL_1998 if anio <= 2007 else _CIVIL_2008
        hechas = _causas_armonizadas(df, anio)
        nuevas |= hechas | {
            "grupo_edad": grupo,
            "grupo_edad_amplio": _grupo_amplio(grupo),
            "menor_un_anio": grupo.astype("object").map(
                {g: g == _MENOR_1 for g in GRUPOS_EDAD if g not in (_DESCONOCIDA, _SIN_DETALLE)}).astype("boolean"),
            "sitio": _etiquetar(df, "SIT_DEFUN", _SITIO_ANTES_1998 if antiguo else _SITIO, "sitio"),
            "estado_civil": _etiquetar(df, "EST_CIVIL", civil, "estado_civil"),
            "nivel_educativo": _etiquetar(df, "NIVEL_EDU", _EDUCACION_1998 if anio <= 2007 else _EDUCACION_2008,
                                          "nivel_educativo"),
            "etnia": _etiquetar(df, "IDPERTET", _ETNIA, "etnia"),
            "manera_muerte": _manera_muerte(df, anio),
            **_maternas(hechas["causa_cie"], anio),
            **_neonatales(df, anio, grupo),
        }
    elif tipo == "nacimientos":
        parto = _numero(df, "TIPO_PARTO")
        nuevas |= _madre(df, anio, tipo) | {
            "sitio_parto": _etiquetar(df, "SIT_PARTO", _SITIO_PARTO, "sitio_parto"),
            "atencion_parto": _etiquetar(df, "ATEN_PAR", _ATENCION, "atencion_parto"),
            "tipo_parto": parto.map(_TIPO_PARTO).astype(CATEGORIAS["tipo_parto"]),
            "cesarea": _booleana(parto, si=(2,), no=(1, 3)),
            # El DDI dice que en 2008–2011 y 2014–2019 «sin información» es 5; en los datos siempre es 9 (ver README)
            "parto_multiple": _booleana(_numero(df, "MUL_PARTO"), si=(2, 3, 4), no=(1,)),
            "consultas": _conteo(df, "NUMCONSUL"),
            "hijos_nacidos_vivos": _conteo(df, "N_HIJOSV"),
            "embarazos": _conteo(df, "N_EMB"),
            "edad_padre": _conteo(df, "EDAD_PADRE", sin_dato=(99, 999)),
            "etnia": _etiquetar(df, "IDPERTET", _ETNIA, "etnia"),
        }
    else:
        madre = _madre(df, anio, tipo)
        nuevas |= _causas_armonizadas(df, anio) | madre | {
            "sitio": _etiquetar(df, "SIT_DEFUN", _SITIO, "sitio"),
            "mortinato": _mortinato(madre["gestacion_grupo"], madre["peso_grupo"]),
        }
    return pd.concat([df, pd.DataFrame(nuevas)], axis=1)


def _unir(partes: list[pd.DataFrame]) -> pd.DataFrame:
    """Une años. Las categorías que cambian de un año a otro (municipios, causas) se igualan antes: si no, quedarían como texto."""
    columnas = {c for p in partes for c in p.columns if isinstance(p[c].dtype, pd.CategoricalDtype)}
    for c in columnas:
        tipos = {p[c].dtype for p in partes if c in p.columns}
        if len(tipos) > 1:
            comun = pd.CategoricalDtype(sorted({v for t in tipos for v in t.categories}))
            partes = [p.assign(**{c: p[c].astype(comun)}) if c in p.columns else p for p in partes]
    return pd.concat(partes, ignore_index=True, sort=False)


def _avisar_cobertura(tipo: str, anios: Iterable[int]) -> None:
    if tipo != "defunciones":
        return
    avisos = []
    anios = set(anios)
    if anios & {1979, 1980}:
        avisos.append("los archivos de 1979 y 1980 están incompletos (en 1979 faltan Caldas, Norte de Santander, Quindío, "
                      "Risaralda, Santander y Arauca; en 1980, Caldas, Quindío y Risaralda traen cerca de la mitad): esos "
                      "totales nacionales no son comparables")
    if 1991 in anios:
        avisos.append("en enero–junio de 1991 no se pueden separar las edades de menores de 10 años, así que "
                      "'menor_un_anio' queda vacía en esas filas")
    if avisos:
        warnings.warn("Defunciones: " + "; ".join(avisos) + ". Vea la tabla de diferencias del README.", UserWarning,
                      stacklevel=3)


def load(
    years: Iterable[int] | int | None = None,
    tipo: str = "defunciones",
    columns="core",
    harmonize_vars: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Carga las Estadísticas Vitales: un certificado por fila, con las variables armonizadas.

    Parámetros
    ----------
    years
        Año, lista o rango de años. ``None`` para todos los descargados.
    tipo
        ``"defunciones"`` (1979–2025), ``"nacimientos"`` o ``"fetales"`` (ambos 1998–2025).
    columns
        ``"core"`` (solo las variables armonizadas; por defecto), ``"all"`` (también todas las del DANE) o una lista
        de variables del DANE para agregar, por ejemplo ``["GRU_ED1", "HORA"]``.
    harmonize_vars
        Agregar las variables armonizadas. Si False, solo las del DANE y ``anio``.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Una fila por certificado, con las variables de ``ETIQUETAS[tipo]``. En minúscula las armonizadas y en
        mayúscula las del DANE.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.
    ValueError
        Si ``tipo`` no es uno de los tres.

    Avisos
    ------
    UserWarning
        Si los años incluyen 1979, 1980 o 1991, cuyos archivos de defunciones tienen problemas.

    Véase también
    -------------
    indicadores : Conteos y porcentajes por grupo.
    serie_indicadores : Lo mismo, año por año y sin tener todo en memoria.
    tasas : Tasas de natalidad y mortalidad.
    ETIQUETAS : Qué es cada variable armonizada.

    Notas
    -----
    Es un registro: no hay factor de expansión, y el total de filas es el total de certificados. Un año completo de
    nacimientos pasa de 700 000 filas: para series largas use :func:`serie_indicadores`.

    Se cuenta el año en que ocurrió el hecho. Los registros tardíos de años anteriores no están aquí: el DANE los publica
    aparte.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> nac = dd.eevv.load(2025, tipo="nacimientos")  # doctest: +SKIP
    >>> len(nac)  # doctest: +SKIP
    441537
    >>> round(float(nac["cesarea"].mean()), 4)  # doctest: +SKIP
    0.5384
    """
    archivos = find_files(years, tipo=_tipo_valido(tipo), root=root)
    if not archivos:
        raise FileNotFoundError(
            f"No hay datos de {tipo} para años={years} en {_root(root)}. "
            "Descárguelos con dane_data.eevv.download(...) o revise dane_data.set_paths(...)."
        )
    _avisar_cobertura(tipo, archivos)
    if isinstance(columns, str) and columns not in ("core", "all"):
        columns = [columns]  # un solo nombre: list("HORA") lo partiría en letras
    extras = [] if isinstance(columns, str) else [c.upper() for c in columns]
    if columns == "all":
        selector = None
    else:
        leer = set(CORE[tipo]) | set(extras)
        selector = lambda c: c in leer  # noqa: E731

    partes = []
    for i, (anio, ruta) in enumerate(sorted(archivos.items())):
        if progress:
            progress(i / len(archivos), f"Leyendo {tipo} {anio}")
        crudo = read_table(ruta, columns=selector)
        if harmonize_vars:
            d = harmonize(crudo, tipo, anio)
            if columns != "all":  # Lo crudo ocupa más que lo armonizado; en toda la serie, varios GB
                d = d.drop(columns=[c for c in crudo.columns if c not in extras])
        else:
            d = crudo.assign(anio=anio)
        partes.append(d)
    if progress:
        progress(1.0, "Listo")
    return _unir(partes)
