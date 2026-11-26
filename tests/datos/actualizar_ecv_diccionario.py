"""
Regenera el diccionario de la ECV (``src/dane_data/data/ecv_diccionario.json``) desde el DDI del
ANDA.

    uv run python tests/datos/actualizar_ecv_diccionario.py [ARCHIVO_DDI.xml]

Sin argumento se baja el DDI del catálogo más reciente. Solo van las variables de los capítulos que
descarga ``dd.ecv.download``, y en ``modulos`` el nombre del capítulo en ``dd.ecv.MODULOS`` (el que
se pide a ``dd.ecv.load``). Se guarda tal como lo publica el DANE: lo que contradice los datos va
en la tabla de diferencias del README.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

from dane_data.referencias import strip_accents

CATALOGO = 905  # 2025
DDI = "https://microdatos.dane.gov.co/index.php/metadata/export/{c}/ddi"
SALIDA = Path(__file__).parents[2] / "src" / "dane_data" / "data" / "ecv_diccionario.json"
# Nombre del archivo en el DDI (sin tildes, en minúscula) -> capítulo de dd.ecv.MODULOS
CAPITULOS = {
    "datos de la vivienda": "vivienda",
    "servicios del hogar": "servicios",
    "tenencia y financiacion de la vivienda que ocupa el hogar": "tenencia",
    "condiciones de vida del hogar y tenencia de bienes": "condiciones",
    "caracteristicas y composicion del hogar": "caracteristicas",
    "salud": "salud",
    "atencion integral de los ninos y ninas menores de 5 anos": "primera_infancia",
    "educacion": "educacion",
    "fuerza de trabajo": "fuerza_trabajo",
    "tecnologias de informacion y comunicacion": "tic",
    "trabajo infantil": "trabajo_infantil",
}


def _texto(elemento) -> str:
    return re.sub(r"\s+", " ", (elemento.text or "")).strip() if elemento is not None else ""


def main() -> None:
    if len(sys.argv) > 1:
        raiz = ET.parse(sys.argv[1]).getroot()
    else:
        r = requests.get(DDI.format(c=CATALOGO), timeout=180)
        r.raise_for_status()
        raiz = ET.fromstring(r.content)
    ns = raiz.tag.split("}")[0].strip("{")
    q = lambda s: f"{{{ns}}}{s}"  # noqa: E731
    capitulo = {}
    for archivo in raiz.iterfind(f".//{q('fileDscr')}"):
        nombre = strip_accents(_texto(archivo.find(f".//{q('fileName')}")).replace(".NSDstat", ""))
        if nombre in CAPITULOS:
            capitulo[archivo.get("ID")] = CAPITULOS[nombre]
    if faltan := set(CAPITULOS.values()) - set(capitulo.values()):
        raise ValueError(f"El DDI no trae los capítulos {sorted(faltan)}")
    diccionario: dict[str, dict] = {}
    for v in raiz.iterfind(f".//{q('var')}"):
        if v.get("files") not in capitulo:
            continue
        nombre = v.get("name", "").upper()
        if nombre in diccionario:  # las llaves y FEX_C están en todos los capítulos
            diccionario[nombre]["modulos"].append(capitulo[v.get("files")])
            continue
        categorias = {}
        for c in v.iterfind(q("catgry")):
            codigo = _texto(c.find(q("catValu")))
            if codigo and codigo != '"':
                categorias[codigo] = _texto(c.find(q("labl")))
        etiqueta = _texto(v.find(q("labl")))
        pregunta = _texto(v.find(f"{q('qstn')}/{q('qstnLit')}")) or etiqueta
        diccionario[nombre] = {
            "etiqueta": etiqueta,
            "pregunta": pregunta,
            "categorias": categorias,
            "modulos": [capitulo[v.get("files")]],
        }
    SALIDA.write_text(
        json.dumps(diccionario, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"{SALIDA.name}: {len(diccionario)} variables")


if __name__ == "__main__":
    main()
