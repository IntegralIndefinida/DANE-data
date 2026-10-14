"""Ganchos de progreso y cancelación compartidos por los descargadores."""

from __future__ import annotations

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
