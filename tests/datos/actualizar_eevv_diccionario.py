"""
Regenera los diccionarios de las Estadísticas Vitales (``src/dane_data/data/eevv_*_diccionario.json``) desde el DDI del ANDA.

    uv run python tests/datos/actualizar_eevv_diccionario.py [ARCHIVO_DDI.xml]

Sin argumento se baja el DDI del catálogo más reciente. Son tres diccionarios porque una misma variable cambia de etiqueta
según el certificado (``SEXO`` es «del nacido vivo» o «del fallecido»). Se guardan tal como los publica el DANE: lo que
contradice los datos va en la tabla de diferencias del README.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

CATALOGO = 915  # 2025
DDI = "https://microdatos.dane.gov.co/index.php/metadata/export/{c}/ddi"
SALIDA = Path(__file__).parents[2] / "src" / "dane_data" / "data"
ARCHIVOS = {"Nacimientos": "nacimientos", "Defuncionesfetales": "fetales", "Defuncionesnofetales": "defunciones"}


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
    por_id = {}
    for archivo in raiz.iterfind(f".//{q('fileDscr')}"):
        nombre = _texto(archivo.find(f".//{q('fileName')}")).replace(".NSDstat", "")
        tipo = next((t for clave, t in ARCHIVOS.items() if clave in nombre), None)
        if tipo:
            por_id[archivo.get("ID")] = (tipo, nombre)
    diccionarios: dict[str, dict] = {t: {} for t in ARCHIVOS.values()}
    for v in raiz.iterfind(f".//{q('var')}"):
        if v.get("files") not in por_id:
            continue
        tipo, nombre = por_id[v.get("files")]
        categorias = {}
        for c in v.iterfind(q("catgry")):
            codigo = _texto(c.find(q("catValu")))
            if codigo and codigo != '"':
                categorias[codigo] = _texto(c.find(q("labl")))
        etiqueta = _texto(v.find(q("labl")))
        pregunta = _texto(v.find(f"{q('qstn')}/{q('qstnLit')}")) or etiqueta
        diccionarios[tipo][v.get("name", "").upper()] = {"etiqueta": etiqueta, "pregunta": pregunta, "categorias": categorias,
                                                         "modulos": [f"{nombre}.NSDstat"]}
    for tipo, d in diccionarios.items():
        if not d:
            raise ValueError(f"El DDI no trae variables de {tipo}")
        destino = SALIDA / f"eevv_{tipo}_diccionario.json"
        destino.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"{destino.name}: {len(d)} variables")


if __name__ == "__main__":
    main()
