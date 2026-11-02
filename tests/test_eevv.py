"""Estadísticas Vitales: carpetas, carga, armonización, indicadores y tasas."""

import json
import warnings

import pandas as pd
import pytest

import dane_data as dd


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
