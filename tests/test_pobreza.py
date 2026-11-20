"""Pobreza monetaria y desigualdad: carpetas, descarga, carga, indicadores y unión con la GEIH."""

import json

import dane_data as dd


def test_carpeta_pobreza(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_POBREZA", raising=False)
    assert dd.get_path("pobreza") == dd.config.DEFAULT_HOME / "pobreza"
    dd.set_paths(pobreza=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["pobreza"] == str(tmp_path / "x")
    assert dd.show_paths()["pobreza"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("pobreza") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_POBREZA", str(tmp_path / "env"))
    assert dd.get_path("pobreza") == tmp_path / "env"
