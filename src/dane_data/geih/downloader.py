"""
GEIH Downloader & Extractor
===========================
Automated pipeline to discover, download, and extract microdata from Colombia's
Gran Encuesta Integrada de Hogares (GEIH) and its official Empalme Series (CNPV 2018)
from DANE's National Data Archive (ANDA).

Features:
  - Exclusive CSV extraction for key modules (Housing, Demographics, Labor force,
    Employed, Other forms of work).
  - Preserves household, individual, and geographic identifiers (DIRECTORIO,
    SECUENCIA_P, ORDEN, HOGAR, DPTO, MPIO, CLASE, AREA, FEX_C).
  - Automatic handling of nested archives, non-breaking spaces, and historical naming typos.
  - Resilient downloads with retry backoff and incremental caching (skips already extracted months).

Autor original: Luis Ramírez (adaptado para dane-data)
License: MIT
Version: 1.0.0
"""

import io
import re
import json
import time
import zipfile
import logging
import unicodedata
from pathlib import Path
from bs4 import BeautifulSoup

from .._hooks import DescargadorANDA, extraer_miembro, ya_extraido
from .loader import EXTENSIONES, _pick_files, MesGEIH, month_from_folder

MARCADOR = ".dane_data_ok"  # se escribe tras una extracción exitosa

# Nombre del módulo en el descargador -> nombre en el cargador / en MesGEIH.faltantes
_MODULO_CARGADOR = {
    "vivienda": "vivienda", "caracteristicas": "caracteristicas", "fuerza_trabajo": "fuerza",
    "ocupados": "ocupados", "desocupados": "desocupados", "inactivos": None,  # se deduce de PET
    "otras_formas_trabajo": "otras",
}


def faltantes_mes(month_dir: Path, modules) -> list[str]:
    """
    Módulos pedidos que no están en ``month_dir`` (búsqueda recursiva).

    Reutiliza la lógica del cargador: en 2020 y en la serie de empalme las
    marcas OCI/DSI vienen dentro de Características, así que la ausencia del
    archivo de Desocupados no cuenta como faltante.
    """
    files = [f for f in month_dir.rglob("*") if f.is_file() and f.suffix.lower() in EXTENSIONES] if month_dir.is_dir() else []
    if not files:
        return ["todos"]
    mes = MesGEIH(0, 0, month_dir, _pick_files(files))
    pedidos = {_MODULO_CARGADOR[m] for m in modules} - {None}
    falta = set(mes.faltantes)
    falta |= {m for m in pedidos & {"vivienda", "otras"} if m not in mes.archivos}
    return sorted(falta & pedidos)


def _marcador_cubre(dest: Path, modules) -> bool:
    """
    El marcador existe y la extracción que lo escribió incluyó todos los ``modules``.
    Los marcadores anteriores no registran módulos: no se confía en ellos.
    """
    try:
        data = json.loads((dest / MARCADOR).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    return set(modules) <= set(data.get("modulos", []))


def mes_completo(month_dir: Path, modules) -> bool:
    return _marcador_cubre(month_dir, modules) or not faltantes_mes(month_dir, modules)


def _escribir_marcador(dest: Path, zip_name: str, n: int, modules) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    data = {"zip": zip_name, "csv_extraidos": n, "modulos": sorted(modules)}
    (dest / MARCADOR).write_text(json.dumps(data), encoding="utf-8")

__version__ = "1.0.0"

log = logging.getLogger("dane_data.geih")

# Catálogos oficiales verificados en ANDA (DANE) para la GEIH Principal Nacional
KNOWN_CATALOGS = {
    "2007": "317",
    "2008": "206",
    "2009": "207",
    "2010": "205",
    "2011": "182",
    "2012": "77",
    "2013": "68",
    "2014": "328",
    "2015": "356",
    "2016": "427",
    "2017": "458",
    "2018": "547",
    "2019": "599",
    "2020": "780",
    "2021": "701",
    "2022": "771",
    "2023": "782",
    "2024": "819",
    "2025": "853",
    "2026": "900",
}

# Catálogos oficiales verificados en ANDA (DANE) para la Serie de Empalme (Marco CNPV 2018)
EMPALME_CATALOGS = {
    "2010": "765",
    "2011": "755",
    "2012": "760",
    "2013": "761",
    "2014": "756",
    "2015": "762",
    "2016": "757",
    "2017": "763",
    "2018": "758",
    "2019": "759",
    "2020": "764",
}

# Patrones por módulo (nombres normalizados sin tildes). Se aceptan variaciones
# frecuentes de los nombres publicados por DANE.
MODULE_PATTERNS = {
    "vivienda": ("vivienda", "hogar"),
    "caracteristicas": ("caracteristica", "caracterica", "personas"),
    "fuerza_trabajo": ("fuerza de trabajo",),
    "ocupados": ("ocupados",),
    "desocupados": ("desocupados", "deocupados"),
    "inactivos": ("inactivos", "no ocupado"),
    "otras_formas_trabajo": ("otras formas de trabajo", "otras actividades"),
}
DEFAULT_MODULES = tuple(MODULE_PATTERNS)

# CSV del ANDA (serie principal) que no se pueden leer bien: para esos meses se baja otro
# formato del mismo catálogo. Ver README, "Diferencias con la documentación del DANE".
# Año -> {mes: formato}; el mes None vale para todo el año.
CSV_DANADOS = {
    "2008": {None: "txt"},  # FEX_C_2011 sin punto decimal ("849.491.032.387.525")
    "2011": {None: "txt"},
    "2021": {9: "dta"},     # separado por espacios, y el texto libre también los tiene
}
EXCLUDE_MODULE_PATTERNS = ("otros ingresos", "migracion", "tipo de investigacion")


def normalize_text(text: str) -> str:
    """Elimina acentos/diacríticos y normaliza espacios no separables (NBSP)."""
    text = text.replace("\xa0", " ").replace("\u202f", " ").replace("\u200b", "")
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    ).lower()


def _formato(nombre: str) -> str | None:
    """Formato de un ZIP del ANDA según su nombre ("Marzo_txt.zip" -> "txt"); None si no lo dice."""
    n = normalize_text(nombre)
    for formato, marcas in (("csv", ("csv",)), ("txt", ("txt",)), ("sav", ("sav", "spss")), ("dta", ("dta",))):
        if any(m in n for m in marcas):
            return formato
    return None


def is_target_csv(filename: str, modules=DEFAULT_MODULES, extensiones=(".csv",)) -> bool:
    """
    Determina si un archivo dentro del ZIP es un CSV correspondiente a uno de los
    módulos solicitados:
      - Identificación de vivienda y hogar
      - Características generales (Personas)
      - Fuerza de trabajo
      - Ocupados
      - Otras formas de trabajo / Otras actividades
    """
    if not filename.lower().endswith(tuple(extensiones)):
        return False

    norm_name = normalize_text(filename)

    # Si coincide con exclusiones explícitas (e.g. 'no ocupados', 'desocupados')
    if any(ex in norm_name for ex in EXCLUDE_MODULE_PATTERNS):
        return False

    # Debe contener alguno de los patrones de los módulos objetivo
    return any(
        pattern in norm_name
        for module in modules
        for pattern in MODULE_PATTERNS[module]
    )


def sanitize_member_name(raw_name: str) -> str:
    """Limpia caracteres corruptos habituales de codificación DOS/Windows en ZIPs."""
    name = Path(raw_name).name
    # Intentar decodificación limpia
    try:
        clean = name.encode("cp437").decode("utf-8")
    except Exception:
        clean = name

    # Reemplazar posibles caracteres de dibujo de cajas o fallos de tabla OEM
    for bad, good in [("╡rea", "Area"), ("µrea", "Area"), ("CaracterÝsticas", "Caracteristicas"), ("Caracter¡sticas", "Caracteristicas"), ("educaci¾n", "educacion"), ("educaci¢n", "educacion")]:
        clean = clean.replace(bad, good)

    return clean


class GEIHDownloader(DescargadorANDA):
    log = log

    def __init__(self, base_dir="data", keep_zips=True, extract_csv=True, is_empalme=False, modules=None,
                 progress=None, should_stop=None):
        self.progress = progress
        self.should_stop = should_stop
        self.is_empalme = is_empalme
        # A diferencia del script original, base_dir ya es la raíz de la serie
        # (la serie de empalme no se anida automáticamente en base_dir/empalme).
        self.base_dir = Path(base_dir)
        self.metadata_dir = self.base_dir / "metadata"
        self.raw_dir = self.base_dir / "raw_zips"
        self.csv_dir = self.base_dir / "datos_csv"
        self.keep_zips = keep_zips
        self.extract_csv = extract_csv
        if isinstance(modules, str):  # un solo módulo: tuple("ocupados") lo partiría en letras
            modules = [modules]
        modules = DEFAULT_MODULES if modules is None else tuple(modules)
        if not modules:
            raise ValueError("modules está vacío: elija al menos un módulo, o None para todos.")
        if desconocidos := [m for m in modules if m not in MODULE_PATTERNS]:
            raise ValueError(f"Módulos desconocidos: {desconocidos}. Opciones: {list(MODULE_PATTERNS)}.")
        self.modules = modules

        self._abrir_sesion()

        self._setup_directories()

    def _setup_directories(self):
        """Crea la estructura de carpetas local."""
        self.metadata_dir.mkdir(parents=True, exist_ok=True)
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        if self.extract_csv:
            self.csv_dir.mkdir(parents=True, exist_ok=True)
        series_label = "Serie de Empalme (2010-2020)" if self.is_empalme else "Serie Principal (2007-2026)"
        log.info(f"Directorio base configurado para [{series_label}] en: {self.base_dir.resolve()}")

    def discover_catalogs(self) -> dict:
        """
        Descubre dinámicamente los catálogos en ANDA mediante búsqueda AJAX.
        Si la búsqueda falla o está incompleta, usa los catálogos verificados como respaldo.
        """
        if self.is_empalme:
            log.info("Buscando catálogos de la Serie de Empalme GEIH en el portal del DANE...")
            discovered = {}
            for page in [1, 2]:
                search_url = f"{self.base_url}/index.php/catalog/search"
                params = {"sk": "Empalme", "ps": 100, "page": page}
                headers = {"X-Requested-With": "XMLHttpRequest"}
                try:
                    res = self.session.get(search_url, params=params, headers=headers, timeout=20)
                    res.raise_for_status()
                    soup = BeautifulSoup(res.text, "html.parser")
                    for a in soup.find_all("a", href=True):
                        m = re.search(r"/catalog/(\d+)$", a["href"])
                        if not m:
                            continue
                        cat_id = m.group(1)
                        title = a.get_text(strip=True)
                        if "GEIH" in title.upper() and "EMPALME" in title.upper():
                            yr_match = re.search(r"\b(20\d\d)\b", title)
                            if yr_match:
                                discovered[yr_match.group(1)] = cat_id
                except Exception as e:
                    log.warning(f"Error buscando catálogos de empalme en página {page}: {e}")
            final_catalogs = dict(EMPALME_CATALOGS)
            final_catalogs.update(discovered)
            log.info(f"Catálogos de Empalme identificados para {len(final_catalogs)} años: {sorted(final_catalogs.keys())}")
            return final_catalogs

        log.info("Buscando catálogos de la GEIH Nacional en el portal del DANE...")
        discovered = {}
        page = 1
        max_pages = 5

        while page <= max_pages:
            search_url = f"{self.base_url}/index.php/catalog/search"
            params = {"sk": "GEIH", "ps": 100, "page": page}
            headers = {"X-Requested-With": "XMLHttpRequest"}

            try:
                res = self.session.get(search_url, params=params, headers=headers, timeout=20)
                res.raise_for_status()
                soup = BeautifulSoup(res.text, "html.parser")

                found_on_page = 0
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    m = re.search(r"/catalog/(\d+)$", href)
                    if not m:
                        continue
                    cat_id = m.group(1)
                    title = a.get_text(strip=True)

                    if not title or not ("GEIH" in title.upper() or "GRAN ENCUESTA" in title.upper()):
                        continue

                    # Filtrar módulos satélite y submuestras territoriales
                    norm_title = normalize_text(title)
                    is_satellite = any(w in norm_title for w in [
                        "san andres", "amazon", "orinoqu", "ciudades intermedias",
                        "infantil", "mti", "mfpt", "formacion", "migracion",
                        "tic", "mtic", "etnia", "empalme", "factores de expansion", "ciiu"
                    ])

                    if not is_satellite:
                        year_match = re.search(r"\b(200[6-9]|20[1-3][0-9])\b", title)
                        if year_match:
                            year = year_match.group(1)
                            if year not in discovered:
                                discovered[year] = cat_id
                                found_on_page += 1

                if found_on_page == 0:
                    break
                page += 1

            except Exception as e:
                log.warning(f"No se pudo completar la búsqueda en página {page}: {e}")
                break

        # Combinar con los catálogos verificados para garantizar cobertura completa
        final_catalogs = dict(KNOWN_CATALOGS)
        final_catalogs.update(discovered)

        log.info(f"Catálogos identificados para {len(final_catalogs)} años: {sorted(final_catalogs.keys())}")
        return final_catalogs

    def fetch_metadata(self, year: str, catalog_id: str) -> dict:
        """Obtiene y almacena el JSON metodológico de ANDA."""
        metadata_path = self.metadata_dir / f"{year}.json"
        if metadata_path.exists():
            try:
                with open(metadata_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        json_url = f"{self.base_url}/index.php/metadata/export/{catalog_id}/json"
        try:
            res = self.session.get(json_url, timeout=20)
            if res.status_code == 200:
                data = res.json()
                with open(metadata_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                log.info(f"Metadata metodológica guardada: {metadata_path.name}")
                return data
            else:
                log.warning(f"Endpoint metadata JSON retornó HTTP {res.status_code} para catálogo {catalog_id}")
        except Exception as e:
            log.warning(f"No se pudo descargar metadata JSON para {year}: {e}")
        return {}

    def _enlaces(self, catalog_id: str) -> dict:
        """``{url: nombre}`` de todos los archivos de /get-microdata del catálogo."""
        microdata_url = f"{self.base_url}/index.php/catalog/{catalog_id}/get-microdata"
        try:
            res = self.session.get(microdata_url, timeout=20)
            res.raise_for_status()
        except Exception as e:
            log.error(f"Error accediendo a página de microdatos del catálogo {catalog_id}: {e}")
            return {}

        # Extraer parámetros de onclick="mostrarModal('filename', 'download_url')"
        matches = re.findall(r"mostrarModal\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", res.text)
        if not matches:
            log.warning(f"No se encontraron enlaces de descarga en catálogo {catalog_id}")
            return {}

        # Deduplicar por URL de descarga
        unique_files = {}
        for name, url in matches:
            clean_url = url.strip()
            clean_name = name.strip()
            if clean_url not in unique_files:
                unique_files[clean_url] = clean_name
        return unique_files

    def get_csv_download_links(self, catalog_id: str) -> list:
        """
        Extrae los enlaces de descarga para archivos CSV desde /get-microdata.
        Maneja dos épocas del DANE:
          1. 2007-2021: ZIPs separados por formato (*.csv.zip)
          2. 2022-2026: ZIPs mensuales completos que contienen CSV, DTA y SAV en su interior
        """
        unique_files = self._enlaces(catalog_id)
        if not unique_files:
            return []

        # 1. Verificar si existen archivos con extensión específica de CSV (ej. Enero.csv.zip)
        csv_specific = [
            {"name": name, "url": url}
            for url, name in unique_files.items()
            if "csv" in name.lower()
        ]

        if csv_specific:
            return csv_specific

        # 2. Si no hay archivos específicos de CSV (años 2022 en adelante),
        # los datos vienen empaquetados mensualmente (ej. Ene_2024.zip, Enero 2025.zip).
        # Descartamos archivos de documentación o complementarios no mensuales.
        monthly_bundles = []
        for url, name in unique_files.items():
            norm_name = normalize_text(name)
            # Ignorar FEX u otros zips de apoyo si no son los datos mensuales
            if "fex" in norm_name or "proyecciones" in norm_name:
                continue
            if norm_name.endswith(".zip"):
                monthly_bundles.append({"name": name, "url": url})

        return monthly_bundles

    def get_download_links(self, year: str, catalog_id: str) -> list:
        """
        Enlaces del año: el CSV de cada mes, salvo los meses de ``CSV_DANADOS``, que se
        cambian por otro formato del mismo catálogo (``item["formato"]``).
        """
        files = self.get_csv_download_links(catalog_id)
        danados = {} if self.is_empalme else CSV_DANADOS.get(str(year), {})
        if not danados:
            return files

        def formato_de(mes):
            return danados.get(mes, danados.get(None))

        alternos = {}
        for url, nombre in self._enlaces(catalog_id).items():
            mes = month_from_folder(nombre)
            buscado = formato_de(mes) if mes else None
            # Los ZIP sin formato en el nombre (p. ej. "Septiembre.zip" en 2021) traen el Stata.
            if buscado and (_formato(nombre) or "dta") == buscado and mes not in alternos:
                alternos[mes] = {"name": nombre, "url": url, "formato": buscado}
        out = []
        for item in files:
            mes = month_from_folder(item["name"])
            if mes and formato_de(mes) and mes in alternos:
                out.append(alternos[mes])
            else:
                if mes and formato_de(mes):
                    log.warning(f"El CSV de {item['name']} ({year}) está dañado y el ANDA no ofrece el formato "
                                f"{formato_de(mes)}: se baja el CSV.")
                out.append(item)
        return out

    def _extract_from_zip(self, z_obj: zipfile.ZipFile, dest_dir: Path, extensiones=(".csv",),
                          errores: list | None = None) -> int:
        """Extrae los módulos pedidos (también de ZIPs anidados); los fallos se anotan en ``errores``."""
        count = 0
        for member in z_obj.infolist():
            if member.is_dir():
                continue

            # Soporte para ZIPs anidados (ej. CSV.zip dentro de paquetes mensuales 2022-2024 o 1. Enero.zip en Empalme)
            if member.filename.lower().endswith(".zip") and not any(fmt in member.filename.lower() for fmt in ["dta", "sav", "spss"]):
                try:
                    nested_bytes = io.BytesIO(z_obj.read(member))
                    with zipfile.ZipFile(nested_bytes) as nested_z:
                        inner_stem = Path(member.filename).stem
                        # Solo el paquete anual del empalme trae un ZIP por mes (ej. "1. Enero.zip"):
                        # esos van a su subcarpeta. Cualquier otro ZIP anidado ("CSV.zip",
                        # "CSV 13.zip", "CSV_4.zip"...) se aplana en la carpeta del mes.
                        if self.is_empalme and month_from_folder(inner_stem) is not None:
                            target_dest = dest_dir / inner_stem
                        else:
                            target_dest = dest_dir
                        target_dest.mkdir(parents=True, exist_ok=True)
                        count += self._extract_from_zip(nested_z, target_dest, extensiones, errores)
                except Exception as e:
                    log.warning(f"Error abriendo ZIP anidado {member.filename}: {e}")
                    if errores is not None:
                        errores.append(f"{member.filename}: {e}")
                continue

            if is_target_csv(member.filename, self.modules, extensiones):
                clean_filename = sanitize_member_name(member.filename)
                target_file = dest_dir / clean_filename

                if not ya_extraido(member, target_file):
                    extraer_miembro(z_obj, member, target_file)
                count += 1
        return count

    def extract_requested_modules(self, zip_path: Path, dest_dir: Path, extensiones=(".csv",),
                                  errores: list | None = None) -> int:
        """
        Inspecciona el archivo ZIP descargado y extrae EXCLUSIVAMENTE los archivos CSV
        de los módulos solicitados:
          - Vivienda y Hogares / Datos del hogar y la vivienda
          - Características generales (Personas)
          - Fuerza de trabajo
          - Ocupados
          - Otras formas de trabajo / Otras actividades
        Conserva los identificadores de personas (DIRECTORIO, SECUENCIA_P, ORDEN)
        y geográficos (DPTO, MPIO, CLASE, AREA) ya incluidos en dichas tablas.
        Soporta además archivos ZIP anidados internamente (ej. CSV.zip o meses).
        Si se pasa ``errores``, se le agregan los fallos (ZIP dañado, ZIP anidado ilegible...).
        """
        if errores is None:
            errores = []
        if not zip_path.exists():
            errores.append(f"{zip_path.name}: no existe")
            return 0

        dest_dir.mkdir(parents=True, exist_ok=True)
        extracted_count = 0

        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                extracted_count = self._extract_from_zip(z, dest_dir, extensiones, errores)

            log.info(f"  → Extraídos {extracted_count} CSVs de módulos solicitados desde {zip_path.name}")
        except zipfile.BadZipFile:
            log.error(f"El archivo {zip_path.name} está corrupto o no es un ZIP válido; se borra para volver "
                      "a descargarlo.")
            errores.append(f"{zip_path.name}: ZIP dañado")
            zip_path.unlink(missing_ok=True)
        except Exception as e:
            log.error(f"Error extrayendo módulos de {zip_path.name}: {e}")
            errores.append(f"{zip_path.name}: {e}")

        return extracted_count

    def process_year(self, year: str, catalog_id: str, limit_files: int = None):
        """Descarga y procesa un año específico de la GEIH o de la Serie de Empalme."""
        series_label = f"Empalme Año {year}" if self.is_empalme else f"Año {year}"
        log.info(f"\n{'='*20} Procesando GEIH {series_label} (Catálogo {catalog_id}) {'='*20}")

        # 1. Metadata metodológica
        self.fetch_metadata(year, catalog_id)

        # 2. Obtener lista de archivos a descargar (CSV, u otro formato si el CSV está dañado)
        files = self.get_download_links(year, catalog_id)
        if not files:
            log.warning(f"No se encontraron enlaces válidos de microdatos para {year}")
            return

        if limit_files and limit_files > 0:
            files = files[:limit_files]

        log.info(f"Se procesarán {len(files)} archivos para {year}.")
        year_raw_dir = self.raw_dir / year
        year_raw_dir.mkdir(parents=True, exist_ok=True)

        year_csv_dir = self.csv_dir / year
        if self.extract_csv:
            year_csv_dir.mkdir(parents=True, exist_ok=True)

        # 3. Descargar y extraer selectivamente
        for item in files:
            self._check_stop()
            self._emit(None, f"{year}: {item['name']}")
            safe_name = "".join(c for c in item["name"] if c.isalnum() or c in (" ", ".", "_", "-")).strip()
            zip_dest = year_raw_dir / safe_name
            month_stem = safe_name.replace(".csv.zip", "").replace(".zip", "").strip()

            if self.is_empalme:
                # En la serie de empalme, el archivo anual empaqueta los 12 meses adentro
                meses = [d for d in year_csv_dir.iterdir() if d.is_dir() and month_from_folder(d.name)] \
                    if year_csv_dir.is_dir() else []
                if _marcador_cubre(year_csv_dir, self.modules) or (
                        len(meses) >= 12 and all(mes_completo(d, self.modules) for d in meses)):
                    log.info(f"Año {year} de Empalme ya está completo. Saltando.")
                    continue

                success = self.download_file(item["url"], zip_dest)
                if success and self.extract_csv:
                    errores = []
                    n = self.extract_requested_modules(zip_dest, year_csv_dir, errores=errores)
                    # Con un mes ilegible el marcador daría el año por completo y ese mes no se
                    # volvería a intentar: sin marcador, la próxima vez se revisa mes a mes.
                    if n and not errores:
                        _escribir_marcador(year_csv_dir, item["name"], n, self.modules)
                    elif errores:
                        log.warning(f"Empalme {year}: extracción con errores ({'; '.join(errores)}). "
                                    "Vuelva a descargar el año.")
                    if not self.keep_zips and zip_dest.exists():
                        zip_dest.unlink()
            else:
                month_csv_dir = year_csv_dir / month_stem
                # Se salta solo si una extracción anterior de estos mismos módulos terminó
                # (marcador) o, si no, si ya están todos los módulos pedidos. Contar archivos no
                # basta: así se colaron meses sin "No ocupados" (p. ej. marzo 2024).
                if mes_completo(month_csv_dir, self.modules):
                    log.info(f"Mes {month_stem} ({year}) ya está completo. Saltando.")
                    continue
                if month_csv_dir.is_dir():
                    falta = faltantes_mes(month_csv_dir, self.modules)
                    log.warning(f"Mes {month_stem} ({year}) incompleto (falta: {', '.join(falta)}). Se vuelve a extraer.")
                    # Un ZIP ya en disco puede ser el que produjo la extracción incompleta:
                    # se reutiliza (download_file lo salta) y se re-extrae con la lógica corregida.

                success = self.download_file(item["url"], zip_dest)
                if success and self.extract_csv:
                    errores = []
                    n = self.extract_requested_modules(zip_dest, month_csv_dir, (f".{item.get('formato', 'csv')}",),
                                                       errores=errores)
                    if n and not errores:
                        _escribir_marcador(month_csv_dir, item["name"], n, self.modules)
                    falta = faltantes_mes(month_csv_dir, self.modules)
                    if falta:
                        log.warning(f"El ZIP del DANE para {month_stem} ({year}) no trae: {', '.join(falta)}.")
                    if not self.keep_zips and zip_dest.exists():
                        zip_dest.unlink()

            time.sleep(1)

    def run_pipeline(self, target_years=None, limit_files: int = None):
        """Ejecuta el pipeline de descarga para todos los años o los años seleccionados."""
        catalogs = self.discover_catalogs()

        years_to_process = sorted(catalogs.keys(), key=lambda y: int(y))
        if target_years is not None:  # [] es "ningún año", no "todos"
            target_years = [str(y) for y in target_years]
            if desconocidos := [y for y in target_years if y not in catalogs]:
                log.warning(f"Años sin catálogo de la GEIH en el ANDA (se ignoran): {', '.join(desconocidos)}. "
                            f"Disponibles: {years_to_process[0]}–{years_to_process[-1]}.")
            years_to_process = [y for y in years_to_process if y in target_years]

        series_name = "Empalme" if self.is_empalme else "Principal"
        log.info(f"Iniciando descarga de la serie [{series_name}] para {len(years_to_process)} años: {years_to_process}")

        for i, year in enumerate(years_to_process):
            self._check_stop()
            self._emit(i / max(len(years_to_process), 1), f"Procesando año {year}")
            self.process_year(year, catalogs[year], limit_files=limit_files)
        self._emit(1.0, "Descarga terminada")

        log.info(f"\n¡Pipeline [{series_name}] finalizado exitosamente!")
        log.info(f"Datos CSV organizados en: {self.csv_dir.resolve()}")
