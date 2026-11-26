"""
Regenera ``dane_ecv_publicado.csv`` y ``dane_ipm_publicado.csv`` con las cifras que publica el DANE
de la ECV y del IPM.

    uv run --extra app python tests/datos/actualizar_ecv_publicado.py CARPETA

``CARPETA`` tiene los anexos del DANE, tal como se bajan de dane.gov.co:

* ``anex-ECV-Series-<año>.xlsx``: la serie de indicadores de la ECV desde 2018 (Calidad de vida,
  ECV <año>).
* ``anex-PMultidimensional-<año>.xlsx`` y ``anex-PMultidimensional-Departamental-<año>.xlsx``
  (Pobreza multidimensional).

Cada fila es ``anio, dominio, indicador, valor``: el dominio es el total nacional, la cabecera, los
centros poblados y rural disperso, una región del IPM o un departamento; el indicador lleva el
nombre de la columna de ``dd.ecv.indicadores`` o de ``dd.ecv.ipm``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from dane_data.referencias import strip_accents

DATOS = Path(__file__).parent
NACIONAL = "Total nacional"
_DOMINIOS = {
    "nacional": NACIONAL,
    "total nacional": NACIONAL,
    "cabecera": "Cabecera",
    "cabeceras": "Cabecera",
    "centros poblados y rural disperso": "Centros poblados y rural disperso",
    "bogota (cabecera)": "Bogotá (cabecera)",
    "orinoquia - amazonia": "Orinoquía-Amazonía",
    "orinoquia-amazonia": "Orinoquía-Amazonía",
    "valle": "Valle del Cauca",
}

# Cuadro de la serie de la ECV -> {texto del encabezado (sin tildes) que nombra la columna:
# indicador}. En los cuadros de porcentajes el valor es la columna «%» que sigue al encabezado.
_SERIE = {
    1: {
        "total hogares": "hogares",
        "total personas": "personas",
        "personas por hogar": "personas_por_hogar",
    },
    4: {
        "energia": "pct_energia",
        "gas natural": "pct_gas_natural",
        "acueducto": "pct_acueducto",
        "alcantarillado": "pct_alcantarillado",
        "recoleccion de basura": "pct_recoleccion_basuras",
    },
    7: {"hogares con acceso a internet": "pct_internet_hogar"},
    8: {
        "propia, totalmente pagada": "pct_propia_pagada",
        "propia, la estan pagando": "pct_propia_pagando",
        "en arriendo o subarriendo": "pct_arriendo",
        "usufructuario": "pct_usufructo",
        "ocupante de hecho": "pct_ocupante_de_hecho",
        "propiedad colectiva": "pct_propiedad_colectiva",
    },
    12: {
        "afiliados": "pct_afiliados",
        "contributivo": "pct_contributivo",
        "subsidiado": "pct_subsidiado",
    },
    17: {
        "personas de 6 a 21": "pct_asistencia_6_21",
        "6 a 10": "pct_asistencia_6_10",
        "11 a 14": "pct_asistencia_11_14",
        "15 a 16": "pct_asistencia_15_16",
        "17 a 21": "pct_asistencia_17_21",
    },
    18: {
        "5 anos y mas": "anios_educacion_5_mas",
        "5 a 14": "anios_educacion_5_14",
        "15 a 24": "anios_educacion_15_24",
        "25 a 34": "anios_educacion_25_34",
        "35 anos y mas": "anios_educacion_35_mas",
    },
    20: {
        "computador": "pct_usa_computador",
        "internet": "pct_usa_internet",
        "celular": "pct_usa_celular",
    },
    22: {"se considera pobre": "pct_se_considera_pobre"},
}
_EN_MILES = {"hogares", "personas"}  # el Cuadro 1 está en miles
# Privación del anexo del IPM -> columna de dd.ecv.ipm
_PRIVACIONES = {
    "analfabetismo": "analfabetismo",
    "bajo logro educativo": "logro_educativo",
    "barreras a servicios para cuidado de la primera infancia": "atencion_integral",
    "barreras de acceso a servicios de salud": "barreras_acceso_salud",
    "desempleo de larga duracion": "desempleo_larga_duracion",
    "hacinamiento critico": "hacinamiento",
    "inadecuada eliminacion de excretas": "alcantarillado",
    "inasistencia escolar": "inasistencia_escolar",
    "material inadecuado de paredes exteriores": "paredes",
    "material inadecuado de pisos": "pisos",
    "rezago escolar": "rezago_escolar",
    "sin acceso a fuente de agua mejorada": "acueducto",
    "sin aseguramiento en salud": "aseguramiento_salud",
    "trabajo infantil": "trabajo_infantil",
    "trabajo informal": "empleo_formal",
}


def _limpio(texto) -> str:
    return re.sub(r"\s+", " ", strip_accents(str(texto))).strip()


def _anio(valor) -> int | None:
    m = re.fullmatch(r"(20\d\d)(?:\.0)?\**", str(valor).strip())
    return int(m.group(1)) if m else None


def _dominio(valor) -> str | None:
    if pd.isna(valor) or str(valor).strip() == "":
        return None
    texto = re.sub(r"\s+", " ", str(valor)).strip()
    return _DOMINIOS.get(_limpio(texto), texto)


def _serie_ecv(archivo: Path) -> list[dict]:
    filas = []
    for cuadro, nombres in _SERIE.items():
        x = pd.read_excel(archivo, sheet_name=f"Cuadro {cuadro}", header=None)
        fila_anios = next(
            i for i in range(len(x)) if sum(_anio(v) is not None for v in x.iloc[i]) >= 2
        )
        inicio = next(i for i in range(len(x)) if _limpio(x.iat[i, 0]) == "total nacional")
        bloques = [(j, _anio(v)) for j, v in enumerate(x.iloc[fila_anios]) if _anio(v)]
        for k, (j0, anio) in enumerate(bloques):
            j1 = bloques[k + 1][0] if k + 1 < len(bloques) else x.shape[1]
            # El encabezado de cada columna: lo que hay encima, desde la fila de los años; una
            # columna «%» o «Promedio» sin texto propio es del grupo de la columna anterior
            etiquetas, ultima = {}, ""
            for j in range(j0, j1):
                partes = [
                    _limpio(x.iat[i, j])
                    for i in range(fila_anios + 1, inicio)
                    if pd.notna(x.iat[i, j])
                ]
                texto = " / ".join(
                    p for p in partes if p.lower() not in ("total", "%", "promedio")
                )
                ultima = texto.lower() or ultima
                etiquetas[j] = (ultima, partes[-1].lower() if partes else "")
            for clave, indicador in nombres.items():
                en_miles = indicador in _EN_MILES
                candidatas = [
                    j
                    for j, (texto, ultimo) in etiquetas.items()
                    if clave in texto.split(" / ")[-1]
                    and (ultimo == "%")
                    != (
                        en_miles
                        or indicador == "personas_por_hogar"
                        or indicador.startswith("anios_")
                    )
                ]
                if not candidatas:
                    continue
                j = candidatas[0]
                for i in range(inicio, len(x)):
                    dominio, valor = (
                        _dominio(x.iat[i, 0]),
                        pd.to_numeric(x.iat[i, j], errors="coerce"),
                    )
                    if (
                        dominio is None
                        or pd.isna(valor)
                        or _limpio(dominio).lower().startswith(("fuente", "nota", "*"))
                    ):
                        continue
                    filas.append(
                        {
                            "anio": anio,
                            "dominio": dominio,
                            "indicador": indicador,
                            "valor": float(valor) * (1000 if en_miles else 1),
                            "fuente": f"ECV Cuadro {cuadro}",
                        }
                    )
    return filas


def _tabla_por_anio(x: pd.DataFrame) -> tuple[int, list[tuple[int, int]]]:
    """La fila de los años y sus columnas (año, columna) en una hoja de los anexos del IPM."""
    fila = next(i for i in range(len(x)) if sum(_anio(v) is not None for v in x.iloc[i]) >= 2)
    return fila, [(int(_anio(v)), j) for j, v in enumerate(x.iloc[fila]) if _anio(v)]


def _ipm(nacional: Path, departamental: Path) -> list[dict]:
    filas = []

    def agregar(anio, dominio, indicador, valor, fuente):
        valor = pd.to_numeric(valor, errors="coerce")
        if (
            dominio
            and pd.notna(valor)
            and anio >= 2018
            and not _limpio(dominio).lower().startswith(("fuente", "nota"))
        ):
            filas.append(
                {
                    "anio": anio,
                    "dominio": dominio,
                    "indicador": indicador,
                    "valor": float(valor),
                    "fuente": fuente,
                }
            )

    # Incidencia por dominio y región, e incidencia ajustada (el IPM): una columna por año
    for hoja, indicador in (("IPM_Dominios", "incidencia"), ("Incidencia Ajustada_IPM", "ipm")):
        x = pd.read_excel(nacional, sheet_name=hoja, header=None)
        fila, anios = _tabla_por_anio(x)
        for i in range(fila + 1, len(x)):
            for anio, j in anios:
                agregar(anio, _dominio(x.iat[i, 0]), indicador, x.iat[i, j], f"IPM {hoja}")
    # Privaciones: dominio, variable y una columna por año
    x = pd.read_excel(nacional, sheet_name="IPM_Indicadores", header=None)
    fila, anios = _tabla_por_anio(x)
    dominio = None
    for i in range(fila + 1, len(x)):
        dominio = _dominio(x.iat[i, 0]) or dominio
        privacion = _PRIVACIONES.get(_limpio(x.iat[i, 1]).lower())
        if privacion:
            for anio, j in anios:
                agregar(anio, dominio, f"pct_{privacion}", x.iat[i, j], "IPM IPM_Indicadores")
    # Departamentos: el total de cada año (la primera de sus tres columnas: total, cabeceras,
    # centros poblados)
    x = pd.read_excel(departamental, sheet_name="IPM_Departamentos", header=None)
    fila, anios = _tabla_por_anio(x)
    for i in range(fila + 2, len(x)):
        for anio, j in anios:
            agregar(
                anio,
                _dominio(x.iat[i, 0]),
                "incidencia",
                x.iat[i, j],
                "IPM departamental IPM_Departamentos",
            )
    return filas


def main() -> None:
    carpeta = Path(sys.argv[1])
    serie = pd.DataFrame(_serie_ecv(next(carpeta.glob("anex-ECV-Series-*.xlsx"))))
    serie = serie.drop_duplicates(["anio", "dominio", "indicador"]).sort_values(
        ["indicador", "dominio", "anio"]
    )
    serie.to_csv(DATOS / "dane_ecv_publicado.csv", index=False)
    print(
        f"dane_ecv_publicado.csv: {len(serie)} cifras, {serie.indicador.nunique()} indicadores, "
        f"años {serie.anio.min()}–{serie.anio.max()}"
    )
    ipm = pd.DataFrame(
        _ipm(
            next(carpeta.glob("anex-PMultidimensional-2*.xlsx")),
            next(carpeta.glob("anex-PMultidimensional-Departamental-*.xlsx")),
        )
    )
    ipm = ipm.drop_duplicates(["anio", "dominio", "indicador"]).sort_values(
        ["indicador", "dominio", "anio"]
    )
    ipm.to_csv(DATOS / "dane_ipm_publicado.csv", index=False)
    print(
        f"dane_ipm_publicado.csv: {len(ipm)} cifras, {ipm.indicador.nunique()} indicadores, "
        f"{ipm.dominio.nunique()} dominios"
    )


if __name__ == "__main__":
    main()
