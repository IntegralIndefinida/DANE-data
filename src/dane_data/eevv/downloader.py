"""
Descarga de las Estadísticas Vitales (EEVV) del ANDA del DANE.

Un archivo por año y tipo de certificado, en ``<raíz>/datos/<tipo>/<año>/``:

* ``defunciones``: defunciones no fetales, 1979–2025.
* ``nacimientos``: nacidos vivos, 1998–2025.
* ``fetales``: defunciones fetales, 1998–2025.

El empaque cambia con los años:

* 1979–2007 y fetales 2012–2013: un ZIP por año y tipo, con TXT y SPSS.
* 2008–2011: un ZIP de los cuatro años con un ZIP por año adentro, con CSV, Stata y SPSS.
* 2012–2013 (defunciones y nacimientos): un ZIP de los dos años por formato. Se usa el de TXT.
* 2014–2019: un ZIP con un ZIP por año adentro (2017 y 2018 van juntos).
* 2020–2025: un ZIP por año y tipo, con CSV, Stata y SPSS.

Se extrae solo el año pedido y se prefiere CSV, luego TXT y luego Stata. SPSS no se usa: leerlo pediría otra
dependencia, y siempre hay otro formato. Un año nuevo se agrega a ``_CATALOGOS``.
"""

from __future__ import annotations

import logging
import re
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

from .._hooks import DescargadorANDA, extraer_miembro, sanitize_member_name
from .loader import EXTENSIONES, TIPOS, _archivos_datos

log = logging.getLogger("dane_data.eevv")

_DEF, _NAC, _FET = TIPOS

# Años de cada catálogo del ANDA -> {tipo: (nombre del ZIP, número de descarga)}. El nombre lleva {a} si cambia con el año.
_CATALOGOS = {
    "375": (range(2008, 2012), {_DEF: ("Defunciones.zip", 21417), _FET: ("Fetales.zip", 21416),
                                _NAC: ("Nacidos.zip", 21415)}),
    # De 2012–2013 se usa el ZIP de TXT: el otro trae solo SPSS
    "377": (range(2012, 2014), {_DEF: ("Defunciones txt.zip", 5822), _NAC: ("Nacidos vivos txt.zip", 5824)}),
    "420": (range(2014, 2015), {_DEF: ("Defunciones.zip", 21433), _FET: ("Fetales.zip", 21434),
                                _NAC: ("Nacimientos.zip", 21435)}),
    "475": (range(2015, 2016), {_DEF: ("Defunciones.zip", 21430), _FET: ("Fetales.zip", 21431),
                                _NAC: ("Nacimientos.zip", 21432)}),
    "519": (range(2016, 2017), {_DEF: ("Defunciones.zip", 21427), _FET: ("Fetales.zip", 21428),
                                _NAC: ("Nacimientos.zip", 21429)}),
    "652": (range(2017, 2019), {_DEF: ("Defunciones.zip", 21421), _FET: ("Fetales.zip", 21422),
                                _NAC: ("Nacimientos.zip", 21423)}),
    "696": (range(2019, 2020), {_DEF: ("Defunciones.zip", 21424), _FET: ("Fetales.zip", 21425),
                                _NAC: ("Nacimientos.zip", 21426)}),
    "732": (range(2020, 2021), {_DEF: ("nofetal2020.zip", 21082), _FET: ("fetal2020.zip", 21084),
                                _NAC: ("nac2020.zip", 21085)}),
    "775": (range(2021, 2022), {_DEF: ("nofetal2021.zip", 22162), _FET: ("fetal2021.zip", 22305),
                                _NAC: ("nacimientos2021.zip", 22160)}),
    "807": (range(2022, 2023), {_DEF: ("nofetal2022.zip", 23132), _FET: ("fetal2022.zip", 23131),
                                _NAC: ("nac2022.zip", 23133)}),
}
_BD = {_DEF: "BD-EEVV-Defuncionesnofetales-{a}.zip", _FET: "BD-EEVV-Defuncionesfetales-{a}.zip",
       _NAC: "BD-EEVV-Nacimientos-{a}.zip"}
_RECIENTES = {  # Un catálogo por año, con el mismo nombre de archivo
    2023: ("876", {_DEF: 24249, _FET: 24248, _NAC: 24250}),
    2024: ("878", {_DEF: 24462, _FET: 24460, _NAC: 24461}),
    2025: ("915", {_DEF: 24800, _FET: 24799, _NAC: 24798}),
}


def _armar_tabla() -> dict[tuple[int, str], tuple[str, str, str]]:
    """``{(año, tipo): (catálogo, nombre del ZIP, url)}`` de todos los archivos del ANDA."""
    base = "https://microdatos.dane.gov.co/index.php/catalog/{c}/download/{d}"
    tabla = {}

    def poner(anio, tipo, catalogo, nombre, descarga):
        tabla[anio, tipo] = (catalogo, nombre, base.format(c=catalogo, d=descarga))

    # Defunciones 1979–1997: los únicos certificados de esos años en el ANDA
    for i, anio in enumerate(range(1979, 1992)):
        poner(anio, _DEF, "396", f"Defun{anio}.zip", 6344 + i)
    for i, anio in enumerate(range(1992, 1997)):
        poner(anio, _DEF, "397", f"Defun{anio}.zip", 6360 + i)
    poner(1997, _DEF, "398", "Defun1997.zip", 6367)
    # 1998–2007: el nombre no sigue un patrón (espacios dobles, guiones bajos)
    espacios_dobles = {2000, 2003, 2004, 2006}
    for i, anio in enumerate(range(1998, 2008)):
        nombre_nac = f"Nacimientos_{anio}.zip" if anio >= 2006 else f"Nacimientos {anio}.zip"
        poner(anio, _NAC, "366", nombre_nac, 5599 + 2 * i)
        poner(anio, _DEF, "366", f"Defunciones{'  ' if anio in espacios_dobles else ' '}{anio}.zip", 5600 + 2 * i)
        poner(anio, _FET, "366", f"fetal{anio}.zip", 6677 + i)
    for catalogo, (anios, archivos) in _CATALOGOS.items():
        for anio in anios:
            for tipo, (nombre, descarga) in archivos.items():
                poner(anio, tipo, catalogo, nombre, descarga)
    for anio, descarga in ((2012, 6675), (2013, 6676)):
        poner(anio, _FET, "377", f"fetal{anio}.zip", descarga)
    for anio, (catalogo, descargas) in _RECIENTES.items():
        for tipo, descarga in descargas.items():
            poner(anio, tipo, catalogo, _BD[tipo].format(a=anio), descarga)
    return tabla


EEVV_KNOWN_FILES = _armar_tabla()

_ANIO_EN_NOMBRE = re.compile(r"(?<!\d)((?:19|20)\d\d)(?!\d)")


def _es_del_anio(nombre: str, anio: int) -> bool:
    """El archivo es de ``anio``, o su nombre no dice el año (``Fetales.zip``, ``datos.csv``)."""
    hallados = _ANIO_EN_NOMBRE.findall(Path(nombre).name)
    return not hallados or str(anio) in hallados


class EEVVDownloader(DescargadorANDA):
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

    def _extraer_datos(self, z: zipfile.ZipFile, anio: int, destino: Path) -> list[Path]:
        """Saca de ``z`` los datos de ``anio``, entrando a los ZIP anidados, en el formato preferido."""
        miembros = [m for m in z.infolist() if not m.is_dir() and _es_del_anio(m.filename, anio)]
        extraidos = []
        for m in miembros:
            if m.filename.lower().endswith(".zip"):
                with tempfile.TemporaryFile() as tmp:
                    with z.open(m) as origen:
                        shutil.copyfileobj(origen, tmp, 1 << 20)
                    tmp.seek(0)
                    with zipfile.ZipFile(tmp) as interno:
                        extraidos += self._extraer_datos(interno, anio, destino)
        if extraidos:
            return extraidos
        for extension in EXTENSIONES:
            for m in miembros:
                if m.filename.lower().endswith(extension):
                    archivo = destino / sanitize_member_name(m.filename)
                    extraer_miembro(z, m, archivo)
                    extraidos.append(archivo)
            if extraidos:
                return extraidos
        return []

    def _extraer(self, zip_path: Path, anio: int, carpeta: Path) -> bool:
        """
        Extrae primero aparte y solo si salió bien mueve a ``carpeta`` y borra lo que había (con ``forzar``).
        Si falla, queda lo de antes.
        """
        nueva = Path(tempfile.mkdtemp(prefix="extraccion-", dir=self.raw_dir))
        try:
            with zipfile.ZipFile(zip_path) as z:
                extraidos = self._extraer_datos(z, anio, nueva)
            if not extraidos:
                return False
            carpeta.mkdir(parents=True, exist_ok=True)
            nuevos = set()
            for f in extraidos:
                f.replace(carpeta / f.name)
                nuevos.add(carpeta / f.name)
            for viejo in _archivos_datos(carpeta):
                if viejo not in nuevos:
                    viejo.unlink()
            return True
        except (zipfile.BadZipFile, OSError) as e:
            log.error(f"Error extrayendo {anio} de {zip_path.name}: {e}")
            return False
        finally:
            shutil.rmtree(nueva, ignore_errors=True)

    def run_pipeline(self, target_years=None, tipos=TIPOS) -> list[str]:
        """Descarga los años y tipos pedidos. Devuelve lo que no se pudo bajar o extraer."""
        pedidos = sorted(k for k in EEVV_KNOWN_FILES if k[1] in tipos)
        if target_years is not None:  # [] es "ningún año", no "todos"
            anios = {int(a) for a in target_years}
            if desconocidos := sorted(anios - {a for a, _ in pedidos}):
                log.warning(f"Años sin archivos de {', '.join(tipos)} en el ANDA (se ignoran): "
                            f"{', '.join(map(str, desconocidos))}.")
            pedidos = [k for k in pedidos if k[0] in anios]

        self.fallidos = []
        faltantes = [k for k in pedidos if self.forzar or not _archivos_datos(self.data_dir / k[1] / str(k[0]))]
        for anio, tipo in pedidos:
            if (anio, tipo) not in faltantes:
                log.info(f"{tipo} {anio} ya está extraído. Se salta.")
        log.info(f"Estadísticas Vitales: {len(faltantes)} archivo(s) por descargar de {len(pedidos)} pedido(s).")

        # Un ZIP puede traer varios años: se baja una vez y se borra (si se pidió) al terminar el último
        pendientes: dict[str, int] = {}
        for k in faltantes:
            pendientes[EEVV_KNOWN_FILES[k][2]] = pendientes.get(EEVV_KNOWN_FILES[k][2], 0) + 1
        bajados: dict[str, bool] = {}
        for i, (anio, tipo) in enumerate(faltantes):
            self._check_stop()
            self._emit(i / max(len(faltantes), 1), f"{tipo.capitalize()} {anio}")
            catalogo, nombre, url = EEVV_KNOWN_FILES[anio, tipo]
            carpeta_zip = self.raw_dir / catalogo
            carpeta_zip.mkdir(parents=True, exist_ok=True)
            # Sin espacios dobles: el nombre local no tiene por qué repetir los del ANDA
            destino = carpeta_zip / " ".join(nombre.split())
            if url not in bajados:
                bajados[url] = self.download_file(url, destino)
                time.sleep(self.pausa)
            pendientes[url] -= 1
            carpeta = self.data_dir / tipo / str(anio)
            if not bajados[url]:
                self._fallo(f"{tipo} {anio}: no se pudo descargar {nombre}.")
            elif not self._extraer(destino, anio, carpeta):
                conserva = " Se conserva lo extraído antes." if _archivos_datos(carpeta) else ""
                self._fallo(f"{tipo} {anio}: no se encontró un archivo CSV, TXT o Stata de ese año en {nombre}.{conserva}")
            if not self.keep_zips and pendientes[url] == 0:
                destino.unlink(missing_ok=True)
        return self._terminar("las Estadísticas Vitales", self.data_dir)
