"""Datos sintéticos que imitan las rarezas de cada época de la GEIH y la EAM."""

from pathlib import Path

import pytest


def _write(path: Path, text: str, encoding="utf-8-sig"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode(encoding))


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
