"""Ganchos de progreso y cancelación, y extracción de ZIPs, compartidos por los descargadores."""

from __future__ import annotations

import logging
import shutil
import time
import uuid
import zipfile
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

import requests

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


class DescargadorANDA(ProgressMixin):
    """Lo común de los descargadores de la GEIH y la EAM: la sesión HTTP y la descarga de cada ZIP."""

    base_url = "https://microdatos.dane.gov.co"
    log = logging.getLogger("dane_data")  # cada descargador pone el suyo

    def _abrir_sesion(self) -> None:
        self.fallidos: list[str] = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def download_file(self, url: str, dest_path: Path, max_retries: int = 3) -> bool:
        """
        Descarga un archivo con streaming y verificación de integridad.
        """
        log = self.log
        if dest_path.exists() and dest_path.stat().st_size > 0:
            if zip_valido(dest_path):
                log.info(f"Archivo ya existente: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.1f} MB). Saltando descarga.")
                return True
            log.warning(f"{dest_path.name} en disco está dañado: se vuelve a descargar.")
            dest_path.unlink()

        temp_dest = _temporal(dest_path)

        for attempt in range(1, max_retries + 1):
            try:
                log.info(f"Descargando {dest_path.name} (intento {attempt}/{max_retries})...")
                with self.session.get(url, stream=True, timeout=45) as r:
                    r.raise_for_status()
                    total_size = int(r.headers.get("content-length", 0))
                    downloaded = 0

                    with open(temp_dest, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            self._check_stop()
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_size:
                                    self._emit(None, f"{dest_path.name}: {downloaded / 1e6:.1f} / {total_size / 1e6:.1f} MB")

                    if total_size > 0 and downloaded < total_size:
                        log.warning(f"Descarga incompleta ({downloaded}/{total_size} bytes). Reintentando...")
                        continue
                    # Sin content-length, un corte o una página de error del ANDA no se notan arriba
                    if not zip_valido(temp_dest, dest_path):
                        log.warning(f"{dest_path.name}: lo descargado no es un ZIP válido. Reintentando...")
                        continue

                temp_dest.replace(dest_path)
                size_mb = dest_path.stat().st_size / 1024 / 1024
                log.info(f"✓ Descarga completada: {dest_path.name} ({size_mb:.2f} MB)")
                return True

            except DownloadCancelled:
                temp_dest.unlink(missing_ok=True)
                raise
            except Exception as e:
                log.error(f"Error descargando {dest_path.name} (intento {attempt}): {e}")
                temp_dest.unlink(missing_ok=True)
                time.sleep(2 * attempt)

        temp_dest.unlink(missing_ok=True)
        return False

    def _fallo(self, mensaje: str) -> None:
        """Anota algo que no se pudo bajar o extraer: ``run_pipeline`` lo resume al final y lo devuelve."""
        self.log.error(mensaje)
        self.fallidos.append(mensaje)

    def _terminar(self, serie: str, carpeta: Path) -> list[str]:
        """Cierre de ``run_pipeline``: éxito solo si nada falló. Devuelve lo que falló."""
        if self.fallidos:
            self._emit(1.0, f"Descarga terminada con {len(self.fallidos)} problema(s)")
            self.log.warning(f"\nLa descarga de {serie} terminó con {len(self.fallidos)} problema(s):\n  - "
                             + "\n  - ".join(self.fallidos)
                             + "\nVuelva a descargar los mismos años: lo que ya está completo se salta.")
        else:
            self._emit(1.0, "Descarga terminada")
            self.log.info(f"\n¡Descarga de {serie} finalizada exitosamente!")
        self.log.info(f"Datos organizados en: {carpeta.resolve()}")
        return list(self.fallidos)


def _temporal(destino: Path) -> Path:
    """
    Nombre temporal único junto a ``destino``. Con uno fijo (``<archivo>.part``), dos descargas del mismo
    año a la vez (dos pestañas, la app en modo aula) escribirían el mismo archivo; en Windows la segunda
    falla porque está en uso.
    """
    return destino.with_name(f"{destino.name}.{uuid.uuid4().hex[:12]}.part")


def url_del_anda(url: str, base: str = DescargadorANDA.base_url) -> str | None:
    """
    El enlace de descarga sacado de una página del ANDA, si apunta al ANDA por https (los relativos se
    completan con ``base``); ``None`` si apunta a otro sitio o por http. Así un enlace raro en la página
    no hace descargar nada de otro servidor.
    """
    completa = urljoin(base + "/", url.strip())
    partes = urlparse(completa)
    return completa if partes.scheme == "https" and partes.hostname == urlparse(base).hostname else None


def zip_valido(archivo: Path, nombre: Path | None = None) -> bool:
    """
    ``archivo`` es un ZIP legible, o no se espera que lo sea (``nombre``, por defecto el mismo
    ``archivo``, no termina en ``.zip``). Detecta descargas cortadas y páginas de error del servidor.
    """
    return (nombre or archivo).suffix.lower() != ".zip" or zipfile.is_zipfile(archivo)


def ya_extraido(member: zipfile.ZipInfo, destino: Path) -> bool:
    """``destino`` ya tiene el archivo completo (mismo tamaño que dentro del ZIP)."""
    return destino.is_file() and destino.stat().st_size == member.file_size


def extraer_miembro(z: zipfile.ZipFile, member: zipfile.ZipInfo, destino: Path) -> None:
    """
    Copia ``member`` a ``destino`` por partes, primero con otro nombre (``.part``) y renombrando
    al terminar: si se interrumpe (Ctrl+C, disco lleno), no queda un archivo a medias con el
    nombre final que la próxima descarga daría por bueno.
    """
    tmp = _temporal(destino)
    try:
        with z.open(member) as src, open(tmp, "wb") as dst:
            shutil.copyfileobj(src, dst, 1 << 20)
        tmp.replace(destino)
    finally:
        tmp.unlink(missing_ok=True)
