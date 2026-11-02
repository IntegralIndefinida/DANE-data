"""Estadísticas Vitales: carpetas, carga, armonización, indicadores y tasas."""

import json

import dane_data as dd


def test_carpeta_eevv(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EEVV", raising=False)
    assert dd.get_path("eevv") == dd.config.DEFAULT_HOME / "eevv"
    dd.set_paths(eevv=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["eevv"] == str(tmp_path / "x")
    assert dd.show_paths()["eevv"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("eevv") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_EEVV", str(tmp_path / "env"))
    assert dd.get_path("eevv") == tmp_path / "env"
