"""Ganchos de progreso y cancelación, y extracción de ZIPs, compartidos por los descargadores."""

from __future__ import annotations

import glob
import logging
import re
import shutil
import tempfile
import time
import uuid
import zipfile
import zlib
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

import requests

ProgressFn = Callable[[Optional[float], str], None]


class DownloadCancelled(Exception):
    """
    La descarga se detuvo porque ``detener()`` devolvió True.

    La lanzan ``dd.geih.download``, ``dd.eam.download`` y ``dd.eevv.download`` cuando se les pasa ``detener`` (la aplicación
    lo usa para su botón de cancelar). Los meses o años que ya terminaron quedan en disco y la próxima
    descarga los salta.

    Ejemplos
    --------
    >>> import time
    >>> import dane_data as dd
    >>> limite = time.time() + 60
    >>> try:  # doctest: +SKIP
    ...     dd.geih.download(2025, detener=lambda: time.time() > limite)
    ... except dd.DownloadCancelled:
    ...     print("Se detuvo al minuto; lo descargado se conserva.")
    """


class DescargadorANDA:
    """Lo común de los descargadores: la sesión HTTP, la descarga de cada ZIP y los ganchos de progreso y cancelación."""

    base_url = "https://microdatos.dane.gov.co"
    log = logging.getLogger("dane_data")  # cada descargador pone el suyo
    forzar = False  # volver a bajar y extraer aunque ya esté en disco
    progress: ProgressFn | None = None
    should_stop: Callable[[], bool] | None = None

    def _emit(self, fraction: float | None, message: str) -> None:
        if self.progress is not None:
            self.progress(fraction, message)

    def _check_stop(self) -> None:
        if self.should_stop is not None and self.should_stop():
            raise DownloadCancelled("Descarga cancelada por el usuario.")

    def _abrir_sesion(self) -> None:
        self.fallidos: list[str] = []
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def _enlaces(self, catalog_id: str) -> dict:
        """
        ``{url: nombre}`` de los archivos de /get-microdata del catálogo, sacados de ``mostrarModal('nombre', 'url')``.
        Solo los del ANDA por https (``url_del_anda``); vacío si la página no responde o no trae enlaces.
        """
        try:
            res = self.session.get(f"{self.base_url}/index.php/catalog/{catalog_id}/get-microdata", timeout=20)
            res.raise_for_status()
        except Exception as e:
            self.log.warning(f"No se pudo leer la página de microdatos del catálogo {catalog_id}: {e}")
            return {}
        matches = re.findall(r"mostrarModal\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", res.text)
        if not matches:
            self.log.warning(f"No se encontraron enlaces de descarga en catálogo {catalog_id}")
        enlaces = {}
        for name, url in matches:
            if (completa := url_del_anda(url, self.base_url)) is None:
                self.log.warning(f"Enlace de {name.strip()} fuera del ANDA o sin https, se ignora: {url.strip()}")
            else:
                enlaces.setdefault(completa, name.strip())
        return enlaces

    def download_file(self, url: str, dest_path: Path, max_retries: int = 3) -> bool:
        """
        Descarga un archivo con streaming y verificación de integridad.
        """
        log = self.log
        if not self.forzar and dest_path.exists() and dest_path.stat().st_size > 0:
            if zip_valido(dest_path):
                log.info(f"Archivo ya existente: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.1f} MB). Saltando descarga.")
                return True
            log.warning(f"{dest_path.name} en disco está dañado: se vuelve a descargar.")
            dest_path.unlink()

        temp_dest = _temporal(dest_path)
        # finally y no solo except: el botón Detener de Streamlit (StopException) y Ctrl+C no son Exception,
        # y como el nombre es único, ninguna descarga posterior pisaría el temporal que quedara.
        try:
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
                    raise
                except Exception as e:
                    log.error(f"Error descargando {dest_path.name} (intento {attempt}): {e}")
                    temp_dest.unlink(missing_ok=True)
                    time.sleep(2 * attempt)
            return False
        finally:
            temp_dest.unlink(missing_ok=True)

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


_PARTE_VIEJA = 86400  # segundos sin escribirse tras los cuales un temporal ya no es de ninguna descarga en curso


def _temporal(destino: Path) -> Path:
    """
    Nombre temporal único junto a ``destino``. Con uno fijo (``<archivo>.part``), dos descargas del mismo
    año a la vez (dos pestañas, la app en modo aula) escribirían el mismo archivo; en Windows la segunda
    falla porque está en uso.

    Antes borra los temporales de ``destino`` que llevan más de un día sin escribirse: los que dejó un proceso
    que se mató (cerrar la ventana de la app no deja correr los ``finally``), que con el nombre único nadie más borraría.
    """
    for viejo in destino.parent.glob(f"{glob.escape(destino.name)}.*.part"):
        try:
            if time.time() - viejo.stat().st_mtime > _PARTE_VIEJA:
                viejo.unlink()
        except OSError:  # otra sesión ya lo borró, o en Windows está abierto
            pass
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


def sanitize_member_name(raw_name: str) -> str:
    """Corrige codificación CP850/CP437/Latin1 habitual en ZIPs generados en Windows."""
    clean = Path(raw_name).name
    try:
        clean = clean.encode("cp437").decode("utf-8")
    except Exception:
        pass
    return clean


def ya_extraido(member: zipfile.ZipInfo, destino: Path) -> bool:
    """``destino`` ya tiene el archivo completo (mismo tamaño que dentro del ZIP)."""
    return destino.is_file() and destino.stat().st_size == member.file_size


def archivos_datos(carpeta: Path, extensiones) -> list[Path]:
    """Archivos de datos (con alguna de ``extensiones``) ya extraídos en ``carpeta``, sin entrar en subcarpetas como ``TIC/``."""
    if not carpeta.is_dir():
        return []
    return sorted(f for f in carpeta.iterdir() if f.is_file() and f.suffix.lower() in extensiones)


def extraer_aparte(extraer: Callable[[Path], list[Path]], carpeta: Path, temporal: Path, extensiones) -> bool:
    """
    Corre ``extraer(nueva)`` en una carpeta nueva dentro de ``temporal`` y, solo si sacó archivos, los pasa a ``carpeta`` y
    borra los archivos de datos que había y no se reemplazaron (los de antes, con ``forzar``). Si no sacó nada o falla,
    queda lo de antes. Devuelve si sacó algo.
    """
    nueva = Path(tempfile.mkdtemp(prefix="extraccion-", dir=temporal))
    try:
        extraidos = extraer(nueva)
        if not extraidos:
            return False
        carpeta.mkdir(parents=True, exist_ok=True)
        nuevos = set()
        for f in extraidos:
            f.replace(carpeta / f.name)
            nuevos.add(carpeta / f.name)
        for viejo in archivos_datos(carpeta, extensiones):
            if viejo not in nuevos:
                viejo.unlink()
        return True
    finally:
        shutil.rmtree(nueva, ignore_errors=True)


_DEFLATE64 = 9  # método de compresión que zipfile no lee; lo usa Windows con archivos grandes


def _copiar_deflate64(z: zipfile.ZipFile, member: zipfile.ZipInfo, dst) -> None:
    """Descomprime un miembro en Deflate64 (Educación 2021 de la ECV) con inflate64, leyendo los bytes crudos del ZIP."""
    import inflate64

    with open(z.filename, "rb") as f:
        f.seek(member.header_offset)
        cabecera = f.read(30)  # encabezado local: firma, versiones, banderas... y largo del nombre y del campo extra
        if cabecera[:4] != b"PK\x03\x04":
            raise zipfile.BadZipFile(f"Encabezado dañado en {member.filename}")
        f.seek(int.from_bytes(cabecera[26:28], "little") + int.from_bytes(cabecera[28:30], "little"), 1)
        inflador, faltan, crc = inflate64.Inflater(), member.compress_size, 0
        while faltan > 0:
            bloque = f.read(min(1 << 20, faltan))
            if not bloque:
                raise zipfile.BadZipFile(f"{member.filename} está incompleto")
            faltan -= len(bloque)
            datos = inflador.inflate(bloque)
            crc = zlib.crc32(datos, crc)
            dst.write(datos)
    if crc != member.CRC:
        raise zipfile.BadZipFile(f"CRC distinto en {member.filename}")


def extraer_miembro(z: zipfile.ZipFile, member: zipfile.ZipInfo, destino: Path) -> None:
    """
    Copia ``member`` a ``destino`` por partes, primero con otro nombre (``.part``) y renombrando
    al terminar: si se interrumpe (Ctrl+C, disco lleno), no queda un archivo a medias con el
    nombre final que la próxima descarga daría por bueno.
    """
    tmp = _temporal(destino)
    try:
        if member.compress_type == _DEFLATE64:
            with open(tmp, "wb") as dst:
                _copiar_deflate64(z, member, dst)
        else:
            with z.open(member) as src, open(tmp, "wb") as dst:
                shutil.copyfileobj(src, dst, 1 << 20)
        tmp.replace(destino)
    finally:
        tmp.unlink(missing_ok=True)
