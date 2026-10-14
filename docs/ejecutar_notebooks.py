"""
Ejecuta los notebooks de la documentación con los microdatos locales y guarda sus salidas.

    uv run --extra docs python docs/ejecutar_notebooks.py              # todos
    uv run --extra docs python docs/ejecutar_notebooks.py desempleo    # los que contengan «desempleo»

El servidor de la documentación no tiene los microdatos: publica los notebooks con las salidas que quedan
guardadas aquí. La figura de la celda con la etiqueta «miniatura» se guarda además en
docs/_static/galeria/<notebook>.png, para la galería de ejemplos y la portada.
"""

import base64
import sys
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient

DOCS = Path(__file__).parent
GALERIA = DOCS / "_static" / "galeria"


def ejecutar(ruta: Path) -> None:
    nb = nbformat.read(ruta, as_version=4)
    NotebookClient(nb, timeout=1800, kernel_name="python3", record_timing=False,
                   resources={"metadata": {"path": str(ruta.parent)}}).execute()
    nbformat.write(nb, ruta)
    for celda in nb.cells:
        if "miniatura" not in celda.metadata.get("tags", []):
            continue
        for salida in celda.get("outputs", []):
            if png := salida.get("data", {}).get("image/png"):
                GALERIA.mkdir(parents=True, exist_ok=True)
                (GALERIA / f"{ruta.stem}.png").write_bytes(base64.b64decode(png))
                break


def main(filtros: list[str]) -> None:
    rutas = sorted([DOCS / "primeros_pasos.ipynb", *(DOCS / "ejemplos").glob("*.ipynb")])
    if filtros:
        rutas = [r for r in rutas if any(f in r.stem for f in filtros)]
    for ruta in rutas:
        inicio = time.time()
        print(f"{ruta.relative_to(DOCS)} ...", end=" ", flush=True)
        ejecutar(ruta)
        print(f"{time.time() - inicio:.0f} s")


if __name__ == "__main__":
    main(sys.argv[1:])
