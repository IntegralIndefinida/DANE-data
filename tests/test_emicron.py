"""Encuesta de Micronegocios (EMICRON): carpetas, descarga, carga, indicadores y validación."""

import json

import dane_data as dd


def test_carpeta_emicron(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EMICRON", raising=False)
    assert dd.get_path("emicron") == dd.config.DEFAULT_HOME / "emicron"
    dd.set_paths(emicron=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["emicron"] == str(tmp_path / "x")
    assert dd.show_paths()["emicron"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("emicron") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_EMICRON", str(tmp_path / "env"))
    assert dd.get_path("emicron") == tmp_path / "env"
