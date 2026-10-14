# Configuración de Sphinx para la documentación de dane-data.
#   uv run --extra docs sphinx-build -W -b html docs docs/_build/html
#
# Las páginas de la guía incluyen secciones del README (buscándolas por su título), así que el texto vive en
# un solo lugar. Si cambia el título de una sección del README, actualice el `start-after`/`end-before` de
# la página que la incluye: con -W la compilación falla si no lo encuentra.

import dane_data

project = "dane-data"
author = "Luis Ramírez"
copyright = "Luis Ramírez. Datos: DANE, Archivo Nacional de Datos (ANDA)"
release = dane_data.__version__
version = release
language = "es"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
exclude_patterns = ["_build"]

# Docstrings en estilo NumPy, con las secciones en español.
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_custom_sections = [
    ("Parámetros", "Parameters"),
    ("Devuelve", "Returns"),
    ("Ejemplo", "Examples"),
    ("Ejemplos", "Examples"),
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True

myst_enable_extensions = ["colon_fence"]
myst_heading_anchors = 3

html_theme = "furo"
html_title = f"dane-data {release}"
html_theme_options = {
    "source_repository": "https://github.com/IntegralIndefinida/DANE-data/",
    "source_branch": "main",
    "source_directory": "docs/",
}
