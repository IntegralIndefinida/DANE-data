"""Archivos de las Estadísticas Vitales en disco."""

from __future__ import annotations

import numbers
from pathlib import Path
from typing import Iterable

import pandas as pd

from .. import config

# Los tres certificados: defunciones no fetales (desde 1979), nacidos vivos y defunciones fetales (desde 1998)
TIPOS = ("defunciones", "nacimientos", "fetales")

# En orden de preferencia, leídos con _io.read_table
EXTENSIONES = (".csv", ".txt", ".dta")


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("eevv")


def _archivos_datos(carpeta: Path) -> list[Path]:
    """Archivos de datos ya extraídos en ``carpeta``."""
    if not carpeta.is_dir():
        return []
    return sorted(f for f in carpeta.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONES)


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
        if (years is None or anio in years) and (archivos := _archivos_datos(carpeta)):
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

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eevv.available().tail(2)  # doctest: +SKIP
             tipo  anio                         archivo  tamano_mb
    101   fetales  2024  BD-EEVV-Defuncionesfetales-2024.csv        4.1
    102   fetales  2025  BD-EEVV-Defuncionesfetales-2025.csv        3.8
    """
    filas = [{"tipo": tipo, "anio": anio, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
             for tipo in TIPOS for anio, f in find_files(tipo=tipo, root=root).items()]
    return pd.DataFrame(filas, columns=["tipo", "anio", "archivo", "tamano_mb"])
