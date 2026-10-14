import os
import sys
from pathlib import Path

import pandas as pd
import pytest

import dane_data as dd
from dane_data.geih.loader import classify_file, month_from_folder


@pytest.mark.parametrize("name,expected", [
    ("Cabecera - Características generales (Personas).csv", ("caracteristicas", "cabecera")),
    ("Resto - Caracteristicas generales (Personas).CSV", ("caracteristicas", "resto")),
    ("Area - Desocupados (1).csv", ("no_ocupados", "area")),
    ("No ocupados.CSV", ("no_ocupados", None)),
    ("Ocupados.CSV", ("ocupados", None)),
    ("Datos del hogar y la vivienda.CSV.CSV", ("vivienda", None)),
    ("Otras formas de trabajo.CSV", ("otras", None)),
    ("Fuerza de trabajo.CSV", ("fuerza", None)),
    ("No ocupado.CSV", ("no_ocupados", None)),                 # marzo 2024, en singular
    ("Area - Ocupados04.csv", ("ocupados", "area")),            # 2013, sufijo de mes
    ("Resto - Deocupados04.csv", ("no_ocupados", "resto")),
])
def test_classify_file(name, expected):
    assert classify_file(name) == expected


@pytest.mark.parametrize("folder,mes", [
    ("Enero", 1), ("Diciembre_csv", 12), ("1.Enero", 1), ("10. Octubre", 10), ("Ene_2024", 1),
    ("GEIH_Octubre_Marco_2018", 10), ("GEIH_Marzo_2022_Marco_2018", 3), ("Septiembre.csv 2 1", 9),
    ("Noviembre_ 2024", 11), ("Total Departamentos", None), ("total_2009_csv", None),
])
def test_month_from_folder(folder, mes):
    assert month_from_folder(folder) == mes


def test_available_marks_incomplete(geih_root):
    av = dd.geih.available(root=geih_root)
    assert list(zip(av.anio, av.mes)) == [(2016, 1), (2025, 1), (2025, 2)]
    assert av.set_index("mes").loc[2, "faltantes"] == "desocupados"
    assert av.completo.tolist() == [True, True, False]


def test_old_era_cabecera_plus_resto(geih_root):
    df = dd.geih.load(2016, root=geih_root, cache=False)
    assert len(df) == 5  # Cabecera (4) + Resto (1); Area no se duplica
    assert df["fex"].tolist() == pytest.approx([100.5, 100.5, 100.5, 200.0, 300.25])  # coma decimal
    cond = df.set_index(["DIRECTORIO", "ORDEN"])["condicion"]
    assert cond[(1, 1)] == "Ocupado"
    assert cond[(1, 2)] == "Desocupado"
    assert cond[(1, 3)] == "Fuera de la PET"
    assert cond[(3, 1)] == "Inactivo"
    assert df["sexo"].tolist() == ["Hombre", "Mujer", "Mujer", "Hombre", "Mujer"]
    assert df.loc[df.ORDEN.eq(1) & df.DIRECTORIO.eq(1), "formal"].item() == 1
    assert df.loc[df.DIRECTORIO.eq(2), "formal"].item() == 0
    assert set(df["rama_rev"].dropna()) == {3}
    assert df.loc[df.DIRECTORIO.eq(1) & df.ORDEN.eq(1), "nivel_educativo"].item() == "Superior"


def test_new_era_and_nested_folder(geih_root):
    df = dd.geih.load(2025, root=geih_root, cache=False, columns=["P5000"])
    assert df.attrs["meses_omitidos"] == [(2025, 2, ["desocupados"])]
    assert (df["mes"] == 1).all()
    cond = df.set_index(["DIRECTORIO", "ORDEN"])["condicion"]
    assert cond[(10, 2)] == "Desocupado"  # viene de la subcarpeta "CSV 13"
    assert cond[(11, 1)] == "Inactivo"
    assert df.loc[df.ORDEN.eq(1) & df.DIRECTORIO.eq(10), "ratio_smlv"].item() == pytest.approx(1.0)
    assert "P5000" in df.columns  # módulo hogar fusionado por DIRECTORIO + SECUENCIA_P


def test_posicion_ocupacional_cambia_en_2022():
    """Desde 2022 el código 7 de P6430 es jornalero y el 8 'otro' (antes eran el 8 y el 9)."""
    df = pd.DataFrame({"anio": [2021, 2021, 2021, 2022, 2022], "mes": 1, "OCI": 1, "P6430": [7, 8, 9, 7, 8]})
    assert dd.geih.harmonize(df)["posicion_ocupacional"].tolist() == [
        "Sin remuneración (otros hogares)", "Jornalero o peón", "Otro", "Jornalero o peón", "Otro"]


def test_load_variables(geih_root):
    completo = dd.geih.load([2016, 2025], root=geih_root, cache=False)
    df = dd.geih.load([2016, 2025], root=geih_root, cache=False, variables=["fex", "departamento", "P6040"])
    assert list(df.columns) == ["anio", "mes", "fex", "departamento", "P6040"]
    pd.testing.assert_frame_equal(df, completo[df.columns])
    assert isinstance(df["departamento"].dtype, pd.CategoricalDtype)  # se conserva al concatenar meses


def test_include_incomplete(geih_root):
    df = dd.geih.load(2025, root=geih_root, cache=False, incluir_incompletos=True)
    assert set(df["mes"]) == {1, 2}


def test_indicadores_weighted(geih_root):
    df = dd.geih.load(2016, root=geih_root, cache=False)
    ind = dd.geih.indicadores(df).iloc[0]
    # FT = ocupados (100.5 + 200) + desocupados (100.5)
    assert ind["fuerza_trabajo"] == pytest.approx(401.0)
    assert ind["td"] == pytest.approx(100 * 100.5 / 401.0)
    assert ind["pet"] == pytest.approx(701.25)
    assert ind["tasa_informalidad"] == pytest.approx(100 * 200 / 300.5)


def test_tabla_averages_months(geih_root):
    df = dd.geih.load(2025, root=geih_root, cache=False, incluir_incompletos=True)
    t = dd.tabla(df, por="anio")
    # Enero: 2501 personas expandidas; Febrero: 1000 → promedio mensual 1750.5
    assert t["total"].item() == pytest.approx((1000.5 * 2 + 500 + 1000) / 2)


def test_cache_roundtrip(geih_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    a = dd.geih.load(2016, root=geih_root)
    b = dd.geih.load(2016, root=geih_root)
    assert list((tmp_path / "cache" / "geih").glob("*.parquet"))
    pd.testing.assert_frame_equal(a, b, check_dtype=False, check_categorical=False)


@pytest.mark.parametrize("anual", [True, False])
@pytest.mark.parametrize("por", dd.geih.POR_PRECALCULADOS)
def test_serie_indicadores_igual_a_indicadores(geih_root, tmp_path, monkeypatch, por, anual):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    esperado = dd.geih.indicadores(dd.geih.load([2016, 2025], root=geih_root, cache=False), por=por, anual=anual)
    serie = dd.geih.serie_indicadores([2016, 2025], por=por, anual=anual, root=geih_root)
    pd.testing.assert_frame_equal(serie, esperado)


def test_serie_indicadores_usa_cache_y_se_invalida(geih_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    a = dd.geih.serie_indicadores(2016, root=geih_root)
    assert len(list((tmp_path / "cache" / "geih" / "indicadores").glob("principal_2016_*.parquet"))) == 1

    mod = sys.modules["dane_data.geih.indicadores"]  # dd.geih.indicadores es la función
    llamadas = []
    original = mod.load
    monkeypatch.setattr(mod, "load", lambda *a, **k: llamadas.append(1) or original(*a, **k))
    pd.testing.assert_frame_equal(dd.geih.serie_indicadores(2016, root=geih_root), a)
    assert not llamadas

    csv = next((geih_root / "datos_csv" / "2016").rglob("Cabecera - Ocupados.csv"))
    os.utime(csv, (csv.stat().st_atime, csv.stat().st_mtime + 10))
    dd.geih.serie_indicadores(2016, root=geih_root)
    assert llamadas


def test_serie_indicadores_por_no_precalculado(geih_root):
    with pytest.raises(ValueError, match="no está precalculado"):
        dd.geih.serie_indicadores(2016, por="rama2d", root=geih_root)


def test_missing_data_message(tmp_path):
    with pytest.raises(FileNotFoundError, match="download"):
        dd.geih.load(2020, root=tmp_path)


# --------------------------------------------------------------------------- #
# Integración con datos reales (se salta si no están)
# --------------------------------------------------------------------------- #
REAL = Path(os.environ.get("DANE_DATA_TEST_GEIH", dd.get_path("geih")))


@pytest.mark.skipif(not (REAL / "datos_csv" / "2025").is_dir(), reason="sin datos GEIH reales")
@pytest.mark.parametrize("anio,mes,td", [(2016, 1, 11.9), (2019, 1, 12.8), (2021, 1, 17.3), (2025, 1, 11.6)])
def test_real_td_matches_dane(anio, mes, td):
    df = dd.geih.load(anio, months=mes, root=REAL)
    assert dd.geih.indicadores(df)["td"].item() == pytest.approx(td, abs=0.15)


REAL_EMPALME = Path(os.environ.get("DANE_DATA_TEST_GEIH_EMPALME", dd.get_path("geih_empalme")))
# Cambios de metodología: la PET cambia de golpe y es correcto.
QUIEBRES_PET = {
    False: {(2020, 1): "2020 viene con proyecciones CNPV 2018 y PET de 15 años o más",
            (2021, 1): "2021 vuelve al marco 2005 (PET 12+ urbano, 10+ rural)",
            (2022, 1): "rediseño 2022: marco 2018 y PET de 15 años o más"},
    True: {},
}
CHOQUES = {(2020, 4): "inicio de la pandemia"}  # saltos reales en las tasas


@pytest.mark.parametrize("empalme", [False, True], ids=["principal", "empalme"])
def test_real_serie_mensual_sin_saltos(empalme):
    """
    La serie mensual no debe tener huecos ni saltos bruscos. La PET crece ~0,1 % al mes: un
    cambio de más de 1 % delata un factor de expansión dañado o una PET con otra definición.
    """
    root = REAL_EMPALME if empalme else REAL
    av = dd.geih.available(empalme=empalme, root=root) if (root / "datos_csv").is_dir() else pd.DataFrame()
    if av.empty:
        pytest.skip(f"sin datos GEIH reales en {root}")
    m = dd.geih.serie_indicadores(sorted(av.anio.unique()), anual=False, empalme=empalme, root=root)

    problemas = []
    faltan = set(zip(av.loc[av.completo, "anio"], av.loc[av.completo, "mes"])) - set(zip(m.anio, m.mes))
    problemas += [f"{a}-{ms:02d}: mes completo en disco sin filas en la serie" for a, ms in sorted(faltan)]
    validos = (m["pet"] > 0) & m[["td", "tgp", "to"]].notna().all(axis=1)
    problemas += [f"{a}-{ms:02d}: sin población expandida o tasas vacías (¿fex dañado?)"
                  for a, ms in zip(m.loc[~validos, "anio"], m.loc[~validos, "mes"])]

    m = m[validos].sort_values(["anio", "mes"]).reset_index(drop=True)
    indice = m["anio"] * 12 + m["mes"]
    seguidos = indice.diff() == 1  # solo meses consecutivos: tras un hueco no se compara
    for i in m.index[seguidos]:
        a, ms, antes, ahora = int(m.at[i, "anio"]), int(m.at[i, "mes"]), m.loc[i - 1], m.loc[i]
        cambio_pet = 100 * (ahora["pet"] / antes["pet"] - 1)
        if abs(cambio_pet) > 1 and (a, ms) not in QUIEBRES_PET[empalme]:
            problemas.append(f"{a}-{ms:02d}: la PET cambia {cambio_pet:+.1f} %")
        for tasa in ("td", "tgp", "to"):
            salto = ahora[tasa] - antes[tasa]
            if abs(salto) > 5 and (a, ms) not in CHOQUES:
                problemas.append(f"{a}-{ms:02d}: {tasa.upper()} salta {salto:+.1f} p.p.")
    assert not problemas, f"{len(problemas)} problema(s) en la serie {'empalme' if empalme else 'principal'}:\n" + \
        "\n".join(sorted(problemas))
