"""Páginas de la app con el probador de Streamlit (se salta si no está instalado el extra `app`)."""

from pathlib import Path

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
