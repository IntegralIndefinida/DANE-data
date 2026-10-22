"""Páginas de la app con el probador de Streamlit (se salta si no está instalado el extra `app`)."""

import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dane_data as dd

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest

PAGINAS = Path(dd.__file__).parent / "app" / "paginas"


def test_descargar_toda_la_serie_eam(tmp_path, monkeypatch):
    for clave in ("geih", "geih_empalme", "eam"):
        monkeypatch.setitem(dd.config._session, clave, tmp_path / clave)
    pedidos = []
    monkeypatch.setattr(dd.eam, "download", lambda anios, **kw: pedidos.append(list(anios)))

    at = AppTest.from_file(str(PAGINAS / "descargar.py")).run()
    at.radio[0].set_value("EAM (industria, anual)").run()
    next(b for b in at.button if b.label.startswith("Seleccionar toda")).click().run()
    assert at.multiselect[0].value == dd.eam.ANIOS_DISPONIBLES
    next(b for b in at.button if b.label.endswith("Descargar")).click().run()
    assert not at.exception
    assert pedidos == [dd.eam.ANIOS_DISPONIBLES]


def test_descarga_con_fallas_lo_dice(tmp_path, monkeypatch):
    for clave in ("geih", "geih_empalme", "eam"):
        monkeypatch.setitem(dd.config._session, clave, tmp_path / clave)
    monkeypatch.setattr(dd.eam, "download", lambda anios, **kw: ["2024: no se pudo descargar EAM_2024.zip."])
    at = AppTest.from_file(str(PAGINAS / "descargar.py")).run()
    at.radio[0].set_value("EAM (industria, anual)").run()
    next(b for b in at.button if b.label.endswith("Descargar")).click().run()
    assert not at.exception
    assert not at.success
    assert any("EAM_2024.zip" in w.value for w in at.warning)


def test_citar_usa_la_version_instalada():
    at = AppTest.from_file(str(PAGINAS / "citar.py")).run()
    assert not at.exception
    apa, bibtex = at.code[0].value, at.code[1].value
    assert f"(versión {dd.__version__})" in apa
    assert f"version = {{{dd.__version__}}}" in bibtex


def test_inicio_guarda_solo_las_carpetas_cambiadas(tmp_path, monkeypatch):
    archivo = tmp_path / "config.json"
    monkeypatch.setattr(dd.config, "CONFIG_FILE", archivo)
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.setenv("DANE_DATA_GEIH", str(tmp_path / "desde_env"))
    monkeypatch.setenv("DANE_DATA_GEIH_EMPALME", str(tmp_path / "emp"))
    monkeypatch.setenv("DANE_DATA_EAM", str(tmp_path / "eam_env"))
    at = AppTest.from_file(str(PAGINAS / "inicio.py"), default_timeout=60).run()
    campo = lambda etiqueta: next(t for t in at.text_input if t.label == etiqueta)  # noqa: E731
    campo("EAM").set_value(str(tmp_path / "eam_nueva"))
    next(b for b in at.button if b.label == "Guardar").click().run()
    assert not at.exception
    assert json.loads(archivo.read_text(encoding="utf-8")) == {"eam": str(tmp_path / "eam_nueva")}

    campo("GEIH serie principal").set_value("")
    next(b for b in at.button if b.label == "Guardar").click().run()
    assert not at.exception
    assert any("vacía" in e.value for e in at.error)


def test_inicio_rechaza_carpetas_relativas(tmp_path, monkeypatch):
    """La app corre dentro del paquete: "datos" quedaría en site-packages."""
    archivo = tmp_path / "config.json"
    monkeypatch.setattr(dd.config, "CONFIG_FILE", archivo)
    monkeypatch.setattr(dd.config, "_session", {"geih": tmp_path / "g", "geih_empalme": tmp_path / "e",
                                                "eam": tmp_path / "eam"})
    at = AppTest.from_file(str(PAGINAS / "inicio.py"), default_timeout=60).run()
    next(t for t in at.text_input if t.label == "EAM").set_value("datos")
    next(b for b in at.button if b.label == "Guardar").click().run()
    assert not at.exception
    assert any("ruta completa" in e.value for e in at.error)
    assert not archivo.exists()


def test_descargar_geih_sin_modulos(tmp_path, monkeypatch):
    """Sin módulos elegidos el botón queda desactivado (antes se bajaban todos)."""
    for clave in ("geih", "geih_empalme", "eam"):
        monkeypatch.setitem(dd.config._session, clave, tmp_path / clave)
    at = AppTest.from_file(str(PAGINAS / "descargar.py")).run()
    boton = lambda: next(b for b in at.button if b.label.endswith("Descargar"))  # noqa: E731
    assert not boton().disabled
    next(m for m in at.multiselect if m.label == "Módulos").set_value([]).run()
    assert not at.exception
    assert boton().disabled
    assert any("al menos un módulo" in w.value for w in at.warning)


@pytest.mark.parametrize("pagina", ["eam_industria.py", "eam_microdatos.py"])
def test_eam_anios_no_consecutivos(eam_root, monkeypatch, pagina):
    """Años descargados 1992, 2016 y 2024: el rango por defecto empieza en 2016, no en 2014."""
    monkeypatch.setitem(dd.config._session, "eam", eam_root)
    at = AppTest.from_file(str(PAGINAS / pagina), default_timeout=60).run()
    assert not at.exception
    assert at.select_slider[0].value == (2016, 2024)


@pytest.mark.parametrize("pagina, clave", [("eam_industria.py", "eam"), ("eam_microdatos.py", "eamm")])
def test_eam_filtros_sin_establecimientos(eam_root, monkeypatch, pagina, clave):
    """Un sector que no está en el departamento elegido: aviso, no un IndexError."""
    monkeypatch.setitem(dd.config._session, "eam", eam_root)
    eam = dd.eam.load(2016, root=eam_root)
    sector = eam.loc[eam["departamento"] == "Antioquia", "sector"].iloc[0]

    at = AppTest.from_file(str(PAGINAS / pagina), default_timeout=60).run()
    assert not at.exception
    at.multiselect(key=f"{clave}_sector").set_value([sector])
    at.multiselect(key=f"{clave}_dpto").set_value(["Valle del Cauca"])
    at.run()
    assert not at.exception
    assert any("Ningún establecimiento" in w.value for w in at.warning)


def test_mercado_laboral_precalculado_y_con_filtros(geih_root, tmp_path, monkeypatch):
    monkeypatch.setitem(dd.config._session, "geih", geih_root)
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")

    at = AppTest.from_file(str(PAGINAS / "geih_mercado.py"), default_timeout=60).run()
    assert not at.exception
    assert list((tmp_path / "cache" / "geih" / "indicadores").glob("*.parquet"))  # tabla precalculada
    assert "serie_indicadores" in at.code[0].value

    at.multiselect(key="geih_sexo").set_value(["Mujer"]).run()  # con filtro: también año por año
    assert not at.exception
    assert "filtros={'sexo': ['Mujer']}" in at.code[0].value


def test_informalidad_vacia_antes_de_2022(geih_root, tmp_path, monkeypatch):
    """2021 no tiene las preguntas de la medición del DANE: la tasa queda vacía y la página lo explica."""
    monkeypatch.setitem(dd.config._session, "geih", geih_root)
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    at = AppTest.from_file(str(PAGINAS / "geih_mercado.py"), default_timeout=60).run()
    assert at.multiselect(key="geih_anios").value == [2021, 2025]
    next(s for s in at.selectbox if s.label == "Indicador").set_value("Tasa de informalidad").run()
    assert not at.exception
    assert any("antes de 2022 queda vacía" in i.value for i in at.info)
    assert at.metric[3].value == "0,0 %"                       # 2025: la asalariada del ejemplo es formal
    next(s for s in at.selectbox if s.label == "Indicador").set_value(
        "Tasa de informalidad (medición anterior, hasta 2021)").run()
    assert not at.exception
    assert any("llega hasta 2021" in i.value for i in at.info)


def test_aviso_cuando_los_anios_mezclan_marcos(geih_root, tmp_path, monkeypatch):
    monkeypatch.setitem(dd.config._session, "geih", geih_root)
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")

    at = AppTest.from_file(str(PAGINAS / "geih_mercado.py"), default_timeout=60).run()
    assert at.multiselect(key="geih_anios").value == [2021, 2025]       # censo 2005 y CNPV 2018
    aviso = [w.value for w in at.warning if "no son comparables" in w.value]
    assert aviso and "2021 usa" in aviso[0] and "2025 usa" in aviso[0]

    at.multiselect(key="geih_anios").set_value([2025]).run()
    assert not [w for w in at.warning if "no son comparables" in w.value]


def test_tablas_y_microdatos_sin_cargar_todos_los_anios(geih_root, tmp_path, monkeypatch):
    monkeypatch.setitem(dd.config._session, "geih", geih_root)
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    monkeypatch.setattr(dd.geih, "load", _solo_un_mes(dd.geih.load))

    at = AppTest.from_file(str(PAGINAS / "geih_explorar.py"), default_timeout=60).run()
    assert not at.exception
    assert "dd.geih.serie_tabla([2021, 2025]" in at.code[0].value

    extra = at.multiselect(key="exp_extra")
    assert any(o.startswith("P6040 ") for o in extra.options)  # las de CORE_RAW también se ofrecen
    extra.set_value(["P5000", "P6040"]).run()
    assert not at.exception
    assert "columns=['P5000']" in at.code[0].value             # P6040 ya se lee siempre

    next(b for b in at.button if b.label == "Exportar a CSV").click().run()
    assert not at.exception
    exportado = pd.read_csv(next((geih_root / "exportaciones").glob("*.csv")), encoding="utf-8-sig")
    assert len(exportado) == 2 and "P5000" in exportado.columns  # ocupados de enero 2021 y enero 2025

    # Otra selección se exporta a otro archivo: no pisa la anterior
    next(m for m in at.multiselect if m.label == "Columnas").set_value(["anio", "mes", "fex"]).run()
    next(b for b in at.button if b.label == "Exportar a CSV").click().run()
    assert not at.exception
    assert len(list((geih_root / "exportaciones").glob("*.csv"))) == 2

    # Para Excel en español: otro archivo, con «;» y coma decimal
    at.toggle(key="exp_excel").set_value(True).run()
    next(b for b in at.button if b.label == "Exportar a CSV").click().run()
    assert not at.exception
    assert 'sep=\';\', decimal=\',\'' in at.code[-1].value
    excel = [f for f in (geih_root / "exportaciones").glob("*.csv")
             if f.read_text(encoding="utf-8-sig").startswith("anio;mes;fex")]
    assert len(excel) == 1 and len(list((geih_root / "exportaciones").glob("*.csv"))) == 3


def _solo_un_mes(load):
    """La app nunca debe pedir más de un mes de microdatos a la vez."""
    def envoltura(years, months=None, **kw):
        assert months is not None and len([months] if isinstance(months, int) else months) == 1
        return load(years, months=months, **kw)
    return envoltura


def test_descargas_se_arman_al_hacer_clic(eam_root, monkeypatch):
    """Sin clic no se arma el Excel: antes se armaban CSV, Excel y Stata en cada interacción."""
    from dane_data.app import _ui

    monkeypatch.setitem(dd.config._session, "eam", eam_root)
    monkeypatch.setattr(pd.DataFrame, "to_excel", lambda *a, **k: pytest.fail("Excel armado sin clic"))
    at = AppTest.from_file(str(PAGINAS / "eam_industria.py"), default_timeout=60).run()
    assert not at.exception
    monkeypatch.undo()
    df = pd.DataFrame({"anio": [2023, 2024], "sector": pd.Categorical(["A", None]),
                       "n": pd.array([1, None], dtype="Int64")})
    assert pd.read_excel(io.BytesIO(_ui._excel(df)))["sector"].tolist() == ["A", np.nan]
    stata = pd.read_stata(io.BytesIO(_ui._stata(df)))
    assert stata["sector"].tolist() == ["A", ""] and stata["n"].tolist()[0] == 1


def test_tabla_pivote_conserva_el_orden_de_las_categorias(geih_root, tmp_path, monkeypatch):
    """El nivel educativo va de Ninguno a Superior, no en orden alfabético."""
    monkeypatch.setitem(dd.config._session, "geih", geih_root)
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    at = AppTest.from_file(str(PAGINAS / "geih_explorar.py"), default_timeout=60).run()
    at.radio[0].set_value(at.radio[0].options[0]).run()            # toda la población
    next(s for s in at.selectbox if s.label == "Filas").set_value("Nivel educativo").run()
    next(s for s in at.selectbox if s.label == "Columnas / comparar por").set_value("Sexo").run()
    assert not at.exception
    filas = [str(v) for v in at.dataframe[0].value.index]
    orden = [str(v) for v in dd.geih.NIVELES_EDUC if str(v) in filas]
    assert len(filas) > 2 and filas == orden


def test_eam_por_defecto_los_ultimos_10_anios(tmp_path, monkeypatch):
    for anio in range(2013, 2025):
        archivo = tmp_path / "datos" / str(anio) / f"EAM_{anio}.csv"
        archivo.parent.mkdir(parents=True)
        archivo.write_text("nordemp;nordest;dpto;ciiu4;PRODBR2;CONSIN2;VALAGRI;PERTOTAL;PPERYTEM;SALPEYTE;PRESPYTE\n"
                           f"1;10;5;1011;200;120;{anio};12;10;20;4\n", encoding="utf-8")
    monkeypatch.setitem(dd.config._session, "eam", tmp_path)
    at = AppTest.from_file(str(PAGINAS / "eam_industria.py"), default_timeout=60).run()
    assert not at.exception
    assert at.select_slider[0].value == (2015, 2024)              # antes (2014, 2024): 11 años
