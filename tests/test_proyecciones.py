"""Las proyecciones empaquetadas: cifras del DANE, empalmes y desagregaciones."""

import warnings

import pytest

import dane_data as dd


@pytest.mark.parametrize("anio, total", [(1950, 13_570_943), (1985, 30_419_892), (2005, 41_671_878),
                                         (2018, 48_258_494), (2025, 53_057_212), (2070, 50_592_097)])
def test_totales_del_dane(anio, total):
    assert dd.poblacion(anio)["poblacion"].tolist() == [total]


def test_empalmes_sin_saltos():
    """Los años en que cambia de archivo del DANE (1985, 1993, 2005, 2018, 2046, 2051) no saltan."""
    serie = dd.poblacion().set_index("anio")["poblacion"]
    variacion = serie.pct_change().abs().dropna()
    assert variacion.max() < 0.03
    assert list(serie.index) == list(range(1950, 2071))


def test_departamentos_suman_el_total():
    t = dd.poblacion(range(1985, 2051))
    d = dd.poblacion(range(1985, 2051), por="departamento")
    assert d["departamento"].nunique() == 33
    assert d.groupby("anio")["poblacion"].sum().tolist() == t["poblacion"].tolist()


def test_desagregaciones_suman_el_total():
    total = dd.poblacion(2020)["poblacion"].iloc[0]
    for por in ("sexo", "area", "edad", "dpto", ["sexo", "area"], ["departamento", "sexo", "edad"]):
        assert dd.poblacion(2020, por=por)["poblacion"].sum() == total


def test_filtros():
    m = dd.poblacion(2020, sexo="Mujer")["poblacion"].iloc[0]
    h = dd.poblacion(2020, sexo="Hombre")["poblacion"].iloc[0]
    assert m + h == dd.poblacion(2020)["poblacion"].iloc[0]
    jovenes = dd.poblacion(2020, edades=(15, 28))["poblacion"].iloc[0]
    assert jovenes == dd.poblacion(2020, edades=(15, 28), por="edad")["poblacion"].sum()
    assert dd.poblacion(2020, edades=15)["poblacion"].iloc[0] < jovenes
    cabecera = dd.poblacion(2020, area="Cabecera")["poblacion"].iloc[0]
    resto = dd.poblacion(2020, area="Centros poblados y rural disperso")["poblacion"].iloc[0]
    assert cabecera + resto == dd.poblacion(2020)["poblacion"].iloc[0]


def test_departamento_por_nombre_o_codigo():
    esperado = dd.poblacion(2020, departamento="Bogotá D.C.")["poblacion"].iloc[0]
    assert dd.poblacion(2020, departamento=11)["poblacion"].iloc[0] == esperado
    assert dd.poblacion(2020, departamento="bogota d.c.")["poblacion"].iloc[0] == esperado
    dos = dd.poblacion(2020, departamento=["Chocó", 11], por="departamento")
    assert sorted(dos["departamento"]) == ["Bogotá D.C.", "Chocó"]


def test_anios_sin_ese_detalle_avisan():
    with pytest.warns(UserWarning, match="1980"):
        res = dd.poblacion([1980, 1990], por="departamento")
    assert res["anio"].unique().tolist() == [1990]
    with pytest.warns(UserWarning, match="2060"):
        assert dd.poblacion(2060, area="Cabecera").empty
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert dd.poblacion(1980)["poblacion"].iloc[0] > 0  # el total nacional sí está


def test_area_sin_partir_sale_como_total():
    assert dd.poblacion(2060, por="area")["area"].tolist() == ["Total"]


@pytest.mark.parametrize("kw", [dict(por="municipio"), dict(sexo="Otro"), dict(area="Rural"),
                                dict(departamento="Narnia"), dict(departamento=2)])
def test_argumentos_invalidos(kw):
    with pytest.raises(ValueError):
        dd.poblacion(2020, **kw)


def test_no_se_puede_danar_la_copia_en_memoria():
    res = dd.poblacion(2020)
    res["poblacion"] = 0
    assert dd.poblacion(2020)["poblacion"].iloc[0] > 0
