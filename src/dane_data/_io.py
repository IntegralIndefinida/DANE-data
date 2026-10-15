"""Lectura robusta de los archivos planos del DANE.

Los archivos cambian de separador (``;``, ``,``, tabulador), de codificación
(UTF-8 con BOM, Latin-1) y de separador decimal (coma en la GEIH anterior a
2020 y en algunas celdas de la EAM) entre años. ``read_table`` detecta todo eso
automáticamente.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd


def sniff(path: Path) -> tuple[str, str]:
    """Detecta (separador, codificación) leyendo el encabezado."""
    # Siempre cerrado: en Windows un archivo abierto no se puede reemplazar al volver a descargar.
    with open(path, "rb") as fh:
        raw = fh.read(64_000)
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
        # Basta con que aparezca una coma, no la mayoría: en la EAM (1998, 1999, 2002,
        # 2006) casi todo es entero y solo las plantas anonimizadas por promedio traen
        # coma decimal ("83779570,6666667"); decidir con una muestra las volvía NaN.
        # Si la columna es texto genuino, la conversión de abajo falla y no se toca.
        if s.str.contains(",", regex=False).any():
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


# Códigos de tipo del formato 110 (b, i, l, f, d) en el formato 111; las cadenas strN son 127 + N.
_TIPOS_STATA_110 = {98: 251, 105: 252, 108: 253, 102: 254, 100: 255}
_NUMPY_STATA = {251: "i1", 252: "i2", 253: "i4", 254: "f4", 255: "f8"}
# Entero del formato 110 -> (rango válido para pandas 2, faltante del formato 110, tipo más ancho,
# faltante del tipo ancho que pandas 2 y 3 reconocen).
_ENSANCHAR_STATA = {
    251: ((-127, 100), 127, 252, 32767),
    252: ((-32767, 32740), 32767, 253, 2147483647),
    253: ((-2147483647, 2147483620), 2147483647, 255, 2.0**1023),
}


def _stata(path: Path) -> Path | io.BytesIO:
    """
    Archivo Stata legible por cualquier pandas >= 2.

    El Stata de septiembre de 2021 viene en formato 110 (Stata 7), que pandas solo lee desde
    la versión 3 (Colab trae pandas 2). Se traduce en memoria al formato 111 (Stata 7SE), que
    tiene el mismo encabezado salvo por los códigos de tipo. Además, pandas 2 toma como
    faltantes los valores reservados desde Stata 8 (un byte mayor que 100, como una edad de
    101 años), que en estos formatos son datos. Las columnas enteras que tienen esos valores
    se pasan a un tipo más ancho.
    """
    with open(path, "rb") as fh:
        if fh.read(1) != bytes([110]):
            return path
        datos = bytes([110]) + fh.read()
    orden = ">" if datos[1] == 1 else "<"
    entero = lambda b: int.from_bytes(b, "big" if orden == ">" else "little")  # noqa: E731
    nvar, nobs = entero(datos[4:6]), entero(datos[6:10])
    inicio = 4 + 2 + 4 + 81 + 18  # versión…, nvar, nobs, etiqueta de los datos, fecha
    tipos = [_TIPOS_STATA_110.get(t, t - 127) for t in datos[inicio:inicio + nvar]]
    # Nombres (33), orden (2 por variable + 2), formatos (12), etiquetas de valor (33) y de variable (81)
    pos = inicio + nvar + 2 * (nvar + 1) + nvar * (33 + 12 + 33 + 81)
    while datos[pos]:  # campos de expansión: tipo (1 byte) y largo (4) hasta un tipo 0
        pos += 5 + entero(datos[pos + 1:pos + 5])
    pos += 5
    dtype = lambda ts: np.dtype([(f"v{i}", orden + _NUMPY_STATA.get(t, f"S{t}")) for i, t in enumerate(ts)])  # noqa: E731
    filas = np.frombuffer(datos, dtype(tipos), count=nobs, offset=pos)
    fin = pos + filas.nbytes

    nuevos = list(tipos)
    for i, t in enumerate(tipos):
        if t in _ENSANCHAR_STATA:
            (minimo, maximo), faltante, ancho, _ = _ENSANCHAR_STATA[t]
            x = filas[f"v{i}"]
            if ((x < minimo) | ((x > maximo) & (x != faltante))).any():
                nuevos[i] = ancho
    if nuevos != tipos:
        anchas = np.empty(nobs, dtype(nuevos))
        for i, t in enumerate(tipos):
            anchas[f"v{i}"] = filas[f"v{i}"]
            if nuevos[i] != t:
                faltante, faltante_ancho = _ENSANCHAR_STATA[t][1], _ENSANCHAR_STATA[t][3]
                anchas[f"v{i}"][filas[f"v{i}"] == faltante] = faltante_ancho
        filas = anchas
    encabezado = bytes([111]) + datos[1:inicio] + bytes(nuevos) + datos[inicio + nvar:pos]
    return io.BytesIO(encabezado + filas.tobytes() + datos[fin:])


def columnas(path: Path, case: str = "upper") -> list[str]:
    """Nombres de columna normalizados de un archivo del DANE (texto o Stata), sin leer los datos."""
    path = Path(path)
    if path.suffix.lower() == ".dta":
        with pd.read_stata(_stata(path), iterator=True) as reader:
            return normalize_columns(reader.variable_labels(), case)
    sep, enc = sniff(path)
    with open(path, encoding=enc, errors="replace") as fh:
        return normalize_columns(fh.readline().rstrip("\r\n").split(sep), case)


def read_table(
    path: Path,
    columns: Iterable[str] | Callable[[str], bool] | None = None,
    case: str = "upper",
) -> pd.DataFrame:
    """
    Lee un CSV/TXT del DANE detectando separador, codificación y coma decimal.
    También lee Stata (``.dta``), el formato que se usa cuando el CSV del ANDA está dañado.

    ``columns`` puede ser una lista de nombres (en cualquier mayúscula/minúscula)
    o una función ``nombre_normalizado -> bool``. Los nombres de columna del
    resultado quedan normalizados (``case='upper'`` o ``'lower'``).
    """
    path = Path(path)
    usecols = None
    if columns is not None:
        if callable(columns):
            pred = columns
        else:
            wanted = {normalize_columns([c], case)[0] for c in columns}
            pred = lambda c: c in wanted  # noqa: E731
        usecols = lambda c: pred(normalize_columns([c], case)[0])  # noqa: E731

    if path.suffix.lower() == ".dta":
        with pd.read_stata(_stata(path), iterator=True) as reader:
            nombres = list(reader.variable_labels())
        elegidas = [c for c in nombres if usecols is None or usecols(c)]
        if not elegidas:
            return pd.DataFrame()
        df = pd.read_stata(_stata(path), columns=elegidas, convert_categoricals=False)
        df.columns = normalize_columns(df.columns, case)
        return _coerce_numeric(df.loc[:, ~df.columns.duplicated()])

    sep, encoding = sniff(path)
    kwargs = dict(sep=sep, usecols=usecols, low_memory=False)
    try:
        df = pd.read_csv(path, encoding=encoding, **kwargs)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1", **kwargs)
    df.columns = normalize_columns(df.columns, case)
    df = df.loc[:, ~df.columns.duplicated()]
    return _coerce_numeric(df)
