# Configuración de Sphinx para la documentación de dane-data.
#
#   uv run --extra docs sphinx-build -W -b html docs docs/_build/html
#
# Los notebooks de docs/ (primeros pasos y ejemplos) se publican con las salidas guardadas: el servidor de
# documentación no tiene los microdatos. Para volver a ejecutarlos con los datos locales:
#
#   uv run --extra docs python docs/ejecutar_notebooks.py

import argparse
from pathlib import Path

import pandas as pd
from sphinx.domains.python import PyXRefRole

import dane_data

project = "dane-data"
author = "Luis Ramírez"
copyright = "Luis Ramírez · Código MIT · Datos: DANE, Archivo Nacional de Datos (ANDA)"
release = dane_data.__version__
version = release
language = "es"

extensions = [
    "myst_nb",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.viewcode",
    "sphinx_design",
    "sphinx_copybutton",
]
exclude_patterns = ["_build", "_generado", "**.ipynb_checkpoints", "ejecutar_notebooks.py"]
templates_path = ["_templates"]

# --------------------------------------------------------------------------- #
# Docstrings: estilo NumPy con las secciones en español
# --------------------------------------------------------------------------- #
napoleon_google_docstring = False
napoleon_numpy_docstring = True
napoleon_custom_sections = [
    ("Parámetros", "Parameters"),
    ("Devuelve", "Returns"),
    ("Lanza", "Raises"),
    ("Avisos", "Warns"),
    ("Véase también", "See Also"),
    ("Notas", "Notes"),
    ("Ejemplos", "Examples"),
    ("Ejemplo", "Examples"),
]
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_preserve_defaults = True
autosummary_generate = True
python_use_unqualified_type_names = True
# Para que las anotaciones apunten a la documentación de pandas (pandas.DataFrame, no pandas.core.frame...).
pd.DataFrame.__module__ = "pandas"
pd.Series.__module__ = "pandas"

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pandas": ("https://pandas.pydata.org/docs", None),
    "numpy": ("https://numpy.org/doc/stable", None),
}

# --------------------------------------------------------------------------- #
# MyST y notebooks
# --------------------------------------------------------------------------- #
myst_enable_extensions = ["colon_fence", "dollarmath", "amsmath", "deflist", "attrs_inline", "substitution"]
myst_heading_anchors = 3
myst_substitutions = {"version": release}
nb_execution_mode = "off"
nb_merge_streams = True

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

# --------------------------------------------------------------------------- #
# Tema
# --------------------------------------------------------------------------- #
html_theme = "pydata_sphinx_theme"
html_title = f"dane-data {release}"
html_logo = "_static/logo.svg"
html_favicon = "_static/logo.svg"
html_static_path = ["_static"]
html_css_files = ["dane-data.css"]
html_show_sourcelink = False
html_context = {
    "github_user": "IntegralIndefinida",
    "github_repo": "DANE-data",
    "github_version": "main",
    "doc_path": "docs",
    "default_mode": "light",
}
html_theme_options = {
    "logo": {"text": "dane-data", "alt_text": "dane-data"},
    "navbar_align": "left",
    "header_links_before_dropdown": 6,
    "header_dropdown_text": "Más",
    "icon_links": [
        {"name": "GitHub", "url": "https://github.com/IntegralIndefinida/DANE-data", "icon": "fa-brands fa-github"},
        {"name": "PyPI", "url": "https://pypi.org/project/dane-data/", "icon": "fa-brands fa-python"},
    ],
    "use_edit_page_button": True,
    "show_toc_level": 2,
    "secondary_sidebar_items": ["page-toc", "edit-this-page"],
    "footer_start": ["copyright"],
    "footer_end": ["last-updated"],
    "pygments_light_style": "tango",
    "pygments_dark_style": "github-dark",
}
html_last_updated_fmt = "%d/%m/%Y"
html_sidebars = {
    "index": [],
    "instalacion": [],
    "primeros_pasos": [],
    "novedades": [],
    "citar": [],
    "glosario": [],
}


# --------------------------------------------------------------------------- #
# Páginas generadas: el glosario (dd.geih.GLOSARIO, dd.eam.GLOSARIO), las variables de la EAM
# (dd.eam.ETIQUETAS) y la línea de comandos (cli._parser). Así el texto vive en un solo lugar.
# --------------------------------------------------------------------------- #
def _glosario(nombre: str, terminos: dict[str, str]) -> None:
    lineas = ["```{glossary}", ":sorted:", ""]
    for termino, definicion in terminos.items():
        lineas += [termino, f"   {definicion}", ""]
    _escribir(nombre, "\n".join(lineas + ["```", ""]))


def _escribir(nombre: str, texto: str) -> None:
    destino = Path(__file__).parent / "_generado" / nombre
    destino.parent.mkdir(exist_ok=True)
    if not destino.exists() or destino.read_text(encoding="utf-8") != texto:
        destino.write_text(texto, encoding="utf-8")


_glosario("glosario_geih.md", dane_data.geih.GLOSARIO)
_glosario("glosario_eam.md", dane_data.eam.GLOSARIO)
def _cli() -> str:
    """Referencia de la línea de comandos en español, a partir de los argumentos reales (cli._parser)."""
    from dane_data.cli import _parser

    sub = next(a for a in _parser()._actions if isinstance(a, argparse._SubParsersAction))
    ayudas = {a.dest: a.help for a in sub._choices_actions}
    lineas = []
    for nombre, comando in sub.choices.items():
        uso = comando.format_usage().strip().replace("usage: ", "")
        lineas += [f"### `dane-data {nombre}`", "", f"{ayudas[nombre]}.", "", "```text", uso, "```", ""]
        argumentos = [a for a in comando._actions if not isinstance(a, argparse._HelpAction)]
        if not argumentos:
            continue
        lineas += ["| Argumento | Descripción |", "|---|---|"]
        for a in argumentos:
            nombre_arg = ", ".join(f"`{o}`" for o in a.option_strings) or f"`{a.dest}`"
            texto = (a.help or "").rstrip(".")
            texto += "." if texto else ""
            if a.choices:
                texto += " Opciones: " + ", ".join(f"`{c}`" for c in a.choices) + "."
            if a.default not in (None, False):
                texto += f" Por defecto: `{a.default}`."
            lineas.append(f"| {nombre_arg} | {texto.strip()} |")
        lineas.append("")
    return "\n".join(lineas)


_escribir("cli.md", _cli())
_escribir("eam_variables.md", "| Variable | Contenido |\n|---|---|\n" + "".join(
    f"| `{v}` | {e} |\n" for v, e in dane_data.eam.ETIQUETAS.items()))


# --------------------------------------------------------------------------- #
# Rol {dd}`geih.load()`: enlace a dane_data.geih.load con el texto «dd.geih.load()», como se usa la librería
# --------------------------------------------------------------------------- #
class _RolDD(PyXRefRole):
    def process_link(self, env, refnode, has_explicit_title, title, target):
        title, target = super().process_link(env, refnode, has_explicit_title, title, target)
        target = target.removesuffix("()")
        if not has_explicit_title:
            title = f"dd.{title}"
        return title, f"dane_data.{target}"


def setup(app):
    app.add_role_to_domain("py", "dd", _RolDD())
