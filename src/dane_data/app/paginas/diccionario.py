import pandas as pd
import streamlit as st

import dane_data as dd

st.title("📚 Diccionario de variables")
st.markdown(
    "Busque variables por código o por palabras de la pregunta. Fuente: metadatos oficiales del DANE "
    "(GEIH 2025 y EAM 2024). Los nombres pueden variar en años antiguos."
)

c1, c2 = st.columns([1, 3])
encuesta = c1.radio("Encuesta", ["GEIH", "EAM"], horizontal=True)
texto = c2.text_input("Buscar", placeholder="p. ej. pensión, arriendo, horas, salarios, P6920")

res = dd.buscar_variable(texto or "", encuesta.lower())
st.caption(f"{len(res)} variables")
evento = st.dataframe(res, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row",
                      column_config={"pregunta": st.column_config.TextColumn(width="large")})

filas = evento.selection.rows if evento and evento.selection else []
if filas:
    var = res.iloc[filas[0]]["variable"]
    info = dd.diccionario(encuesta.lower())[var]
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
    st.code(f'df = dd.{encuesta.lower()}.load(2024, columns=["{var if encuesta == "GEIH" else var.lower()}"])',
            language="python")
else:
    st.caption("👆 Seleccione una fila para ver sus categorías.")

with st.expander("Variables armonizadas por dane-data (iguales en todos los años)"):
    if encuesta == "GEIH":
        st.markdown("""
| Variable | Descripción |
|---|---|
| `anio`, `mes` | Año y mes de la encuesta |
| `fex` | Factor de expansión mensual (FEX_C18 / FEX_C / FEX_C_2011 según la época) |
| `sexo`, `edad`, `grupo_edad` | Sexo (P3271 o P6020), edad (P6040) y grupos de edad |
| `departamento`, `dpto`, `zona` | Departamento y zona urbana/rural (CLASE) |
| `condicion` | Ocupado / Desocupado / Inactivo / Fuera de la PET |
| `pet`, `fuerza_trabajo`, `ocupado`, `desocupado`, `inactivo` | Indicadoras 0/1 |
| `formal` | 1 si el ocupado es formal según la medición del DANE (desde 2022; vacía antes) |
| `ingreso_laboral`, `ratio_smlv`, `smlv` | INGLABO, su razón frente al salario mínimo y el salario mínimo del año |
| `horas_semana` | Horas trabajadas normalmente (P6800) |
| `posicion_ocupacional` | P6430 con etiquetas |
| `nivel_educativo` | Ninguno / Primaria / Secundaria / Media / Superior (P3042 o P6210) |
| `rama2d`, `rama_rev` | Rama de actividad a 2 dígitos y su revisión CIIU (3 o 4) |
""")
    else:
        st.dataframe([{"variable": k, "descripción": v} for k, v in dd.eam.ETIQUETAS.items()]
                     + [{"variable": "ciiu / ciiu_rev", "descripción": "Código CIIU y su revisión (2, 3 o 4)"},
                        {"variable": "division / sector", "descripción": "CIIU a 2 dígitos y su nombre"},
                        {"variable": "departamento", "descripción": "Nombre del departamento"}], hide_index=True)
