import streamlit as st

import dane_data as dd
from dane_data.app._ui import (AYUDA_ANIOS, MAX_SERIES, args_py, barras, botones_descarga, codigo, disponibles_pobreza,
                               fmt_grande, fmt_num, fmt_pct, grafico, indicadores_pobreza, linea, rutas_actuales, sin_datos)

st.title("Pobreza monetaria")
st.caption("**Medición de Pobreza Monetaria y Desigualdad del DANE.** Sale de la GEIH: el DANE calcula el ingreso per cápita "
           "de cada hogar y lo compara con la línea de pobreza de su ciudad o zona. Las cifras son de personas.")
rutas = rutas_actuales()
av = disponibles_pobreza(rutas)
anios_disp = sorted(int(a) for a in av.anio.dropna()) if len(av) else []  # las filas del empalme no tienen año
if not anios_disp:
    sin_datos("pobreza monetaria", "No se encontraron datos de la pobreza monetaria en la carpeta configurada.")
# Los que usa load(empalme=True); el departamental de 2021 es opcional
hay_empalme = {"empalme_2012_2020", "lineas_2012_2018", "hogares_empalmado_2021"} <= set(av.archivo)

with st.sidebar:
    st.header("Pobreza monetaria")
    lo, hi = st.select_slider("Años", options=anios_disp, value=(anios_disp[0], anios_disp[-1]), key="pobreza_rango",
                              help=AYUDA_ANIOS) if len(anios_disp) > 1 else (anios_disp[0], anios_disp[0])
    anios = [a for a in anios_disp if lo <= a <= hi]
    empalme = st.toggle("Serie empalmada (comparable 2012–2025)", value=hay_empalme, disabled=not hay_empalme,
                        key="pobreza_empalme",
                        help="La serie que publica el DANE: lleva 2012–2021 al marco 2018 y a las líneas actualizadas. "
                             "Sin ella, 2012–2018 (líneas MESEP) y 2019 en adelante no se pueden comparar."
                        if hay_empalme else "Baje los archivos del empalme en Descargar datos para usarla.")
    if not hay_empalme:
        st.caption("Sin los archivos del empalme solo se puede ver la serie sin empalmar.")

DESAGREGAR = {"Total nacional": None, "Zona": "zona", "Gran dominio": "grupo_dominio", "Ciudad o dominio": "dominio",
              "Departamento": "departamento"}
INDICADORES = {
    "Incidencia de la pobreza (%)": ("incidencia", "pct"),
    "Incidencia de la pobreza extrema (%)": ("incidencia_extrema", "pct"),
    "Brecha de la pobreza (%)": ("brecha", "pct"), "Brecha de la pobreza extrema (%)": ("brecha_extrema", "pct"),
    "Severidad de la pobreza (%)": ("severidad", "pct"), "Severidad de la pobreza extrema (%)": ("severidad_extrema", "pct"),
    "Coeficiente de Gini": ("gini", "numero"), "Ingreso per cápita (pesos al mes)": ("ingreso_pc", "numero"),
    "Línea de pobreza (pesos por persona al mes)": ("linea_pobreza", "numero"),
    "Línea de pobreza extrema (pesos por persona al mes)": ("linea_pobreza_extrema", "numero"),
    "Personas en pobreza": ("pobres", "numero"), "Personas en pobreza extrema": ("pobres_extremos", "numero"),
    "Población": ("personas", "numero"),
}

c1, c2 = st.columns(2)
nombre = c1.selectbox("Indicador", list(INDICADORES))
nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR),
                          help="Por departamento se usa el factor de expansión departamental, como el anexo del DANE.")
columna, tipo_valor = INDICADORES[nombre]
por = DESAGREGAR[nombre_por]
departamental = por == "departamento"
calcular = anios
if departamental and empalme and lo <= 2020:
    calcular = [a for a in anios if a >= 2021]
    st.warning("El DANE publica la serie departamental empalmada desde 2021: los años anteriores no se muestran por "
               "departamento.", icon=":material/warning:")
    if not calcular:
        st.stop()


def cifras(por_: str | None, departamental_: bool):
    try:
        res, avisos = indicadores_pobreza(calcular, por_, empalme, departamental_, rutas)
    except (ValueError, FileNotFoundError) as e:  # p. ej. faltan los archivos del empalme o el factor departamental
        st.error(f"No se pudieron calcular las cifras: {e}")
        st.stop()
    for aviso in avisos:
        st.warning(aviso, icon=":material/warning:")
    return res


total = cifras(None, False)
u = total.iloc[-1]
st.markdown(f"##### Total nacional {int(u['anio'])}")
k = st.columns(4)
k[0].metric("Pobreza monetaria", fmt_pct(u.incidencia), help=dd.pobreza.GLOSARIO["Incidencia"])
k[1].metric("Pobreza extrema", fmt_pct(u.incidencia_extrema), help=dd.pobreza.GLOSARIO["Línea de pobreza extrema"])
k[2].metric("Coeficiente de Gini", fmt_num(u.gini, 3), help=dd.pobreza.GLOSARIO["Coeficiente de Gini"])
k[3].metric("Ingreso per cápita", f"$ {fmt_num(u.ingreso_pc)}", help=dd.pobreza.GLOSARIO["Ingreso per cápita"])
st.caption(f"{fmt_grande(u.pobres)} de personas en pobreza de {fmt_grande(u.personas)}. "
           + ("Serie empalmada al marco 2018." if empalme else "Sin empalme."))
st.divider()

res = cifras(por, departamental) if por else total
g = res[res[columna].notna()].copy()
todos = None
if por:
    todos = g[por]
    g[por] = g[por].astype(str)
subtitulo = (f"Por {nombre_por.lower()} · " if por else "Total nacional · ") + (
    f"{calcular[0]}–{calcular[-1]}" if len(calcular) > 1 else str(calcular[0])) + (" · serie empalmada" if empalme else "")
if por and g["anio"].nunique() == 1:
    grafico(barras(g, x=por, y=columna, pct=tipo_valor == "pct", horizontal=True), f"{nombre}, {g['anio'].iloc[0]}",
            "pobreza", subtitulo)
else:
    if por and g[por].nunique() > MAX_SERIES:
        orden = g.groupby(por)[columna].mean().sort_values(ascending=False).index.tolist()
        elegidos = st.multiselect(f"Hay {len(orden)} grupos; elija hasta {MAX_SERIES}", orden, default=orden[:5],
                                  max_selections=MAX_SERIES, placeholder="Elija los grupos", key=f"pobreza_grupos_{por}")
        g = g[g[por].isin(elegidos)]
    grafico(linea(g, x="anio", y=columna, color=por, pct=tipo_valor == "pct", todos=todos), nombre, "pobreza", subtitulo)

with st.expander("Antes de comparar", icon=":material/info:"):
    st.markdown(
        "- **Sin empalme**, 2012–2018 usa las líneas de la MESEP y 2019 en adelante las actualizadas; hasta 2021 la GEIH "
        "usa el marco del censo 2005 y desde 2022 el del CNPV 2018. Solo la serie empalmada se compara en 2012–2025.\n"
        "- **Por departamento**, las cifras usan el factor departamental (como el anexo departamental del DANE), y la serie "
        "empalmada empieza en 2021.\n"
        "- La pobreza se mide en **23 departamentos y Bogotá**: San Andrés, Arauca, Casanare, Putumayo y los de la Amazonía "
        "y la Orinoquía no están.\n"
        "- Las **ciudades** son sus áreas metropolitanas (Medellín A.M., Cali A.M.…), como los dominios del DANE."
    )
with st.expander("Tabla completa", icon=":material/table:"):
    st.dataframe(res, hide_index=True, width="stretch",
                 column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
    botones_descarga(res, f"pobreza_{calcular[0]}_{calcular[-1]}", "pobreza")
with st.expander("Glosario", icon=":material/menu_book:"):
    for clave, texto in dd.pobreza.GLOSARIO.items():
        st.markdown(f"**{clave}.** {texto}")
codigo(f"""
import dane_data as dd

res = dd.pobreza.serie_indicadores({calcular!r}{args_py(por=por, empalme=empalme, departamental=departamental)})
res
""")
