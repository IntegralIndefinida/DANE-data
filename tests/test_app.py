"""Páginas de la app con el probador de Streamlit (se salta si no está instalado el extra `app`)."""

from pathlib import Path

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


def _solo_un_mes(load):
    """La app nunca debe pedir más de un mes de microdatos a la vez."""
    def envoltura(years, months=None, **kw):
        assert months is not None and len([months] if isinstance(months, int) else months) == 1
        return load(years, months=months, **kw)
    return envoltura
