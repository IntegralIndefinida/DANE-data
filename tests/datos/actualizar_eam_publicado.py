"""
Regenera ``dane_eam_publicado.csv`` con los totales nacionales que publica el DANE para la EAM.

    uv run --extra app --with xlrd python tests/datos/actualizar_eam_publicado.py [--cache CARPETA]

1992–2011: la serie «Evolución de las principales variables industriales 1956–2011» (CIIU Rev. 3).
2015 en adelante: el cuadro 2.1 («Resumen de las variables principales», fila del total) del anexo
de cada año. 2012–2014 no tienen anexo en la página: el archivo de 2012 con CIIU Rev. 4 es de 2014
y no coincide con los microdatos publicados después, así que no se usa.
https://www.dane.gov.co/index.php/estadisticas-por-tema/industria/encuesta-anual-manufacturera-enam/eam-historicos

Los montos van en miles de pesos corrientes, como en los microdatos. ``--cache`` guarda lo
descargado en una carpeta.
"""

from __future__ import annotations

import argparse
import io
import re
import tempfile
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.dane.gov.co/files/"
SERIE = BASE + "investigaciones/industria/eam/Evolucion_principales_variables_1956-2011_CIIU3.xls"
ANEXOS = {
    2015: BASE + "investigaciones/boletines/eam/Anexos_EAM_principales_variables.xls",
    **{
        a: BASE + f"investigaciones/boletines/eam/Anexos_EAM_principales_variables_{a}.xlsx"
        for a in range(2016, 2021)
    },
    **{a: BASE + f"operaciones/EAM/anex-EAM-{a}.xlsx" for a in range(2021, 2025)},
}
# Fila (serie histórica) o columna (anexos) del DANE -> columna de dd.eam.resumen
VARIABLES = {
    "establecimientos": "establecimientos",
    "total personal ocupado": "personal_total",
    "produccion bruta": "produccion_bruta",
    "consumo intermedio": "consumo_intermedio",
    "valor agregado": "valor_agregado",
}
SALIDA = Path(__file__).with_name("dane_eam_publicado.csv")
PAUSA = 3  # segundos entre pedidos: el sitio del DANE responde 429 si se le pide mucho seguido
CABECERAS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
}


def _traer(url: str, carpeta: Path) -> bytes:
    archivo = carpeta / url.rsplit("/", 1)[-1]
    if not archivo.exists():
        time.sleep(PAUSA)
        r = requests.get(url, headers=CABECERAS, timeout=180)
        r.raise_for_status()
        archivo.write_bytes(r.content)
    return archivo.read_bytes()


def _texto(x) -> str:
    """Sin tildes, en minúscula y sin notas como «(b)» ni «(M)»."""
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"\([^)]*\)", " ", x)).strip().lower()


def _variable(etiqueta: str) -> str | None:
    t = _texto(etiqueta)
    return next((v for k, v in VARIABLES.items() if t.startswith(k) or t.endswith(k)), None)


def serie_historica(contenido: bytes) -> list[dict]:
    df = pd.read_excel(io.BytesIO(contenido), header=None)
    fila_anios = df.index[df[0].map(_texto) == "variables"][0]
    anios = df.loc[fila_anios]
    filas = []
    for _, fila in df.loc[fila_anios + 1 :].iterrows():
        if (variable := _variable(fila[0])) is None:
            continue
        for col, anio in anios.items():
            # 2011 viene dos veces: «sin» y «con mezcla de combustibles» (57 plantas de etanol y
            # biodiésel, que la EAM incluye desde 2011); los microdatos son los de «con mezcla»
            if (
                col
                and pd.notna(anio)
                and "sin mezcla" not in str(anio)
                and 1992 <= (a := int(str(anio)[:4])) <= 2011
            ):
                filas.append({"anio": a, "variable": variable, "valor": float(fila[col])})
    return filas


def cuadro_2_1(contenido: bytes, hoja: str, anio: int) -> list[dict]:
    df = pd.read_excel(io.BytesIO(contenido), sheet_name=hoja, header=None)
    # El encabezado ocupa dos filas («Número de» / «establecimientos», «Total» / «personal ocupado
    # (b)»...)
    fila = df.index[
        df.apply(lambda f: f.map(lambda x: _texto(x).startswith("numero de")).any(), axis=1)
    ][0]
    celda = lambda f, c: "" if pd.isna(df.at[f, c]) else str(df.at[f, c])  # noqa: E731
    total = df.index[df[0].map(_texto) == "total"][0]
    filas = [
        {"anio": anio, "variable": variable, "valor": float(df.at[total, c])}
        for c in df.columns
        if (variable := _variable(f"{celda(fila, c)} {celda(fila + 1, c)}")) is not None
    ]
    if sorted(f["variable"] for f in filas) != sorted(VARIABLES.values()):
        raise ValueError(
            f"Cuadro 2.1 de {anio}: no se encontraron las variables una vez cada una ({filas})."
        )
    return filas


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cache", type=Path, help="Carpeta donde guardar lo descargado")
    args = p.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        carpeta = args.cache or Path(tmp)
        carpeta.mkdir(parents=True, exist_ok=True)
        filas = serie_historica(_traer(SERIE, carpeta))
        for anio, url in ANEXOS.items():
            filas += cuadro_2_1(_traer(url, carpeta), "2.1", anio)
    tabla = pd.DataFrame(filas).sort_values(["anio", "variable"])
    tabla["valor"] = tabla["valor"].round().astype("int64")
    tabla.to_csv(SALIDA, index=False)
    print(
        f"{SALIDA.name}: {len(tabla)} cifras, {tabla.anio.nunique()} años "
        f"({tabla.anio.min()}–{tabla.anio.max()})"
    )


if __name__ == "__main__":
    main()
