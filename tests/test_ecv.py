"""Encuesta Nacional de Calidad de Vida: carpetas."""

import json

import dane_data as dd
from dane_data import cli


def test_carpeta_ecv(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_ECV", raising=False)
    assert dd.get_path("ecv") == dd.config.DEFAULT_HOME / "ecv"
    dd.set_paths(ecv=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["ecv"] == str(tmp_path / "x")
    assert dd.show_paths()["ecv"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("ecv") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_ECV", str(tmp_path / "env"))
    assert dd.get_path("ecv") == tmp_path / "env"


def test_set_paths_posicional_no_cambia(tmp_path, monkeypatch):
    # ecv va al final: el quinto argumento posicional sigue siendo eevv
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_ECV", raising=False)
    dd.set_paths(tmp_path / "a", tmp_path / "b", tmp_path / "c", False, tmp_path / "d")
    assert dd.get_path("eevv") == tmp_path / "d"
    assert dd.get_path("ecv") == dd.config.DEFAULT_HOME / "ecv"


def test_cli_config_ecv(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_ECV", raising=False)
    assert cli.main(["config", "--ecv", str(tmp_path / "ecv")]) == 0
    assert json.loads((tmp_path / "c.json").read_text())["ecv"] == str(tmp_path / "ecv")
    assert "ecv" in capsys.readouterr().out
