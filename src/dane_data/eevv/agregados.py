"""
Agregados de las Estadísticas Vitales calculados año por año y guardados en disco, y tasas sobre la población.

Un año de nacimientos pasa de 700 000 filas: así no hace falta tener toda la serie en memoria. La caché vive en
``~/.cache/dane_data/eevv/`` y se invalida sola si cambian los archivos o el código.
"""

from __future__ import annotations

import hashlib
import json
import logging
import numbers
import time
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

import numpy as np
import pandas as pd

from .. import config
from ..geih.agregados import _clave_json, _mascara
from ..geih.loader import _guardar_parquet, _usado
from ..proyecciones import poblacion
from .indicadores import _lista, indicadores
from .loader import _SIN_DETALLE, _avisar_cobertura, _root, _tipo_valido, _unir, find_files, load

log = logging.getLogger("dane_data.eevv")

_CACHE_DIAS = 90  # Días sin usarse tras los cuales un archivo de la caché se borra solo
_MIL = 1000

# Cómo se llama cada desagregación de las tasas en los certificados
_POR_TASAS = {"departamento": "departamento_residencia", "sexo": "sexo", "area": "area_residencia"}
_AREA_POBLACION = {"Cabecera": "Cabecera", "Centro poblado": "Centros poblados y rural disperso",
                   "Rural disperso": "Centros poblados y rural disperso", "Resto": "Centros poblados y rural disperso"}
_EDADES_FERTILES = [(a, a + 4) for a in range(15, 50, 5)]
_EDADES_MADRE = {f"De {a} a {a + 4} años": (a, a + 4) for a in range(10, 55, 5)}
_EDADES_DEFUNCION = {"Menor de 1 año": (0, 0), "De 1 a 4 años": (1, 4),
                     **{f"De {a} a {a + 4} años": (a, a + 4) for a in range(5, 85, 5)}, "De 85 años y más": (85, 100)}


@lru_cache(maxsize=1)
def _firma_codigo() -> str:
    """Hash de lo que produce los resultados: si cambia, la caché se recalcula sola."""
    from .. import __version__

    base = Path(__file__).resolve().parent.parent
    h = hashlib.sha1(__version__.encode())
    # stats.py (_con_categorias) y geih/agregados.py (_mascara, _clave_json) también dan forma a lo que se guarda
    for rel in ("eevv/loader.py", "eevv/indicadores.py", "eevv/agregados.py", "proyecciones.py", "referencias.py", "_io.py",
                "stats.py", "geih/agregados.py", "data/eevv_causas.json", "data/proyecciones_poblacion.parquet"):
        try:
            h.update((base / rel).read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:16]


def _firma_archivo(ruta: Path) -> str:
    estado = ruta.stat()
    return f"{ruta.name}|{estado.st_size}|{estado.st_mtime_ns}"


def clear_cache(dias: float | None = None) -> int:
    """
    Borra la caché de las Estadísticas Vitales.

    Nunca hace falta para tener resultados correctos, porque se invalida sola cuando cambian los datos o el código: sirve
    para liberar espacio.

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
    Lo que no se usa en 90 días se borra solo, revisando como mucho una vez al día.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.eevv.clear_cache()  # doctest: +SKIP
    57
    """
    limite = None if dias is None else time.time() - dias * 86400
    n = 0
    for f in (config.CACHE_DIR / "eevv").rglob("*"):
        if f.suffix not in (".parquet", ".tmp"):  # .tmp: escrituras que se interrumpieron
            continue
        try:
            if limite is None or f.stat().st_mtime < limite:
                f.unlink()
                n += 1
        except OSError:  # otra sesión lo borró o lo está usando
            pass
    return n


def _limpiar_cache_vieja() -> None:
    """``clear_cache(_CACHE_DIAS)``, como mucho una vez al día (la fecha del marcador dice cuándo fue la última)."""
    marcador = config.CACHE_DIR / "eevv" / ".ultima_limpieza"
    try:
        if marcador.exists() and time.time() - marcador.stat().st_mtime < 86400:
            return
        marcador.parent.mkdir(parents=True, exist_ok=True)
        marcador.touch()
    except OSError:
        return
    if n := clear_cache(_CACHE_DIAS):
        log.info(f"Caché: se borraron {n} archivos sin usar en {_CACHE_DIAS} días.")


def _desde_cache(ruta: Path, calcular: Callable[[], pd.DataFrame]) -> pd.DataFrame:
    if ruta.exists():
        try:
            tabla = pd.read_parquet(ruta)
            _usado(ruta)
            return tabla
        except Exception:  # caché corrupta: se regenera
            pass
    tabla = calcular()
    try:
        _guardar_parquet(tabla, ruta)
        _limpiar_cache_vieja()
    except Exception as e:  # disco lleno, sin permisos, etc.
        log.debug(f"No se pudo guardar caché {ruta}: {e}")
    return tabla


def _armonizado(tipo: str, anio: int, ruta: Path) -> pd.DataFrame:
    """Un año ya armonizado. Leerlo de la caché es unas diez veces más rápido que del archivo del DANE."""
    digest = hashlib.sha1("|".join([_firma_codigo(), _firma_archivo(ruta)]).encode()).hexdigest()[:16]

    def leer() -> pd.DataFrame:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # las funciones de este módulo avisan una sola vez
            return load(anio, tipo=tipo, root=ruta.parents[3])

    return _desde_cache(config.CACHE_DIR / "eevv" / tipo / "anios" / f"{anio}_{digest}.parquet", leer)


def _por_anio(tabla: str, anios, tipo: str, solicitud: dict, calcular: Callable[[pd.DataFrame], pd.DataFrame], root=None,
              progress=None) -> list[pd.DataFrame]:
    """``calcular(datos del año)`` para cada año, leído de la caché si ya se hizo con los mismos archivos y solicitud."""
    archivos = find_files(anios, tipo=_tipo_valido(tipo), root=root)
    if not archivos:
        raise FileNotFoundError(
            f"No hay datos de {tipo} para años={anios} en {_root(root)}. "
            "Descárguelos con dane_data.eevv.download(...) o revise dane_data.set_paths(...)."
        )
    texto = json.dumps(_clave_json(solicitud), sort_keys=True, default=str, ensure_ascii=False)
    partes = []
    for i, (anio, ruta) in enumerate(sorted(archivos.items())):
        if progress:
            progress(i / len(archivos), f"Calculando {tipo} {anio} (solo la primera vez)")
        digest = hashlib.sha1("|".join([_firma_codigo(), _firma_archivo(ruta), texto]).encode()).hexdigest()[:16]
        destino = config.CACHE_DIR / "eevv" / tipo / tabla / f"{anio}_{digest}.parquet"
        partes.append(_desde_cache(destino, lambda a=anio, r=ruta: calcular(_armonizado(tipo, a, r))))
    if progress:
        progress(1.0, "Listo")
    return partes


def _anios_lista(anios) -> list[int] | None:
    if anios is None:
        return None
    return [int(anios)] if isinstance(anios, (numbers.Integral, str)) else [int(a) for a in anios]


def _aplicar_filtros(df: pd.DataFrame, filtros: dict | None) -> pd.DataFrame:
    return df[_mascara(df, filtros)] if filtros else df


def serie_indicadores(
    anios: Iterable[int] | int | None = None,
    tipo: str = "defunciones",
    por: str | Iterable[str] | None = None,
    filtros: dict | None = None,
    dropna: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Indicadores por año sin tener toda la serie en memoria.

    Da exactamente lo mismo que ``indicadores(load(anios, tipo), por=["anio", *por])``, pero lee un año a la vez y guarda
    cada resultado en disco.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    tipo
        ``"defunciones"``, ``"nacimientos"`` o ``"fetales"``.
    por
        Columna o lista de columnas para desagregar, además del año.
    filtros
        Solo estas filas: ``{columna: [valores]}`` o ``{columna: (mínimo, máximo)}``.
    dropna
        Quitar las filas de los registros sin dato en ``por``.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        Las columnas de :func:`indicadores`, con ``anio`` y las de ``por``.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.

    Véase también
    -------------
    indicadores : Lo mismo sobre unos datos ya cargados.
    serie_conteos : Conteos por cualquier combinación de variables.
    tasas : Tasas sobre la población.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> r = dd.eevv.serie_indicadores(range(2023, 2026), tipo="nacimientos")  # doctest: +SKIP
    >>> r[["anio", "nacimientos", "pct_bajo_peso", "pct_cesarea"]].round(1)  # doctest: +SKIP
       anio  nacimientos  pct_bajo_peso  pct_cesarea
    0  2023       515549           11.0         50.0
    1  2024       453901           11.3         51.8
    2  2025       441537           11.0         53.8
    >>> dd.eevv.serie_indicadores(2025, por="gran_causa", filtros={"sexo": ["Mujer"]})  # doctest: +SKIP
    """
    anios = _anios_lista(anios)
    if tipo == "defunciones":
        _avisar_cobertura(tipo, anios if anios is not None else find_files(tipo=tipo, root=root))
    llaves = ["anio", *_lista(por)]

    def calcular(d: pd.DataFrame) -> pd.DataFrame:
        return indicadores(_aplicar_filtros(d, filtros), por=llaves, dropna=dropna)

    partes = _por_anio("indicadores", anios, tipo, {"por": llaves, "filtros": filtros, "dropna": dropna}, calcular, root, progress)
    return _unir(partes).sort_values(llaves, ignore_index=True)


def serie_conteos(
    anios: Iterable[int] | int | None = None,
    tipo: str = "defunciones",
    por: str | Iterable[str] | None = None,
    filtros: dict | None = None,
    dropna: bool = True,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Cuántos certificados hay por año y grupo, sin tener toda la serie en memoria.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    tipo
        ``"defunciones"``, ``"nacimientos"`` o ``"fetales"``.
    por
        Columna o lista de columnas, además del año, por ejemplo ``"causa_105_nombre"``.
    filtros
        Solo estas filas: ``{columna: [valores]}`` o ``{columna: (mínimo, máximo)}``.
    dropna
        Quitar las filas de los registros sin dato en ``por``.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        ``anio``, las columnas de ``por`` y ``n``.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.

    Véase también
    -------------
    serie_indicadores : Indicadores por año.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> causas = dd.eevv.serie_conteos(2025, por="causa_105_nombre")  # doctest: +SKIP
    >>> causas.nlargest(2, "n")[["causa_105_nombre", "n"]]  # doctest: +SKIP
                                                  causa_105_nombre      n
    31                             Enfermedades isquémicas del corazón  49261
    18      Enfermedades crónicas de las vías respiratorias inferiores  18187
    """
    anios = _anios_lista(anios)
    if tipo == "defunciones":
        _avisar_cobertura(tipo, anios if anios is not None else find_files(tipo=tipo, root=root))
    llaves = ["anio", *_lista(por)]

    def calcular(d: pd.DataFrame) -> pd.DataFrame:
        d = _aplicar_filtros(d, filtros)
        return d.groupby(llaves, observed=True, dropna=dropna, sort=True).size().rename("n").reset_index()

    partes = _por_anio("conteos", anios, tipo, {"por": llaves, "filtros": filtros, "dropna": dropna}, calcular, root, progress)
    return _unir(partes).sort_values(llaves, ignore_index=True)


# --------------------------------------------------------------------------- #
# Tasas
# --------------------------------------------------------------------------- #
def _para_tasas(d: pd.DataFrame, por: list[str]) -> pd.DataFrame:
    """Los datos de un año con las columnas de ``por`` como en la población. Lo que no tiene dato queda vacío."""
    d = d.copy()
    if "departamento" in por:
        d["departamento"] = d["departamento_residencia"].astype("object")
    if "sexo" in por:
        d["sexo"] = d["sexo"].astype("object").where(d["sexo"].isin(["Hombre", "Mujer"]))
    if "area" in por:
        d["area"] = d["area_residencia"].astype("object").map(_AREA_POBLACION)
    return d


def _contar_para_tasas(tipo: str, anios, por: list[str], root, progress=None) -> pd.DataFrame:
    """Los hechos de un tipo por año y grupo. Vacío si ese tipo no está descargado: las demás tasas sí se pueden calcular."""
    if not find_files(anios, tipo=tipo, root=root):
        return pd.DataFrame(columns=["anio", *por])
    llaves = ["anio", *por]

    def calcular(d: pd.DataFrame) -> pd.DataFrame:
        d = _para_tasas(d, por).dropna(subset=por)
        grupos = d.groupby(llaves, observed=True, sort=True)
        res = grupos.size().rename(tipo).to_frame()
        if tipo == "defunciones":
            sin_detalle = d["grupo_edad"].eq(_SIN_DETALLE).groupby([d[k] for k in llaves], observed=True).sum()
            menores = d["menor_un_anio"].fillna(False).astype(bool).groupby([d[k] for k in llaves], observed=True).sum()
            res["defunciones_menores_1"] = menores.astype("float64").where(sin_detalle == 0)
            con_causa = d["materna"].notna().groupby([d[k] for k in llaves], observed=True).sum()
            maternas = d["materna"].fillna(False).astype(bool).groupby([d[k] for k in llaves], observed=True).sum()
            res["defunciones_maternas"] = maternas.astype("float64").where(con_causa > 0)
        return res.reset_index()

    partes = _por_anio("para_tasas", anios, tipo, {"por": por}, calcular, root, progress)
    return pd.concat(partes, ignore_index=True)


def _poblacion_por(anios: list[int], por: list[str], **kw) -> pd.DataFrame:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # los años sin población quedan vacíos: se avisa una vez, arriba
        return poblacion(anios, por=por, **kw)


def _anios_descargados(anios, tipos, root) -> list[int]:
    if anios is not None:
        return anios
    return sorted({a for t in tipos for a in find_files(tipo=t, root=root)})


def _por_valido(por) -> list[str]:
    por = _lista(por)
    if desconocidas := [c for c in por if c not in _POR_TASAS]:
        raise ValueError(f"Las tasas no se pueden desagregar por {desconocidas}. Opciones: {list(_POR_TASAS)}")
    return por


def _avisar_sin_poblacion(res: pd.DataFrame, por: list[str]) -> None:
    if "departamento" in por and (viejos := sorted(a for a in res["anio"].unique() if a < 1985)):
        warnings.warn(f"Sin población por departamento para {viejos[0]}–{viejos[-1]}: esos años quedan sin tasa. "
                      "Las proyecciones por departamento empiezan en 1985.", UserWarning, stacklevel=3)


def tasas(
    anios: Iterable[int] | int | None = None,
    por: str | Iterable[str] | None = None,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Tasas de natalidad, mortalidad y fecundidad con las proyecciones de población del DANE.

    Combina los tres certificados con :func:`dane_data.poblacion`, un año a la vez. Cada tasa se calcula con lo que haya
    descargado; las demás quedan vacías.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    por
        ``"departamento"`` (de residencia), ``"sexo"`` o ``"area"`` (de residencia: ``"Cabecera"`` o ``"Centros poblados y
        rural disperso"``), o una lista de ellos.
    root
        Carpeta raíz de las Estadísticas Vitales. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        ``anio``, las columnas de ``por`` y:

        * ``poblacion``, ``nacimientos``, ``defunciones``, ``defunciones_menores_1``, ``defunciones_maternas``,
          ``fetales``.
        * ``tasa_natalidad`` y ``tasa_mortalidad``, por 1.000 habitantes.
        * ``tasa_global_fecundidad``, hijos por mujer, de 15 a 49 años.
        * ``mortalidad_infantil``, por 1.000 nacidos vivos.
        * ``razon_mortalidad_materna``, por 100.000 nacidos vivos.
        * ``razon_mortalidad_fetal``, por 1.000 nacidos vivos más defunciones fetales.

        Por sexo solo hay ``tasa_mortalidad`` y ``mortalidad_infantil``: las demás quedan vacías.

    Lanza
    -----
    FileNotFoundError
        Si no hay ningún certificado descargado de esos años.
    ValueError
        Si ``por`` no es válido.

    Avisos
    ------
    UserWarning
        Si los años incluyen defunciones con problemas de cobertura (1979, 1980, 1991), o años sin población para esa
        desagregación.

    Véase también
    -------------
    tasas_especificas : Tasas por grupo de edad.
    dane_data.poblacion : Las proyecciones de población.

    Notas
    -----
    **Son tasas de hechos registrados, sin ajustar por subregistro.** No tienen por qué coincidir con los indicadores
    demográficos que publica el DANE, que salen del modelo de sus proyecciones. Las de los años antiguos, con más
    subregistro, salen más bajas que las reales.

    Por departamento se usa la residencia, y quedan por fuera los registros sin departamento o de residentes en el
    extranjero; por eso la suma es menor que el total nacional, que sí los incluye para coincidir con lo publicado.
    Los certificados de nacimiento y las defunciones de menores de un año se atribuyen a la residencia de la madre.

    Por sexo, los nacimientos se cuentan por el sexo del nacido, no de quien los tiene: la natalidad y la fecundidad no
    se pueden partir así, y las muertes maternas, todas de mujeres, no se pueden dividir por las nacidas mujeres. Las
    defunciones fetales casi siempre traen sexo indeterminado.

    Los nacimientos sin edad de la madre no entran en la fecundidad, lo que la subestima un poco: son como mucho 1,5 % de
    los nacimientos de cada año.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> r = dd.eevv.tasas(2025)  # doctest: +SKIP
    >>> r[["tasa_natalidad", "tasa_mortalidad", "tasa_global_fecundidad", "mortalidad_infantil"]].round(2)  # doctest: +SKIP
       tasa_natalidad  tasa_mortalidad  tasa_global_fecundidad  mortalidad_infantil
    0            8.32             5.36                    1.02                10.25
    >>> dd.eevv.tasas(range(2015, 2026), por="departamento")  # doctest: +SKIP
    """
    por = _por_valido(por)
    anios = _anios_lista(anios)
    tipos = ("defunciones", "nacimientos", "fetales")
    if not any(find_files(anios, tipo=t, root=root) for t in tipos):
        raise FileNotFoundError(
            f"No hay Estadísticas Vitales para años={anios} en {_root(root)}. "
            "Descárguelas con dane_data.eevv.download(...) o revise dane_data.set_paths(...)."
        )
    llaves = ["anio", *por]
    disponibles = _anios_descargados(anios, tipos, root)
    _avisar_cobertura("defunciones", [a for a in disponibles if a in find_files(tipo="defunciones", root=root)])

    res = None
    for i, tipo in enumerate(tipos):
        # Fetales casi siempre traen sexo indeterminado: por sexo no dicen nada
        if tipo == "fetales" and "sexo" in por:
            continue
        avance = None if progress is None else lambda f, m, i=i: progress((i + f) / len(tipos), m)
        conteo = _contar_para_tasas(tipo, disponibles, por, root, avance)
        res = conteo if res is None else res.merge(conteo, how="outer", on=llaves)
    for columna in ("nacimientos", "defunciones", "defunciones_menores_1", "defunciones_maternas", "fetales"):
        if columna not in res.columns:
            res[columna] = np.nan

    pob = _poblacion_por(disponibles, por)
    res = res.merge(pob, how="left", on=llaves)
    _avisar_sin_poblacion(res, por)

    # Por sexo, los nacimientos son los del sexo del nacido: dividirlos por la población de ese sexo, o dividir por las
    # nacidas mujeres las muertes maternas (todas de mujeres), no mide nada. La mortalidad infantil sí: niños sobre niños.
    por_sexo = "sexo" in por
    res["tasa_natalidad"] = np.nan if por_sexo else _MIL * res["nacimientos"] / res["poblacion"]
    res["tasa_mortalidad"] = _MIL * res["defunciones"] / res["poblacion"]
    res["mortalidad_infantil"] = _MIL * res["defunciones_menores_1"] / res["nacimientos"]
    res["razon_mortalidad_materna"] = np.nan if por_sexo else 100_000 * res["defunciones_maternas"] / res["nacimientos"]
    res["razon_mortalidad_fetal"] = _MIL * res["fetales"] / (res["nacimientos"] + res["fetales"])
    res["tasa_global_fecundidad"] = np.nan
    if "sexo" not in por and find_files(anios, tipo="nacimientos", root=root):
        especificas = tasas_especificas(disponibles, "nacimientos", por, root=root)
        fertil = especificas[especificas["edad_madre"].isin([f"De {a} a {b} años" for a, b in _EDADES_FERTILES])]
        tgf = (5 * (fertil["nacimientos"] / fertil["mujeres"]).groupby([fertil[k] for k in llaves], observed=True).sum(min_count=7)
               ).rename("_tgf").reset_index()
        res = res.merge(tgf, how="left", on=llaves)
        res["tasa_global_fecundidad"] = res.pop("_tgf")

    orden = [*llaves, "poblacion", "nacimientos", "defunciones", "defunciones_menores_1", "defunciones_maternas", "fetales",
             "tasa_natalidad", "tasa_mortalidad", "tasa_global_fecundidad", "mortalidad_infantil",
             "razon_mortalidad_materna", "razon_mortalidad_fetal"]
    return res[orden].replace([np.inf, -np.inf], np.nan).sort_values(llaves, ignore_index=True)


def tasas_especificas(
    anios: Iterable[int] | int | None = None,
    tipo: str = "nacimientos",
    por: str | Iterable[str] | None = None,
    root=None,
    progress=None,
) -> pd.DataFrame:
    """
    Tasas por grupo de edad: fecundidad de las mujeres, o mortalidad.

    Parámetros
    ----------
    anios
        Año o lista de años. ``None`` para todos los descargados.
    tipo
        ``"nacimientos"`` da nacimientos por edad de la madre sobre las mujeres de esa edad; ``"defunciones"``,
        defunciones por grupo de edad sobre las personas de esa edad.
    por
        ``"departamento"`` (de residencia), ``"area"`` y, solo en defunciones, ``"sexo"``. Un nombre o una lista.
    root
        Carpeta raíz. Por defecto, la configurada.
    progress
        Función ``progress(fraccion, mensaje)`` que recibe el avance.

    Devuelve
    --------
    DataFrame
        ``anio``, las columnas de ``por`` y, según el tipo:

        * Nacimientos: ``edad_madre``, ``nacimientos``, ``mujeres`` y ``tasa``, por 1.000 mujeres.
        * Defunciones: ``grupo_edad``, ``defunciones``, ``poblacion`` y ``tasa``, por 1.000 personas. En 1991 los grupos
          de menores de 10 años quedan vacíos.

    Lanza
    -----
    FileNotFoundError
        Si no hay datos para esos años.
    ValueError
        Si ``tipo`` o ``por`` no son válidos.

    Avisos
    ------
    UserWarning
        Si los años incluyen 1979, 1980 o 1991, o años sin población para esa desagregación.

    Véase también
    -------------
    tasas : Tasas generales.

    Notas
    -----
    Son hechos registrados, sin ajustar por subregistro (vea :func:`tasas`). Quedan por fuera los registros sin edad.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> r = dd.eevv.tasas_especificas(2025, "nacimientos").round(2)  # doctest: +SKIP
    >>> r[["edad_madre", "nacimientos", "mujeres", "tasa"]].head(2)  # doctest: +SKIP
            edad_madre  nacimientos  mujeres   tasa
    0  De 10 a 14 años       2967.0  2016446   1.47
    1  De 15 a 19 años      59104.0  2126519  27.79
    >>> dd.eevv.tasas_especificas(2025, "defunciones", por="sexo")  # doctest: +SKIP
    """
    if tipo not in ("nacimientos", "defunciones"):
        raise ValueError(f"Las tasas específicas son de 'nacimientos' o 'defunciones', no de {tipo!r}.")
    por = _por_valido(por)
    if tipo == "nacimientos" and "sexo" in por:
        raise ValueError("La fecundidad es de las mujeres: no se puede desagregar por sexo.")
    anios = _anios_lista(anios)
    if tipo == "defunciones":
        _avisar_cobertura(tipo, anios if anios is not None else find_files(tipo=tipo, root=root))
    edad, bandas, numerador, denominador = (("edad_madre", _EDADES_MADRE, "nacimientos", "mujeres") if tipo == "nacimientos"
                                            else ("grupo_edad", _EDADES_DEFUNCION, "defunciones", "poblacion"))
    llaves = ["anio", *por]

    def calcular(d: pd.DataFrame) -> pd.DataFrame:
        d = _para_tasas(d, por).dropna(subset=por)
        d = d.assign(**{edad: d[edad].astype("object")})
        conteo = d.groupby([*llaves, edad], observed=True, sort=True).size().rename(numerador).reset_index()
        # Enero–junio de 1991: los menores de 10 años no se pueden repartir, así que esos grupos contarían de menos
        if tipo == "defunciones" and (d[edad] == _SIN_DETALLE).any():
            menores = ["Menor de 1 año", "De 1 a 4 años", "De 5 a 9 años"]
            conteo[numerador] = conteo[numerador].astype("float64").mask(conteo[edad].isin(menores))
        return conteo[conteo[edad].isin(list(bandas))]

    partes = _por_anio("especificas", anios, tipo, {"por": por}, calcular, root, progress)
    conteo = pd.concat(partes, ignore_index=True)
    disponibles = sorted(conteo["anio"].unique().tolist())
    sexo_pob = {"sexo": "Mujer"} if tipo == "nacimientos" else {}
    pobs = [_poblacion_por(disponibles, por, edades=rango, **sexo_pob).assign(**{edad: nombre}) for nombre, rango in bandas.items()]
    pob = pd.concat(pobs, ignore_index=True).rename(columns={"poblacion": denominador})
    # Con merge por la derecha, un grupo sin hechos queda en 0 en vez de desaparecer: es una tasa de 0, no un dato faltante
    res = conteo.merge(pob, how="right", on=[*llaves, edad])
    faltantes = res[numerador].isna() & ~res["anio"].isin(conteo.loc[conteo[numerador].isna(), "anio"])
    res[numerador] = res[numerador].astype("float64").mask(faltantes, 0.0)
    _avisar_sin_poblacion(conteo, por)
    res["tasa"] = _MIL * res[numerador] / res[denominador]
    orden = list(bandas)
    res[edad] = pd.Categorical(res[edad], categories=orden, ordered=True)
    return res[[*llaves, edad, numerador, denominador, "tasa"]].sort_values([*llaves, edad], ignore_index=True)
