"""Tablas de referencia: salario mínimo, departamentos, meses y diccionarios DANE."""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from importlib import resources

# Salario mínimo legal mensual vigente (SMLMV), pesos corrientes.
# Fuente: decretos anuales del Gobierno Nacional. Verificar antes de publicar.
SMLV = {
    1992: 65_190, 1993: 81_510, 1994: 98_700, 1995: 118_934, 1996: 142_125,
    1997: 172_005, 1998: 203_826, 1999: 236_460, 2000: 260_100, 2001: 286_000,
    2002: 309_000, 2003: 332_000, 2004: 358_000, 2005: 381_500, 2006: 408_000,
    2007: 433_700, 2008: 461_500, 2009: 496_900, 2010: 515_000, 2011: 535_600,
    2012: 566_700, 2013: 589_500, 2014: 616_000, 2015: 644_350, 2016: 689_455,
    2017: 737_717, 2018: 781_242, 2019: 828_116, 2020: 877_803, 2021: 908_526,
    2022: 1_000_000, 2023: 1_160_000, 2024: 1_300_000, 2025: 1_423_500,
    2026: 1_750_905,
}

DEPARTAMENTOS = {
    5: "Antioquia", 8: "Atlántico", 11: "Bogotá D.C.", 13: "Bolívar", 15: "Boyacá",
    17: "Caldas", 18: "Caquetá", 19: "Cauca", 20: "Cesar", 23: "Córdoba",
    25: "Cundinamarca", 27: "Chocó", 41: "Huila", 44: "La Guajira", 47: "Magdalena",
    50: "Meta", 52: "Nariño", 54: "Norte de Santander", 63: "Quindío", 66: "Risaralda",
    68: "Santander", 70: "Sucre", 73: "Tolima", 76: "Valle del Cauca", 81: "Arauca",
    85: "Casanare", 86: "Putumayo", 88: "San Andrés", 91: "Amazonas", 94: "Guainía",
    95: "Guaviare", 97: "Vaupés", 99: "Vichada",
}

MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def strip_accents(text: str) -> str:
    text = text.replace("\xa0", " ").replace(" ", " ").replace("​", "")
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn").lower()


@lru_cache(maxsize=None)
def diccionario(encuesta: str) -> dict:
    """
    Diccionario oficial de variables (DDI de ANDA): GEIH 2025 o EAM 2024.

    Devuelve ``{VARIABLE: {"etiqueta", "pregunta", "categorias", "modulos"}}``.
    Los nombres cambian entre épocas; úselo como guía, no como verdad absoluta
    para años antiguos.
    """
    name = {"geih": "geih_diccionario.json", "eam": "eam_diccionario.json"}[encuesta.lower()]
    with resources.files("dane_data.data").joinpath(name).open(encoding="utf-8") as f:
        return json.load(f)


def describir(variable: str, encuesta: str = "geih") -> str:
    """Etiqueta legible de una variable, o el mismo nombre si no se conoce."""
    info = diccionario(encuesta).get(variable.upper())
    return info["etiqueta"] if info and info["etiqueta"] else variable


def buscar_variable(texto: str, encuesta: str = "geih"):
    """
    Busca variables cuyo nombre, etiqueta o pregunta contengan ``texto``.

    >>> dd.buscar_variable("pensión")
    """
    import pandas as pd

    q = strip_accents(texto)
    rows = []
    for var, info in diccionario(encuesta).items():
        blob = strip_accents(f"{var} {info['etiqueta']} {info['pregunta']}")
        if q in blob:
            rows.append({"variable": var, "etiqueta": info["etiqueta"], "pregunta": info["pregunta"],
                         "modulo": ", ".join(info.get("modulos", []))[:80]})
    return pd.DataFrame(rows, columns=["variable", "etiqueta", "pregunta", "modulo"])
