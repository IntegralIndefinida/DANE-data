"""Descargadores GEIH y EAM sin red: se simula el ANDA con ZIPs construidos en memoria."""

import io
import json
import zipfile

import pandas as pd
import pytest

import dane_data as dd
from dane_data.eam.downloader import EAM_TIC_CATALOGS, EAMDownloader
from dane_data.geih.downloader import MARCADOR, GEIHDownloader, faltantes_mes, mes_completo

CAR = "DIRECTORIO;SECUENCIA_P;ORDEN;P6040;FEX_C18\n1;1;1;30;10\n"
MOD = "DIRECTORIO;SECUENCIA_P;ORDEN;FEX_C18\n1;1;1;10\n"
TODOS = ("vivienda", "caracteristicas", "fuerza_trabajo", "ocupados", "desocupados", "inactivos",
         "otras_formas_trabajo")


def _zip(files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, content in files.items():
            z.writestr(name, content)
    return buf.getvalue()


def _mes_2024(nested_name="CSV 13.zip"):
    """Paquete mensual 2022+: parte de los CSV viene en un ZIP anidado con nombre raro."""
    nested = _zip({"Fuerza de trabajo.CSV": MOD, "No ocupados.CSV": MOD})
    return _zip({
        "Características generales, seguridad social en salud y educación.CSV": CAR,
        "Ocupados.CSV": MOD, "Datos del hogar y la vivienda.CSV": MOD, "Otras formas de trabajo.CSV": MOD,
        nested_name: nested, "DTA.zip": _zip({"x.dta": "no"}),
    })


class FakeDownloader(GEIHDownloader):
    def __init__(self, paquetes: dict, **kw):
        super().__init__(**kw)
        self.paquetes = paquetes
        self.descargas = []

    def fetch_metadata(self, year, catalog_id):
        return {}

    def get_csv_download_links(self, catalog_id):
        return [{"name": n, "url": n} for n in self.paquetes]

    def download_file(self, url, dest_path, max_retries=3):
        self.descargas.append(url)
        dest_path.write_bytes(self.paquetes[url])
        return True


@pytest.fixture(autouse=True)
def sin_pausas(monkeypatch):
    monkeypatch.setattr("dane_data.geih.downloader.time.sleep", lambda s: None)


@pytest.mark.parametrize("nombre", ["CSV.zip", "CSV 13.zip", "CSV_4.zip", "csv (1).zip"])
def test_nested_zip_is_flattened(tmp_path, nombre):
    dl = FakeDownloader({"Marzo 2024.zip": _mes_2024(nombre)}, base_dir=tmp_path, keep_zips=False)
    dl.process_year("2024", "819")
    mes = tmp_path / "datos_csv" / "2024" / "Marzo 2024"
    assert (mes / "No ocupados.CSV").exists()            # ya no queda en una subcarpeta
    assert not [d for d in mes.iterdir() if d.is_dir()]
    assert (mes / MARCADOR).exists()
    assert not (tmp_path / "raw_zips" / "2024" / "Marzo 2024.zip").exists()  # keep_zips=False


def test_skip_uses_marker_then_reextracts_incomplete_legacy(tmp_path):
    dl = FakeDownloader({"Marzo 2024.zip": _mes_2024()}, base_dir=tmp_path)
    dl.process_year("2024", "819")
    dl.process_year("2024", "819")
    assert dl.descargas == ["Marzo 2024.zip"]           # la segunda vez se salta

    # Carpeta "heredada" (sin marcador) con 5 CSV pero sin No ocupados: el viejo
    # conteo de archivos la daba por buena; ahora se vuelve a extraer.
    mes = tmp_path / "datos_csv" / "2024" / "Marzo 2024"
    (mes / MARCADOR).unlink()
    (mes / "No ocupados.CSV").unlink()
    assert faltantes_mes(mes, TODOS) == ["desocupados"]
    dl.process_year("2024", "819")
    assert len(dl.descargas) == 2
    assert (mes / "No ocupados.CSV").exists() and mes_completo(mes, TODOS)


def test_marcador_registra_modulos(tmp_path):
    """Una descarga previa de solo Características no impide completar el mes después."""
    FakeDownloader({"Marzo 2024.zip": _mes_2024()}, base_dir=tmp_path,
                   modules=("caracteristicas",)).process_year("2024", "819")
    mes = tmp_path / "datos_csv" / "2024" / "Marzo 2024"
    assert "ocupados" in faltantes_mes(mes, TODOS)

    dl = FakeDownloader({"Marzo 2024.zip": _mes_2024()}, base_dir=tmp_path)
    dl.process_year("2024", "819")
    assert dl.descargas == ["Marzo 2024.zip"]
    assert faltantes_mes(mes, TODOS) == []
    dl.process_year("2024", "819")                      # ahora sí se salta
    assert dl.descargas == ["Marzo 2024.zip"]


def test_marcador_antiguo_sin_modulos_no_cuenta(tmp_path):
    """Los marcadores anteriores no dicen qué módulos se extrajeron: se revisan los archivos."""
    mes = tmp_path / "Marzo 2024"
    mes.mkdir()
    (mes / MARCADOR).write_text(json.dumps({"zip": "Marzo 2024.zip", "csv_extraidos": 1}), encoding="utf-8")
    assert not mes_completo(mes, TODOS)


def test_flags_in_caracteristicas_count_as_complete(tmp_path):
    """2020 / empalme: sin archivo de Desocupados pero con DSI en Características."""
    mes = tmp_path / "1.Enero"
    mes.mkdir()
    (mes / "Características generales (personas).CSV").write_text(
        "DIRECTORIO,SECUENCIA_P,ORDEN,OCI,DSI,INI,FEX_C\n1,1,1,1,,,10\n", encoding="utf-8")
    (mes / "Ocupados.CSV").write_text("DIRECTORIO,SECUENCIA_P,ORDEN\n1,1,1\n", encoding="utf-8")
    (mes / "Fuerza de trabajo.CSV").write_text("DIRECTORIO,SECUENCIA_P,ORDEN\n1,1,1\n", encoding="utf-8")
    pedidos = ("caracteristicas", "fuerza_trabajo", "ocupados", "desocupados", "inactivos")
    assert mes_completo(mes, pedidos)
    assert faltantes_mes(mes, TODOS) == ["otras", "vivienda"]  # esos sí se pidieron y no están


def test_empalme_month_zips_keep_their_folder(tmp_path):
    mes = _zip({"Características generales (personas).CSV": CAR, "Ocupados.CSV": MOD,
                "Fuerza de trabajo.CSV": MOD, "Desocupados.CSV": MOD})
    anual = _zip({f"{i}. {m}.zip": mes for i, m in enumerate(
        ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
         "Octubre", "Noviembre", "Diciembre"], start=1)})
    dl = FakeDownloader({"GEIH_Empalme_2016.zip": anual}, base_dir=tmp_path, is_empalme=True,
                        modules=("caracteristicas", "ocupados", "fuerza_trabajo", "desocupados"))
    dl.process_year("2016", "757")
    anio = tmp_path / "datos_csv" / "2016"
    assert (anio / "1. Enero" / "Ocupados.CSV").exists()
    assert (anio / "12. Diciembre" / "Desocupados.CSV").exists()
    dl.process_year("2016", "757")
    assert dl.descargas == ["GEIH_Empalme_2016.zip"]


class FakeANDA(FakeDownloader):
    """Lista todos los formatos del catálogo, como /get-microdata, y filtra los CSV igual que el real."""
    get_csv_download_links = GEIHDownloader.get_csv_download_links

    def _enlaces(self, catalog_id):
        return {n: n for n in self.paquetes}


def _dta(**cols) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(cols).to_stata(buf, write_index=False)
    return buf.getvalue()


def test_csv_danados_se_bajan_en_otro_formato(tmp_path):
    """2011 (factor sin punto decimal) se baja en TXT; septiembre de 2021 (CSV con espacios), en Stata."""
    mes_txt = _zip({"03_txt/Cabecera - Caracteristicas generales (Personas).txt":
                    "DIRECTORIO\tSECUENCIA_P\tORDEN\tOCI\tDSI\tPETI\tfex_c_2011\n1\t1\t1\t1\t\t1\t84.9491032387525\n",
                    "03_txt/Cabecera - Otros ingresos.txt": "x\n"})
    dl = FakeANDA({"Marzo_csv.zip": _zip({"Cabecera - Caracteristicas generales (Personas).csv": "roto"}),
                   "Marzo_txt.zip": mes_txt, "Marzo.zip": b"spss", "total_2011_c_txt.zip": b"anual"},
                  base_dir=tmp_path, modules=("caracteristicas",))
    dl.process_year("2011", "182")
    assert dl.descargas == ["Marzo_txt.zip"]
    assert [f.name for f in (tmp_path / "datos_csv" / "2011" / "Marzo_txt").glob("*.txt")] == [
        "Cabecera - Caracteristicas generales (Personas).txt"]
    assert dd.geih.load(2011, root=tmp_path, cache=False)["fex"].tolist() == [84.9491032387525]

    car = _dta(DIRECTORIO=[1], SECUENCIA_P=[1], ORDEN=[1], OCI=[1], DSI=[0], PETI=[1], fex_c_2011=[250.5])
    dl = FakeANDA({"Agosto.csv.zip": _zip({"Características generales (personas).CSV": CAR}),
                   "Septiembre.csv (2) (1).zip": _zip({"Características generales (personas).csv": "A B\n1 2\n"}),
                   "Septiembre.spss(2).zip": b"spss",
                   "Septiembre.zip": _zip({"Septiembre.dta/╡rea - Características generales (Personas).dta": car})},
                  base_dir=tmp_path, modules=("caracteristicas",))
    dl.process_year("2021", "701")
    assert sorted(dl.descargas) == ["Agosto.csv.zip", "Septiembre.zip"]
    assert (tmp_path / "datos_csv" / "2021" / "Septiembre" / "Area - Características generales (Personas).dta").exists()


class FakeEAMDownloader(EAMDownloader):
    def __init__(self, paquetes: dict, **kw):
        super().__init__(**kw)
        self.paquetes = paquetes
        self.descargas = []

    def fetch_metadata(self, catalog_id):
        pass

    def download_file(self, url, dest_path, max_retries=3):
        self.descargas.append(url)
        dest_path.write_bytes(self.paquetes[url])
        return True


def test_eam_tic_en_anio_ya_descargado(tmp_path):
    """Pedir el módulo TIC de un año que ya tiene los datos principales sí lo descarga."""
    _, _, tic_url = EAM_TIC_CATALOGS["2015"]
    paquetes = {"principal": _zip({"EAM_2015.csv": "nordest;valagri\n1;10\n"}),
                tic_url: _zip({"EAM_TIC_2015.csv": "nordest;usa_internet\n1;1\n"})}
    dl = FakeEAMDownloader(paquetes, base_dir=tmp_path)
    dl.process_year("2015", "491", "EAM_2015.zip", "principal")
    assert dl.descargas == ["principal"]

    dl.include_tic = True
    dl.process_year("2015", "491", "EAM_2015.zip", "principal")
    assert dl.descargas == ["principal", tic_url]
    assert (tmp_path / "datos" / "2015" / "TIC" / "EAM_TIC_2015.csv").exists()
    dl.process_year("2015", "491", "EAM_2015.zip", "principal")   # ya está todo: no descarga
    assert dl.descargas == ["principal", tic_url]
