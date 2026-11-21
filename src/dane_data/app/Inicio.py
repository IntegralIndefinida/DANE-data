"""Punto de entrada de la app: `dane-data app` o `streamlit run src/dane-data/app/Inicio.py`."""

from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="dane-data · Microdatos DANE", page_icon=str(Path(__file__).with_name("logo.svg")), layout="wide"
)

paginas = {
    "": [st.Page("paginas/inicio.py", title="Inicio", icon=":material/home:", default=True)],
    "GEIH · Hogares y mercado laboral": [
        st.Page("paginas/geih_mercado.py", title="Indicadores laborales", icon=":material/groups:"),
        st.Page("paginas/geih_explorar.py", title="Tablas y microdatos", icon=":material/table_chart:"),
    ],
    "EAM · Industria manufacturera": [
        st.Page("paginas/eam_industria.py", title="Indicadores industriales", icon=":material/factory:"),
        st.Page("paginas/eam_microdatos.py", title="Panel y microdatos", icon=":material/dataset:"),
    ],
    "Pobreza monetaria": [
        st.Page("paginas/pobreza.py", title="Pobreza monetaria", icon=":material/savings:"),
    ],
    "Estadísticas Vitales": [
        st.Page("paginas/eevv_vitales.py", title="Nacimientos y defunciones", icon=":material/child_care:"),
    ],
    "EMICRON · Micronegocios": [
        st.Page("paginas/emicron_micronegocios.py", title="Micronegocios", icon=":material/storefront:"),
    ],
    "ECV · Calidad de vida": [
        st.Page("paginas/ecv_calidad.py", title="Calidad de vida y pobreza", icon=":material/home_work:"),
    ],
    "Herramientas": [
        st.Page("paginas/descargar.py", title="Descargar datos", icon=":material/download:"),
        st.Page("paginas/diccionario.py", title="Diccionario de variables", icon=":material/menu_book:"),
        st.Page("paginas/citar.py", title="Cómo citar", icon=":material/format_quote:"),
    ],
}
st.navigation(paginas).run()
