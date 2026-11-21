import streamlit as st

import dane_data as dd
from dane_data.app._ui import (args_py, botones_descarga, codigo, fmt_grande, fmt_num, fmt_pct, indicadores_ecv, ipm_ecv,
                               rutas_actuales, seleccion_ecv, serie_anual)

st.title("Calidad de vida y pobreza multidimensional")
st.caption("**Encuesta Nacional de Calidad de Vida (ECV) del DANE.** Encuesta anual a unos 90.000 hogares, con un capítulo "
           "por tema: vivienda, servicios, salud, educación, trabajo, tecnologías. Las cifras se expanden con el factor de "
           "la encuesta y dan las que publica el DANE.")
sel = seleccion_ecv()
anios = sel["anios"]
rutas = rutas_actuales()
st.caption(f"**Datos:** {sel['descripcion']}")

INDICADORES = {
    "Personas por hogar": ("personas_por_hogar", "numero"),
    "Hogares con internet (%)": ("pct_internet_hogar", "pct"),
    "Hogares con energía eléctrica (%)": ("pct_energia", "pct"),
    "Hogares con acueducto (%)": ("pct_acueducto", "pct"),
    "Hogares con alcantarillado (%)": ("pct_alcantarillado", "pct"),
    "Hogares con recolección de basuras (%)": ("pct_recoleccion_basuras", "pct"),
    "Hogares con gas natural (%)": ("pct_gas_natural", "pct"),
    "Hogares en vivienda propia, totalmente pagada (%)": ("pct_propia_pagada", "pct"),
    "Hogares en arriendo (%)": ("pct_arriendo", "pct"),
    "Hogares cuyo jefe o cónyuge se considera pobre (%)": ("pct_se_considera_pobre", "pct"),
    "Personas afiliadas a salud (%)": ("pct_afiliados", "pct"),
    "Afiliados al régimen subsidiado (%)": ("pct_subsidiado", "pct"),
    "Asistencia escolar de 6 a 21 años (%)": ("pct_asistencia_6_21", "pct"),
    "Asistencia escolar de 17 a 21 años (%)": ("pct_asistencia_17_21", "pct"),
    "Años promedio de educación (5 años y más)": ("anios_educacion_5_mas", "numero"),
    "Años promedio de educación (25 a 34 años)": ("anios_educacion_25_34", "numero"),
    "Personas que usan internet (5 años y más, %)": ("pct_usa_internet", "pct"),
    "Personas que usan computador (5 años y más, %)": ("pct_usa_computador", "pct"),
    "Personas que usan celular (5 años y más, %)": ("pct_usa_celular", "pct"),
}
DESAGREGAR = {"Total nacional": None, "Área": "area", "Región": "region", "Departamento": "departamento"}
PRIVACIONES = {
    "logro_educativo": "Bajo logro educativo", "analfabetismo": "Analfabetismo",
    "inasistencia_escolar": "Inasistencia escolar", "rezago_escolar": "Rezago escolar",
    "atencion_integral": "Barreras a servicios para la primera infancia", "trabajo_infantil": "Trabajo infantil",
    "desempleo_larga_duracion": "Desempleo de larga duración", "empleo_formal": "Trabajo informal",
    "aseguramiento_salud": "Sin aseguramiento en salud", "barreras_acceso_salud": "Barreras de acceso a servicios de salud",
    "acueducto": "Sin acceso a fuente de agua mejorada", "alcantarillado": "Inadecuada eliminación de excretas",
    "pisos": "Material inadecuado de pisos", "paredes": "Material inadecuado de paredes exteriores",
    "hacinamiento": "Hacinamiento crítico",
}
VARIABLES_IPM = {
    "Incidencia (% de personas en pobreza multidimensional)": ("incidencia", "pct"),
    "IPM (incidencia ajustada, de 0 a 1)": ("ipm", "numero"),
    "Intensidad (% de privaciones de los pobres)": ("intensidad", "pct"),
    **{f"Hogares con privación: {nombre.lower()} (%)": (f"pct_{clave}", "pct") for clave, nombre in PRIVACIONES.items()},
}
DESAGREGAR_IPM = {"Total nacional": None, "Área": "area", "Región (como el DANE)": "region_ipm",
                  "Departamento": "departamento", "Sexo del jefe del hogar": "sexo_jefe"}

vista = st.radio("Vista", ["Indicadores", "Pobreza multidimensional (IPM)"], horizontal=True)

# ---------------------------------------------------------------- Indicadores
if vista == "Indicadores":
    try:
        total = indicadores_ecv(anios, None, rutas)
    except ValueError as e:  # faltan los factores de 2018
        st.warning(f"{e} También se puede en Descargar datos.")
        st.stop()
    u = total.iloc[-1]
    st.markdown(f"##### Resumen {int(u['anio'])}")
    k = st.columns(4)
    k[0].metric("Hogares", fmt_grande(u.hogares))
    k[1].metric("Personas por hogar", fmt_num(u.personas_por_hogar, 2))
    k[2].metric("Hogares con internet", fmt_pct(u.get("pct_internet_hogar")))
    k[3].metric("Afiliados a salud", fmt_pct(u.get("pct_afiliados")))
    st.divider()

    c1, c2 = st.columns(2)
    nombre = c1.selectbox("Variable", list(INDICADORES))
    nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR))
    columna, tipo_valor = INDICADORES[nombre]
    por = DESAGREGAR[nombre_por]
    res = indicadores_ecv(anios, por, rutas) if por else total
    if columna not in res.columns:
        st.warning("Faltan los capítulos de la ECV que necesita esta variable: bájelos en Descargar datos.")
    else:
        serie_anual(res, columna, por, tipo_valor, nombre, (f"Por {nombre_por.lower()} · " if por else "") + sel["descripcion"],
                    "ecv")
    with st.expander("Tabla completa", icon=":material/table:"):
        st.dataframe(res, hide_index=True, width="stretch",
                     column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
        botones_descarga(res, f"ecv_{anios[0]}_{anios[-1]}", "ecvind")
    codigo(f"""
import dane_data as dd

res = dd.ecv.serie_indicadores({anios!r}{args_py(por=por)})
res
""")

# ---------------------------------------------------------------- IPM
else:
    try:
        total = ipm_ecv(anios, None, rutas)
    except ValueError as e:  # le falta un capítulo a algún año
        st.warning(f"{e} También se puede en Descargar datos.")
        st.stop()
    u = total.iloc[-1]
    st.markdown(f"##### Resumen {int(u['anio'])}")
    k = st.columns(4)
    k[0].metric("Personas en pobreza multidimensional", fmt_pct(u.incidencia))
    k[1].metric("Intensidad", fmt_pct(u.intensidad), help="Porcentaje promedio de privaciones de las personas pobres.")
    k[2].metric("IPM", fmt_num(u.ipm, 3), help="Incidencia ajustada: incidencia por intensidad.")
    k[3].metric("Personas pobres", fmt_grande(u.personas_pobres))
    st.divider()

    c1, c2 = st.columns(2)
    nombre = c1.selectbox("Variable", list(VARIABLES_IPM))
    nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR_IPM))
    columna, tipo_valor = VARIABLES_IPM[nombre]
    por = DESAGREGAR_IPM[nombre_por]
    res = ipm_ecv(anios, por, rutas) if por else total
    serie_anual(res, columna, por, tipo_valor, nombre, (f"Por {nombre_por.lower()} · " if por else "") + sel["descripcion"],
                "ipm")
    st.caption("Como el DANE: el total nacional y por área van sin la parte rural de los ocho departamentos de la "
               "Orinoquía-Amazonía; las regiones y los departamentos, con toda la muestra.")
    with st.expander("Las 15 privaciones y sus pesos", icon=":material/menu_book:"):
        st.markdown("Un hogar es **pobre** si su puntaje, la suma ponderada de sus privaciones, es de **5/15 (33,3 %) o más**, "
                    "y todas sus personas lo son. Cada dimensión pesa 20 %, repartido por igual entre sus privaciones.")
        st.dataframe([{"Dimensión": dimension, "Privación": PRIVACIONES[clave], "Peso": fmt_pct(100 * peso)}
                      for clave, (dimension, peso) in dd.ecv.PRIVACIONES.items()], hide_index=True)
    with st.expander("Tabla completa", icon=":material/table:"):
        st.dataframe(res, hide_index=True, width="stretch",
                     column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
        botones_descarga(res, f"ipm_{anios[0]}_{anios[-1]}", "ecvipm")
    codigo(f"""
import dane_data as dd

res = dd.ecv.serie_ipm({anios!r}{args_py(por=por)})
res
""")
