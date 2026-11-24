"""
Carga de la Encuesta de Micronegocios (EMICRON): un micronegocio por fila.

Los módulos de cada año quedan en ``<raíz>/datos/<año>/<módulo>.csv`` (ver ``downloader``). Todos tienen una fila
por micronegocio, con la clave ``DIRECTORIO``, ``SECUENCIA_P`` y ``SECUENCIA_ENCUESTA`` (la del hogar y la persona
en la GEIH), salvo ``personal_ocupado``, que tiene una fila por trabajador.
"""

from __future__ import annotations

import logging
import warnings
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .. import config
from .._io import read_table
from ..stats import _enteros, _opciones
from ..referencias import DEPARTAMENTOS, MESES, strip_accents

log = logging.getLogger("dane_data.emicron")

# Módulos de la encuesta, en el orden del formulario. No todos existen todos los años (``EMICRON_KNOWN_FILES``).
MODULOS = {
    "identificacion": "Identificación y clasificación económica",
    "emprendimiento": "Emprendimiento",
    "sitio": "Sitio o ubicación",
    "propietario": "Personal ocupado (propietario)",
    "personal_ocupado": "Personal ocupado (trabajadores, socios y familiares)",
    "caracteristicas": "Características del micronegocio",
    "tic": "Tecnologías de la información y las comunicaciones (TIC)",
    "inclusion_financiera": "Inclusión financiera",
    "costos": "Costos, gastos y activos",
    "ventas": "Ventas o ingresos",
    "capital_social": "Capital social",
    "covid": "Expectativas adaptativas (COVID-19), solo 2020",
    "fex_ajustado": "Factor de expansión ajustado (serie vigente 2019–2021)",
    "fex_dpto": "Factor de expansión departamental",
}
FACTORES = ("fex_ajustado", "fex_dpto")


def _root(root) -> Path:
    return Path(root).expanduser() if root is not None else config.get_path("emicron")


def find_files(years: Iterable[int] | int | None = None, root=None) -> dict[int, dict[str, Path]]:
    """
    Archivos descargados de cada año de la EMICRON.

    Parámetros
    ----------
    years
        Año o lista de años. ``None`` para todos.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("emicron")``).

    Devuelve
    --------
    dict
        ``{año: {módulo: ruta}}``, solo con los años que tienen el módulo de identificación.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.emicron.find_files(2024)[2024]["ventas"]  # doctest: +SKIP
    PosixPath('/home/ana/dane_data_datos/emicron/datos/2024/ventas.csv')
    """
    base = _root(root) / "datos"
    if not base.is_dir():
        return {}
    anios = _enteros(years)
    out = {}
    for carpeta in sorted(p for p in base.iterdir() if p.is_dir() and p.name.isdigit()):
        anio = int(carpeta.name)
        if anios is not None and anio not in anios:
            continue
        modulos = {m: carpeta / f"{m}.csv" for m in MODULOS if (carpeta / f"{m}.csv").is_file()}
        if "identificacion" in modulos:
            out[anio] = modulos
    return out


def available(root=None) -> pd.DataFrame:
    """
    Tabla de los módulos de la EMICRON descargados.

    Parámetros
    ----------
    root
        Carpeta raíz. Por defecto, la configurada.

    Devuelve
    --------
    DataFrame
        Una fila por año y módulo con ``anio``, ``modulo``, ``archivo`` y ``tamano_mb``.

    Véase también
    -------------
    download : Descargar lo que falta.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.emicron.available().groupby("anio").size()  # doctest: +SKIP
    """
    filas = [{"anio": a, "modulo": m, "archivo": f.name, "tamano_mb": round(f.stat().st_size / 1e6, 1)}
             for a, modulos in find_files(root=root).items() for m, f in modulos.items()]
    return pd.DataFrame(filas, columns=["anio", "modulo", "archivo", "tamano_mb"])


# ---------------------------------------------------------------------------------------------------- #
# Carga
# ---------------------------------------------------------------------------------------------------- #
CLAVE = ["directorio", "secuencia_p", "secuencia_encuesta"]

# Lo que repiten los módulos (y el factor de 2021 en inclusión financiera): viene una sola vez, de la identificación
_REPETIDAS = {"clase_te", "clase", "cod_depto", "area", "f_exp", "fex_c"}

_CLASE = {1: "Cabeceras municipales", 2: "Centros poblados y rural disperso"}
_SEXO = {1: "Hombre", 2: "Mujer"}
_SITUACION = {1: "Patrón o empleador", 2: "Trabajador por cuenta propia"}
_ACTIVIDAD = {1: "Agricultura, ganadería, caza, silvicultura y pesca", 2: "Industria manufacturera", 3: "Comercio",
              4: "Servicios", 5: "No informa"}
_ACTIVIDAD12 = {
    1: "Agricultura, ganadería, caza, silvicultura y pesca", 2: "Minería", 3: "Industria manufacturera",
    4: "Construcción", 5: "Comercio y reparación de vehículos automotores y motocicletas",
    6: "Transporte y almacenamiento", 7: "Alojamiento y servicios de comida", 8: "Información y comunicaciones",
    9: "Actividades inmobiliarias, profesionales y servicios administrativos", 10: "Educación",
    11: "Actividades de atención a la salud humana y de asistencia social",
    12: "Actividades artísticas, de entretenimiento, de recreación y otras actividades de servicios", 13: "No informa",
}
# Las etiquetas de los anexos del DANE, no las del formulario
_SITIO = {1: "En la vivienda", 2: "Local, tienda, taller, fábrica, oficina, consultorio",
          3: "De puerta en puerta o a domicilio", 4: "Ambulante sitio al descubierto", 5: "Vehículo con o sin motor",
          6: "Obra o construcción", 7: "Finca", 8: "Otro"}
_SALUD_PENSION = {1: "Salud y pensión", 2: "No aportó", 3: "Solo salud", 4: "Solo pensión"}
_TIPO = {1: "Trabajador remunerado", 2: "Socio", 3: "Trabajador o familiar sin remuneración"}
CIUDADES = {
    5: "Medellín A.M.", 8: "Barranquilla A.M.", 11: "Bogotá D.C.", 13: "Cartagena", 15: "Tunja", 17: "Manizales A.M.",
    18: "Florencia", 19: "Popayán", 20: "Valledupar", 23: "Montería", 27: "Quibdó", 41: "Neiva", 44: "Riohacha",
    47: "Santa Marta", 50: "Villavicencio", 52: "Pasto", 54: "Cúcuta A.M.", 63: "Armenia", 66: "Pereira A.M.",
    68: "Bucaramanga A.M.", 70: "Sincelejo", 73: "Ibagué", 76: "Cali A.M.", 88: "San Andrés",
}
_SI_NO = {1: True, 2: False}
# Personal ocupado: la clave del micronegocio con los nombres corridos, y la persona en SECUENCIA_ENCUESTA
_CLAVE_PERSONAL = {"secuencia_encuesta": "orden", "secuencia_p": "secuencia_encuesta", "secuencia_ph": "secuencia_p"}


def _categoria(valores) -> pd.CategoricalDtype:
    return pd.CategoricalDtype(list(dict.fromkeys(valores)))


# Tipos fijos: así se conservan al unir años con pd.concat
CATEGORIAS = {
    "departamento": _categoria(DEPARTAMENTOS.values()),
    "ciudad": _categoria(CIUDADES.values()),
    "clase": _categoria(_CLASE.values()),
    "sexo": _categoria(_SEXO.values()),
    "situacion_empleo": _categoria(_SITUACION.values()),
    "actividad": _categoria(_ACTIVIDAD.values()),
    "actividad12": _categoria(_ACTIVIDAD12.values()),
    "sitio": _categoria(_SITIO.values()),
    "salud_pension": _categoria(_SALUD_PENSION.values()),
    "tipo": _categoria(_TIPO.values()),
}

# Variable armonizada -> (módulo, variable de origen, códigos). Sin códigos: número tal cual.
_ARMONIZADAS = {
    "cod_depto": ("identificacion", "cod_depto", None),
    "departamento": ("identificacion", "cod_depto", DEPARTAMENTOS),
    "area": ("identificacion", "area", None),
    "ciudad": ("identificacion", "area", CIUDADES),
    "clase": ("identificacion", "clase_te", _CLASE),
    "sexo": ("identificacion", "p35", _SEXO),
    "edad": ("identificacion", "p241", None),
    "situacion_empleo": ("identificacion", "p3033", _SITUACION),
    "actividad": ("identificacion", "grupos4", _ACTIVIDAD),
    "actividad12": ("identificacion", "grupos12", _ACTIVIDAD12),
    "rut": ("caracteristicas", "p1633", _SI_NO),
    "camara_comercio": ("caracteristicas", "p1055", _SI_NO),
    "salud_pension": ("propietario", "p3088", _SALUD_PENSION),
    "sitio": ("sitio", "p3053", _SITIO),
}
_PERSONAL = {"trabajadores_remunerados": "p3032_1", "socios": "p3032_2", "familiares_sin_remuneracion": "p3032_3"}
# Montos mensuales en pesos, con el nombre del DANE. 2019 no los trae.
MONTOS = {
    "ventas_mes_anterior": "ventas", "consumo_intermedio": "costos", "valor_agregado": "ventas",
    "ingreso_mixto": "ventas", "sueldos": "propietario", "prestaciones": "propietario",
    "remuneracion_total": "propietario",
}

CORE = [*CLAVE, "anio", "mes_ref", "cod_depto", "departamento", "area", "ciudad", "clase", "sexo", "edad",
        "situacion_empleo", "actividad", "actividad12", *_PERSONAL, "personal_ocupado", "fex", "fex_dpto", "rut",
        "camara_comercio", "salud_pension", "sitio", *MONTOS]

ETIQUETAS = {
    "directorio": "Vivienda en la GEIH (clave)", "secuencia_p": "Hogar en la GEIH (clave)",
    "secuencia_encuesta": "Persona en la GEIH, el propietario (clave)", "anio": "Año de la encuesta",
    "mes_ref": "Mes de referencia (1–12)", "cod_depto": "Código DANE del departamento",
    "departamento": "Departamento", "area": "Código de la ciudad o área metropolitana (24 ciudades)",
    "ciudad": "Ciudad o área metropolitana (vacío fuera de las 24 ciudades)",
    "clase": "Cabeceras municipales o centros poblados y rural disperso", "sexo": "Sexo del propietario",
    "edad": "Edad del propietario", "situacion_empleo": "Situación en el empleo del propietario",
    "actividad": "Actividad económica, 4 grupos (CIIU Rev. 4)", "actividad12": "Actividad económica, 12 grupos",
    "trabajadores_remunerados": "Trabajadores que reciben un pago", "socios": "Socios",
    "familiares_sin_remuneracion": "Trabajadores o familiares sin remuneración",
    "personal_ocupado": "Personal ocupado: el propietario más trabajadores remunerados, socios y familiares",
    "fex": "Factor de expansión de la serie vigente (ajustado en 2019–2021)",
    "fex_dpto": "Factor de expansión para cifras por departamento (vacío en 2025)", "rut": "Tiene Registro Único Tributario (RUT)",
    "camara_comercio": "Registrado en una Cámara de Comercio",
    "salud_pension": "Aporte del propietario a salud y pensión el mes anterior",
    "sitio": "Sitio o ubicación principal del negocio",
    "ventas_mes_anterior": "Ventas o ingresos del mes anterior (pesos)",
    "consumo_intermedio": "Consumo intermedio mensual (pesos)", "valor_agregado": "Valor agregado mensual (pesos)",
    "ingreso_mixto": "Ingreso mixto mensual (pesos)", "sueldos": "Sueldos y salarios mensuales (pesos)",
    "prestaciones": "Prestaciones sociales mensuales (pesos)",
    "remuneracion_total": "Remuneración total mensual del personal ocupado (pesos)",
}

_MESES = {strip_accents(nombre): numero for numero, nombre in MESES.items()}
_ORIGEN_CORE = {m: {v for (mod, v, _) in _ARMONIZADAS.values() if mod == m} for m in MODULOS}
_ORIGEN_CORE["identificacion"] |= {"clase", "mes_ref", "f_exp", *_PERSONAL.values()}
for _monto, _mod in MONTOS.items():
    _ORIGEN_CORE[_mod].add(_monto)


def _codigos(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").round().astype("Int64")


def _mapear(s: pd.Series, mapa: dict, nombre: str, anio: int) -> pd.Series:
    codigos = _codigos(s)
    out = codigos.map(mapa)
    if (sin := codigos.notna() & out.isna()).any():
        log.warning(f"EMICRON {anio}: {nombre} trae códigos sin categoría ({', '.join(map(str, sorted(codigos[sin].unique())[:5]))}); "
                    "quedan vacíos.")
    if nombre in CATEGORIAS:
        return out.astype(CATEGORIAS[nombre])
    return out.astype("boolean")


def _mes(s: pd.Series, anio: int) -> pd.Series:
    texto = s.astype("string").str.strip().map(lambda x: strip_accents(x) if isinstance(x, str) else x)
    numero = pd.to_numeric(texto, errors="coerce")
    out = texto.map(_MESES).astype("Float64").fillna(numero).astype("Int64")
    if (sin := s.notna() & out.isna()).any():
        log.warning(f"EMICRON {anio}: MES_REF sin mes reconocible ({', '.join(map(repr, s[sin].unique()[:3]))}).")
    return out


def _con_clave(df: pd.DataFrame, origen: Path) -> pd.DataFrame:
    if faltan := [c for c in CLAVE if c not in df.columns]:
        raise ValueError(f"{origen}: falta la clave {', '.join(faltan).upper()}.")
    df = df.dropna(subset=CLAVE)
    return df.astype({c: "int64" for c in CLAVE})


def _factor(path: Path, anio: int) -> pd.Series:
    """El factor de un archivo de factores, indexado por la clave: sin filas vacías ni duplicadas."""
    df = _con_clave(read_table(path, case="lower"), path)
    col = next((c for c in ("fex_c", "fex_micro_dpto") if c in df.columns), None)
    if col is None:
        raise ValueError(f"{path}: no se encontró el factor (FEX_C o FEX_MICRO_DPTO).")
    # 2020 repite una clave con el factor vacío, y los departamentales traen micronegocios que no están en los módulos
    df = df.dropna(subset=[col]).drop_duplicates(subset=[*CLAVE, col])
    if df.duplicated(CLAVE).any():
        raise ValueError(f"{path}: hay micronegocios con dos factores distintos; no se puede saber cuál usar.")
    return df.set_index(CLAVE)[col].astype("float64")


def _selector(modulo: str, columns, extras: set[str]):
    if columns == "all":
        return None
    quiero = set(CLAVE) | _ORIGEN_CORE.get(modulo, set()) | extras
    return lambda c: c in quiero


def _leer_anio(anio: int, archivos: dict[str, Path], modulos: list[str], columns, extras: set[str]) -> pd.DataFrame:
    df = _con_clave(read_table(archivos["identificacion"], columns=_selector("identificacion", columns, extras),
                               case="lower"), archivos["identificacion"])
    df = df.rename(columns={"clase": "clase_te"})  # 2019
    for m in modulos:
        if m == "identificacion":
            continue
        if m not in archivos:
            from .downloader import EMICRON_KNOWN_FILES  # aquí: el descargador importa este módulo
            motivo = (f"no está descargado: use dane_data.emicron.download({anio})" if (anio, m) in EMICRON_KNOWN_FILES
                      else "el DANE no lo aplicó ese año")
            warnings.warn(f"EMICRON {anio}: sin el módulo {m} ({motivo}); sus variables quedan vacías.", UserWarning,
                          stacklevel=3)
            continue
        mod = _con_clave(read_table(archivos[m], columns=_selector(m, columns, extras), case="lower"), archivos[m])
        mod = mod.drop(columns=[c for c in mod.columns if c in _REPETIDAS or (c in df.columns and c not in CLAVE)])
        df = df.merge(mod, on=CLAVE, how="left", validate="one_to_one")
    clave = pd.MultiIndex.from_frame(df[CLAVE])
    if anio <= 2021 and "fex_ajustado" in archivos:
        df["fex"] = _factor(archivos["fex_ajustado"], anio).reindex(clave).to_numpy()
    else:
        if anio <= 2021:
            warnings.warn(f"EMICRON {anio}: falta el factor ajustado; fex es el F_EXP de la serie anterior y los totales "
                          f"no coinciden con los anexos vigentes. Descárguelo con dane_data.emicron.download({anio}).",
                          UserWarning, stacklevel=3)
        df["fex"] = pd.to_numeric(df["f_exp"], errors="coerce")
    df["fex_dpto"] = (_factor(archivos["fex_dpto"], anio).reindex(clave).to_numpy() if "fex_dpto" in archivos
                      else np.nan)
    from .downloader import EMICRON_KNOWN_FILES  # aquí: el descargador importa este módulo
    if "fex_dpto" not in archivos and (anio, "fex_dpto") in EMICRON_KNOWN_FILES:  # 2025 no lo tiene en el ANDA
        warnings.warn(f"EMICRON {anio}: falta el factor departamental; fex_dpto queda vacío. Descárguelo con "
                      f"dane_data.emicron.download({anio}).", UserWarning, stacklevel=3)
    return harmonize(df, anio)


def harmonize(df: pd.DataFrame, anio: int) -> pd.DataFrame:
    """
    Agrega las variables armonizadas a un año de la EMICRON.

    Parámetros
    ----------
    df
        Un año, con los módulos ya unidos por la clave y los nombres en minúscula; ``fex`` y ``fex_dpto`` ya puestos.
    anio
        Año de los datos.

    Devuelve
    --------
    DataFrame
        Una copia con ``anio``, ``mes_ref`` y las variables de ``CORE`` que se pueden armar con las columnas que hay;
        las demás quedan vacías. Las categorías usan los tipos de ``CATEGORIAS``.

    Véase también
    -------------
    load : Carga y armoniza.
    """
    df = df.copy()
    df.insert(0, "anio", anio)
    df["mes_ref"] = _mes(df["mes_ref"], anio) if "mes_ref" in df.columns else pd.array([pd.NA] * len(df), "Int64")
    nuevas = {}
    for nombre, (_, origen, mapa) in _ARMONIZADAS.items():
        if origen not in df.columns:
            nuevas[nombre] = (pd.Series(pd.NA, index=df.index, dtype=CATEGORIAS.get(nombre, "boolean")) if mapa
                              else pd.Series(pd.NA, index=df.index, dtype="Int64"))
        elif mapa is None:
            nuevas[nombre] = _codigos(df[origen])
        else:
            nuevas[nombre] = _mapear(df[origen], mapa, nombre, anio)
    for nombre, origen in _PERSONAL.items():
        # Vacío cuando el propietario trabaja solo (P3031 = 2): cero personas
        nuevas[nombre] = _codigos(df[origen]).fillna(0) if origen in df.columns else pd.Series(0, index=df.index, dtype="Int64")
    nuevas["personal_ocupado"] = 1 + sum(nuevas[n] for n in _PERSONAL)
    for monto in MONTOS:
        nuevas[monto] = pd.to_numeric(df[monto], errors="coerce").astype("float64") if monto in df.columns else np.nan
    # Las de origen con el mismo nombre (cod_depto, area, montos) se reemplazan por la versión armonizada
    df = df.drop(columns=[c for c in nuevas if c in df.columns])
    return pd.concat([df, pd.DataFrame(nuevas, index=df.index)], axis=1)


def load(
    years: Iterable[int] | int | None = None,
    modulos: Iterable[str] | str | None = None,
    columns="core",
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Carga la EMICRON: un micronegocio por fila, con los módulos unidos y las variables armonizadas.

    Parámetros
    ----------
    years
        Año, lista o rango de años. ``None`` para todos los descargados.
    modulos
        Módulo o lista de módulos que se unen a la identificación (claves de ``MODULOS``, salvo
        ``personal_ocupado``, que tiene una fila por persona: vea ``load_personal``). ``None`` para todos los que
        estén descargados.
    columns
        ``"core"`` (las de ``CORE``, con el mismo esquema todos los años; por defecto), ``"all"`` (todas las de los
        módulos, con su nombre del DANE en minúscula, más las de ``CORE``) o una lista de variables del DANE que se
        agregan a ``CORE``, por ejemplo ``["p3051", "P3034"]``.
    root
        Carpeta raíz. Por defecto, la configurada (``dd.get_path("emicron")``).
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Una fila por micronegocio con ``anio``, la clave (``directorio``, ``secuencia_p``, ``secuencia_encuesta``,
        la de la persona propietaria en la GEIH) y las variables pedidas. Los montos están en pesos corrientes del
        mes de referencia.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.
    ValueError
        Si un módulo no es una clave de ``MODULOS``, o una variable pedida en ``columns`` no está en ningún módulo
        cargado.

    Véase también
    -------------
    indicadores : Número de micronegocios, personal ocupado, ventas y valor agregado como los anexos del DANE.
    load_personal : Detalle de los trabajadores, socios y familiares.
    dane_data.tabla : Tablas ponderadas de cualquier variable (use ``peso="fex"``).

    Notas
    -----
    El peso es ``fex``: el factor ajustado en 2019–2021 y el ``F_EXP`` de la identificación desde 2022. Con él los
    totales coinciden con los anexos vigentes del DANE. Para cifras por departamento use ``fex_dpto``.

    El factor es anual: la suma de ``fex`` en los 12 meses es el total del año. Por eso el mes se llama ``mes_ref`` y
    no ``mes``: ``dd.tabla`` promedia los meses cuando hay una columna ``mes`` (como en la GEIH).

    2019 no trae ventas, consumo intermedio, valor agregado, ingreso mixto ni remuneraciones calculados: quedan
    vacíos. Los microdatos de 2025 solo cubren las 24 ciudades principales (se avisa al cargarlos). Algunos módulos
    no existen todos los años (``download``) o no cubren todos los micronegocios: el COVID de 2020 y la inclusión
    financiera de 2021 dejan vacías las filas de los que no respondieron.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> emi = dd.emicron.load(2024)  # doctest: +SKIP
    >>> dd.tabla(emi, por="actividad", estadistico="porcentaje")  # doctest: +SKIP
    """
    files = find_files(years, root=root)
    if not files:
        raise FileNotFoundError(
            f"No hay datos de la EMICRON para años={years} en {_root(root)}. "
            "Descárguelos con dane_data.emicron.download(...) o revise dane_data.set_paths(...)."
        )
    # Los factores se leen siempre y aparte (_factor quita sus filas vacías o repetidas): no se unen como un módulo
    pedidos = None if modulos is None else [m for m in _opciones(modulos, MODULOS, "Módulo") if m not in FACTORES]
    if pedidos is not None and "personal_ocupado" in pedidos:
        raise ValueError("personal_ocupado tiene una fila por persona: cárguelo con dane_data.emicron.load_personal.")
    if isinstance(columns, str) and columns not in ("core", "all"):
        columns = [columns]  # un solo nombre: list("p3051") lo partiría en letras
    extras = set() if columns in ("core", "all") else {c.lower() for c in columns}

    frames = []
    for i, (anio, archivos) in enumerate(sorted(files.items())):
        if progress:
            progress(i / len(files), f"Leyendo EMICRON {anio}")
        unir = pedidos if pedidos is not None else [m for m in archivos if m not in FACTORES and m != "personal_ocupado"]
        frames.append(_leer_anio(anio, archivos, unir, columns, extras))
    if progress:
        progress(1.0, "Listo")
    out = pd.concat(frames, ignore_index=True, sort=False)
    if faltan := sorted(extras - set(out.columns)):
        raise ValueError(f"Variables que no están en los módulos cargados: {', '.join(faltan)}. "
                         "Búsquelas con dane_data.diccionario('emicron').")
    if 2025 in files:
        warnings.warn("Los microdatos de la EMICRON 2025 solo cubren las 24 ciudades principales: sus totales no son "
                      "nacionales, y no traen factor departamental (fex_dpto queda vacío).", UserWarning, stacklevel=2)
    if columns == "all":
        return out
    return out[[*CORE, *[c for c in out.columns if c in extras and c not in CORE]]]


def load_personal(years: Iterable[int] | int | None = None, root=None) -> pd.DataFrame:
    """
    Carga el módulo de personal ocupado: una fila por trabajador, socio o familiar.

    Parámetros
    ----------
    years
        Año, lista o rango de años. ``None`` para todos los descargados.
    root
        Carpeta raíz. Por defecto, la configurada.

    Devuelve
    --------
    DataFrame
        Las variables del módulo con su nombre del DANE en minúscula, ``anio``, la clave del micronegocio, ``orden``
        (la persona dentro del micronegocio), ``tipo`` (categoría) y, del micronegocio, ``fex``, ``clase``,
        ``ciudad``, ``departamento`` y ``actividad``.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos del módulo para esos años.

    Notas
    -----
    En este módulo el DANE corre los nombres de la clave: su ``SECUENCIA_PH`` es el ``SECUENCIA_P`` (hogar) de los
    demás módulos, su ``SECUENCIA_P`` es el ``SECUENCIA_ENCUESTA`` (propietario) y su ``SECUENCIA_ENCUESTA`` numera
    a las personas del micronegocio. Aquí quedan con los nombres de los demás módulos, y el número de la persona en
    ``orden``.

    Hay una fila por persona ocupada distinta del propietario, y ``fex`` es el del micronegocio: sumado por ``tipo``
    da casi lo mismo que ``trabajadores_remunerados``, ``socios`` y ``familiares_sin_remuneracion`` de ``load``. Para
    los totales del DANE use esas tres.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> per = dd.emicron.load_personal(2024)  # doctest: +SKIP
    >>> dd.tabla(per, por=["tipo", "p3077"])  # doctest: +SKIP
    """
    files = {a: f for a, f in find_files(years, root=root).items() if "personal_ocupado" in f}
    if not files:
        raise FileNotFoundError(f"No hay datos del módulo de personal ocupado de la EMICRON para años={years} en "
                                f"{_root(root)}. Descárguelos con dane_data.emicron.download(...).")
    micro = ["anio", *CLAVE, "fex", "clase", "ciudad", "departamento", "actividad"]
    frames = []
    for anio, archivos in sorted(files.items()):
        per = read_table(archivos["personal_ocupado"], case="lower")
        per = _con_clave(per.rename(columns=_CLAVE_PERSONAL), archivos["personal_ocupado"]).astype({"orden": "Int64"})
        per = per.drop(columns=[c for c in per.columns if c in _REPETIDAS])
        per["tipo"] = _mapear(per["tipo"], _TIPO, "tipo", anio) if "tipo" in per.columns else pd.NA
        base = _leer_anio(anio, archivos, [], "core", set())[micro]
        frames.append(base.merge(per, on=CLAVE, how="right", validate="one_to_many"))
    return pd.concat(frames, ignore_index=True, sort=False)
