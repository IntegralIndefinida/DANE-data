"""
Regenera ``dane_publicado.csv`` con las series mensuales de los anexos de mercado laboral del DANE.

    uv run --extra app python tests/datos/actualizar_publicado.py sep2026

El argumento es el anexo vigente: el mes como aparece en su nombre (``anex-GEIH-sep2026.xlsx``),
una URL o un archivo ya descargado. Está en la página "Empleo y desempleo" del DANE:
https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/empleo-y-desempleo

El anexo de diciembre de 2021 es fijo. Los microdatos del ANDA de 2007–2019 y 2021 usan las
proyecciones del censo 2005, y el anexo vigente ya solo trae la serie con el CNPV 2018.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import openpyxl
import pandas as pd
import requests

ANEXO_2021 = "https://www.dane.gov.co/files/investigaciones/boletines/ech/ech/anexo_empleo_dic_21.xlsx"
ANEXO_VIGENTE = "https://www.dane.gov.co/files/operaciones/GEIH/anex-GEIH-{mes}.xlsx"
SALIDA = Path(__file__).with_name("dane_publicado.csv")

MESES = {"Ene": 1, "Feb": 2, "Mar": 3, "Abr": 4, "May": 5, "Jun": 6, "Jul": 7, "Ago": 8, "Sep": 9, "Oct": 10,
         "Nov": 11, "Dic": 12}
# Nombre de la fila en cada anexo -> columna del CSV
FILAS = {"TGP": "tgp", "Tasa Global de Participación (TGP)": "tgp", "TO": "to", "Tasa de Ocupación (TO)": "to",
         "TD": "td", "Tasa de Desocupación (TD)": "td", "Población en edad de trabajar": "pet",
         "Población en edad de trabajar (PET)": "pet", "Ocupados": "ocupados", "Población ocupada": "ocupados",
         "Desocupados": "desocupados", "Población desocupada": "desocupados"}


def abrir(fuente: str, carpeta: Path) -> Path:
    """Ruta local del anexo: el archivo dado, o lo descarga de la URL (o del mes del anexo vigente)."""
    if Path(fuente).is_file():
        return Path(fuente)
    url = fuente if fuente.startswith("http") else ANEXO_VIGENTE.format(mes=fuente)
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=120)
    res.raise_for_status()
    destino = carpeta / url.rsplit("/", 1)[-1]
    destino.write_bytes(res.content)
    return destino


def leer(archivo: Path, hoja: str, bloque: str = "Total Nacional") -> pd.DataFrame:
    """Serie mensual de un bloque (``"Total Nacional"``, ``"Total Cabeceras"``...) de una hoja del anexo."""
    filas = list(openpyxl.load_workbook(archivo, read_only=True, data_only=True)[hoja].iter_rows(values_only=True))
    b = next(k for k, r in enumerate(filas) if str(r[0]).strip() == bloque)
    i = next(k for k in range(b, len(filas)) if filas[k][0] == "Concepto")
    # Fila de años (solo en el primer mes de cada año) y fila de meses ("Ene", "Feb"...)
    anios, anio = [], None
    for v in filas[i][1:]:
        anio = int(str(v)[:4]) if v is not None and str(v).strip()[:4].isdigit() else anio
        anios.append(anio)
    meses = [MESES.get(str(v).strip()[:3]) for v in filas[i + 1][1:]]
    datos = {}
    for r in filas[i + 2:]:
        if r[0] is not None and str(r[0]).startswith(("Total", "Fuente")):
            break  # fin del bloque
        clave = FILAS.get(str(r[0]).strip()) if r[0] is not None else None
        if clave and clave not in datos:
            datos[clave] = [v if isinstance(v, (int, float)) else None for v in r[1:len(anios) + 1]]
    df = pd.DataFrame({"anio": anios, "mes": meses, **datos})
    return df.dropna(subset=["anio", "mes", "td"]).astype({"anio": int, "mes": int})


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("anexo", help="anexo vigente: mes (p. ej. sep2026), URL o archivo .xlsx")
    p.add_argument("--salida", type=Path, default=SALIDA)
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp)
        viejo = leer(abrir(ANEXO_2021, carpeta), "Tnal mensual")
        vigente = abrir(args.anexo, carpeta)
        # El anexo vigente también trae cabeceras y sexo por mes; el de 2021 solo en trimestre móvil.
        nuevos = {"total": leer(vigente, "Total nacional"),
                  "urbano": leer(vigente, "Total nacional", "Total Cabeceras"),
                  "hombres": leer(vigente, "Total_nacional_IML_Sexo", "Total Nacional Hombres"),
                  "mujeres": leer(vigente, "Total_nacional_IML_Sexo", "Total Nacional Mujeres")}

    partes = [viejo[viejo.anio.between(2007, 2019) | (viejo.anio == 2021)].assign(serie="principal", grupo="total",
                                                                                 anexo="dic2021")]
    nombre = vigente.stem.replace("anex-GEIH-", "")
    for grupo, nuevo in nuevos.items():
        # Los microdatos de 2020 en el ANDA ya vienen con el CNPV 2018; los de 2021, con el censo 2005.
        partes += [nuevo[(nuevo.anio == 2020) | (nuevo.anio >= 2022)].assign(serie="principal", grupo=grupo,
                                                                              anexo=nombre),
                   nuevo[nuevo.anio.between(2010, 2020)].assign(serie="empalme", grupo=grupo, anexo=nombre)]
    out = pd.concat(partes)[["serie", "grupo", "anio", "mes", "td", "tgp", "to", "pet", "ocupados", "desocupados",
                             "anexo"]]
    orden = {"total": 0, "urbano": 1, "hombres": 2, "mujeres": 3}
    out = out.sort_values(["serie", "grupo", "anio", "mes"], key=lambda c: c.map(orden) if c.name == "grupo" else c,
                          ascending=[False, True, True, True])

    ultimo = out[out.anexo == nombre]["anio"].max()
    encabezado = f"""\
# Mercado laboral publicado por el DANE: serie mensual del total nacional, cabeceras y por sexo. Tasas en %,
# niveles en miles. Se regenera con tests/datos/actualizar_publicado.py.
# principal 2007-2019 y 2021 (proyecciones del censo 2005): anexo de diciembre de 2021, hoja "Tnal mensual"
#   {ANEXO_2021}
# principal 2020 y 2022-{ultimo}, y empalme 2010-2020 (proyecciones del CNPV 2018): anexo vigente,
#   {ANEXO_VIGENTE.format(mes=nombre)}. grupo total y urbano (cabeceras):
#   hoja "Total nacional"; hombres y mujeres: hoja "Total_nacional_IML_Sexo" (desde 2010).
# Los microdatos de 2020 en el ANDA ya vienen con el marco 2018, y los de 2021 todavía con el de 2005.
"""
    with open(args.salida, "w", encoding="utf-8") as fh:
        fh.write(encabezado)
        out.to_csv(fh, index=False, float_format="%.6f")
    print(f"{len(out)} filas en {args.salida}")
    print(out.groupby(["serie", "grupo", "anexo"])["anio"].agg(["min", "max", "count"]).to_string())


if __name__ == "__main__":
    main()
