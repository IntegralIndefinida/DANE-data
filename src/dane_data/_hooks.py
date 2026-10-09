"""Ganchos de progreso y cancelación compartidos por los descargadores."""

from __future__ import annotations

from typing import Callable, Optional

ProgressFn = Callable[[Optional[float], str], None]


class DownloadCancelled(Exception):
    """El usuario pidió detener la descarga."""


class ProgressMixin:
    progress: ProgressFn | None = None
    should_stop: Callable[[], bool] | None = None

    def _emit(self, fraction: float | None, message: str) -> None:
        if self.progress is not None:
            self.progress(fraction, message)

    def _check_stop(self) -> None:
        if self.should_stop is not None and self.should_stop():
            raise DownloadCancelled("Descarga cancelada por el usuario.")
