"""
Configuración de rutas de datos.

Cada encuesta vive en su propia carpeta raíz, con la misma estructura que
generan los descargadores originales:

    GEIH  (serie principal) : <raiz>/datos_csv/<año>/<mes>/*.csv|*.txt|*.dta
    GEIH  (serie empalme)   : <raiz>/datos_csv/<año>/<mes>/*.csv
    EAM                     : <raiz>/datos/<año>/*.csv|*.txt|*.dta

Prioridad para resolver cada ruta:
  1. ``set_paths(...)`` en la sesión actual.
  2. Variables de entorno ``DANE_DATA_GEIH``, ``DANE_DATA_GEIH_EMPALME``, ``DANE_DATA_EAM``.
  3. Archivo ``~/.config/dane_data/config.json`` (lo escribe ``save()`` y la app).
  4. Valor por defecto bajo ``~/dane_data_datos/``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

CONFIG_FILE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "dane_data" / "config.json"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "dane_data"
DEFAULT_HOME = Path.home() / "dane_data_datos"

_KEYS = {
    "geih": ("DANE_DATA_GEIH", DEFAULT_HOME / "geih"),
    "geih_empalme": ("DANE_DATA_GEIH_EMPALME", DEFAULT_HOME / "geih" / "empalme"),
    "eam": ("DANE_DATA_EAM", DEFAULT_HOME / "eam"),
}
_session: dict[str, Path] = {}


def _read_file() -> dict:
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}  # un JSON que no es un objeto: como si no existiera


def get_path(key: str) -> Path:
    """
    Carpeta raíz de una encuesta.

    Se resuelve en este orden: ``set_paths`` en la sesión actual, la variable de entorno
    (``DANE_DATA_GEIH``, ``DANE_DATA_GEIH_EMPALME`` o ``DANE_DATA_EAM``), el archivo
    ``~/.config/dane_data/config.json`` y, si nada de eso existe, ``~/dane_data_datos/``.

    Parámetros
    ----------
    key
        ``"geih"``, ``"geih_empalme"`` o ``"eam"``.

    Devuelve
    --------
    Path
        La carpeta, aunque todavía no exista.

    Lanza
    -----
    KeyError
        Si ``key`` no es una de las tres claves.

    Véase también
    -------------
    set_paths : Cambiar las carpetas.
    show_paths : Las tres carpetas a la vez.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.get_path("geih")  # doctest: +SKIP
    PosixPath('/home/ana/dane_data_datos/geih')
    """
    if key not in _KEYS:
        raise KeyError(f"Clave desconocida {key!r}. Opciones: {list(_KEYS)}")
    if key in _session:
        return _session[key]
    env, default = _KEYS[key]
    if os.environ.get(env):
        return Path(os.environ[env]).expanduser()
    stored = _read_file().get(key)
    if stored:
        return Path(stored).expanduser()
    return default


def set_paths(geih=None, geih_empalme=None, eam=None, save: bool = False) -> None:
    """
    Fija las carpetas raíz de los datos.

    Cada carpeta es la raíz de una encuesta: la GEIH queda en ``<raíz>/datos_csv/<año>/<mes>/`` y la EAM en
    ``<raíz>/datos/<año>/``. Las carpetas que no se indican no cambian.

    Parámetros
    ----------
    geih
        Carpeta de la serie principal de la GEIH.
    geih_empalme
        Carpeta de la serie de empalme de la GEIH (2010–2020).
    eam
        Carpeta de la EAM.
    save
        Si True, guarda las carpetas indicadas en esta llamada en ``~/.config/dane_data/config.json``:
        valen para las próximas sesiones, para la línea de comandos y para la aplicación. Si False, solo
        para esta sesión.

    Lanza
    -----
    ValueError
        Si alguna carpeta es un texto vacío (sería la carpeta desde donde se ejecuta Python).

    Notas
    -----
    Una carpeta relativa (``"datos"``) se completa con la carpeta desde donde se ejecuta Python y se guarda
    completa: así la línea de comandos, la aplicación y otro notebook la encuentran en el mismo lugar.

    Véase también
    -------------
    get_path : Carpeta efectiva de una encuesta.
    show_paths : Las tres carpetas efectivas.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.set_paths(geih="~/datos/GEIH", eam="~/datos/EAM", save=True)  # doctest: +SKIP
    """
    nuevas = {k: v for k, v in (("geih", geih), ("geih_empalme", geih_empalme), ("eam", eam)) if v is not None}
    if vacias := [k for k, v in nuevas.items() if not str(v).strip()]:
        raise ValueError(f"Carpeta vacía para {', '.join(vacias)}: indique una ruta.")
    for key, val in nuevas.items():
        # Completa: guardada como "datos", cada proceso la buscaría en su propia carpeta (la app corre
        # dentro del paquete instalado)
        _session[key] = Path(os.path.abspath(Path(val).expanduser()))
    if save:
        # Solo las de esta llamada: las fijadas antes solo para la sesión no se vuelven permanentes
        data = _read_file()
        data.update({k: str(_session[k]) for k in nuevas})
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = CONFIG_FILE.with_name(f"{CONFIG_FILE.name}.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(CONFIG_FILE)  # un corte a mitad de escritura no deja el archivo vacío


def show_paths() -> dict[str, str]:
    """
    Carpetas efectivas de las tres encuestas.

    Útil para revisar de dónde está leyendo la librería.

    Devuelve
    --------
    dict
        ``{"geih": ..., "geih_empalme": ..., "eam": ...}`` con las rutas como texto.

    Véase también
    -------------
    set_paths : Cambiar las carpetas.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> dd.show_paths()  # doctest: +SKIP
    {'geih': '/home/ana/datos/GEIH', 'geih_empalme': '/home/ana/dane_data_datos/geih/empalme', 'eam': '/home/ana/datos/EAM'}
    """
    return {k: str(get_path(k)) for k in _KEYS}
