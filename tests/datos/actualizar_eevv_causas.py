"""
Regenera ``src/dane_data/data/eevv_causas.json`` con los nombres de las listas de causas de defunción.

    uv run --extra app python tests/datos/actualizar_eevv_causas.py [ANEXO.xlsx]

El DDI no trae los nombres de ``CAUSA_667`` ni de ``CAU_HOMOL``: salen de los cuadros de defunciones no fetales del
DANE, el 5 (lista 6/67 de la OPS) y el 12 (lista Colombia 105), del total nacional. Sin argumento se baja el anexo de 2025.
"""

from __future__ import annotations

import json
import re
import sys
import tempfile
from pathlib import Path

import pandas as pd
import requests

ANEXO = ("https://www.dane.gov.co/files/operaciones/EEVV/2026/24-sep-2026/"
         "anex-EEVV-DefuncionesNoFetalesCuadroUnificado-2025.xlsx")
SALIDA = Path(__file__).parents[2] / "src" / "dane_data" / "data" / "eevv_causas.json"
CODIGO = re.compile(r"^(\d{3})\s+(.+)$", re.S)


def _lista(libro: pd.ExcelFile, hoja: str, esperados: int) -> dict[str, str]:
    """Los códigos del primer bloque del cuadro, el del total nacional: los siguientes repiten por departamento."""
    tabla = libro.parse(hoja, header=None)
    lista: dict[str, str] = {}
    for fila in tabla.itertuples(index=False):
        for celda in fila:
            if isinstance(celda, str) and (m := CODIGO.match(celda.strip())):
                if m.group(1) in lista:
                    if len(lista) != esperados:
                        raise ValueError(f"{hoja}: {len(lista)} causas; se esperaban {esperados}")
                    return dict(sorted(lista.items()))
                lista[m.group(1)] = re.sub(r"\s+", " ", m.group(2)).strip()
                break
    raise ValueError(f"{hoja}: no se encontró el final del primer bloque")


def main() -> None:
    with tempfile.TemporaryDirectory() as t:
        if len(sys.argv) > 1:
            archivo = Path(sys.argv[1])
        else:
            archivo = Path(t) / "anexo.xlsx"
            r = requests.get(ANEXO, timeout=300)
            r.raise_for_status()
            archivo.write_bytes(r.content)
        libro = pd.ExcelFile(archivo, engine="openpyxl")
        causas = {"667": _lista(libro, "Cuadro5", 67), "105": _lista(libro, "Cuadro12", 105)}
    SALIDA.write_text(json.dumps(causas, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{SALIDA.name}: {len(causas['667'])} causas 6/67 y {len(causas['105'])} de la lista 105")


if __name__ == "__main__":
    main()
