"""La referencia de la documentación (docs/api/*.md) cubre toda la API pública."""

import inspect
from pathlib import Path

import pytest

import dane_data as dd

API = Path(__file__).parent.parent / "docs" / "api"


@pytest.mark.parametrize("modulo, pagina, prefijo", [
    (dd, "dane_data.md", "dd."),
    (dd.geih, "geih.md", ""),
    (dd.eam, "eam.md", ""),
])
def test_referencia_cubre_all(modulo, pagina, prefijo):
    texto = (API / pagina).read_text(encoding="utf-8")
    faltan = []
    for nombre in modulo.__all__:
        objeto = getattr(modulo, nombre)
        if inspect.ismodule(objeto):
            continue
        if inspect.isclass(objeto):
            buscado = f".. autoexception:: {modulo.__name__}.{nombre}\n"
        elif callable(objeto):  # también las envueltas en lru_cache
            buscado = f".. autofunction:: {modulo.__name__}.{nombre}\n"
        else:  # constantes: en la tabla de la página
            buscado = f"`{prefijo}{nombre}`"
        if buscado not in texto:
            faltan.append(nombre)
    assert not faltan, f"Agregue a docs/api/{pagina}: {faltan}"
