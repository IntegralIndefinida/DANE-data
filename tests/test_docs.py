"""La documentación: la referencia cubre toda la API pública y los ejemplos de los docstrings funcionan."""

import doctest
import importlib
import inspect
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
    "dane_data.config", "dane_data.stats", "dane_data.referencias", "dane_data._hooks",
    "dane_data.geih", "dane_data.geih.loader", "dane_data.geih.indicadores", "dane_data.geih.agregados",
    "dane_data.eam", "dane_data.eam.loader", "dane_data.eam.indicadores",
])
def test_ejemplos_de_los_docstrings(modulo):
    mod = importlib.import_module(modulo)
    resultado = doctest.testmod(mod, optionflags=doctest.NORMALIZE_WHITESPACE | doctest.ELLIPSIS, verbose=False)
    assert resultado.failed == 0
