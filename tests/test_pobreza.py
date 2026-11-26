"""Pobreza monetaria y desigualdad: carpetas, descarga, carga, indicadores y unión con la GEIH."""

import json
import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dane_data as dd
from dane_data import cli


def test_carpeta_pobreza(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_POBREZA", raising=False)
    assert dd.get_path("pobreza") == dd.config.DEFAULT_HOME / "pobreza"
    dd.set_paths(pobreza=tmp_path / "x", guardar=True)
    assert json.loads((tmp_path / "c.json").read_text())["pobreza"] == str(tmp_path / "x")
    assert dd.show_paths()["pobreza"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("pobreza") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_POBREZA", str(tmp_path / "env"))
    assert dd.get_path("pobreza") == tmp_path / "env"


# --------------------------------------------------------------------------- #
# Carga y armonización, con las rarezas de cada época del DANE

# Los datos sintéticos de cada época (fixture pobreza_root) están en conftest.py


def test_armoniza_todas_las_epocas(pobreza_root):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        df = dd.pobreza.load(raiz=pobreza_root)
    assert sorted(df.anio.unique()) == [2012, 2014, 2017, 2018, 2019, 2021, 2022, 2023, 2025]
    assert (df.groupby("anio").size() == 3).all()
    for c in ("dominio", "departamento", "zona", "ingreso_pc", "linea_pobreza", "fex", "fex_dpto"):
        assert df[c].notna().all(), c
    assert set(df.dominio) == {"Bogotá", "Medellín", "Rural"}
    assert set(df.departamento) == {"Bogotá D.C.", "Antioquia", "Cundinamarca"}
    # La zona rural con el departamento de Bogotá cuenta en Cundinamarca, como en los anexos del
    # DANE
    ruta = pobreza_root / "datos" / "2022" / "hogares.csv"
    h22 = pd.read_csv(ruta, sep=";", decimal=",")
    h22.loc[2, "Dpto"] = 11
    h22.to_csv(ruta, sep=";", decimal=",", index=False)
    assert dd.pobreza.load(2022, raiz=pobreza_root).departamento.tolist()[2] == "Cundinamarca"
    # 2014 (número de 1 a 24) y 2025 (nombre) bien traducidos
    assert (df.groupby("DIRECTORIO", observed=True).departamento.nunique() == 1).all()
    assert set(df.loc[df.DIRECTORIO == 3, "departamento"]) == {"Cundinamarca"}
    assert df.DIRECTORIO.dtype == "int64" and "UNNAMED: 0" not in df.columns
    assert df.pobre.tolist()[:3] == [True, False, True] and df.pobre_extremo.tolist()[:3] == [
        False,
        False,
        True,
    ]
    assert set(df.zona) == {"Urbano (cabecera)", "Rural (centros poblados y disperso)"}
    assert df.groupby("anio").metodologia.first().to_dict()[2018] == "mesep"
    assert df.groupby("anio").metodologia.first().to_dict()[2019] == "actualizacion"
    assert not df.empalmado.any()
    assert df.loc[df.anio == 2023, "ingreso_ug_arriendo"].notna().all()  # INGTOTARR


def test_columnas(pobreza_root):
    df = dd.pobreza.load(2018, raiz=pobreza_root)
    assert list(df.columns) == ["DIRECTORIO", "SECUENCIA_P", *dd.pobreza.ETIQUETAS]
    todo = dd.pobreza.load(2018, raiz=pobreza_root, columnas="all")
    assert {"POBRE", "INDIGENTE", "INGPCUG"} <= set(todo.columns)
    assert "POBRE" in dd.pobreza.load(2018, raiz=pobreza_root, columnas="POBRE").columns
    crudo = dd.pobreza.load(2018, raiz=pobreza_root, armonizar=False)
    assert "ingreso_pc" not in crudo and "INGPCUG" in crudo and (crudo.anio == 2018).all()


def test_avisa_si_mezcla_metodologias_o_marcos(pobreza_root):
    with pytest.warns(UserWarning, match="MESEP"):
        dd.pobreza.load([2018, 2019], raiz=pobreza_root)
    with pytest.warns(UserWarning, match="marco"):
        dd.pobreza.load([2021, 2022], raiz=pobreza_root)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dd.pobreza.load([2022, 2023], raiz=pobreza_root)
        dd.pobreza.load([2012, 2025], raiz=pobreza_root, empalme=True)


def test_empalme(pobreza_root):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        crudo = dd.pobreza.load([2017, 2019, 2021, 2022], raiz=pobreza_root)
    emp = dd.pobreza.load([2017, 2019, 2021, 2022], raiz=pobreza_root, empalme=True)
    c, e = (d.set_index(["anio", "DIRECTORIO"]) for d in (crudo, emp))
    # 2012–2020: fex × FEX_G
    assert np.allclose(e.loc[2017, "fex"], c.loc[2017, "fex"] * 0.5)
    assert np.allclose(e.loc[2019, "fex"], c.loc[2019, "fex"] * 0.5)
    # 2012–2018: líneas actualizadas (2017 trae el dominio con tildes) y pobreza recalculada
    assert (e.loc[2017, "linea_pobreza"] == 260).all() and e.loc[2017, "pobre"].all()
    assert (e.loc[2019, "linea_pobreza"] == c.loc[2019, "linea_pobreza"]).all()
    # 2021: ingreso y factor del archivo empalmado
    assert (
        np.allclose(e.loc[2021, "ingreso_pc"], c.loc[2021, "ingreso_pc"] * 2)
        and (e.loc[2021, "fex"] == 40).all()
    )
    assert e.loc[2021, "pobre"].tolist() == [False, False, False]
    # 2022 en adelante no cambia
    pd.testing.assert_frame_equal(
        e.loc[2022].drop(columns="empalmado"), c.loc[2022].drop(columns="empalmado")
    )
    assert (
        emp.loc[emp.anio <= 2021, "empalmado"].all() and (emp.metodologia == "actualizacion").all()
    )
    # El DANE no publica departamentos empalmados antes de 2021
    assert emp.loc[emp.anio <= 2020, "fex_dpto"].isna().all()
    assert (emp.loc[emp.anio == 2021, "fex_dpto"] == 7).all()


def test_empalme_exige_todos_los_hogares_y_los_archivos(pobreza_root):
    emp = pobreza_root / "datos" / "empalme" / "empalme_2012_2020.csv"
    fex_g = pd.read_csv(emp, sep=";")
    fex_g.iloc[1:].to_csv(emp, sep=";", index=False)  # falta un hogar de 2012
    with pytest.raises(ValueError, match="1 hogares de 2012"):
        dd.pobreza.load(2012, raiz=pobreza_root, empalme=True)
    pd.concat([fex_g, fex_g.iloc[[0]]]).to_csv(emp, sep=";", index=False)  # uno repetido
    with pytest.raises(ValueError, match="repetidas"):
        dd.pobreza.load(2012, raiz=pobreza_root, empalme=True)
    emp.unlink()
    with pytest.raises(FileNotFoundError, match="empalme=True"):
        dd.pobreza.load(2012, raiz=pobreza_root, empalme=True)
    dd.pobreza.load(2022, raiz=pobreza_root, empalme=True)  # desde 2022 no hace falta


def test_falla_con_dominio_desconocido_o_sin_linea(pobreza_root):
    ruta = pobreza_root / "datos" / "2019" / "hogares.csv"
    df = pd.read_csv(ruta, sep=";")
    df.loc[0, "Dominio"] = "MARTE"
    df.to_csv(ruta, sep=";", index=False)
    with pytest.raises(ValueError, match="MARTE"):
        dd.pobreza.load(2019, raiz=pobreza_root)
    df.loc[0, "Dominio"] = "BOGOTA"
    df["Lp"] = df["Lp"].astype(object)
    df.loc[0, "Lp"] = ""
    df.to_csv(ruta, sep=";", index=False)
    with pytest.raises(ValueError, match="linea_pobreza"):
        dd.pobreza.load(2019, raiz=pobreza_root)


def test_find_files_y_available(pobreza_root):
    (pobreza_root / "datos" / "notas").mkdir()
    assert sorted(dd.pobreza.find_files(raiz=pobreza_root)) == [
        2012,
        2014,
        2017,
        2018,
        2019,
        2021,
        2022,
        2023,
        2025,
    ]
    assert list(dd.pobreza.find_files([2014, 2030], raiz=pobreza_root)) == [2014]
    av = dd.pobreza.available(raiz=pobreza_root)
    assert av.anio.notna().sum() == 9 and not av.personas.any()
    assert set(av.loc[av.anio.isna(), "archivo"]) == set(dd.pobreza.ARCHIVOS_EMPALME)
    with pytest.raises(FileNotFoundError, match="download"):
        dd.pobreza.load(2030, raiz=pobreza_root)


# --------------------------------------------------------------------------- #
# Gini e indicadores
def test_weighted_gini():
    assert dd.weighted_gini([3, 1, 2], [2, 1, 1]) == pytest.approx(
        dd.weighted_gini([1, 2, 3, 3], [1, 1, 1, 1])
    )
    assert dd.weighted_gini([1, np.nan, 3], [1, 1, 1]) == pytest.approx(
        dd.weighted_gini([1, 3], [1, 1])
    )
    assert dd.weighted_gini([1, 2], [0, 5]) == 0.0  # peso 0: no cuenta
    assert np.isnan(dd.weighted_gini([], [])) and np.isnan(dd.weighted_gini([0, 0], [1, 1]))
    with pytest.raises(ValueError, match="negativos"):
        dd.weighted_gini([-1, 2], [1, 1])
    # Contra la fórmula de diferencias absolutas entre todos los pares, con pesos enteros
    rng = np.random.default_rng(0)
    y, w = rng.integers(0, 1000, 50).astype(float), rng.integers(1, 5, 50)
    r = np.repeat(y, w)
    pares = np.abs(r[:, None] - r[None, :]).sum() / (2 * len(r) ** 2 * r.mean())
    assert dd.weighted_gini(y, w) == pytest.approx(pares)


def _hogares_ind(**kw):
    base = {
        "anio": 2025,
        "ingreso_pc": [100.0, 150.0, 400.0],
        "linea_pobreza": 200.0,
        "linea_pobreza_extrema": 120.0,
        "fex": [10.0, 20.0, 10.0],
        "personas": [3, 2, 1],
        "zona": ["a", "a", "b"],
    }
    df = pd.DataFrame({**base, **kw})
    return df.assign(
        pobre=df.ingreso_pc < df.linea_pobreza,
        pobre_extremo=df.ingreso_pc < df.linea_pobreza_extrema,
    )


def test_indicadores_a_mano():
    r = dd.pobreza.indicadores(_hogares_ind()).iloc[0]
    # pesos de personas: 30, 40, 10
    assert r.personas == 80 and r.hogares == 40 and r.hogares_muestra == 3
    assert r.pobres == 70 and r.incidencia == pytest.approx(87.5)
    assert r.pobres_extremos == 30 and r.incidencia_extrema == pytest.approx(37.5)
    assert r.brecha == pytest.approx((30 * 0.5 + 40 * 0.25) / 80 * 100)
    assert r.severidad == pytest.approx((30 * 0.25 + 40 * 0.0625) / 80 * 100)
    assert r.brecha_extrema == pytest.approx(30 * (20 / 120) / 80 * 100)
    assert r.ingreso_pc == pytest.approx((30 * 100 + 40 * 150 + 10 * 400) / 80)
    assert r.gini == pytest.approx(dd.weighted_gini([100, 150, 400], [30, 40, 10]))
    # Justo en la línea no es pobre
    assert (
        dd.pobreza.indicadores(_hogares_ind(ingreso_pc=[200.0, 200.0, 200.0])).incidencia[0] == 0
    )


def test_indicadores_por_grupo_y_contexto():
    df = _hogares_ind()
    r = dd.pobreza.indicadores(df, por="zona")
    assert r.zona.tolist() == ["a", "b"] and r.personas.tolist() == [70, 10]
    dos = pd.concat([df, df.assign(anio=2024)])
    with pytest.raises(ValueError, match="'anio' a por"):
        dd.pobreza.indicadores(dos)
    assert len(dd.pobreza.indicadores(dos, por=["anio", "zona"])) == 4
    with pytest.raises(ValueError, match="'empalmado' a por"):
        dd.pobreza.indicadores(pd.concat([df.assign(empalmado=False), df.assign(empalmado=True)]))
    with pytest.raises(ValueError, match="Hogares sin dato"):
        dd.pobreza.indicadores(df.assign(fex=[1.0, np.nan, 1.0]))
    with pytest.raises(ValueError, match="armonizar"):
        dd.pobreza.indicadores(df.drop(columns="ingreso_pc"))


def test_indicadores_con_load(pobreza_root):
    df = dd.pobreza.load(2025, raiz=pobreza_root)
    assert df.grupo_dominio.tolist() == [
        "13 ciudades y áreas metropolitanas",
        "13 ciudades y áreas metropolitanas",
        "Centros poblados y rural disperso",
    ]
    r = dd.pobreza.indicadores(df, por="grupo_dominio")
    assert r.grupo_dominio.dtype == dd.pobreza.CATEGORIAS["grupo_dominio"] and len(r) == 2
    emp = dd.pobreza.load([2019, 2025], raiz=pobreza_root, empalme=True)
    assert emp.empalmado.all()
    assert list(dd.pobreza.indicadores(emp, por="anio").anio) == [2019, 2025]


# --------------------------------------------------------------------------- #
# Series con caché
@pytest.fixture
def cache_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    return tmp_path / "cache"


def test_serie_igual_a_load_e_indicadores(pobreza_root, cache_tmp):
    anios = [2017, 2019, 2021, 2022, 2025]
    for empalme in (False, True):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            serie = dd.pobreza.serie_indicadores(
                anios, por="zona", empalme=empalme, raiz=pobreza_root
            )
            directo = dd.pobreza.indicadores(
                dd.pobreza.load(anios, empalme=empalme, raiz=pobreza_root), por=["anio", "zona"]
            )
        pd.testing.assert_frame_equal(serie, directo)
    filtrada = dd.pobreza.serie_indicadores(
        2025, filtros={"dominio": ["Bogotá"]}, raiz=pobreza_root
    )
    assert filtrada.hogares_muestra.tolist() == [1]


def test_serie_usa_la_cache_y_se_invalida(pobreza_root, cache_tmp, monkeypatch):
    from dane_data.pobreza import loader

    lecturas = []
    leer = loader.read_table
    monkeypatch.setattr(
        loader,
        "read_table",
        lambda ruta, **kw: lecturas.append(Path(ruta).name) or leer(ruta, **kw),
    )
    primera = dd.pobreza.serie_indicadores([2019, 2021], empalme=True, raiz=pobreza_root)
    # 2019 y 2021 no usan las líneas de 2012–2018: no se leen
    assert sorted(set(lecturas)) == [
        "empalme_2012_2020.csv",
        "hogares.csv",
        "hogares_empalmado_2021.csv",
        "hogares_empalmado_dpto_2021.csv",
    ]
    lecturas.clear()
    pd.testing.assert_frame_equal(
        dd.pobreza.serie_indicadores([2019, 2021], empalme=True, raiz=pobreza_root), primera
    )
    assert lecturas == []
    # Sin empalme es otra entrada de la caché
    dd.pobreza.serie_indicadores(2019, raiz=pobreza_root)
    assert lecturas == ["hogares.csv"]
    # Cambia el factor de empalme: se recalcula 2019, que lo usa, y no 2021, que no
    lecturas.clear()
    emp = pobreza_root / "datos" / "empalme" / "empalme_2012_2020.csv"
    emp.write_text(emp.read_text().replace(";0.5", ";0.25"))
    nueva = dd.pobreza.serie_indicadores([2019, 2021], empalme=True, raiz=pobreza_root)
    assert "hogares_empalmado_2021.csv" not in lecturas and "empalme_2012_2020.csv" in lecturas
    assert (
        nueva.personas[0] == primera.personas[0] / 2 and nueva.personas[1] == primera.personas[1]
    )
    assert dd.pobreza.clear_cache() > 0 and dd.pobreza.clear_cache() == 0


def test_serie_avisa_una_vez_aun_desde_la_cache(pobreza_root, cache_tmp):
    dd.pobreza.serie_indicadores(2018, raiz=pobreza_root)
    dd.pobreza.serie_indicadores(2019, raiz=pobreza_root)
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        dd.pobreza.serie_indicadores([2018, 2019], raiz=pobreza_root)
    assert len(avisos) == 1 and "empalme=True" in str(avisos[0].message)
    with pytest.raises(FileNotFoundError, match="download"):
        dd.pobreza.serie_indicadores(2030, raiz=pobreza_root)


# --------------------------------------------------------------------------- #
# Unión con la GEIH
def _personas_geih(**kw):
    # Hogar 1 (Bogotá, 2 personas), hogar 2 (Medellín, 1 persona) y una persona de San Andrés, que
    # la pobreza no mide
    base = {
        "anio": 2025,
        "mes": [1, 1, 1, 1],
        "DIRECTORIO": [1, 1, 2, 9],
        "SECUENCIA_P": [1, 1, 1, 1],
        "ORDEN": [1, 2, 1, 1],
        "sexo": ["Mujer", "Hombre", "Mujer", "Mujer"],
        "fex": [5.0, 5.0, 5.0, 5.0],
        "departamento": ["Bogotá D.C.", "Bogotá D.C.", "Antioquia", "San Andrés"],
    }
    df = pd.DataFrame({**base, **kw})
    df.attrs["meses_omitidos"] = []
    return df


def test_unir_geih(pobreza_root):
    per = dd.pobreza.unir_geih(_personas_geih(), raiz=pobreza_root)
    assert per.pobre.tolist()[:3] == [True, True, False] and pd.isna(per.pobre.iloc[3])
    # El de la GEIH no cambia
    assert per.fex_pobreza.tolist()[:3] == [10.0, 10.0, 20.0] and per.fex.tolist() == [5.0] * 4
    assert per.dominio.tolist()[:3] == ["Bogotá", "Bogotá", "Medellín"]
    cob = per.attrs["union_pobreza"]
    assert cob["personas"] == 1.0 and cob["departamentos_no_medidos"] == ["San Andrés"]
    assert per.attrs["meses_omitidos"] == []  # se conservan los de la GEIH
    # Con los hogares ya cargados, y solo algunas variables
    hog = dd.pobreza.load(2025, raiz=pobreza_root)
    solo = dd.pobreza.unir_geih(_personas_geih(), hogares=hog, variables=["ingreso_pc"])
    assert list(solo.columns[-2:]) == ["ingreso_pc", "fex_pobreza"]


def test_unir_geih_avisa_y_falla(pobreza_root):
    with pytest.warns(UserWarning, match="Solo 66.7%"):
        # El hogar 7 no está
        dd.pobreza.unir_geih(_personas_geih(DIRECTORIO=[1, 1, 7, 9]), raiz=pobreza_root)
    with pytest.raises(ValueError, match="Ninguna persona"):
        dd.pobreza.unir_geih(_personas_geih(mes=[5, 5, 5, 5]), raiz=pobreza_root)
    with pytest.raises(ValueError, match="ya tiene"):
        dd.pobreza.unir_geih(_personas_geih(pobre=True), raiz=pobreza_root)
    with pytest.raises(ValueError, match="agregue 'DIRECTORIO'"):
        dd.pobreza.unir_geih(_personas_geih().drop(columns="DIRECTORIO"), raiz=pobreza_root)
    hog = dd.pobreza.load(2025, raiz=pobreza_root)
    with pytest.raises(ValueError, match="repiten llave"):
        dd.pobreza.unir_geih(_personas_geih(), hogares=pd.concat([hog, hog]))


# --------------------------------------------------------------------------- #
# Línea de comandos
def test_cli_descargar_pobreza(monkeypatch):
    llamada = {}
    monkeypatch.setattr(dd.pobreza, "download", lambda **kw: llamada.update(kw) or [])
    monkeypatch.setattr(dd.eevv, "download", lambda **kw: pytest.fail("pobreza no debe ir a EEVV"))
    assert (
        cli.main(
            [
                "descargar",
                "pobreza",
                "--anios",
                "2024",
                "2025",
                "--empalme",
                "--archivos",
                "hogares",
            ]
        )
        == 0
    )
    assert llamada == {
        "years": [2024, 2025],
        "archivos": ["hogares"],
        "empalme": True,
        "borrar_zips": False,
        "forzar": False,
    }
    assert (
        cli.main(["descargar", "pobreza"]) == 0
        and llamada["years"] is None
        and llamada["archivos"] is None
    )
    monkeypatch.setattr(
        dd.pobreza, "download", lambda **kw: ["hogares 2025: no se pudo descargar"]
    )
    assert cli.main(["descargar", "pobreza", "--anios", "2025"]) == 1


@pytest.mark.parametrize(
    "argumentos",
    [
        ["descargar", "pobreza", "--tipos", "fetales"],
        ["descargar", "pobreza", "--modulos", "ocupados"],
        ["descargar", "eevv", "--archivos", "hogares"],
        ["descargar", "geih", "--archivos", "personas"],
    ],
)
def test_cli_pobreza_opciones_de_otra_encuesta(argumentos, capsys):
    assert cli.main(argumentos) == 2
    assert "no aplica" in capsys.readouterr().err


def test_cli_estado_pobreza(pobreza_root, tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(dd.config._session, "pobreza", pobreza_root)
    assert cli.main(["estado"]) == 0
    assert (
        "Pobreza monetaria: 9 años (2012–2025); archivos del empalme 2012–2021: sí"
        in capsys.readouterr().out
    )
    monkeypatch.setitem(dd.config._session, "pobreza", tmp_path / "nada")
    assert cli.main(["estado"]) == 0
    assert "Pobreza monetaria: sin datos" in capsys.readouterr().out


# --------------------------------------------------------------------------- #
# Cifras departamentales
def test_indicadores_departamentales(pobreza_root):
    df = dd.pobreza.load(2025, raiz=pobreza_root)
    with pytest.warns(UserWarning, match="departamental=True"):
        nacional = dd.pobreza.indicadores(df, por="departamento")
    dpto = dd.pobreza.indicadores(df, por="departamento", departamental=True)
    # fex_dpto = 1,1 × fex en los datos sintéticos
    assert np.allclose(dpto.personas, nacional.personas * 1.1) and np.allclose(
        dpto.hogares, nacional.hogares * 1.1
    )


def test_departamental_con_empalme(pobreza_root):
    emp = dd.pobreza.load([2019, 2021, 2022], raiz=pobreza_root, empalme=True)
    e = emp.set_index(["anio", "DIRECTORIO"])
    # 2021: ingreso y factor del archivo departamental, distintos de los nacionales
    assert (e.loc[2021, "fex_dpto"] == 7).all() and (e.loc[2021, "fex"] == 40).all()
    assert np.allclose(e.loc[2021, "ingreso_pc_dpto"], e.loc[2021, "ingreso_pc"] / 2 * 3)
    assert e.loc[2019, "fex_dpto"].isna().all() and e.loc[2022, "fex_dpto"].notna().all()
    with pytest.raises(ValueError, match=r"\[2019\].*antes de 2021"):
        dd.pobreza.indicadores(emp, por=["anio", "departamento"], departamental=True)
    r = dd.pobreza.indicadores(emp[emp.anio == 2021], por="departamento", departamental=True)
    # Todos pobres con la línea nacional? el ingreso departamental es 1,5 × el nacional empalmado
    nac = dd.pobreza.indicadores(emp[emp.anio == 2021], por="anio")
    assert r.personas.sum() == pytest.approx(7 * (4 + 2 + 3)) and nac.personas[0] == 40 * 9
    # Sin el archivo departamental, 2021 queda sin factor departamental (el nacional funciona
    # igual)
    (pobreza_root / "datos" / "empalme" / "hogares_empalmado_dpto_2021.csv").unlink()
    sin = dd.pobreza.load(2021, raiz=pobreza_root, empalme=True)
    assert sin.fex_dpto.isna().all() and (sin.ingreso_pc_dpto == sin.ingreso_pc).all()


# --------------------------------------------------------------------------- #
# Con los datos reales: contra los anexos del DANE (tests/datos/dane_pobreza_publicado.csv)
REAL = Path(os.environ.get("DANE_DATA_TEST_POBREZA", dd.get_path("pobreza")))
hay_datos_reales = pytest.mark.skipif(
    not dd.pobreza.find_files(raiz=REAL), reason="sin datos reales de pobreza"
)
PUBLICADO = Path(__file__).parent / "datos" / "dane_pobreza_publicado.csv"
# Las 7 ciudades con área metropolitana: el dominio es el área metropolitana
_AM = {"Barranquilla", "Bucaramanga", "Cali", "Cúcuta", "Manizales", "Medellín", "Pereira"}
_ETIQUETA_DOMINIO = {d: f"{d} A.M." if d in _AM else d for d in dd.pobreza.DOMINIOS.values()}
_GRANDES = {
    "13 ciudades y áreas metropolitanas": "13 ciudades y A.M.",
    "Otras cabeceras": "Otras cabeceras",
    "Centros poblados y rural disperso": "Centros poblados y rural disperso",
}
# Lo publicado tiene un decimal (porcentajes), tres o cinco (Gini) o es entero (pesos) o en miles
# (personas)
_TOLERANCIA = {"%": 0.08, "coeficiente": 0.0006, "pesos": 2.0, "personas": 1000.0}
# Diferencias conocidas con el anexo (ver docs/guia/diferencias.md): ninguna por ahora
_CONOCIDAS: set = set()


def _calculado(anios, root):
    """Lo mismo que publica el DANE, en el formato del CSV: (anio, nivel, dominio, indicador) ->
    valor.
    """

    def serie(por=None, **kw):
        return dd.pobreza.serie_indicadores(anios, por=por, empalme=True, raiz=root, **kw)

    partes = [
        serie().assign(dominio="Nacional", nivel="nacional"),
        serie("zona").assign(
            dominio=lambda d: d.zona.map(
                {
                    "Urbano (cabecera)": "Cabeceras",
                    "Rural (centros poblados y disperso)": "Centros poblados y rural disperso",
                }
            ),
            nivel="nacional",
        ),
        serie("grupo_dominio").assign(
            dominio=lambda d: d.grupo_dominio.map(_GRANDES), nivel="nacional"
        ),
        serie("dominio").assign(
            dominio=lambda d: d.dominio.map(_ETIQUETA_DOMINIO), nivel="nacional"
        ),
    ]
    desde_2021 = [a for a in anios if a >= 2021]
    if desde_2021:
        dpto = dd.pobreza.serie_indicadores(
            desde_2021, por="departamento", empalme=True, raiz=root, departamental=True
        )
        partes.append(dpto.assign(dominio=dpto.departamento.astype(str), nivel="departamental"))
    largo = pd.concat(partes, ignore_index=True).melt(
        id_vars=["anio", "nivel", "dominio"],
        value_vars=list(_TOLERANCIA_POR_INDICADOR),
        var_name="indicador",
    )
    largo = largo.dropna(subset=["dominio"])
    return largo.drop_duplicates(["anio", "nivel", "dominio", "indicador"]).set_index(
        ["anio", "nivel", "dominio", "indicador"]
    )["value"]


_TOLERANCIA_POR_INDICADOR = {
    **dict.fromkeys(
        [
            "incidencia",
            "incidencia_extrema",
            "brecha",
            "brecha_extrema",
            "severidad",
            "severidad_extrema",
        ],
        "%",
    ),
    "gini": "coeficiente",
    "ingreso_pc": "pesos",
    "linea_pobreza": "pesos",
    "linea_pobreza_extrema": "pesos",
    "personas": "personas",
    "pobres": "personas",
    "pobres_extremos": "personas",
}


@hay_datos_reales
def test_real_coincide_con_lo_publicado():
    """Toda la serie empalmada 2012–2025 contra los anexos nacional y departamental del DANE."""
    publicado = pd.read_csv(PUBLICADO)
    anios = sorted(set(dd.pobreza.find_files(raiz=REAL)) & set(publicado.anio))
    hay_empalme = all(
        (REAL / "datos" / "empalme" / f"{n}.csv").exists()
        or (REAL / "datos" / "empalme" / f"{n}.dta").exists()
        for n in ("empalme_2012_2020", "lineas_2012_2018", "hogares_empalmado_2021")
    )
    if not hay_empalme:
        anios = [a for a in anios if a >= 2022]
    calculado = _calculado(anios, REAL)
    # Un NaN nunca supera la tolerancia: compararlo daría una coincidencia que no se verificó
    publicado = publicado[publicado.anio.isin(anios) & publicado.valor.notna()].set_index(
        ["anio", "nivel", "dominio", "indicador"]
    )
    comparables = publicado.index.intersection(calculado.index)
    # No se comparan las capitales sin área metropolitana de 2022 en adelante ni el total del anexo
    # departamental
    assert len(comparables) > 0.8 * len(publicado)
    problemas = []
    for clave in comparables:
        fila = publicado.loc[clave]
        if (
            not abs(calculado[clave] - fila.valor) <= _TOLERANCIA[fila.unidad]
            and clave not in _CONOCIDAS
        ):  # NaN falla
            problemas.append(f"{clave}: calculado {calculado[clave]:.4f}, publicado {fila.valor}")
    assert not problemas, (
        f"{len(problemas)} de {len(comparables)} cifras no coinciden:\n"
        + "\n".join(problemas[:40])
    )
