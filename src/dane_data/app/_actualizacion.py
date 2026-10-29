"""
Aviso de versión nueva en la app: la última versión en PyPI, sus novedades y, en el zip para estudiantes, la
instalación cuando el usuario la pide. Nada se actualiza solo.

La consulta (pypi.org y raw.githubusercontent.com, sin enviar datos del usuario) se hace como mucho una vez
al día y se desactiva con la variable de entorno ``DANE_DATA_SIN_ACTUALIZACIONES=1``. Está declarada en la
política de privacidad del README, que exige SignPath: si cambia lo que se consulta, hay que actualizarla.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import requests

import dane_data as dd
from dane_data import config

URL_PYPI = "https://pypi.org/pypi/dane-data/json"
URL_NOVEDADES = "https://raw.githubusercontent.com/IntegralIndefinida/DANE-data/v{version}/docs/novedades.md"
URL_DOCS = "https://integralindefinida.github.io/DANE-data/"
DESACTIVAR = "DANE_DATA_SIN_ACTUALIZACIONES"
NOMBRE_ZIP = "dane-data-estudiantes"  # [project] name de estudiantes/pyproject.toml
_UN_DIA = 86400


def _numeros(version: str) -> tuple[int, ...]:
    """``"0.10.1"`` → ``(0, 10, 1)``, para comparar versiones (``"0.4.0rc1"`` → ``(0, 4, 0)``)."""
    m = re.match(r"\d+(?:\.\d+)*", version.strip())
    return tuple(int(x) for x in m.group().split(".")) if m else ()


def _es_nueva(version: str) -> bool:
    return _numeros(version) > _numeros(dd.__version__)


def _a_markdown(texto: str) -> str:
    """Quita la sintaxis de Sphinx (MyST) de novedades.md: los roles {dd} y {doc} y los enlaces relativos."""
    texto = re.sub(r"\{dd\}`([^`]+)`", r"`dd.\1`", texto)
    texto = re.sub(r"\{doc\}`([^`<]+?)\s*<([^`>]+)>`", lambda m: f"[{m[1]}]({URL_DOCS}{m[2]}.html)", texto)
    texto = re.sub(r"\{doc\}`([^`]+)`", lambda m: f"[{m[1].rsplit('/', 1)[-1]}]({URL_DOCS}{m[1]}.html)", texto)
    return re.sub(r"\]\((?![a-z]+:)([^)#]+)\.md(#[^)]*)?\)", lambda m: f"]({URL_DOCS}{m[1]}.html{m[2] or ''})",
                  texto)


def extraer_novedades(texto: str, desde: str, hasta: str) -> str:
    """
    Las secciones de ``docs/novedades.md`` de las versiones posteriores a ``desde`` y hasta ``hasta``, en
    Markdown sin la sintaxis de Sphinx. Vacío si no hay ninguna (p. ej. si la sección sigue en «Sin publicar»).
    """
    elegidas = []
    for seccion in re.split(r"(?m)^## ", texto)[1:]:
        version = _numeros(seccion)
        if version and _numeros(desde) < version <= _numeros(hasta):
            elegidas.append("#### " + seccion.strip())
    return _a_markdown("\n\n".join(elegidas))


def _consultar(timeout: float) -> dict | None:
    """La última versión en PyPI y, si es nueva, el novedades.md de esa versión; None sin conexión."""
    try:
        r = requests.get(URL_PYPI, timeout=timeout)
        r.raise_for_status()
        ultima = r.json()["info"]["version"]
    except (requests.RequestException, ValueError, KeyError, TypeError):
        return None
    novedades = None
    if _es_nueva(ultima):
        try:
            r = requests.get(URL_NOVEDADES.format(version=ultima), timeout=timeout)
            r.raise_for_status()
            novedades = r.text
        except requests.RequestException:
            pass
    return {"fecha": time.time(), "ultima": ultima, "novedades": novedades}


def revisar(timeout: float = 5) -> tuple[str, str | None] | None:
    """
    ``(versión, novedades)`` si en PyPI hay una versión más nueva que la instalada, o None si no la hay, no se
    pudo consultar o está desactivado. Las novedades van en Markdown (None si no se pudieron leer).

    Consulta internet como mucho una vez al día: la respuesta queda en ``~/.cache/dane_data/version.json``.
    """
    if os.environ.get(DESACTIVAR):
        return None
    archivo = config.CACHE_DIR / "version.json"
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8"))
        vigente = 0 <= time.time() - datos["fecha"] < _UN_DIA
    except (OSError, ValueError, KeyError, TypeError):
        datos, vigente = None, False
    if not vigente:
        datos = _consultar(timeout)
        if datos is None:  # sin conexión: no se guarda, se intenta la próxima vez
            return None
        try:
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(json.dumps(datos), encoding="utf-8")
        except OSError:
            pass
    ultima = datos.get("ultima")
    if not isinstance(ultima, str) or not _es_nueva(ultima):
        return None
    texto = datos.get("novedades")
    novedades = extraer_novedades(texto, dd.__version__, ultima) if isinstance(texto, str) else ""
    return ultima, novedades or None


def carpeta_zip() -> Path | None:
    """La carpeta del zip para estudiantes si la app corre desde su ``.venv``; None si se instaló de otra forma."""
    carpeta = Path(sys.prefix).parent
    try:
        texto = (carpeta / "pyproject.toml").read_text(encoding="utf-8")
    except OSError:
        return None
    return carpeta if re.search(rf'(?m)^name = "{NOMBRE_ZIP}"', texto) else None


def actualizar_zip(carpeta: Path, version: str) -> str | None:
    """
    Pasa el zip para estudiantes de ``carpeta`` a ``version``: cambia su ``uv.lock`` y baja lo que falte a la
    caché de uv, instalándolo en un entorno de prueba que después se borra. No toca el ``.venv`` de la app
    abierta (en Windows no se pueden reemplazar las librerías en uso): el lanzador instala la versión nueva al
    volver a abrir, desde la caché, así que ya no hace falta internet.

    Devuelve None si salió bien, o el error; entonces el ``uv.lock`` queda como estaba.
    """
    uv = os.environ.get("UV") or shutil.which("uv")  # `uv run` pone en UV la ruta de uv
    if not uv:
        return "no se encontró uv"
    lock = carpeta / "uv.lock"
    antes = lock.read_bytes() if lock.exists() else None
    entorno = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}  # el de la app, no el de prueba
    try:
        with tempfile.TemporaryDirectory(prefix=".venv-actualizacion-", dir=carpeta,
                                         ignore_cleanup_errors=True) as prueba:
            for comando, extra in (([uv, "lock", "--upgrade-package", f"dane-data=={version}"], {}),
                                   ([uv, "sync", "--frozen", "--extra", "app"], {"UV_PROJECT_ENVIRONMENT": prueba})):
                r = subprocess.run(comando, cwd=carpeta, env={**entorno, **extra}, capture_output=True,
                                   encoding="utf-8", errors="replace", timeout=1800)
                if r.returncode != 0:
                    raise RuntimeError((r.stderr or r.stdout).strip() or f"uv {comando[1]} terminó con error")
    except (OSError, RuntimeError, subprocess.SubprocessError) as e:
        if antes is not None:
            lock.write_bytes(antes)
        return str(e)
    return None
