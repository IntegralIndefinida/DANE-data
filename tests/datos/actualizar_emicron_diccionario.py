"""
Regenera el diccionario de la EMICRON (``src/dane_data/data/emicron_diccionario.json``) desde el
DDI del ANDA.

    uv run python tests/datos/actualizar_emicron_diccionario.py [ARCHIVO_DDI.xml]

Sin argumento se baja el DDI de 2024, el último año con cobertura nacional (2025 solo cubre las 24
ciudades). Se guarda tal como lo publica el DANE, salvo las categorías sin etiqueta, que no dicen
nada. Las variables que repiten los módulos (CLASE_TE, COD_DEPTO, AREA, F_EXP y la clave) quedan
una vez, con la etiqueta de su primer módulo y la lista de todos los módulos que las traen.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

CATALOGO = 875  # 2024
DDI = "https://microdatos.dane.gov.co/index.php/metadata/export/{c}/ddi"
SALIDA = Path(__file__).parents[2] / "src" / "dane_data" / "data" / "emicron_diccionario.json"


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
    archivos = {
        f.get("ID"): _texto(f.find(f".//{q('fileName')}"))
        for f in raiz.iterfind(f".//{q('fileDscr')}")
    }
    d: dict[str, dict] = {}
    for v in raiz.iterfind(f".//{q('var')}"):
        nombre = v.get("name", "").upper()
        modulo = archivos.get(v.get("files"), "")
        if nombre in d:
            if modulo not in d[nombre]["modulos"]:
                d[nombre]["modulos"].append(modulo)
            continue
        categorias = {}
        for c in v.iterfind(q("catgry")):
            codigo, etiqueta = _texto(c.find(q("catValu"))), _texto(c.find(q("labl")))
            if codigo and etiqueta and codigo.lower() != "sysmiss":
                categorias[codigo] = etiqueta
        etiqueta = _texto(v.find(q("labl")))
        pregunta = _texto(v.find(f"{q('qstn')}/{q('qstnLit')}")) or etiqueta
        d[nombre] = {
            "etiqueta": etiqueta,
            "pregunta": pregunta,
            "categorias": categorias,
            "modulos": [modulo],
        }
    if len(d) < 300:
        raise ValueError(f"El DDI trae solo {len(d)} variables: ¿es el de la EMICRON?")
    SALIDA.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{SALIDA.name}: {len(d)} variables")


if __name__ == "__main__":
    main()
