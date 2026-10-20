import pandas as pd
import streamlit as st

import dane_data as dd
from dane_data.app._ui import (MAX_SERIES, barras, botones_descarga, codigo, fmt_num, fmt_pct, grafico,
                             linea, selector_eam)

st.title("🏭 Indicadores de la industria manufacturera")
eam, descripcion, params = selector_eam(clave="eam")
st.caption(f"**Datos:** EAM {descripcion} · {fmt_num(len(eam))} registros establecimiento-año")

VARIABLES = {
    "Valor agregado": ("valor_agregado", "monetaria"),
    "Producción bruta": ("produccion_bruta", "monetaria"),
    "Personal ocupado total": ("personal_total", "personas"),
    "Productividad laboral (VA por persona)": ("productividad_laboral", "monetaria"),
    "Remuneración media por empleado": ("remuneracion_media", "monetaria"),
    "Participación laboral en el VA (%)": ("participacion_laboral", "pct"),
    "Valor agregado / producción (%)": ("tasa_valor_agregado", "pct"),
    "Número de establecimientos": ("establecimientos", "conteo"),
    "Inversión bruta": ("inversion_bruta", "monetaria"),
    "Activos fijos": ("activos_fijos", "monetaria"),
    "Energía eléctrica (kWh)": ("energia_kwh", "conteo"),
}
DESAGREGAR = {"Total industria": None, "Sector (división CIIU)": "sector", "Departamento": "departamento"}

# ---------------------------------------------------------------- KPIs
tot = dd.eam.resumen(eam, por="anio")
u = tot.iloc[-1]
p = tot.iloc[-2] if len(tot) > 1 else None


def var(col, pp=False):
    if p is None or pd.isna(p[col]) or p[col] == 0:
        return None
    return f"{u[col] - p[col]:+.1f} p.p." if pp else f"{100 * (u[col] / p[col] - 1):+.1f} % vs {int(p['anio'])}"


st.markdown(f"##### Resumen {int(u['anio'])}")
k = st.columns(5)
k[0].metric("Establecimientos", fmt_num(u.establecimientos), var("establecimientos"))
k[1].metric("Personal ocupado", fmt_num(u.personal_total), var("personal_total"))
k[2].metric("Valor agregado (billones $)", fmt_num(u.valor_agregado / 1e9, 1), var("valor_agregado"),
            help="Pesos corrientes. Los microdatos de la EAM vienen en miles de pesos.")
k[3].metric("Productividad (millones $/persona)", fmt_num(u.productividad_laboral / 1e3, 1), var("productividad_laboral"),
            help=dd.eam.GLOSARIO["Productividad laboral"])
k[4].metric("Participación laboral", fmt_pct(u.participacion_laboral), var("participacion_laboral", pp=True),
            help=dd.eam.GLOSARIO["Participación laboral"])
st.divider()

# ---------------------------------------------------------------- Gráfico
c1, c2, c3 = st.columns([2, 2, 1.3])
nombre_var = c1.selectbox("Variable", list(VARIABLES))
nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR))
vista = c3.radio("Vista", ["Evolución", "Un año"], horizontal=True)
col, tipo = VARIABLES[nombre_var]
por = DESAGREGAR[nombre_por]

res = dd.eam.resumen(eam, por=["anio"] + ([por] if por else []))
# Escala para graficar: los microdatos vienen en miles de pesos.
POR_PERSONA = ("productividad_laboral", "remuneracion_media")
if tipo == "monetaria":
    div, unidad = (1e3, "millones de $ por persona") if col in POR_PERSONA else (1e6, "miles de millones de $")
    res["_y"] = res[col] / div
else:
    unidad = None
    res["_y"] = res[col]
if por:
    res = res[res[por].notna()]
    revs = eam.groupby("anio")["ciiu_rev"].first().nunique()
    if por == "sector" and revs > 1 and vista == "Evolución":
        st.warning("⚠️ Los años elegidos mezclan revisiones de la CIIU: los sectores cambian de definición y "
                   "las series se cortan. Elija años de una sola revisión (p. ej. 2012 en adelante).")
    if por == "sector":
        st.warning("⚠️ Para anonimizar, el ANDA publica muchos establecimientos grandes con el código residual "
                   "«otras industrias manufactureras» (3290, 3699 o 3909): **Otras manufacturas** sale inflada y "
                   "las demás divisiones, subestimadas (en 2024, bebidas suma 5,3 % del valor agregado frente a "
                   "9,7 % en el anexo del DANE). En 2016–2017 el código se trunca y la división sí es la real, "
                   "así que las series saltan. Para la composición por sector, use los anexos del DANE.")

if vista == "Evolución":
    indice = False
    if tipo == "monetaria":
        indice = st.toggle("Ver como índice (primer año = 100)",
                           help="Los valores están en pesos corrientes: incluyen inflación. El índice facilita "
                                "comparar crecimientos entre grupos de distinto tamaño.")
    g = res.copy()
    if por and g[por].nunique() > MAX_SERIES:
        orden = g.groupby(por)[col].sum().sort_values(ascending=False).index.tolist()
        elegidos = st.multiselect(f"Hay {len(orden)} grupos; elija hasta {MAX_SERIES}", orden, default=orden[:5],
                                  max_selections=MAX_SERIES)
        g = g[g[por].isin(elegidos)]
    y, titulo = "_y", nombre_var + (f" ({unidad})" if unidad else "")
    if indice:
        base = g.sort_values("anio").groupby(por)[col].transform("first") if por else g[col].iloc[0]
        g["indice"] = 100 * g[col] / base
        y, titulo = "indice", f"{nombre_var} (índice, {g['anio'].min()} = 100)"
    grafico(linea(g, x="anio", y=y, color=por, titulo_y=titulo, pct=tipo == "pct"))
else:
    anio = st.select_slider("Año", sorted(res["anio"].unique()), value=res["anio"].max())
    g = res[res["anio"] == anio]
    if por:
        grafico(barras(g, x=por, y="_y", titulo_y=nombre_var + (f" ({unidad})" if unidad else ""),
                       pct=tipo == "pct", horizontal=True))
        if tipo in ("monetaria", "personas", "conteo") and col not in ("productividad_laboral", "remuneracion_media"):
            top = g.sort_values(col, ascending=False).head(3)
            share = 100 * top[col].sum() / g[col].sum()
            st.caption(f"Los 3 primeros ({', '.join(top[por].astype(str))}) concentran el **{fmt_pct(share)}** "
                       f"del total en {anio}.")
    else:
        v = g[col].iloc[0]
        st.metric(nombre_var + (f" ({unidad})" if unidad else ""),
                  fmt_pct(v) if tipo == "pct" else fmt_num(g["_y"].iloc[0], 1))

if tipo == "monetaria":
    st.caption("💡 Valores en **pesos corrientes**: incluyen inflación (los microdatos vienen en miles de pesos). Para comparar en términos reales use un deflactor "
               "(IPP o deflactor del PIB) con `dd.eam.deflactar` en Python.")

with st.expander("📋 Tabla completa"):
    res = res.drop(columns="_y")
    st.dataframe(res, hide_index=True, width="stretch",
                 column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
    botones_descarga(res, f"resumen_eam_{params['anios'][0]}_{params['anios'][-1]}", "eamres")

with st.expander("📖 Glosario"):
    for k_, v in dd.eam.GLOSARIO.items():
        st.markdown(f"**{k_}.** {v}")

codigo(f'''
import dane_data as dd

{params["carga"]}
res = dd.eam.resumen(eam, por={["anio"] + ([por] if por else [])!r})
res
''')
