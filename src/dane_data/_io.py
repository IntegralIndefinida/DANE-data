"""Lectura robusta de los archivos planos del DANE.

Los archivos cambian de separador (``;``, ``,``, tabulador), de codificación
(UTF-8 con BOM, Latin-1) y de separador decimal (coma en la GEIH anterior a
2020) entre años. ``read_table`` detecta todo eso automáticamente.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

_DECIMAL_COMMA = re.compile(r"^-?\d+,\d+$")


def sniff(path: Path) -> tuple[str, str]:
    """Detecta (separador, codificación) leyendo el encabezado."""
    raw = Path(path).open("rb").read(64_000)
    try:
        text = raw.decode("utf-8-sig")
        encoding = "utf-8-sig"
    except UnicodeDecodeError:
        # Puede ser un corte a mitad de carácter multibyte: reintentar sin el final
        try:
            text = raw[:-3].decode("utf-8-sig")
            encoding = "utf-8-sig"
        except UnicodeDecodeError:
            text = raw.decode("latin-1")
            encoding = "latin-1"
    header = text.splitlines()[0] if text else ""
    sep = max((";", ",", "\t", "|"), key=header.count)
    return sep, encoding


def _coerce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convierte a número las columnas de texto que en realidad son numéricas:
    celdas en blanco escritas como ``" "`` y coma decimal (``"71,22"``).
    """
    for col in df.columns:
        s = df[col]
        if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
            continue
        s = s.astype("string").str.strip().replace("", pd.NA)
        nonnull = s.notna().sum()
        if nonnull == 0:
            df[col] = np.nan
            continue
        sample = s.dropna().head(200)
        if sample.str.match(_DECIMAL_COMMA).mean() > 0.5:
            s = s.str.replace(",", ".", regex=False)
        converted = pd.to_numeric(s, errors="coerce").astype("float64")
        # Solo si no se pierden datos (texto genuino se deja como está)
        if converted.notna().sum() >= nonnull * 0.99:
            if converted.notna().all() and (converted % 1 == 0).all():
                converted = converted.astype("int64")
            df[col] = converted
    return df


def normalize_columns(cols: Iterable[str], case: str = "upper") -> list[str]:
    out = []
    for c in cols:
        c = str(c).replace("﻿", "").strip()
        out.append(c.upper() if case == "upper" else c.lower())
    return out


def read_table(
    path: Path,
    columns: Iterable[str] | Callable[[str], bool] | None = None,
    case: str = "upper",
) -> pd.DataFrame:
    """
    Lee un CSV/TXT del DANE detectando separador, codificación y coma decimal.

    ``columns`` puede ser una lista de nombres (en cualquier mayúscula/minúscula)
    o una función ``nombre_normalizado -> bool``. Los nombres de columna del
    resultado quedan normalizados (``case='upper'`` o ``'lower'``).
    """
    path = Path(path)
    sep, encoding = sniff(path)

    usecols = None
    if columns is not None:
        if callable(columns):
            pred = columns
        else:
            wanted = {normalize_columns([c], case)[0] for c in columns}
            pred = lambda c: c in wanted  # noqa: E731
        usecols = lambda c: pred(normalize_columns([c], case)[0])  # noqa: E731

    kwargs = dict(sep=sep, usecols=usecols, low_memory=False)
    try:
        df = pd.read_csv(path, encoding=encoding, **kwargs)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", **kwargs)
    df.columns = normalize_columns(df.columns, case)
    df = df.loc[:, ~df.columns.duplicated()]
    return _coerce_numeric(df)
