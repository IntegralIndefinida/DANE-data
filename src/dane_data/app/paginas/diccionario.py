import pandas as pd
import streamlit as st

import dane_data as dd

st.title("Diccionario de variables")
st.markdown(
    "Busque variables por código o por palabras de la pregunta. Las de origen **dane-data** son las armonizadas por la "
    "librería: en minúscula y con el mismo significado en todos los años. Las de origen **DANE** vienen de los "
    "metadatos oficiales (DDI) del año de la columna *ddi*; sus nombres pueden variar en años antiguos."
)

# Una variable de las Estadísticas Vitales cambia de etiqueta según el certificado: un diccionario para cada uno
ENCUESTAS = {"GEIH": "geih", "EAM": "eam", "EMICRON": "emicron", "Defunciones": "eevv_defunciones",
             "Nacimientos": "eevv_nacimientos", "Defunciones fetales": "eevv_fetales", "ECV": "ecv"}
c1, c2 = st.columns([2, 3])
encuesta = c1.radio("Encuesta", list(ENCUESTAS), horizontal=True)
clave = ENCUESTAS[encuesta]
texto = c2.text_input("Buscar", placeholder="p. ej. pensión, arriendo, horas, salarios, P6920")

res = dd.buscar_variable(texto or "", clave)
st.caption(f"{len(res)} variables")
evento = st.dataframe(res, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      column_config={"pregunta": st.column_config.TextColumn(width="large")})

filas = evento.selection.rows if evento and evento.selection else []
if filas and (fila := res.iloc[filas[0]])["origen"] == "dane-data":
    st.subheader(fila["variable"])
    st.markdown(f"**{fila['etiqueta']}**")
    st.caption("Variable armonizada por dane-data: la librería la crea al cargar los datos.")
elif filas:
    var = res.iloc[filas[0]]["variable"]
    info = dd.diccionario(clave)[var]
    st.subheader(var)
    st.markdown(f"**{info['etiqueta']}**")
    if info["pregunta"] and info["pregunta"] != info["etiqueta"]:
        st.markdown(f"> {info['pregunta']}")
    if info.get("modulos"):
        st.caption("Módulo(s): " + ", ".join(m.replace(".NSDstat", "") for m in info["modulos"]))
    if info["categorias"]:
        st.markdown("**Categorías**")
        st.dataframe(pd.DataFrame(list(info["categorias"].items()), columns=["código", "significado"]),
                     hide_index=True)
    if clave.startswith("eevv_"):
        carga = f'df = dd.eevv.load(2025, tipo="{clave.removeprefix("eevv_")}", columnas=["{var}"])'
    elif clave == "ecv":  # el capítulo donde está la variable; Características siempre se carga
        modulo = next((m for m in info["modulos"] if m != "caracteristicas"), None)
        carga = (f'df = dd.ecv.load(2025, columnas=["{var}"])' if modulo is None
                 else f'df = dd.ecv.load(2025, modulos=["{modulo}"], columnas=["{var}"])')
    else:
        carga = f'df = dd.{clave}.load(2024, columnas=["{var if clave == "geih" else var.lower()}"])'
    st.code(carga, language="python")
else:
    st.caption("Seleccione una fila para ver sus categorías.")
