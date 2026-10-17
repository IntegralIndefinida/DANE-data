"""Ganchos de progreso y cancelación, y extracción de ZIPs, compartidos por los descargadores."""

from __future__ import annotations

import shutil
import zipfile
from pathlib import Path
from typing import Callable, Optional

ProgressFn = Callable[[Optional[float], str], None]


class DownloadCancelled(Exception):
    """
    La descarga se detuvo porque ``should_stop()`` devolvió True.

    La lanzan ``dd.geih.download`` y ``dd.eam.download`` cuando se les pasa ``should_stop`` (la aplicación
    lo usa para su botón de cancelar). Los meses o años que ya terminaron quedan en disco y la próxima
    descarga los salta.

    Ejemplos
    --------
    >>> import time
    >>> import dane_data as dd
    >>> limite = time.time() + 60
    >>> try:  # doctest: +SKIP
    ...     dd.geih.download(2025, should_stop=lambda: time.time() > limite)
    ... except dd.DownloadCancelled:
    ...     print("Se detuvo al minuto; lo descargado se conserva.")
    """


class ProgressMixin:
    progress: ProgressFn | None = None
    should_stop: Callable[[], bool] | None = None

    def _emit(self, fraction: float | None, message: str) -> None:
        if self.progress is not None:
            self.progress(fraction, message)

    def _check_stop(self) -> None:
        if self.should_stop is not None and self.should_stop():
            raise DownloadCancelled("Descarga cancelada por el usuario.")


def ya_extraido(member: zipfile.ZipInfo, destino: Path) -> bool:
    """``destino`` ya tiene el archivo completo (mismo tamaño que dentro del ZIP)."""
    return destino.is_file() and destino.stat().st_size == member.file_size


def extraer_miembro(z: zipfile.ZipFile, member: zipfile.ZipInfo, destino: Path) -> None:
    """
    Copia ``member`` a ``destino`` por partes, primero con otro nombre (``.part``) y renombrando
    al terminar: si se interrumpe (Ctrl+C, disco lleno), no queda un archivo a medias con el
    nombre final que la próxima descarga daría por bueno.
    """
    tmp = destino.with_name(destino.name + ".part")
    try:
        with z.open(member) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        tmp.replace(destino)
    finally:
        tmp.unlink(missing_ok=True)
