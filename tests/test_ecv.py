"""Encuesta Nacional de Calidad de Vida: carpetas, carga, armonización, indicadores e IPM."""

import json
import os
import warnings
from pathlib import Path

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


# ---------------------------------------------------------------------------------------------------- #
# IPM
# ---------------------------------------------------------------------------------------------------- #
# Una persona sin ninguna privación: adulto que trabaja y cotiza, sabe leer, con media completa y salud; vivienda urbana
# con acueducto, alcantarillado, piso de baldosa, paredes de ladrillo y dos cuartos.
_NADA = dict(anio=2025, DIRECTORIO=1, SECUENCIA_P=1, fex=10.0, edad=40, area="Cabecera", region="Bogotá D.C.",
             departamento="Bogotá D.C.", sexo="Mujer", parentesco="Jefe(a) del hogar", P8586=2, P8587=5, P8587S1=11,
             P6211=np.nan, P1088=np.nan, P1088S1=np.nan, P6160=1, P6090=1, P5665=2, P8563=np.nan, P51=np.nan,
             P55=np.nan, P774=np.nan, P6180=np.nan, P6240=1, P6250=np.nan, P6260=np.nan, P6270=np.nan, P6351=np.nan,
             P7250=np.nan, P6920=1, P8520S5=1, P8520S3=1, P8530=1, P8526=1, P4015=4, P4005=1, P5010=2, P3336S1=np.nan,
             P3336S2=np.nan, P3336S3=np.nan, P3337=np.nan, P1075=1)
_HIJO = dict(parentesco="Hijo(a) o hijastro(a)", P6240=np.nan, P6920=np.nan, P8587=np.nan, P8587S1=np.nan)


def _hogar(*personas, **del_hogar):
    """Un hogar: cada persona son los cambios sobre _NADA; del_hogar cambia a todas (la vivienda, el año)."""
    return pd.DataFrame([{**_NADA, **del_hogar, **p} for p in (personas or ({},))])


def _priv(*personas, **del_hogar) -> pd.Series:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # 2020 sin la base complementaria
        fila = dd.ecv.privaciones(_hogar(*personas, **del_hogar)).iloc[0]
    return fila[[p for p in dd.ecv.PRIVACIONES if fila[p]]].index.tolist()


def test_privaciones_de_educacion_y_ninez():
    assert _priv() == []
    assert _priv({"P8587S1": 10}, {**_HIJO, "edad": 20, "P8587": 4, "P8587S1": 7}) == ["logro_educativo"]  # (10+7)/2 < 9
    # la media cuenta hasta 11: (5 + 11) / 2 < 9; con el 13 de la normal serían 9
    assert _priv({"P8587": 3, "P8587S1": 5}, {**_HIJO, "edad": 18, "P8587": 5, "P8587S1": 13}) == ["logro_educativo"]
    # la superior suma el año aprobado a 11, y a 16 en posgrado: (3 + 14) / 2 < 9, (3 + 17) / 2 >= 9
    assert _priv({"P8587": 3, "P8587S1": 3}, {**_HIJO, "edad": 23, "P8586": 1, "P1088": 7, "P1088S1": 4}) == ["logro_educativo"]
    assert _priv({"P8587": 3, "P8587S1": 3}, {**_HIJO, "edad": 30, "P8587": 13, "P8587S1": 1}) == []
    assert _priv({"P6160": 2}) == ["analfabetismo"]
    assert _priv({"edad": 14, "P8586": 1, "P1088": 3, "P1088S1": 9, "P6240": 3, "P6920": np.nan}) == [
        "logro_educativo", "analfabetismo", "desempleo_larga_duracion", "empleo_formal"]  # sin mayores de 15 ni PEA
    nino = {**_HIJO, "edad": 10, "P8586": 1, "P1088": 2, "P1088S1": 5}
    deserto = {**nino, "P8586": 2, "P1088": np.nan, "P1088S1": np.nan, "P8587": 3, "P8587S1": 2}  # aprobó 2.º
    assert _priv({}, deserto) == ["inasistencia_escolar", "rezago_escolar"]
    virtual = {**nino, "P3336S1": 2, "P3336S2": 1, "P3336S3": 2, "P3337": 1}
    assert _priv({}, virtual) == []
    assert _priv({}, virtual, P1075=2) == ["inasistencia_escolar"]  # solo virtual y sin internet
    assert _priv({}, {**virtual, "P3337": 2}) == ["inasistencia_escolar"]  # sin contacto con los maestros
    assert _priv({}, {**nino, "P1088S1": 2}) == ["rezago_escolar"]  # a los 10 años, 1 año aprobado
    assert _priv({}, {**_HIJO, "edad": 3, "P6090": 2}) == ["atencion_integral"]
    assert _priv({}, {**_HIJO, "edad": 3, "P51": 7}) == ["atencion_integral"]  # en casa solo
    assert _priv({}, {**_HIJO, "edad": 3, "P51": 1, "P55": 1, "P774": 2}) == []  # jardín con comida por pago simbólico
    assert _priv({}, {**_HIJO, "edad": 3, "P51": 1, "P55": 1, "P774": 1}) == ["atencion_integral"]
    assert _priv({}, {**_HIJO, "edad": 5, "P8586": 1, "P1088": 1}) == []  # sin el dato de la comida en el colegio
    assert _priv({}, {**_HIJO, "edad": 5, "P8586": 1, "P1088": 1, "P6180": 2}) == ["atencion_integral"]
    assert _priv({}, {**nino, "edad": 15, "P1088": 3, "P1088S1": 10, "P6240": 1}) == ["trabajo_infantil"]


def test_inasistencia_de_2020_con_la_base_complementaria():
    """En 2020, con los colegios cerrados, la inasistencia sale de las estrategias de estudio en casa."""
    nino = {**_HIJO, "edad": 10, "P8586": 1, "P1088": 2, "P1088S1": 5, "P1077S21": 2, "P1077S22": 2, "P1077S23": 2,
            "CELULAR_INTELIGENTE": 2, "CELULAR": 1, "P5305": 2, "EST_PLATAFORMAS": 2, "EST_GUIAS": 2, "EST_LLAMADA": 2,
            "EST_VISITA": 2}
    en_2020 = dict(anio=2020, P4005=1)

    def priv(**cambios):
        return _priv({}, {**nino, **cambios}, **en_2020)

    assert priv(ESTRATEGIAS=1, EST_PLATAFORMAS=1, CELULAR_INTELIGENTE=1) == []       # plataformas, internet y celular
    assert priv(ESTRATEGIAS=1, EST_PLATAFORMAS=1) == ["inasistencia_escolar"]          # plataformas sin equipo
    assert priv(ESTRATEGIAS=1, EST_GUIAS=1, EST_LLAMADA=1) == []                       # guías y llamadas
    assert priv(ESTRATEGIAS=1, EST_GUIAS=1) == ["inasistencia_escolar"]                # solo guías
    assert priv(ESTRATEGIAS=1, EST_LLAMADA=1) == ["inasistencia_escolar"]              # solo llamadas
    assert priv(ESTRATEGIAS=2, P1077S22=1) == []                                       # sin estrategias, pero conectado
    assert priv(ESTRATEGIAS=2, P1077S22=1, P1075=2) == ["inasistencia_escolar"]
    assert _priv({}, {**nino, "ESTRATEGIAS": 1, "EST_GUIAS": 1}) == []  # en 2025 la regla de 2020 no aplica


def test_privaciones_de_trabajo_salud_y_vivienda():
    buscando = {"P6240": 2, "P6250": 2, "P6260": 2, "P6270": 2, "P6351": 1, "P6920": np.nan}
    assert _priv({}, {**_HIJO, "edad": 30, **buscando, "P7250": 51}) == ["empleo_formal"]
    assert _priv({}, {**_HIJO, "edad": 30, **buscando, "P7250": 52}) == ["desempleo_larga_duracion"]  # 52 semanas o más
    assert _priv({"P6920": 2}) == ["empleo_formal"]
    assert _priv({"P6240": 5, "P6920": 3}) == ["desempleo_larga_duracion"]  # solo pensionados: no es informal
    assert _priv({"P6090": 9}) == ["aseguramiento_salud"]  # «no sabe»
    assert _priv({"P5665": 1, "P8563": 6}) == ["barreras_acceso_salud"]
    assert _priv({"P5665": 1, "P8563": 1}) == []
    assert _priv(P8520S5=2) == ["acueducto"]
    assert _priv(area="Centros poblados y rural disperso", P8520S5=2, P8520S3=2, P8526=2) == []  # en lo rural, la fuente
    assert _priv(area="Centros poblados y rural disperso", P8530=4, P8526=3) == ["acueducto", "alcantarillado"]
    assert _priv(P4015=7) == ["pisos"]
    assert _priv(P4005=5) == ["paredes"] and _priv(P4005=5, area="Centros poblados y rural disperso") == []
    assert _priv(P4005=10) == ["paredes"] and _priv(P4005=10, anio=2018) == []  # 2018: 9 es «sin paredes»
    assert _priv(P4005=10, anio=2020) == []  # el DANE siguió con los códigos de 2018–2019 en 2020
    assert _priv(P4005=9, anio=2018) == ["paredes"]
    tres = ({}, {**_HIJO, "edad": 41, "P6240": 1, "P6920": 1}, {**_HIJO, "edad": 42, "P6240": 1, "P6920": 1})
    assert _priv(*tres, P5010=1) == ["hacinamiento"]  # 3 por cuarto
    assert _priv(*tres, P5010=1, area="Centros poblados y rural disperso") == []  # en lo rural, más de 3


def test_umbral_y_agregados_del_ipm():
    pobre = _hogar({"P6160": 2, "P6090": 2, "P8587S1": 5}, P4015=7)  # 0,1 + 0,1 + 0,1 + 0,04 = 0,34
    casi = _hogar({"P6160": 2, "P6090": 2, "P8587S1": 5}, DIRECTORIO=2)  # 0,3
    lejos = _hogar({}, {**_HIJO, "edad": 30, "P6240": 1, "P6920": 1}, DIRECTORIO=3, fex=5.0, departamento="Vaupés",
                   area="Centros poblados y rural disperso", P6160=2, P6090=2, P8587S1=5, P4015=7)
    h = dd.ecv.privaciones(pd.concat([pobre, casi, lejos], ignore_index=True))
    assert h.pobre.tolist() == [True, False, True]
    assert h.puntaje.round(2).tolist() == [0.34, 0.3, 0.34] and h.personas.tolist() == [1, 1, 2]
    r = dd.ecv.ipm(h).iloc[0]  # nacional: sin lo rural de Vaupés
    assert (r.personas, r.personas_pobres, r.incidencia) == (20, 10, 50)
    assert r.intensidad == pytest.approx(34) and r.ipm == pytest.approx(0.17)
    assert r.hogares == 20 and r.pct_pisos == 50 and r.pct_aseguramiento_salud == 100  # privaciones: % de hogares
    assert h.region_ipm.tolist() == ["Bogotá (cabecera)", "Bogotá (cabecera)", "Orinoquía-Amazonía"]
    assert dd.ecv.ipm(h, por="region_ipm").personas.tolist() == [10, 20]  # por región, toda la muestra (Vaupés rural)
    assert dd.ecv.ipm(h, muestra="completa").personas.tolist() == [30]
    por_dpto = dd.ecv.ipm(h, por="departamento")  # con departamento, toda la muestra
    assert por_dpto.set_index("departamento").incidencia.to_dict() == {"Bogotá D.C.": 50, "Vaupés": 100}
    assert dd.ecv.ipm(pd.concat([pobre, casi], ignore_index=True), por="sexo_jefe").sexo_jefe.tolist() == ["Mujer"]
    with pytest.raises(ValueError, match="Muestra desconocida"):
        dd.ecv.ipm(h, muestra="rural")
    with pytest.warns(UserWarning, match="base complementaria"):
        dd.ecv.privaciones(pobre.assign(anio=2020))
    with pytest.raises(ValueError, match="MODULOS_IPM"):
        dd.ecv.privaciones(pobre.drop(columns="P6160"))


def test_serie_ipm_pide_los_capitulos(ecv_root):
    with pytest.raises(ValueError, match="le faltan los capítulos"):
        dd.ecv.serie_ipm(2025, root=ecv_root)
    with pytest.raises(FileNotFoundError):
        dd.ecv.serie_ipm(2019, root=ecv_root)


# ---------------------------------------------------------------------------------------------------- #
# Datos reales (se saltan si no están)
# ---------------------------------------------------------------------------------------------------- #
REAL = Path(os.environ.get("DANE_DATA_TEST_ECV", dd.get_path("ecv")))
hay_datos_reales = pytest.mark.skipif(not (REAL / "datos").is_dir(), reason="sin datos reales de la ECV")
DATOS = Path(__file__).parent / "datos"
# El anexo de 2024 trae intercambiados el uso de celular de Chocó y de Córdoba (vea la guía, «Diferencias con el DANE»)
_ECV_DIFERENCIAS = {(2024, "Chocó", "pct_usa_celular"), (2024, "Córdoba", "pct_usa_celular")}


def _comparar(publicado: pd.DataFrame, calculado: list[pd.DataFrame], llave: str) -> pd.DataFrame:
    calculado = pd.concat([c.rename(columns={llave: "dominio"}) if llave in c else c.assign(dominio="Total nacional")
                           for c in calculado])
    largo = calculado.melt(id_vars=["anio", "dominio"], var_name="indicador", value_name="calculado")
    largo["dominio"] = largo["dominio"].astype(str)
    return publicado.merge(largo, on=["anio", "dominio", "indicador"], how="left")


@hay_datos_reales
def test_real_indicadores_coinciden_con_la_serie_del_dane():
    """Los 27 indicadores de la serie 2018–2025 del DANE, nacionales, por área y por departamento."""
    publicado = pd.read_csv(DATOS / "dane_ecv_publicado.csv")
    anios = sorted(set(publicado.anio) & set(dd.ecv.available(root=REAL).anio))
    publicado = publicado[publicado.anio.isin(anios)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        partes = [dd.ecv.serie_indicadores(anios, root=REAL)] + [
            dd.ecv.serie_indicadores(anios, por=k, root=REAL).rename(columns={k: "dominio"}) for k in ("area", "departamento")]
    x = _comparar(publicado, partes, "dominio")
    x = x[~x.apply(lambda f: (f.anio, f.dominio, f.indicador) in _ECV_DIFERENCIAS, axis=1)]
    assert x.calculado.notna().all(), x[x.calculado.isna()].head()
    dif = (x.calculado - x.valor).abs()
    en_miles = x.indicador.isin(["hogares", "personas"])
    departamento = ~x.dominio.isin(["Total nacional", "Cabecera", "Centros poblados y rural disperso"])
    # Nacional y por área, exacto (el Cuadro 1 va en miles); por departamento, a menos de 0,1 puntos (5 cifras de 2023 y
    # 2024 difieren en 0,004 a 0,08)
    tolerancia = np.where(en_miles, 500, np.where(departamento, 0.1, 0.0005 * np.maximum(1, x.valor.abs())))
    malos = x[dif > tolerancia]
    assert malos.empty, malos.head(10)


@hay_datos_reales
def test_real_ipm_coincide_con_los_anexos_del_dane():
    """Incidencia, IPM y privaciones de los anexos del IPM, nacional, por área, región y departamento, en 2018–2025."""
    publicado = pd.read_csv(DATOS / "dane_ipm_publicado.csv")
    anios = sorted(set(publicado.anio) & set(dd.ecv.available(root=REAL).anio))
    publicado = publicado[publicado.anio.isin(anios)]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        partes = [dd.ecv.serie_ipm(anios, root=REAL)] + [
            dd.ecv.serie_ipm(anios, por=k, root=REAL).rename(columns={k: "dominio"})
            for k in ("area", "region_ipm", "departamento")]
    x = _comparar(publicado, partes, "dominio")
    assert x.calculado.notna().all(), x[x.calculado.isna()].head()
    # Los anexos redondean a 0,1 (el IPM a 0,001); en 2020 4 hogares y en 2021 21 tienen otra inasistencia escolar
    tolerancia = np.where(x.indicador == "ipm", 0.00051, np.where(x.anio.isin([2020, 2021]), 0.15, 0.051))
    malos = x[(x.calculado - x.valor).abs() > tolerancia]
    assert malos.empty, malos.head(10)


# ---------------------------------------------------------------------------------------------------- #
# Línea de comandos
# ---------------------------------------------------------------------------------------------------- #
def test_cli_estado_ecv(ecv_root, monkeypatch, capsys):
    monkeypatch.setitem(dd.config._session, "ecv", ecv_root)
    assert cli.main(["estado"]) == 0
    salida = capsys.readouterr().out
    assert "ECV:" in salida and "2025: 4 de 11 capítulos" in salida and "2018: 3 de 11 capítulos" in salida  # sin los factores


def test_cli_descargar_ecv(monkeypatch, capsys):
    llamada = {}
    monkeypatch.setattr(dd.ecv, "download", lambda **kw: llamada.update(kw) or [])
    assert cli.main(["descargar", "ecv", "--anios", "2024", "2025", "--modulos", "salud", "tic", "--borrar-zips"]) == 0
    assert llamada == {"years": [2024, 2025], "modulos": ["salud", "tic"], "delete_zips": True, "forzar": False}
    assert cli.main(["descargar", "ecv", "--modulos", "ocupados"]) == 2  # de la GEIH, no de la ECV
    assert "ocupados no existen" in capsys.readouterr().err
    assert cli.main(["descargar", "geih", "--modulos", "salud"]) == 2
    assert cli.main(["descargar", "ecv", "--tipos", "fetales"]) == 2
    assert "no aplica" in capsys.readouterr().err
