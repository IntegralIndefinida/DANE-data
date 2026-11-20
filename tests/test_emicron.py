"""Encuesta de Micronegocios (EMICRON): carpetas, descarga, carga, indicadores y validación."""

import json
import os
import warnings
from pathlib import Path

import pandas as pd
import pytest

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


# ---------------------------------------------------------------------------------------------------- #
# Carga y armonización (datos sintéticos de tests/conftest.py)
# ---------------------------------------------------------------------------------------------------- #
def _load(root, years, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # módulos que el sintético no trae
        return dd.emicron.load(years, root=root, **kw)


def test_load_mismo_esquema_todos_los_anios(emicron_root):
    e = _load(emicron_root, [2019, 2021, 2024, 2025])
    assert list(e.columns) == dd.emicron.CORE
    assert e.groupby("anio").size().to_dict() == {2019: 3, 2021: 3, 2024: 3, 2025: 1}
    for c, tipo in dd.emicron.CATEGORIAS.items():
        if c in e.columns:
            assert e[c].dtype == tipo, c  # pd.concat entre años no las vuelve texto
    assert set(dd.emicron.ETIQUETAS) == set(dd.emicron.CORE)


def test_armonizadas(emicron_root):
    e = _load(emicron_root, [2019, 2024]).set_index(["anio", "directorio"])
    assert e.loc[(2019, 1), ["clase", "sexo", "situacion_empleo", "actividad", "actividad12", "ciudad"]].tolist() == [
        "Cabeceras municipales", "Hombre", "Patrón o empleador", "Servicios",
        "Actividades artísticas, de entretenimiento, de recreación y otras actividades de servicios", "Cali A.M."]
    assert pd.isna(e.loc[(2019, 2), "ciudad"])  # fuera de las 24 ciudades
    assert e.loc[(2019, 2), "departamento"] == "Antioquia"
    assert e.xs(2019)["mes_ref"].tolist() == [1, 10, 12]  # ENERO, octubre, Diciembre
    assert e.loc[(2024, 20), ["rut", "camara_comercio", "salud_pension", "sitio"]].tolist() == [
        True, True, "Salud y pensión", "Local, tienda, taller, fábrica, oficina, consultorio"]
    assert e.loc[(2024, 21), "rut"] == False  # noqa: E712  (booleano nulable)
    # Personal: vacío es cero personas; el propietario cuenta siempre
    assert e.xs(2019)[["trabajadores_remunerados", "socios", "familiares_sin_remuneracion", "personal_ocupado"]].values.tolist() == [
        [2, 0, 0, 3], [0, 0, 0, 1], [0, 1, 1, 3]]


def test_fex_de_la_serie_vigente_y_departamental(emicron_root):
    e = _load(emicron_root, [2019, 2021, 2024]).set_index(["anio", "directorio"])
    # 2019 y 2021: el ajustado, no el F_EXP de los módulos; 2024: F_EXP
    assert e.xs(2019)["fex"].tolist() == [250.0, 90.5, 45.0]
    assert e.xs(2021)["fex"].tolist() == [260.0, 180.0, 90.0]
    assert e.xs(2024)["fex"].tolist() == [1000.5, 500.0, 250.0]
    # FEX_C es el ajustado en 2019–2021 pero el departamental en 2023–2024
    assert e.xs(2019)["fex_dpto"].tolist() == [260.0, 95.0, 40.0]
    assert e.xs(2021)["fex_dpto"].tolist() == [270.0, 170.0, 95.0]  # sin la clave repetida y vacía
    assert e.xs(2024)["fex_dpto"].tolist() == [990.0, 510.0, 240.0]


def test_tabla_no_divide_entre_12(emicron_root):
    """El factor es anual: con varios meses, dd.tabla debe sumarlo tal cual (no promediar meses, como en la GEIH)."""
    e = _load(emicron_root, 2024)
    assert e["mes_ref"].nunique() == 3
    assert dd.tabla(e)["total"].iloc[0] == e["fex"].sum()
    por_sexo = dd.tabla(e, por="sexo").set_index("sexo")["total"]
    assert por_sexo.to_dict() == {"Hombre": 1250.5, "Mujer": 500.0}


def test_montos_coma_decimal_y_2019_sin_derivadas(emicron_root):
    e = _load(emicron_root, [2019, 2024]).set_index(["anio", "directorio"])
    assert e.xs(2019)["ventas_mes_anterior"].tolist() == [1000000.0, 500000.5, 0.0]
    assert e.xs(2019)[["valor_agregado", "consumo_intermedio", "sueldos"]].isna().all().all()  # vacías, no cero
    assert e.loc[(2024, 20), ["valor_agregado", "consumo_intermedio", "remuneracion_total"]].tolist() == [3e6, 2e6, 1.5e6]


def test_sin_factor_ajustado_avisa_y_usa_el_anterior(emicron_root):
    (emicron_root / "datos" / "2021" / "fex_ajustado.csv").unlink()
    with pytest.warns(UserWarning, match="2021: falta el factor ajustado"):
        e = dd.emicron.load(2021, modulos=[], root=emicron_root)
    assert e["fex"].tolist() == [300.0, 200.0, 100.0]


def test_factor_departamental_contradictorio_es_error(emicron_root):
    f = emicron_root / "datos" / "2024" / "fex_dpto.csv"
    f.write_text(f.read_text() + "20,1,1,5\n")
    with pytest.raises(ValueError, match="dos factores distintos"):
        dd.emicron.load(2024, modulos=[], root=emicron_root)


def test_modulos_ausentes_avisan(emicron_root):
    with pytest.warns(UserWarning, match="2021: sin el módulo capital_social \\(el DANE no lo aplicó"):
        dd.emicron.load(2021, modulos=["capital_social"], root=emicron_root)
    with pytest.warns(UserWarning, match="2024: sin el módulo tic \\(no está descargado"):
        dd.emicron.load(2024, modulos=["tic"], root=emicron_root)
    # Inclusión financiera de 2021 no cubre a todos: la fila queda vacía, no se pierde
    e = dd.emicron.load(2021, modulos=["inclusion_financiera"], columns=["p1765"], root=emicron_root)
    assert e["p1765"].tolist()[:2] == [1, 2] and pd.isna(e["p1765"].iloc[2])


def test_columns_all_y_extras(emicron_root):
    e = _load(emicron_root, 2024, columns="all")
    assert {"p35", "p3053", "f_exp", "fex"} <= set(e.columns)
    assert not [c for c in e.columns if c.endswith(("_x", "_y"))] and not e.columns.duplicated().any()
    e = _load(emicron_root, 2019, columns="P3089")
    assert list(e.columns) == [*dd.emicron.CORE, "p3089"]
    with pytest.raises(ValueError, match="p9999"):
        _load(emicron_root, 2019, columns=["p9999"])


def test_load_errores(emicron_root, tmp_path):
    with pytest.raises(FileNotFoundError, match="dane_data.emicron.download"):
        dd.emicron.load(2020, root=emicron_root)
    with pytest.raises(ValueError, match="load_personal"):
        dd.emicron.load(2024, modulos="personal_ocupado", root=emicron_root)
    with pytest.raises(ValueError, match="Módulo desconocido"):
        dd.emicron.load(2024, modulos="nomina", root=emicron_root)


def test_aviso_de_cobertura_2025(emicron_root):
    with pytest.warns(UserWarning, match="2025 solo cubren las 24 ciudades"):
        dd.emicron.load(2025, root=emicron_root)


def test_codigo_sin_categoria_se_avisa(emicron_root, caplog):
    f = emicron_root / "datos" / "2025" / "identificacion.csv"
    f.write_text(f.read_text(encoding="utf-8-sig").replace(",2,03,05,700", ",7,03,05,700"), encoding="utf-8")
    e = _load(emicron_root, 2025)
    assert pd.isna(e["situacion_empleo"].iloc[0])
    assert "situacion_empleo trae códigos sin categoría (7)" in caplog.text


def test_load_personal_con_la_clave_corrida(emicron_root):
    p = dd.emicron.load_personal(2024, root=emicron_root)
    assert p[["directorio", "secuencia_p", "secuencia_encuesta", "orden"]].values.tolist() == [
        [20, 1, 1, 1], [20, 1, 1, 2], [22, 1, 1, 1], [22, 1, 1, 2]]
    assert p["tipo"].tolist() == ["Trabajador remunerado", "Socio", "Trabajador o familiar sin remuneración",
                                  "Trabajador o familiar sin remuneración"]
    assert p["fex"].tolist() == [1000.5, 1000.5, 250.0, 250.0]  # el del micronegocio
    assert p["actividad"].iloc[0] == "Servicios"
    with pytest.raises(FileNotFoundError):
        dd.emicron.load_personal(2019, root=emicron_root)


# ---------------------------------------------------------------------------------------------------- #
# Indicadores
# ---------------------------------------------------------------------------------------------------- #
def test_indicadores_como_el_cuadro_i1(emicron_root):
    e = _load(emicron_root, 2024)
    r = dd.emicron.indicadores(e).iloc[0]
    w = e["fex"]
    assert r["micronegocios"] == w.sum() == 1750.5
    assert r["personal_ocupado"] == (e["personal_ocupado"] * w).sum() == 1000.5 * 3 + 500 + 250 * 3
    # Montos: el mes de referencia por 12, en miles de pesos
    assert r["ventas"] == pytest.approx((e["ventas_mes_anterior"] * w).sum() * 12 / 1000)
    assert r["valor_agregado"] == pytest.approx((3e6 * 1000.5 + 5e5 * 500 + 2e5 * 250) * 12 / 1000)
    # Cociente de sumas, no promedio de cocientes
    assert r["coeficiente_tecnico"] == pytest.approx(100 * (2e6 * 1000.5 + 3e5 * 500 + 1e5 * 250)
                                                    / (5e6 * 1000.5 + 8e5 * 500 + 3e5 * 250))
    assert r["pct_rut"] == pytest.approx(100 * (1000.5 + 250) / 1750.5)
    assert r["pct_camara_comercio"] == pytest.approx(100 * 1000.5 / 1750.5)
    assert r["pct_salud_pension"] == pytest.approx(100 * 1000.5 / 1750.5)  # «Solo pensión» no cuenta
    assert r["n_muestra"] == 3


def test_indicadores_por_grupo_peso_y_dropna(emicron_root):
    e = _load(emicron_root, 2024)
    r = dd.emicron.indicadores(e, por=["anio", "clase"]).set_index("clase")
    assert r["micronegocios"].to_dict() == {"Cabeceras municipales": 1500.5, "Centros poblados y rural disperso": 250.0}
    assert r.index.dtype == dd.emicron.CATEGORIAS["clase"]
    por_ciudad = dd.emicron.indicadores(e, por="ciudad")
    assert por_ciudad["micronegocios"].sum() == 1500.5  # sin el de fuera de las 24 ciudades
    assert dd.emicron.indicadores(e, por="ciudad", dropna=False)["micronegocios"].sum() == 1750.5
    assert dd.emicron.indicadores(e, peso="fex_dpto")["micronegocios"].iloc[0] == 990 + 510 + 240
    with pytest.raises(KeyError, match="nada"):
        dd.emicron.indicadores(e, por="nada")


def test_indicadores_2019_sin_derivadas_son_vacios(emicron_root):
    e = _load(emicron_root, [2019, 2024])
    with pytest.warns(UserWarning, match="EMICRON 2019: sin consumo intermedio"):
        r = dd.emicron.indicadores(e).set_index("anio")
    assert r.loc[2019, "ventas"] > 0
    assert r.loc[2019, ["consumo_intermedio", "valor_agregado", "coeficiente_tecnico", "pct_rut"]].isna().all()
    assert r.loc[2024, "valor_agregado"] > 0


def test_indicadores_sin_separar_anios_avisa(emicron_root):
    e = _load(emicron_root, [2021, 2024])
    with pytest.warns(UserWarning) as avisos:
        r = dd.emicron.indicadores(e, por=None)
    assert any("varios años" in str(a.message) for a in avisos)
    assert len(r) == 1 and r["n_muestra"].iloc[0] == 6


# ---------------------------------------------------------------------------------------------------- #
# Datos reales (se saltan sin la EMICRON descargada)
# ---------------------------------------------------------------------------------------------------- #
REAL = Path(os.environ.get("DANE_DATA_TEST_EMICRON", dd.get_path("emicron")))
hay_datos_reales = pytest.mark.skipif(not (REAL / "datos" / "2024").is_dir(), reason="sin datos reales de la EMICRON")


@hay_datos_reales
def test_real_load_2024():
    e = dd.emicron.load(2024, root=REAL)
    assert len(e) == 78_501
    assert e["fex"].sum() == pytest.approx(5_297_251.5562481, abs=1e-3)
    for c in ("clase", "sexo", "situacion_empleo", "actividad", "actividad12", "sitio", "salud_pension", "departamento"):
        assert e[c].notna().all(), c  # ningún código sin categoría
    assert e["ciudad"].notna().sum() == 52_430  # las 24 ciudades
