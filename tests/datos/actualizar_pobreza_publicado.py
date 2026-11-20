"""
Regenera ``dane_pobreza_publicado.csv`` con las cifras de pobreza monetaria que publica el DANE.

    uv run --extra app python tests/datos/actualizar_pobreza_publicado.py [ANEXO_NACIONAL.xlsx ANEXO_DEPARTAMENTAL.xlsx]

Sin argumentos baja los anexos del boletín más reciente de dane.gov.co. De cada hoja de la metodología actualizada (la
serie empalmada, 2012–2025 nacional y 2021–2025 departamental) se toma cada fila: grandes dominios, ciudades y
departamentos. Una fila del CSV por año, nivel, dominio e indicador, con la unidad y la hoja de donde salió.

Si el DANE cambia las hojas o sus bloques, el script falla en vez de escribir un CSV incompleto.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pandas as pd
import requests

ANEXOS = {
    "nacional": "https://www.dane.gov.co/files/operaciones/PM/anex-PM-TotalNacional-2025.xlsx",
    "departamental": "https://www.dane.gov.co/files/operaciones/PM/anex-PMDepartamental-2025.xlsx",
}
SALIDA = Path(__file__).with_name("dane_pobreza_publicado.csv")
# Hoja -> indicador de cada bloque, en orden, y su unidad. "miles" se pasa a personas.
HOJAS = {
    "Población": [("personas", "miles")],
    "Pobreza Monetaria Act.Met.": [("incidencia", "%"), ("pobres", "miles")],
    "Pobreza Extrema Act.Met.": [("incidencia_extrema", "%"), ("pobres_extremos", "miles")],
    "Brecha Act.Met.": [("brecha", "%"), ("brecha_extrema", "%")],
    "Severidad Act.Met.": [("severidad", "%"), ("severidad_extrema", "%")],
    "Gini": [("gini", "coeficiente")],
    "Ingpc Act.Met.": [("ingreso_pc", "pesos")],
    "LP_LI Act.Met.": [("linea_pobreza", "pesos"), ("linea_pobreza_extrema", "pesos")],
}
# Títulos de sección dentro de un bloque: no son dominios
SECCIONES = {"Grandes dominios", "Ciudades capitales", "Ciudades con Área Metropolitana"}
# Ni las notas, la fuente, los títulos de los bloques o la unidad
NO_DOMINIO = ("Nota", "Fuente", "Fecha", "Cifras", "Personas en", "Brecha de", "Severidad de", "Líneas de", "Incidencia de",
              "Coeficiente", "Ingreso per", "Población total")


def _numero(v) -> float | None:
    if isinstance(v, str):
        v = v.strip().replace(",", ".")
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _bloques(hoja: pd.DataFrame) -> list[tuple[list[int], list[tuple[str, list]]]]:
    """Cada bloque de la hoja: los años del encabezado y las filas (etiqueta, valores) que le siguen."""
    bloques = []
    for _, fila in hoja.iterrows():
        valores = fila.tolist()
        anios = [_numero(v) for v in valores[1:]]
        if all(a is None or 2000 <= a <= 2100 and a == int(a) for a in anios) and sum(a is not None for a in anios) >= 3:
            bloques.append(([int(a) if a is not None else None for a in anios], []))
            continue
        etiqueta = valores[0]
        if (bloques and isinstance(etiqueta, str) and etiqueta.strip() and etiqueta.strip() not in SECCIONES
                and not etiqueta.strip().startswith(NO_DOMINIO)):
            nums = [_numero(v) for v in valores[1:]]
            if any(n is not None for n in nums):
                bloques[-1][1].append((etiqueta.strip(), nums))
    return bloques


def leer(ruta_o_bytes, nivel: str) -> pd.DataFrame:
    libro = pd.read_excel(ruta_o_bytes, sheet_name=None, header=None)
    filas = []
    for nombre, indicadores in HOJAS.items():
        if nombre not in libro:
            raise SystemExit(f"El anexo {nivel} ya no trae la hoja {nombre!r}: revise HOJAS.")
        bloques = [b for b in _bloques(libro[nombre]) if b[1]]
        if len(bloques) != len(indicadores):
            raise SystemExit(f"{nivel}, hoja {nombre!r}: {len(bloques)} bloques con datos, se esperaban "
                             f"{len(indicadores)}. Revise HOJAS.")
        for (anios, datos), (indicador, unidad) in zip(bloques, indicadores):
            for etiqueta, nums in datos:
                for anio, valor in zip(anios, nums):
                    if anio is None or valor is None:
                        continue
                    if unidad == "miles":
                        valor, unidad_csv = valor * 1000, "personas"
                    else:
                        unidad_csv = unidad
                    filas.append({"anio": anio, "nivel": nivel, "dominio": etiqueta, "indicador": indicador,
                                  "valor": valor, "unidad": unidad_csv, "fuente": f"{ANEXOS[nivel].rsplit('/', 1)[1]}: {nombre}"})
    return pd.DataFrame(filas)


def main() -> None:
    if len(sys.argv) == 3:
        fuentes = dict(zip(ANEXOS, sys.argv[1:]))
    else:
        fuentes = {}
        for nivel, url in ANEXOS.items():
            r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            fuentes[nivel] = io.BytesIO(r.content)
    tabla = pd.concat([leer(f, nivel) for nivel, f in fuentes.items()], ignore_index=True)
    tabla = tabla.sort_values(["nivel", "indicador", "dominio", "anio"], ignore_index=True)
    tabla.to_csv(SALIDA, index=False)
    print(f"{len(tabla)} cifras en {SALIDA}")
    print(tabla.groupby(["nivel", "indicador"]).size().to_string())


if __name__ == "__main__":
    main()
