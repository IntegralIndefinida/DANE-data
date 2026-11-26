"""Tablas de referencia: salario mínimo, departamentos, meses y diccionarios DANE."""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from importlib import resources

# Salario mínimo legal mensual vigente (SMLMV), pesos corrientes.
# Fuente: decretos anuales del Gobierno Nacional. Verificar antes de publicar.
SMLV = {
    1992: 65_190,
    1993: 81_510,
    1994: 98_700,
    1995: 118_934,
    1996: 142_125,
    1997: 172_005,
    1998: 203_826,
    1999: 236_460,
    2000: 260_100,
    2001: 286_000,
    2002: 309_000,
    2003: 332_000,
    2004: 358_000,
    2005: 381_500,
    2006: 408_000,
    2007: 433_700,
    2008: 461_500,
    2009: 496_900,
    2010: 515_000,
    2011: 535_600,
    2012: 566_700,
    2013: 589_500,
    2014: 616_000,
    2015: 644_350,
    2016: 689_455,
    2017: 737_717,
    2018: 781_242,
    2019: 828_116,
    2020: 877_803,
    2021: 908_526,
    2022: 1_000_000,
    2023: 1_160_000,
    2024: 1_300_000,
    2025: 1_423_500,
    2026: 1_750_905,
}

DEPARTAMENTOS = {
    5: "Antioquia",
    8: "Atlántico",
    11: "Bogotá D.C.",
    13: "Bolívar",
    15: "Boyacá",
    17: "Caldas",
    18: "Caquetá",
    19: "Cauca",
    20: "Cesar",
    23: "Córdoba",
    25: "Cundinamarca",
    27: "Chocó",
    41: "Huila",
    44: "La Guajira",
    47: "Magdalena",
    50: "Meta",
    52: "Nariño",
    54: "Norte de Santander",
    63: "Quindío",
    66: "Risaralda",
    68: "Santander",
    70: "Sucre",
    73: "Tolima",
    76: "Valle del Cauca",
    81: "Arauca",
    85: "Casanare",
    86: "Putumayo",
    88: "San Andrés",
    91: "Amazonas",
    94: "Guainía",
    95: "Guaviare",
    97: "Vaupés",
    99: "Vichada",
}

MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def strip_accents(text: str) -> str:
    text = text.replace("\xa0", " ").replace(" ", " ").replace("​", "")
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn"
    ).lower()


# Archivo de cada diccionario y año del DDI del que sale
_DICCIONARIOS = {
    "geih": ("geih_diccionario.json", 2025),
    "eam": ("eam_diccionario.json", 2024),
    "emicron": ("emicron_diccionario.json", 2024),
    **{
        f"eevv_{t}": (f"eevv_{t}_diccionario.json", 2025)
        for t in ("defunciones", "nacimientos", "fetales")
    },
    "ecv": ("ecv_diccionario.json", 2025),
}


@lru_cache(maxsize=None)
def diccionario(encuesta: str) -> dict:
    """
    Diccionario oficial de variables de una encuesta.

    Es el diccionario DDI del ANDA, tal como lo publica el DANE: el de la GEIH 2025, el de la EAM
    2024, el de la EMICRON 2024, el de las Estadísticas Vitales 2025 o el de la ECV 2025. Viene con
    la librería, así que no necesita descargar nada.

    Parámetros
    ----------
    encuesta
        ``"geih"``, ``"eam"``, ``"emicron"``, ``"eevv_defunciones"``, ``"eevv_nacimientos"``,
        ``"eevv_fetales"`` o ``"ecv"``.

    Devuelve
    --------
    dict
        ``{VARIABLE: {"etiqueta": ..., "pregunta": ..., "categorias": {código: etiqueta},
        "modulos": [...]}}``.

    Véase también
    -------------
    buscar_variable : Buscar variables por texto.
    describir : Etiqueta de una variable.

    Notas
    -----
    Los nombres y las categorías de algunas variables cambian entre épocas de la encuesta: úselo
    como guía para los años antiguos. Donde los datos contradicen el DDI, ``dane-data`` sigue los
    datos; vea la página «Diferencias con la documentación del DANE».

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> geih = dd.diccionario("geih")
    >>> len(geih)
    675
    >>> geih["P6920"]["categorias"]
    {'1': 'Sí', '2': 'No', '3': 'Ya es pensionado'}
    """
    name, _ = _DICCIONARIOS[encuesta.lower()]
    with resources.files("dane_data.data").joinpath(name).open(encoding="utf-8") as f:
        return json.load(f)


def describir(variable: str, encuesta: str = "geih") -> str:
    """
    Etiqueta legible de una variable.

    Parámetros
    ----------
    variable
        Nombre de la variable del DANE, en mayúscula o minúscula.
    encuesta
        ``"geih"``, ``"eam"``, ``"emicron"``, ``"eevv_defunciones"``, ``"eevv_nacimientos"``,
        ``"eevv_fetales"`` o ``"ecv"``.

    Devuelve
    --------
    str
        La etiqueta del diccionario oficial, o el mismo nombre si la variable no está en él (por
        ejemplo, las armonizadas de ``dane-data`` o variables de años antiguos).

    Véase también
    -------------
    diccionario : El diccionario completo.
    buscar_variable : Buscar variables por texto.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.describir("P6920")
    '¿está ... Cotizando actualmente a un fondo de pensiones?'
    >>> dd.describir("valagri", encuesta="eam")
    'Valor agregado'
    >>> dd.describir("SEXO", encuesta="eevv_nacimientos")
    'Sexo del nacido vivo'
    """
    info = diccionario(encuesta).get(variable.upper())
    return info["etiqueta"] if info and info["etiqueta"] else variable


def _armonizadas(encuesta: str) -> dict:
    """Las variables que crea ``dane-data`` en una encuesta, con su descripción."""
    from . import eam, ecv, eevv, emicron, geih

    if encuesta.startswith("eevv_"):
        return eevv.ETIQUETAS[encuesta.removeprefix("eevv_")]
    if encuesta == "ecv":
        return {var: texto for nivel in ecv.ETIQUETAS.values() for var, texto in nivel.items()}
    if (
        encuesta == "eam"
    ):  # la EAM usa los nombres del DANE en minúscula: las de CORE ya están en el DDI
        return {
            var: texto
            for var, texto in eam.ETIQUETAS.items()
            if var.upper() not in diccionario("eam")
        }
    return {"geih": geih.ETIQUETAS, "emicron": emicron.ETIQUETAS}[encuesta]


def buscar_variable(texto: str, encuesta: str = "geih"):
    """
    Busca variables por su nombre, etiqueta o pregunta.

    Busca en las variables armonizadas que crea ``dane-data`` (en minúscula, iguales en todos los
    años), que salen primero, y en el diccionario oficial (DDI) del DANE. La búsqueda no distingue
    mayúsculas ni tildes.

    Parámetros
    ----------
    texto
        Texto a buscar, por ejemplo ``"arriendo"`` o ``"P64"``.
    encuesta
        ``"geih"``, ``"eam"``, ``"emicron"``, ``"eevv_defunciones"``, ``"eevv_nacimientos"``,
        ``"eevv_fetales"`` o ``"ecv"``.

    Devuelve
    --------
    DataFrame
        Una fila por variable con ``variable``, ``origen`` (``"dane-data"`` en las armonizadas,
        ``"DANE"`` en las del DDI), ``ddi`` (el año del DDI de donde sale la variable, como texto,
        o ``"armonizada"``), ``etiqueta``, ``pregunta`` y ``modulo``. Las armonizadas no tienen
        pregunta ni módulo.

    Véase también
    -------------
    diccionario : El diccionario completo.
    dane_data.geih.load : Cargar variables del DANE extra con ``columnas=[...]``.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.buscar_variable("arriendo")["variable"].tolist()
    ['ingreso_no_laboral', 'P3064S1', 'P5090', 'P5130', 'P5140', 'P7495', 'P7500S1', 'P7500S1A1']
    >>> dd.buscar_variable("fex")[["variable", "origen", "ddi"]]
      variable     origen         ddi
    0      fex  dane-data  armonizada
    1  FEX_C18       DANE        2025
    """
    import pandas as pd

    encuesta = encuesta.lower()
    q = strip_accents(texto)
    rows = [
        {
            "variable": var,
            "origen": "dane-data",
            "ddi": "armonizada",
            "etiqueta": etiqueta,
            "pregunta": "",
            "modulo": "",
        }
        for var, etiqueta in _armonizadas(encuesta).items()
        if q in strip_accents(f"{var} {etiqueta}")
    ]
    _, ddi = _DICCIONARIOS[encuesta]
    for var, info in diccionario(encuesta).items():
        blob = strip_accents(f"{var} {info['etiqueta']} {info['pregunta']}")
        if q in blob:
            rows.append(
                {
                    "variable": var,
                    "origen": "DANE",
                    "ddi": str(ddi),
                    "etiqueta": info["etiqueta"],
                    "pregunta": info["pregunta"],
                    "modulo": ", ".join(info.get("modulos", []))[:80],
                }
            )
    return pd.DataFrame(
        rows, columns=["variable", "origen", "ddi", "etiqueta", "pregunta", "modulo"]
    )
