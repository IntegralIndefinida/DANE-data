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


def test_extraccion_interrumpida_no_deja_archivos_a_medias(tmp_path, monkeypatch):
    """Si la copia se corta, no queda el archivo con su nombre final (ni el .part) ni el marcador."""
    import dane_data._hooks as hooks

    original = hooks.shutil.copyfileobj

    def cortar(src, dst, *a):
        if "Ocupados" in getattr(dst, "name", "") and "No ocupados" not in dst.name:
            dst.write(src.read(5))
            raise OSError("disco lleno")
        return original(src, dst, *a)

    monkeypatch.setattr(hooks.shutil, "copyfileobj", cortar)
    dl = FakeDownloader({"Marzo 2024.zip": _mes_2024()}, base_dir=tmp_path)
    dl.process_year("2024", "819")
    mes = tmp_path / "datos_csv" / "2024" / "Marzo 2024"
    assert not (mes / "Ocupados.CSV").exists()
    assert not list(mes.glob("*.part"))
    assert not (mes / MARCADOR).exists()

    monkeypatch.setattr(hooks.shutil, "copyfileobj", original)
    dl.process_year("2024", "819")
    assert (mes / "Ocupados.CSV").read_text() == MOD
    assert mes_completo(mes, TODOS)


def test_archivo_truncado_se_vuelve_a_extraer(tmp_path):
    """Un CSV de distinto tamaño que en el ZIP no se da por extraído."""
    mes = tmp_path / "datos_csv" / "2024" / "Marzo 2024"
    mes.mkdir(parents=True)
    (mes / "Ocupados.CSV").write_text(MOD[:10])
    FakeDownloader({"Marzo 2024.zip": _mes_2024()}, base_dir=tmp_path).process_year("2024", "819")
    assert (mes / "Ocupados.CSV").read_text() == MOD


def test_empalme_con_un_mes_ilegible_no_escribe_marcador(tmp_path):
    """Un ZIP mensual dañado dentro del paquete anual: el año no queda como completo."""
    mes = _zip({"Características generales (personas).CSV": CAR, "Ocupados.CSV": MOD,
                "Fuerza de trabajo.CSV": MOD, "Desocupados.CSV": MOD})
    nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
               "Octubre", "Noviembre", "Diciembre"]
    danado = _zip({f"{i}. {m}.zip": (b"no es un zip" if m == "Marzo" else mes)
                   for i, m in enumerate(nombres, start=1)})
    modulos = ("caracteristicas", "ocupados", "fuerza_trabajo", "desocupados")
    dl = FakeDownloader({"GEIH_Empalme_2016.zip": danado}, base_dir=tmp_path, is_empalme=True, modules=modulos)
    dl.process_year("2016", "757")
    anio = tmp_path / "datos_csv" / "2016"
    assert (anio / "1. Enero" / "Ocupados.CSV").exists()
    assert not (anio / MARCADOR).exists()

    # El ZIP con el mes dañado se borró (keep_zips=True por defecto): si no, se reutilizaría para siempre
    assert not (tmp_path / "raw_zips" / "2016" / "GEIH_Empalme_2016.zip").exists()
    dl.paquetes["GEIH_Empalme_2016.zip"] = _zip({f"{i}. {m}.zip": mes for i, m in enumerate(nombres, start=1)})
    dl.process_year("2016", "757")                      # se vuelve a intentar
    assert len(dl.descargas) == 2
    assert (anio / "3. Marzo" / "Ocupados.CSV").exists() and (anio / MARCADOR).exists()


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


class _CatalogosFijos:
    """Sin red: catálogos fijos y process_year solo anota el año."""

    def discover_catalogs(self):
        return {"2023": "1", "2024": "2"}

    def process_year(self, year, *a, **k):
        self.procesados.append(year)


class _GEIHCatalogos(_CatalogosFijos, GEIHDownloader):
    procesados: list


class _EAMCatalogos(_CatalogosFijos, EAMDownloader):
    def discover_catalogs(self):
        return {"2023": ("1", "EAM_2023.zip", "u"), "2024": ("2", "EAM_2024.zip", "u")}


@pytest.mark.parametrize("clase", [_GEIHCatalogos, _EAMCatalogos])
def test_anios_vacios_o_desconocidos(tmp_path, caplog, clase):
    dl = clase(base_dir=tmp_path)
    dl.procesados = []
    dl.run_pipeline(target_years=[])
    assert dl.procesados == []                          # lista vacía: ningún año, no todos
    with caplog.at_level("WARNING"):
        dl.run_pipeline(target_years=[2024, 2030])
    assert dl.procesados == ["2024"]
    assert "2030" in caplog.text
    dl.run_pipeline(target_years=None)
    assert dl.procesados == ["2024", "2023", "2024"]


def test_modulos_vacios_texto_o_desconocidos(tmp_path):
    with pytest.raises(ValueError, match="vacío"):
        GEIHDownloader(base_dir=tmp_path, modules=[])
    with pytest.raises(ValueError, match="desconocidos"):
        GEIHDownloader(base_dir=tmp_path, modules=["ocupado"])
    assert GEIHDownloader(base_dir=tmp_path, modules="ocupados").modules == ("ocupados",)


class _Respuesta:
    def __init__(self, cuerpo: bytes, con_tamano: bool = False):
        self.cuerpo = cuerpo
        self.headers = {"content-length": str(len(cuerpo))} if con_tamano else {}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.cuerpo


class _Sesion:
    """``requests.Session`` falsa: devuelve las respuestas en orden y anota cada pedido."""

    def __init__(self, *respuestas):
        self.respuestas = list(respuestas)
        self.pedidos = 0

    def get(self, url, **kw):
        self.pedidos += 1
        return self.respuestas.pop(0)


@pytest.fixture
def sin_pausas_eam(monkeypatch):
    monkeypatch.setattr("dane_data.eam.downloader.time.sleep", lambda s: None)


@pytest.mark.parametrize("clase", [GEIHDownloader, EAMDownloader])
def test_zip_danado_en_disco_se_vuelve_a_descargar(tmp_path, sin_pausas_eam, clase):
    dl = clase(base_dir=tmp_path)
    destino = tmp_path / "Enero.zip"
    destino.write_bytes(b"cortado")
    dl.session = _Sesion(_Respuesta(_zip({"a.csv": "x"})))
    assert dl.download_file("u", destino)
    assert dl.session.pedidos == 1 and zipfile.is_zipfile(destino)

    dl.session = _Sesion()
    assert dl.download_file("u", destino)              # ahora sí está bien: no se pide de nuevo
    assert dl.session.pedidos == 0


@pytest.mark.parametrize("clase", [GEIHDownloader, EAMDownloader])
def test_respuesta_que_no_es_zip_se_reintenta(tmp_path, sin_pausas_eam, clase):
    """Sin content-length, una página de error o un corte no se notan por el tamaño."""
    dl = clase(base_dir=tmp_path)
    destino = tmp_path / "Enero.zip"
    dl.session = _Sesion(_Respuesta(b"<html>error</html>"), _Respuesta(_zip({"a.csv": "x"}), con_tamano=True))
    assert dl.download_file("u", destino)
    assert dl.session.pedidos == 2 and zipfile.is_zipfile(destino)
    assert not list(tmp_path.glob("*.part"))

    otro = tmp_path / "Febrero.zip"
    dl.session = _Sesion(*[_Respuesta(b"<html>error</html>") for _ in range(3)])
    assert not dl.download_file("u", otro)
    assert not otro.exists()


def _zip_crc_malo() -> bytes:
    """Un ZIP con su índice bien (``is_zipfile`` lo acepta) pero un archivo dañado adentro."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_STORED) as z:
        z.writestr("Ocupados.CSV", MOD)
        z.writestr("EAM_2015.csv", MOD)
    return buf.getvalue().replace(MOD.encode(), MOD.replace("1", "2").encode())


def test_zip_que_falla_al_extraer_se_borra(tmp_path, sin_pausas_eam):
    zip_path = tmp_path / "Marzo 2024.zip"
    zip_path.write_bytes(_zip_crc_malo())
    assert zipfile.is_zipfile(zip_path)
    errores = []
    GEIHDownloader(base_dir=tmp_path).extract_requested_modules(zip_path, tmp_path / "mes", errores=errores)
    assert errores and not zip_path.exists()

    zip_path.write_bytes(_zip_crc_malo())
    EAMDownloader(base_dir=tmp_path).extract_preferred_format(zip_path, tmp_path / "anio")
    assert not zip_path.exists()


# --------------------------------------------------------------------------- #
# Raspado del ANDA (páginas de búsqueda, get-microdata y metadata) sin red
# --------------------------------------------------------------------------- #
class _Pagina:
    def __init__(self, texto="", estado=200, datos=None):
        self.text, self.status_code, self.datos = texto, estado, datos

    def raise_for_status(self):
        if self.status_code >= 400:
            raise OSError(f"HTTP {self.status_code}")

    def json(self):
        return self.datos


class _ANDA:
    """``requests.Session`` falsa que responde según la URL (y la página de la búsqueda)."""

    def __init__(self, rutas: dict, falla: bool = False):
        self.rutas, self.falla, self.pedidos = rutas, falla, []

    def get(self, url, params=None, **kw):
        self.pedidos.append((url, params))
        if self.falla:
            raise OSError("sin conexión")
        clave = url.split("microdatos.dane.gov.co")[-1] + (f"?page={params['page']}" if params else "")
        return self.rutas.get(clave, _Pagina(estado=404))


def _busqueda(*titulos):
    return _Pagina("".join(f'<a href="/index.php/catalog/{cid}">{t}</a>' for cid, t in titulos)
                   + '<a href="/index.php/catalog/search?page=2">siguiente</a>')


def _modal(*archivos):
    return _Pagina("".join(f"<a onclick=\"mostrarModal('{n}', '{u}')\">{n}</a>" for n, u in archivos))


def test_descubrir_catalogos_geih(tmp_path):
    from dane_data.geih.downloader import KNOWN_CATALOGS

    dl = GEIHDownloader(base_dir=tmp_path)
    dl.session = _ANDA({
        "/index.php/catalog/search?page=1": _busqueda(
            ("999", "Gran Encuesta Integrada de Hogares - GEIH - 2027"),
            ("998", "GEIH 2024 - San Andrés"),                   # módulo satélite: no cuenta
            ("997", "GEIH Empalme 2015 Marco 2018"),             # empalme: no es la serie principal
            ("996", "Encuesta de Calidad de Vida 2024")),         # otra encuesta
        "/index.php/catalog/search?page=2": _busqueda(),          # sin más resultados: para
    })
    cat = dl.discover_catalogs()
    assert cat["2027"] == "999"
    assert cat["2024"] == KNOWN_CATALOGS["2024"]
    assert len(dl.session.pedidos) == 2


def test_descubrir_catalogos_empalme_y_sin_conexion(tmp_path):
    from dane_data.geih.downloader import EMPALME_CATALOGS, KNOWN_CATALOGS

    dl = GEIHDownloader(base_dir=tmp_path, is_empalme=True)
    dl.session = _ANDA({"/index.php/catalog/search?page=1": _busqueda(("995", "GEIH Empalme 2019"),
                                                                      ("994", "GEIH 2019"))})
    assert dl.discover_catalogs() == {**EMPALME_CATALOGS, "2019": "995"}

    dl = GEIHDownloader(base_dir=tmp_path)
    dl.session = _ANDA({}, falla=True)                       # sin internet: los catálogos conocidos
    assert dl.discover_catalogs() == KNOWN_CATALOGS


def test_enlaces_de_microdatos_por_epoca(tmp_path):
    dl = GEIHDownloader(base_dir=tmp_path)
    dl.session = _ANDA({
        # 2007–2021: un ZIP por formato; se toman los CSV (y se quitan los repetidos)
        "/index.php/catalog/1/get-microdata": _modal(("Enero.csv.zip", "u/1"), ("Enero.sav.zip", "u/2"),
                                                     ("Enero.csv.zip", "u/1"), ("Febrero.csv.zip", "u/3"),
                                                     ("Marzo.csv.zip", "https://otro.example/m.zip"),
                                                     ("Abril.csv.zip", "http://microdatos.dane.gov.co/a.zip")),
        # 2022+: un ZIP por mes con todos los formatos; fuera los de apoyo
        "/index.php/catalog/2/get-microdata": _modal(("Ene_2024.zip", "u/4"), ("FEX_2024.zip", "u/5"),
                                                     ("Proyecciones.zip", "u/6"), ("Diccionario.pdf", "u/7")),
        "/index.php/catalog/3/get-microdata": _Pagina("<html>sin enlaces</html>"),
    })
    anda = "https://microdatos.dane.gov.co/"
    # Los relativos se completan; los de otro sitio o sin https se ignoran
    assert dl.get_csv_download_links("1") == [{"name": "Enero.csv.zip", "url": anda + "u/1"},
                                              {"name": "Febrero.csv.zip", "url": anda + "u/3"}]
    assert dl.get_csv_download_links("2") == [{"name": "Ene_2024.zip", "url": anda + "u/4"}]
    assert dl.get_csv_download_links("3") == []
    assert dl.get_csv_download_links("4") == []             # HTTP 404


def test_metadata_se_guarda_y_se_reutiliza(tmp_path):
    dl = GEIHDownloader(base_dir=tmp_path)
    dl.session = _ANDA({"/index.php/metadata/export/819/json": _Pagina(datos={"titulo": "GEIH 2024"})})
    assert dl.fetch_metadata("2024", "819") == {"titulo": "GEIH 2024"}
    assert dl.fetch_metadata("2024", "819") == {"titulo": "GEIH 2024"}
    assert len(dl.session.pedidos) == 1                     # la segunda vez, del disco
    assert dl.fetch_metadata("2025", "853") == {}           # HTTP 404: sigue sin metadata

    eam = EAMDownloader(base_dir=tmp_path / "eam")
    eam.session = _ANDA({"/index.php/metadata/export/491/json": _Pagina(datos={"titulo": "EAM"})})
    eam.fetch_metadata("491")
    eam.fetch_metadata("491")
    assert len(eam.session.pedidos) == 1
    assert json.loads((tmp_path / "eam" / "metadata" / "catalogo_491.json").read_text()) == {"titulo": "EAM"}


def test_descubrir_catalogos_eam(tmp_path):
    from dane_data.eam.downloader import EAM_KNOWN_CATALOGS

    dl = EAMDownloader(base_dir=tmp_path)
    dl.session = _ANDA({"/index.php/catalog/888/get-microdata": _modal(
        ("EAM_2025.zip", "https://microdatos.dane.gov.co/x/1"), ("EAM_TIC_2025.zip", "u/2"),
        ("EAM_2026.zip", "https://otro.example/x.zip"))})       # fuera del ANDA: se ignora
    cat = dl.discover_catalogs()                            # los demás catálogos dan 404: se avisa y sigue
    assert cat["2025"] == ("888", "EAM_2025.zip", "https://microdatos.dane.gov.co/x/1")
    assert "2026" not in cat
    assert {k: v for k, v in cat.items() if k != "2025"} == EAM_KNOWN_CATALOGS


@pytest.mark.parametrize("clase", [GEIHDownloader, EAMDownloader])
def test_descarga_cancelada_no_deja_nada(tmp_path, sin_pausas_eam, clase):
    from dane_data import DownloadCancelled

    class Trozos(_Respuesta):
        def iter_content(self, chunk_size):
            yield from (self.cuerpo[:10], self.cuerpo[10:])

    pedidos = iter([False, True])                           # cancelar después del primer trozo
    dl = clase(base_dir=tmp_path, should_stop=lambda: next(pedidos))
    dl.session = _Sesion(Trozos(_zip({"a.csv": "x" * 100})))
    with pytest.raises(DownloadCancelled):
        dl.download_file("u", tmp_path / "Enero.zip")
    assert not list(tmp_path.glob("Enero.zip*"))


@pytest.mark.parametrize("clase", [GEIHDownloader, EAMDownloader])
def test_descarga_mas_corta_que_content_length_se_reintenta(tmp_path, sin_pausas_eam, clase):
    cuerpo = _zip({"a.csv": "x"})
    corta = _Respuesta(cuerpo[:-5])
    corta.headers = {"content-length": str(len(cuerpo))}
    dl = clase(base_dir=tmp_path)
    dl.session = _Sesion(corta, _Respuesta(cuerpo, con_tamano=True))
    assert dl.download_file("u", tmp_path / "Enero.zip")
    assert dl.session.pedidos == 2
    assert (tmp_path / "Enero.zip").read_bytes() == cuerpo


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


def test_eam_stata_se_usa_tal_cual_con_sus_codigos(tmp_path):
    """El .dta de 2024 no se convierte: el cargador lo lee con los códigos, no con las etiquetas de valor."""
    dta = io.BytesIO()
    pd.DataFrame({"nordest": [10], "dpto": [5], "ciiu4": [1011], "valagri": [80.0]}).to_stata(
        dta, write_index=False, value_labels={"dpto": {5: "ANTIOQUIA (etiqueta)"}})
    zip_path = tmp_path / "EAM_2024.zip"
    zip_path.write_bytes(_zip({"EAM_2024.dta": dta.getvalue()}))
    destino = tmp_path / "datos" / "2024"
    archivos = EAMDownloader(base_dir=tmp_path).extract_preferred_format(zip_path, destino)
    assert [f.name for f in archivos] == ["EAM_2024.dta"]
    assert sorted(f.name for f in destino.iterdir()) == ["EAM_2024.dta"]

    eam = dd.eam.load(2024, root=tmp_path)
    assert eam["departamento"].tolist() == ["Antioquia"]     # del código 5, no de la etiqueta
    assert eam["valagri"].tolist() == [80.0]

    # Un TXT convertido por una versión anterior, junto al .dta, se sigue usando
    (destino / "EAM_2024.txt").write_text("nordest\tdpto\tciiu4\tvalagri\n10\t11\t1011\t80\n", encoding="utf-8")
    assert dd.eam.find_files(2024, root=tmp_path)[2024].suffix == ".txt"


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
