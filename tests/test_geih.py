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
    assert list(zip(av.anio, av.mes)) == [(2011, 3), (2016, 1), (2021, 9), (2025, 1), (2025, 2)]
    assert av.set_index(["anio", "mes"]).loc[(2025, 2), "faltantes"] == "desocupados"
    assert av.completo.tolist() == [True, True, True, True, False]


def test_csv_danado_usa_formato_alterno(geih_root):
    """2011: el CSV del ANDA perdió el punto decimal del factor; se usa la carpeta del TXT."""
    av = dd.geih.available(root=geih_root)
    assert av.set_index(["anio", "mes"]).loc[(2011, 3), "carpeta"] == "Marzo_txt"
    df = dd.geih.load(2011, root=geih_root, cache=False)
    assert df["fex"].tolist() == pytest.approx([84.9491032387525, 84.9491032387525, 1078.45157267357])
    assert df["condicion"].tolist() == ["Ocupado", "Desocupado", "Ocupado"]
    assert "FEX_C" not in df.columns  # el factor de "Otras actividades" no reemplaza al de características


def test_mes_completo_en_dos_carpetas_no_se_duplica(geih_root, caplog):
    """Una copia del mes (p. ej. descomprimida dos veces) no suma sus filas dos veces."""
    import shutil

    antes = len(dd.geih.load(2016, root=geih_root, cache=False))
    shutil.copytree(geih_root / "datos_csv" / "2016" / "Enero", geih_root / "datos_csv" / "2016" / "Enero_copia")
    with caplog.at_level("WARNING", logger="dane_data.geih"):
        assert len(dd.geih.find_months(2016, root=geih_root)) == 1
        assert len(dd.geih.load(2016, root=geih_root, cache=False)) == antes
    assert "varias carpetas" in caplog.text


def test_carpeta_del_mes_sin_archivos_reconocidos(geih_root):
    """Junto al mes, otra carpeta con el nombre del mes pero sin módulos (un diccionario): no falla."""
    otra = geih_root / "datos_csv" / "2016" / "Enero_documentacion"
    otra.mkdir()
    (otra / "diccionario.csv").write_text("variable;descripcion\nP6020;Sexo\n", encoding="utf-8")
    meses = dd.geih.find_months(2016, root=geih_root)
    assert len(meses) == 1 and meses[0].carpeta.name == "Enero"


def test_archivo_reemplazado_se_vuelve_a_revisar(geih_root):
    """Con la app abierta, un CSV dañado que se reemplaza por uno bueno en la misma ruta deja de omitirse."""
    car = next((geih_root / "datos_csv" / "2016" / "Enero").glob("Cabecera - Car*"))
    bueno = car.read_bytes()
    assert dd.geih.find_months(2016, root=geih_root)[0].completo
    car.write_text(car.read_text(encoding="utf-8").replace(";", " "), encoding="utf-8")  # separado por espacios
    os.utime(car, ns=(car.stat().st_atime_ns, car.stat().st_mtime_ns + 10**9))
    assert not dd.geih.find_months(2016, root=geih_root)[0].completo
    car.write_bytes(bueno)
    os.utime(car, ns=(car.stat().st_atime_ns, car.stat().st_mtime_ns + 2 * 10**9))
    assert dd.geih.find_months(2016, root=geih_root)[0].completo


def test_csv_ilegible_usa_stata(geih_root):
    """Septiembre de 2021: el CSV viene separado por espacios; se usa el Stata del ANDA."""
    df = dd.geih.load(2021, root=geih_root, cache=False)
    assert df["fex"].tolist() == [250.5, 250.5]
    assert df["condicion"].tolist() == ["Ocupado", "Desocupado"]
    assert df["ingreso_laboral"].tolist()[0] == 3000000
    assert df["edad"].tolist() == [101, 38]


def test_stata_110(geih_root):
    """El Stata de septiembre de 2021 es formato 110 (Stata 7), que pandas 2 no lee; se traduce al 111."""
    from dane_data import _io
    p = geih_root / "datos_csv" / "2021" / "Septiembre" / "Cabecera - Características generales (Personas).dta"
    assert p.read_bytes()[0] == 110
    df = pd.read_stata(_io._stata(p), convert_categoricals=False)
    assert df["P6040"].tolist() == [101, 38]
    # Ensanchadas: en un byte, pandas 2 tomaría 101 y 104 por faltantes (lo son desde Stata 8)
    assert df["P6040"].dtype == "int16" and df["P7260"].dtype == "float64"
    assert df["P7260"].isna().tolist() == [True, False] and df["P7260"].iloc[1] == 104
    assert df["CLASE"].dtype == "int8"  # sin valores ambiguos no cambia
    assert _io.columnas(p)[:3] == ["DIRECTORIO", "SECUENCIA_P", "ORDEN"]
    if int(pd.__version__.split(".")[0]) >= 3:  # pandas 3 lee el formato 110 directamente
        pd.testing.assert_frame_equal(pd.read_stata(p, convert_categoricals=False), df, check_dtype=False)


@pytest.mark.parametrize("anio,carpeta,defecto", [(2011, "Marzo_txt", "sin punto decimal"),
                                                    (2021, "Septiembre", "separado por espacios")])
def test_csv_danado_sin_alterno_se_omite(geih_root, caplog, anio, carpeta, defecto):
    import shutil
    shutil.rmtree(geih_root / "datos_csv" / str(anio) / carpeta)
    av = dd.geih.available(root=geih_root).set_index("anio")
    assert not av.loc[anio, "completo"] and defecto in av.loc[anio, "faltantes"]
    with pytest.raises(FileNotFoundError):
        dd.geih.load(anio, root=geih_root, cache=False)
    assert "Vuelva a descargar" in caplog.text


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


def test_empalme_pet_15_anios(tmp_path):
    """El empalme se publica con PET de 15+; octubre de 2012 la trae con la definición anterior."""
    m = tmp_path / "datos_csv" / "2012" / "10. Octubre"
    m.mkdir(parents=True)
    (m / "Características generales (personas).CSV").write_text(
        "DIRECTORIO;SECUENCIA_P;ORDEN;P6040;CLASE;OCI;DSI;PETI;INGLABO;FEX_C\n"
        "1;1;1;40;1;1;;1;900000;100\n1;1;2;12;1;1;;1;200000;100\n1;1;3;13;2;;;1;;100\n", encoding="utf-8")
    empalme = dd.geih.load(2012, empalme=True, root=tmp_path, cache=False)
    assert empalme["condicion"].tolist() == ["Ocupado", "Fuera de la PET", "Fuera de la PET"]
    assert empalme["ingreso_laboral"].notna().tolist() == [True, False, False]
    principal = dd.geih.load(2012, root=tmp_path, cache=False)
    assert principal["condicion"].tolist() == ["Ocupado", "Ocupado", "Inactivo"]


def test_marco_muestral():
    principal = {a: dd.geih.marco_muestral(a) for a in (2007, 2019, 2020, 2021, 2022, 2025)}
    assert principal == {2007: "censo 2005", 2019: "censo 2005", 2020: "CNPV 2018", 2021: "censo 2005",
                         2022: "CNPV 2018", 2025: "CNPV 2018"}
    assert dd.geih.marco_muestral(2015, empalme=True) == "CNPV 2018"


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


def test_un_solo_nombre_sin_lista(geih_root, eam_root):
    """Un solo valor o nombre en vez de una lista no se parte en letras."""
    df = dd.geih.load(2016, root=geih_root, cache=False)
    assert dd.geih.filtrar(df, {"sexo": "Mujer"}).equals(dd.geih.filtrar(df, {"sexo": ["Mujer"]}))
    assert len(dd.geih.filtrar(df, {"sexo": "Mujer"})) > 0
    assert len(dd.geih.filtrar(df, {"anio": 2016})) == len(df)
    uno = dd.geih.load(2016, root=geih_root, cache=False, columns="P6050", modules="caracteristicas",
                       harmonize_vars=False)
    lista = dd.geih.load(2016, root=geih_root, cache=False, columns=["P6050"], modules=["caracteristicas"],
                         harmonize_vars=False)
    assert "P6050" in uno.columns
    pd.testing.assert_frame_equal(uno, lista)
    assert "prodbr2" in dd.eam.load(2016, root=eam_root, columns="prodbr2", harmonize_vars=False).columns
    eam = dd.eam.load(2016, root=eam_root)
    assert "valagri_real" in dd.eam.deflactar(eam, "valagri", pd.Series({2016: 100.0})).columns


def test_exportar_una_sola_variable(geih_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    ruta = tmp_path / "fex.csv"
    dd.geih.exportar(2016, ruta, variables="fex", root=geih_root)
    assert list(pd.read_csv(ruta, encoding="utf-8-sig").columns) == ["anio", "mes", "fex"]
    # Para un Excel con coma decimal (configuración regional de Colombia)
    dd.geih.exportar(2016, ruta, variables="fex", root=geih_root, sep=";", decimal=",")
    assert ruta.read_text(encoding="utf-8-sig").splitlines()[:2] == ["anio;mes;fex", "2016;1;100,5"]


def test_cache_interrumpida_no_deja_parquet_a_medias(geih_root, tmp_path, monkeypatch):
    """Si falla la escritura, no queda ni el parquet (a medias) ni el temporal, y load funciona igual."""
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    original = pd.DataFrame.to_parquet
    temporales = []

    def falla(self, ruta, *a, **k):
        temporales.append(Path(ruta).name)
        Path(ruta).write_bytes(b"PAR1 a medias")
        raise OSError("disco lleno")

    monkeypatch.setattr(pd.DataFrame, "to_parquet", falla)
    esperado = dd.geih.load(2016, root=geih_root, cache=False)
    pd.testing.assert_frame_equal(dd.geih.load(2016, root=geih_root), esperado)
    dd.geih.serie_indicadores(2016, root=geih_root)
    assert len(temporales) >= 2 and all(t.endswith(".tmp") for t in temporales)
    assert not [f for f in (tmp_path / "cache").rglob("*") if f.is_file()]

    monkeypatch.setattr(pd.DataFrame, "to_parquet", original)
    dd.geih.serie_indicadores(2016, root=geih_root)
    dd.geih.serie_indicadores(2016, root=geih_root, filtros={"sexo": ["Mujer"]})
    (tmp_path / "cache" / "geih" / "huerfano.parquet.ab12.tmp").write_bytes(b"x")  # de una versión anterior
    archivos = [f for f in (tmp_path / "cache").rglob("*") if f.is_file()]
    assert len(archivos) == 4                           # 1 mes (load) + 2 años (serie) + el huérfano
    assert dd.geih.clear_cache() == 4
    assert not [f for f in (tmp_path / "cache").rglob("*") if f.is_file()]


def test_cache_corrupta_se_regenera(geih_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    a = dd.geih.load(2016, root=geih_root)
    dd.geih.serie_indicadores(2016, root=geih_root)
    for f in (tmp_path / "cache").rglob("*.parquet"):
        f.write_bytes(b"no es parquet")
    pd.testing.assert_frame_equal(dd.geih.load(2016, root=geih_root), a)
    pd.testing.assert_frame_equal(dd.geih.serie_indicadores(2016, root=geih_root),
                                  dd.geih.indicadores(dd.geih.load(2016, root=geih_root, cache=False)))
    assert all(pd.read_parquet(f) is not None for f in (tmp_path / "cache").rglob("*.parquet"))


def test_cache_temporales_con_nombre_unico(tmp_path, monkeypatch):
    """Dos sesiones de la app (hilos del mismo proceso) no escriben el mismo temporal."""
    from dane_data.geih.loader import _guardar_parquet

    nombres = []
    original = pd.DataFrame.to_parquet
    monkeypatch.setattr(pd.DataFrame, "to_parquet",
                        lambda self, ruta, *a, **k: nombres.append(Path(ruta).name) or original(self, ruta, *a, **k))
    for _ in range(2):
        _guardar_parquet(pd.DataFrame({"x": [1]}), tmp_path / "c" / "a.parquet")
    assert len(set(nombres)) == 2
    assert [f.name for f in (tmp_path / "c").iterdir()] == ["a.parquet"]


@pytest.mark.parametrize("dropna", [True, False])
@pytest.mark.parametrize("anual", [True, False])
@pytest.mark.parametrize("por", dd.geih.POR_PRECALCULADOS)
def test_serie_indicadores_igual_a_indicadores(geih_root, tmp_path, monkeypatch, por, anual, dropna):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    df = dd.geih.load([2016, 2025], root=geih_root, cache=False)
    esperado = dd.geih.indicadores(df, por=por, anual=anual, dropna=dropna)
    serie = dd.geih.serie_indicadores([2016, 2025], por=por, anual=anual, root=geih_root, dropna=dropna)
    pd.testing.assert_frame_equal(serie, esperado)


def test_serie_indicadores_sin_grupo_vacio(geih_root, tmp_path, monkeypatch):
    """
    Por defecto serie_indicadores deja fuera la fila de nivel educativo vacío (en los datos reales, los
    menores fuera de la PET); indicadores la conserva para que los grupos sumen el total.
    """
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    mod = sys.modules["dane_data.geih.agregados"]
    original = mod.load

    def sin_educacion(*a, **k):
        df = original(*a, **k)
        df.loc[df["pet"] == 0, "nivel_educativo"] = None
        return df

    monkeypatch.setattr(mod, "load", sin_educacion)
    df = sin_educacion(2016, root=geih_root, cache=False)
    con_vacio = dd.geih.indicadores(df, por="nivel_educativo")
    assert con_vacio["nivel_educativo"].isna().sum() == 1
    assert con_vacio["n_muestra"].sum() == len(df)                  # los grupos suman el total
    serie = dd.geih.serie_indicadores(2016, por="nivel_educativo", root=geih_root)
    assert serie["nivel_educativo"].notna().all() and len(serie) == len(con_vacio) - 1
    pd.testing.assert_frame_equal(serie, dd.geih.indicadores(df, por="nivel_educativo", dropna=True))
    pd.testing.assert_frame_equal(
        dd.geih.serie_indicadores(2016, por="nivel_educativo", root=geih_root, dropna=False), con_vacio)


def test_serie_indicadores_usa_cache_y_se_invalida(geih_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    a = dd.geih.serie_indicadores(2016, root=geih_root)
    assert len(list((tmp_path / "cache" / "geih" / "indicadores").glob("principal_2016_*.parquet"))) == 1

    mod = sys.modules["dane_data.geih.agregados"]
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


def test_serie_indicadores_con_filtros_y_meses(geih_root, tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    filtros = {"sexo": ["Mujer"], "edad": (20, 60)}
    df = dd.geih.filtrar(dd.geih.load([2016, 2025], months=[1], root=geih_root, cache=False), filtros)
    for por, anual in (("zona", True), (None, False)):
        esperado = dd.geih.indicadores(df, por=por, anual=anual, dropna=True)
        serie = dd.geih.serie_indicadores([2016, 2025], por=por, anual=anual, root=geih_root, filtros=filtros,
                                          meses=[1])
        pd.testing.assert_frame_equal(serie, esperado)


def test_porcentaje_con_grupo_exterior_vacio(geih_root, tmp_path, monkeypatch):
    """Las personas sin posición ocupacional (NaN: no ocupadas) también suman 100 % dentro de su grupo."""
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    df = dd.geih.load(2016, root=geih_root, cache=False)
    assert df["posicion_ocupacional"].isna().any()
    por = ["posicion_ocupacional", "sexo"]
    t = dd.tabla(df, por=por, estadistico="porcentaje")
    assert t["porcentaje"].notna().all()
    assert t.groupby("posicion_ocupacional", dropna=False, observed=True)["porcentaje"].sum().tolist() == \
        pytest.approx([100.0] * t["posicion_ocupacional"].nunique(dropna=False))
    s = dd.geih.serie_tabla(2016, por=por, estadistico="porcentaje", root=geih_root)
    pd.testing.assert_frame_equal(s, t, check_dtype=False, rtol=1e-9)


def test_serie_promedia_sobre_los_meses_cargados(geih_root, tmp_path, monkeypatch):
    """Un mes sin nadie en el grupo filtrado cuenta como 0 en el promedio mensual, no se descarta."""
    import shutil

    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    anio = geih_root / "datos_csv" / "2016"
    shutil.copytree(anio / "Enero", anio / "Febrero")
    for f in (anio / "Febrero").glob("Resto - *.csv"):  # en febrero nadie vive en el resto (rural)
        f.write_text(f.read_text(encoding="utf-8").splitlines()[0] + "\n", encoding="utf-8")
    filtros = {"zona": ["Rural (centros poblados y disperso)"]}

    t = dd.geih.serie_tabla(2016, filtros=filtros, root=geih_root)
    assert t["total"].item() == pytest.approx(300.25 / 2)          # enero 300,25 y febrero 0
    ind = dd.geih.serie_indicadores(2016, filtros=filtros, root=geih_root)
    assert ind["pet"].item() == pytest.approx(300.25 / 2)
    # Filtrar por mes sí cambia los meses del promedio
    t = dd.geih.serie_tabla(2016, filtros={**filtros, "mes": [1]}, root=geih_root)
    assert t["total"].item() == pytest.approx(300.25)
    # Con microdatos, filtrar anota los meses cargados: lo mismo que serie_* (también dos filtrar seguidos)
    micro = dd.geih.load(2016, root=geih_root, cache=False)
    df = dd.geih.filtrar(micro, filtros)
    assert dd.tabla(df)["total"].item() == pytest.approx(300.25 / 2)
    assert dd.geih.indicadores(df)["pet"].item() == pytest.approx(300.25 / 2)
    doble = dd.geih.filtrar(dd.geih.filtrar(micro, {"sexo": ["Mujer"]}), filtros)
    assert dd.tabla(doble)["total"].item() == pytest.approx(300.25 / 2)
    # Elegir meses con df[...] (un trimestre, por ejemplo) sí cuenta solo los que quedan
    rural = micro[micro["zona"] == filtros["zona"][0]]
    assert dd.tabla(rural)["total"].item() == pytest.approx(300.25)
    # También después de filtrar: la anotación no pasa al subconjunto (antes se dividía por 2 meses)
    mujeres = dd.geih.filtrar(micro, {"sexo": ["Mujer"]})
    enero = mujeres[mujeres["mes"] == 1]
    esperado = dd.tabla(micro[(micro["sexo"] == "Mujer") & (micro["mes"] == 1)])["total"].item()
    assert dd.tabla(enero)["total"].item() == pytest.approx(esperado)
    assert dd.geih.indicadores(enero)["pet"].item() == pytest.approx(
        dd.geih.indicadores(micro[(micro["sexo"] == "Mujer") & (micro["mes"] == 1)])["pet"].item())
    assert dd.geih.filtrar(enero, filtros).attrs["meses_por_anio"] == {2016: 1}


def test_serie_cache_distingue_rango_de_lista(geih_root, tmp_path, monkeypatch):
    """``(15, 28)`` es el rango 15–28 y ``[15, 28]`` solo esas dos edades: no comparten caché."""
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    for filtro in ((10, 60), [10, 60]):
        filtros = {"edad": filtro}
        esperado = dd.geih.indicadores(dd.geih.filtrar(dd.geih.load(2016, root=geih_root, cache=False), filtros))
        pd.testing.assert_frame_equal(dd.geih.serie_indicadores(2016, root=geih_root, filtros=filtros), esperado)
        esperado = dd.tabla(dd.geih.filtrar(dd.geih.load(2016, root=geih_root, cache=False), filtros), por="sexo")
        pd.testing.assert_frame_equal(dd.geih.serie_tabla(2016, por="sexo", root=geih_root, filtros=filtros),
                                      esperado, check_dtype=False, rtol=1e-9)


@pytest.mark.parametrize("pedido", [
    dict(por=["anio", "sexo"]),
    dict(por=["sexo", "nivel_educativo"], estadistico="porcentaje"),
    dict(por="zona", estadistico="porcentaje", poblacion="ocupado"),
    dict(por="sexo", variable="ingreso_laboral", estadistico="media"),
    dict(por="zona", variable="edad", estadistico="mediana", filtros={"edad": (10, 60)}),
    dict(por=None, variable="edad", estadistico="mediana", poblacion="pet"),
    dict(por=["anio", "posicion_ocupacional"], estadistico="porcentaje", dropna=True),
    dict(por="departamento", filtros={"sexo": ["Mujer"]}, meses=[1]),
])
def test_serie_tabla_igual_a_tabla(geih_root, tmp_path, monkeypatch, pedido):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    df = dd.geih.load([2016, 2025], months=pedido.get("meses"), root=geih_root, cache=False)
    df = dd.geih.filtrar(df, pedido.get("filtros"), pedido.get("poblacion"))
    if pedido.get("dropna"):
        df = df.dropna(subset=pedido["por"])
    esperado = dd.tabla(df, por=pedido.get("por"), variable=pedido.get("variable"),
                        estadistico=pedido.get("estadistico", "total"))
    serie = dd.geih.serie_tabla([2016, 2025], root=geih_root, **pedido)
    pd.testing.assert_frame_equal(serie, esperado, check_dtype=False, rtol=1e-9)


def test_serie_frecuencias_variable_que_no_existe_algunos_anios(geih_root, tmp_path, monkeypatch):
    """P5000 solo está en 2025: en 2016 queda vacía en vez de fallar."""
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    f = dd.geih.serie_frecuencias([2016, 2025], por="P5000", columns=["P5000"], root=geih_root)
    assert f.loc[f["anio"] == 2016, "P5000"].isna().all()
    assert set(f.loc[f["anio"] == 2025, "P5000"]) == {2, 4}


def test_exportar_mes_a_mes(geih_root, tmp_path):
    ruta = tmp_path / "salida" / "ocupados.csv"
    filas = dd.geih.exportar([2016, 2025], ruta, variables=["fex", "sexo", "ingreso_laboral"], poblacion="ocupado",
                             root=geih_root)
    esperado = dd.geih.filtrar(dd.geih.load([2016, 2025], root=geih_root, cache=False), poblacion="ocupado")
    leido = pd.read_csv(ruta, encoding="utf-8-sig")
    assert filas == len(esperado) == len(leido)
    assert list(leido.columns) == ["anio", "mes", "fex", "sexo", "ingreso_laboral"]
    assert leido["fex"].tolist() == pytest.approx(esperado["fex"].tolist())
    assert leido["sexo"].tolist() == esperado["sexo"].astype(str).tolist()
    assert not list(ruta.parent.glob("*.tmp"))


def test_exportar_sin_variables_escribe_todas_las_armonizadas(geih_root, tmp_path, monkeypatch):
    """Sin ``variables`` no se recorta a las columnas de los filtros."""
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    ruta = tmp_path / "ocupados.csv"
    filas = dd.geih.exportar([2016, 2025], ruta, poblacion="ocupado", filtros={"sexo": ["Mujer"]}, root=geih_root)
    esperado = dd.geih.filtrar(dd.geih.load([2016, 2025], root=geih_root, cache=False), {"sexo": ["Mujer"]},
                               "ocupado")
    leido = pd.read_csv(ruta, encoding="utf-8-sig")
    assert filas == len(esperado) == len(leido)
    assert list(leido.columns) == [c for c in esperado.columns if c == c.lower()]
    assert {"fex", "edad", "condicion"} <= set(leido.columns)


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
PUBLICADO = pd.read_csv(Path(__file__).parent / "datos" / "dane_publicado.csv", comment="#")


def _disponibles_reales(empalme: bool) -> tuple[Path, pd.DataFrame]:
    root = REAL_EMPALME if empalme else REAL
    av = dd.geih.available(empalme=empalme, root=root) if (root / "datos_csv").is_dir() else pd.DataFrame()
    if av.empty:
        pytest.skip(f"sin datos GEIH reales en {root}")
    return root, av


# grupo del CSV -> desagregación de serie_indicadores
GRUPOS_PUBLICADOS = {"total": (None, None), "urbano": ("zona", "Urbano (cabecera)"),
                     "hombres": ("sexo", "Hombre"), "mujeres": ("sexo", "Mujer")}
# Diferencias que vienen de los microdatos del ANDA y no tienen arreglo (ver README): no se comparan.
SIN_COMPARAR = {
    # Putumayo sin características (Mocoa no se encuestó en abril ni mayo); los totales sí coinciden
    ("empalme", "hombres", 2017, 4), ("empalme", "mujeres", 2017, 4),
    ("empalme", "hombres", 2017, 5), ("empalme", "mujeres", 2017, 5),
}


def _serie_grupo(anios, grupo, anual, empalme, root) -> pd.DataFrame:
    por, valor = GRUPOS_PUBLICADOS[grupo]
    s = dd.geih.serie_indicadores(anios, por=por, anual=anual, empalme=empalme, root=root)
    return s if por is None else s[s[por] == valor].drop(columns=por)


@pytest.mark.parametrize("empalme", [False, True], ids=["principal", "empalme"])
def test_real_coincide_con_lo_publicado(empalme):
    """
    TD, TGP, TO y ocupados de cada mes, y las tasas de cada año completo, coinciden con los
    anexos del DANE (tests/datos/dane_publicado.csv): total nacional y, con el marco 2018,
    también cabeceras y cada sexo. El año es el promedio de los niveles mensuales, como lo
    calcula el DANE.
    """
    root, av = _disponibles_reales(empalme)
    publicado = PUBLICADO[PUBLICADO["serie"] == ("empalme" if empalme else "principal")]
    anios = sorted(set(av["anio"]) & set(publicado["anio"]))
    if not anios:
        pytest.skip("ningún año descargado tiene cifras publicadas")

    problemas = []
    for grupo, pub in publicado.groupby("grupo"):
        anios_grupo = sorted(set(anios) & set(pub["anio"]))
        if not anios_grupo:
            continue
        nombre = "" if grupo == "total" else f" ({grupo})"
        mensual = _serie_grupo(anios_grupo, grupo, False, empalme, root)
        if grupo == "total":
            calculados = set(zip(mensual["anio"], mensual["mes"]))
            for a, ms, falta in zip(av["anio"], av["mes"], av["faltantes"]):
                if a in anios_grupo and (a, ms) not in calculados and ((pub["anio"] == a) & (pub["mes"] == ms)).any():
                    problemas.append(f"{a}-{ms:02d}: no se pudo calcular (falta {falta or 'todo: el mes se leyó vacío'})")
        for _, r in mensual.merge(pub, on=["anio", "mes"], suffixes=("", "_dane")).iterrows():
            if (r["serie"], grupo, r["anio"], r["mes"]) in SIN_COMPARAR:
                continue
            fecha = f"{int(r['anio'])}-{int(r['mes']):02d}{nombre}"
            for tasa in ("td", "tgp", "to"):
                if not abs(r[tasa] - r[f"{tasa}_dane"]) <= 0.01:
                    problemas.append(f"{fecha}: {tasa.upper()} {r[tasa]:.2f}, el DANE publica {r[f'{tasa}_dane']:.2f}")
            if not abs(r["ocupados"] / (1000 * r["ocupados_dane"]) - 1) <= 1e-4:
                problemas.append(f"{fecha}: {r['ocupados'] / 1e3:,.0f} mil ocupados, el DANE publica "
                                 f"{r['ocupados_dane']:,.0f} mil")

        completos = [a for a in anios_grupo if (mensual["anio"] == a).sum() == 12 and (pub["anio"] == a).sum() == 12]
        if completos:
            niveles = pub[pub["anio"].isin(completos)].groupby("anio")[["pet", "ocupados", "desocupados"]].mean()
            fuerza = niveles["ocupados"] + niveles["desocupados"]
            dane = pd.DataFrame({"td": 100 * niveles["desocupados"] / fuerza, "tgp": 100 * fuerza / niveles["pet"],
                                 "to": 100 * niveles["ocupados"] / niveles["pet"]})
            anual = _serie_grupo(completos, grupo, True, empalme, root).set_index("anio")
            for a in completos:
                for tasa in ("td", "tgp", "to"):
                    if not abs(anual.at[a, tasa] - dane.at[a, tasa]) <= 0.01:
                        problemas.append(f"{a} anual{nombre}: {tasa.upper()} {anual.at[a, tasa]:.2f}, con las cifras "
                                         f"mensuales del DANE da {dane.at[a, tasa]:.2f}")
    assert not problemas, f"{len(problemas)} diferencia(s) con lo publicado por el DANE:\n" + \
        "\n".join(sorted(problemas))


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
    root, av = _disponibles_reales(empalme)
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


def test_anios_y_meses_de_numpy(geih_root, tmp_path, monkeypatch):
    """dd.geih.load(df.anio.max()) da un entero de numpy, que no es int."""
    import numpy as np

    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    df = dd.geih.load(np.int64(2016), months=np.int64(1), root=geih_root, cache=False)
    assert df["anio"].unique().tolist() == [2016] and df["mes"].unique().tolist() == [1]
    t = dd.geih.serie_tabla(np.int64(2016), meses=np.int64(1), root=geih_root)
    assert t["total"].item() == pytest.approx(dd.tabla(df)["total"].item())
