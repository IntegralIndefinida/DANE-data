"""
Carga y armonización de microdatos GEIH ya descargados.

La GEIH cambia de estructura según la época:

* 2007–2021: cada módulo viene partido por dominio (``Area``, ``Cabecera``,
  ``Resto``). ``Area`` (13/23 ciudades) es un subconjunto de ``Cabecera``, así
  que el total nacional es ``Cabecera + Resto``. Desocupados e inactivos
  vienen en módulos separados. Factor de expansión ``FEX_C_2011`` (coma decimal).
* 2020 y serie de empalme: un archivo por módulo, factor ``FEX_C``.
* 2022 en adelante (Marco 2018): módulo único "No ocupados" (desocupados +
  fuera de la fuerza de trabajo), factor ``FEX_C18``, sexo en ``P3271``.

``load`` oculta todo eso y entrega una persona por fila con variables
armonizadas en minúscula (``anio``, ``mes``, ``fex``, ``sexo``, ``edad``,
``condicion``, ``formal``, ``ingreso_laboral``, ...). Las variables originales
del DANE se conservan en MAYÚSCULA.
"""

from __future__ import annotations

import hashlib
import logging
import numbers
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from .._io import columnas, normalize_columns, read_table, sniff
from ..referencias import DEPARTAMENTOS, MESES, SMLV, strip_accents

log = logging.getLogger("dane_data.geih")

KEYS_PERSONA = ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
KEYS_HOGAR = ["DIRECTORIO", "SECUENCIA_P"]

# Variables originales que se leen siempre (si existen) para poder armonizar.
CORE_RAW = [
    *KEYS_PERSONA, "HOGAR", "MES", "PERIODO", "DPTO", "AREA", "CLASE",
    "FEX_C18", "FEX_C", "FEX_C_2011",
    "P6020", "P3271", "P6040", "P6050",
    "OCI", "DSI", "INI", "FFT", "FT", "PET", "PETI",
    "INGLABO", "P6090", "P6920", "P6430", "P6800",
    "RAMA2D", "RAMA2D_R4", "P6210", "P3042",
    # Informalidad del DANE (cuestionario del marco 2018, desde 2022): ver _formal_dane
    # y la medición anterior (marco 2005, hasta 2021): ver _formal_marco2005
    "P6870", "OFICIO",
    "OFICIO_C8", "P3045S1", "P3046", "P3069", "P6765", "P3065", "P3066", "P3067", "P3067S1", "P3067S2",
    "P6775", "P3068", "P6100", "P6110", "P6450", "P6930", "P6940",
]

MODULOS = ("caracteristicas", "fuerza", "ocupados", "no_ocupados", "otras", "vivienda")
_MESES_PREFIJO = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6, "jul": 7,
    "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
}
# Nombres de módulo con plural opcional: el DANE publica "No ocupado.CSV" (marzo 2024),
# "No ocupados.CSV", "Desocupados", la errata "Deocupados", "Ocupados04.csv" (2013), etc.
_RE_NO_OCU = re.compile(r"\bno ocupados?(?![a-z])")
_RE_DESOCU = re.compile(r"\bd(?:e|es)ocupados?(?![a-z])")
_RE_INACT = re.compile(r"\binactivos?(?![a-z])")
_RE_OCU = re.compile(r"\bocupados?(?![a-z])")
_HARMONIZE_VERSION = "9"
# Formatos de los microdatos. Se baja el CSV salvo donde el del ANDA está dañado (ver
# CSV_DANADOS en el descargador); dentro de una carpeta se prefiere el formato alterno.
EXTENSIONES = {".dta": 0, ".txt": 1, ".csv": 2}
_RE_MILES = re.compile(r"^\d{1,3}(\.\d{3}){2,}$")


# --------------------------------------------------------------------------- #
# Descubrimiento de archivos
# --------------------------------------------------------------------------- #
def classify_file(filename: str) -> tuple[str | None, str | None]:
    """Devuelve (módulo, dominio) a partir del nombre de archivo del DANE."""
    n = strip_accents(Path(filename).name)
    dominio = None
    for d in ("area", "cabecera", "resto"):
        if re.match(rf"^{d}\b", n):
            dominio = d
    if _RE_NO_OCU.search(n) or _RE_DESOCU.search(n) or _RE_INACT.search(n):
        modulo = "no_ocupados"
    elif _RE_OCU.search(n):
        modulo = "ocupados"
    elif "fuerza de trabajo" in n:
        modulo = "fuerza"
    elif "caracter" in n or "personas" in n:
        modulo = "caracteristicas"
    elif "hogar" in n or "vivienda" in n:
        modulo = "vivienda"
    elif "otras" in n:
        modulo = "otras"
    else:
        modulo = None
    return modulo, dominio


def _sello(path: Path) -> tuple[int, int]:
    """Fecha y tamaño del archivo: parte de la clave de las cachés de abajo, para que un archivo
    reemplazado en la misma ruta (con la app abierta) se vuelva a revisar."""
    try:
        st = path.stat()
    except OSError:
        return (0, 0)
    return (st.st_mtime_ns, st.st_size)


def _header(path: Path) -> frozenset[str]:
    return _header_sellado(path, _sello(path))


def _defecto(path: Path) -> str | None:
    return _defecto_sellado(path, _sello(path))


@lru_cache(maxsize=4096)
def _header_sellado(path: Path, sello: tuple[int, int]) -> frozenset[str]:
    return frozenset(columnas(path))


@lru_cache(maxsize=4096)
def _defecto_sellado(path: Path, sello: tuple[int, int]) -> str | None:
    """
    Defectos conocidos de los CSV del ANDA que hacen inservible un archivo (ver README,
    "Diferencias con la documentación del DANE"). En septiembre de 2021 el CSV viene
    separado por espacios, y el texto libre también los tiene. En 2008 y 2011 el factor
    de expansión perdió el punto decimal ("849.491.032.387.525" es 84,9491032387525).
    """
    if path.suffix.lower() == ".dta":
        return None
    sep, enc = sniff(path)
    with open(path, encoding=enc, errors="replace") as fh:
        encabezado = fh.readline().rstrip("\r\n").split(sep)
        filas = [fh.readline().rstrip("\r\n").split(sep) for _ in range(20)]
    if len(encabezado) == 1:
        return "un archivo legible (el CSV del DANE viene separado por espacios)"
    fex = [i for i, c in enumerate(normalize_columns(encabezado)) if c.startswith("FEX")]
    valores = [f[i].strip() for f in filas for i in fex if len(f) > i and f[i].strip()]
    if valores and sum(bool(_RE_MILES.match(v)) for v in valores) > len(valores) / 2:
        return "un factor de expansión legible (el CSV del DANE lo trae sin punto decimal)"
    return None


def month_from_folder(name: str) -> int | None:
    for word in re.findall(r"[a-z]+", strip_accents(name)):
        if word[:3] in _MESES_PREFIJO and not word.startswith("marco"):
            return _MESES_PREFIJO[word[:3]]
    return None


_NOMBRE_PARTE = {"caracteristicas": "Características generales", "fuerza": "Fuerza de trabajo",
                 "ocupados": "Ocupados", "desocupados": "Desocupados"}


@dataclass
class MesGEIH:
    anio: int
    mes: int
    carpeta: Path
    archivos: dict[str, list[Path]] = field(default_factory=dict)

    @property
    def modulos(self) -> list[str]:
        return sorted(self.archivos)

    @property
    def faltantes(self) -> list[str]:
        """
        Información necesaria para los indicadores laborales que no está en disco.
        En 2020 y en la serie de empalme las marcas OCI/DSI/INI vienen en el
        módulo de características, así que se revisan los encabezados.

        En los meses con los módulos partidos en Cabecera y Resto (2007–2021), cada módulo necesita las dos
        partes: con una sola, el total nacional sale sin la zona rural o sin la urbana. La parte que falta
        se nombra como el archivo del DANE (``"Resto - Ocupados"``).
        """
        if "caracteristicas" not in self.archivos:
            return ["caracteristicas"]
        if danos := sorted({d for f in self.archivos["caracteristicas"] if (d := _defecto(f))}):
            return danos
        cols = set().union(*(_header(f) for f in self.archivos["caracteristicas"]))
        nombres = [strip_accents(f.name) for f in self.archivos.get("no_ocupados", [])]
        falta = []
        if "ocupados" not in self.archivos and "OCI" not in cols:
            falta.append("ocupados")
        if not any(_RE_NO_OCU.search(n) or _RE_DESOCU.search(n) for n in nombres) and "DSI" not in cols:
            falta.append("desocupados")
        if "fuerza" not in self.archivos and not cols & {"PET", "PETI", "INI"}:
            falta.append("fuerza")
        return falta + [nombre for _, nombre in self.partes_faltantes()]

    def partes_faltantes(self) -> list[tuple[str, str]]:
        """``(módulo, archivo)`` de las partes Cabecera o Resto que faltan, p. ej. ``("ocupados", "Resto - Ocupados")``."""
        partes: dict[str, set] = {}
        for modulo in ("caracteristicas", "fuerza", "ocupados", "no_ocupados"):
            for f in self.archivos.get(modulo, []):
                # Antes de 2022, Desocupados e Inactivos son archivos aparte. Inactivos no hace falta: la PET
                # sale de Fuerza de trabajo (y faltantes tampoco lo pide).
                if modulo == "no_ocupados" and _RE_INACT.search(strip_accents(f.name)):
                    continue
                tipo = "desocupados" if modulo == "no_ocupados" else modulo
                partes.setdefault(tipo, set()).add(classify_file(f.name)[1])
        if not any(d & {"cabecera", "resto"} for d in partes.values()):
            return []  # 2022 en adelante y el empalme: un archivo nacional por módulo
        return [(tipo, f"{dominio.capitalize()} - {_NOMBRE_PARTE[tipo]}")
                for tipo, dominios in partes.items() for dominio in ("cabecera", "resto") if dominio not in dominios]

    @property
    def completo(self) -> bool:
        return not self.faltantes


def _root(empalme: bool, root) -> Path:
    if root is not None:
        return Path(root).expanduser()
    return config.get_path("geih_empalme" if empalme else "geih")


def _csv_dir(root: Path) -> Path:
    return root / "datos_csv" if (root / "datos_csv").is_dir() else root


def _pick_files(files: list[Path]) -> dict[str, list[Path]]:
    """Agrupa por módulo y elige el dominio nacional (Cabecera + Resto)."""
    grouped: dict[str, dict[str | None, list[Path]]] = {}
    for f in files:
        modulo, dominio = classify_file(f.name)
        if modulo:
            grouped.setdefault(modulo, {}).setdefault(dominio, []).append(f)
    out = {}
    for modulo, by_dom in grouped.items():
        if "cabecera" in by_dom or "resto" in by_dom:
            chosen = by_dom.get("cabecera", []) + by_dom.get("resto", [])
        elif None in by_dom:
            chosen = by_dom[None]
        else:
            chosen = by_dom["area"]
        # Desocupados + Inactivos (antes de 2022) son dos archivos del mismo
        # módulo lógico; se conservan ambos. Duplicados exactos de nombre no.
        seen, uniq = set(), []
        # Archivos del nivel superior primero; las copias en subcarpetas se ignoran.
        for f in sorted(chosen, key=lambda p: (len(p.parts), EXTENSIONES.get(p.suffix.lower(), 9), str(p))):
            key = re.sub(r"\s*\(\d+\)", "", f.stem.lower())
            if key not in seen:
                seen.add(key)
                uniq.append(f)
        out[modulo] = uniq
    return out


def find_months(years: Iterable[int] | int | None = None, empalme: bool = False, root=None) -> list[MesGEIH]:
    """
    Meses de la GEIH que hay en disco.

    Recorre ``<carpeta>/datos_csv/<año>/<mes>/`` y reconoce el mes aunque la carpeta tenga el nombre
    que trae el ZIP del DANE (``Enero 2024``, ``ENE_2021``, ``CSV 13``...). Busca los archivos en
    subcarpetas y, de cada módulo, elige el total nacional (Cabecera + Resto).

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    empalme
        Buscar en la carpeta de la serie de empalme.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path``).

    Devuelve
    --------
    list of MesGEIH
        Uno por mes, ordenados. Cada uno tiene ``anio``, ``mes``, ``carpeta``, ``archivos``
        (``{módulo: [rutas]}``), ``modulos``, ``faltantes`` (lo que falta para los indicadores
        laborales) y ``completo``.

    Véase también
    -------------
    available : Lo mismo como tabla.
    load_month : Leer un mes.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> meses = dd.geih.find_months(2024)  # doctest: +SKIP
    >>> meses[0].anio, meses[0].mes, meses[0].completo  # doctest: +SKIP
    (2024, 1, True)
    >>> meses[0].modulos  # doctest: +SKIP
    ['caracteristicas', 'fuerza', 'no_ocupados', 'ocupados', 'otras', 'vivienda']
    """
    base = _csv_dir(_root(empalme, root))
    if not base.is_dir():
        return []
    if years is not None:
        # numbers.Integral: también un año de numpy (df.anio.max())
        years = {int(y) for y in ([years] if isinstance(years, (numbers.Integral, str)) else years)}
    result = []
    for ydir in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(ydir.name)
        if years is not None and anio not in years:
            continue
        for mdir in sorted(p for p in ydir.iterdir() if p.is_dir()):
            mes = month_from_folder(mdir.name)
            # rglob: algunos ZIP del DANE traen subcarpetas (p. ej. "CSV 13/No ocupados.CSV")
            files = [f for f in mdir.rglob("*") if f.is_file() and f.suffix.lower() in EXTENSIONES]
            if mes is None or not files:
                continue
            result.append(MesGEIH(anio, mes, mdir, _pick_files(files)))
    # Un mes puede quedar en dos carpetas: la del CSV dañado del ANDA y la del formato que
    # lo reemplaza. Se usa una sola (sumar las dos duplicaría el mes): la completa, la que
    # trae más módulos y, si empatan, la más reciente.
    por_mes: dict[tuple[int, int], list[MesGEIH]] = {}
    for m in result:
        por_mes.setdefault((m.anio, m.mes), []).append(m)
    result = []
    for (anio, mes), ms in por_mes.items():
        if len(ms) > 1:
            ms = sorted(ms, key=lambda m: (m.completo, len(m.archivos), _mtime(m)), reverse=True)
            if ms[1].completo:  # el caso esperado (una dañada y su reemplazo) no merece aviso
                log.warning(f"{MESES[mes]} {anio} está completo en varias carpetas; se usa "
                            f"{ms[0].carpeta.name!r} y se ignora "
                            f"{', '.join(repr(m.carpeta.name) for m in ms[1:] if m.completo)}.")
        result.append(ms[0])
    return sorted(result, key=lambda m: (m.anio, m.mes))


def _mtime(mes: MesGEIH) -> float:
    """Fecha del archivo más reciente del mes (0 si no tiene archivos reconocidos o desaparecieron)."""
    fechas = []
    for f in (f for fs in mes.archivos.values() for f in fs):
        try:
            fechas.append(f.stat().st_mtime)
        except OSError:
            pass
    return max(fechas, default=0.0)


def available(empalme: bool = False, root=None) -> pd.DataFrame:
    """
    Tabla de los meses de la GEIH descargados.

    Parámetros
    ----------
    empalme
        Revisar la serie de empalme en vez de la principal.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path``).

    Devuelve
    --------
    DataFrame
        Una fila por mes con ``anio``, ``mes``, ``nombre_mes``, ``carpeta``, ``modulos``, ``completo`` y
        ``faltantes``. ``load`` omite los meses con ``completo=False``.

    Véase también
    -------------
    download : Descargar lo que falta.
    find_months : Los mismos meses como objetos.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> av = dd.geih.available()  # doctest: +SKIP
    >>> av.groupby("anio")["completo"].sum().tail(3)  # doctest: +SKIP
    anio
    2024    12
    2025    12
    2026     8
    Name: completo, dtype: int64
    """
    rows = [
        {"anio": m.anio, "mes": m.mes, "nombre_mes": MESES[m.mes], "carpeta": m.carpeta.name,
         "modulos": ", ".join(m.modulos), "completo": m.completo, "faltantes": ", ".join(m.faltantes)}
        for m in find_months(empalme=empalme, root=root)
    ]
    return pd.DataFrame(rows, columns=["anio", "mes", "nombre_mes", "carpeta", "modulos", "completo", "faltantes"])


# --------------------------------------------------------------------------- #
# Lectura de un mes
# --------------------------------------------------------------------------- #
def _merge_new_columns(base: pd.DataFrame, other: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    keys = [k for k in keys if k in base.columns and k in other.columns]
    extra = [c for c in other.columns if c not in base.columns]
    # El factor de expansión es el de características. Otros módulos pueden traer uno
    # distinto con otro nombre (febrero de 2011: FEX_C en "Otras actividades" junto a
    # FEX_C_2011), que harmonize preferiría.
    if any(c.startswith("FEX") for c in base.columns):
        extra = [c for c in extra if not c.startswith("FEX")]
    if not keys or not extra:
        return base
    other = other[keys + extra].drop_duplicates(subset=keys)
    for k in keys:  # tipos compatibles para el merge
        if base[k].dtype != other[k].dtype:
            base[k] = pd.to_numeric(base[k], errors="coerce")
            other[k] = pd.to_numeric(other[k], errors="coerce")
    return base.merge(other, on=keys, how="left")


def _markers(path: Path) -> dict[str, int]:
    """
    Marcas de pertenencia a un módulo. En años antiguos (p. ej. 2007) no existen
    las variables OCI/DSI/INI: estar en el archivo de Ocupados es ser ocupado.
    """
    n = strip_accents(path.name)
    if "fuerza de trabajo" in n:
        return {"_EN_FT": 1}
    if _RE_DESOCU.search(n):
        return {"_EN_DSI": 1}
    if "inactivos" in n:
        return {"_EN_INI": 1}
    if _RE_OCU.search(n) and not _RE_NO_OCU.search(n):
        return {"_EN_OCU": 1}
    return {}


def _read_module(files: list[Path], columns) -> pd.DataFrame:
    frames = []
    for f in files:
        df = read_table(f, columns=columns)
        if len(df.columns):
            frames.append(df.assign(**_markers(f)))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True, sort=False) if len(frames) > 1 else frames[0]


def load_month(mes: MesGEIH, columns="core", modules: Iterable[str] | None = None) -> pd.DataFrame:
    """
    Une los módulos de un mes en una tabla de personas, sin armonizar.

    Parte del módulo de características generales (una fila por persona) y le agrega las columnas
    nuevas de los demás módulos con la llave de persona (``DIRECTORIO``, ``SECUENCIA_P``, ``ORDEN``), o
    la de hogar (``DIRECTORIO``, ``SECUENCIA_P``) para vivienda. Es el primer paso de ``load``, que
    además guarda el resultado en caché y lo armoniza.

    Parámetros
    ----------
    mes
        Un mes de ``find_months``.
    columns
        ``"core"`` (las de ``CORE_RAW``), ``"all"`` (todas) o una lista de variables DANE que se suman a
        las de ``CORE_RAW``.
    modules
        Módulos a unir (de ``MODULOS``). Por defecto, todos los que haya.

    Devuelve
    --------
    DataFrame
        Una fila por persona, con ``anio``, ``mes`` y las variables originales del DANE en mayúscula.

    Lanza
    -----
    FileNotFoundError
        Si el mes no tiene el módulo de características generales.

    Véase también
    -------------
    load : Varios meses, con caché y armonizados.
    harmonize : Agregar las variables armonizadas.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> mes = dd.geih.find_months(2024)[0]  # doctest: +SKIP
    >>> crudo = dd.geih.load_month(mes)  # doctest: +SKIP
    >>> crudo.shape  # doctest: +SKIP
    (70648, 29)
    """
    columns, modules = _lista_columnas(columns), _lista(modules)
    if columns == "all":
        selector = None
    else:
        wanted = set(CORE_RAW) | ({c.upper() for c in columns} if columns not in (None, "core") else set())
        selector = wanted.__contains__
    modules = set(modules or MODULOS)

    if "caracteristicas" not in mes.archivos:
        raise FileNotFoundError(f"{mes.carpeta}: falta el módulo de características generales")
    base = _read_module(mes.archivos["caracteristicas"], selector)

    for modulo in ("fuerza", "ocupados", "no_ocupados", "otras"):
        if modulo not in mes.archivos or modulo not in modules:
            continue
        df = _read_module(mes.archivos[modulo], selector)
        base = _merge_new_columns(base, df, KEYS_PERSONA)

    if "vivienda" in mes.archivos and "vivienda" in modules:
        df = _read_module(mes.archivos["vivienda"], selector)
        base = _merge_new_columns(base, df, KEYS_HOGAR)

    ids = pd.DataFrame({"anio": mes.anio, "mes": mes.mes}, index=base.index)
    return pd.concat([ids, base], axis=1)


# --------------------------------------------------------------------------- #
# Armonización
# --------------------------------------------------------------------------- #
def _num(df: pd.DataFrame, col: str) -> pd.Series:
    if col in df.columns:
        return pd.to_numeric(df[col], errors="coerce").astype("float64")
    return pd.Series(np.nan, index=df.index)


# Las preguntas que usa la medición de informalidad del DANE; existen desde 2022
COLUMNAS_INFORMALIDAD = ("P6430", "RAMA2D_R4", "OFICIO_C8", "P3045S1", "P3046", "P3069", "P6765", "P3065", "P3066",
                         "P3067", "P3067S1", "P3067S2", "P6775", "P3068", "P6100", "P6110", "P6450", "P6920",
                         "P6930", "P6940")


def _formal_dane(df: pd.DataFrame, anio: pd.Series) -> pd.Series:
    """
    Formalidad como la mide el DANE (17.ª CIET, medición publicada desde julio de 2022): 1 formal, 0 informal,
    vacío antes de 2022, cuando el cuestionario no tenía estas preguntas.

    Traduce regla por regla el código SAS que el DANE publica en el anexo de «Empleo informal y seguridad
    social» (hoja «Código_SAS»), en el mismo orden: en cada cadena gana la primera regla que se cumple, como
    en el IF ... ELSE de SAS. Con eso, los formales e informales de cada mes de 2022 a 2026 coinciden con
    los del anexo (tests/datos/dane_informalidad.csv). Lo que el código no dice y hubo que suponer:

    * ``OFICIO_C8`` viene como número en los archivos del ANDA y pierde el cero inicial (``110`` es el
      código ``0110``): se completa a 4 dígitos antes de tomar los 2 primeros, como el texto del DANE.
      Hay independientes con código ``0`` que el DANE cuenta como formales; sin completar, quedarían sin
      clasificar.
    * ``PER``, «el año de análisis», es ``anio``.
    * Un vacío se compara como en SAS, menor que cualquier número (``P3069 <= 3`` se cumple, ``>= 4`` no).
      En 2022–2026 ningún registro llega a esas reglas con un vacío.
    """
    nada = pd.Series(np.nan, index=df.index)
    if any(c not in df.columns for c in COLUMNAS_INFORMALIDAD):
        return nada
    v = {c: _num(df, c) for c in COLUMNAS_INFORMALIDAD}
    p = v["P6430"]
    def es(c, *k): return v[c].isin(k)                      # noqa: E301,E704
    def ge(c, k): return v[c] >= k                          # noqa: E301,E704  vacío: no
    def le(c, k): return v[c].isna() | (v[c] <= k)          # noqa: E301,E704  vacío: sí, como en SAS
    oficio = v["OFICIO_C8"].astype("Int64").astype("string").str.zfill(4).str[:2]
    of_bajo = oficio.between("00", "20").fillna(False).astype(bool)   # directivos y profesionales
    of_alto = (oficio >= "21").fillna(False).astype(bool)
    rama = es("RAMA2D_R4", 84, 99)                         # administración pública, organismos extraterritoriales
    asal, ind, cp, pat = p.isin([1, 7]), p.isin([4, 5]), p == 4, p == 5
    sin_neg, con_neg = ind & ~es("P6765", 7), ind & es("P6765", 7)
    s1 = es("P3045S1", 2, 9)
    sn = sin_neg & es("P3065", 2, 9)
    reg, no_reg = con_neg & (v["P3067"] == 1), con_neg & (v["P3067"] == 2)
    renovo, no_renovo = reg & (v["P3067S1"] == 1), reg & (v["P3067S1"] == 2)
    anterior = anio - 1                                     # ANIOS=(PER-1)
    renovado = v["P3067S2"] >= anterior
    # /*SECTOR INFORMAL*/
    sector = [
        (p == 3, np.nan), (p == 6, 0), (rama, 1), (p == 8, 0),
        (p == 2, 1),
        # /*ASALARIADOS*/
        (asal & (v["P3045S1"] == 1), 1),
        (asal & s1 & (v["P3046"] == 1), 1),
        (asal & s1 & (v["P3046"] == 2), 0),
        (asal & s1 & (v["P3046"] == 9) & ge("P3069", 4), 1),
        (asal & s1 & (v["P3046"] == 9) & le("P3069", 3), 0),
        # /*INDEPENDIENTES*/ /*SIN NEGOCIO*/
        (sin_neg & (v["P3065"] == 1), 1),
        (sn & (v["P3066"] == 1), 1),
        (sn & (v["P3066"] == 2), 0),
        (sn & pat & (v["P3066"] == 9) & ge("P3069", 4), 1),
        (sn & pat & (v["P3066"] == 9) & le("P3069", 3), 0),
        (sn & cp & (v["P3066"] == 9) & of_bajo, 1),
        (sn & cp & (v["P3066"] == 9) & of_alto, 0),
        # /*CON NEGOCIO*/ /*CON REGISTRO MERCANTIL*/
        (renovo & renovado, 1),
        (renovo & ~renovado, 0),                            # P3067S2 < ANIOS, también vacío
        (no_renovo & (v["P6775"] == 1), 1),
        (no_renovo & (v["P6775"] == 3) & of_bajo, 1),
        (no_renovo & (v["P6775"] == 3) & of_alto, 0),
        (no_renovo & (v["P6775"] == 2), 0),
        (no_renovo & cp & (v["P6775"] == 9) & of_bajo, 1),
        (no_renovo & cp & (v["P6775"] == 9) & of_alto, 0),
        (no_renovo & pat & (v["P6775"] == 9) & ge("P3069", 4), 1),
        (no_renovo & pat & (v["P6775"] == 9) & le("P3069", 3), 0),
        # /*SIN REGISTRO MERCANTIL*/
        (no_reg & (v["P6775"] == 1) & (v["P3068"] == 1), 1),
        (no_reg & (v["P6775"] == 1) & (v["P3068"] == 2), 0),
        (no_reg & (v["P6775"] == 3) & of_bajo, 1),
        (no_reg & (v["P6775"] == 3) & of_alto, 0),
        (no_reg & (v["P6775"] == 1) & es("P3068", 3, 9), 0),  # el 3 reemplaza al 9 desde 2023
        (no_reg & (v["P6775"] == 2), 0),
        (no_reg & pat & (v["P6775"] == 9) & ge("P3069", 4), 1),
        (no_reg & pat & (v["P6775"] == 9) & le("P3069", 3), 0),
        (no_reg & cp & (v["P6775"] == 9) & of_bajo, 1),
        (no_reg & cp & (v["P6775"] == 9) & of_alto, 0),
    ]
    formal_sector = np.select([c.to_numpy(bool) for c, _ in sector], [k for _, k in sector], default=np.nan)
    # /*OCUPACIÓN INFORMAL*/: asalariados, empleados domésticos y jornaleros, por salud y pensión
    a137 = p.isin([1, 3, 7])
    salud = (a137 & es("P6100", 1, 2) & es("P6110", 1, 2, 4)) | (a137 & (v["P6100"] == 9) & (v["P6450"] == 2)) \
        | (a137 & (v["P6110"] == 9) & (v["P6450"] == 2))
    pension = (a137 & (v["P6920"] == 3)) | (a137 & (v["P6920"] == 1) & es("P6930", 1, 2, 3) & es("P6940", 1, 3))
    ei = np.select([(p == 2).to_numpy(bool), p.isin([6, 8]).to_numpy(bool), ind.to_numpy(bool),
                    (a137 & salud & pension).to_numpy(bool), a137.to_numpy(bool)],
                   [1, 0, formal_sector, 1, 0], default=np.nan)
    ei = np.where(rama & ~p.isin([6, 8]), 1, ei)
    return pd.Series(ei, index=df.index).where(anio >= 2022)


# Las de la medición anterior: posición ocupacional, tamaño de la empresa y oficio (CNO 1970), hasta 2021
COLUMNAS_INFORMALIDAD_2005 = ("P6430", "P6870", "OFICIO")


def _formal_marco2005(df: pd.DataFrame, anio: pd.Series) -> pd.Series:
    """
    Formalidad con la medición anterior del DANE (marco 2005, 15.ª CIET, empresas de hasta 5 trabajadores
    desde diciembre de 2009): 1 formal, 0 informal, vacío desde 2022 o sin el dato que hace falta.

    El DANE no publicó el código de esta medición. La regla sale de la metodología de 2009 y de la
    presentación de julio de 2022, y se ajustó con lo que publicó: con ella, los informales de cada
    trimestre móvil de 2007 a 2019 y de 2021 coinciden con el anexo en las 13 ciudades, y en las 23 salvo
    febrero de 2008 (tests/datos/dane_informalidad_marco2005.csv). Es informal quien trabaja en una empresa
    de hasta 5 personas (``P6870`` 1 a 3) como empleado particular, empleado doméstico, patrón,
    trabajador sin remuneración, jornalero o cuenta propia que no es profesional; los demás son formales,
    también los del gobierno y «otro».
    """
    nada = pd.Series(np.nan, index=df.index)
    if any(c not in df.columns for c in COLUMNAS_INFORMALIDAD_2005):
        return nada
    p, tamano, oficio = _num(df, "P6430"), _num(df, "P6870"), _num(df, "OFICIO")
    hasta5 = tamano <= 3                                    # trabaja solo, 2 a 3 o 4 a 5 personas
    # Difiere de la metodología de 2009, que cuenta como informales a todos los empleados domésticos,
    # trabajadores sin remuneración y jornaleros: lo publicado solo cuadra si también están en empresas de
    # hasta 5 personas, como dice la presentación de 2022. Y «profesionales» son los oficios 1 a 20 de la CNO
    # (profesionales, técnicos y directivos): el 0 no lo es (ver README).
    profesional = oficio.between(1, 20)
    informal = hasta5 & (p.isin([1, 3, 5, 6, 7, 8]) | ((p == 4) & ~profesional))
    formal = pd.Series(np.where(informal, 0.0, 1.0), index=df.index)
    sin_dato = p.isna() | (tamano.isna() & ~p.isin([2, 9])) | (hasta5 & (p == 4) & oficio.isna())
    return formal.mask(sin_dato).where(anio <= 2021)


def _first(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    out = pd.Series(np.nan, index=df.index)
    for c in cols:
        if c in df.columns:
            out = out.fillna(pd.to_numeric(df[c], errors="coerce").astype("float64"))
    return out


_EDUC_P3042 = {1: "Ninguno", 2: "Ninguno", 3: "Primaria", 4: "Secundaria", 5: "Media", 6: "Media",
               7: "Media", 8: "Superior", 9: "Superior", 10: "Superior", 11: "Superior",
               12: "Superior", 13: "Superior"}
_EDUC_P6210 = {1: "Ninguno", 2: "Ninguno", 3: "Primaria", 4: "Secundaria", 5: "Media", 6: "Superior"}
NIVELES_EDUC = ["Ninguno", "Primaria", "Secundaria", "Media", "Superior"]
CONDICIONES = ["Ocupado", "Desocupado", "Inactivo", "Fuera de la PET"]
GRUPOS_EDAD = ["0–14", "15–24", "25–34", "35–44", "45–54", "55–64", "65+"]
POSICIONES = ["Empleado particular", "Empleado del gobierno", "Empleado doméstico", "Cuenta propia",
              "Patrón o empleador", "Familiar sin remuneración", "Sin remuneración (otros hogares)",
              "Jornalero o peón", "Otro"]
# Categorías fijas: los meses se armonizan por separado y, al concatenarlos, solo
# conservan el tipo categórico si todos tienen exactamente las mismas categorías.
CATEGORIAS = {
    "sexo": pd.CategoricalDtype(["Hombre", "Mujer"]),
    "zona": pd.CategoricalDtype(["Urbano (cabecera)", "Rural (centros poblados y disperso)"]),
    "grupo_edad": pd.CategoricalDtype(GRUPOS_EDAD, ordered=True),
    "nivel_educativo": pd.CategoricalDtype(NIVELES_EDUC, ordered=True),
    "departamento": pd.CategoricalDtype(sorted(set(DEPARTAMENTOS.values()))),
    "condicion": pd.CategoricalDtype(CONDICIONES),
    "posicion_ocupacional": pd.CategoricalDtype(POSICIONES),
}
MARCOS = {
    "censo 2005": "proyecciones de población del censo 2005 y PET de 12 años o más (10 en la zona rural)",
    "CNPV 2018": "proyecciones de población del CNPV 2018 y PET de 15 años o más",
}


def marco_muestral(anio: int, empalme: bool = False) -> str:
    """
    Marco muestral de los factores de expansión de un año.

    Los niveles y las tasas no son comparables entre marcos: cambian las proyecciones de población y la
    edad mínima de la PET. En la serie principal, 2020 ya viene con el CNPV 2018 pero 2021 todavía con
    el censo 2005; desde 2022, con el CNPV 2018. La serie de empalme lleva 2010–2020 al CNPV 2018.

    Parámetros
    ----------
    anio
        Año de la encuesta.
    empalme
        Si el año es de la serie de empalme.

    Devuelve
    --------
    str
        ``"censo 2005"`` o ``"CNPV 2018"``, las claves de ``MARCOS``.

    Véase también
    -------------
    MARCOS : Qué significa cada marco.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.geih.marco_muestral(2021)
    'censo 2005'
    >>> dd.geih.marco_muestral(2022)
    'CNPV 2018'
    >>> dd.geih.marco_muestral(2015, empalme=True)
    'CNPV 2018'
    >>> dd.geih.MARCOS["CNPV 2018"]
    'proyecciones de población del CNPV 2018 y PET de 15 años o más'
    """
    return "CNPV 2018" if empalme or anio == 2020 or anio >= 2022 else "censo 2005"


def harmonize(df: pd.DataFrame, edad_minima_pet: int | None = None) -> pd.DataFrame:
    """
    Agrega las variables armonizadas, iguales en todos los años.

    Cada variable se construye fila a fila desde la variable del DANE que exista en esa época (por
    ejemplo, ``sexo`` desde ``P3271`` o ``P6020``), así que se pueden juntar años distintos. Las
    variables armonizadas van en minúscula; las originales, en mayúscula, no se tocan. ``load`` la
    aplica a cada mes.

    Parámetros
    ----------
    df
        Un mes (o varios) de ``load_month``: variables del DANE con ``anio`` y ``mes``.
    edad_minima_pet
        Si se indica, quien tenga menos años queda fuera de la PET (y de la fuerza de trabajo) aunque el
        archivo del DANE lo marque dentro. ``load`` usa 15 para la serie de empalme.

    Devuelve
    --------
    DataFrame
        Una copia de ``df`` con ``fex``, ``sexo``, ``edad``, ``grupo_edad``, ``jefe_hogar``, ``dpto``,
        ``departamento``, ``zona``, ``condicion``, ``pet``, ``fuerza_trabajo``, ``ocupado``,
        ``desocupado``, ``inactivo``, ``formal``, ``formal_marco2005``, ``cotiza_pension``,
        ``ingreso_laboral``, ``smlv``,
        ``ratio_smlv``, ``horas_semana``, ``posicion_ocupacional``, ``rama2d``, ``rama_rev`` y
        ``nivel_educativo``.

    Véase también
    -------------
    load : Carga y armoniza.
    CATEGORIAS : Categorías de las variables categóricas.

    Notas
    -----
    La guía «Variables armonizadas» explica de qué variable del DANE sale cada una y cómo se define. Las
    variables de ocupados (``formal``, ``ingreso_laboral``, ``horas_semana``,
    ``posicion_ocupacional``) quedan vacías para quien no está ocupado.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> crudo = dd.geih.load_month(dd.geih.find_months(2024)[0])  # doctest: +SKIP
    >>> df = dd.geih.harmonize(crudo)  # doctest: +SKIP
    >>> df["condicion"].value_counts()  # doctest: +SKIP
    """
    df = df.copy()
    anio = df["anio"]

    df["fex"] = _first(df, ["FEX_C18", "FEX_C", "FEX_C_2011"])
    sexo = _num(df, "P3271").fillna(_num(df, "P6020"))
    df["sexo"] = pd.Categorical(sexo.map({1: "Hombre", 2: "Mujer"}), dtype=CATEGORIAS["sexo"])
    df["edad"] = _num(df, "P6040")
    df["grupo_edad"] = pd.cut(df["edad"], bins=[-1, 14, 24, 34, 44, 54, 64, 200], labels=GRUPOS_EDAD)
    df["jefe_hogar"] = (_num(df, "P6050") == 1).astype("Int8")

    dpto = _num(df, "DPTO")
    df["dpto"] = dpto.astype("Int64")
    df["departamento"] = pd.Categorical(dpto.map(DEPARTAMENTOS), dtype=CATEGORIAS["departamento"])
    clase = _num(df, "CLASE")
    df["zona"] = pd.Categorical(clase.map({1: "Urbano (cabecera)", 2: "Rural (centros poblados y disperso)"}),
                                dtype=CATEGORIAS["zona"])

    # Condición de actividad
    ocupado = (_num(df, "OCI") == 1) | (_num(df, "_EN_OCU") == 1)
    desocupado = ((_num(df, "DSI") == 1) | (_num(df, "_EN_DSI") == 1)) & ~ocupado
    pet = ((_num(df, "PET") == 1) | (_num(df, "PETI") == 1) | (_num(df, "INI") == 1)
           | (_num(df, "_EN_FT") == 1) | (_num(df, "_EN_INI") == 1)
           | ocupado | desocupado)
    if edad_minima_pet is not None:
        en_edad = df["edad"] >= edad_minima_pet
        ocupado, desocupado, pet = ocupado & en_edad, desocupado & en_edad, pet & en_edad
    inactivo = pet & ~ocupado & ~desocupado
    cond = np.select([ocupado, desocupado, inactivo], CONDICIONES[:3], default=CONDICIONES[3])
    df["condicion"] = pd.Categorical(cond, dtype=CATEGORIAS["condicion"])
    df["pet"] = pet.astype("Int8")
    df["fuerza_trabajo"] = (ocupado | desocupado).astype("Int8")
    df["ocupado"] = ocupado.astype("Int8")
    df["desocupado"] = desocupado.astype("Int8")
    df["inactivo"] = inactivo.astype("Int8")

    # Formalidad: la medición del DANE, desde 2022 (_formal_dane). Solo para ocupados.
    df["formal"] = _formal_dane(df, anio).astype("Int8").where(ocupado)
    df["formal_marco2005"] = _formal_marco2005(df, anio).astype("Int8").where(ocupado)
    cotiza = _num(df, "P6920") == 1
    df["cotiza_pension"] = cotiza.astype("Int8").where(ocupado)

    ing = _num(df, "INGLABO")
    df["ingreso_laboral"] = ing.where(ocupado)
    df["smlv"] = anio.map(SMLV)
    df["ratio_smlv"] = df["ingreso_laboral"] / df["smlv"]
    df["horas_semana"] = _num(df, "P6800").where(ocupado)

    pos = _num(df, "P6430")
    pos_map = dict(enumerate(POSICIONES, start=1))
    # Cuestionario de 2022 en adelante: 7 = jornalero y 8 = otro (desaparece el 9). El DDI
    # del DANE para 2022–2025 repite las categorías antiguas, pero en los datos el 7 es
    # 100 % agropecuario y con ingreso. Fila a fila: se pueden juntar años de ambas épocas.
    pos_map_2022 = {**pos_map, 7: "Jornalero o peón", 8: "Otro"}
    del pos_map_2022[9]
    etiqueta = pos.map(pos_map).where(anio < 2022, pos.map(pos_map_2022))
    df["posicion_ocupacional"] = pd.Categorical(etiqueta.where(ocupado), dtype=CATEGORIAS["posicion_ocupacional"])

    # Fila a fila: al juntar años distintos conviven ambas versiones.
    r4, r3 = _num(df, "RAMA2D_R4"), _num(df, "RAMA2D")
    df["rama2d"] = r4.fillna(r3).astype("Int64")
    df["rama_rev"] = pd.Series(np.where(r4.notna(), 4, np.where(r3.notna(), 3, np.nan)), index=df.index).astype("Int8")

    # where y no fillna: con dos columnas de texto, fillna avisa en pandas 2 que dejará de convertir el tipo
    nuevo, viejo = _num(df, "P3042").map(_EDUC_P3042), _num(df, "P6210").map(_EDUC_P6210)
    educ = nuevo.where(nuevo.notna(), viejo)
    df["nivel_educativo"] = pd.Categorical(educ, dtype=CATEGORIAS["nivel_educativo"])

    return df.drop(columns=["_EN_FT", "_EN_OCU", "_EN_DSI", "_EN_INI"], errors="ignore")


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #
def _firma_archivos(mes: MesGEIH) -> list[str]:
    """Ruta, tamaño y fecha de modificación de cada archivo del mes (para las llaves de caché)."""
    stamp = []
    for files in mes.archivos.values():
        for f in files:
            st = f.stat()
            stamp.append(f"{f}:{st.st_size}:{int(st.st_mtime)}")
    return sorted(stamp)


def _lista(x):
    """Un solo nombre como lista (``list("P6500")`` lo partiría en letras); ``None`` se deja igual."""
    return [x] if isinstance(x, str) else x


def _lista_columnas(columns):
    """Como ``_lista``, salvo los valores especiales ``"core"`` y ``"all"``."""
    return columns if columns in ("core", "all") else _lista(columns)


def _cache_path(mes: MesGEIH, columns, modules) -> Path:
    cols = "all" if columns == "all" else ",".join(sorted({c.upper() for c in (columns if columns not in (None, "core") else [])}))
    key = "|".join([_HARMONIZE_VERSION, *_firma_archivos(mes), cols, ",".join(sorted(modules or MODULOS))])
    digest = hashlib.sha1(key.encode()).hexdigest()[:16]
    return config.CACHE_DIR / "geih" / f"{mes.anio}_{mes.mes:02d}_{digest}.parquet"


def load(
    years: Iterable[int] | int,
    months: Iterable[int] | int | None = None,
    columns="core",
    empalme: bool = False,
    harmonize_vars: bool = True,
    modules: Iterable[str] | None = None,
    root=None,
    cache: bool = True,
    progress=None,
    incluir_incompletos: bool = False,
    variables: Iterable[str] | None = None,
) -> pd.DataFrame:
    """
    Carga la GEIH: una fila por persona, con los módulos unidos y las variables armonizadas.

    Es la puerta de entrada a los microdatos. Para cada mes, une los módulos (``load_month``), guarda el
    resultado en caché, agrega las variables armonizadas (``harmonize``) y se queda con las columnas
    pedidas; al final junta todos los meses.

    Parámetros
    ----------
    years
        Año o lista de años.
    months
        Mes o lista de meses (1–12); None para todos los disponibles.
    columns
        ``"core"`` (por defecto), ``"all"`` o lista de variables DANE extra,
        por ejemplo ``["P6500", "P7070"]``.
    empalme
        Usar la serie de empalme (2010–2020, marco 2018).
    harmonize_vars
        Agregar variables armonizadas (``sexo``, ``condicion``...).
    modules
        Subconjunto de ``dane_data.geih.MODULOS`` a fusionar.
    cache
        Guarda cada mes procesado en ``~/.cache/dane_data`` (parquet) para
        que la siguiente carga sea casi instantánea.
    progress
        Función opcional ``(fraccion, mensaje)``.
    incluir_incompletos
        Por defecto se omiten (con aviso) los meses a los que
        les falta un módulo clave (p. ej. desocupados): con ellos la tasa de
        desocupación saldría 0 %. Los meses omitidos quedan en
        ``df.attrs["meses_omitidos"]``.
    variables
        Conservar solo estas variables (armonizadas o del DANE; ``anio`` y
        ``mes`` siempre). Cada mes se recorta al leerlo, así que la memoria depende
        solo de lo que se conserva: útil para juntar muchos años. Las variables DANE
        que no están en ``CORE_RAW`` deben pedirse también en ``columns``.

    Devuelve
    --------
    DataFrame
        Una fila por persona y mes: ``anio``, ``mes``, las variables armonizadas en minúscula y las del
        DANE en mayúscula. ``df.attrs["meses_omitidos"]`` lista los meses incompletos que se saltaron.

    Lanza
    -----
    FileNotFoundError
        Si no hay ningún mes completo para lo pedido.

    Véase también
    -------------
    indicadores : Indicadores del mercado laboral.
    serie_indicadores : Indicadores de muchos años sin cargarlos en memoria.
    dane_data.tabla : Tablas ponderadas.
    available : Qué meses hay en disco.

    Notas
    -----
    Un año completo tiene del orden de 800 000 registros. Con ``variables`` la memoria depende solo de las columnas
    que se conservan, porque cada mes se recorta antes de juntarlos.

    La primera lectura de un mes tarda unos segundos; las siguientes salen de la caché
    (``~/.cache/dane_data/geih``). La caché se invalida sola si cambian los archivos del mes.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> df = dd.geih.load(2025, months=[1, 2, 3])  # doctest: +SKIP
    >>> dd.geih.indicadores(df, por="sexo")  # doctest: +SKIP

    Variables del DANE que no están en ``CORE_RAW``:

    >>> df = dd.geih.load(2024, columns=["P6500", "P7070"])  # doctest: +SKIP

    Muchos años, solo con lo necesario:

    >>> df = dd.geih.load(range(2007, 2026), variables=["fex", "sexo", "ocupado", "ingreso_laboral"])  # doctest: +SKIP
    """
    columns, modules = _lista_columnas(columns), _lista(modules)
    if isinstance(months, numbers.Integral):
        months = [months]
    conservar = None
    if variables is not None:
        conservar = list(dict.fromkeys(["anio", "mes", *([variables] if isinstance(variables, str) else variables)]))
    meses = find_months(years, empalme=empalme, root=root)
    if months is not None:
        months = {int(m) for m in months}
        meses = [m for m in meses if m.mes in months]
    omitidos = [m for m in meses if not m.completo]
    if omitidos and not incluir_incompletos:
        detalle = "; ".join(f"{MESES[m.mes]} {m.anio} (falta {', '.join(m.faltantes)})" for m in omitidos)
        if any("CSV del DANE" in f for m in omitidos for f in m.faltantes):
            detalle += (". Vuelva a descargar esos años con dane_data.geih.download(...): para esos meses "
                        "se baja otro formato del ANDA")
        log.warning(f"Se omiten meses incompletos: {detalle}. Use incluir_incompletos=True para cargarlos.")
        meses = [m for m in meses if m.completo]
    if not meses:
        raise FileNotFoundError(
            f"No hay datos GEIH para años={years}, meses={months} en {_root(empalme, root)}. "
            "Descárguelos con dane_data.geih.download(...) o revise dane_data.set_paths(...)."
        )

    frames = []
    for i, mes in enumerate(meses):
        if progress:
            progress(i / len(meses), f"Leyendo {MESES[mes.mes]} {mes.anio}")
        cpath = _cache_path(mes, columns, modules) if cache else None
        df = None
        if cpath is not None and cpath.exists():
            try:
                df = pd.read_parquet(cpath)
                _usado(cpath)
            except Exception:  # caché corrupta: se regenera
                df = None
        if df is None:
            try:
                df = load_month(mes, columns=columns, modules=modules)
            except FileNotFoundError as e:
                log.warning(str(e))
                continue
            if cpath is not None:
                try:
                    _guardar_parquet(df, cpath)
                except Exception as e:  # columnas de tipo mixto, disco lleno, etc.
                    log.debug(f"No se pudo guardar caché {cpath}: {e}")
        # Mes a mes (harmonize es fila a fila): evita armonizar y copiar el frame
        # concatenado de muchos años, que no cabe en memoria.
        if harmonize_vars:
            # El DANE publica el empalme con la PET de 15 años o más, pero el archivo de
            # octubre de 2012 (catálogo 760) la marca con la definición anterior (12+ urbano,
            # 10+ rural). Ver README, "Diferencias con la documentación del DANE".
            df = harmonize(df, edad_minima_pet=15 if empalme else None)
        if conservar is not None:
            df = df[[c for c in conservar if c in df.columns]].copy()  # sin copia, la vista retiene el mes entero
        frames.append(df)
    if progress:
        progress(1.0, "Listo")
    if not frames:
        raise FileNotFoundError("Ningún mes pudo leerse (faltan módulos de características).")

    out = pd.concat(frames, ignore_index=True, sort=False)
    if conservar is not None:
        if faltan := [c for c in conservar if c not in out.columns]:
            log.warning(f"Variables que no existen en los datos cargados: {', '.join(faltan)}.")
        out = out[[c for c in conservar if c in out.columns]]
    out.attrs["meses_omitidos"] = [] if incluir_incompletos else [(m.anio, m.mes, m.faltantes) for m in omitidos]
    return out


def clear_cache(dias: float | None = None) -> int:
    """
    Borra la caché de la GEIH.

    Incluye los meses ya leídos por ``load`` y los resultados por año de ``serie_indicadores``,
    ``serie_tabla`` y ``serie_frecuencias``. Nunca hace falta para tener resultados correctos (la caché
    se invalida sola cuando cambian los datos o el código); sirve para liberar espacio.

    Parámetros
    ----------
    dias
        Borrar solo lo que no se usa hace más de esos días. Por defecto, todo.

    Devuelve
    --------
    int
        Número de archivos borrados.

    Notas
    -----
    Lo que no se usa en 90 días se borra solo, revisando como mucho una vez al día:
    cada combinación de filtros, meses o columnas crea sus propios archivos, y sin esto la caché crecería
    sin límite.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.geih.clear_cache()  # doctest: +SKIP
    412
    >>> dd.geih.clear_cache(dias=30)  # lo que no se usó en el último mes  # doctest: +SKIP
    57
    """
    limite = None if dias is None else time.time() - dias * 86400
    n = 0
    for f in (config.CACHE_DIR / "geih").rglob("*"):
        if f.suffix not in (".parquet", ".tmp"):  # .tmp: escrituras que se interrumpieron
            continue
        try:
            if limite is None or f.stat().st_mtime < limite:
                f.unlink()
                n += 1
        except OSError:  # otra sesión lo borró o lo está usando
            pass
    return n


# Días sin usarse tras los cuales un archivo de la caché se borra solo (ver clear_cache)
_CACHE_DIAS = 90


def _usado(ruta: Path) -> None:
    """Marca un archivo de la caché como recién usado (su fecha es la que mira la limpieza)."""
    try:
        os.utime(ruta)
    except OSError:
        pass


def _limpiar_cache_vieja() -> None:
    """``clear_cache(_CACHE_DIAS)``, como mucho una vez al día (la fecha del marcador dice cuándo fue la última)."""
    marcador = config.CACHE_DIR / "geih" / ".ultima_limpieza"
    try:
        if marcador.exists() and time.time() - marcador.stat().st_mtime < 86400:
            return
        marcador.parent.mkdir(parents=True, exist_ok=True)
        marcador.touch()
    except OSError:
        return
    if n := clear_cache(_CACHE_DIAS):
        log.info(f"Caché: se borraron {n} archivos sin usar en {_CACHE_DIAS} días.")


def _guardar_parquet(df: pd.DataFrame, ruta: Path) -> None:
    """
    Escribe la caché con otro nombre y la renombra al terminar, así nunca se lee un parquet a medias.
    El nombre temporal es único: las sesiones de la app son hilos del mismo proceso y pueden calcular
    lo mismo a la vez.
    """
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(f"{ruta.name}.{uuid.uuid4().hex}.tmp")
    try:
        df.to_parquet(tmp, index=False)
        tmp.replace(ruta)
    finally:
        tmp.unlink(missing_ok=True)
    _limpiar_cache_vieja()  # al escribir algo nuevo, lo viejo que nadie usa
