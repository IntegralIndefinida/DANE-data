"""Encuesta Nacional de Calidad de Vida: carpetas, carga, armonización e indicadores."""

import json
import warnings

import numpy as np
import pandas as pd
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
        if nombre in df:  # las de capítulos que no se cargaron no están
            assert df[nombre].dtype == tipo
    assert {"anio", "fex", "area", "region", "departamento", "sexo", "edad", "parentesco", "etnia",
            "afiliado_salud"} <= set(df.columns)
    assert {c for c in df.columns if c.islower()} <= set(dd.ecv.ETIQUETAS["persona"])  # todas documentadas


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
        if nombre in df:  # las de capítulos que no se cargaron no están
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


# ---------------------------------------------------------------------------------------------------- #
# Indicadores
# ---------------------------------------------------------------------------------------------------- #
def test_anios_educacion_como_el_dane():
    nan = np.nan
    crudo = pd.DataFrame({  # no estudia: ninguno, primaria 3, media 13 (normal), superior 4 años; estudia: preescolar,
        "P8586": [2, 2, 2, 2, 1, 1, 1],  # secundaria cursando 7, universidad con 2 años aprobados
        "P8587": [1, 3, 5, 11, nan, nan, nan], "P8587S1": [nan, 3, 13, nan, nan, nan, nan],
        "P6211": [nan, nan, nan, 4, nan, nan, nan],
        "P1088": [nan, nan, nan, nan, 1, 3, 7], "P1088S1": [nan, nan, nan, nan, nan, 7, nan],
        "P6216": [nan, nan, nan, nan, nan, nan, 2]})
    assert dd.ecv.harmonize(crudo).anios_educacion.tolist() == [0, 3, 13, 15, 0, 6, 13]


def test_armonizadas_de_los_capitulos():
    crudo = pd.DataFrame({"P6090": [1, 2, 9, 1], "P6100": [2, None, 3, 3], "P1910": [5, 5, 1, None],
                          "P1911": [5, 2, 5, None], "P1084": [5, 4, 1, None], "P1082": [2, 2, 1, None],
                          "P5504": [1, 2, None, None], "P5095": [3, 1, 6, 4], "P1075": [1, 2, None, 1]})
    d = dd.ecv.harmonize(crudo)
    assert d.afiliado_salud.tolist() == [True, False, False, True]  # «no sabe» no es afiliado
    assert d.regimen_salud.tolist()[0] == "Especial" and pd.isna(d.regimen_salud[1])
    assert d.usa_computador.tolist()[:3] == [False, True, True] and pd.isna(d.usa_computador[3])
    assert d.usa_internet.tolist()[:3] == [False, True, True]
    assert d.usa_celular.tolist()[:3] == [True, False, True]  # el primero no tiene, pero usa uno
    assert d.tenencia_vivienda.tolist()[0] == "En arriendo o subarriendo"
    assert d.internet_hogar.tolist()[:2] == [True, False] and pd.isna(d.internet_hogar[2])


def _personas():
    """Dos hogares: uno de 3 personas (fex 10) y otro de 2 (fex 5)."""
    jefe, hijo = "Jefe(a) del hogar", "Hijo(a) o hijastro(a)"
    return pd.DataFrame({
        "anio": [2025] * 5, "fex": [10.0, 10.0, 10.0, 5.0, 5.0], "area": ["Cabecera"] * 3 + ["Centros poblados y rural disperso"] * 2,
        "parentesco": [jefe, hijo, hijo, jefe, hijo], "edad": [40, 8, 18, 70, 3],
        "internet_hogar": pd.array([True] * 3 + [False] * 2, dtype="boolean"),
        "tenencia_vivienda": ["En arriendo o subarriendo"] * 3 + ["Propia, totalmente pagada"] * 2,
        "afiliado_salud": pd.array([True, True, False, True, True], dtype="boolean"),
        "regimen_salud": ["Contributivo", "Especial", None, "Subsidiado", "Subsidiado"],
        "asiste": pd.array([False, True, False, False, None], dtype="boolean"),
        "anios_educacion": [11.0, 2.0, 11.0, 5.0, np.nan],
        "usa_internet": pd.array([True, False, True, False, None], dtype="boolean"),
    })


def test_indicadores_de_hogares_sobre_los_jefes():
    r = dd.ecv.indicadores(_personas()).iloc[0]
    assert (r.hogares, r.personas, r.personas_por_hogar) == (15, 40, 40 / 15)
    assert r.pct_internet_hogar == pytest.approx(100 * 10 / 15)
    assert r.pct_arriendo == pytest.approx(100 * 10 / 15) and r.pct_propia_pagada == pytest.approx(100 * 5 / 15)
    assert r.pct_afiliados == pytest.approx(100 * 30 / 40)
    assert r.pct_contributivo == pytest.approx(100 * 20 / 30)  # con el especial, sobre los afiliados
    assert r.pct_subsidiado == pytest.approx(100 * 10 / 30)
    assert r.pct_asistencia_6_21 == 50 and r.pct_asistencia_6_10 == 100 and r.pct_asistencia_17_21 == 0
    assert r.anios_educacion_5_mas == pytest.approx((10 * 11 + 10 * 2 + 10 * 11 + 5 * 5) / 35)
    assert r.pct_usa_internet == pytest.approx(100 * 20 / 35)  # de 5 años y más
    assert "pct_afiliados" not in dd.ecv.indicadores(_personas().drop(columns="afiliado_salud"))


def test_indicadores_por_grupo_y_de_hogares():
    r = dd.ecv.indicadores(_personas(), por=["anio", "area"])
    assert r.area.tolist() == ["Cabecera", "Centros poblados y rural disperso"]
    assert r.pct_internet_hogar.tolist() == [100, 0]
    hogares = _personas().iloc[[0, 3]].drop(columns="parentesco")  # una tabla de hogares
    r = dd.ecv.indicadores(hogares)
    assert r.hogares.tolist() == [15] and "personas" not in r and r.pct_internet_hogar.tolist() == [pytest.approx(200 / 3)]
    with pytest.raises(ValueError, match="fex"):
        dd.ecv.indicadores(_personas().drop(columns="fex"))


def test_serie_indicadores_con_cache(ecv_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    with pytest.warns(UserWarning, match="faltan capítulos"):
        r = dd.ecv.serie_indicadores([2018, 2025], root=ecv_root)
    assert r.anio.tolist() == [2018, 2025]
    assert r.hogares.tolist() == [5.5, 221]  # 2018 con los factores del CNPV 2018
    assert r.pct_afiliados.isna().tolist() == [True, False]  # 2018 no tiene Salud en los datos de prueba
    assert len(list((tmp_path / "cache" / "ecv" / "indicadores").glob("*.parquet"))) == 2
    pd.testing.assert_frame_equal(dd.ecv.serie_indicadores([2018, 2025], root=ecv_root), r)
    with pytest.warns(UserWarning, match="faltan capítulos"):
        r = dd.ecv.serie_indicadores(2025, por="area", filtros={"sexo": ["Mujer"]}, root=ecv_root)
    assert r.area.tolist() == ["Cabecera", "Centros poblados y rural disperso"]
    assert dd.ecv.clear_cache() == 3
    with pytest.raises(FileNotFoundError):
        dd.ecv.serie_indicadores(2019, root=ecv_root)
