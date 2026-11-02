"""Estadísticas Vitales: carpetas, carga, armonización, indicadores y tasas."""

import json
import os
import warnings
from pathlib import Path

import pandas as pd
import pytest

import dane_data as dd
from dane_data import cli


def test_carpeta_eevv(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EEVV", raising=False)
    assert dd.get_path("eevv") == dd.config.DEFAULT_HOME / "eevv"
    dd.set_paths(eevv=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["eevv"] == str(tmp_path / "x")
    assert dd.show_paths()["eevv"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("eevv") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_EEVV", str(tmp_path / "env"))
    assert dd.get_path("eevv") == tmp_path / "env"


# ---------------------------------------------------------------------------------------------------- #
# Carga y armonización
# ---------------------------------------------------------------------------------------------------- #
def _def(root, anio):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return dd.eevv.load(anio, root=root)


def test_load_varias_epocas_con_el_mismo_esquema(eevv_root):
    d = _def(eevv_root, [1979, 1991, 1998, 2025])
    assert len(d) == 12
    assert d["anio"].value_counts().to_dict() == {1979: 3, 1991: 3, 1998: 3, 2025: 3}
    # Las categorías fijas se conservan al unir años (municipios y causas cambian de un año a otro y se igualan)
    for c in ("sexo", "grupo_edad", "departamento_residencia", "mpio_residencia", "causa_cie", "causa_105"):
        assert isinstance(d[c].dtype, pd.CategoricalDtype), c
    assert set(d.columns) == set(dd.eevv.ETIQUETAS["defunciones"])


def test_load_sin_datos(tmp_path):
    with pytest.raises(FileNotFoundError, match="dane_data.eevv.download"):
        dd.eevv.load(2020, root=tmp_path)
    with pytest.raises(ValueError, match="Tipo desconocido"):
        dd.eevv.load(2020, tipo="bautizos", root=tmp_path)


def test_grupos_de_edad_de_las_tres_epocas(eevv_root):
    d = _def(eevv_root, [1979, 1998, 2025])
    grupo = lambda anio, mes, col="grupo_edad": d[(d.anio == anio) & (d.mes == mes)][col].tolist()  # noqa: E731
    # 25 grupos: el 5 es «6 a 11 meses», el 10 «15 a 19 años» y el 25 «edad desconocida»
    assert grupo(1979, 1) == ["Menor de 1 año"]
    assert grupo(1979, 2) == ["De 15 a 19 años"]
    assert grupo(1979, 3) == ["Edad desconocida"]
    assert grupo(1979, 2, "grupo_edad_amplio") == ["De 15 a 44 años"]
    # 26 grupos: el 6 es «6 a 11 meses», el 11 «15 a 19 años» y el 26 «edad desconocida»
    assert grupo(1998, 4) == ["De 15 a 19 años", "Menor de 1 año"]
    assert grupo(1998, 5) == ["Edad desconocida"]
    # 30 grupos: el 14 es «30 a 34 años» y el 28 «100 años y más»; antes de 2008 el DANE cierra en 85
    assert grupo(2025, 12) == ["De 30 a 34 años"]
    assert grupo(2025, 11) == ["Menor de 1 año"]
    assert grupo(2025, 1) == ["De 85 años y más"]
    assert grupo(2025, 1, "grupo_edad_amplio") == ["De 65 años y más"]


def test_menor_un_anio(eevv_root):
    d = _def(eevv_root, [1979, 2025]).set_index(["anio", "mes"])["menor_un_anio"]
    assert bool(d.loc[(1979, 1)])
    assert not d.loc[(1979, 2)]
    assert pd.isna(d.loc[(1979, 3)])  # edad desconocida


def test_primer_semestre_de_1991_sin_detalle_de_edad(eevv_root):
    with pytest.warns(UserWarning, match="1991"):
        d = dd.eevv.load(1991, root=eevv_root)
    d = d.set_index(["mes", "sexo"])
    enero_junio = d.loc[(3, "Hombre")]
    assert enero_junio["grupo_edad"] == "Menor de 10 años, sin detalle"
    assert enero_junio["grupo_edad_amplio"] == "Menor de 10 años, sin detalle"
    assert pd.isna(enero_junio["menor_un_anio"])
    assert d.loc[(9, "Hombre"), "grupo_edad"] == "De 1 a 4 años"  # julio–diciembre sigue el DDI
    assert d.loc[(3, "Mujer"), "grupo_edad"] == "De 85 años y más"  # los mayores de 10 años no se tocan


def test_aviso_de_cobertura_de_1979(eevv_root):
    with pytest.warns(UserWarning, match="incompletos"):
        dd.eevv.load(1979, root=eevv_root)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        dd.eevv.load(2025, root=eevv_root)
        dd.eevv.load(1998, tipo="nacimientos", root=eevv_root)


def test_lugares_codigo_antiguo_de_caqueta_y_residencias_especiales(eevv_root):
    d = _def(eevv_root, 1979).set_index("mes")
    assert d.loc[1, "dpto_ocurrencia"] == 18
    assert d.loc[1, "departamento_ocurrencia"] == "Caquetá"
    assert d.loc[1, "mpio_ocurrencia"] == "18001"
    assert d.loc[1, "departamento_residencia"] == "Caquetá"
    # 01 es «sin información» y 75 «en el extranjero»: se conserva el código, pero no son departamentos
    assert d.loc[2, "dpto_residencia"] == 1
    assert pd.isna(d.loc[2, "departamento_residencia"]) and pd.isna(d.loc[2, "mpio_residencia"])
    assert d.loc[3, "mpio_ocurrencia"] == "05002"
    extranjero = _def(eevv_root, 1998).set_index("sexo").loc["Mujer"].iloc[0]
    assert extranjero["dpto_residencia"] == 75 and pd.isna(extranjero["departamento_residencia"])
    blanco = _def(eevv_root, 2025).set_index("mes").loc[11]
    assert pd.isna(blanco["dpto_residencia"]) and blanco["mpio_ocurrencia"] == "08634"


def test_areas_y_sitios_por_epoca(eevv_root):
    d = _def(eevv_root, 1979).set_index("mes")
    assert d.loc[2, "area_ocurrencia"] == "Resto"
    assert d.loc[3, "area_ocurrencia"] == "Sin información"
    assert d.loc[1, "sitio"] == "Casa" and d.loc[3, "sitio"] == "Sin información"
    assert d["area_residencia"].isna().all()  # no existe antes de 1992
    d = _def(eevv_root, 2025).set_index("mes")
    assert d.loc[1, "area_ocurrencia"] == "Centro poblado" and d.loc[1, "area_residencia"] == "Centro poblado"
    assert d.loc[1, "sitio"] == "Casa" and d.loc[12, "sitio"] == "Hospital o clínica"


def test_estado_civil_y_educacion_por_epoca(eevv_root):
    d = _def(eevv_root, 1979).set_index("mes")["estado_civil"]
    assert d.loc[1] == "Soltero(a)" and d.loc[2] == "Unión libre, divorciado(a) u otro" and d.loc[3] == "Sin información"
    d = _def(eevv_root, 1998).set_index("mes")
    assert d.loc[5, "estado_civil"] == "Sin información"
    assert d.loc[4, "estado_civil"].tolist() == ["Soltero(a)", "Separado(a) o divorciado(a)"]
    assert d.loc[4, "nivel_educativo"].tolist() == ["Primaria", "Ninguno"]
    d = _def(eevv_root, 2025).set_index("mes")
    assert d.loc[12, "estado_civil"] == "Casado(a)" and d.loc[1, "estado_civil"] == "Soltero(a)"
    assert d.loc[12, "nivel_educativo"] == "Superior" and d.loc[11, "nivel_educativo"] == "Ninguno"
    assert d["nivel_educativo"].cat.ordered
    assert d.loc[12, "etnia"] == "Indígena"


def test_regimen_de_salud_por_epoca(eevv_root):
    d = _def(eevv_root, 1998).set_index("mes")["regimen_salud"]
    assert d.loc[4].tolist() == ["Sin información", "Sin información"]  # hasta 2000, el 4 es «ignorado»
    assert d.loc[5] == "Vinculado"
    d = _def(eevv_root, 2025).set_index("mes")["regimen_salud"]
    assert d.loc[12] == "Subsidiado" and d.loc[1] == "No asegurado"


def test_manera_de_muerte_por_epoca(eevv_root):
    assert _def(eevv_root, 1979)["manera_muerte"].isna().all()
    d = _def(eevv_root, 1998).set_index("sexo")["manera_muerte"]
    assert d.loc["Hombre"] == "Homicidio"
    assert d.loc["Mujer"].tolist() == ["Natural", "En estudio"]
    d = _def(eevv_root, 2025).set_index("mes")["manera_muerte"]
    assert d.loc[12] == "Natural" and d.loc[11] == "Homicidio" and d.loc[1] == "Suicidio"


def test_causas(eevv_root):
    d = _def(eevv_root, 1979).set_index("mes")
    assert d.loc[1, "causa_cie"] == "0090"  # read_table lo vuelve número: se recupera el cero
    assert d["cie_rev"].eq(9).all()
    assert d.loc[1, "causa_105"] == "001"
    assert d.loc[1, "causa_105_nombre"] == dd.eevv.causas()["105"]["001"]
    assert d["gran_causa"].isna().all() and d["materna"].isna().all()
    d = _def(eevv_root, 1998).set_index("sexo")
    assert d.loc["Hombre", "causa_cie"] == "X954"
    assert d["cie_rev"].eq(10).all()
    # La 6/66 no se pasa a la 6/67, pero su primer dígito sí sirve; su 700 es el 000 de la 6/67
    assert d["causa_667"].isna().all()
    assert d.loc["Hombre", "gran_causa"] == "Causas externas"
    assert d.loc["Mujer", "gran_causa"].tolist() == ["Enfermedades del sistema circulatorio", "Signos y síntomas mal definidos"]
    d = _def(eevv_root, 2025).set_index("mes")
    assert d.loc[12, "causa_667"] == "612"
    assert d.loc[12, "causa_667_nombre"] == "Embarazo, parto y puerperio"
    assert d.loc[12, "gran_causa"] == "Las demás causas"
    assert bool(d.loc[12, "materna"]) and not d.loc[11, "materna"]


def test_listas_de_causas_completas():
    c = dd.eevv.causas()
    assert len(c["667"]) == 67 and len(c["105"]) == 105
    assert c["105"]["101"] == "Agresiones (homicidios) y secuelas"


def test_nacimientos(eevv_root):
    d = dd.eevv.load([1998, 2025], tipo="nacimientos", root=eevv_root)
    assert set(d.columns) == set(dd.eevv.ETIQUETAS["nacimientos"])
    a = d[d.anio == 1998].set_index("sexo")
    h, m = a.loc["Hombre"], a.loc["Mujer"]
    assert h["peso_grupo"] == "2.000 a 2.499" and bool(h["bajo_peso"]) and not m["bajo_peso"]
    assert h["edad_madre"] == "De 15 a 19 años" and bool(h["madre_adolescente"]) and not m["madre_adolescente"]
    assert bool(h["cesarea"]) and not m["cesarea"]
    assert not h["parto_multiple"] and bool(m["parto_multiple"])
    assert h["consultas"] == 3 and pd.isna(m["consultas"])
    assert h["edad_padre"] == 25 and pd.isna(m["edad_padre"])
    assert pd.isna(m["hijos_nacidos_vivos"]) and h["hijos_nacidos_vivos"] == 1
    assert h["nivel_educativo_madre"] == "Primaria" and m["nivel_educativo_madre"] == "Ninguno"
    assert h["gestacion_grupo"] == "De 38 a 41"
    assert d[d.anio == 1998]["prematuro"].isna().all()  # no existe antes de 2008

    b = d[d.anio == 2025].set_index("sexo")
    # El grupo «de 28 a 37» de T_GES es el mismo para los dos; solo T_GES_AGRU_CIE distingue el prematuro
    assert b.loc["Hombre", "gestacion_grupo"] == b.loc["Mujer", "gestacion_grupo"] == "De 28 a 37"
    assert not b.loc["Hombre", "prematuro"] and bool(b.loc["Mujer", "prematuro"])
    i = b.loc["Indeterminado"]
    assert pd.isna(i["prematuro"]) and pd.isna(i["cesarea"]) and pd.isna(i["bajo_peso"]) and pd.isna(i["madre_adolescente"])
    assert i["edad_madre"] == "Sin información" and i["peso_grupo"] == "Sin información"


def test_fetales(eevv_root):
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # el texto de N_HIJOSM no debe romper nada
        d = dd.eevv.load([1998, 2009], tipo="fetales", root=eevv_root)
    assert set(d.columns) == set(dd.eevv.ETIQUETAS["fetales"])
    a = d[d.anio == 1998].set_index("sexo")
    assert a.loc["Hombre", "gestacion_grupo"] == "De 28 y más"  # en 1998–2007 el 3 es «28 y más»
    assert a.loc["Indeterminado", "gestacion_grupo"] == "Ignorado"
    assert a.loc["Hombre", "nivel_educativo_madre"] == "Superior"
    assert a.loc["Hombre", "causa_cie"] == "P018"
    b = d[d.anio == 2009].iloc[0]
    assert pd.isna(b["nivel_educativo_madre"])  # no sigue el DDI
    assert b["gestacion_grupo"] == "Menos de 22" and bool(b["prematuro"])
    assert b["causa_667"] == "402" and b["gran_causa"] == "Afecciones del período perinatal"


def test_regimen_de_salud_fetal_desde_2024_cambia_de_nombre(eevv_root):
    d = dd.eevv.load(2025, tipo="fetales", root=eevv_root)
    assert d["regimen_salud"].tolist() == ["Subsidiado"]


def test_columnas(eevv_root):
    d = dd.eevv.load(2025, columns=["GRU_ED1", "otrsitiode"], root=eevv_root)
    assert {"GRU_ED1", "OTRSITIODE", "grupo_edad"} <= set(d.columns)
    assert "C_BAS1" not in d.columns
    d = dd.eevv.load(2025, columns="GRU_ED1", root=eevv_root)
    assert "GRU_ED1" in d.columns
    d = dd.eevv.load(2025, columns="all", root=eevv_root)
    assert {"C_BAS1", "OTRSITIODE", "grupo_edad"} <= set(d.columns)
    d = dd.eevv.load(2025, harmonize_vars=False, root=eevv_root)
    assert "C_BAS1" in d.columns and "grupo_edad" not in d.columns and d["anio"].eq(2025).all()


def test_progreso(eevv_root):
    avance = []
    dd.eevv.load(2025, root=eevv_root, progress=lambda f, m: avance.append(f))
    assert avance == [0.0, 1.0]


# ---------------------------------------------------------------------------------------------------- #
# Indicadores y series
# ---------------------------------------------------------------------------------------------------- #
@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CACHE_DIR", tmp_path / "cache")
    return tmp_path / "cache"


def test_indicadores_defunciones(eevv_root):
    r = dd.eevv.indicadores(_def(eevv_root, [1979, 1998, 2025]), por="anio").set_index("anio")
    assert r["defunciones"].tolist() == [3, 3, 3]
    assert r.loc[1998, ["hombres", "mujeres"]].tolist() == [1, 2]
    assert r["menores_un_anio"].tolist() == [1, 1, 1]
    assert r.loc[2025, "pct_menores_un_anio"] == pytest.approx(100 / 3)
    assert pd.isna(r.loc[1979, "maternas"]) and r.loc[1998, "maternas"] == 0 and r.loc[2025, "maternas"] == 1
    assert pd.isna(r.loc[1979, "homicidios"])  # no hay manera de muerte antes de 1997
    assert r.loc[1998, ["homicidios", "suicidios", "accidentes"]].tolist() == [1, 0, 0]
    assert r.loc[2025, ["homicidios", "suicidios", "accidentes"]].tolist() == [1, 1, 0]
    assert r.loc[1998, "pct_mal_definidas"] == pytest.approx(100 / 3)


def test_indicadores_menores_vacio_en_1991(eevv_root):
    r = dd.eevv.indicadores(_def(eevv_root, 1991), por="anio")
    assert pd.isna(r["menores_un_anio"].iloc[0]) and pd.isna(r["pct_menores_un_anio"].iloc[0])


def test_indicadores_nacimientos(eevv_root):
    r = dd.eevv.indicadores(dd.eevv.load(2025, tipo="nacimientos", root=eevv_root)).iloc[0]
    assert r["nacimientos"] == 3
    assert r["razon_sexo"] == 100  # un hombre, una mujer; el indeterminado no cuenta
    # Sobre quienes tienen el dato: 2 de los 3 nacimientos
    assert r["pct_cesarea"] == 50 and r["pct_prematuro"] == 50 and r["pct_bajo_peso"] == 50
    assert r["pct_parto_multiple"] == 50 and r["pct_madre_adolescente"] == 50
    assert r["pct_cuatro_consultas"] == 50 and r["consultas_promedio"] == 3


def test_indicadores_vacios_sin_el_dato(eevv_root):
    r = dd.eevv.indicadores(dd.eevv.load(1998, tipo="nacimientos", root=eevv_root), por="anio").iloc[0]
    assert pd.isna(r["pct_prematuro"])
    assert r["pct_cesarea"] == 50


def test_indicadores_fetales(eevv_root):
    r = dd.eevv.indicadores(dd.eevv.load(1998, tipo="fetales", root=eevv_root)).iloc[0]
    assert r["fetales"] == 2 and "hombres" not in r.index
    assert r["pct_bajo_peso"] == 100 and r["pct_madre_adolescente"] == 100


def test_indicadores_dropna(eevv_root):
    d = _def(eevv_root, 2025)
    r = dd.eevv.indicadores(d, por="departamento_residencia")
    assert r["defunciones"].sum() == 2
    assert dd.eevv.indicadores(d, por="departamento_residencia", dropna=False)["defunciones"].sum() == 3


def test_indicadores_sin_armonizar(eevv_root):
    with pytest.raises(ValueError, match="armonizados"):
        dd.eevv.indicadores(dd.eevv.load(2025, harmonize_vars=False, root=eevv_root))


@pytest.mark.parametrize("tipo, anios, por, filtros", [
    ("defunciones", [1998, 2025], None, None),
    ("defunciones", [1998, 2025], "sexo", None),
    ("defunciones", [1998, 2025], "gran_causa", {"sexo": ["Mujer"]}),
    ("nacimientos", [1998, 2025], ["sexo", "edad_madre"], None),
    ("nacimientos", [1998, 2025], None, {"mes": (10, 12)}),
    ("fetales", [1998, 2009], "sexo", None),
])
def test_serie_indicadores_igual_a_los_microdatos(eevv_root, cache, tipo, anios, por, filtros):
    d = dd.eevv.load(anios, tipo=tipo, root=eevv_root)
    if filtros:
        d = dd.geih.filtrar(d, filtros)
    llaves = ["anio", *([por] if isinstance(por, str) else por or [])]
    esperado = dd.eevv.indicadores(d, por=llaves).astype({"anio": "int64"})
    res = dd.eevv.serie_indicadores(anios, tipo, por=por, filtros=filtros, root=eevv_root).astype({"anio": "int64"})
    pd.testing.assert_frame_equal(res, esperado.sort_values(llaves, ignore_index=True), check_categorical=False, check_dtype=False)


def test_serie_usa_la_cache_y_se_invalida(eevv_root, cache, monkeypatch):
    primera = dd.eevv.serie_indicadores(2025, root=eevv_root)
    assert list(cache.rglob("*.parquet"))

    def no_debe_leer(*a, **k):
        raise AssertionError("debió usar la caché")

    monkeypatch.setattr(dd.eevv.agregados, "load", no_debe_leer)
    pd.testing.assert_frame_equal(dd.eevv.serie_indicadores(2025, root=eevv_root), primera)
    # Un filtro nuevo se calcula de la caché del año armonizado, sin volver a leer el archivo del DANE
    assert dd.eevv.serie_indicadores(2025, filtros={"sexo": ["Mujer"]}, root=eevv_root)["defunciones"].tolist() == [1]
    monkeypatch.undo()
    monkeypatch.setattr(dd.config, "CACHE_DIR", cache)

    # Si el archivo cambia, se recalcula
    archivo = next((eevv_root / "datos" / "defunciones" / "2025").iterdir())
    archivo.write_bytes(archivo.read_bytes() + '"05","001","1","1","","2025","01","1","5","14","04","99","9","05","001","1","5","0","I219","307","051"\n'.encode("latin-1"))
    assert dd.eevv.serie_indicadores(2025, root=eevv_root)["defunciones"].tolist() == [4]


def test_serie_conteos(eevv_root, cache):
    r = dd.eevv.serie_conteos([1998, 2025], por="sexo", root=eevv_root)
    assert r.set_index(["anio", "sexo"])["n"].to_dict() == {(1998, "Hombre"): 1, (1998, "Mujer"): 2, (2025, "Hombre"): 2, (2025, "Mujer"): 1}
    r = dd.eevv.serie_conteos(2025, por="causa_105_nombre", root=eevv_root)
    assert "Agresiones (homicidios) y secuelas" in r["causa_105_nombre"].tolist()
    assert dd.eevv.serie_conteos(2025, por="departamento_residencia", dropna=False, root=eevv_root)["n"].sum() == 3


def test_serie_sin_datos(tmp_path, cache):
    with pytest.raises(FileNotFoundError, match="eevv.download"):
        dd.eevv.serie_indicadores(2025, root=tmp_path)


def test_serie_avisa_una_vez_de_la_cobertura(eevv_root, cache):
    with pytest.warns(UserWarning, match="incompletos") as avisos:
        dd.eevv.serie_indicadores(1979, root=eevv_root)
    assert len(avisos) == 1


def test_clear_cache(eevv_root, cache):
    dd.eevv.serie_indicadores(2025, root=eevv_root)
    n = len(list(cache.rglob("*.parquet")))
    assert n >= 2  # el año armonizado y el resultado
    assert dd.eevv.clear_cache(dias=1) == 0
    assert dd.eevv.clear_cache() == n
    assert not list(cache.rglob("*.parquet"))


# ---------------------------------------------------------------------------------------------------- #
# Tasas
# ---------------------------------------------------------------------------------------------------- #
def _poblacion(anio, **kw):
    return dd.poblacion(anio, **kw)["poblacion"].iloc[0]


def test_tasas_a_mano(eevv_root, cache):
    r = dd.eevv.tasas(2025, root=eevv_root).iloc[0]
    pob = _poblacion(2025)
    assert r["poblacion"] == pob
    assert (r["nacimientos"], r["defunciones"], r["fetales"]) == (3, 3, 1)
    assert r["tasa_natalidad"] == pytest.approx(1000 * 3 / pob)
    assert r["tasa_mortalidad"] == pytest.approx(1000 * 3 / pob)
    assert r["defunciones_menores_1"] == 1
    assert r["mortalidad_infantil"] == pytest.approx(1000 * 1 / 3)
    assert r["defunciones_maternas"] == 1
    assert r["razon_mortalidad_materna"] == pytest.approx(100_000 * 1 / 3)
    assert r["razon_mortalidad_fetal"] == pytest.approx(1000 * 1 / (3 + 1))
    # Una madre de 25–29 y otra de 15–19; la que no tiene edad no entra. Los demás grupos fértiles valen 0.
    mujeres_15 = _poblacion(2025, sexo="Mujer", edades=(15, 19))
    mujeres_25 = _poblacion(2025, sexo="Mujer", edades=(25, 29))
    assert r["tasa_global_fecundidad"] == pytest.approx(5 * (1 / mujeres_15 + 1 / mujeres_25))


def test_tasas_por_departamento_usa_la_residencia(eevv_root, cache):
    r = dd.eevv.tasas(2025, por="departamento", root=eevv_root).set_index("departamento")
    # Defunciones: residentes en Cauca y Antioquia; el de residencia en blanco queda por fuera, aunque ocurrió en Atlántico
    assert r["defunciones"].dropna().to_dict() == {"Antioquia": 1, "Cauca": 1}
    assert "Atlántico" not in r.index
    assert r.loc["Cauca", "poblacion"] == _poblacion(2025, departamento="Cauca")
    assert r.loc["Cauca", "tasa_mortalidad"] == pytest.approx(1000 / _poblacion(2025, departamento="Cauca"))
    assert r["nacimientos"].dropna().to_dict() == {"Bolívar": 1, "Casanare": 1}
    assert r.loc["Bolívar", "tasa_natalidad"] == pytest.approx(1000 / _poblacion(2025, departamento="Bolívar"))
    mujeres = _poblacion(2025, departamento="Bolívar", sexo="Mujer", edades=(15, 19))
    assert r.loc["Bolívar", "tasa_global_fecundidad"] == pytest.approx(5 / mujeres)


def test_tasas_por_sexo_y_area(eevv_root, cache):
    r = dd.eevv.tasas(2025, por="sexo", root=eevv_root).set_index("sexo")
    assert r.loc["Hombre", "poblacion"] == _poblacion(2025, sexo="Hombre")
    assert r.loc["Hombre", "defunciones"] == 2 and r.loc["Mujer", "defunciones"] == 1
    assert r.loc["Mujer", "tasa_mortalidad"] == pytest.approx(1000 / _poblacion(2025, sexo="Mujer"))
    assert r["tasa_global_fecundidad"].isna().all() and r["fetales"].isna().all()  # no aplican por sexo
    r = dd.eevv.tasas(2025, por="area", root=eevv_root).set_index("area")
    resto = "Centros poblados y rural disperso"
    assert r.loc[resto, "poblacion"] == _poblacion(2025, area=resto)
    # Centro poblado + rural disperso = centros poblados y rural disperso; el indeterminado sin área queda por fuera
    assert r.loc[resto, "defunciones"] == 1 and r.loc["Cabecera", "defunciones"] == 1
    assert r.loc[resto, "nacimientos"] == 1


def test_tasas_avisos_de_cobertura_y_anios_sin_poblacion(eevv_root, cache):
    with pytest.warns(UserWarning, match="incompletos"):
        r = dd.eevv.tasas(1979, root=eevv_root).iloc[0]
    assert r["poblacion"] == _poblacion(1979) and r["tasa_mortalidad"] > 0
    assert pd.isna(r["tasa_natalidad"]) and pd.isna(r["mortalidad_infantil"])
    with pytest.warns(UserWarning, match="1985"):
        r = dd.eevv.tasas(1979, por="departamento", root=eevv_root)
    assert r["defunciones"].sum() == 2 and r["tasa_mortalidad"].isna().all()


def test_tasas_1991_sin_mortalidad_infantil(eevv_root, cache):
    with pytest.warns(UserWarning, match="1991"):
        r = dd.eevv.tasas(1991, root=eevv_root).iloc[0]
    assert pd.isna(r["defunciones_menores_1"]) and pd.isna(r["mortalidad_infantil"]) and r["tasa_mortalidad"] > 0


def test_tasas_solo_con_lo_descargado(eevv_root, cache):
    # 2009 solo tiene fetales
    r = dd.eevv.tasas(2009, root=eevv_root).iloc[0]
    assert r["fetales"] == 1 and pd.isna(r["nacimientos"]) and pd.isna(r["razon_mortalidad_fetal"])


def test_tasas_errores(tmp_path, eevv_root, cache):
    with pytest.raises(FileNotFoundError, match="eevv.download"):
        dd.eevv.tasas(2025, root=tmp_path)
    with pytest.raises(ValueError, match="municipio"):
        dd.eevv.tasas(2025, por="municipio", root=eevv_root)
    with pytest.raises(ValueError, match="fetales"):
        dd.eevv.tasas_especificas(2025, "fetales", root=eevv_root)
    with pytest.raises(ValueError, match="mujeres"):
        dd.eevv.tasas_especificas(2025, "nacimientos", por="sexo", root=eevv_root)


def test_tasas_especificas_fecundidad(eevv_root, cache):
    r = dd.eevv.tasas_especificas(2025, "nacimientos", root=eevv_root).set_index("edad_madre")
    assert len(r) == 9  # de 10 a 54 años, también los grupos sin nacimientos
    assert r.loc["De 15 a 19 años", "nacimientos"] == 1
    assert r.loc["De 15 a 19 años", "mujeres"] == _poblacion(2025, sexo="Mujer", edades=(15, 19))
    assert r.loc["De 15 a 19 años", "tasa"] == pytest.approx(1000 / r.loc["De 15 a 19 años", "mujeres"])
    assert r.loc["De 30 a 34 años", "nacimientos"] == 0 and r.loc["De 30 a 34 años", "tasa"] == 0


def test_tasas_especificas_mortalidad(eevv_root, cache):
    r = dd.eevv.tasas_especificas(2025, "defunciones", root=eevv_root).set_index("grupo_edad")
    assert len(r) == 19  # menor de 1, 1–4, 16 quinquenios y 85 o más; sin la edad desconocida
    assert r.loc["Menor de 1 año", "poblacion"] == _poblacion(2025, edades=0)
    assert r.loc["De 85 años y más", "poblacion"] == _poblacion(2025, edades=(85, 100))
    assert r.loc["De 85 años y más", "defunciones"] == 1
    r = dd.eevv.tasas_especificas(2025, "defunciones", por="sexo", root=eevv_root).set_index(["sexo", "grupo_edad"])
    assert r.loc[("Mujer", "De 30 a 34 años"), "poblacion"] == _poblacion(2025, sexo="Mujer", edades=(30, 34))


def test_tasas_especificas_1991_menores_vacios(eevv_root, cache):
    with pytest.warns(UserWarning, match="1991"):
        r = dd.eevv.tasas_especificas(1991, "defunciones", root=eevv_root).set_index("grupo_edad")
    assert r.loc[["Menor de 1 año", "De 1 a 4 años", "De 5 a 9 años"], "tasa"].isna().all()
    assert r.loc["De 85 años y más", "defunciones"] == 1


# ---------------------------------------------------------------------------------------------------- #
# Línea de comandos
# ---------------------------------------------------------------------------------------------------- #
def test_cli_estado(eevv_root, monkeypatch, capsys):
    monkeypatch.setitem(dd.config._session, "eevv", eevv_root)
    assert cli.main(["estado"]) == 0
    salida = capsys.readouterr().out
    assert "Estadísticas Vitales:" in salida
    assert "defunciones: 4 años (1979–2025)" in salida and "fetales: 3 años (1998–2025)" in salida


def test_cli_estado_sin_datos(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(dd.config._session, "eevv", tmp_path / "nada")
    assert cli.main(["estado"]) == 0
    assert "Estadísticas Vitales: sin datos" in capsys.readouterr().out


def test_cli_descargar(monkeypatch):
    llamada = {}
    monkeypatch.setattr(dd.eevv, "download", lambda **kw: llamada.update(kw) or [])
    assert cli.main(["descargar", "eevv", "--anios", "2024", "2025", "--tipos", "fetales", "--borrar-zips"]) == 0
    assert llamada == {"years": [2024, 2025], "tipos": ["fetales"], "delete_zips": True, "forzar": False}
    monkeypatch.setattr(dd.eevv, "download", lambda **kw: ["fetales 2025: no se pudo descargar"])
    assert cli.main(["descargar", "eevv", "--anios", "2025"]) == 1


@pytest.mark.parametrize("argumentos", [["descargar", "eevv", "--tic"], ["descargar", "eevv", "--empalme"],
                                        ["descargar", "eam", "--tipos", "fetales"], ["descargar", "geih", "--tipos", "fetales"]])
def test_cli_opciones_de_otra_encuesta(argumentos, capsys):
    assert cli.main(argumentos) == 2
    assert "no aplica" in capsys.readouterr().err


def test_cli_config(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EEVV", raising=False)
    assert cli.main(["config", "--eevv", str(tmp_path / "x")]) == 0
    assert json.loads((tmp_path / "c.json").read_text())["eevv"] == str(tmp_path / "x")


# ---------------------------------------------------------------------------------------------------- #
# Datos reales (se saltan si no están)
# ---------------------------------------------------------------------------------------------------- #
REAL = Path(os.environ.get("DANE_DATA_TEST_EEVV", dd.get_path("eevv")))
hay_datos_reales = pytest.mark.skipif(not (REAL / "datos").is_dir(), reason="sin datos reales de las Estadísticas Vitales")
DATOS = Path(__file__).parent / "datos"


@hay_datos_reales
@pytest.mark.parametrize("tipo", dd.eevv.TIPOS)
def test_real_coincide_con_lo_publicado(tipo):
    """El total y el sexo de cada año, contra los cuadros definitivos del DANE (2008–2025)."""
    publicado = pd.read_csv(DATOS / "dane_eevv_publicado.csv")
    publicado = publicado[publicado["tipo"] == tipo].set_index("anio")
    assert len(publicado) == 18
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        conteo = dd.eevv.serie_conteos(publicado.index.tolist(), tipo, por="sexo", dropna=False, root=REAL)
    total = conteo.groupby("anio")["n"].sum()
    pd.testing.assert_series_equal(total, publicado["total"], check_names=False, check_index_type=False)
    for sexo, columna in (("Hombre", "hombres"), ("Mujer", "mujeres")):
        d = conteo[conteo["sexo"] == sexo].set_index("anio")["n"]
        pd.testing.assert_series_equal(d, publicado[columna], check_names=False, check_index_type=False)


@hay_datos_reales
@pytest.mark.parametrize("tipo", dd.eevv.TIPOS)
def test_real_coincide_por_departamento(tipo):
    """Los 33 departamentos de 2019–2025, contra los cuadros del DANE."""
    publicado = pd.read_csv(DATOS / "dane_eevv_departamentos.csv")
    publicado = publicado[publicado["tipo"] == tipo]
    columna = f"dpto_{publicado['base'].iloc[0]}"
    conteo = dd.eevv.serie_conteos(sorted(publicado["anio"].unique()), tipo, por=columna, root=REAL)
    res = conteo.rename(columns={columna: "dpto"}).astype({"dpto": "int64", "anio": "int64"})
    res = res[res["dpto"].isin(publicado["dpto"])].set_index(["anio", "dpto"])["n"].sort_index()
    pd.testing.assert_series_equal(res, publicado.set_index(["anio", "dpto"])["total"].sort_index(), check_names=False)


@hay_datos_reales
def test_real_grupos_de_edad_coinciden_con_gru_ed2():
    """El DANE agrupa GRU_ED2 aparte desde 1992: el grupo amplio armonizado debe dar lo mismo, salvo errores sueltos."""
    amplios = dict(enumerate(dd.eevv.GRUPOS_EDAD_AMPLIOS[:7], start=1))
    for anio in (1992, 1997, 1998, 2007, 2008, 2025):
        d = dd.eevv.load(anio, columns=["GRU_ED2"], root=REAL)
        esperado = pd.to_numeric(d["GRU_ED2"]).map(amplios)
        assert (d["grupo_edad_amplio"].astype("object") == esperado).mean() > 0.9995, anio


@hay_datos_reales
def test_real_serie_sin_saltos():
    """Cambios anuales grandes fuera de lo conocido: archivos cortados o mal leídos."""
    conocidos = {
        # 1980–1981 completan departamentos que faltan en 1979; 1985 sube en todo el país, sin explicación documentada;
        # 2020–2022 es la pandemia
        "defunciones": {1980, 1981, 1985, 2020, 2021, 2022},
        "nacimientos": {2023, 2024},  # la caída de la natalidad
        "fetales": {2000, 2001, 2002, 2003, 2005, 2007, 2011, 2012, 2020, 2023, 2024},  # muy variable: el registro va mejorando
    }
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        for tipo in dd.eevv.TIPOS:
            t = dd.eevv.serie_conteos(tipo=tipo, root=REAL).set_index("anio")["n"]
            assert list(t.index) == list(range(t.index.min(), 2026)), tipo
            variacion = t.pct_change().abs().dropna()
            saltos = {int(a) for a in variacion[variacion > 0.10].index} - conocidos[tipo]
            assert not saltos, (tipo, saltos)


@hay_datos_reales
def test_real_materna_coincide_con_el_cuadro_7():
    r = dd.eevv.indicadores(dd.eevv.load(2025, root=REAL)).iloc[0]
    assert r["maternas"] == 355
    assert r["menores_un_anio"] == 4526


# ---------------------------------------------------------------------------------------------------- #
# Diccionarios
# ---------------------------------------------------------------------------------------------------- #
@pytest.mark.parametrize("tipo, variable, etiqueta", [("nacimientos", "SEXO", "Sexo del nacido vivo"),
                                                      ("defunciones", "SEXO", "Sexo del fallecido"),
                                                      ("fetales", "TIPO_DEFUN", "Tipo de defunción")])
def test_diccionarios_por_certificado(tipo, variable, etiqueta):
    d = dd.diccionario(f"eevv_{tipo}")
    assert d[variable]["etiqueta"] == etiqueta
    assert dd.describir(variable, encuesta=f"eevv_{tipo}") == etiqueta


def test_diccionario_categorias_y_busqueda():
    assert dd.diccionario("eevv_nacimientos")["TIPO_PARTO"]["categorias"]["2"] == "Cesárea"
    assert "TIPO_PARTO" in dd.buscar_variable("parto", "eevv_nacimientos")["variable"].tolist()
    assert "P_PMAN_IRIS" in dd.buscar_variable("manera de muerte", "eevv_defunciones")["variable"].tolist()
