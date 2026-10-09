"""
Carga y armonización de microdatos EAM (un establecimiento por fila).

Entre 1992 y 2024 cambian: el separador (``;``, ``,``, tabulador), las
mayúsculas de los nombres y el nombre de la variable CIIU (``CIIU2N4``,
``ciiu2``, ``CIIU``, ``ciiu3``, ``ciiu4``, ``ciiu_4``). ``load`` deja todos los
nombres en minúscula y agrega:

* ``anio``      año de referencia.
* ``ciiu``      código CIIU (texto; normalmente 4 dígitos, pero en algunos años
                se publica a 2–3 dígitos por anonimización).
* ``ciiu_rev``  revisión de la CIIU (2, 3 o 4) según la variable de origen.
* ``division``  primeros 2 dígitos del CIIU y ``sector`` su nombre.
* ``departamento`` nombre del departamento.

Valores monetarios en **miles de pesos corrientes** (p. ej. el valor agregado
total de 2024 suma ~1,48e11, es decir ~148 billones de pesos). Para comparar
entre años hay que deflactar (``dd.eam.deflactar``).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from .._io import read_table
from ..referencias import DEPARTAMENTOS

log = logging.getLogger("dane_data.eam")

# Variables presentes en TODOS los años 1992–2024 (más algunas desde 2000).
VARIABLES_COMUNES = [
    "nordemp", "nordest", "dpto", "periodo",
    "prodbr2", "prodbind", "consin2", "valagri", "valorven", "valorcom",
    "pertotal", "persocu", "persoesc", "pertem3", "pperytem",
    "salarper", "pressper", "salpeyte", "prespyte",
    "activfi", "invebrta", "eelec",
]
VARIABLES_DESDE_2000 = ["totalv", "deprecia"]
CORE = VARIABLES_COMUNES + VARIABLES_DESDE_2000

ETIQUETAS = {
    "nordemp": "Identificador de la empresa",
    "nordest": "Identificador del establecimiento (planta)",
    "dpto": "Departamento",
    "periodo": "Año de referencia",
    "prodbr2": "Producción bruta",
    "prodbind": "Producción industrial",
    "consin2": "Consumo intermedio",
    "valagri": "Valor agregado",
    "valorven": "Ventas totales",
    "valorcom": "Compras de materias primas, materiales y empaques",
    "pertotal": "Personal total (permanente + propietarios + temporal directo + agencias)",
    "persocu": "Empleados permanentes",
    "persoesc": "Empleados permanentes + propietarios",
    "pertem3": "Empleados temporales directos",
    "pperytem": "Empleados permanentes y temporales directos",
    "salarper": "Salarios de empleados permanentes",
    "pressper": "Prestaciones de empleados permanentes",
    "salpeyte": "Salarios de empleados permanentes y temporales",
    "prespyte": "Prestaciones de empleados permanentes y temporales",
    "activfi": "Activos fijos",
    "invebrta": "Inversión bruta",
    "eelec": "Energía eléctrica consumida (kWh)",
    "totalv": "Valor de otros energéticos consumidos",
    "deprecia": "Depreciación",
}

# Nombres de división (2 dígitos) por revisión de la CIIU.
SECTORES = {
    4: {
        "10": "Alimentos", "11": "Bebidas", "12": "Tabaco", "13": "Textiles",
        "14": "Prendas de vestir", "15": "Cuero y calzado", "16": "Madera", "17": "Papel y cartón",
        "18": "Impresión", "19": "Refinación de petróleo", "20": "Químicos", "21": "Farmacéuticos",
        "22": "Caucho y plástico", "23": "Minerales no metálicos", "24": "Metalurgia básica",
        "25": "Productos de metal", "26": "Electrónicos y ópticos", "27": "Equipo eléctrico",
        "28": "Maquinaria y equipo", "29": "Vehículos automotores", "30": "Otro equipo de transporte",
        "31": "Muebles", "32": "Otras manufacturas", "33": "Reparación e instalación de maquinaria",
        "58": "Edición (publicaciones)", "59": "Cine, video y música", "73": "Publicidad",
    },
    3: {
        "15": "Alimentos y bebidas", "16": "Tabaco", "17": "Textiles", "18": "Prendas de vestir",
        "19": "Cuero y calzado", "20": "Madera", "21": "Papel y cartón", "22": "Edición e impresión",
        "23": "Refinación de petróleo", "24": "Químicos", "25": "Caucho y plástico",
        "26": "Minerales no metálicos", "27": "Metalurgia básica", "28": "Productos de metal",
        "29": "Maquinaria y equipo", "30": "Maquinaria de oficina", "31": "Aparatos eléctricos",
        "32": "Radio, TV y comunicaciones", "33": "Instrumentos médicos y de precisión",
        "34": "Vehículos automotores", "35": "Otro equipo de transporte", "36": "Muebles y otras manufacturas",
        "37": "Reciclaje",
    },
    2: {
        "31": "Alimentos, bebidas y tabaco", "32": "Textiles, confecciones y cuero",
        "33": "Madera y muebles", "34": "Papel e imprentas", "35": "Químicos, petróleo, caucho y plástico",
        "36": "Minerales no metálicos", "37": "Metálicas básicas", "38": "Productos metálicos y maquinaria",
        "39": "Otras manufacturas",
    },
}

_CIIU_COL = re.compile(r"^ciiu(_?\d)?(n\d)?$")


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("eam")


def _data_dir(root: Path) -> Path:
    return root / "datos" if (root / "datos").is_dir() else root


def find_files(years: Iterable[int] | int | None = None, root=None) -> dict[int, Path]:
    """``{año: archivo}`` de los datos EAM descargados (ignora el módulo TIC)."""
    base = _data_dir(_root(root))
    if not base.is_dir():
        return {}
    if years is not None:
        years = {int(y) for y in ([years] if isinstance(years, (int, str)) else years)}
    out = {}
    for ydir in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(ydir.name)
        if years is not None and anio not in years:
            continue
        files = sorted(f for f in ydir.iterdir() if f.is_file() and f.suffix.lower() in (".csv", ".txt"))
        if files:
            out[anio] = max(files, key=lambda f: f.stat().st_size)
    return out


def available(root=None) -> pd.DataFrame:
    rows = [{"anio": y, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
            for y, f in find_files(root=root).items()]
    return pd.DataFrame(rows, columns=["anio", "archivo", "tamano_mb"])


def _ciiu_rev(colname: str, anio: int) -> int:
    m = re.search(r"ciiu_?(\d)", colname)
    if m:  # ciiu2, ciiu3, ciiu4, ciiu_4, ciiu2n4 -> el dígito tras 'ciiu'
        return int(m.group(1))
    return 2 if anio <= 1999 else 3 if anio <= 2011 else 4


def harmonize(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    df = df.copy()
    ciiu_cols = [c for c in df.columns if _CIIU_COL.match(c)]
    if ciiu_cols:
        col = ciiu_cols[0]
        codes = pd.to_numeric(df[col], errors="coerce")
        rev = _ciiu_rev(col, anio)
        # Los nombres originales cambian cada época; quedan unificados en `ciiu`.
        df = df.drop(columns=ciiu_cols)
        # Sin ceros a la izquierda: por anonimización algunos años publican el
        # código a 2 o 3 dígitos (p. ej. "20", "110"); los 2 primeros siempre son la división.
        df["ciiu"] = codes.astype("Int64").astype("string")
        df["ciiu_rev"] = rev
    else:
        df["ciiu"] = pd.NA
        df["ciiu_rev"] = pd.NA
    df["division"] = df["ciiu"].str[:2]
    rev = df["ciiu_rev"].iloc[0] if len(df) else None
    df["sector"] = df["division"].map(SECTORES.get(rev, {}))
    dpto = pd.to_numeric(df.get("dpto"), errors="coerce")
    df["departamento"] = dpto.map(DEPARTAMENTOS) if dpto is not None else pd.NA
    df.insert(0, "anio", anio)
    return df


def load(
    years: Iterable[int] | int | None = None,
    columns="core",
    harmonize_vars: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Carga la EAM (un establecimiento-año por fila).

    Parámetros
    ----------
    years : año, lista/rango de años o None (todos los disponibles).
    columns : ``"core"`` (variables comparables entre años, por defecto),
        ``"all"`` o lista de variables extra (minúscula o mayúscula),
        p. ej. ``["c3r10c1", "c4r5c1"]``.

    >>> eam = dd.eam.load(range(2014, 2025))
    >>> dd.eam.resumen(eam, por=["anio", "sector"])
    """
    files = find_files(years, root=root)
    if not files:
        raise FileNotFoundError(
            f"No hay datos EAM para años={years} en {_root(root)}. "
            "Descárguelos con dane_data.eam.download(...) o revise dane_data.set_paths(...)."
        )
    if columns == "all":
        selector = None
    else:
        wanted = set(CORE) | ({c.lower() for c in columns} if columns not in (None, "core") else set())
        selector = lambda c: c in wanted or bool(_CIIU_COL.match(c))  # noqa: E731

    frames = []
    for i, (anio, path) in enumerate(sorted(files.items())):
        if progress:
            progress(i / len(files), f"Leyendo EAM {anio}")
        df = read_table(path, columns=selector, case="lower")
        frames.append(harmonize(df, anio) if harmonize_vars else df.assign(anio=anio))
    if progress:
        progress(1.0, "Listo")
    out = pd.concat(frames, ignore_index=True, sort=False)
    for c in ("nordemp", "nordest"):
        if c in out.columns:
            out[c] = pd.to_numeric(out[c], errors="coerce").astype("Int64")
    return out
