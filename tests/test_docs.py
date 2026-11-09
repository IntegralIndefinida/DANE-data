"""
La documentación: la referencia cubre toda la API pública, los ejemplos de los docstrings funcionan y los
enlaces {dd} de la guía existen.
"""

import doctest
import importlib
import inspect
import json
import re
from pathlib import Path

import pytest

import dane_data as dd

API = Path(__file__).parent.parent / "docs" / "api"


@pytest.mark.skipif(not API.is_dir(), reason="sin docs/ (por ejemplo, desde el sdist)")
@pytest.mark.parametrize("modulo, pagina, prefijo", [
    (dd, "general.md", "dd."),
    (dd.geih, "geih.md", ""),
    (dd.eam, "eam.md", ""),
    (dd.eevv, "eevv.md", ""),
])
def test_referencia_cubre_all(modulo, pagina, prefijo):
    texto = (API / pagina).read_text(encoding="utf-8")
    assert f".. currentmodule:: {modulo.__name__}\n" in texto
    faltan = []
    for nombre in modulo.__all__:
        objeto = getattr(modulo, nombre)
        if inspect.ismodule(objeto):
            continue
        if callable(objeto):  # funciones y clases
            presente = re.search(rf"^   {nombre}$", texto, re.M)  # entrada de un autosummary
        else:  # constantes: en la tabla de la página
            presente = f"`{prefijo}{nombre}`" in texto
        if not presente:
            faltan.append(nombre)
    assert not faltan, f"Agregue a docs/api/{pagina}: {faltan}"


# Los ejemplos que necesitan los microdatos llevan `# doctest: +SKIP`; los demás se ejecutan aquí.
@pytest.mark.parametrize("modulo", [
    "dane_data.config", "dane_data.stats", "dane_data.referencias", "dane_data._hooks", "dane_data.proyecciones",
    "dane_data.geih", "dane_data.geih.loader", "dane_data.geih.indicadores", "dane_data.geih.agregados",
    "dane_data.eam", "dane_data.eam.loader", "dane_data.eam.indicadores",
    "dane_data.eevv", "dane_data.eevv.loader", "dane_data.eevv.indicadores", "dane_data.eevv.agregados",
])
def test_ejemplos_de_los_docstrings(modulo):
    mod = importlib.import_module(modulo)
    resultado = doctest.testmod(mod, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS, verbose=False)
    assert resultado.failed == 0


# Sphinx publica un {dd}`nombre` que ya no existe como texto sin enlace, sin avisar (nitpicky está apagado)
@pytest.mark.skipif(not API.is_dir(), reason="sin docs/ (por ejemplo, desde el sdist)")
def test_los_enlaces_dd_de_la_guia_existen():
    docs = API.parent
    rotos = []
    for ruta in sorted([*docs.rglob("*.md"), *docs.rglob("*.ipynb")]):
        if {"_build", "_generado", ".ipynb_checkpoints"} & set(ruta.parts):
            continue
        texto = ruta.read_text(encoding="utf-8")
        if ruta.suffix == ".ipynb":
            texto = "\n".join("".join(c["source"]) for c in json.loads(texto)["cells"] if c["cell_type"] == "markdown")
        for nombre in re.findall(r"\{dd\}`([^`]+)`", texto):
            objeto = dd
            for parte in nombre.removesuffix("()").split("."):
                objeto = getattr(objeto, parte, None)
            if objeto is None:
                rotos.append(f"{ruta.relative_to(docs)}: {nombre}")
    assert not rotos, f"{{dd}} que no existen en dane_data: {rotos}"
