"""
Descarga de la Encuesta Nacional de Calidad de Vida (ECV) del ANDA del DANE.

Un ZIP por año y capítulo, con el mismo archivo en CSV, Stata y SPSS (en 2025, dentro de una subcarpeta). Se extrae el
CSV, o el Stata si no hay CSV, a ``<raíz>/datos/<año>/<módulo>/``. Los nombres de los ZIP cambian según el año
(``Datos de la vivienda.zip`` hasta 2023, ``DBF-ENCV-Datos_vivienda-2024.zip``, ``DBF-ECV-Datos_vivienda-2025.zip``),
así que la tabla tiene el nombre y el número de descarga de cada uno. Un año nuevo se agrega a ``_CATALOGOS``.

En 2018 se baja además ``Factores de expansion 2018 basados en el CNPV 2018.zip``, que el DANE publicó aparte en 2020: el
``FEX_C`` de los capítulos de ese año es anterior al CNPV 2018. En 2020, ``Base_complementaria.zip`` del catálogo del IPM
2020: las estrategias de estudio en casa con las que el DANE armó la inasistencia escolar del IPM ese año.
"""

from __future__ import annotations

import logging
import time
import zipfile
from pathlib import Path

from .._hooks import DescargadorANDA, archivos_datos, extraer_aparte, extraer_miembro, sanitize_member_name
from .loader import _COMPLEMENTARIA, _FACTORES, _INTERNOS, EXTENSIONES, MODULOS

log = logging.getLogger("dane_data.ecv")

# Nombres de los ZIP de 2018–2023 (salvo Salud en 2023)
_NOMBRES = {
    "vivienda": "Datos de la vivienda.zip",
    "servicios": "Servicios del hogar.zip",
    "tenencia": "Tenencia y financiacion de la vivienda que ocupa el hogar.zip",
    "condiciones": "Condiciones de vida del hogar y tenencia de bienes.zip",
    "caracteristicas": "Caracteristicas y composicion del hogar.zip",
    "salud": "Salud.zip",
    "primera_infancia": "Atencion integral de los ninos y ninas menores de 5 anos.zip",
    "educacion": "Educacion.zip",
    "fuerza_trabajo": "Fuerza de trabajo.zip",
    "tic": "Tecnologias de informacion y comunicacion.zip",
    "trabajo_infantil": "Trabajo infantil.zip",
}
_ORDEN = list(_NOMBRES)  # las descargas de cada año van en este orden


def _numeros(*descargas: int) -> dict[str, tuple[str, int]]:
    """``{módulo: (nombre, descarga)}`` con los nombres de 2018–2023, en el orden de ``_NOMBRES``."""
    return {m: (_NOMBRES[m], d) for m, d in zip(_ORDEN, descargas)}


# Año -> (catálogo del ANDA, {módulo: (nombre del ZIP, número de descarga)}), de las páginas get-microdata.
# Orden de los números: vivienda, servicios, tenencia, condiciones, características, salud, primera infancia,
# educación, fuerza de trabajo, TIC, trabajo infantil.
_CATALOGOS = {
    2018: ("607", {**_numeros(11195, 10971, 10976, 10979, 10977, 10973, 10980, 10978, 10982, 10972, 10974),
                   _FACTORES: ("Factores de expansion 2018 basados en el CNPV 2018.zip", 20629)}),
    2019: ("678", _numeros(13705, 13706, 13714, 13716, 13707, 13708, 13709, 13710, 13711, 13712, 13713)),
    2020: ("718", _numeros(20603, 20605, 20608, 20601, 20599, 20607, 20610, 20606, 20600, 20595, 20604)),
    2021: ("734", _numeros(21949, 21950, 21122, 21829, 21121, 21834, 21118, 21831, 21832, 21835, 21132)),
    2022: ("793", _numeros(22591, 22597, 22604, 22714, 22586, 22596, 22585, 22592, 22593, 22598, 22601)),
    2023: ("827", {**_numeros(23439, 23444, 23447, 23481, 23435, 23480, 23434, 23441, 23442, 23445, 23448),
                   "salud": ("Salud_ajustada.zip", 23480)}),
    2024: ("861", {
        "vivienda": ("DBF-ENCV-Datos_vivienda-2024.zip", 23948),
        "servicios": ("DBF-ENCV-Servicios_hogar-2024.zip", 23957),
        "tenencia": ("DBF-ENCV-Tenencia_financiacion_vivienda_ocupa_hogar-2024.zip", 23952),
        "condiciones": ("DBF-ENCV-Condiciones_vida_hogar_tenencia_bienes-2024.zip", 24059),
        "caracteristicas": ("DBF-ENCV-Caracteristicas_composicion_hogar-2024.zip", 23942),
        "salud": ("DBF-ENCV-Salud2024.zip", 24536),
        "primera_infancia": ("DBF-ENCV-Atencion_integral_ninos_ninas_menores_5_anos-2024.zip", 23954),
        "educacion": ("DBF-ENCV-Educacion-2024.zip", 23949),
        "fuerza_trabajo": ("DBF-ENCV-Fuerza_trabajo-2024.zip", 23950),
        "tic": ("DBF-ENCV-Tecnologias_informacion_comunicacion-2024.zip", 23956),
        "trabajo_infantil": ("DBF-ENCV-Trabajo_infantil-2024.zip", 23953),
    }),
    2025: ("905", {
        "vivienda": ("DBF-ECV-Datos_vivienda-2025.zip", 24628),
        "servicios": ("DBF-ECV-Servicios_hogar-2025.zip", 24625),
        "tenencia": ("DBF-ECV-Tenencia_financiacion_vivienda_ocupa_hogar-2025.zip", 24621),
        "condiciones": ("DBF-ECV-Condiciones_vida_hogar_tenencia_bienes-2025.zip", 24681),
        "caracteristicas": ("DBF-ECV-Caracteristicas_composicion_hogar-2025.zip", 24631),
        "salud": ("DBF-ECV-Salud-2025.zip", 24626),
        "primera_infancia": ("DBF-ECV-Atencion_integral_ninos_ninas_menores_5_anos-2025.zip", 24635),
        "educacion": ("DBF-ECV-Educacion-2025.zip", 24629),
        "fuerza_trabajo": ("DBF-ECV-Fuerza_trabajo2025.zip", 24627),
        "tic": ("DBF-ECV-Tecnologias_informacion_comunicacion-2025.zip", 24623),
        "trabajo_infantil": ("DBF-ECV-Trabajo infantil-2025.zip", 24622),
    }),
}

_URL = "https://microdatos.dane.gov.co/index.php/catalog/{c}/download/{d}"
# {(año, módulo): (catálogo, nombre del ZIP, url)}
ECV_KNOWN_FILES = {(anio, modulo): (catalogo, nombre, _URL.format(c=catalogo, d=descarga))
                   for anio, (catalogo, archivos) in _CATALOGOS.items()
                   for modulo, (nombre, descarga) in archivos.items()}
# Del catálogo del IPM 2020 (679), no del de la ECV
ECV_KNOWN_FILES[2020, _COMPLEMENTARIA] = ("679", "Base_complementaria.zip", _URL.format(c="679", d=20574))


class ECVDownloader(DescargadorANDA):
    log = log
    pausa = 1  # segundos entre descargas

    def __init__(self, base_dir="data", keep_zips=True, progress=None, should_stop=None, forzar=False):
        self.progress = progress
        self.should_stop = should_stop
        self.forzar = forzar
        self.base_dir = Path(base_dir)
        self.raw_dir = self.base_dir / "raw_zips"
        self.data_dir = self.base_dir / "datos"
        self.keep_zips = keep_zips
        self._abrir_sesion()
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _extraer(self, zip_path: Path, carpeta: Path) -> bool:
        """
        Saca los CSV del ZIP (o los Stata, si no hay CSV), estén o no en una subcarpeta. Extrae primero aparte: si falla,
        queda lo de antes.
        """
        def extraer(nueva: Path) -> list[Path]:
            with zipfile.ZipFile(zip_path) as z:
                miembros = [m for m in z.infolist() if not m.is_dir()]
                for extension in EXTENSIONES:
                    elegidos = [m for m in miembros if m.filename.lower().endswith(extension)]
                    if elegidos:
                        nombres = [sanitize_member_name(m.filename) for m in elegidos]
                        if len(set(nombres)) < len(nombres):  # al aplanar las subcarpetas uno pisaría al otro
                            raise ValueError(f"dos archivos de {zip_path.name} quedan con el mismo nombre: "
                                             f"{sorted({n for n in nombres if nombres.count(n) > 1})}")
                        extraidos = []
                        for m in elegidos:
                            extraer_miembro(z, m, destino := nueva / sanitize_member_name(m.filename))
                            extraidos.append(destino)
                        return extraidos
            return []

        try:
            return extraer_aparte(extraer, carpeta, self.raw_dir, EXTENSIONES)
        except (zipfile.BadZipFile, OSError, ValueError) as e:
            log.error(f"Error extrayendo {zip_path.name}: {e}")
            return False

    def run_pipeline(self, target_years=None, modulos=MODULOS) -> list[str]:
        """Descarga los años y capítulos pedidos. Devuelve lo que no se pudo bajar o extraer."""
        # Los factores del CNPV 2018 y la base complementaria de 2020 van con cualquier capítulo: sin ellos 2018 no se expande
        # como el DANE hoy y el IPM de 2020 no es el publicado
        modulos = {*modulos, *_INTERNOS} if modulos else set()
        pedidos = sorted(k for k in ECV_KNOWN_FILES if k[1] in modulos)
        self.fallidos = []
        if target_years is not None:  # [] es "ningún año", no "todos"
            anios = {int(a) for a in target_years}
            # Un fallo y no solo un aviso: si no, pedir un año que no está devolvía "éxito" sin bajar nada
            if desconocidos := sorted(anios - set(_CATALOGOS)):
                self._fallo(f"Años sin la ECV en el ANDA: {', '.join(map(str, desconocidos))} "
                            f"(hay {min(_CATALOGOS)}–{max(_CATALOGOS)}).")
            pedidos = [k for k in pedidos if k[0] in anios]

        faltantes = [k for k in pedidos if self.forzar or not archivos_datos(self._carpeta(*k), EXTENSIONES)]
        for anio, modulo in pedidos:
            if (anio, modulo) not in faltantes:
                log.info(f"{modulo} {anio} ya está extraído. Se salta.")
        log.info(f"ECV: {len(faltantes)} archivo(s) por descargar de {len(pedidos)} pedido(s).")

        for i, (anio, modulo) in enumerate(faltantes):
            self._check_stop()
            self._emit(i / max(len(faltantes), 1), f"ECV {anio}: {modulo}")
            catalogo, nombre, url = ECV_KNOWN_FILES[anio, modulo]
            carpeta_zip = self.raw_dir / catalogo
            carpeta_zip.mkdir(parents=True, exist_ok=True)
            destino = carpeta_zip / nombre
            bajado = self.download_file(url, destino)
            time.sleep(self.pausa)
            carpeta = self._carpeta(anio, modulo)
            if not bajado:
                self._fallo(f"{modulo} {anio}: no se pudo descargar {nombre}.")
            elif not self._extraer(destino, carpeta):
                conserva = " Se conserva lo extraído antes." if archivos_datos(carpeta, EXTENSIONES) else ""
                self._fallo(f"{modulo} {anio}: no se encontró un archivo CSV o Stata en {nombre}.{conserva}")
            if not self.keep_zips:
                destino.unlink(missing_ok=True)
        return self._terminar("la ECV", self.data_dir)

    def _carpeta(self, anio: int, modulo: str) -> Path:
        return self.data_dir / str(anio) / modulo
