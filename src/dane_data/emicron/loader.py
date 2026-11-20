"""
Carga de la Encuesta de Micronegocios (EMICRON): un micronegocio por fila.

Los módulos de cada año quedan en ``<raíz>/datos/<año>/<módulo>.csv`` (ver ``downloader``). Todos tienen una fila
por micronegocio, con la clave ``DIRECTORIO``, ``SECUENCIA_P`` y ``SECUENCIA_ENCUESTA`` (la del hogar y la persona
en la GEIH), salvo ``personal_ocupado``, que tiene una fila por trabajador.
"""

from __future__ import annotations

import numbers
from pathlib import Path
from typing import Iterable

import pandas as pd

from .. import config

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


def _modulo_valido(modulo: str) -> str:
    if modulo not in MODULOS:
        raise ValueError(f"Módulo desconocido {modulo!r}. Opciones: {', '.join(MODULOS)}")
    return modulo


def _anios(years) -> set[int] | None:
    if years is None:
        return None
    # numbers.Integral: también un año de numpy (df.anio.max())
    return {int(y) for y in ([years] if isinstance(years, (numbers.Integral, str)) else years)}


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
    anios = _anios(years)
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
