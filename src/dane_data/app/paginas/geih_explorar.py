import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dane_data as dd
from dane_data.app._ui import (fmt_num, MAX_SERIES, PALETA, _estilo, barras, botones_descarga, codigo, fmt_pct,
                             fmt_pesos, grafico, selector_geih)

st.title("🔎 Tablas y microdatos GEIH")

# Variables DANE adicionales (se cargan además de las armonizadas)
dic = dd.diccionario("geih")
opciones_extra = sorted(v for v in dic if v not in dd.geih.CORE_RAW)
with st.sidebar:
    extra = st.multiselect(
        "Variables DANE adicionales", opciones_extra, key="exp_extra",
        format_func=lambda v: f"{v} — {dic[v]['etiqueta'][:60]}",
        help="Busque por código o por texto de la pregunta (p. ej. 'arriendo', 'P6500'). "
             "Nombres según el diccionario 2025; en años antiguos algunas no existen.",
    )
df, descripcion, params = selector_geih(extra=tuple(extra), clave="exp")

POBLACIONES = {
    "Toda la población": None,
    "En edad de trabajar (PET)": "pet",
    "Fuerza de trabajo": "fuerza_trabajo",
    "Ocupados": "ocupado",
    "Desocupados": "desocupado",
    "Inactivos": "inactivo",
}
pob = st.radio("Población", list(POBLACIONES), horizontal=True, index=3)
if POBLACIONES[pob]:
    df = df[df[POBLACIONES[pob]] == 1]
st.caption(f"**Datos:** {descripcion} · {pob.lower()} · {fmt_num(len(df))} personas en la muestra")

CATEGORICAS = {
    "Año": "anio", "Mes": "mes", "Sexo": "sexo", "Zona": "zona", "Grupo de edad": "grupo_edad",
    "Nivel educativo": "nivel_educativo", "Departamento": "departamento",
    "Condición de actividad": "condicion", "Posición ocupacional": "posicion_ocupacional",
    "Formal (seguridad social)": "formal", "Jefe de hogar": "jefe_hogar",
    "Rama de actividad (2 díg.)": "rama2d",
}
NUMERICAS = {
    "Ingreso laboral": "ingreso_laboral", "Ingreso / salario mínimo": "ratio_smlv",
    "Horas trabajadas por semana": "horas_semana", "Edad": "edad",
}
for v in extra:
    if v in df.columns:
        if pd.api.types.is_numeric_dtype(df[v]) and df[v].nunique() > 15:
            NUMERICAS[f"{v} — {dic[v]['etiqueta'][:40]}"] = v
        else:
            CATEGORICAS[f"{v} — {dic[v]['etiqueta'][:40]}"] = v

tab1, tab2, tab3 = st.tabs(["📊 Tabla ponderada", "💰 Ingresos y salario mínimo", "🗂️ Microdatos"])

# ---------------------------------------------------------------- Tabla ponderada
with tab1:
    c1, c2, c3 = st.columns(3)
    estad = c1.selectbox("¿Qué quiere calcular?", ["Distribución (%)", "Número de personas", "Promedio de…",
                                                    "Mediana de…"])
    filas = c2.selectbox("Filas", list(CATEGORICAS), index=2)
    cols_opts = ["(ninguna)"] + [k for k in CATEGORICAS if k != filas]
    columnas = c3.selectbox("Columnas / comparar por", cols_opts, index=cols_opts.index("Año"))
    variable = None
    if estad in ("Promedio de…", "Mediana de…"):
        variable = NUMERICAS[st.selectbox("Variable", list(NUMERICAS))]

    f, c = CATEGORICAS[filas], (CATEGORICAS[columnas] if columnas != "(ninguna)" else None)
    por = [c, f] if c else [f]
    est = {"Distribución (%)": "porcentaje", "Número de personas": "total", "Promedio de…": "media",
           "Mediana de…": "mediana"}[estad]
    d = df[df[f].notna()] if f in df.columns else df
    t = dd.tabla(d, por=por, variable=variable, estadistico=est)
    valor = {"porcentaje": "porcentaje", "total": "total", "media": "media", "mediana": "mediana"}[est]

    if c:
        t[c] = t[c].astype(str)
    t[f] = t[f].astype(str)
    if c and t[c].nunique() <= MAX_SERIES:
        fig = barras(t, x=f, y=valor, color=c, pct=est == "porcentaje", horizontal=t[f].nunique() > 8)
    else:
        fig = barras(t, x=f, y=valor, pct=est == "porcentaje", horizontal=t[f].nunique() > 8)
    grafico(fig)

    if c:
        pivot = t.pivot(index=f, columns=c, values=valor)
        st.dataframe(pivot.style.format("{:,.1f}" if est == "porcentaje" else "{:,.0f}"), width="stretch")
    else:
        st.dataframe(t, hide_index=True, width="stretch")
    if (t["n_muestra"] < 100).any():
        st.warning("⚠️ Algunas celdas tienen menos de 100 observaciones: interprételas con cautela.")
    st.caption("Distribución (%): porcentaje de cada fila dentro de cada columna. Cifras ponderadas con el "
               "factor de expansión (promedio mensual).")
    botones_descarga(t, "tabla_geih", "tab")
    codigo(f'''
import dane_data as dd

{params["carga"]}
{f'df = df[df["{POBLACIONES[pob]}"] == 1]  # {pob}' if POBLACIONES[pob] else ''}
dd.tabla(df, por={por!r}{f', variable="{variable}"' if variable else ''}, estadistico="{est}")
''')

# ---------------------------------------------------------------- Ingresos
with tab2:
    oc = df[(df["ocupado"] == 1) & (df["ingreso_laboral"] > 0)]
    if oc.empty:
        st.info("No hay ocupados con ingreso en la selección (la GEIH 2007 no trae ingresos laborales).")
    else:
        w = dd.stats.peso_mensual_promedio(oc)
        r = oc["ratio_smlv"]
        tramos = pd.cut(r, [0, 0.5, 0.95, 1.05, 1.22, 1.5, 2, 4, np.inf],
                        labels=["< 0,5", "0,5–0,95", "≈ 1 (0,95–1,05)", "1,05–1,22", "1,22–1,5", "1,5–2", "2–4",
                                "4 o más"])
        dist = (w.groupby(tramos, observed=False).sum() / w.sum() * 100).rename("porcentaje").reset_index()
        dist.columns = ["Salarios mínimos", "porcentaje"]

        k = st.columns(3)
        k[0].metric("Ingreso mediano", fmt_pesos(dd.weighted_quantile(oc.ingreso_laboral, w, 0.5)))
        k[1].metric("Ganan menos de 1 SMLV", fmt_pct(100 * w[r < 0.95].sum() / w.sum()))
        k[2].metric("Ganan ≈ 1 SMLV (±5 %)", fmt_pct(100 * w[(r >= 0.95) & (r <= 1.05)].sum() / w.sum()),
                    help="La acumulación en el mínimo muestra cuánto 'muerde' el salario mínimo.")

        st.markdown("**Distribución de los ocupados según su ingreso en salarios mínimos**")
        grafico(barras(dist, x="Salarios mínimos", y="porcentaje", titulo_y="% de ocupados", pct=True))

        st.markdown("**Histograma del ingreso / salario mínimo** (hasta 4 SMLV)")
        rr = r[r <= 4]
        hist, edges = np.histogram(rr, bins=80, weights=w[r <= 4])
        fig = go.Figure(go.Bar(x=(edges[:-1] + edges[1:]) / 2, y=100 * hist / w.sum(), marker_color=PALETA[0],
                               marker_line_width=0,
                               hovertemplate="%{x:.2f} SMLV: %{y:.2f} %<extra></extra>"))
        fig.add_vline(x=1, line_dash="dash", line_width=1.5, line_color="gray",
                      annotation_text="1 salario mínimo", annotation_position="top right")
        fig = _estilo(fig, "% de ocupados", pct=True)
        fig.update_layout(bargap=0.05)
        fig.update_xaxes(title="Ingreso laboral / salario mínimo del año")
        grafico(fig)
        st.caption("Salario mínimo usado por año: " +
                   ", ".join(f"{a}: {fmt_pesos(dd.SMLV.get(a))}" for a in params["anios"]))
        codigo(f'''
import dane_data as dd

{params["carga"]}
oc = df[(df.ocupado == 1) & (df.ingreso_laboral > 0)]
w = dd.stats.peso_mensual_promedio(oc)
(w[oc.ratio_smlv < 0.95].sum() / w.sum()) * 100   # % que gana menos de 1 SMLV
''')

# ---------------------------------------------------------------- Microdatos
with tab3:
    st.markdown("Vista de las primeras filas. Las variables en **minúscula** son armonizadas por `dane-data`; "
                "las de **MAYÚSCULA** son las originales del DANE.")
    armonizadas = ["anio", "mes", "fex", "sexo", "edad", "grupo_edad", "departamento", "zona", "condicion",
                   "formal", "ingreso_laboral", "ratio_smlv", "horas_semana", "posicion_ocupacional",
                   "nivel_educativo", "rama2d"]
    todas = list(df.columns)
    sel = st.multiselect("Columnas", todas, default=[c for c in armonizadas + list(extra) if c in todas])
    st.dataframe(df[sel].head(1000), hide_index=True, width="stretch")
    st.caption(f"{fmt_num(len(df))} filas en total.")
    if len(df) > 300_000:
        st.info("Archivo grande: la exportación puede tardar unos segundos.")
    if st.toggle("Preparar archivos para descargar"):
        botones_descarga(df[sel], "microdatos_geih", "micro")
    st.caption("💡 `fex` es el factor de expansión **mensual**: si junta varios meses, divida por el número "
               "de meses (o use `dd.tabla`, que lo hace solo).")
