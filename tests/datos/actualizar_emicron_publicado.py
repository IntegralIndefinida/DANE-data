"""
Regenera ``dane_emicron_publicado.csv`` con las cifras que publica el DANE en los anexos anuales de la EMICRON.

    uv run --extra app python tests/datos/actualizar_emicron_publicado.py [--cache CARPETA]

Se usan los anexos vigentes: los nacionales de 2019–2024 (los de 2019–2022 son los «actualizado-abr2023», con el
factor ajustado) y los de 24 ciudades de 2019–2025. De cada uno se toman las cantidades (no las distribuciones) de los
cuadros A1.10 (situación en el empleo), A1.12 (sexo), B.1 (actividad, 4 grupos), D.1 (sitio), E.1.1 (salud y pensión),
F.1 (RUT) y F.6 (Cámara de Comercio), por dominio, y el cuadro I.1 (resumen de las principales variables).
https://www.dane.gov.co/index.php/estadisticas-por-tema/mercado-laboral/micronegocios

``--cache`` es una carpeta con los anexos ya bajados (por ejemplo ``metodologia/emicron/resultados``); lo que no esté
ahí se baja y se guarda en ella. dane.gov.co responde 429 si se le piden muchos archivos seguidos: se espera entre uno y
otro.
"""

from __future__ import annotations

import argparse
import re
import tempfile
import time
from pathlib import Path

import pandas as pd
import requests

from dane_data.referencias import strip_accents

BASE = "https://www.dane.gov.co/files/"
_VIEJOS = "investigaciones/boletines/ech/micro/"
_NUEVOS = "operaciones/EMICRON/"
ANEXOS = {  # (año, alcance) -> ruta en dane.gov.co
    **{(a, "nacional"): f"{_VIEJOS}Anexo_total_nacional_{a}-(actualizado-abr2023).xlsx" for a in range(2019, 2023)},
    (2023, "nacional"): f"{_NUEVOS}anex-EMICRON-2023.xlsx",
    (2024, "nacional"): f"{_NUEVOS}anex-EMICRON-2024.xlsx",
    **{(a, "24 ciudades"): f"{_VIEJOS}Anexo_24_ciudades_{a}-(actualizado-abr2023).xlsx" for a in range(2019, 2023)},
    (2023, "24 ciudades"): f"{_NUEVOS}anex-EMICRON-24Ciudades-2023.xlsx",
    (2024, "24 ciudades"): f"{_NUEVOS}anex-Ciudades-EMICRON-2024.xlsx",
    (2025, "24 ciudades"): f"{_NUEVOS}anex-EMICRON-24Ciudades-2025.xlsx",
}
SALIDA = Path(__file__).with_name("dane_emicron_publicado.csv")

# Cuadro -> variable de dd.emicron
CUADROS = {"A1.10": "situacion_empleo", "A1.12": "sexo", "B.1": "actividad", "D.1": "sitio", "E.1.1": "salud_pension",
           "F.1": "rut", "F.6": "camara_comercio"}
# Columnas del cuadro I.1 -> columna de dd.emicron.indicadores ("Propietarios" es igual a micronegocios)
I1 = {"número de micronegocios": "micronegocios", "personal ocupado": "personal_ocupado",
      "trabajadores remunerados": "trabajadores_remunerados", "socios": "socios",
      "trabajadores o familiares sin remuneración": "familiares_sin_remuneracion", "ventas o ingresos": "ventas",
      "consumo intermedio": "consumo_intermedio", "valor agregado": "valor_agregado",
      "remuneración del personal ocupado": "remuneracion", "sueldos y salarios": "sueldos",
      "prestaciones sociales": "prestaciones", "ingreso mixto": "ingreso_mixto",
      "coeficiente técnico": "coeficiente_tecnico"}
# Etiquetas del anexo que no son iguales a las de dd.emicron (sin notas al pie y en minúscula)
CATEGORIAS = {"trabajador(a) por cuenta propia": "Trabajador por cuenta propia", "hombres": "Hombre", "mujeres": "Mujer",
              "sí": "True", "si": "True", "no": "False",
              "de puerta a puerta o a domicilio": "De puerta en puerta o a domicilio"}
_ESTADISTICOS = {"L.i", "L.s", "Int/2", "C.v"}


def _limpia(texto) -> str:
    """Sin notas al pie («Industria manufacturera (2) », «Ingreso mixto2»), sin espacios de más."""
    texto = re.sub(r"\s+", " ", str(texto)).strip()
    return re.sub(r"\s*\(\d\)$|(?<=[a-zó])\d$", "", texto).strip()


def _sin_marcas(texto: str) -> str:
    return re.sub(r"\b(a\.? ?m\.?|d\.? ?c\.?)$", "", strip_accents(texto)).strip(" .,")


def _dominio(texto: str, ciudades) -> str:
    t = _limpia(texto)
    if t in ("Total", "Total nacional"):
        return "total"
    if t.lower().startswith("total 24 ciudades"):
        return "24 ciudades"
    # Las ciudades con el nombre de dd.emicron.CIUDADES («Bogotá» -> «Bogotá D.C.», «Valledupar A.M.» -> «Valledupar»)
    return next((c for c in ciudades if _sin_marcas(c) == _sin_marcas(t)), t)


def _categoria(texto: str, propias: set[str]) -> str:
    t = _limpia(texto)
    if t.lower() in CATEGORIAS:
        return CATEGORIAS[t.lower()]
    # La etiqueta de dd.emicron que coincide sin importar mayúsculas («No Informa» -> «No informa»)
    return next((p for p in propias if p.lower() == t.lower()), t)


def _bloque_cantidades(hoja: pd.DataFrame, ciudades) -> tuple[int, list[tuple[int, str]]]:
    """Fila del primer encabezado (el de las cantidades) y las columnas de cada dominio."""
    fila = next(i for i in range(len(hoja)) if hoja.iloc[i].astype(str).str.strip().isin(_ESTADISTICOS).any())
    columnas = [(j, _dominio(v, ciudades)) for j, v in enumerate(hoja.iloc[fila]) if pd.notna(v) and str(v).strip() not in _ESTADISTICOS]
    return fila, columnas


def _cuadro(hoja: pd.DataFrame, cuadro: str, propias: set[str], ciudades) -> list[dict]:
    fila, columnas = _bloque_cantidades(hoja, ciudades)
    filas = []
    for i in range(fila + 1, len(hoja)):
        etiqueta = hoja.iloc[i, 0]
        if pd.isna(etiqueta) or str(etiqueta).strip().startswith(("Cuadro", "Fuente")):
            break
        for j, dominio in columnas:
            valor = pd.to_numeric(hoja.iloc[i, j], errors="coerce")
            if pd.notna(valor):
                filas.append({"dominio": dominio, "cuadro": cuadro, "variable": CUADROS[cuadro],
                              "categoria": _categoria(etiqueta, propias), "valor": float(valor)})
    return filas


def _i1(hoja: pd.DataFrame, ciudades) -> list[dict]:
    fila = next(i for i in range(len(hoja)) if hoja.iloc[i].astype(str).str.contains("Número de micronegocios").any())
    columnas = [(j, I1[_limpia(v).lower()]) for j, v in enumerate(hoja.iloc[fila])
                if pd.notna(v) and _limpia(v).lower() in I1]
    filas = []
    for i in range(fila + 1, len(hoja)):
        etiqueta = hoja.iloc[i, 0]
        if pd.isna(etiqueta) or str(etiqueta).strip().startswith(("Cuadro", "Fuente")):
            break
        for j, variable in columnas:
            valor = pd.to_numeric(hoja.iloc[i, j], errors="coerce")
            if pd.notna(valor):
                filas.append({"dominio": _dominio(etiqueta, ciudades), "cuadro": "I.1", "variable": variable, "categoria": "",
                              "valor": float(valor)})
    return filas


def _archivo(ruta: str, cache: Path) -> Path:
    destino = cache / Path(ruta).name
    if not destino.is_file():
        for intento in range(5):
            r = requests.get(BASE + ruta, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 429:
                break
            time.sleep(30 * (intento + 1))
        r.raise_for_status()
        destino.write_bytes(r.content)
        time.sleep(5)
    return destino


def main() -> None:
    import dane_data as dd

    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[1])
    p.add_argument("--cache", type=Path, help="Carpeta con los anexos ya bajados (lo que falte se guarda ahí)")
    args = p.parse_args()
    cache = args.cache or Path(tempfile.mkdtemp(prefix="emicron-anexos-"))
    cache.mkdir(parents=True, exist_ok=True)
    propias = {str(c) for t in dd.emicron.CATEGORIAS.values() for c in t.categories}
    ciudades = list(dd.emicron.CIUDADES.values())

    filas = []
    for (anio, alcance), ruta in sorted(ANEXOS.items()):
        archivo = _archivo(ruta, cache)
        hojas = pd.read_excel(archivo, sheet_name=None, header=None)
        sufijo = "" if alcance == "nacional" else "_24C"
        for cuadro in [*CUADROS, "I.1"]:
            hoja = hojas[f"{cuadro}{sufijo}"]
            nuevas = _i1(hoja, ciudades) if cuadro == "I.1" else _cuadro(hoja, cuadro, propias, ciudades)
            if not nuevas:
                raise ValueError(f"{archivo.name}, {cuadro}{sufijo}: no se encontraron cifras.")
            filas += [{"anio": anio, "alcance": alcance, **f, "fuente": "/files/" + ruta} for f in nuevas]
        print(f"{anio} {alcance}: {sum(f['anio'] == anio and f['alcance'] == alcance for f in filas)} cifras")
    out = pd.DataFrame(filas)
    # En los de 24 ciudades el total es el de las 24 ciudades
    out.loc[(out["alcance"] == "24 ciudades") & (out["dominio"] == "total"), "dominio"] = "24 ciudades"
    out = out.drop(columns="alcance").drop_duplicates(["anio", "dominio", "cuadro", "variable", "categoria"])
    out.to_csv(SALIDA, index=False)
    print(f"{SALIDA.name}: {len(out)} cifras")


if __name__ == "__main__":
    main()
