"""
Descarga de la Encuesta de Micronegocios (EMICRON) del ANDA del DANE.

Un catálogo por año (2019–2025) y en cada uno un ZIP por módulo, con el mismo módulo en CSV, Stata y SPSS. Se
extrae solo el CSV, con el nombre del módulo: ``<raíz>/datos/<año>/<módulo>.csv``. Los factores de expansión
que no vienen en los módulos van en ZIP aparte:

* ``fex_ajustado`` (2019–2021): el factor de la serie vigente, ajustado en 2023 a las proyecciones de población
  del CNPV 2018. El ``F_EXP`` que traen los módulos de esos años es el de la serie anterior.
* ``fex_dpto`` (2019–2024): el factor para las cifras por departamento.

El ZIP del factor «proyecciones CNPV» de 2019–2020 no se baja: es de la serie anterior y lo reemplaza el ajustado.
Un año nuevo se agrega a ``_CATALOGOS``.
"""

from __future__ import annotations

import logging
import time
import zipfile
from pathlib import Path

from .._hooks import DescargadorANDA, extraer_miembro
from .loader import FACTORES, MODULOS

log = logging.getLogger("dane_data.emicron")

# Año -> (catálogo del ANDA, {módulo: (nombre del ZIP, número de descarga)}), tal como aparecen en el ANDA
_CATALOGOS = {
    2019: ("681", {
        "identificacion": ("Modulo de identificacion y clasificacion economica.zip", 20422),
        "emprendimiento": ("Modulo de emprendimiento.zip", 20423),
        "sitio": ("Modulo de sitio o ubicacion.zip", 20424),
        "propietario": ("Informacion del propietario(a).zip", 20425),
        "personal_ocupado": ("Modulo de personal ocupado.zip", 20426),
        "caracteristicas": ("Modulo de caracteristicas del micronegocio.zip", 20427),
        "tic": ("Modulo de TIC.zip", 20428),
        "inclusion_financiera": ("Modulo de inclusion financiera.zip", 20429),
        "costos": ("Modulo de costos, gastos y activos.zip", 20430),
        "ventas": ("Modulo de ventas o ingresos.zip", 20431),
        "capital_social": ("Modulo de capital social.zip", 20432),
        "fex_ajustado": ("Factor de expansion ajustado 2019.zip", 22745),
        "fex_dpto": ("Factores de expansion departamentales 2019.zip", 23515),
    }),
    2020: ("712", {
        "identificacion": ("Modulo de identificacion.zip", 20404),
        "emprendimiento": ("Modulo de emprendimiento.zip", 20405),
        "sitio": ("Modulo de sitio o ubicacion.zip", 20406),
        "personal_ocupado": ("Modulo de personal ocupado.zip", 20407),
        "propietario": ("Modulo personal ocupado (propietario(a)).zip", 20408),
        "caracteristicas": ("Modulo de caracteristicas del micronegocio.zip", 20409),
        "tic": ("Modulo de TIC.zip", 20410),
        "costos": ("Modulo de costos, gastos y activos.zip", 20411),
        "ventas": ("Modulo de ventas o ingresos.zip", 20412),
        "covid": ("Modulo de expectativas adaptativas (COVID).zip", 20414),
        "fex_ajustado": ("Factor de expansion ajustado 2020.zip", 22748),
        "fex_dpto": ("Factores de expansion departamentales 2020.zip", 23518),
    }),
    2021: ("742", {
        "identificacion": ("Modulo_identificacion.zip", 21247),
        "emprendimiento": ("Modulo_emprendimiento.zip", 21248),
        "sitio": ("Modulo_sitio_ubicacion.zip", 21249),
        "personal_ocupado": ("Modulo_personal_ocupado.zip", 21250),
        "propietario": ("Modulo_personal_ocupado_(propietario).zip", 21251),
        "caracteristicas": ("Modulo_caracteristicas_del_micronegocio.zip", 21252),
        "tic": ("Modulo_TIC.zip", 21253),
        "costos": ("Modulo_costos_gastos_y_activos.zip", 21254),
        "ventas": ("Modulo_ventas_ingresos.zip", 21255),
        "inclusion_financiera": ("Modulo de inclusion financiera.zip", 21405),
        "fex_ajustado": ("Factor de expansion ajustado 2021.zip", 22751),
        "fex_dpto": ("Factores de expansion departamentales 2021.zip", 23519),
    }),
    2022: ("796", {
        "capital_social": ("Modulo de capital social.zip", 22671),
        "caracteristicas": ("Modulo de caracteristicas del micronegocio.zip", 22672),
        "costos": ("Modulo de costos, gastos y activos.zip", 22673),
        "emprendimiento": ("Modulo de emprendimiento.zip", 22674),
        "identificacion": ("Modulo de identificacion.zip", 22675),
        "inclusion_financiera": ("Modulo de inclusion financiera.zip", 22676),
        "personal_ocupado": ("Modulo de personal ocupado.zip", 22677),
        "sitio": ("Modulo de sitio o ubicacion.zip", 22678),
        "tic": ("Modulo de TIC.zip", 22679),
        "ventas": ("Modulo de ventas o ingresos.zip", 22680),
        "propietario": ("Modulo personal ocupado (propietario(a)).zip", 22681),
        "fex_dpto": ("Factores_expansion_departamental.zip", 23114),
    }),
    2023: ("832", {
        "capital_social": ("Modulo de capital social.zip", 23526),
        "caracteristicas": ("Modulo de caracteristicas del micronegocio.zip", 23527),
        "costos": ("Modulo de costos, gastos y activos.zip", 23528),
        "emprendimiento": ("Modulo de emprendimiento.zip", 23529),
        "identificacion": ("Modulo de identificacion.zip", 23530),
        "inclusion_financiera": ("Modulo de inclusion financiera.zip", 23531),
        "personal_ocupado": ("Modulo de personal ocupado.zip", 23532),
        "sitio": ("Modulo de sitio o ubicacion.zip", 23533),
        "tic": ("Modulo de TIC.zip", 23534),
        "ventas": ("Modulo de ventas o ingresos.zip", 23535),
        "propietario": ("Modulo personal ocupado (propietario(a)).zip", 23536),
        "fex_dpto": ("Factores de expansion departamentales 2023.zip", 24179),
    }),
    2024: ("875", {
        "capital_social": ("BDATOS-EMICRON-Modulo_Capital_Social-2024.zip", 24185),
        "caracteristicas": ("BDATOS-EMICRON-Modulo_Caracteristicas_Micronegocios-2024.zip", 24186),
        "costos": ("BDATOS-EMICRON-Modulo_Costos_Gastos_Activos-2024.zip", 24187),
        "emprendimiento": ("BDATOS-EMICRON-Modulo_Emprendimiento-2024.zip", 24188),
        "identificacion": ("BDATOS-EMICRON-Modulo_Identificacion-2024.zip", 24189),
        "inclusion_financiera": ("BDATOS-EMICRON-Modulo_Inclusion_Financiera-2024.zip", 24190),
        "propietario": ("BDATOS-EMICRON-Modulo_Personal_Ocupado_(propietario(a))-2024.zip", 24191),
        "personal_ocupado": ("BDATOS-EMICRON-Modulo_Personal_Ocupado-2024.zip", 24192),
        "sitio": ("BDATOS-EMICRON-Modulo_Sitio_Ubicacion-2024.zip", 24193),
        "tic": ("BDATOS-EMICRON-Modulo_TIC-2024.zip", 24194),
        "ventas": ("BDATOS-EMICRON-Modulo_Ventas_Ingresos-2024.zip", 24195),
        "fex_dpto": ("BDATOS-Factores_Departamental-EMICRON-2024.zip", 24196),
    }),
    # 2025: solo las 24 ciudades y sin factor departamental
    2025: ("914", {
        "capital_social": ("BDATOS-EMICRON-Modulo_Capital_Social-2025.zip", 24775),
        "caracteristicas": ("BDATOS-EMICRON-Modulo_Caracteristicas_Micronegocios-2025.zip", 24776),
        "costos": ("BDATOS-EMICRON-Modulo_Costos_Gastos_Activos-2025.zip", 24777),
        "emprendimiento": ("BDATOS-EMICRON-Modulo_Emprendimiento-2025.zip", 24778),
        "identificacion": ("BDATOS-EMICRON-Modulo_Identificacion-2025.zip", 24779),
        "inclusion_financiera": ("BDATOS-EMICRON-Modulo_Inclusion_Financiera-2025.zip", 24780),
        "propietario": ("BDATOS-EMICRON-Modulo_Personal_Ocupado_(propietario(a))-2025.zip", 24781),
        "personal_ocupado": ("BDATOS-EMICRON-Modulo_Personal_Ocupado-2025.zip", 24782),
        "sitio": ("BDATOS-EMICRON-Modulo_Sitio_Ubicacion-2025.zip", 24783),
        "tic": ("BDATOS-EMICRON-Modulo_TIC-2025.zip", 24784),
        "ventas": ("BDATOS-EMICRON-Modulo_Ventas_Ingresos-2025.zip", 24785),
    }),
}

_URL = "https://microdatos.dane.gov.co/index.php/catalog/{c}/download/{d}"

# {(año, módulo): (catálogo, nombre del ZIP, url)}
EMICRON_KNOWN_FILES = {(anio, modulo): (catalogo, nombre, _URL.format(c=catalogo, d=descarga))
                       for anio, (catalogo, archivos) in _CATALOGOS.items()
                       for modulo, (nombre, descarga) in archivos.items()}


class EMICRONDownloader(DescargadorANDA):
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

    def _extraer(self, zip_path: Path, destino: Path) -> bool:
        """
        Copia el único CSV de ``zip_path`` a ``destino``. ``extraer_miembro`` escribe primero con otro nombre: si se
        corta, queda lo de antes (con ``forzar``) y no un archivo a medias.
        """
        try:
            with zipfile.ZipFile(zip_path) as z:
                csvs = [m for m in z.infolist() if not m.is_dir() and m.filename.lower().endswith(".csv")]
                if len(csvs) != 1:
                    log.error(f"{zip_path.name}: se esperaba un CSV y hay {len(csvs)}.")
                    return False
                destino.parent.mkdir(parents=True, exist_ok=True)
                extraer_miembro(z, csvs[0], destino)
                return True
        except (zipfile.BadZipFile, OSError) as e:
            log.error(f"Error extrayendo {zip_path.name}: {e}")
            return False

    def run_pipeline(self, target_years=None, modulos=None) -> list[str]:
        """
        Descarga los años y módulos pedidos (``None``: todos), siempre con la identificación y los factores, que
        ``load`` necesita. Devuelve lo que no se pudo bajar o extraer.
        """
        self.fallidos = []
        pedidos_mod = set(MODULOS) if modulos is None else {"identificacion", *FACTORES, *modulos}
        anios = sorted({a for a, _ in EMICRON_KNOWN_FILES})
        if target_years is not None:  # [] es "ningún año", no "todos"
            pedidos_anio = {int(a) for a in target_years}
            # Un fallo y no solo un aviso: si no, pedir un año que no está devolvía "éxito" sin bajar nada
            if desconocidos := sorted(pedidos_anio - set(anios)):
                self._fallo(f"Años sin catálogo de la EMICRON en el ANDA: {', '.join(map(str, desconocidos))}. "
                            f"Disponibles: {anios[0]}–{anios[-1]}.")
            anios = [a for a in anios if a in pedidos_anio]
        if modulos is not None:
            for m in sorted(set(modulos) - set(FACTORES)):
                if sin := [a for a in anios if (a, m) not in EMICRON_KNOWN_FILES]:
                    log.warning(f"El módulo {m} no existe en {', '.join(map(str, sin))}: el DANE no lo aplicó ese año.")

        pedidos = [k for k in sorted(EMICRON_KNOWN_FILES) if k[0] in anios and k[1] in pedidos_mod]
        faltantes = [k for k in pedidos if self.forzar or not (self.data_dir / str(k[0]) / f"{k[1]}.csv").is_file()]
        log.info(f"EMICRON: {len(faltantes)} módulo(s) por descargar de {len(pedidos)} pedido(s).")

        for i, (anio, modulo) in enumerate(faltantes):
            self._check_stop()
            self._emit(i / max(len(faltantes), 1), f"{anio}: {modulo}")
            _, nombre, url = EMICRON_KNOWN_FILES[anio, modulo]
            zip_dest = self.raw_dir / str(anio) / nombre
            zip_dest.parent.mkdir(parents=True, exist_ok=True)
            destino = self.data_dir / str(anio) / f"{modulo}.csv"
            if not self.download_file(url, zip_dest):
                self._fallo(f"{anio} {modulo}: no se pudo descargar {nombre}.")
            elif not self._extraer(zip_dest, destino):
                conserva = " Se conserva lo extraído antes." if destino.is_file() else ""
                self._fallo(f"{anio} {modulo}: no se pudo extraer el CSV de {nombre}.{conserva}")
            if not self.keep_zips:
                zip_dest.unlink(missing_ok=True)
            time.sleep(self.pausa)
        return self._terminar("la EMICRON", self.data_dir)
