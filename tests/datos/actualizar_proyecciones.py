"""
Regenera ``src/dane_data/data/proyecciones_poblacion.parquet`` con las proyecciones de población del DANE.

    uv run --extra app python tests/datos/actualizar_proyecciones.py [--excel CARPETA]

Los Excel están en la página "Proyecciones de población" del DANE:
https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion

``--excel`` lee de una carpeta los que ya estén descargados (se busca por nombre de archivo, también en subcarpetas).

Se guarda por departamento, año, área (salvo los últimos años, que el DANE no parte por área), sexo y edad simple. El total nacional es la suma de los departamentos (aquí se
comprueba, año por año), así que del archivo nacional solo se guardan los años sin dato por departamento: 1950–1984 y
2051–2070, con ``dpto`` 0.
"""

from __future__ import annotations

import argparse
import re
import tempfile
from pathlib import Path

import pandas as pd
import requests

BASE = "https://www.dane.gov.co/files/censo2018/proyecciones-de-poblacion/"
DEPARTAMENTALES = [
    "Departamental/DCD-area-sexo-edad-proypoblacion-dep-1985-1992.xlsx",
    "Departamental/DCD-area-sexo-edad-proypoblacion-dep-1993-2004.xlsx",
    "Departamental/DCD-area-sexo-edad-proypoblacion-dep-2005-2017_VP.xlsx",
    "Departamental/PPED-AreaSexoEdadDep-2018-2050_VP.xlsx",
]
NACIONALES = ["Nacional/PPED-AreaSexoEdadNac-1950-2017.xlsx", "Nacional/PPED-AreaSexoEdadNac-2018-2070.xlsx"]
SALIDA = Path(__file__).parents[2] / "src" / "dane_data" / "data" / "proyecciones_poblacion.parquet"

COLUMNA_EDAD = re.compile(r"^(Hombres|Mujeres)[_ ](\d+)")
AREAS = {"cabecera": "Cabecera", "centros poblados y rural disperso": "Centros poblados y rural disperso"}
TOTAL = "Total"  # Departamentos desde 2046 y nacional desde 2051: el DANE ya no parte por área


def _traer(relativa: str, carpeta: Path | None, temporal: Path) -> Path:
    nombre = relativa.rsplit("/", 1)[1]
    if carpeta is not None and (hallados := list(carpeta.rglob(nombre))):
        return hallados[0]
    destino = temporal / nombre
    print(f"Bajando {nombre}…")
    r = requests.get(BASE + relativa, timeout=300)
    r.raise_for_status()
    destino.write_bytes(r.content)
    return destino


def _leer(archivo: Path) -> pd.DataFrame:
    """Una fila por departamento, año y área. Los encabezados cambian: una o dos filas, ``Hombres_0`` o ``Hombres 0 años``."""
    libro = pd.ExcelFile(archivo, engine="openpyxl")
    crudo = libro.parse(libro.sheet_names[-1], header=None)
    fila = next(i for i, f in crudo.iterrows() if "AÑO" in {str(v).strip() for v in f.values})
    arriba = [str(v).strip() for v in crudo.iloc[fila].values]
    abajo = crudo.iloc[fila + 1].values
    dos_filas = pd.isna(abajo[arriba.index("AÑO")])
    nombres = [str(b).strip() if dos_filas and pd.notna(b) else a for a, b in zip(arriba, abajo)]
    datos = crudo.iloc[fila + (2 if dos_filas else 1):].copy()
    datos.columns = nombres
    return datos[datos["AÑO"].notna()].loc[:, ~pd.Index(nombres).duplicated()]


def _a_largo(ancho: pd.DataFrame, nacional: bool) -> pd.DataFrame:
    """
    Formato largo sin las columnas de totales. Las filas «Total» de área se dejan solo en los años que no traen las
    dos áreas; en los demás se comprueba que las áreas sumen ese total y se quitan.
    """
    edades = {c: COLUMNA_EDAD.match(c) for c in ancho.columns if COLUMNA_EDAD.match(c)}
    if len(edades) != 202:  # dos sexos, de 0 a 100 años
        raise ValueError(f"Se esperaban 202 columnas de sexo y edad; hay {len(edades)}")
    area = ancho["ÁREA GEOGRÁFICA"].astype(str).str.strip().str.lower().str.replace(" municipal", "", regex=False)
    d = pd.DataFrame({"anio": pd.to_numeric(ancho["AÑO"]).astype(int),
                      "dpto": 0 if nacional else pd.to_numeric(ancho["DP"]).astype(int), "area": area})
    valores = ancho[list(edades)].apply(pd.to_numeric)
    d = pd.concat([d, valores], axis=1)

    llaves = ["anio", "dpto"]
    total = d[d["area"] == "total"].set_index(llaves)[list(edades)].sort_index()
    partes = d[d["area"].isin(AREAS)]
    if (faltan := set(d["area"]) - set(AREAS) - {"total"}):
        raise ValueError(f"Áreas desconocidas: {faltan}")
    suma = partes.groupby(llaves)[list(edades)].sum().sort_index()
    comunes = suma.index.intersection(total.index)
    if (suma.loc[comunes].sub(total.loc[comunes]).abs() > 1e-6).any(axis=None):
        raise ValueError("Cabecera + centros poblados no da el total del archivo")
    if (partes.groupby(llaves)["area"].nunique() != 2).any():
        raise ValueError("Hay años con una sola área")

    con_areas = pd.MultiIndex.from_frame(d[llaves]).isin(suma.index)
    solo_total = d[(d["area"] == "total") & ~con_areas]
    largo = pd.concat([partes, solo_total]).melt(id_vars=["anio", "dpto", "area"], var_name="columna",
                                                 value_name="poblacion")
    largo["sexo"] = largo["columna"].map(lambda c: {"Hombres": "Hombre", "Mujeres": "Mujer"}[edades[c].group(1)])
    largo["edad"] = largo["columna"].map(lambda c: int(edades[c].group(2)))
    largo["area"] = largo["area"].map({**AREAS, "total": TOTAL})
    if (largo["poblacion"] % 1 != 0).any():
        raise ValueError("Hay valores de población que no son enteros")
    return largo.drop(columns="columna")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--excel", type=Path, help="Carpeta con los Excel ya descargados")
    args = p.parse_args()

    with tempfile.TemporaryDirectory() as t:
        temporal = Path(t)
        dep = pd.concat([_a_largo(_leer(_traer(f, args.excel, temporal)), False) for f in DEPARTAMENTALES],
                        ignore_index=True)
        nac = pd.concat([_a_largo(_leer(_traer(f, args.excel, temporal)), True) for f in NACIONALES],
                        ignore_index=True)

    # Lo que justifica no guardar el nacional en los años comunes
    por_dep = dep.groupby("anio")["poblacion"].sum()
    por_nac = nac.groupby("anio")["poblacion"].sum()
    comunes = por_dep.index.intersection(por_nac.index)
    if (por_dep[comunes] != por_nac[comunes]).any():
        raise ValueError("La suma de los departamentos no da el total nacional")
    if len(dep["dpto"].unique()) != 33:
        raise ValueError(f"Se esperaban 33 departamentos; hay {dep['dpto'].nunique()}")
    variacion = por_nac.pct_change().abs().dropna()
    if variacion.max() > 0.04:
        raise ValueError(f"Salto de {variacion.max():.1%} en {variacion.idxmax()}: revise los empalmes de los archivos")

    final = pd.concat([dep, nac[~nac["anio"].isin(comunes)]], ignore_index=True)
    final = final.astype({"anio": "int16", "dpto": "int8", "edad": "int8", "poblacion": "int32",
                          "area": "category", "sexo": "category"})
    final = final[["anio", "dpto", "area", "sexo", "edad", "poblacion"]].sort_values(
        ["anio", "dpto", "area", "sexo", "edad"], ignore_index=True)
    final.to_parquet(SALIDA, index=False, compression="zstd", compression_level=19)
    print(f"{SALIDA.name}: {len(final):,} filas, {SALIDA.stat().st_size / 1e6:.2f} MB; años {final.anio.min()}–{final.anio.max()}; "
          f"departamentos {dep.anio.min()}–{dep.anio.max()}; 2025 = {por_nac[2025]:,}")


if __name__ == "__main__":
    main()
