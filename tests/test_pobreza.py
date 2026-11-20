"""Pobreza monetaria y desigualdad: carpetas, descarga, carga, indicadores y unión con la GEIH."""

import json
import warnings

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
