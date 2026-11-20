"""Encuesta Nacional de Calidad de Vida: carpetas, carga y armonización."""

import json
import warnings

import pytest

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


# ---------------------------------------------------------------------------------------------------- #
# Carga y armonización
# ---------------------------------------------------------------------------------------------------- #
def _load(*args, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return dd.ecv.load(*args, **kw)


def test_load_personas_une_hogar_y_vivienda(ecv_root):
    df = _load(2025, modulos=["servicios", "salud"], root=ecv_root)
    assert len(df) == 5
    assert not df.duplicated(dd.ecv.KEYS_PERSONA).any()
    assert df.fex.tolist() == [100.5, 100.5, 100.5, 20.0, 20.0]
    # el hogar 2 de la vivienda 1 es SECUENCIA_ENCUESTA = 2 en Servicios y SECUENCIA_P = 2 en Características
    assert df.set_index(dd.ecv.KEYS_PERSONA).P5010.to_dict() == {(1, 1, 1): 2, (1, 1, 2): 2, (1, 2, 1): 1,
                                                                 (2, 1, 1): 1, (2, 1, 2): 1}
    assert df.P6090.isna().sum() == 1  # la persona que no está en Salud
    assert df.edad.tolist() == [45, 8, 70, 30, 29]
    assert df.sexo.tolist() == ["Hombre", "Mujer", "Mujer", "Hombre", "Mujer"]
    assert df.region.tolist() == ["Bogotá D.C."] * 3 + ["Antioquia"] * 2
    assert df.departamento.tolist() == ["Bogotá D.C."] * 3 + ["Antioquia"] * 2
    assert df.area.tolist() == ["Cabecera"] * 3 + ["Centros poblados y rural disperso"] * 2
    assert df.etnia.tolist()[2:4] == ["Negro(a), mulato(a), afrodescendiente", "Indígena"]
    assert df.parentesco.iloc[1] == "Hijo(a) o hijastro(a)"
    for nombre, tipo in dd.ecv.CATEGORIAS.items():
        assert df[nombre].dtype == tipo
    assert set(dd.ecv.ETIQUETAS["persona"]) <= set(df.columns)


def test_load_hogares(ecv_root):
    df = _load(2025, nivel="hogar", root=ecv_root)
    assert len(df) == 3 and df.fex.sum() == 221
    assert list(df[dd.ecv.KEYS_HOGAR].itertuples(index=False, name=None)) == [(1, 1), (1, 2), (2, 1)]
    assert "SECUENCIA_ENCUESTA" not in df and "sexo" not in df
    with pytest.raises(ValueError, match="capítulo de personas"):
        dd.ecv.load(2025, modulos="salud", nivel="hogar", root=ecv_root)
    with pytest.raises(ValueError, match="Nivel desconocido"):
        dd.ecv.load(2025, nivel="vivienda", root=ecv_root)
    with pytest.raises(ValueError, match="Módulo desconocido"):
        dd.ecv.load(2025, modulos="gastos", root=ecv_root)


def test_load_varios_anios_y_factores_de_2018(ecv_root):
    df = _load([2018, 2020, 2025], root=ecv_root)
    assert df.groupby("anio").size().to_dict() == {2018: 1, 2020: 1, 2025: 5}
    fila = df[df.anio == 2018].iloc[0]
    assert (fila.fex, fila.FEX_C, fila.FEX_C_ORIGINAL) == (5.5, 5.5, 9)  # el del CNPV 2018
    assert fila.departamento == "Bogotá D.C." and fila.region == "Oriental"
    assert df[df.anio == 2020].region.tolist() == ["Oriental"]  # sin REGION: rural de Bogotá
    for nombre, tipo in dd.ecv.CATEGORIAS.items():
        assert df[nombre].dtype == tipo


def test_load_avisa_lo_que_falta(ecv_root):
    with pytest.warns(UserWarning, match="salud en 2018"):
        df = dd.ecv.load([2018, 2025], modulos="salud", root=ecv_root)
    assert df[df.anio == 2018].P6090.isna().all()
    (ecv_root / "datos" / "2018" / "factores" / "Factores de expansión 2018 basados en el CNPV 2018.csv").unlink()
    with pytest.warns(UserWarning, match="CNPV 2018"):
        df = dd.ecv.load(2018, root=ecv_root)
    assert df.fex.tolist() == [9]
    with pytest.raises(FileNotFoundError, match="dane_data.ecv.download"):
        dd.ecv.load(2019, root=ecv_root)


def test_load_columns_limita_lo_que_se_lee(ecv_root):
    df = _load(2025, modulos="servicios", columns=["P5010"], root=ecv_root)
    assert "P5010" in df and "P5000" not in df and "P4005" not in df
    assert {"sexo", "edad", "region", "fex"} <= set(df.columns)  # las armonizadas siempre


def test_diccionario_ecv():
    d = dd.diccionario("ecv")
    assert d["P6090"]["modulos"] == ["salud"]
    assert d["P1075"]["modulos"] == ["condiciones"] and d["P1075"]["categorias"] == {"1": "Si", "2": "No"}
    assert set(d["DIRECTORIO"]["modulos"]) == set(dd.ecv.MODULOS)  # las llaves están en todos los capítulos
    assert {m for v in d.values() for m in v["modulos"]} == set(dd.ecv.MODULOS)
    assert dd.describir("p5230", encuesta="ecv") == "6. ¿Usted se considera pobre?"
    assert "P8586" in dd.buscar_variable("actualmente estudia", "ecv").variable.tolist()
