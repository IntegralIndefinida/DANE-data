"""
Descarga de la Medición de Pobreza Monetaria y Desigualdad del ANDA del DANE.

Cada año, 2012–2025, trae dos archivos: ``hogares`` (ingreso per cápita de la unidad de gasto,
líneas de pobreza, pobre e indigente, factor de expansión) y ``personas`` (los componentes del
ingreso). Quedan en ``<raíz>/datos/<año>/hogares.<ext>`` y ``personas.<ext>``, con nombre fijo:
hasta 2022 vienen en un ZIP cada uno y desde 2023 en uno solo. El nombre original, el catálogo y la
URL quedan en ``<raíz>/datos/<año>/origen.json``.

Con ``empalme=True`` se bajan además, a ``<raíz>/datos/empalme/``, los archivos para comparar
2012–2021 con el marco 2018: el factor de empalme 2012–2020 (``FEX_G``), los hogares empalmados de
2021 (nacional y departamental) y las líneas de pobreza actualizadas de 2012–2018.

Se prefiere CSV, luego TXT y luego Stata; SPSS no se usa. El archivo de víctimas de cada catálogo
no se baja. Un año nuevo se agrega a ``_CATALOGOS``.
"""

from __future__ import annotations

import json
import logging
import re
import time
import zipfile
from pathlib import Path

from .._hooks import DescargadorANDA, _temporal, extraer_miembro

log = logging.getLogger("dane_data.pobreza")

ARCHIVOS = ("hogares", "personas")
EXTENSIONES = (".csv", ".txt", ".dta")  # en orden de preferencia
_URL = "https://microdatos.dane.gov.co/index.php/catalog/{c}/download/{d}"

# Año -> (catálogo, {archivo: (nombre del ZIP, número de descarga)})
_CATALOGOS = {
    2012: ("40", {"hogares": ("HOGARES.zip", 378), "personas": ("PERSONAS.zip", 379)}),
    2013: ("211", {"hogares": ("Hogares.zip", 3370), "personas": ("Personas.zip", 3371)}),
    2014: ("334", {"hogares": ("Hogares.zip", 4905), "personas": ("Personas.zip", 4906)}),
    2015: ("410", {"hogares": ("Hogares.zip", 6673), "personas": ("Personas_2015.zip", 7227)}),
    2016: ("454", {"hogares": ("Hogares.zip", 8443), "personas": ("Personas.zip", 8444)}),
    2017: ("545", {"hogares": ("HOGARES.zip", 9665), "personas": ("PERSONAS.zip", 9666)}),
    2018: (
        "608",
        {"hogares": ("Hogares 2018.zip", 11190), "personas": ("Personas 2018.zip", 11191)},
    ),
    2019: ("684", {"hogares": ("Hogaresd.zip", 14160), "personas": ("Personasd.zip", 14161)}),
    2020: ("708", {"hogares": ("Hogares.zip", 20329), "personas": ("Personas.zip", 20330)}),
    2021: ("733", {"hogares": ("Hogares.zip", 21110), "personas": ("Personas.zip", 21111)}),
    2022: ("804", {"hogares": ("HOGARES.zip", 23079), "personas": ("PERSONAS.zip", 23080)}),
    **{
        a: (c, dict.fromkeys(ARCHIVOS, (f"BDatos-Pobreza_Monetaria_Desigualdad-{a}.zip", d)))
        for a, c, d in ((2023, "835", 24209), (2024, "874", 24210), (2025, "908", 24758))
    },
}
# Archivos del empalme al marco 2018 -> (catálogo, nombre del ZIP, número de descarga)
_EMPALME = {
    "empalme_2012_2020": ("842", "Empalme 2012-2020.zip", 23713),
    "hogares_empalmado_2021": ("733", "Hogares Empalmado.zip", 22955),
    "hogares_empalmado_dpto_2021": ("733", "hogares_empalmado_dpto.zip", 23062),
    "lineas_2012_2018": ("689", "lineas_20122018.zip", 13968),
}
ARCHIVOS_EMPALME = tuple(_EMPALME)

# Nombre del archivo dentro del ZIP (sin carpeta ni extensión, en minúscula). Tiene que haber
# exactamente uno: si el DANE cambia el empaque, la descarga falla con la lista de lo que trae el
# ZIP en vez de tomar otro archivo.
_MIEMBROS = {
    "hogares": re.compile(r"hogares(?!.*(empalm|victim))[\w ]*"),
    "personas": re.compile(r"personas(?!.*victim)[\w ]*"),
    "empalme_2012_2020": re.compile(r"empalme[\w -]*"),
    "hogares_empalmado_2021": re.compile(r"hogares[ _]?empalmado(?!.*dpto)[\w ]*"),
    "hogares_empalmado_dpto_2021": re.compile(
        r"[\w ]*empalmado[\w ]*dpto[\w ]*|[\w ]*dpto[\w ]*empalmado[\w ]*"
    ),
    "lineas_2012_2018": re.compile(r"l[ií]neas[\w -]*"),
}


def _armar_tabla() -> dict[tuple[int | str, str], tuple[str, str, str]]:
    """``{(año, archivo): (catálogo, nombre del ZIP, url)}``; el empalme con ``"empalme"`` como
    año.
    """
    tabla = {
        (a, archivo): (c, nombre, _URL.format(c=c, d=d))
        for a, (c, archivos) in _CATALOGOS.items()
        for archivo, (nombre, d) in archivos.items()
    }
    tabla.update(
        {
            ("empalme", archivo): (c, nombre, _URL.format(c=c, d=d))
            for archivo, (c, nombre, d) in _EMPALME.items()
        }
    )
    return tabla


POBREZA_KNOWN_FILES = _armar_tabla()


def _elegir(miembros: list[zipfile.ZipInfo], archivo: str) -> zipfile.ZipInfo | str:
    """El miembro de ``archivo`` en el formato preferido, o el motivo por el que no se puede elegir
    uno.
    """
    patron = _MIEMBROS[archivo]
    for extension in EXTENSIONES:
        hallados = [
            m
            for m in miembros
            if m.filename.lower().endswith(extension)
            and patron.fullmatch(Path(m.filename).stem.lower().strip())
        ]
        if len(hallados) == 1:
            return hallados[0]
        if len(hallados) > 1:
            return f"hay {len(hallados)} candidatos ({', '.join(m.filename for m in hallados)})"
    return (
        f"no hay un archivo CSV, TXT o Stata de {archivo} (el ZIP trae: "
        f"{', '.join(m.filename for m in miembros)})"
    )


class PobrezaDownloader(DescargadorANDA):
    log = log
    pausa = 1  # segundos entre descargas

    def __init__(
        self, base_dir="data", keep_zips=True, progress=None, should_stop=None, forzar=False
    ):
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

    def _ya_esta(self, carpeta: Path, archivo: str) -> bool:
        return any((carpeta / f"{archivo}{e}").is_file() for e in EXTENSIONES)

    def _extraer(self, zip_path: Path, archivo: str, carpeta: Path, origen: dict) -> str | None:
        """
        Saca ``archivo`` del ZIP a ``carpeta/<archivo>.<ext>``. Primero a un temporal: si falla,
        queda lo de antes, y lo de antes en otro formato se borra solo después. Devuelve el motivo
        si no se pudo.
        """
        try:
            with zipfile.ZipFile(zip_path) as z:
                elegido = _elegir([m for m in z.infolist() if not m.is_dir()], archivo)
                if isinstance(elegido, str):
                    return elegido
                extension = Path(elegido.filename).suffix.lower()
                carpeta.mkdir(parents=True, exist_ok=True)
                destino = carpeta / f"{archivo}{extension}"
                tmp = _temporal(destino)
                try:
                    extraer_miembro(z, elegido, tmp)
                    tmp.replace(destino)
                finally:
                    tmp.unlink(missing_ok=True)
        except (zipfile.BadZipFile, OSError) as e:
            return f"error al extraer {zip_path.name}: {e}"
        for otra in EXTENSIONES:
            if otra != extension:
                (carpeta / f"{archivo}{otra}").unlink(missing_ok=True)
        _anotar_origen(carpeta, archivo, {**origen, "miembro": elegido.filename})
        return None

    def run_pipeline(self, target_years=None, archivos=ARCHIVOS, empalme=False) -> list[str]:
        """Descarga los años y archivos pedidos, y el empalme si se pide. Devuelve lo que no se
        pudo bajar o extraer.
        """
        self.fallidos = []
        pedidos = sorted(k for k in POBREZA_KNOWN_FILES if k[0] != "empalme" and k[1] in archivos)
        if target_years is not None:  # [] es "ningún año", no "todos"
            anios = {int(a) for a in target_years}
            if desconocidos := sorted(anios - set(_CATALOGOS)):
                self._fallo(
                    "Años sin microdatos de pobreza en el ANDA: "
                    f"{', '.join(map(str, desconocidos))} (hay "
                    f"{min(_CATALOGOS)}–{max(_CATALOGOS)})."
                )
            pedidos = [k for k in pedidos if k[0] in anios]
        if empalme:
            pedidos += [("empalme", a) for a in ARCHIVOS_EMPALME]

        faltantes = [
            k for k in pedidos if self.forzar or not self._ya_esta(self.data_dir / str(k[0]), k[1])
        ]
        log.info(
            f"Pobreza monetaria: {len(faltantes)} archivo(s) por descargar de {len(pedidos)} "
            "pedido(s)."
        )

        # Desde 2023 hogares y personas vienen en el mismo ZIP: se baja una vez y se borra (si se
        # pidió) al terminar
        pendientes: dict[str, int] = {}
        for k in faltantes:
            pendientes[POBREZA_KNOWN_FILES[k][2]] = (
                pendientes.get(POBREZA_KNOWN_FILES[k][2], 0) + 1
            )
        bajados: dict[str, bool] = {}
        fallo_zip: set[str] = set()  # ZIP con algo que no se pudo bajar o extraer: se conservan
        for i, (anio, archivo) in enumerate(faltantes):
            self._check_stop()
            self._emit(i / max(len(faltantes), 1), f"Pobreza {anio}: {archivo}")
            catalogo, nombre, url = POBREZA_KNOWN_FILES[anio, archivo]
            carpeta_zip = self.raw_dir / catalogo
            carpeta_zip.mkdir(parents=True, exist_ok=True)
            destino = carpeta_zip / " ".join(nombre.split())
            if url not in bajados:
                bajados[url] = self.download_file(url, destino)
                time.sleep(self.pausa)
            pendientes[url] -= 1
            if not bajados[url]:
                self._fallo(f"{archivo} {anio}: no se pudo descargar {nombre}.")
                fallo_zip.add(url)
            elif motivo := self._extraer(
                destino,
                archivo,
                self.data_dir / str(anio),
                {"catalogo": catalogo, "zip": nombre, "url": url},
            ):
                self._fallo(f"{archivo} {anio}: {motivo}.")
                fallo_zip.add(url)
            # Solo cuando todo lo de ese ZIP se extrajo: si falló, el ZIP de antes (con forzar)
            # sirve para reintentar
            if not self.keep_zips and pendientes[url] == 0 and url not in fallo_zip:
                destino.unlink(missing_ok=True)
        return self._terminar("la pobreza monetaria", self.data_dir)


def _anotar_origen(carpeta: Path, archivo: str, datos: dict) -> None:
    """Guarda en ``carpeta/origen.json`` de dónde salió cada archivo: el nombre en el ZIP, el
    catálogo y la URL.
    """
    ruta = carpeta / "origen.json"
    try:
        actual = json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        actual = {}
    actual[archivo] = datos
    ruta.write_text(json.dumps(actual, indent=2, ensure_ascii=False), encoding="utf-8")
