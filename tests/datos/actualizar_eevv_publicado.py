"""
Regenera ``dane_eevv_publicado.csv`` con los totales que publica el DANE para las Estadísticas Vitales.

    uv run --extra app --with xlrd --with msoffcrypto-tool python tests/datos/actualizar_eevv_publicado.py [--cache CARPETA]

De la página de cada año y tipo se toma el cuadro definitivo más reciente y de él la fila del total nacional: total, hombres
y mujeres. Desde 2019 también el total por departamento (``dane_eevv_departamentos.csv``), de residencia en nacimientos y
defunciones y de ocurrencia en fetales. Los años anteriores a 2008 no tienen cuadros en la página.
https://www.dane.gov.co/index.php/estadisticas-por-tema/salud/nacimientos-y-defunciones

``--cache`` guarda lo descargado en una carpeta, para no volver a bajarlo.

Los ``.xls`` de 2019–2023 traen la protección de solo lectura de Excel, con su clave predeterminada: Excel los abre sin
pedir nada, pero xlrd no. Por eso se necesita msoffcrypto-tool.
"""

from __future__ import annotations

import argparse
import io
import re
import tempfile
import time
from pathlib import Path
from urllib.parse import quote, unquote

import msoffcrypto
import pandas as pd
import requests

PAGINA = "https://www.dane.gov.co/index.php/estadisticas-por-tema/salud/nacimientos-y-defunciones/"
RUTAS = {
    "nacimientos": "nacimientos/nacimientos-{a}",
    "defunciones": "defunciones-no-fetales/defunciones-no-fetales-{a}",
    "fetales": "defunciones-fetales/defunciones-fetales-{a}",
}
ANIOS = range(2008, 2026)
SALIDA = Path(__file__).with_name("dane_eevv_publicado.csv")
SALIDA_DEPARTAMENTOS = Path(__file__).with_name("dane_eevv_departamentos.csv")
# Hoja del cuadro por departamento y si es de residencia u ocurrencia
HOJAS_DEPARTAMENTO = {"nacimientos": ("Cuadro3", "residencia"), "defunciones": ("Cuadro4", "residencia"),
                      "fetales": ("Cuadro1", "ocurrencia")}
DEPARTAMENTO = re.compile(r"^(\d\d)\s+\D")
ENLACE = re.compile(r'href="(?:https?://www\.dane\.gov\.co)?(/files/[^"?]+\.xlsx?)(?:\?[^"]*)?"', re.I)
CUADRO_1 = re.compile(r"cuadro[\s_-]*1(?![0-9])", re.I)
PAUSA = 3  # segundos entre pedidos
CABECERAS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}


def _traer(url: str, carpeta: Path) -> bytes:
    archivo = carpeta / re.sub(r"[^\w.-]", "_", url.rsplit("files/", 1)[-1].rsplit("index.php/", 1)[-1])
    if archivo.exists():
        return archivo.read_bytes()
    # El sitio del DANE responde 429 si se le pide mucho seguido: un pedido a la vez, con pausa, y espera larga si se queja
    for intento in range(4):
        time.sleep(PAUSA)
        r = requests.get(url, headers=CABECERAS, timeout=180)
        if r.status_code != 429:
            break
        espera = int(r.headers.get("Retry-After", 0) or 0) or 300 * (intento + 1)
        print(f"  El sitio pide esperar (429): {espera} s", flush=True)
        time.sleep(espera)
    r.raise_for_status()
    archivo.write_bytes(r.content)
    return r.content


def _cuadro(pagina: str) -> str | None:
    """
    El enlace del cuadro definitivo. Hasta 2018 cada cuadro es un archivo y sirve el 1; desde 2019 el primero de la lista es
    el archivo completo. Nunca otro: los demás son preliminares o trimestres, con otros totales.
    """
    enlaces = list(dict.fromkeys(ENLACE.findall(pagina)))
    if not enlaces:
        return None
    if re.search(r"definiti|definiv|unificado|acumulado", unquote(enlaces[0]), re.I) and not CUADRO_1.search(unquote(enlaces[0])):
        return enlaces[0]
    return next((u for u in enlaces if CUADRO_1.search(unquote(u))), None)


def _sin_proteccion(contenido: bytes) -> bytes:
    """Quita la protección de solo lectura de Excel (su clave predeterminada es pública), si la tiene."""
    documento = msoffcrypto.OfficeFile(io.BytesIO(contenido))
    if not documento.is_encrypted():
        return contenido
    documento.load_key(password="VelvetSweatshop")
    salida = io.BytesIO()
    documento.decrypt(salida)
    return salida.getvalue()


def _libro(contenido: bytes, sufijo: str) -> pd.ExcelFile:
    return pd.ExcelFile(io.BytesIO(_sin_proteccion(contenido) if sufijo.lower() == ".xls" else contenido))


def _total_nacional(libro: pd.ExcelFile) -> tuple[int, int, int] | None:
    """``(total, hombres, mujeres)`` de la primera hoja con columnas de hombres y mujeres y fila de total."""
    hojas = sorted(libro.sheet_names, key=lambda h: 0 if re.fullmatch(r"(?i)cuadro\s*1", h.strip()) else 1)
    for hoja in hojas:
        if hoja.lower().startswith(("indice", "índice", "listas")):
            continue
        con_sexo = False
        for _, fila in libro.parse(hoja, header=None, nrows=40).iterrows():
            celdas = list(fila)
            textos = [str(c).strip().lower() for c in celdas if isinstance(c, str)]
            if not con_sexo:
                con_sexo = "hombres" in textos and "mujeres" in textos
                continue
            etiqueta = next((i for i, c in enumerate(celdas) if isinstance(c, str) and c.strip().lower().startswith("total")), None)
            if etiqueta is None:
                continue
            # Solo lo que va después de la etiqueta: antes puede haber códigos de departamento y municipio
            numeros = [int(c) for c in celdas[etiqueta + 1:] if isinstance(c, (int, float)) and pd.notna(c)]
            if len(numeros) >= 4:
                total, hombres, mujeres, otro = numeros[:4]
                # Algunos cuadros traen una columna de sexo indeterminado y otros no
                if total in (hombres + mujeres, hombres + mujeres + otro):
                    return total, hombres, mujeres
    return None


def _por_departamento(libro: pd.ExcelFile, hoja: str) -> dict[int, int]:
    """``{código: total}`` de las filas de departamento: «05 Antioquia», sin las de municipio («05001 Medellín»)."""
    totales = {}
    for fila in libro.parse(hoja, header=None).itertuples(index=False):
        celdas = list(fila)
        for i, c in enumerate(celdas):
            if isinstance(c, str) and (m := DEPARTAMENTO.match(c.strip())):
                numeros = [int(v) for v in celdas[i + 1:] if isinstance(v, (int, float)) and pd.notna(v)]
                if numeros:
                    totales[int(m.group(1))] = numeros[0]
                break
    return totales


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--cache", type=Path, help="Carpeta donde guardar lo descargado")
    args = p.parse_args()
    temporal = tempfile.TemporaryDirectory()
    carpeta = args.cache or Path(temporal.name)
    carpeta.mkdir(parents=True, exist_ok=True)

    filas, departamentos = [], []
    for tipo, ruta in RUTAS.items():
        for anio in ANIOS:
            url = PAGINA + ruta.format(a=anio)
            pagina = _traer(url, carpeta).decode("utf-8", "replace")
            hallado = None
            if enlace := _cuadro(pagina):
                completa = "https://www.dane.gov.co" + quote(unquote(enlace))
                libro = _libro(_traer(completa, carpeta), Path(enlace).suffix)
                hallado = _total_nacional(libro)
                if hallado:
                    filas.append({"tipo": tipo, "anio": anio, "total": hallado[0], "hombres": hallado[1], "mujeres": hallado[2],
                                  "fuente": unquote(enlace)})
                if anio >= 2019:  # Desde entonces un solo archivo trae todos los cuadros, con el mismo formato
                    hoja, base = HOJAS_DEPARTAMENTO[tipo]
                    por_dpto = _por_departamento(libro, hoja)
                    if len(por_dpto) != 33:
                        raise ValueError(f"{tipo} {anio}, {hoja}: {len(por_dpto)} departamentos")
                    departamentos += [{"tipo": tipo, "anio": anio, "base": base, "dpto": d, "total": n} for d, n in sorted(por_dpto.items())]
            print(f"{tipo} {anio}: {hallado}", flush=True)
    tabla = pd.DataFrame(filas)
    tabla.to_csv(SALIDA, index=False)
    pd.DataFrame(departamentos).to_csv(SALIDA_DEPARTAMENTOS, index=False)
    print(f"{SALIDA.name}: {len(tabla)} filas de {len(RUTAS) * len(ANIOS)}; {SALIDA_DEPARTAMENTOS.name}: {len(departamentos)} filas")


if __name__ == "__main__":
    main()
