"""Datos sintéticos que imitan las rarezas de cada época de la GEIH y la EAM."""

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
    oc = "Directorio;Secuencia_p;Orden;Oci;Inglabo;P6920;P6430;P6800;Rama2d;Fex_c_2011\n"
    _write(m / "Cabecera - Ocupados.csv", oc + "1;1;1;1;2000000;1;1;48;15;100,5\n2;1;1;1;500000;2;4;30;52;200,0\n")
    _write(m / "Resto - Ocupados.csv", oc)
    _write(m / "Cabecera - Desocupados.csv", "Directorio;Secuencia_p;Orden;Dsi;Fex_c_2011\n1;1;2;1;100,5\n")
    _write(m / "Resto - Inactivos.csv", "Directorio;Secuencia_p;Orden;Ini;Fex_c_2011\n3;1;1;1;300,25\n")
    # Carpeta que no es un mes (debe ignorarse)
    (base / "2016" / "Total_fact_exp_dto").mkdir(parents=True)

    # --- Época 2025: archivos únicos, PET/FFT/DSI en 'No ocupados', FEX_C18, latin-1, en subcarpeta
    m = base / "2025" / "Enero 2025"
    car = "PERIODO;MES;DIRECTORIO;SECUENCIA_P;ORDEN;P3271;P6040;P6050;P6090;P3042;CLASE;DPTO;FEX_C18\n"
    _write(m / "Características generales, seguridad social en salud y educación.CSV",
           car + "202501;1;10;1;1;2;35;1;1;10;1;76;1000.5\n202501;1;10;1;2;1;20;3;1;6;1;76;1000.5\n"
                 "202501;1;11;1;1;1;70;1;1;3;2;76;500\n", encoding="latin-1")
    _write(m / "Fuerza de trabajo.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;PET;FT;FFT;FEX_C18\n"
                                        "10;1;1;1;1;;1000.5\n10;1;2;1;1;;1000.5\n11;1;1;1;;1;500\n")
    _write(m / "Ocupados.CSV", "DIRECTORIO;SECUENCIA_P;ORDEN;OCI;INGLABO;P6920;P6430;P6800;RAMA2D_R4;FEX_C18\n"
                               "10;1;1;1;1423500;1;1;48;10;1000.5\n")
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

    # --- Mes incompleto (sin desocupados)
    m = base / "2025" / "Febrero 2025"
    _write(m / "Características generales, seguridad social en salud y educación.CSV", car + "202502;2;10;1;1;2;35;1;1;10;1;76;1000\n")
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
