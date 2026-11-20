"""Pobreza monetaria y desigualdad: carpetas, descarga, carga, indicadores y unión con la GEIH."""

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dane_data as dd


def test_carpeta_pobreza(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_POBREZA", raising=False)
    assert dd.get_path("pobreza") == dd.config.DEFAULT_HOME / "pobreza"
    dd.set_paths(pobreza=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["pobreza"] == str(tmp_path / "x")
    assert dd.show_paths()["pobreza"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("pobreza") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_POBREZA", str(tmp_path / "env"))
    assert dd.get_path("pobreza") == tmp_path / "env"


# ---------------------------------------------------------------------------------------------------- #
# Carga y armonización, con las rarezas de cada época del DANE

# Tres hogares por año: (DIRECTORIO, SECUENCIA_P, MES, CLASE, DOMINIO, DPTO, NPER, NPERSUG, INGPCUG, LI, LP, FEX_C)
_HOGARES = [(1, 1, 1, 1, "BOGOTA", 11, 4, 3, 150.0, 100.0, 200.0, 10.0),
            (2, 1, 1, 1, "MEDELLIN", 5, 2, 2, 250.0, 100.0, 200.0, 20.0),
            (3, 1, 2, 2, "RURAL", 25, 3, 3, 80.0, 90.0, 150.0, 30.0)]


def _escribir(ruta, df, sep=";", decimal=","):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, sep=sep, decimal=decimal, index=False)


def _hogares_df(anio):
    df = pd.DataFrame(_HOGARES, columns=["Directorio", "Secuencia_p", "Mes", "Clase", "Dominio", "Dpto", "Nper",
                                         "Npersug", "Ingpcug", "Li", "Lp", "Fex_c"])
    df["Ingtotug"] = df.Ingpcug * df.Npersug
    df["Ingtotugarr"] = df.Ingtotug
    df["Pobre"] = (df.Ingpcug < df.Lp).astype(int)
    df["Indigente"] = (df.Ingpcug < df.Li).astype(int)
    df["Fex_dpto"] = df.Fex_c * 1.1
    if anio <= 2014:
        df = df.rename(columns={"Fex_dpto": "Fex_dpto_c"})
    if anio == 2014:  # número de 1 a 24 en vez del código DANE
        df["Dpto"] = df.Dpto.map({11: 23, 5: 21, 25: 24})
    if anio == 2017:  # dominio con tildes, en tipo título
        df["Dominio"] = df.Dominio.map({"BOGOTA": "Bogotá", "MEDELLIN": "Medellín", "RURAL": "Rural"})
    if 2018 <= anio <= 2020:
        df = df.rename(columns={"Dpto": "Depto"})
    if anio == 2022:  # índice basura y DIRECTORIO decimal
        df.insert(0, "Unnamed: 0", range(len(df)))
        df["Directorio"] = df.Directorio.astype(float)
    if anio >= 2023:
        df = df.rename(columns={"Ingtotugarr": "ingtotarr"})
        df.columns = df.columns.str.lower()
    if anio == 2025:  # el nombre del departamento
        df["dpto"] = df.dpto.map({11: "Bogotá D.C.", 5: "Antioquia", 25: "Cundinamarca"})
    return df


@pytest.fixture
def pobreza_root(tmp_path):
    root = tmp_path / "pobreza"
    for anio in (2012, 2014, 2017, 2018, 2019, 2021, 2022, 2023, 2025):
        df = _hogares_df(anio)
        if anio <= 2016:
            _escribir(root / "datos" / str(anio) / "hogares.txt", df, sep="\t", decimal=".")
        else:
            _escribir(root / "datos" / str(anio) / "hogares.csv", df)
    emp = root / "datos" / "empalme"
    fex_g = pd.DataFrame([(a, h[2], h[0], h[1], 0.5) for a in range(2012, 2021) for h in _HOGARES],
                         columns=["año", "mes", "directorio", "secuencia_p", "FEX_G"])
    _escribir(emp / "empalme_2012_2020.csv", fex_g, decimal=".")
    lineas = pd.DataFrame([(a, 1, m, d, 60.0, 260.0) for a in range(2012, 2019) for m in (1, 2)
                           for d in ("BOGOTA", "MEDELLIN", "RURAL")], columns=["AÑO", "SEMESTRE", "MES", "DOMINIO", "LI", "LP"])
    _escribir(emp / "lineas_2012_2018.csv", lineas)
    h21 = pd.DataFrame([(h[2], h[0], h[1], h[8], 1.0, 40.0, h[8] * 2) for h in _HOGARES],
                       columns=["MES", "DIRECTORIO", "SECUENCIA_P", "INGPCUG", "FAC_EMP", "FEX_C", "INGPCUG_EMP"])
    _escribir(emp / "hogares_empalmado_2021.csv", h21)
    return root


def test_armoniza_todas_las_epocas(pobreza_root):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        df = dd.pobreza.load(root=pobreza_root)
    assert sorted(df.anio.unique()) == [2012, 2014, 2017, 2018, 2019, 2021, 2022, 2023, 2025]
    assert (df.groupby("anio").size() == 3).all()
    for c in ("dominio", "departamento", "zona", "ingreso_pc", "linea_pobreza", "fex", "fex_dpto"):
        assert df[c].notna().all(), c
    assert set(df.dominio) == {"Bogotá", "Medellín", "Rural"}
    assert set(df.departamento) == {"Bogotá D.C.", "Antioquia", "Cundinamarca"}
    # 2014 (número de 1 a 24) y 2025 (nombre) bien traducidos
    assert (df.groupby("DIRECTORIO", observed=True).departamento.nunique() == 1).all()
    assert set(df.loc[df.DIRECTORIO == 3, "departamento"]) == {"Cundinamarca"}
    assert df.DIRECTORIO.dtype == "int64" and "UNNAMED: 0" not in df.columns
    assert df.pobre.tolist()[:3] == [True, False, True] and df.pobre_extremo.tolist()[:3] == [False, False, True]
    assert set(df.zona) == {"Urbano (cabecera)", "Rural (centros poblados y disperso)"}
    assert df.groupby("anio").metodologia.first().to_dict()[2018] == "mesep"
    assert df.groupby("anio").metodologia.first().to_dict()[2019] == "actualizacion"
    assert not df.empalmado.any()
    assert df.loc[df.anio == 2023, "ingreso_ug_arriendo"].notna().all()  # INGTOTARR


def test_columnas(pobreza_root):
    df = dd.pobreza.load(2018, root=pobreza_root)
    assert list(df.columns) == ["DIRECTORIO", "SECUENCIA_P", *dd.pobreza.ETIQUETAS]
    todo = dd.pobreza.load(2018, root=pobreza_root, columns="all")
    assert {"POBRE", "INDIGENTE", "INGPCUG"} <= set(todo.columns)
    assert "POBRE" in dd.pobreza.load(2018, root=pobreza_root, columns="POBRE").columns
    crudo = dd.pobreza.load(2018, root=pobreza_root, harmonize_vars=False)
    assert "ingreso_pc" not in crudo and "INGPCUG" in crudo and (crudo.anio == 2018).all()


def test_avisa_si_mezcla_metodologias_o_marcos(pobreza_root):
    with pytest.warns(UserWarning, match="MESEP"):
        dd.pobreza.load([2018, 2019], root=pobreza_root)
    with pytest.warns(UserWarning, match="marco"):
        dd.pobreza.load([2021, 2022], root=pobreza_root)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dd.pobreza.load([2022, 2023], root=pobreza_root)
        dd.pobreza.load([2012, 2025], root=pobreza_root, empalme=True)


def test_empalme(pobreza_root):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        crudo = dd.pobreza.load([2017, 2019, 2021, 2022], root=pobreza_root)
    emp = dd.pobreza.load([2017, 2019, 2021, 2022], root=pobreza_root, empalme=True)
    c, e = (d.set_index(["anio", "DIRECTORIO"]) for d in (crudo, emp))
    # 2012–2020: fex × FEX_G
    assert np.allclose(e.loc[2017, "fex"], c.loc[2017, "fex"] * 0.5)
    assert np.allclose(e.loc[2019, "fex"], c.loc[2019, "fex"] * 0.5)
    # 2012–2018: líneas actualizadas (2017 trae el dominio con tildes) y pobreza recalculada
    assert (e.loc[2017, "linea_pobreza"] == 260).all() and e.loc[2017, "pobre"].all()
    assert (e.loc[2019, "linea_pobreza"] == c.loc[2019, "linea_pobreza"]).all()
    # 2021: ingreso y factor del archivo empalmado
    assert np.allclose(e.loc[2021, "ingreso_pc"], c.loc[2021, "ingreso_pc"] * 2) and (e.loc[2021, "fex"] == 40).all()
    assert e.loc[2021, "pobre"].tolist() == [False, False, False]
    # 2022 en adelante no cambia
    pd.testing.assert_frame_equal(e.loc[2022].drop(columns="empalmado"), c.loc[2022].drop(columns="empalmado"))
    assert emp.loc[emp.anio <= 2021, "empalmado"].all() and (emp.metodologia == "actualizacion").all()
    assert emp.loc[emp.anio <= 2021, "fex_dpto"].isna().all()  # sin empalme departamental validado


def test_empalme_exige_todos_los_hogares_y_los_archivos(pobreza_root):
    emp = pobreza_root / "datos" / "empalme" / "empalme_2012_2020.csv"
    fex_g = pd.read_csv(emp, sep=";")
    fex_g.iloc[1:].to_csv(emp, sep=";", index=False)  # falta un hogar de 2012
    with pytest.raises(ValueError, match="1 hogares de 2012"):
        dd.pobreza.load(2012, root=pobreza_root, empalme=True)
    pd.concat([fex_g, fex_g.iloc[[0]]]).to_csv(emp, sep=";", index=False)  # uno repetido
    with pytest.raises(ValueError, match="repetidas"):
        dd.pobreza.load(2012, root=pobreza_root, empalme=True)
    emp.unlink()
    with pytest.raises(FileNotFoundError, match="empalme=True"):
        dd.pobreza.load(2012, root=pobreza_root, empalme=True)
    dd.pobreza.load(2022, root=pobreza_root, empalme=True)  # desde 2022 no hace falta


def test_falla_con_dominio_desconocido_o_sin_linea(pobreza_root):
    ruta = pobreza_root / "datos" / "2019" / "hogares.csv"
    df = pd.read_csv(ruta, sep=";")
    df.loc[0, "Dominio"] = "MARTE"
    df.to_csv(ruta, sep=";", index=False)
    with pytest.raises(ValueError, match="MARTE"):
        dd.pobreza.load(2019, root=pobreza_root)
    df.loc[0, "Dominio"] = "BOGOTA"
    df["Lp"] = df["Lp"].astype(object)
    df.loc[0, "Lp"] = ""
    df.to_csv(ruta, sep=";", index=False)
    with pytest.raises(ValueError, match="linea_pobreza"):
        dd.pobreza.load(2019, root=pobreza_root)


def test_find_files_y_available(pobreza_root):
    (pobreza_root / "datos" / "notas").mkdir()
    assert sorted(dd.pobreza.find_files(root=pobreza_root)) == [2012, 2014, 2017, 2018, 2019, 2021, 2022, 2023, 2025]
    assert list(dd.pobreza.find_files([2014, 2030], root=pobreza_root)) == [2014]
    av = dd.pobreza.available(root=pobreza_root)
    assert av.anio.notna().sum() == 9 and not av.personas.any()
    assert set(av.loc[av.anio.isna(), "archivo"]) == {"empalme_2012_2020", "lineas_2012_2018", "hogares_empalmado_2021"}
    with pytest.raises(FileNotFoundError, match="download"):
        dd.pobreza.load(2030, root=pobreza_root)


# ---------------------------------------------------------------------------------------------------- #
# Gini e indicadores
def test_weighted_gini():
    assert dd.weighted_gini([3, 1, 2], [2, 1, 1]) == pytest.approx(dd.weighted_gini([1, 2, 3, 3], [1, 1, 1, 1]))
    assert dd.weighted_gini([1, np.nan, 3], [1, 1, 1]) == pytest.approx(dd.weighted_gini([1, 3], [1, 1]))
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
    base = {"anio": 2025, "ingreso_pc": [100.0, 150.0, 400.0], "linea_pobreza": 200.0, "linea_pobreza_extrema": 120.0,
            "fex": [10.0, 20.0, 10.0], "personas": [3, 2, 1], "zona": ["a", "a", "b"]}
    df = pd.DataFrame({**base, **kw})
    return df.assign(pobre=df.ingreso_pc < df.linea_pobreza, pobre_extremo=df.ingreso_pc < df.linea_pobreza_extrema)


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
    assert dd.pobreza.indicadores(_hogares_ind(ingreso_pc=[200.0, 200.0, 200.0])).incidencia[0] == 0


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
    with pytest.raises(ValueError, match="harmonize_vars"):
        dd.pobreza.indicadores(df.drop(columns="pobre"))


def test_indicadores_con_load(pobreza_root):
    df = dd.pobreza.load(2025, root=pobreza_root)
    assert df.grupo_dominio.tolist() == ["13 ciudades y áreas metropolitanas", "13 ciudades y áreas metropolitanas",
                                         "Centros poblados y rural disperso"]
    r = dd.pobreza.indicadores(df, por="grupo_dominio")
    assert r.grupo_dominio.dtype == dd.pobreza.CATEGORIAS["grupo_dominio"] and len(r) == 2
    emp = dd.pobreza.load([2019, 2025], root=pobreza_root, empalme=True)
    assert emp.empalmado.all()
    assert list(dd.pobreza.indicadores(emp, por="anio").anio) == [2019, 2025]


# ---------------------------------------------------------------------------------------------------- #
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
            serie = dd.pobreza.serie_indicadores(anios, por="zona", empalme=empalme, root=pobreza_root)
            directo = dd.pobreza.indicadores(dd.pobreza.load(anios, empalme=empalme, root=pobreza_root), por=["anio", "zona"])
        pd.testing.assert_frame_equal(serie, directo)
    filtrada = dd.pobreza.serie_indicadores(2025, filtros={"dominio": ["Bogotá"]}, root=pobreza_root)
    assert filtrada.hogares_muestra.tolist() == [1]


def test_serie_usa_la_cache_y_se_invalida(pobreza_root, cache_tmp, monkeypatch):
    from dane_data.pobreza import loader
    lecturas = []
    leer = loader.read_table
    monkeypatch.setattr(loader, "read_table", lambda ruta, **kw: lecturas.append(Path(ruta).name) or leer(ruta, **kw))
    primera = dd.pobreza.serie_indicadores([2019, 2021], empalme=True, root=pobreza_root)
    # 2019 y 2021 no usan las líneas de 2012–2018: no se leen
    assert sorted(set(lecturas)) == ["empalme_2012_2020.csv", "hogares.csv", "hogares_empalmado_2021.csv"]
    lecturas.clear()
    pd.testing.assert_frame_equal(dd.pobreza.serie_indicadores([2019, 2021], empalme=True, root=pobreza_root), primera)
    assert lecturas == []
    # Sin empalme es otra entrada de la caché
    dd.pobreza.serie_indicadores(2019, root=pobreza_root)
    assert lecturas == ["hogares.csv"]
    # Cambia el factor de empalme: se recalcula 2019, que lo usa, y no 2021, que no
    lecturas.clear()
    emp = pobreza_root / "datos" / "empalme" / "empalme_2012_2020.csv"
    emp.write_text(emp.read_text().replace(";0.5", ";0.25"))
    nueva = dd.pobreza.serie_indicadores([2019, 2021], empalme=True, root=pobreza_root)
    assert "hogares_empalmado_2021.csv" not in lecturas and "empalme_2012_2020.csv" in lecturas
    assert nueva.personas[0] == primera.personas[0] / 2 and nueva.personas[1] == primera.personas[1]
    assert dd.pobreza.clear_cache() > 0 and dd.pobreza.clear_cache() == 0


def test_serie_avisa_una_vez_aun_desde_la_cache(pobreza_root, cache_tmp):
    dd.pobreza.serie_indicadores(2018, root=pobreza_root)
    dd.pobreza.serie_indicadores(2019, root=pobreza_root)
    with warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        dd.pobreza.serie_indicadores([2018, 2019], root=pobreza_root)
    assert len(avisos) == 1 and "empalme=True" in str(avisos[0].message)
    with pytest.raises(FileNotFoundError, match="download"):
        dd.pobreza.serie_indicadores(2030, root=pobreza_root)


# ---------------------------------------------------------------------------------------------------- #
# Unión con la GEIH
def _personas_geih(**kw):
    # Hogar 1 (Bogotá, 2 personas), hogar 2 (Medellín, 1 persona) y una persona de San Andrés, que la pobreza no mide
    base = {"anio": 2025, "mes": [1, 1, 1, 1], "DIRECTORIO": [1, 1, 2, 9], "SECUENCIA_P": [1, 1, 1, 1],
            "ORDEN": [1, 2, 1, 1], "sexo": ["Mujer", "Hombre", "Mujer", "Mujer"], "fex": [5.0, 5.0, 5.0, 5.0],
            "departamento": ["Bogotá D.C.", "Bogotá D.C.", "Antioquia", "San Andrés"]}
    df = pd.DataFrame({**base, **kw})
    df.attrs["meses_omitidos"] = []
    return df


def test_unir_geih(pobreza_root):
    per = dd.pobreza.unir_geih(_personas_geih(), root=pobreza_root)
    assert per.pobre.tolist()[:3] == [True, True, False] and pd.isna(per.pobre.iloc[3])
    assert per.fex_pobreza.tolist()[:3] == [10.0, 10.0, 20.0] and per.fex.tolist() == [5.0] * 4  # el de la GEIH no cambia
    assert per.dominio.tolist()[:3] == ["Bogotá", "Bogotá", "Medellín"]
    cob = per.attrs["union_pobreza"]
    assert cob["personas"] == 1.0 and cob["departamentos_no_medidos"] == ["San Andrés"]
    assert per.attrs["meses_omitidos"] == []  # se conservan los de la GEIH
    # Con los hogares ya cargados, y solo algunas variables
    hog = dd.pobreza.load(2025, root=pobreza_root)
    solo = dd.pobreza.unir_geih(_personas_geih(), hogares=hog, variables=["ingreso_pc"])
    assert list(solo.columns[-2:]) == ["ingreso_pc", "fex_pobreza"]


def test_unir_geih_avisa_y_falla(pobreza_root):
    with pytest.warns(UserWarning, match="Solo 66.7%"):
        dd.pobreza.unir_geih(_personas_geih(DIRECTORIO=[1, 1, 7, 9]), root=pobreza_root)  # el hogar 7 no está
    with pytest.raises(ValueError, match="Ninguna persona"):
        dd.pobreza.unir_geih(_personas_geih(mes=[5, 5, 5, 5]), root=pobreza_root)
    with pytest.raises(ValueError, match="ya tiene"):
        dd.pobreza.unir_geih(_personas_geih(pobre=True), root=pobreza_root)
    with pytest.raises(ValueError, match="agregue 'DIRECTORIO'"):
        dd.pobreza.unir_geih(_personas_geih().drop(columns="DIRECTORIO"), root=pobreza_root)
    hog = dd.pobreza.load(2025, root=pobreza_root)
    with pytest.raises(ValueError, match="repiten llave"):
        dd.pobreza.unir_geih(_personas_geih(), hogares=pd.concat([hog, hog]))
