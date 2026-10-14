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
import re
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
_HARMONIZE_VERSION = "7"
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


@lru_cache(maxsize=4096)
def _header(path: Path) -> frozenset[str]:
    return frozenset(columnas(path))


@lru_cache(maxsize=4096)
def _defecto(path: Path) -> str | None:
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
        return falta

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
    """Lista las carpetas mensuales disponibles localmente."""
    base = _csv_dir(_root(empalme, root))
    if not base.is_dir():
        return []
    if years is not None:
        years = {int(y) for y in ([years] if isinstance(years, (int, str)) else years)}
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
    # lo reemplaza. Se usa la completa.
    por_mes: dict[tuple[int, int], list[MesGEIH]] = {}
    for m in result:
        por_mes.setdefault((m.anio, m.mes), []).append(m)
    result = []
    for ms in por_mes.values():
        completos = [m for m in ms if m.completo] if len(ms) > 1 else []
        result += completos or ms
    return sorted(result, key=lambda m: (m.anio, m.mes))


def available(empalme: bool = False, root=None) -> pd.DataFrame:
    """Tabla de años/meses descargados y sus módulos."""
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
    Fusiona los módulos de un mes a nivel persona (llave DIRECTORIO, SECUENCIA_P, ORDEN).

    ``columns``: ``"core"`` (variables para armonizar), ``"all"`` (todas) o una
    lista de variables DANE adicionales a las ``core``.
    """
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
    Marco de los factores de expansión de un año en el ANDA (clave de ``MARCOS``). Los niveles y las
    tasas no son comparables entre marcos. En la serie principal, 2020 ya viene con el CNPV 2018 pero
    2021 todavía con el censo 2005; desde 2022, con el CNPV 2018. La serie de empalme lleva 2010–2020
    al CNPV 2018.
    """
    return "CNPV 2018" if empalme or anio == 2020 or anio >= 2022 else "censo 2005"


def harmonize(df: pd.DataFrame, edad_minima_pet: int | None = None) -> pd.DataFrame:
    """
    Agrega variables armonizadas (minúscula) comparables entre años.

    ``edad_minima_pet``: si se indica, quien tenga menos años queda fuera de la PET
    (y de la fuerza de trabajo) aunque el archivo del DANE lo marque dentro.
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

    # Formalidad (definición por seguridad social): ocupado afiliado a salud
    # (P6090 = 1) y cotizando a pensión (P6920 = 1). Solo para ocupados.
    cotiza = _num(df, "P6920") == 1
    salud = _num(df, "P6090") == 1
    formal = pd.Series(np.where(cotiza & salud, 1, 0), index=df.index).astype("Int8")
    df["formal"] = formal.where(ocupado)
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

    educ = _num(df, "P3042").map(_EDUC_P3042).fillna(_num(df, "P6210").map(_EDUC_P6210))
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
    Carga la GEIH (una fila por persona) para los años y meses pedidos.

    Parámetros
    ----------
    years : int o lista de int
    months : int, lista de int (1–12) o None para todos los disponibles.
    columns : ``"core"`` (por defecto), ``"all"`` o lista de variables DANE extra,
        por ejemplo ``["P6500", "P7070"]``.
    empalme : usar la serie de empalme (2010–2020, marco 2018).
    harmonize_vars : agregar variables armonizadas (``sexo``, ``condicion``...).
    modules : subconjunto de ``dane_data.geih.MODULOS`` a fusionar.
    cache : guarda cada mes procesado en ``~/.cache/dane_data`` (parquet) para
        que la siguiente carga sea casi instantánea.
    progress : función opcional ``(fraccion, mensaje)``.
    incluir_incompletos : por defecto se omiten (con aviso) los meses a los que
        les falta un módulo clave (p. ej. desocupados): con ellos la tasa de
        desocupación saldría 0 %. Los meses omitidos quedan en
        ``df.attrs["meses_omitidos"]``.
    variables : conservar solo estas variables (armonizadas o del DANE; ``anio`` y
        ``mes`` siempre). Cada mes se recorta al leerlo, así que la memoria depende
        solo de lo que se conserva: útil para juntar muchos años. Las variables DANE
        que no están en ``CORE_RAW`` deben pedirse también en ``columns``.

    Ejemplo
    -------
    >>> df = dd.geih.load(2025, months=[1, 2, 3])
    >>> dd.geih.indicadores(df, por="sexo")
    >>> df = dd.geih.load(range(2007, 2026), variables=["fex", "sexo", "ocupado", "ingreso_laboral"])
    """
    if isinstance(months, int):
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
                    cpath.parent.mkdir(parents=True, exist_ok=True)
                    df.to_parquet(cpath, index=False)
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


def clear_cache() -> int:
    """Borra la caché de meses procesados y de indicadores precalculados. Devuelve el número de archivos borrados."""
    n = 0
    for f in (config.CACHE_DIR / "geih").rglob("*.parquet"):
        f.unlink()
        n += 1
    return n
