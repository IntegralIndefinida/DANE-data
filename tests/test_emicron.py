"""Encuesta de Micronegocios (EMICRON): carpetas, descarga, carga, indicadores y validación."""

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dane_data as dd
from dane_data import cli


def test_carpeta_emicron(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EMICRON", raising=False)
    assert dd.get_path("emicron") == dd.config.DEFAULT_HOME / "emicron"
    dd.set_paths(emicron=tmp_path / "x", guardar=True)
    assert json.loads((tmp_path / "c.json").read_text())["emicron"] == str(tmp_path / "x")
    assert dd.show_paths()["emicron"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("emicron") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_EMICRON", str(tmp_path / "env"))
    assert dd.get_path("emicron") == tmp_path / "env"


# ---------------------------------------------------------------------------------------------------- #
# Carga y armonización (datos sintéticos de tests/conftest.py)
# ---------------------------------------------------------------------------------------------------- #
def _load(raiz, anios, **kw):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)  # módulos que el sintético no trae
        return dd.emicron.load(anios, raiz=raiz, **kw)


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
    with pytest.warns(UserWarning, match="2021: falta el factor ajustado") as avisos:
        e = dd.emicron.load(2021, modulos=[], raiz=emicron_root)
    assert e["fex"].tolist() == [300.0, 200.0, 100.0]
    assert {a.filename for a in avisos} == {__file__}  # sale de varias funciones adentro: apunta igual a esta línea


def test_factor_departamental_contradictorio_es_error(emicron_root):
    f = emicron_root / "datos" / "2024" / "fex_dpto.csv"
    f.write_text(f.read_text() + "20,1,1,5\n")
    with pytest.raises(ValueError, match="dos factores distintos"):
        dd.emicron.load(2024, modulos=[], raiz=emicron_root)


def test_modulos_ausentes_avisan(emicron_root):
    with pytest.warns(UserWarning, match="2021: sin el módulo capital_social \\(el DANE no lo aplicó"):
        dd.emicron.load(2021, modulos=["capital_social"], raiz=emicron_root)
    with pytest.warns(UserWarning, match="2024: sin el módulo tic \\(no está descargado"):
        dd.emicron.load(2024, modulos=["tic"], raiz=emicron_root)
    # Inclusión financiera de 2021 no cubre a todos: la fila queda vacía, no se pierde
    e = dd.emicron.load(2021, modulos=["inclusion_financiera"], columnas=["p1765"], raiz=emicron_root)
    assert e["p1765"].tolist()[:2] == [1, 2] and pd.isna(e["p1765"].iloc[2])


def test_columnas_all_y_extras(emicron_root):
    e = _load(emicron_root, 2024, columnas="all")
    assert {"p35", "p3053", "f_exp", "fex"} <= set(e.columns)
    assert not [c for c in e.columns if c.endswith(("_x", "_y"))] and not e.columns.duplicated().any()
    e = _load(emicron_root, 2019, columnas="P3089")
    assert list(e.columns) == [*dd.emicron.CORE, "p3089"]
    with pytest.raises(ValueError, match="p9999"):
        _load(emicron_root, 2019, columnas=["p9999"])


def test_factores_pedidos_como_modulo_no_se_unen(emicron_root):
    """Los factores se leen siempre aparte: pedirlos en modulos no los une como un módulo (2021 trae una clave repetida)."""
    e = dd.emicron.load(2021, modulos=["fex_dpto", "fex_ajustado"], raiz=emicron_root)
    assert e["fex_dpto"].tolist() == [270.0, 170.0, 95.0] and e["fex"].tolist() == [260.0, 180.0, 90.0]
    assert list(e.columns) == dd.emicron.CORE
    todo = dd.emicron.load(2021, modulos="fex_dpto", columnas="all", raiz=emicron_root)
    assert "fex_micro_dpto" not in todo.columns


def test_load_errores(emicron_root, tmp_path):
    with pytest.raises(FileNotFoundError, match="dane_data.emicron.download"):
        dd.emicron.load(2020, raiz=emicron_root)
    with pytest.raises(ValueError, match="load_personal"):
        dd.emicron.load(2024, modulos="personal_ocupado", raiz=emicron_root)
    with pytest.raises(ValueError, match="Módulo desconocido"):
        dd.emicron.load(2024, modulos="nomina", raiz=emicron_root)


def test_aviso_de_cobertura_2025(emicron_root):
    with pytest.warns(UserWarning, match="2025 solo cubren las 24 ciudades"):
        dd.emicron.load(2025, raiz=emicron_root)


def test_codigo_sin_categoria_se_avisa(emicron_root, caplog):
    f = emicron_root / "datos" / "2025" / "identificacion.csv"
    f.write_text(f.read_text(encoding="utf-8-sig").replace(",2,03,05,700", ",7,03,05,700"), encoding="utf-8")
    e = _load(emicron_root, 2025)
    assert pd.isna(e["situacion_empleo"].iloc[0])
    assert "situacion_empleo trae códigos sin categoría (7)" in caplog.text


def test_load_personal_con_la_clave_corrida(emicron_root):
    p = dd.emicron.load_personal(2024, raiz=emicron_root)
    assert p[["directorio", "secuencia_p", "secuencia_encuesta", "orden"]].values.tolist() == [
        [20, 1, 1, 1], [20, 1, 1, 2], [22, 1, 1, 1], [22, 1, 1, 2]]
    assert p["tipo"].tolist() == ["Trabajador remunerado", "Socio", "Trabajador o familiar sin remuneración",
                                  "Trabajador o familiar sin remuneración"]
    assert p["fex"].tolist() == [1000.5, 1000.5, 250.0, 250.0]  # el del micronegocio
    assert p["actividad"].iloc[0] == "Servicios"
    with pytest.raises(FileNotFoundError):
        dd.emicron.load_personal(2019, raiz=emicron_root)


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


def test_sin_factor_departamental_en_otro_anio_pide_descargarlo(emicron_root):
    """En 2019–2024 el factor departamental existe: si falta es el archivo, no la EMICRON 2025."""
    (emicron_root / "datos" / "2024" / "fex_dpto.csv").unlink()
    with pytest.warns(UserWarning) as avisos:  # también el de cobertura de 2025
        e = dd.emicron.load([2024, 2025], raiz=emicron_root)
    assert any("2024: falta el factor departamental" in str(a.message) for a in avisos)
    with pytest.raises(ValueError, match="Falta el factor departamental de 2024: vuelva a descargar") as error:
        dd.emicron.indicadores(e[e["anio"] == 2024], peso="fex_dpto")
    assert "2025" not in str(error.value)
    with pytest.raises(ValueError, match="Falta el factor departamental de 2024") as error:
        dd.tabla(e, por="anio", peso="fex_dpto")
    assert "2025 no trae factor departamental" in str(error.value)  # las dos causas, cada una con su año


def test_indicadores_sin_micronegocios(emicron_root):
    """Un filtro que no deja a nadie da cero micronegocios, no un error."""
    vacio = _load(emicron_root, 2024).iloc[0:0]
    r = dd.emicron.indicadores(vacio, por=None)
    assert len(r) == 1 and r[["micronegocios", "n_muestra"]].values.tolist() == [[0.0, 0]]
    assert r[["ventas", "pct_rut"]].isna().all(axis=None)
    por_clase = dd.emicron.indicadores(vacio, por="clase")
    assert por_clase.empty and "n_muestra" in por_clase.columns


def test_indicadores_sin_separar_anios_avisa(emicron_root):
    e = _load(emicron_root, [2021, 2024])
    with pytest.warns(UserWarning) as avisos:
        r = dd.emicron.indicadores(e, por=None)
    assert any("varios años" in str(a.message) for a in avisos)
    assert len(r) == 1 and r["n_muestra"].iloc[0] == 6


def test_indicadores_sin_peso_dejan_fuera_esas_filas(emicron_root):
    e = _load(emicron_root, [2024, 2025])
    with pytest.warns(UserWarning, match="Sin fex_dpto: se dejan fuera 1 de 2025"):
        r = dd.emicron.indicadores(e, peso="fex_dpto")
    assert r["anio"].tolist() == [2024]  # 2025 no trae factor departamental: no se suma como cero
    assert r[["micronegocios", "n_muestra"]].values.tolist() == [[1740.0, 3]]
    with pytest.raises(ValueError, match="2025 no trae factor departamental") as error:
        dd.emicron.indicadores(_load(emicron_root, 2025), peso="fex_dpto")
    assert "vuelva a descargar" not in str(error.value)  # en 2025 no falta ningún archivo
    with pytest.warns(UserWarning, match="2025: sin consumo intermedio"):  # el sintético no trae ventas
        assert dd.emicron.indicadores(_load(emicron_root, 2025))["micronegocios"].tolist() == [700.0]


# ---------------------------------------------------------------------------------------------------- #
# Diccionario
# ---------------------------------------------------------------------------------------------------- #
def test_diccionario():
    d = dd.diccionario("emicron")
    assert d["P35"]["categorias"] == {"1": "Hombre", "2": "Mujer"}
    assert dd.describir("valor_agregado", encuesta="emicron") == "Valor agregado mensual"
    assert "P1633" in dd.buscar_variable("tributario", "emicron")["variable"].tolist()
    assert len(d["F_EXP"]["modulos"]) > 5  # la repiten los módulos: una sola entrada con todos
    assert all(etiqueta for v in d.values() for etiqueta in v["categorias"].values())
    # Las variables de CORE que vienen del DANE están en el diccionario
    origenes = {o.upper() for _, o, _ in dd.emicron.loader._ARMONIZADAS.values()} | {m.upper() for m in dd.emicron.MONTOS}
    assert origenes <= set(d)


# ---------------------------------------------------------------------------------------------------- #
# Línea de comandos
# ---------------------------------------------------------------------------------------------------- #
def test_cli_estado(emicron_root, monkeypatch, capsys):
    monkeypatch.setitem(dd.config._session, "emicron", emicron_root)
    assert cli.main(["estado"]) == 0
    assert "EMICRON: 4 años (2019–2025)" in capsys.readouterr().out


def test_cli_estado_sin_datos(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(dd.config._session, "emicron", tmp_path / "nada")
    assert cli.main(["estado"]) == 0
    assert "EMICRON: sin datos" in capsys.readouterr().out


def test_cli_descargar(monkeypatch):
    llamada = {}
    monkeypatch.setattr(dd.emicron, "download", lambda **kw: llamada.update(kw) or [])
    assert cli.main(["descargar", "emicron", "--anios", "2024", "--modulos", "ventas", "tic", "--borrar-zips"]) == 0
    assert llamada == {"years": [2024], "modulos": ["ventas", "tic"], "delete_zips": True, "forzar": False}
    monkeypatch.setattr(dd.emicron, "download", lambda **kw: ["2024 ventas: no se pudo descargar"])
    assert cli.main(["descargar", "emicron", "--anios", "2024"]) == 1


@pytest.mark.parametrize("argumentos, mensaje", [
    (["descargar", "emicron", "--tipos", "fetales"], "no aplica"),
    (["descargar", "emicron", "--empalme"], "no aplica"),
    (["descargar", "emicron", "--modulos", "ocupados"], "no son de esta encuesta"),
    (["descargar", "geih", "--modulos", "ventas"], "no son de esta encuesta"),
    (["descargar", "eam", "--modulos", "ventas"], "no aplica"),
])
def test_cli_opciones_de_otra_encuesta(argumentos, mensaje, capsys):
    assert cli.main(argumentos) == 2
    assert mensaje in capsys.readouterr().err


def test_cli_config(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EMICRON", raising=False)
    assert cli.main(["config", "--emicron", str(tmp_path / "x")]) == 0
    assert json.loads((tmp_path / "c.json").read_text())["emicron"] == str(tmp_path / "x")


# ---------------------------------------------------------------------------------------------------- #
# Datos reales (se saltan sin la EMICRON descargada)
# ---------------------------------------------------------------------------------------------------- #
REAL = Path(os.environ.get("DANE_DATA_TEST_EMICRON", dd.get_path("emicron")))
# Los módulos que usan load(columnas="core") e indicadores
_PARA_INDICADORES = ("identificacion", "caracteristicas", "propietario", "sitio", "costos", "ventas")


def _reales(anio: int, *modulos: str) -> None:
    """Salta la prueba si en los datos reales falta el año o alguno de los módulos que usa."""
    tiene = dd.emicron.find_files(anio, raiz=REAL).get(anio, {})
    if faltan := [m for m in modulos if m not in tiene]:
        pytest.skip(f"sin la EMICRON {anio} real ({', '.join(faltan)})")


def test_real_2025_sin_factor_departamental():
    _reales(2025, "identificacion")
    with pytest.warns(UserWarning, match="24 ciudades"):
        e = dd.emicron.load(2025, modulos=[], raiz=REAL)
    assert e["fex_dpto"].isna().all() and e["fex"].notna().all()
    with pytest.raises(ValueError, match="fex_dpto"):
        dd.emicron.indicadores(e, peso="fex_dpto")


def test_real_load_2024():
    _reales(2024, "identificacion", "caracteristicas", "propietario", "sitio")
    e = dd.emicron.load(2024, raiz=REAL)
    assert len(e) == 78_501
    assert e["fex"].sum() == pytest.approx(5_297_251.5562481, abs=1e-3)
    for c in ("clase", "sexo", "situacion_empleo", "actividad", "actividad12", "sitio", "salud_pension", "departamento"):
        assert e[c].notna().all(), c  # ningún código sin categoría
    assert e["ciudad"].notna().sum() == 52_430  # las 24 ciudades


# ---------------------------------------------------------------------------------------------------- #
# Validación contra los anexos del DANE (tests/datos/dane_emicron_publicado.csv)
# ---------------------------------------------------------------------------------------------------- #
DATOS = Path(__file__).parent / "datos"
_VARIABLES = ["situacion_empleo", "sexo", "actividad", "sitio", "salud_pension", "rut", "camara_comercio"]
_MONTOS_I1 = ["ventas", "consumo_intermedio", "valor_agregado", "remuneracion", "sueldos", "prestaciones",
              "ingreso_mixto", "coeficiente_tecnico"]
# Lo que dd.emicron no puede reproducir con los microdatos, con el motivo (ver docs/guia/diferencias.md): por cuadro y
# variable, o solo en una categoría
CONOCIDAS = {
    **{(2019, "I.1", m): "los microdatos de 2019 no traen los montos calculados" for m in _MONTOS_I1[1:]},
    **{(2019, "B.1", "actividad", c): "el anexo clasifica en servicios (alojamiento y comida) unos 48.549 micronegocios "
                                      "que los microdatos traen como industria, y no traen el código CIIU para separarlos"
       for c in ("Industria manufacturera", "Servicios")},
    (2019, "I.1", "trabajadores_remunerados"): "el anexo cuenta las filas del módulo de personal, y P3032_1 da 0,2 % menos",
    (2019, "I.1", "personal_ocupado"): "incluye a los trabajadores remunerados (ver arriba)",
}


def _publicado() -> pd.DataFrame:
    return pd.read_csv(DATOS / "dane_emicron_publicado.csv", keep_default_na=False)


def test_publicado_completo():
    """El CSV que usan las pruebas reales: sin claves repetidas y con todos los años, cuadros y ciudades."""
    pub = _publicado()
    assert not pub.duplicated(["anio", "dominio", "cuadro", "variable", "categoria"]).any()
    assert sorted(pub["anio"].unique()) == list(range(2019, 2026))
    ciudades = set(dd.emicron.CIUDADES.values())
    for anio, p in pub.groupby("anio"):
        dominios = set(p["dominio"])
        assert ciudades <= dominios, anio
        nacional = {"total", "Cabeceras municipales", "Centros poblados y rural disperso"}
        assert (nacional <= dominios) == (anio <= 2024), anio  # 2025 solo trae las 24 ciudades
        assert set(p["cuadro"]) == {"A1.10", "A1.12", "B.1", "D.1", "E.1.1", "F.1", "F.6", "I.1"}, anio
        assert dominios - ciudades - nacional == {"24 ciudades"}, anio  # nombres de ciudad traducidos
    categorias = {str(c) for t in dd.emicron.CATEGORIAS.values() for c in t.categories} | {"True", "False", "Total", ""}
    assert set(pub["categoria"]) <= categorias


def _calculado(e: pd.DataFrame, variables_i1, peso: str = "fex") -> pd.DataFrame:
    if peso == "fex":
        dominios = {"total": e, "24 ciudades": e[e["ciudad"].notna()]}
        dominios |= {str(c): g for c, g in e.groupby("clase", observed=True)}
        dominios |= {str(c): g for c, g in e.groupby("ciudad", observed=True)}
    else:
        dominios = {"25 departamentos": e} | {str(c): g for c, g in e.groupby("departamento", observed=True)}
    filas = []
    for dominio, g in dominios.items():
        for v in _VARIABLES:
            s = g.groupby(g[v].astype("string"))[peso].sum()
            filas += [(dominio, v, k, x) for k, x in s.items()] + [(dominio, v, "Total", g[peso].sum())]
        ind = dd.emicron.indicadores(g, por=None, peso=peso).iloc[0]
        filas += [(dominio, v, "", ind[v]) for v in variables_i1]
    return pd.DataFrame(filas, columns=["dominio", "variable", "categoria", "calculado"])


def test_reales_se_saltan_si_falta_un_anio_o_un_modulo(emicron_root, monkeypatch):
    monkeypatch.setitem(globals(), "REAL", emicron_root)  # el sintético: 2019, 2021, 2024 y 2025, con pocos módulos
    _reales(2024, *_PARA_INDICADORES)  # 2024 los tiene todos: no se salta
    with pytest.raises(pytest.skip.Exception, match="2019 real \\(caracteristicas"):
        _reales(2019, *_PARA_INDICADORES)
    with pytest.raises(pytest.skip.Exception, match="2020 real"):
        _reales(2020, "identificacion")


@pytest.mark.parametrize("anio", range(2019, 2026))
def test_real_coincide_con_los_anexos(anio):
    """Cuadros A1.10, A1.12, B.1, D.1, E.1.1, F.1, F.6 e I.1: nacional, cabeceras, centros poblados y 24 ciudades."""
    _reales(anio, *_PARA_INDICADORES, *(["fex_ajustado"] if anio <= 2021 else []))
    pub = _publicado().query("anio == @anio")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        e = dd.emicron.load(anio, raiz=REAL)
        calc = _calculado(e, pub.loc[pub["cuadro"] == "I.1", "variable"].unique())
    m = pub.merge(calc, on=["dominio", "variable", "categoria"], how="left")
    # Una categoría que nadie tiene en una ciudad: el anexo publica 0, la tabla no tiene la fila
    m["calculado"] = pd.to_numeric(m["calculado"], errors="coerce").astype("float64").fillna(0.0)
    m["ok"] = np.isclose(m["calculado"], m["valor"], rtol=1e-9, atol=1e-6)
    conocida = m.apply(lambda r: (anio, r["cuadro"], r["variable"]) in CONOCIDAS
                       or (anio, r["cuadro"], r["variable"], r["categoria"]) in CONOCIDAS, axis=1)
    malas = m[~m["ok"] & ~conocida]
    assert malas.empty, malas[["dominio", "cuadro", "variable", "categoria", "valor", "calculado"]].head(20).to_string()
    assert (~conocida).sum() >= 900  # que las conocidas no tapen la comparación: cada año compara más de 900 cifras


# Erratas de los anexos departamentales: la cifra publicada no cuadra con las demás del mismo anexo
CONOCIDAS_DEPARTAMENTOS = {
    (2023, "Atlántico", "I.1", "prestaciones"): "el anexo trae 147.202.380 y sus sueldos más prestaciones no dan su "
                                                "remuneración (826.458.979); con 147.202.280 sí, que es lo que da dd.emicron",
}


def test_errata_del_anexo_departamental_2023():
    """La errata existe en el propio anexo: sueldos + prestaciones publicados no dan la remuneración publicada."""
    pub = pd.read_csv(DATOS / "dane_emicron_departamentos.csv", keep_default_na=False)
    a = pub.query("anio == 2023 and dominio == 'Atlántico' and cuadro == 'I.1'").set_index("variable")["valor"]
    assert a["sueldos"] + a["prestaciones"] - a["remuneracion"] == pytest.approx(100, abs=1e-3)


@pytest.mark.parametrize("anio", range(2020, 2025))
def test_real_coincide_con_los_anexos_departamentales(anio):
    """Los mismos cuadros para los 24 departamentos y Bogotá, con el factor departamental (fex_dpto)."""
    _reales(anio, *_PARA_INDICADORES, "fex_dpto")
    pub = pd.read_csv(DATOS / "dane_emicron_departamentos.csv", keep_default_na=False).query("anio == @anio")
    assert pub["dominio"].nunique() == 26
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        e = dd.emicron.load(anio, raiz=REAL)
        calc = _calculado(e, pub.loc[pub["cuadro"] == "I.1", "variable"].unique(), peso="fex_dpto")
    m = pub.merge(calc, on=["dominio", "variable", "categoria"], how="left")
    m["calculado"] = pd.to_numeric(m["calculado"], errors="coerce").astype("float64").fillna(0.0)
    errata = m.apply(lambda r: (anio, r["dominio"], r["cuadro"], r["variable"]) in CONOCIDAS_DEPARTAMENTOS, axis=1)
    malas = m[~np.isclose(m["calculado"], m["valor"], rtol=1e-9, atol=1e-6) & ~errata]
    assert malas.empty, malas[["dominio", "cuadro", "variable", "categoria", "valor", "calculado"]].head(20).to_string()
