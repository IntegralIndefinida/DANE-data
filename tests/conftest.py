"""Datos sintéticos que imitan las rarezas de cada época de la GEIH, la EAM y las Estadísticas Vitales."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest


def _write(path: Path, text: str, encoding="utf-8-sig"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode(encoding))


def _stata_110(path: Path, columnas: dict):
    """Stata en formato 110 (Stata 7), como el de septiembre de 2021: pandas 2 no lo lee. ``None`` es faltante."""
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
        bytes([110, 2, 1, 0]) + nvar.to_bytes(2, "little") + nobs.to_bytes(4, "little")
        + bytes(81) + texto("01 Oct 2021 00:00", 18) + bytes(tipos)
        + b"".join(texto(n, 33) for n in columnas) + bytes(2 * (nvar + 1)) + texto("%9.0g", 12) * nvar
        + bytes(33 * nvar) + bytes(81 * nvar) + bytes(5) + filas.tobytes())


@pytest.fixture(autouse=True)
def sin_buscar_versiones(monkeypatch):
    """Las pruebas no consultan internet: el aviso de versión nueva se prueba con respuestas falsas."""
    monkeypatch.setenv("DANE_DATA_SIN_ACTUALIZACIONES", "1")


@pytest.fixture
def geih_root(tmp_path):
    root = tmp_path / "geih"
    base = root / "datos_csv"

    # --- Época 2016: Area/Cabecera/Resto, ';', coma decimal, blancos " ", sin PET explícito
    m = base / "2016" / "Enero"
    car = "Directorio;Secuencia_p;Orden;P6020;P6040;P6050;P6090;P6210;Clase;Dpto;Fex_c_2011\n"
    _write(m / "Cabecera - Características generales (Personas).csv",
           car + "1;1;1;1;30;1;1;6;1;11;100,5\n1;1;2;2;28;2;1;5;1;11;100,5\n1;1;3;2;8;3; ;2;1;11;100,5\n"
                 "2;1;1;1;45;1;1;3;1;5;200,0\n")
    _write(m / "Resto - Características generales (Personas).csv", car + "3;1;1;2;50;1;2;3;2;5;300,25\n")
    # Area es subconjunto de Cabecera: no debe sumarse
    _write(m / "Area - Características generales (Personas).csv", car + "1;1;1;1;30;1;1;6;1;11;100,5\n")
    ft = "Directorio;Secuencia_p;Orden;Fex_c_2011\n"
    _write(m / "Cabecera - Fuerza de trabajo.csv", ft + "1;1;1;100,5\n1;1;2;100,5\n2;1;1;200,0\n")
    _write(m / "Resto - Fuerza de trabajo.csv", ft + "3;1;1;300,25\n")
    # P6870 y OFICIO: la medición de informalidad del marco 2005 (asalariado en una empresa grande, formal;
    # cuenta propia solo, que no es profesional, informal)
    oc = "Directorio;Secuencia_p;Orden;Oci;Inglabo;P6920;P6430;P6800;Rama2d;P6870;Oficio;Fex_c_2011\n"
    _write(m / "Cabecera - Ocupados.csv", oc + "1;1;1;1;2000000;1;1;48;15;9;13;100,5\n2;1;1;1;500000;2;4;30;52;1;33;200,0\n")
    _write(m / "Resto - Ocupados.csv", oc)
    _write(m / "Cabecera - Desocupados.csv", "Directorio;Secuencia_p;Orden;Dsi;Fex_c_2011\n1;1;2;1;100,5\n")
    _write(m / "Resto - Inactivos.csv", "Directorio;Secuencia_p;Orden;Ini;Fex_c_2011\n3;1;1;1;300,25\n")
    # Cada módulo trae las dos partes, aunque una esté vacía (sin una, el mes queda incompleto)
    _write(m / "Resto - Desocupados.csv", "Directorio;Secuencia_p;Orden;Dsi;Fex_c_2011\n")
    _write(m / "Cabecera - Inactivos.csv", "Directorio;Secuencia_p;Orden;Ini;Fex_c_2011\n")
    # Carpeta que no es un mes (debe ignorarse)
    (base / "2016" / "Total_fact_exp_dto").mkdir(parents=True)

    # --- Época 2025: archivos únicos, PET/FFT/DSI en 'No ocupados', FEX_C18, latin-1, en subcarpeta
    m = base / "2025" / "Enero 2025"
    car = "PERIODO;MES;DIRECTORIO;SECUENCIA_P;ORDEN;P3271;P6040;P6050;P6090;P3042;CLASE;DPTO;FEX_C18;P6100;P6110\n"
    _write(m / "Características generales, seguridad social en salud y educación.CSV",
           car + "202501;1;10;1;1;2;35;1;1;10;1;76;1000.5;1;1\n202501;1;10;1;2;1;20;3;1;6;1;76;1000.5;3;\n"
                 "202501;1;11;1;1;1;70;1;1;3;2;76;500;1;5\n", encoding="latin-1")
    _write(m / "Fuerza de trabajo.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;PET;FT;FFT;FEX_C18\n"
                                        "10;1;1;1;1;;1000.5\n10;1;2;1;1;;1000.5\n11;1;1;1;;1;500\n")
    # Con las preguntas de la medición de informalidad del DANE: asalariada con salud y pensión pagadas por
    # la empresa (formal)
    _write(m / "Ocupados.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;OCI;INGLABO;P6920;P6430;P6800;RAMA2D_R4;FEX_C18;"
                               "OFICIO_C8;P3045S1;P3046;P3069;P6765;P3065;P3066;P3067;P3067S1;P3067S2;P6775;"
                               "P3068;P6450;P6930;P6940\n"
                               "10;1;1;1;1423500;1;1;48;10;1000.5;5223;1;1;3;;;;;;;;;2;1;1\n")
    _write(m / "CSV 13" / "No ocupados.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;DSI;FFT;FEX_C18\n"
                                             "10;1;2;1;;1000.5\n11;1;1;;1;500\n")
    _write(m / "Datos del hogar y la vivienda.CSV", "DIRECTORIO;SECUENCIA_P;P5000;FEX_C18\n10;1;4;1000.5\n11;1;2;500\n")

    # --- 2011: el CSV del ANDA perdió el punto decimal del factor; el TXT del mismo catálogo está bien
    for carpeta, sep, fex in (("Marzo_csv", ";", ("849.491.032.387.525", "107.845.157.267.357")),
                              ("Marzo_txt", "\t", ("84.9491032387525", "1078.45157267357"))):
        m = base / "2011" / carpeta
        ext = carpeta[-3:]
        fila = lambda *v: sep.join(map(str, v)) + "\n"  # noqa: E731
        _write(m / f"Cabecera - Características generales (Personas).{ext}",
               fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "P6020", "P6040", "CLASE", "DPTO", "fex_c_2011")
               + fila(20, 1, 1, 1, 30, 1, 5, fex[0]) + fila(20, 1, 2, 2, 25, 1, 5, fex[0])
               + fila(21, 1, 1, 2, 40, 1, 5, fex[1]))
        _write(m / f"Cabecera - Ocupados.{ext}", fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "OCI", "INGLABO", "fex_c_2011")
               + fila(20, 1, 1, 1, 1000000, fex[0]) + fila(21, 1, 1, 1, 2000000, fex[1]))
        _write(m / f"Cabecera - Desocupados.{ext}", fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "DSI", "fex_c_2011")
               + fila(20, 1, 2, 1, fex[0]))
        _write(m / f"Cabecera - Fuerza de trabajo.{ext}", fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "fex_c_2011")
               + fila(20, 1, 1, fex[0]) + fila(20, 1, 2, fex[0]) + fila(21, 1, 1, fex[1]))
        for modulo, marca in (("Características generales (Personas)", "P6040"), ("Ocupados", "OCI"),
                              ("Desocupados", "DSI"), ("Fuerza de trabajo", None)):  # el resto, vacío
            _write(m / f"Resto - {modulo}.{ext}", fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", *filter(None, [marca]),
                                                       "fex_c_2011"))
        # Febrero de 2011: "Otras actividades" trae otro factor (FEX_C) que no debe reemplazar al de características
        _write(m / f"Cabecera - Otras actividades y ayudas en la semana.{ext}",
               fila("DIRECTORIO", "SECUENCIA_P", "ORDEN", "FEX_C") + fila(20, 1, 1, 999) + fila(20, 1, 2, 999))

    # --- Septiembre 2021: el CSV viene separado por espacios (ilegible); el Stata está bien, pero en
    # formato 110 (Stata 7), con edades de más de 100 años
    m = base / "2021" / "Septiembre.csv 2 1"
    _write(m / "Cabecera - Características generales (persona).csv",
           "DIRECTORIO SECUENCIA_P ORDEN P6040 FEX_C_2011\n30 1 1 40 250.5\n")
    _write(m / "Cabecera - Ocupados.csv", "DIRECTORIO SECUENCIA_P ORDEN OCI FEX_C_2011\n30 1 1 1 250.5\n")
    m = base / "2021" / "Septiembre"
    m.mkdir(parents=True)
    llaves = {"DIRECTORIO": [30, 30], "SECUENCIA_P": [1, 1], "ORDEN": [1, 2], "fex_c_2011": [250.5, 250.5]}
    _stata_110(m / "Cabecera - Características generales (Personas).dta",
               {**llaves, "P6020": [1, 2], "P6040": [101, 38], "CLASE": [1, 1], "DPTO": [11, 11], "P7260": [None, 104]})
    _stata_110(m / "Cabecera - Ocupados.dta", {k: v[:1] for k, v in llaves.items()} | {"OCI": [1], "INGLABO": [3000000]})
    _stata_110(m / "Cabecera - Desocupados.dta", {k: v[1:] for k, v in llaves.items()} | {"DSI": [1]})
    _stata_110(m / "Cabecera - Fuerza de trabajo.dta", llaves)
    for modulo in ("Características generales (Personas)", "Ocupados", "Desocupados", "Fuerza de trabajo"):
        _stata_110(m / f"Resto - {modulo}.dta", {k: [] for k in llaves})  # el resto, vacío

    # --- Mes incompleto (sin desocupados)
    m = base / "2025" / "Febrero 2025"
    _write(m / "Características generales, seguridad social en salud y educación.CSV", car + "202502;2;10;1;1;2;35;1;1;10;1;76;1000;;\n")
    _write(m / "Fuerza de trabajo.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;PET;FEX_C18\n10;1;1;1;1000\n")
    _write(m / "Ocupados.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;OCI;FEX_C18\n10;1;1;1;1000\n")
    return root


@pytest.fixture
def eam_root(tmp_path):
    root = tmp_path / "eam"
    d = root / "datos"
    _write(d / "1992" / "EAM_1992.csv", "nordemp;nordest;DPTO;CIIU2N4;periodo;PRODBR2;CONSIN2;VALAGRI;PERTOTAL;"
                                        "PPERYTEM;SALPEYTE;PRESPYTE\n1;10;5;311;1992;100;60;40;10;8;10;2\n"
                                        "2;20;11;38;1992;50;30;20;5;5;5;1\n")
    _write(d / "2016" / "EAM_2016.csv", "nordemp;nordest;dpto;ciiu4;periodo;PRODBR2;CONSIN2;VALAGRI;PERTOTAL;"
                                        "PPERYTEM;SALPEYTE;PRESPYTE\n1;10;5;1011;2016;200;120;80;12;10;20;4\n"
                                        "3;30;76;110;2016;90;50;40;6;6;8;2\n")
    _write(d / "2024" / "EAM_ANONIMIZADA_2024.txt", "nordemp\tnordest\tdpto\tciiu4\tperiodo\tPRODBR2\tCONSIN2\t"
                                                    "VALAGRI\tPERTOTAL\tPPERYTEM\tSALPEYTE\tPRESPYTE\n"
                                                    "1.0\t10.0\t5.0\t1011.0\t2024.0\t300\t180\t120\t15\t12\t30\t6\n")
    return root


@pytest.fixture
def eevv_root(tmp_path):
    """Un archivo por cada época de las Estadísticas Vitales, con las rarezas que tiene el real."""
    root = tmp_path / "eevv"
    d = root / "datos"

    # --- 1979: mayúsculas, tabulador, sin AREA_RES, CIE-9 sin letras, 83 = Caquetá, 01 = residencia sin información
    cab = "COD_DPTO\tCOD_MUNIC\tA_DEFUN\tANO\tMES\tSEXO\tGRU_ED1\tEST_CIVIL\tCODPTORE\tCODMUNRE\tSIT_DEFUN\tC_BAS1\tCONS_EXP\tCAU_HOMOL\n"
    _write(d / "defunciones" / "1979" / "Defun1979.txt",
           cab + "83\t001\t1\t1979\t01\t2\t05\t1\t83\t001\t2\t0090\t2\t001\n"
                 "05\t001\t2\t1979\t02\t1\t10\t4\t01\t001\t1\t7651\t1\t080\n"
                 "05\t002\t3\t1979\t03\t1\t25\t5\t05\t002\t4\t7999\t1\t104\n")
    # --- 1991: minúsculas; en enero–junio las edades de menores de 10 años van en 6, 7 y 8
    cab = cab.lower()
    _write(d / "defunciones" / "1991" / "Defun1991.txt",
           cab + "05\t001\t1\t1991\t03\t1\t07\t1\t05\t001\t1\t7650\t1\t080\n"
                 "05\t001\t1\t1991\t09\t1\t07\t1\t05\t001\t1\t0090\t1\t001\n"
                 "05\t001\t1\t1991\t03\t2\t24\t2\t05\t001\t2\t4100\t1\t051\n")
    # --- 1998: Latin-1, 26 grupos de edad, manera de muerte en dos variables, lista 6/66
    _write(d / "defunciones" / "1998" / "Defunciones 1998.txt",
           "cod_dpto\tcod_munic\ta_defun\tsit_defun\tnom_inst\tano\tmes\tsexo\test_civil\tgru_ed1\tgru_ed2\tnivel_edu\tcodptore\t"
           "codmunre\tarea_res\tseg_social\tpman_muer\tman_muer\tc_bas1\tcausa_666\tcau_homol\n"
           "11\t001\t1\t1\tCLÍNICA\t1998\t04\t1\t1\t11\t04\t2\t11\t001\t1\t4\t2\t2\tX954\t512\t101\n"
           "27\t006\t3\t3\t\t1998\t4\t2\t5\t06\t01\t8\t75\t\t\t9\t1\t\tI219\t307\t051\n"
           "27\t006\t2\t3\t\t1998\t5\t2\t9\t26\t07\t9\t27\t006\t9\t3\t3\t\tR99X\t700\t104\n",
           encoding="latin-1")
    # --- 2025: CSV con comillas, Latin-1, 30 grupos de edad, P_PMAN_IRIS, residencia en blanco
    _write(d / "defunciones" / "2025" / "BD-EEVV-Defuncionesnofetales-2025.csv",
           "COD_DPTO,COD_MUNIC,A_DEFUN,SIT_DEFUN,OTRSITIODE,ANO,MES,SEXO,EST_CIVIL,GRU_ED1,GRU_ED2,NIVEL_EDU,IDPERTET,CODPTORE,CODMUNRE,"
           "AREA_RES,SEG_SOCIAL,P_PMAN_IRIS,C_BAS1,CAUSA_667,CAU_HOMOL\n"
           '"19","001","1","1","","2025","12","2","6","14","04","09","1","19","001","1","2","0","O149","612","078"\n'
           '"08","634","1","6","MORGUE DE SABANAGRANDE","2025","11","1","9","01","01","13","6","","","","1","1","X954","512","101"\n'
           '"05","001","2","3","","2025","01","1","5","28","06","99","9","05","001","2","5","4","X700","511","100"\n',
           encoding="latin-1")

    # --- Nacimientos 1998: tabulador, sin T_GES_AGRU_CIE
    _write(d / "nacimientos" / "1998" / "Nacimientos_1998.txt",
           "cod_dpto\tcod_munic\tareanac\tsit_parto\tsexo\tpeso_nac\tano\tmes\taten_par\tt_ges\tnumconsul\ttipo_parto\tmul_parto\t"
           "edad_madre\test_civm\tniv_edum\tcodptore\tcodmunre\tarea_res\tn_hijosv\tn_emb\tseg_social\tedad_padre\n"
           "27\t006\t1\t1\t1\t4\t1998\t11\t1\t4\t03\t2\t1\t2\t1\t3\t27\t006\t1\t1\t1\t4\t25\n"
           "11\t001\t1\t1\t2\t6\t1998\t06\t1\t4\t99\t1\t2\t3\t2\t8\t11\t001\t9\t99\t99\t9\t99\n")
    # --- Nacimientos 2025: CSV, UTF-8 con BOM, T_GES_AGRU_CIE
    _write(d / "nacimientos" / "2025" / "BD-EEVV-Nacimientos-2025.csv",
           "COD_DPTO,COD_MUNIC,AREANAC,SIT_PARTO,SEXO,PESO_NAC,ANO,MES,ATEN_PAR,T_GES,T_GES_AGRU_CIE,NUMCONSUL,TIPO_PARTO,MUL_PARTO,"
           "IDPERTET,EDAD_MADRE,EST_CIVM,NIV_EDUM,CODPTORE,CODMUNRE,AREA_RES,N_HIJOSV,N_EMB,SEG_SOCIAL,EDAD_PADRE\n"
           '"85","250","1","1","1",6,"2025","11","1",3,"4","02","1","1","6",4,"1","03","85","125","3",5,5,"2",40\n'
           '"13","001","1","1","2",3,"2025","10","1",3,"3","04","2","2","6",2,"6","09","13","001","1",1,1,"2",20\n'
           '"13","001","1","1","3",9,"2025","10","9",9,"9","99","9","9","9",99,"9","99","","","",99,99,"9",99\n')

    # --- Fetales 1998: Latin-1 y N_HIJOSM con texto en vez de códigos
    _write(d / "fetales" / "1998" / "fetal1998.txt",
           "cod_dpto\tcod_munic\ta_defun\tsit_defun\tano\tmes\tsexo\tcodptore\tcodmunre\tarea_res\tseg_social\tt_ges\tpeso_nac\t"
           "edad_madre\tn_hijosm\test_civm\tniv_edum\tc_bas1\tcausa_666\tcau_homol\n"
           "68\t755\t1\t1\t1998\t8\t1\t68\t755\t1\t3\t3\t1\t2\tNúmero de hijos nacidos muertos\t1\t7\tP018\t\t080\n"
           "13\t001\t1\t3\t1998\t1\t3\t13\t001\t1\t9\t4\t9\t99\tSin información\t9\t9\tP018\t\t080\n", encoding="latin-1")
    # --- Fetales 2009: NIV_EDUM no sigue el DDI
    _write(d / "fetales" / "2009" / "fetal2009.csv",
           "COD_DPTO,COD_MUNIC,A_DEFUN,SIT_DEFUN,ANO,MES,SEXO,CODPTORE,CODMUNRE,AREA_RES,SEG_SOCIAL,T_GES,T_GES_AGRU_CIE,PESO_NAC,EDAD_MADRE,"
           "EST_CIVM,NIV_EDUM,C_BAS1,CAUSA_666,CAUSA_667,CAU_HOMOL\n"
           "11,001,1,3,2009,06,3,11,001,1,1,1,1,1,2,5,9,P018,402,402,080\n")
    # --- Fetales 2025: el régimen de salud pasa de SEG_SOCIAL a REGSOCIALMADRE
    _write(d / "fetales" / "2025" / "BD-EEVV-Defuncionesfetales-2025.csv",
           "COD_DPTO,COD_MUNIC,A_DEFUN,SIT_DEFUN,ANO,MES,SEXO,CODPTORE,CODMUNRE,AREA_RES,REGSOCIALMADRE,T_GES,T_GES_AGRU_CIE,PESO_NAC,"
           "EDAD_MADRE,EST_CIVM,NIV_EDUM,C_BAS1,CAUSA_667,CAU_HOMOL\n"
           '"68","755","1","1","2025","12","1","68","755","1","2",4,"4",6,4,"6","09","P018","402","080"\n')
    return root
