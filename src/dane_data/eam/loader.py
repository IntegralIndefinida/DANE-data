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
* ``microagregado`` si los valores del registro son el promedio de un grupo de
                establecimientos y no los propios; ``grupo_microagregacion``
                numera el grupo dentro del año.

Valores monetarios en **miles de pesos corrientes** (p. ej. el valor agregado
total de 2024 suma ~1,48e11, es decir ~148 billones de pesos). Para comparar
entre años hay que deflactar (``dd.eam.deflactar``).
"""

from __future__ import annotations

import logging
import numbers
import re
from pathlib import Path
from typing import Iterable

import pandas as pd

from .. import config
from .._io import read_table
from ..referencias import DEPARTAMENTOS

log = logging.getLogger("dane_data.eam")

# Formatos de los archivos de datos: CSV, TXT delimitado (2023) o Stata (2024), todos leídos con _io.read_table
EXTENSIONES = (".csv", ".txt", ".dta")

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

# Lo que no entra en la clave de la microagregación: identificadores, y las ventas, que a veces difieren
# dentro de un grupo (1 de 541 grupos en 2024).
_FUERA_DE_LA_CLAVE = {"nordemp", "nordest", "dpto", "periodo", "valorven"}


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("eam")


def _data_dir(root: Path) -> Path:
    return root / "datos" if (root / "datos").is_dir() else root


def find_files(years: Iterable[int] | int | None = None, root=None) -> dict[int, Path]:
    """
    Archivo de datos de cada año de la EAM descargado.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("eam")``).

    Devuelve
    --------
    dict
        ``{año: ruta}``. Si un año tiene varios archivos se usa el más grande, con CSV o TXT antes que
        Stata; el módulo TIC se ignora.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eam.find_files(2024)  # doctest: +SKIP
    {2024: PosixPath('/home/ana/datos/EAM/datos/2024/EAM_ANONIMIZADA_2024.txt')}
    """
    base = _data_dir(_root(root))
    if not base.is_dir():
        return {}
    if years is not None:
        # numbers.Integral: también un año de numpy (eam.anio.max())
        years = {int(y) for y in ([years] if isinstance(years, (numbers.Integral, str)) else years)}
    out = {}
    for ydir in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(ydir.name)
        if years is not None and anio not in years:
            continue
        files = sorted(f for f in ydir.iterdir() if f.is_file() and f.suffix.lower() in EXTENSIONES)
        if files:
            # El texto primero (un .txt convertido por una versión anterior, junto al .dta); entre
            # archivos del mismo tipo, el más grande.
            out[anio] = max(files, key=lambda f: (f.suffix.lower() != ".dta", f.stat().st_size))
    return out


def available(root=None) -> pd.DataFrame:
    """
    Tabla de los años de la EAM descargados.

    Parámetros
    ----------
    root
        Carpeta raíz. Por defecto, la configurada.

    Devuelve
    --------
    DataFrame
        Una fila por año con ``anio``, ``archivo`` y ``tamano_mb``.

    Véase también
    -------------
    download : Descargar lo que falta.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eam.available().tail(3)  # doctest: +SKIP
        anio                   archivo  tamano_mb
    30  2022  EAM_ANONIMIZADA_2022.csv        9.1
    31  2023  EAM_ANONIMIZADA_2023.txt        9.0
    32  2024  EAM_ANONIMIZADA_2024.txt       14.0
    """
    rows =[{"anio": y, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
            for y, f in find_files(root=root).items()]
    return pd.DataFrame(rows, columns=["anio", "archivo", "tamano_mb"])


def _ciiu_rev(colname: str, anio: int) -> int:
    m = re.search(r"ciiu_?(\d)", colname)
    if m:  # ciiu2, ciiu3, ciiu4, ciiu_4, ciiu2n4 -> el dígito tras 'ciiu'
        return int(m.group(1))
    # Cortes según los códigos de los archivos, no según el ANDA: su documentación dice
    # Rev. 3 desde 2000 y Rev. 4 desde las cifras de 2013, pero el archivo de 2000 trae
    # códigos Rev. 2 y el de 2012 ya trae Rev. 4 (ver README).
    return 2 if anio <= 2000 else 3 if anio <= 2011 else 4


def _microagregacion(df: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """
    ``(microagregado, grupo_microagregacion)``. El ANDA reemplaza los valores de grupos de establecimientos
    del mismo departamento y CIIU por el promedio del grupo (deducido de los datos; el DANE no lo documenta,
    ver README). Se reconocen porque comparten todos los montos de ``CORE`` que haya, salvo las ventas.
    """
    montos = [c for c in CORE if c in df.columns and c not in _FUERA_DE_LA_CLAVE]
    if not montos:
        return pd.Series(False, index=df.index), pd.Series(pd.NA, index=df.index, dtype="Int64")
    clave = df[montos].apply(pd.to_numeric, errors="coerce")
    for c in ("dpto", "ciiu"):
        if c in df.columns:
            clave[f"_{c}"] = df[c]
    n = clave.groupby(list(clave.columns), dropna=False).ngroup()
    # Establecimientos distintos (un registro repetido no es un grupo) y con algún monto: plantas sin datos
    # coinciden en ceros sin estar agrupadas.
    plantas = df["nordest"] if "nordest" in df.columns else pd.Series(range(len(df)), index=df.index)
    agrupado = (plantas.groupby(n).transform("nunique") > 1) & clave[montos].fillna(0).ne(0).any(axis=1)
    return agrupado, n.where(agrupado).rank(method="dense").astype("Int64")


def harmonize(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """
    Agrega las variables armonizadas a los datos de un año.

    Parámetros
    ----------
    df
        Datos de un año de la EAM, con los nombres en minúscula.
    anio
        Año de los datos.

    Devuelve
    --------
    DataFrame
        Una copia de ``df`` con ``anio``, ``ciiu`` (texto), ``ciiu_rev`` (2, 3 o 4), ``division`` (los dos
        primeros dígitos), ``sector`` (nombre de la división, de ``SECTORES``),
        ``departamento``, ``microagregado`` (True o False) y ``grupo_microagregacion`` (número del grupo
        dentro del año; vacío si no está microagregado). Las columnas CIIU originales (``ciiu2``,
        ``ciiu3``, ``ciiu4``...) se reemplazan por ``ciiu``.

    Véase también
    -------------
    load : Carga y armoniza.

    Notas
    -----
    La revisión se deduce de la variable de origen (``ciiu2`` → Rev. 2, ``ciiu3`` → Rev. 3, ``ciiu4`` →
    Rev. 4). Algunos años publican el código a 2 o 3 dígitos por anonimización; los dos primeros son
    siempre la división.

    En los demás años, el ANDA anonimiza publicando muchos establecimientos grandes, de cualquier
    actividad, con el código residual de la revisión («otras industrias manufactureras»: 3909 en la
    Rev. 2, 3699 en la Rev. 3, 3290 en la Rev. 4), así que su ``division`` puede no ser la real. El código
    se deja como lo publica el ANDA (ver README).

    Además, el ANDA **microagrega**: reemplaza los valores de grupos de establecimientos (casi siempre 3)
    del mismo departamento y CIIU por el promedio del grupo. ``microagregado`` marca los registros que
    comparten exactamente todos los montos de ``CORE`` presentes, salvo las ventas (``valorven``), con otro
    establecimiento del mismo departamento y CIIU. Es una deducción de los datos, que el DANE no ha
    confirmado. Las sumas no cambian, pero esos valores no son los del establecimiento.
    """
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
    # Lo publicado como 3290 (o 3909, 3699) no siempre es esa clase, aunque el DDI la describe como una más: el
    # ANDA esconde ahí la actividad de establecimientos grandes, y los anexos del DANE muestran muchos menos (ver
    # README). Se deja así, sin marcarlos ni deducir su actividad, para no deshacer la anonimización.
    if "dpto" in df.columns:
        df["departamento"] = pd.to_numeric(df["dpto"], errors="coerce").map(DEPARTAMENTOS)
    else:
        df["departamento"] = pd.NA
    df["microagregado"], df["grupo_microagregacion"] = _microagregacion(df)
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
    Carga la EAM: un establecimiento-año por fila, con las variables armonizadas.

    Parámetros
    ----------
    years
        Año, lista o rango de años. ``None`` para todos los descargados.
    columns
        ``"core"`` (las de ``CORE``, comparables entre años; por defecto), ``"all"`` o una lista de
        variables extra en minúscula o mayúscula, por ejemplo ``["c3r10c1", "c4r5c1"]``.
    harmonize_vars
        Agregar ``ciiu``, ``ciiu_rev``, ``division``, ``sector``, ``departamento``, ``microagregado`` y
        ``grupo_microagregacion``. Si False, solo ``anio``.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Todas las variables en minúscula. Los montos están en miles de pesos corrientes.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.

    Véase también
    -------------
    resumen : Agregados por año, sector o departamento.
    panel : Panel de establecimientos.
    ETIQUETAS : Qué es cada variable de ``CORE``.

    Notas
    -----
    La CIIU cambia de revisión: Rev. 2 hasta 2000, Rev. 3 en 2001–2011 y Rev. 4 desde 2012. Los
    ``sector`` de revisiones distintas no son comparables sin una correlativa.

    Los totales nacionales y por departamento coinciden con los anexos del DANE, pero la composición por
    división no: para anonimizar, el ANDA publica la actividad de muchos establecimientos grandes con el
    código residual (3909, 3699 o 3290), que queda inflado (vea ``harmonize``). Para la composición por
    sector, use los anexos del DANE. Los registros ``microagregado`` traen el promedio de su grupo: sirven para
    agregados, no para análisis por establecimiento.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> eam = dd.eam.load(range(2022, 2025))  # doctest: +SKIP
    >>> eam[["anio", "ciiu", "ciiu_rev", "division", "sector", "departamento"]].head(3)  # doctest: +SKIP
       anio  ciiu  ciiu_rev division                  sector  departamento
    0  2022  1812         4       18               Impresión   Bogotá D.C.
    1  2022  2392         4       23  Minerales no metálicos  Cundinamarca
    2  2022  2429         4       24       Metalurgia básica     Antioquia
    """
    files = find_files(years, root=root)
    if not files:
        raise FileNotFoundError(
            f"No hay datos EAM para años={years} en {_root(root)}. "
            "Descárguelos con dane_data.eam.download(...) o revise dane_data.set_paths(...)."
        )
    if isinstance(columns, str) and columns not in ("core", "all"):
        columns = [columns]  # un solo nombre: list("valagri") lo partiría en letras
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
