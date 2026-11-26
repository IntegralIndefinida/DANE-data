"""Datos sintéticos que imitan las rarezas de cada época de la GEIH, la EAM, las Estadísticas
Vitales y la ECV.
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _write(path: Path, text: str, encoding="utf-8-sig"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode(encoding))


def _stata_110(path: Path, columnas: dict):
    """Stata en formato 110 (Stata 7), como el de septiembre de 2021: pandas 2 no lo lee. ``None``
    es faltante.
    """
    tipos, campos, valores = [], [], []
    for v in columnas.values():
        if any(isinstance(x, float) for x in v):
            tipo, campo, faltante = 100, "<f8", 2.0**1023  # d
        elif all(x is None or -128 <= x <= 126 for x in v):
            tipo, campo, faltante = 98, "i1", 127  # b
        else:
            tipo, campo, faltante = 108, "<i4", 2147483647  # l
        tipos.append(tipo)
        campos.append(campo)
        valores.append([faltante if x is None else x for x in v])
    nvar, nobs = len(columnas), len(valores[0])
    filas = np.zeros(nobs, np.dtype([(f"v{i}", c) for i, c in enumerate(campos)]))
    for i, v in enumerate(valores):
        filas[f"v{i}"] = v
    texto = lambda s, n: s.encode().ljust(n, b"\0")  # noqa: E731
    path.write_bytes(
        bytes([110, 2, 1, 0])
        + nvar.to_bytes(2, "little")
        + nobs.to_bytes(4, "little")
        + bytes(81)
        + texto("01 Oct 2021 00:00", 18)
        + bytes(tipos)
        + b"".join(texto(n, 33) for n in columnas)
        + bytes(2 * (nvar + 1))
        + texto("%9.0g", 12) * nvar
        + bytes(33 * nvar)
        + bytes(81 * nvar)
        + bytes(5)
        + filas.tobytes()
    )


@pytest.fixture(autouse=True)
def sin_buscar_versiones(monkeypatch):
    """Las pruebas no consultan internet: el aviso de versión nueva se prueba con respuestas
    falsas.
    """
    monkeypatch.setenv("DANE_DATA_SIN_ACTUALIZACIONES", "1")


@pytest.fixture
def geih_root(tmp_path):
    root = tmp_path / "geih"
    base = root / "datos_csv"

    # --- Época 2016: Area/Cabecera/Resto, ';', coma decimal, blancos " ", sin PET explícito
    m = base / "2016" / "Enero"
    car = "Directorio;Secuencia_p;Orden;P6020;P6040;P6050;P6090;P6210;Clase;Dpto;Fex_c_2011\n"
    _write(
        m / "Cabecera - Características generales (Personas).csv",
        car
        + "1;1;1;1;30;1;1;6;1;11;100,5\n1;1;2;2;28;2;1;5;1;11;100,5\n1;1;3;2;8;3; ;2;1;11;100,5\n"
        "2;1;1;1;45;1;1;3;1;5;200,0\n",
    )
    _write(
        m / "Resto - Características generales (Personas).csv",
        car + "3;1;1;2;50;1;2;3;2;5;300,25\n",
    )
    # Area es subconjunto de Cabecera: no debe sumarse
    _write(
        m / "Area - Características generales (Personas).csv",
        car + "1;1;1;1;30;1;1;6;1;11;100,5\n",
    )
    ft = "Directorio;Secuencia_p;Orden;Fex_c_2011\n"
    _write(m / "Cabecera - Fuerza de trabajo.csv", ft + "1;1;1;100,5\n1;1;2;100,5\n2;1;1;200,0\n")
    _write(m / "Resto - Fuerza de trabajo.csv", ft + "3;1;1;300,25\n")
    # P6870 y OFICIO: la medición de informalidad del marco 2005 (asalariado en una empresa grande,
    # formal; cuenta propia solo, que no es profesional, informal)
    oc = (
        "Directorio;Secuencia_p;Orden;Oci;Inglabo;P6920;P6430;P6800;Rama2d;P6870;Oficio;"
        "Fex_c_2011\n"
    )
    _write(
        m / "Cabecera - Ocupados.csv",
        oc + "1;1;1;1;2000000;1;1;48;15;9;13;100,5\n2;1;1;1;500000;2;4;30;52;1;33;200,0\n",
    )
    _write(m / "Resto - Ocupados.csv", oc)
    _write(
        m / "Cabecera - Desocupados.csv",
        "Directorio;Secuencia_p;Orden;Dsi;Fex_c_2011\n1;1;2;1;100,5\n",
    )
    _write(
        m / "Resto - Inactivos.csv",
        "Directorio;Secuencia_p;Orden;Ini;Fex_c_2011\n3;1;1;1;300,25\n",
    )
    # Cada módulo trae las dos partes, aunque una esté vacía (sin una, el mes queda incompleto)
    _write(m / "Resto - Desocupados.csv", "Directorio;Secuencia_p;Orden;Dsi;Fex_c_2011\n")
    _write(m / "Cabecera - Inactivos.csv", "Directorio;Secuencia_p;Orden;Ini;Fex_c_2011\n")
    oi = "Directorio;Secuencia_p;Orden;P7495;P7500S1A1;Fex_c_2011\n"
    # 1.79769313486232e+308: así escribe el ANDA las celdas vacías de septiembre a diciembre de
    # 2017
    _write(
        m / "Cabecera - Otros ingresos.csv",
        oi + "1;1;1;1;800000;100,5\n2;1;1;2;1.79769313486232e+308;200,0\n",
    )
    _write(m / "Resto - Otros ingresos.csv", oi + "3;1;1;1;150000;300,25\n")
    # Carpeta que no es un mes (debe ignorarse)
    (base / "2016" / "Total_fact_exp_dto").mkdir(parents=True)

    # --- Época 2025: archivos únicos, PET/FFT/DSI en 'No ocupados', FEX_C18, latin-1, en
    # subcarpeta
    m = base / "2025" / "Enero 2025"
    car = (
        "PERIODO;MES;DIRECTORIO;SECUENCIA_P;ORDEN;P3271;P6040;P6050;P6090;P3042;CLASE;DPTO;"
        "FEX_C18;P6100;P6110\n"
    )
    _write(
        m / "Características generales, seguridad social en salud y educación.CSV",
        car + "202501;1;10;1;1;2;35;1;1;10;1;76;1000.5;1;1\n202501;1;10;1;2;1;20;3;1;6;1;76;"
        "1000.5;3;\n202501;1;11;1;1;1;70;1;1;3;2;76;500;1;5\n",
        encoding="latin-1",
    )
    _write(
        m / "Fuerza de trabajo.CSV",
        "DIRECTORIO;SECUENCIA_P;ORDEN;PET;FT;FFT;FEX_C18\n"
        "10;1;1;1;1;;1000.5\n"
        "10;1;2;1;1;;1000.5\n"
        "11;1;1;1;;1;500\n",
    )
    # Con las preguntas de la medición de informalidad del DANE: asalariada con salud y pensión
    # pagadas por la empresa (formal)
    _write(
        m / "Ocupados.CSV",
        "DIRECTORIO;SECUENCIA_P;ORDEN;OCI;INGLABO;P6920;P6430;P6800;RAMA2D_R4;FEX_C18;OFICIO_C8;"
        "P3045S1;P3046;P3069;P6765;P3065;P3066;P3067;P3067S1;P3067S2;P6775;P3068;P6450;P6930;"
        "P6940\n"
        "10;1;1;1;1423500;1;1;48;10;1000.5;5223;1;1;3;;;;;;;;;2;1;1\n",
    )
    _write(
        m / "CSV 13" / "No ocupados.CSV",
        "DIRECTORIO;SECUENCIA_P;ORDEN;DSI;FFT;FEX_C18\n10;1;2;1;;1000.5\n11;1;1;;1;500\n",
    )
    _write(
        m / "Datos del hogar y la vivienda.CSV",
        "DIRECTORIO;SECUENCIA_P;P5000;FEX_C18\n10;1;4;1000.5\n11;1;2;500\n",
    )
    _write(
        m / "Otros ingresos e impuestos.CSV",
        "DIRECTORIO;SECUENCIA_P;ORDEN;P7495;P7505;P7510S3A1;FEX_C18\n"
        "10;1;1;2;2;;1000.5\n"
        "11;1;1;2;1;1200000;500\n",
        encoding="latin-1",
    )
    # El "." es el faltante del DANE en las subpreguntas de Migración
    _write(
        m / "Migración.CSV",
        "DIRECTORIO;SECUENCIA_P;ORDEN;P3373;P3373S3;FEX_C18\n"
        "10;1;1;1;.;1000.5\n"
        "10;1;2;3;862;1000.5\n"
        "11;1;1;2;.;500\n",
    )

    # --- 2011: el CSV del ANDA perdió el punto decimal del factor; el TXT del mismo catálogo está
    # bien
    for carpeta, sep, fex in (
        ("Marzo_csv", ";", ("849.491.032.387.525", "107.845.157.267.357")),
        ("Marzo_txt", "\t", ("84.9491032387525", "1078.45157267357")),
    ):
        m = base / "2011" / carpeta
        ext = carpeta[-3:]
        fila = lambda *v: sep.join(map(str, v)) + "\n"  # noqa: E731
        _write(
            m / f"Cabecera - Características generales (Personas).{ext}",
            fila(
                "DIRECTORIO",
                "SECUENCIA_P",
                "ORDEN",
                "P6020",
                "P6040",
                "CLASE",
                "DPTO",
                "fex_c_2011",
            )
            + fila(20, 1, 1, 1, 30, 1, 5, fex[0])
            + fila(20, 1, 2, 2, 25, 1, 5, fex[0])
            + fila(21, 1, 1, 2, 40, 1, 5, fex[1]),
        )
        _write(
            m / f"Cabecera - Ocupados.{ext}",
            fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "OCI", "INGLABO", "fex_c_2011")
            + fila(20, 1, 1, 1, 1000000, fex[0])
            + fila(21, 1, 1, 1, 2000000, fex[1]),
        )
        _write(
            m / f"Cabecera - Desocupados.{ext}",
            fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "DSI", "fex_c_2011")
            + fila(20, 1, 2, 1, fex[0]),
        )
        _write(
            m / f"Cabecera - Fuerza de trabajo.{ext}",
            fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "fex_c_2011")
            + fila(20, 1, 1, fex[0])
            + fila(20, 1, 2, fex[0])
            + fila(21, 1, 1, fex[1]),
        )
        for modulo, marca in (
            ("Características generales (Personas)", "P6040"),
            ("Ocupados", "OCI"),
            ("Desocupados", "DSI"),
            ("Fuerza de trabajo", None),
        ):  # el resto, vacío
            _write(
                m / f"Resto - {modulo}.{ext}",
                fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", *filter(None, [marca]), "fex_c_2011"),
            )
        # Febrero de 2011: "Otras actividades" trae otro factor (FEX_C) que no debe reemplazar al
        # de características
        _write(
            m / f"Cabecera - Otras actividades y ayudas en la semana.{ext}",
            fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "FEX_C")
            + fila(20, 1, 1, 999)
            + fila(20, 1, 2, 999),
        )

    # --- Septiembre 2021: el CSV viene separado por espacios (ilegible); el Stata está bien, pero
    # en formato 110 (Stata 7), con edades de más de 100 años
    m = base / "2021" / "Septiembre.csv 2 1"
    _write(
        m / "Cabecera - Características generales (persona).csv",
        "DIRECTORIO SECUENCIA_P ORDEN P6040 FEX_C_2011\n30 1 1 40 250.5\n",
    )
    _write(
        m / "Cabecera - Ocupados.csv",
        "DIRECTORIO SECUENCIA_P ORDEN OCI FEX_C_2011\n30 1 1 1 250.5\n",
    )
    m = base / "2021" / "Septiembre"
    m.mkdir(parents=True)
    llaves = {
        "DIRECTORIO": [30, 30],
        "SECUENCIA_P": [1, 1],
        "ORDEN": [1, 2],
        "fex_c_2011": [250.5, 250.5],
    }
    _stata_110(
        m / "Cabecera - Características generales (Personas).dta",
        {
            **llaves,
            "P6020": [1, 2],
            "P6040": [101, 38],
            "CLASE": [1, 1],
            "DPTO": [11, 11],
            "P7260": [None, 104],
        },
    )
    _stata_110(
        m / "Cabecera - Ocupados.dta",
        {k: v[:1] for k, v in llaves.items()} | {"OCI": [1], "INGLABO": [3000000]},
    )
    _stata_110(
        m / "Cabecera - Desocupados.dta", {k: v[1:] for k, v in llaves.items()} | {"DSI": [1]}
    )
    _stata_110(m / "Cabecera - Fuerza de trabajo.dta", llaves)
    for modulo in (
        "Características generales (Personas)",
        "Ocupados",
        "Desocupados",
        "Fuerza de trabajo",
    ):
        _stata_110(m / f"Resto - {modulo}.dta", {k: [] for k in llaves})  # el resto, vacío

    # --- Mes incompleto (sin desocupados)
    m = base / "2025" / "Febrero 2025"
    _write(
        m / "Características generales, seguridad social en salud y educación.CSV",
        car + "202502;2;10;1;1;2;35;1;1;10;1;76;1000;;\n",
    )
    _write(
        m / "Fuerza de trabajo.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;PET;FEX_C18\n10;1;1;1;1000\n"
    )
    _write(m / "Ocupados.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;OCI;FEX_C18\n10;1;1;1;1000\n")
    return root


@pytest.fixture
def eam_root(tmp_path):
    root = tmp_path / "eam"
    d = root / "datos"
    _write(
        d / "1992" / "EAM_1992.csv",
        "nordemp;nordest;DPTO;CIIU2N4;periodo;PRODBR2;CONSIN2;VALAGRI;PERTOTAL;PPERYTEM;SALPEYTE;"
        "PRESPYTE\n"
        "1;10;5;311;1992;100;60;40;10;8;10;2\n"
        "2;20;11;38;1992;50;30;20;5;5;5;1\n",
    )
    _write(
        d / "2016" / "EAM_2016.csv",
        "nordemp;nordest;dpto;ciiu4;periodo;PRODBR2;CONSIN2;VALAGRI;PERTOTAL;PPERYTEM;SALPEYTE;"
        "PRESPYTE\n"
        "1;10;5;1011;2016;200;120;80;12;10;20;4\n"
        "3;30;76;110;2016;90;50;40;6;6;8;2\n",
    )
    _write(
        d / "2024" / "EAM_ANONIMIZADA_2024.txt",
        "nordemp\tnordest\tdpto\tciiu4\tperiodo\tPRODBR2\tCONSIN2\tVALAGRI\tPERTOTAL\tPPERYTEM\t"
        "SALPEYTE\tPRESPYTE\n"
        "1.0\t10.0\t5.0\t1011.0\t2024.0\t300\t180\t120\t15\t12\t30\t6\n",
    )
    return root


@pytest.fixture
def eevv_root(tmp_path):
    """Un archivo por cada época de las Estadísticas Vitales, con las rarezas que tiene el real."""
    root = tmp_path / "eevv"
    d = root / "datos"

    # --- 1979: mayúsculas, tabulador, sin AREA_RES, CIE-9 sin letras, 83 = Caquetá, 01 =
    # residencia sin información
    cab = (
        "COD_DPTO\tCOD_MUNIC\tA_DEFUN\tANO\tMES\tSEXO\tGRU_ED1\tEST_CIVIL\tCODPTORE\tCODMUNRE\t"
        "SIT_DEFUN\tC_BAS1\tCONS_EXP\tCAU_HOMOL\n"
    )
    _write(
        d / "defunciones" / "1979" / "Defun1979.txt",
        cab + "83\t001\t1\t1979\t01\t2\t05\t1\t83\t001\t2\t0090\t2\t001\n"
        "05\t001\t2\t1979\t02\t1\t10\t4\t01\t001\t1\t7651\t1\t080\n"
        "05\t002\t3\t1979\t03\t1\t25\t5\t05\t002\t4\t7999\t1\t104\n",
    )
    # --- 1991: minúsculas; en enero–junio las edades de menores de 10 años van en 6, 7 y 8
    cab = cab.lower()
    _write(
        d / "defunciones" / "1991" / "Defun1991.txt",
        cab + "05\t001\t1\t1991\t03\t1\t07\t1\t05\t001\t1\t7650\t1\t080\n"
        "05\t001\t1\t1991\t09\t1\t07\t1\t05\t001\t1\t0090\t1\t001\n"
        "05\t001\t1\t1991\t03\t2\t24\t2\t05\t001\t2\t4100\t1\t051\n",
    )
    # --- 1998: Latin-1, 26 grupos de edad, manera de muerte en dos variables, lista 6/66
    _write(
        d / "defunciones" / "1998" / "Defunciones 1998.txt",
        "cod_dpto\tcod_munic\ta_defun\tsit_defun\tnom_inst\tano\tmes\tsexo\test_civil\tgru_ed1\t"
        "gru_ed2\tnivel_edu\tcodptore\tcodmunre\tarea_res\tseg_social\tpman_muer\tman_muer\t"
        "c_bas1\tcausa_666\tcau_homol\n"
        "11\t001\t1\t1\tCLÍNICA\t1998\t04\t1\t1\t11\t04\t2\t11\t001\t1\t4\t2\t2\tX954\t512\t101\n"
        "27\t006\t3\t3\t\t1998\t4\t2\t5\t06\t01\t8\t75\t\t\t9\t1\t\tI219\t307\t051\n"
        "27\t006\t2\t3\t\t1998\t5\t2\t9\t26\t07\t9\t27\t006\t9\t3\t3\t\tR99X\t700\t104\n",
        encoding="latin-1",
    )
    # --- 2025: CSV con comillas, Latin-1, 30 grupos de edad, P_PMAN_IRIS, residencia en blanco
    _write(
        d / "defunciones" / "2025" / "BD-EEVV-Defuncionesnofetales-2025.csv",
        "COD_DPTO,COD_MUNIC,A_DEFUN,SIT_DEFUN,OTRSITIODE,ANO,MES,SEXO,EST_CIVIL,GRU_ED1,GRU_ED2,"
        "NIVEL_EDU,IDPERTET,CODPTORE,CODMUNRE,AREA_RES,SEG_SOCIAL,P_PMAN_IRIS,C_BAS1,CAUSA_667,"
        "CAU_HOMOL\n"
        '"19","001","1","1","","2025","12","2","6","14","04","09","1","19","001","1","2",'
        '"0","O149","612","078"\n'
        '"08","634","1","6","MORGUE DE '
        'SABANAGRANDE","2025","11","1","9","01","01","13","6","","","","1","1","X954",'
        '"512","101"\n'
        '"05","001","2","3","","2025","01","1","5","28","06","99","9","05","001","2","5",'
        '"4","X700","511","100"\n',
        encoding="latin-1",
    )

    # --- Nacimientos 1998: tabulador, sin T_GES_AGRU_CIE
    _write(
        d / "nacimientos" / "1998" / "Nacimientos_1998.txt",
        "cod_dpto\tcod_munic\tareanac\tsit_parto\tsexo\tpeso_nac\tano\tmes\taten_par\tt_ges\t"
        "numconsul\ttipo_parto\tmul_parto\tedad_madre\test_civm\tniv_edum\tcodptore\tcodmunre\t"
        "area_res\tn_hijosv\tn_emb\tseg_social\tedad_padre\n"
        "27\t006\t1\t1\t1\t4\t1998\t11\t1\t4\t03\t2\t1\t2\t1\t3\t27\t006\t1\t1\t1\t4\t25\n"
        "11\t001\t1\t1\t2\t6\t1998\t06\t1\t4\t99\t1\t2\t3\t2\t8\t11\t001\t9\t99\t99\t9\t99\n",
    )
    # --- Nacimientos 2025: CSV, UTF-8 con BOM, T_GES_AGRU_CIE
    _write(
        d / "nacimientos" / "2025" / "BD-EEVV-Nacimientos-2025.csv",
        "COD_DPTO,COD_MUNIC,AREANAC,SIT_PARTO,SEXO,PESO_NAC,ANO,MES,ATEN_PAR,T_GES,T_GES_AGRU_CIE,"
        "NUMCONSUL,TIPO_PARTO,MUL_PARTO,IDPERTET,EDAD_MADRE,EST_CIVM,NIV_EDUM,CODPTORE,CODMUNRE,"
        "AREA_RES,N_HIJOSV,N_EMB,SEG_SOCIAL,EDAD_PADRE\n"
        '"85","250","1","1","1",6,"2025","11","1",3,"4","02","1","1","6",4,"1","03","85",'
        '"125","3",5,5,"2",40\n'
        '"13","001","1","1","2",3,"2025","10","1",3,"3","04","2","2","6",2,"6","09","13",'
        '"001","1",1,1,"2",20\n'
        '"13","001","1","1","3",9,"2025","10","9",9,"9","99","9","9","9",99,"9","99","",'
        '"","",99,99,"9",99\n',
    )

    # --- Fetales 1998: Latin-1 y N_HIJOSM con texto en vez de códigos
    _write(
        d / "fetales" / "1998" / "fetal1998.txt",
        "cod_dpto\tcod_munic\ta_defun\tsit_defun\tano\tmes\tsexo\tcodptore\tcodmunre\tarea_res\t"
        "seg_social\tt_ges\tpeso_nac\tedad_madre\tn_hijosm\test_civm\tniv_edum\tc_bas1\t"
        "causa_666\tcau_homol\n"
        "68\t755\t1\t1\t1998\t8\t1\t68\t755\t1\t3\t3\t1\t2\tNúmero de hijos nacidos muertos\t1\t"
        "7\tP018\t\t080\n"
        "13\t001\t1\t3\t1998\t1\t3\t13\t001\t1\t9\t4\t9\t99\tSin información\t9\t9\tP018\t\t"
        "080\n",
        encoding="latin-1",
    )
    # --- Fetales 2009: NIV_EDUM no sigue el DDI
    _write(
        d / "fetales" / "2009" / "fetal2009.csv",
        "COD_DPTO,COD_MUNIC,A_DEFUN,SIT_DEFUN,ANO,MES,SEXO,CODPTORE,CODMUNRE,AREA_RES,SEG_SOCIAL,"
        "T_GES,T_GES_AGRU_CIE,PESO_NAC,EDAD_MADRE,EST_CIVM,NIV_EDUM,C_BAS1,CAUSA_666,CAUSA_667,"
        "CAU_HOMOL\n"
        "11,001,1,3,2009,06,3,11,001,1,1,1,1,1,2,5,9,P018,402,402,080\n",
    )
    # --- Fetales 2025: el régimen de salud pasa de SEG_SOCIAL a REGSOCIALMADRE
    _write(
        d / "fetales" / "2025" / "BD-EEVV-Defuncionesfetales-2025.csv",
        "COD_DPTO,COD_MUNIC,A_DEFUN,SIT_DEFUN,ANO,MES,SEXO,CODPTORE,CODMUNRE,AREA_RES,"
        "REGSOCIALMADRE,T_GES,T_GES_AGRU_CIE,PESO_NAC,EDAD_MADRE,EST_CIVM,NIV_EDUM,C_BAS1,"
        "CAUSA_667,CAU_HOMOL\n"
        '"68","755","1","1","2025","12","1","68","755","1","2",4,"4",6,4,"6","09","P018",'
        '"402","080"\n',
    )
    return root


@pytest.fixture
def emicron_root(tmp_path):
    """Tres micronegocios por año de la EMICRON, con las rarezas que tiene el real."""
    root = tmp_path / "emicron"
    d = root / "datos"
    rep = "CLASE_TE,COD_DEPTO,AREA,F_EXP"  # lo que repiten los módulos

    # --- 2019: punto y coma, coma decimal, CLASE (no CLASE_TE), meses con mayúsculas mezcladas,
    # sin derivadas
    _write(
        d / "2019" / "identificacion.csv",
        "﻿DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;COD_DEPTO;AREA;CLASE;P35;P241;MES_REF;P3031;"
        "P3032_1;P3032_2;P3032_3;P3033;P3034;GRUPOS4;GRUPOS12;F_EXP\n"
        "1;1;1;76;76;1;1;40;ENERO;1;2; ; ;1;14;04;12;295,5\n"
        "2;1;1;5; ;2;2;35;octubre;2;0;0;0;2;100;01;01;100,25\n"
        "3;2;1;11;11;1;2;52;Diciembre;1;0;1;1;2;30;03;05;50\n",
    )
    _write(
        d / "2019" / "propietario.csv",
        "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;P3088;P3089\n"
        "1;1;1;1;100000\n"
        "2;1;1;2; \n"
        "3;2;1;3;5000\n",
    )
    _write(
        d / "2019" / "ventas.csv",
        "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;VENTAS_MES_ANTERIOR;P3057\n"
        "1;1;1;1000000;5\n"
        "2;1;1;500000,5;0\n"
        "3;2;1;0;0\n",
    )
    _write(
        d / "2019" / "fex_ajustado.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,FEX_C\n1,1,1,250.0\n2,1,1,90.5\n3,1,2,45.0\n",
    )
    _write(
        d / "2019" / "fex_dpto.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,FEX_MICRO_DPTO\n"
        "1,1,1,260\n"
        "2,1,1,95\n"
        "3,1,2,40\n"
        "9,1,1,7\n",
    )

    # --- 2021: inclusión financiera con FEX_C y sin uno de los micronegocios; factor departamental
    # con una clave repetida y vacía (como 2020)
    _write(
        d / "2021" / "identificacion.csv",
        "DIRECTORIO;SECUENCIA_P;SECUENCIA_ENCUESTA;COD_DEPTO;AREA;CLASE_TE;P35;P241;MES_REF;"
        "P3031;P3032_1;P3032_2;P3032_3;P3033;GRUPOS4;GRUPOS12;F_EXP\n"
        "10;1;1;8;8;1;2;28;MARZO;1;1;0;0;1;03;05;300,0\n"
        "11;1;1;13; ;2;1;61;JULIO;2; ; ; ;2;02;03;200,0\n"
        "12;1;1;68;68;1;1;45;AGOSTO;2; ; ; ;2;04;07;100,0\n",
    )
    _write(
        d / "2021" / "inclusion_financiera.csv",
        "DIRECTORIO;SECUENCIA_P;SECUENCIA_ENCUESTA;P1765;CLASE_TE;FEX_C\n"
        "10;1;1;1;1;300\n"
        "11;1;1;2;2;200\n",
    )
    _write(
        d / "2021" / "fex_ajustado.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,FEX_C\n10,1,1,260\n11,1,1,180\n12,1,1,90\n",
    )
    _write(
        d / "2021" / "fex_dpto.csv",
        "DIRECTORIO;SECUENCIA_P;SECUENCIA_ENCUESTA;FEX_MICRO_DPTO\n"
        "10;1;1;270\n"
        "11;1;1;170\n"
        "12;1;1;95\n"
        "99;1;1.0;\n"
        "99;1;1.0;\n",
    )

    # --- 2024: comas; FEX_C es el factor departamental; personal ocupado con la clave corrida
    _write(
        d / "2024" / "identificacion.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,COD_DEPTO,AREA,CLASE_TE,P35,P241,MES_REF,"
        "P3031,P3032_1,P3032_2,P3032_3,P3033,GRUPOS4,GRUPOS12,F_EXP\n"
        "20,1,1,11,11,1,1,50,ENERO,1,1,1,0,1,04,10,1000.5\n"
        "21,2,3,47,47,1,2,33,JUNIO,2,,,,2,03,05,500\n"
        "22,1,1,52,,2,1,70,DICIEMBRE,1,0,0,2,2,01,01,250\n",
    )
    _write(
        d / "2024" / "caracteristicas.csv",
        f"DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,P1633,P1055,{rep}\n"
        "20,1,1,1,1,1,11,11,1000.5\n"
        "21,2,3,2,2,1,47,47,500\n"
        "22,1,1,1,2,2,52,,250\n",
    )
    _write(
        d / "2024" / "propietario.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,P3088,SUELDOS,PRESTACIONES,"
        f"REMUNERACION_TOTAL,{rep}\n"
        "20,1,1,1,1200000,300000,1500000,1,11,11,1000.5\n"
        "21,2,3,2,0,0,0,1,47,47,500\n"
        "22,1,1,4,0,0,0,2,52,,250\n",
    )
    _write(
        d / "2024" / "sitio.csv",
        f"DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,P3053,{rep}\n"
        "20,1,1,2,1,11,11,1000.5\n"
        "21,2,3,4,1,47,47,500\n"
        "22,1,1,7,2,52,,250\n",
    )
    _write(
        d / "2024" / "costos.csv",
        f"DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,CONSUMO_INTERMEDIO,{rep}\n"
        "20,1,1,2000000,1,11,11,1000.5\n"
        "21,2,3,300000,1,47,47,500\n"
        "22,1,1,100000,2,52,,250\n",
    )
    _write(
        d / "2024" / "ventas.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,VENTAS_MES_ANTERIOR,VALOR_AGREGADO,"
        f"INGRESO_MIXTO,{rep}\n"
        "20,1,1,5000000,3000000,1500000,1,11,11,1000.5\n"
        "21,2,3,800000,500000,500000,1,47,47,500\n"
        "22,1,1,300000,200000,200000,2,52,,250\n",
    )
    _write(
        d / "2024" / "personal_ocupado.csv",
        f"DIRECTORIO,SECUENCIA_PH,SECUENCIA_P,SECUENCIA_ENCUESTA,TIPO,P3077,{rep}\n"
        "20,1,1,1,1,1,1,11,11,1000.5\n"
        "20,1,1,2,2,,1,11,11,1000.5\n"
        "22,1,1,1,3,,2,52,,250\n"
        "22,1,1,2,3,,2,52,,250\n",
    )
    _write(
        d / "2024" / "fex_dpto.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,FEX_C\n20,1,1,990\n21,2,3,510\n22,1,1,240\n",
    )

    # --- 2025: solo las 24 ciudades
    _write(
        d / "2025" / "identificacion.csv",
        "DIRECTORIO,SECUENCIA_P,SECUENCIA_ENCUESTA,COD_DEPTO,AREA,CLASE_TE,P35,P241,MES_REF,"
        "P3032_1,P3032_2,P3032_3,P3033,GRUPOS4,GRUPOS12,F_EXP,SEGMENTO,DOMINIO\n"
        "30,1,1,5,5,1,2,44,MAYO,0,0,0,2,03,05,700,1,1\n",
    )
    return root


@pytest.fixture
def ecv_root(tmp_path):
    """
    La ECV con las rarezas del ANDA: en las tablas de hogar el hogar es SECUENCIA_ENCUESTA; 2018
    trae DPTO y los factores del CNPV 2018 aparte; 2020 no trae REGION; 2025 con encabezados en
    minúscula y coma decimal.
    """
    root = tmp_path / "ecv"
    d = root / "datos"
    viv = "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;ORDEN;{geo};FEX_C;CLASE;P4005;P4015\n"
    hog = "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;ORDEN;FEX_C;P5000;P5010\n"
    per = "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;ORDEN;FEX_C;P6020;P6040;P6051;P6080\n"

    # --- 2025: la vivienda 1 (Bogotá, cabecera) tiene dos hogares; la 2 es de Antioquia, rural
    _write(
        d / "2025" / "vivienda" / "Datos de la vivienda.csv",
        viv.format(geo="P1_DEPARTAMENTO;REGION").lower()
        + "1;1;1;1;11;5;100,5;1;1;2\n2;1;1;1;5;6;20;2;3;1\n",
    )
    _write(
        d / "2025" / "servicios" / "Servicios del hogar.csv",
        hog.lower() + "1;1;1;1;100,5;3;2\n1;2;1;1;100,5;1;1\n2;1;1;1;20;2;1\n",
    )
    _write(
        d / "2025" / "caracteristicas" / "Características y composición del hogar.csv",
        per.lower() + "1;1;1;1;100,5;1;45;1;6\n1;2;1;2;100,5;2;8;3;6\n1;1;2;1;100,5;2;70;1;5\n"
        "2;1;1;1;20;1;30;1;1\n2;2;1;2;20;2;29;2;1\n",
    )
    # Falta una persona
    _write(
        d / "2025" / "salud" / "Salud.csv",
        "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;ORDEN;FEX_C;P6090\n"
        "1;1;1;1;100,5;1\n1;2;1;2;100,5;2\n1;1;2;1;100,5;1\n2;1;1;1;20;9\n",
    )

    # --- 2018: DPTO, y el FEX_C de los capítulos no es el del CNPV 2018
    _write(
        d / "2018" / "vivienda" / "Datos de la vivienda.csv",
        viv.format(geo="REGION;DPTO") + "7;1;1;1;2;11;9;2;2;3\n",
    )
    _write(d / "2018" / "servicios" / "Servicios del hogar.csv", hog + "7;1;1;1;9;2;1\n")
    _write(
        d / "2018" / "caracteristicas" / "Caracteristicas y composicion del hogar.csv",
        per + "7;1;1;1;9;2;33;1;6\n",
    )
    _write(
        d / "2018" / "factores" / "Factores de expansión 2018 basados en el CNPV 2018.csv",
        "DIRECTORIO;FEX_C\n7;5,5\n",
    )

    # --- 2020: sin REGION; la parte rural de Bogotá es de la región Oriental
    _write(
        d / "2020" / "vivienda" / "Datos de la vivienda.csv",
        viv.format(geo="P1_DEPARTAMENTO") + "9;1;1;1;11;4;2;1;1\n",
    )
    _write(d / "2020" / "servicios" / "Servicios del hogar.csv", hog + "9;1;1;1;4;1;1\n")
    _write(
        d / "2020" / "caracteristicas" / "Caracteristicas y composicion del hogar.csv",
        per + "9;1;1;1;4;1;60;1;6\n",
    )
    return root


@pytest.fixture
def ecv_completo(tmp_path):
    """
    Un año de la ECV (2025) con los once capítulos y las variables de los indicadores y del IPM:
    dos hogares de Bogotá, uno de una mujer de 70 años que no sabe leer, sin salud y con piso de
    tierra (pobre) y otro de una pareja que trabaja y un hijo.
    """
    d = tmp_path / "ecv_completo" / "datos" / "2025"
    llaves = "DIRECTORIO;SECUENCIA_ENCUESTA;SECUENCIA_P;ORDEN;FEX_C"
    _write(
        d / "vivienda" / "Datos de la vivienda.csv",
        f"{llaves};P1_DEPARTAMENTO;REGION;CLASE;P4005;P4015;P8520S1;P8520S3;P8520S4;P8520S5\n"
        "1;1;1;1;100;11;5;1;1;4;1;1;1;1\n"
        "2;1;1;1;50;11;5;1;1;7;1;1;1;1\n",
    )
    hogares = {
        "servicios": ("P5010;P8526;P8530;P5666", ["2;1;1;1", "1;1;1;2"]),
        "condiciones": ("P1075;P5230", ["1;2", "2;1"]),
        "tenencia": ("P5095", ["3", "1"]),
    }
    for modulo, (columnas, filas) in hogares.items():
        _write(
            d / modulo / f"{modulo}.csv",
            f"{llaves};{columnas}\n" + f"1;1;1;1;100;{filas[0]}\n2;1;1;1;50;{filas[1]}\n",
        )
    columnas = (
        "P6020;P6040;P6051;P6080;P6090;P6100;P5665;P8563;P51;P55;P774;P6160;P8586;P8587;P8587S1;"
        "P6211;P1088;P1088S1;P6216;P6180;P6240;P6250;P6260;P6270;P6351;P7250;P6920;P1910;P1911;"
        "P1912;P1084;P1082;P5504"
    )
    _write(
        d / "caracteristicas" / "Características y composición del hogar.csv",
        f"{llaves};{columnas}\n"
        "1;1;1;1;100;2;40;1;6;1;1;2;;;;;1;2;5;11;;;;;;1;;;;;;1;5;1;5;1;1;\n"
        "1;2;1;2;100;1;42;2;6;1;1;2;;;;;1;2;5;11;;;;;;1;;;;;;1;5;5;5;2;1;\n"
        "1;3;1;3;100;1;10;3;6;1;3;2;;;;;1;1;;;;2;5;;;3;;;;;;;5;5;5;5;2;1\n"
        "2;1;1;1;50;2;70;1;6;2;;2;;;;;2;2;3;3;;;;;;5;;;;;;2;5;5;5;5;2;2\n",
    )
    for modulo in (
        "salud",
        "primera_infancia",
        "educacion",
        "fuerza_trabajo",
        "tic",
        "trabajo_infantil",
    ):
        _write(d / modulo / f"{modulo}.csv", f"{llaves}\n1;1;1;1;100\n")
    return tmp_path / "ecv_completo"


# --------------------------------------------------------------------------- #
# Pobreza monetaria: tres hogares por año con las rarezas de cada época del DANE
# --------------------------------------------------------------------------- #
# Tres hogares por año: (DIRECTORIO, SECUENCIA_P, MES, CLASE, DOMINIO, DPTO, NPER, NPERSUG,
# INGPCUG, LI, LP, FEX_C)
_HOGARES = [
    (1, 1, 1, 1, "BOGOTA", 11, 4, 3, 150.0, 100.0, 200.0, 10.0),
    (2, 1, 1, 1, "MEDELLIN", 5, 2, 2, 250.0, 100.0, 200.0, 20.0),
    (3, 1, 2, 2, "RURAL", 25, 3, 3, 80.0, 90.0, 150.0, 30.0),
]


def _escribir(ruta, df, sep=";", decimal=","):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, sep=sep, decimal=decimal, index=False)


def _hogares_df(anio):
    # fmt: off
    df = pd.DataFrame(_HOGARES, columns=["Directorio", "Secuencia_p", "Mes", "Clase", "Dominio",
                      "Dpto", "Nper",
                                         "Npersug", "Ingpcug", "Li", "Lp", "Fex_c"])
    # fmt: on
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
        df["Dominio"] = df.Dominio.map(
            {"BOGOTA": "Bogotá", "MEDELLIN": "Medellín", "RURAL": "Rural"}
        )
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
    fex_g = pd.DataFrame(
        [(a, h[2], h[0], h[1], 0.5) for a in range(2012, 2021) for h in _HOGARES],
        columns=["año", "mes", "directorio", "secuencia_p", "FEX_G"],
    )
    _escribir(emp / "empalme_2012_2020.csv", fex_g, decimal=".")
    lineas = pd.DataFrame(
        [
            (a, 1, m, d, 60.0, 260.0)
            for a in range(2012, 2019)
            for m in (1, 2)
            for d in ("BOGOTA", "MEDELLIN", "RURAL")
        ],
        columns=["AÑO", "SEMESTRE", "MES", "DOMINIO", "LI", "LP"],
    )
    _escribir(emp / "lineas_2012_2018.csv", lineas)
    h21 = pd.DataFrame(
        [(h[2], h[0], h[1], h[8], 1.0, 40.0, h[8] * 2) for h in _HOGARES],
        columns=["MES", "DIRECTORIO", "SECUENCIA_P", "INGPCUG", "FAC_EMP", "FEX_C", "INGPCUG_EMP"],
    )
    _escribir(emp / "hogares_empalmado_2021.csv", h21)
    h21d = pd.DataFrame(
        [(h[2], h[0], h[1], h[8], h[8] * 3, 7.0, 1.0, h[5]) for h in _HOGARES],
        columns=[
            "MES",
            "DIRECTORIO",
            "SECUENCIA_P",
            "INGPCUG",
            "INGPUG_EMP",
            "FEX_DPTO",
            "FAC_EMP",
            "DPTO",
        ],
    )
    _escribir(emp / "hogares_empalmado_dpto_2021.csv", h21d)
    return root
