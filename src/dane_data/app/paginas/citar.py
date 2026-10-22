import streamlit as st

import dane_data as dd

# La misma cita que CITATION.cff y docs/citar.md, con la versión instalada
TITULO = "dane-data: microdatos del DANE (GEIH y EAM) listos para analizar"
REPOSITORIO = "https://github.com/IntegralIndefinida/DANE-data"
DOCS = "https://integralindefinida.github.io/DANE-data"

st.title("📝 Cómo citar")
st.markdown(
    "Si usó esta aplicación o la librería en una tesis, un trabajo o un artículo, cite **los datos del DANE** "
    "y **dane-data**. Mencione también las decisiones metodológicas que afecten sus resultados, por ejemplo "
    f"la serie usada (principal o de empalme) y que la informalidad sigue la medición del DANE, disponible "
    f"desde 2022 (vea las [advertencias]({DOCS}/guia/advertencias.html))."
)

st.subheader("dane-data")
st.caption(f"Con la versión instalada en este computador ({dd.__version__}).")
st.markdown("**APA**")
st.code(f"Ramírez, L. (2026). {TITULO} (versión {dd.__version__}) [software]. {REPOSITORIO}",
        language=None, wrap_lines=True)
st.markdown("**BibTeX**")
st.code(
    "@software{dane_data,\n"
    "  author  = {Ramírez, Luis},\n"
    f"  title   = {{{TITULO}}},\n"
    f"  version = {{{dd.__version__}}},\n"
    "  year    = {2026},\n"
    f"  url     = {{{REPOSITORIO}}},\n"
    "}",
    language=None,
)

st.subheader("Los datos")
st.markdown("Cite la encuesta y el catálogo del ANDA que usó:")
st.code(
    "DANE. Gran Encuesta Integrada de Hogares (GEIH) [microdatos]. Archivo Nacional de Datos (ANDA). "
    "https://microdatos.dane.gov.co\n\n"
    "DANE. Encuesta Anual Manufacturera (EAM) [microdatos]. Archivo Nacional de Datos (ANDA). "
    "https://microdatos.dane.gov.co",
    language=None, wrap_lines=True,
)

st.caption(f"En GitHub, el botón *Cite this repository* da la cita en otros formatos. Más en "
           f"[Cómo citar]({DOCS}/citar.html).")
