"""
EAM Downloader & Extractor
==========================
Pipeline automatizado para descubrir, descargar y extraer el histórico completo
de microdatos de la Encuesta Anual Manufacturera (EAM) del DANE (1992 - 2024)
desde el Archivo Nacional de Datos (ANDA).

Reglas de extracción de formatos:
  1. Prioridad 1: Archivo .csv (utilizado en la gran mayoría de la serie histórica).
  2. Prioridad 2: Archivo .txt delimitado (si no existe .csv, como en 2023).
  3. Prioridad 3: Conversión de .dta a .txt tabulado (si no existe .csv ni .txt, como en 2024).

NOTAS METODOLÓGICAS IMPORTANTES:
  - Clasificación CIIU (Rupturas metodológicas):
      * 1992 - 1999: CIIU Rev. 2 A.C. (códigos de 4 dígitos, ej. 3111).
      * 2000 - 2013: CIIU Rev. 3 A.C. (códigos de 4 dígitos, ej. 1511).
      * 2014 - 2024: CIIU Rev. 4 A.C. (códigos de 4 dígitos, ej. 1011).
    Para construir series continuas entre décadas, se requiere aplicar tablas
    de correlación/concordancia CIIU.
  - Identificación de Panel (Seguimiento longitudinal):
      * Las variables clave de identificación de planta y empresa son 'nordemp'
        (número de orden de empresa) y 'nordest' (número de orden de establecimiento).
      * En los microdatos anonimizados públicos de ANDA, verificar la consistencia
        temporal del algoritmo de anonimización según el período de estudio.

Autor original: Equipo de Investigación (adaptado para dane-data)
Licencia: MIT
Versión: 1.0.0
"""

import os
import io
import re
import sys
import json
import time
import zipfile
import logging
import argparse
import unicodedata
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from .._hooks import ProgressMixin

__version__ = "1.0.0"

log = logging.getLogger("dane_data.eam")

# Catálogos oficiales verificados en ANDA (DANE) para la EAM (1992-2024)
EAM_KNOWN_CATALOGS = {
    # 1992-1994: Catálogo 563
    "1992": ("563", "EAM_1992.zip", "https://microdatos.dane.gov.co/index.php/catalog/563/download/10179"),
    "1993": ("563", "EAM_1993.zip", "https://microdatos.dane.gov.co/index.php/catalog/563/download/10180"),
    "1994": ("563", "EAM_1994.zip", "https://microdatos.dane.gov.co/index.php/catalog/563/download/10181"),
    # 1995-1999: Catálogo 492
    "1995": ("492", "EAM_1995.zip", "https://microdatos.dane.gov.co/index.php/catalog/492/download/10182"),
    "1996": ("492", "EAM_1996.zip", "https://microdatos.dane.gov.co/index.php/catalog/492/download/10183"),
    "1997": ("492", "EAM_1997.zip", "https://microdatos.dane.gov.co/index.php/catalog/492/download/10184"),
    "1998": ("492", "EAM_1998.zip", "https://microdatos.dane.gov.co/index.php/catalog/492/download/10185"),
    "1999": ("492", "EAM_1999.zip", "https://microdatos.dane.gov.co/index.php/catalog/492/download/10186"),
    # 2000-2007: Catálogo 494
    "2000": ("494", "EAM_2000.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10187"),
    "2001": ("494", "EAM_2001.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10188"),
    "2002": ("494", "EAM_2002.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10189"),
    "2003": ("494", "EAM_2003.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/14158"),
    "2004": ("494", "EAM_2004.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10191"),
    "2005": ("494", "EAM_2005.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10192"),
    "2006": ("494", "EAM_2006.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10193"),
    "2007": ("494", "EAM_2007.zip", "https://microdatos.dane.gov.co/index.php/catalog/494/download/10194"),
    # 2008-2012: Catálogo 493
    "2008": ("493", "EAM_2008.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10195"),
    "2009": ("493", "EAM_2009.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10196"),
    "2010": ("493", "EAM_2010.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10197"),
    "2011": ("493", "EAM_2011.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10198"),
    "2012": ("493", "EAM_2012.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10199"),
    # 2013-2015: Catálogo 491
    "2013": ("491", "EAM_2013.zip", "https://microdatos.dane.gov.co/index.php/catalog/491/download/10200"),
    "2014": ("491", "EAM_2014.zip", "https://microdatos.dane.gov.co/index.php/catalog/491/download/10201"),
    "2015": ("491", "EAM_2015.zip", "https://microdatos.dane.gov.co/index.php/catalog/491/download/10202"),
    # 2016-2017: Catálogo 523
    "2016": ("523", "EAM_2016.zip", "https://microdatos.dane.gov.co/index.php/catalog/523/download/10203"),
    "2017": ("523", "Estructura - EAM - 2017.zip", "https://microdatos.dane.gov.co/index.php/catalog/523/download/10329"),
    # 2018+: Catálogos individuales
    "2018": ("650", "EAM_2018.zip", "https://microdatos.dane.gov.co/index.php/catalog/650/download/12432"),
    "2019": ("694", "EAM_2019.zip", "https://microdatos.dane.gov.co/index.php/catalog/694/download/14186"),
    "2020": ("724", "EAM_2020.zip", "https://microdatos.dane.gov.co/index.php/catalog/724/download/20937"),
    "2021": ("802", "EAM_2021.zip", "https://microdatos.dane.gov.co/index.php/catalog/802/download/22877"),
    "2022": ("836", "EAM_ANONIMIZADA_2022.zip", "https://microdatos.dane.gov.co/index.php/catalog/836/download/24325"),
    "2023": ("871", "BDATOS-EAM-2023.zip", "https://microdatos.dane.gov.co/index.php/catalog/871/download/24120"),
    "2024": ("888", "BDATOS-EAM-2024.zip", "https://microdatos.dane.gov.co/index.php/catalog/888/download/24429"),
}

# Módulos TIC opcionales
EAM_TIC_CATALOGS = {
    "2008": ("493", "EAM_TIC_2008.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10336"),
    "2009": ("493", "EAM_TIC_2009.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10337"),
    "2010": ("493", "EAM_TIC_2010.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10338"),
    "2011": ("493", "EAM_TIC_2011.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10339"),
    "2012": ("493", "EAM_TIC_2012.zip", "https://microdatos.dane.gov.co/index.php/catalog/493/download/10340"),
    "2013": ("491", "EAM_TIC_2013.zip", "https://microdatos.dane.gov.co/index.php/catalog/491/download/10333"),
    "2014": ("491", "EAM_TIC_2014.zip", "https://microdatos.dane.gov.co/index.php/catalog/491/download/10334"),
    "2015": ("491", "EAM_TIC_2015.zip", "https://microdatos.dane.gov.co/index.php/catalog/491/download/10335"),
    "2016": ("523", "EAM_TIC_2016.zip", "https://microdatos.dane.gov.co/index.php/catalog/523/download/10332"),
    "2017": ("523", "EAM_TIC_2017.zip", "https://microdatos.dane.gov.co/index.php/catalog/523/download/10331"),
    "2018": ("650", "EAM_TIC.zip", "https://microdatos.dane.gov.co/index.php/catalog/650/download/12484"),
}


def sanitize_member_name(raw_name: str) -> str:
    """Corrige codificación CP850/CP437/Latin1 habitual en ZIPs generados en Windows."""
    clean = Path(raw_name).name
    try:
        clean = clean.encode("cp437").decode("utf-8")
    except Exception:
        pass
    return clean


class EAMDownloader(ProgressMixin):
    def __init__(self, base_dir="data", keep_zips=True, extract_data=True, include_tic=False,
                 progress=None, should_stop=None):
        self.progress = progress
        self.should_stop = should_stop
        self.base_url = "https://microdatos.dane.gov.co"
        self.base_dir = Path(base_dir)
        self.metadata_dir = self.base_dir / "metadata"
        self.raw_dir = self.base_dir / "raw_zips"
        self.data_dir = self.base_dir / "datos"
        self.keep_zips = keep_zips
        self.extract_data = extract_data
        self.include_tic = include_tic

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

        self._setup_directories()

    def _setup_directories(self):
        """Crea la estructura de carpetas local."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        if self.extract_data:
            self.data_dir.mkdir(parents=True, exist_ok=True)
        log.info(f"Directorio base de la EAM configurado en: {self.base_dir.resolve()}")

    def discover_catalogs(self) -> dict:
        """
        Descubre dinámicamente los catálogos y archivos de la EAM en ANDA.
        Retorna un diccionario {año: (catalog_id, filename, download_url)}.
        """
        log.info("Sincronizando catálogos de la EAM con el portal ANDA del DANE...")
        discovered = {}

        # IDs base de los catálogos que contienen la serie EAM
        catalog_ids = [
            "563", "492", "494", "493", "491", "523",
            "650", "694", "724", "802", "836", "871", "888"
        ]

        for cid in catalog_ids:
            microdata_url = f"{self.base_url}/index.php/catalog/{cid}/get-microdata"
            try:
                res = self.session.get(microdata_url, timeout=20)
                res.raise_for_status()
                matches = re.findall(r"mostrarModal\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", res.text)
                for name, url in matches:
                    if "tic" in name.lower():
                        continue
                    m = re.search(r"(199\d|20\d\d)", name)
                    if m:
                        yr = m.group(1)
                        if yr not in discovered:
                            discovered[yr] = (cid, name.strip(), url.strip())
            except Exception as e:
                log.warning(f"Error consultando microdatos para catálogo {cid}: {e}")

        # Unificar con los catálogos verificados
        final_catalogs = dict(EAM_KNOWN_CATALOGS)
        final_catalogs.update(discovered)

        log.info(f"Se identificaron archivos de EAM para {len(final_catalogs)} años: {sorted(final_catalogs.keys())}")
        return final_catalogs

    def fetch_metadata(self, catalog_id: str):
        """Obtiene y guarda localmente la metadata metodológica JSON del catálogo."""
        metadata_path = self.metadata_dir / f"catalogo_{catalog_id}.json"
        if metadata_path.exists():
            return

        json_url = f"{self.base_url}/index.php/metadata/export/{catalog_id}/json"
        try:
            res = self.session.get(json_url, timeout=20)
            if res.status_code == 200:
                data = res.json()
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                log.info(f"Metadata metodológica guardada: {metadata_path.name}")
        except Exception as e:
            log.warning(f"No se pudo descargar metadata JSON para catálogo {catalog_id}: {e}")

    def download_file(self, url: str, dest_path: Path, max_retries: int = 3) -> bool:
        """Descarga un archivo con streaming y verificación de integridad."""
        if dest_path.exists() and dest_path.stat().st_size > 0:
            log.info(f"Archivo ya existente: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.1f} MB). Saltando descarga.")
            return True

        temp_dest = dest_path.with_suffix(dest_path.suffix + ".part")

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

                temp_dest.rename(dest_path)
                size_mb = dest_path.stat().st_size / 1024 / 1024
                log.info(f"✓ Descarga completada: {dest_path.name} ({size_mb:.2f} MB)")
                return True

            except Exception as e:
                if type(e).__name__ == "DownloadCancelled":
                    if temp_dest.exists():
                        temp_dest.unlink()
                    raise
                log.error(f"Error descargando {dest_path.name} (intento {attempt}): {e}")
                if temp_dest.exists():
                    temp_dest.unlink()
                time.sleep(2 * attempt)

        return False

    def extract_preferred_format(self, zip_path: Path, dest_dir: Path) -> list:
        """
        Extrae el archivo de datos con la jerarquía de preferencia solicitada:
          1. Archivo .csv (primera opción).
          2. Archivo .txt delimitado (si no existe .csv, como en 2023).
          3. Conversión de .dta a .txt tabulado (si no existe .csv ni .txt, como en 2024).
        """
        if not zip_path.exists():
            return []

        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted_files = []

        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                members = [m for m in z.infolist() if not m.is_dir()]

                # 1. Buscar .csv
                csv_members = [m for m in members if m.filename.lower().endswith(".csv")]
                if csv_members:
                    for m in csv_members:
                        clean_name = sanitize_member_name(m.filename)
                        target = dest_dir / clean_name
                        with z.open(m) as src, open(target, "wb") as dst:
                            dst.write(src.read())
                        extracted_files.append(target)
                    log.info(f"  → Extraído formato CSV: {[f.name for f in extracted_files]}")
                    return extracted_files

                # 2. Buscar .txt
                txt_members = [m for m in members if m.filename.lower().endswith(".txt")]
                if txt_members:
                    for m in txt_members:
                        clean_name = sanitize_member_name(m.filename)
                        target = dest_dir / clean_name
                        with z.open(m) as src, open(target, "wb") as dst:
                            dst.write(src.read())
                        extracted_files.append(target)
                    log.info(f"  → Extraído formato TXT (alternativa al no haber CSV): {[f.name for f in extracted_files]}")
                    return extracted_files

                # 3. Si no hay .csv ni .txt (caso año 2024), extraer/convertir .dta a .txt
                dta_members = [m for m in members if m.filename.lower().endswith(".dta")]
                if dta_members:
                    for m in dta_members:
                        clean_name = sanitize_member_name(m.filename)
                        txt_name = Path(clean_name).stem + ".txt"
                        target_txt = dest_dir / txt_name

                        try:
                            import pandas as pd
                            dta_bytes = io.BytesIO(z.read(m))
                            df = pd.read_stata(dta_bytes)
                            df.to_csv(target_txt, sep="\t", index=False)
                            extracted_files.append(target_txt)
                            log.info(f"  → Generado formato TXT tabulado a partir del archivo Stata .dta: {target_txt.name}")
                        except Exception as e:
                            # Respaldo en caso de fallo de pandas: extraer directamente el .dta
                            target_dta = dest_dir / clean_name
                            with z.open(m) as src, open(target_dta, "wb") as dst:
                                dst.write(src.read())
                            extracted_files.append(target_dta)
                            log.warning(f"  → Extraído .dta directamente por error al convertir a TXT: {e}")

                    return extracted_files

        except zipfile.BadZipFile:
            log.error(f"El archivo {zip_path.name} está corrupto o no es un ZIP válido.")
        except Exception as e:
            log.error(f"Error procesando {zip_path.name}: {e}")

        return extracted_files

    def process_year(self, year: str, catalog_id: str, zip_filename: str, download_url: str):
        """Descarga y procesa un año específico de la EAM."""
        log.info(f"\n{'='*20} Procesando EAM Año {year} (Catálogo {catalog_id}) {'='*20}")

        # 1. Guardar metadata metodológica
        self.fetch_metadata(catalog_id)

        year_raw_dir = self.raw_dir / year
        year_raw_dir.mkdir(parents=True, exist_ok=True)

        year_data_dir = self.data_dir / year
        if self.extract_data:
            year_data_dir.mkdir(parents=True, exist_ok=True)

            # Comprobar si ya existe el archivo de datos (.csv o .txt)
            existing_data = list(year_data_dir.glob("*.csv")) + list(year_data_dir.glob("*.txt")) + list(year_data_dir.glob("*.CSV")) + list(year_data_dir.glob("*.TXT"))
            if existing_data:
                log.info(f"Año {year} ya cuenta con datos extraídos ({[f.name for f in existing_data]}). Saltando descarga.")
                return

        # 2. Descargar paquete ZIP
        safe_name = "".join(c for c in zip_filename if c.isalnum() or c in (" ", ".", "_", "-")).strip()
        zip_dest = year_raw_dir / safe_name

        success = self.download_file(download_url, zip_dest)

        # 3. Extraer formato preferido (.csv -> .txt -> .dta convertido)
        if success and self.extract_data:
            self.extract_preferred_format(zip_dest, year_data_dir)

            if not self.keep_zips and zip_dest.exists():
                zip_dest.unlink()

        # 4. Descargar satélite TIC si fue solicitado
        if self.include_tic and year in EAM_TIC_CATALOGS:
            tic_cid, tic_name, tic_url = EAM_TIC_CATALOGS[year]
            tic_zip = year_raw_dir / tic_name
            log.info(f"Descargando módulo TIC para {year}...")
            tic_ok = self.download_file(tic_url, tic_zip)
            if tic_ok and self.extract_data:
                tic_data_dir = year_data_dir / "TIC"
                self.extract_preferred_format(tic_zip, tic_data_dir)
                if not self.keep_zips and tic_zip.exists():
                    tic_zip.unlink()

        time.sleep(1)

    def run_pipeline(self, target_years=None):
        """Ejecuta el pipeline de descarga de la EAM para todos o los años seleccionados."""
        catalogs = self.discover_catalogs()

        years_to_process = sorted(catalogs.keys(), key=lambda y: int(y))
        if target_years:
            target_years = [str(y) for y in target_years]
            years_to_process = [y for y in years_to_process if y in target_years]

        log.info(f"Iniciando descarga de la EAM para {len(years_to_process)} años: {years_to_process}")

        for i, year in enumerate(years_to_process):
            self._check_stop()
            self._emit(i / max(len(years_to_process), 1), f"Procesando año {year}")
            cid, fn, url = catalogs[year]
            self.process_year(year, cid, fn, url)

        self._emit(1.0, "Descarga terminada")
        log.info("\n¡Pipeline de la EAM finalizado exitosamente!")
        log.info(f"Datos organizados en: {self.data_dir.resolve()}")
