"""Punto de entrada de la app: `dane-data app` o `streamlit run src/dane-data/app/Inicio.py`."""

import streamlit as st

st.set_page_config(page_title="dane-data · Microdatos DANE", page_icon="📊", layout="wide")

paginas = {
    "": [st.Page("paginas/inicio.py", title="Inicio", icon="🏠", default=True)],
    "GEIH · Hogares y mercado laboral": [
        st.Page("paginas/geih_mercado.py", title="Indicadores laborales", icon="👥"),
        st.Page("paginas/geih_explorar.py", title="Tablas y microdatos", icon="🔎"),
    ],
    "EAM · Industria manufacturera": [
        st.Page("paginas/eam_industria.py", title="Indicadores industriales", icon="🏭"),
        st.Page("paginas/eam_microdatos.py", title="Panel y microdatos", icon="🧱"),
    ],
    "Herramientas": [
        st.Page("paginas/descargar.py", title="Descargar datos", icon="⬇️"),
        st.Page("paginas/diccionario.py", title="Diccionario de variables", icon="📚"),
        st.Page("paginas/citar.py", title="Cómo citar", icon="📝"),
    ],
}
st.navigation(paginas).run()
