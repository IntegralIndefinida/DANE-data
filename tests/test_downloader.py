"""Descargador GEIH sin red: se simula el ANDA con ZIPs construidos en memoria."""

import io
import json
import zipfile

import pytest

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
