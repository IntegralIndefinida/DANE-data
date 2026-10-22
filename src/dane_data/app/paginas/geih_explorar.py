import hashlib
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import dane_data as dd
from dane_data.app._ui import (fmt_num, MAX_SERIES, PALETA, _barra, _estilo, args_py, barras, botones_descarga,
                             codigo, fmt_pct, fmt_pesos, frecuencias_geih, grafico, muestra_geih, rutas_actuales,
                             seleccion_geih, tabla_geih)

st.title("🔎 Tablas y microdatos GEIH")

POBLACIONES = {
    "Toda la población": None,
    "En edad de trabajar (PET)": "pet",
    "Fuerza de trabajo": "fuerza_trabajo",
    "Ocupados": "ocupado",
    "Desocupados": "desocupado",
    "Inactivos": "inactivo",
}
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

# Variables DANE adicionales: las del diccionario 2025 y las que dane-data lee siempre (CORE_RAW)
dic = dd.diccionario("geih")


def etiqueta(v: str, largo: int) -> str:
    return f"{v} — {dic.get(v, {}).get('etiqueta', '')[:largo]}"


with st.sidebar:
    extra = st.multiselect(
        "Variables DANE adicionales", sorted(set(dic) | set(dd.geih.CORE_RAW)), key="exp_extra",
        format_func=lambda v: etiqueta(v, 60),
        help="Busque por código o por texto de la pregunta (p. ej. 'arriendo', 'P6500'). "
             "Nombres según el diccionario 2025; en años antiguos algunas no existen.",
    )
sel = seleccion_geih(clave="exp")
anios = tuple(sel["anios"])
# Las variables de CORE_RAW se leen siempre: pedirlas en `columns` solo crearía otra caché.
columnas = tuple(sorted(e for e in extra if e not in dd.geih.CORE_RAW))
# Todas las tablas salen de dd.geih.serie_*: año por año y guardadas en disco, nunca todos los años en memoria.
comunes = dict(filtros=sel["filtros"], meses=tuple(sel["meses"]) if sel["meses"] else None, columnas=columnas,
               empalme=sel["empalme"], meses_disp=sel["meses_disponibles"], rutas=rutas_actuales())
args_comunes = args_py(filtros=sel["filtros"], meses=sel["meses"], columns=list(columnas), empalme=sel["empalme"])

pob = st.radio("Población", list(POBLACIONES), horizontal=True, index=3)
poblacion = POBLACIONES[pob]
n_total = int(tabla_geih(anios, (), None, "total", poblacion, dropna=False, **comunes)["n_muestra"].sum())
st.caption(f"**Datos:** {sel['descripcion']} · {pob.lower()} · {fmt_num(n_total)} personas en la muestra")
if not n_total:
    st.warning("Ninguna persona cumple los filtros elegidos.")
    st.stop()

# Un solo mes de microdatos: para saber el tipo de las variables adicionales y para la vista previa.
anio_m, mes_m = next((a, m) for a, m in sel["meses_disponibles"] if not sel["meses"] or m in sel["meses"])
variables = list(dict.fromkeys(["fex", *filter(None, POBLACIONES.values()), *CATEGORICAS.values(),
                                *NUMERICAS.values(), *extra]))
muestra = dd.geih.filtrar(muestra_geih(anio_m, mes_m, tuple(variables), columnas, sel["empalme"], rutas_actuales()),
                          sel["filtros"], poblacion)
for v in extra:
    if v in muestra.columns:
        if pd.api.types.is_numeric_dtype(muestra[v]) and muestra[v].nunique() > 15:
            NUMERICAS[etiqueta(v, 40)] = v
        else:
            CATEGORICAS[etiqueta(v, 40)] = v

tab1, tab2, tab3 = st.tabs(["📊 Tabla ponderada", "💰 Ingresos y salario mínimo", "🗂️ Microdatos"])

# ---------------------------------------------------------------- Tabla ponderada
with tab1:
    c1, c2, c3 = st.columns(3)
    estad = c1.selectbox("¿Qué quiere calcular?", ["Distribución (%)", "Número de personas", "Promedio de…",
                                                    "Mediana de…"])
    filas = c2.selectbox("Filas", list(CATEGORICAS), index=2)
    cols_opts = ["(ninguna)"] + [k for k in CATEGORICAS if k != filas]
    columnas_tabla = c3.selectbox("Columnas / comparar por", cols_opts, index=cols_opts.index("Año"))
    variable = None
    if estad in ("Promedio de…", "Mediana de…"):
        variable = NUMERICAS[st.selectbox("Variable", list(NUMERICAS))]

    f, c = CATEGORICAS[filas], (CATEGORICAS[columnas_tabla] if columnas_tabla != "(ninguna)" else None)
    por = [c, f] if c else [f]
    est = {"Distribución (%)": "porcentaje", "Número de personas": "total", "Promedio de…": "media",
           "Mediana de…": "mediana"}[estad]
    # dropna: sin las personas con valor vacío en filas o columnas (p. ej. la rama de quien no trabaja)
    t = tabla_geih(anios, tuple(por), variable, est, poblacion, dropna=True, **comunes)

    if t.empty:
        st.info("No hay datos para esta combinación (puede ser una variable que esos años no existe).")
    else:
        # Texto para el gráfico; la tabla pivote usa las categorías, que conservan su orden (el nivel
        # educativo de Ninguno a Superior, no alfabético)
        g = t.astype({k: str for k in filter(None, [f, c])})
        if c and g[c].nunique() <= MAX_SERIES:
            fig = barras(g, x=f, y=est, color=c, pct=est == "porcentaje", horizontal=g[f].nunique() > 8)
        else:
            fig = barras(g, x=f, y=est, pct=est == "porcentaje", horizontal=g[f].nunique() > 8)
        grafico(fig)

        if c:
            pivot = t.pivot_table(index=f, columns=c, values=est, observed=True, aggfunc="first")
            pivot.index, pivot.columns = pivot.index.astype(str), pivot.columns.astype(str)  # ya ordenadas
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

# Igual a dd.tabla(...) sobre los microdatos filtrados, pero año por año y guardado en caché.
t = dd.geih.serie_tabla({list(anios)!r}, por={por!r}{args_py(variable=variable)}\
{f', estadistico="{est}"' if est != "total" else ""}{args_py(poblacion=poblacion)}, dropna=True{args_comunes})
t
''')

# ---------------------------------------------------------------- Ingresos
with tab2:
    st.markdown("**Ocupados con ingreso laboral** (con los filtros de la barra lateral)")
    freq = frecuencias_geih(anios, "ingreso_laboral", (), "ocupado", **{**comunes, "columnas": ()})
    oc = freq[freq["ingreso_laboral"] > 0]
    if oc.empty:
        st.info("No hay ocupados con ingreso en la selección (la GEIH 2007 no trae ingresos laborales).")
    else:
        w = oc["peso"]
        r = oc["ingreso_laboral"] / oc["anio"].map(dd.SMLV)
        tramos = pd.cut(r, [0, 0.5, 0.95, 1.05, 1.22, 1.5, 2, 4, np.inf],
                        labels=["< 0,5", "0,5–0,95", "≈ 1 (0,95–1,05)", "1,05–1,22", "1,22–1,5", "1,5–2", "2–4",
                                "4 o más"])
        dist = (w.groupby(tramos, observed=False).sum() / w.sum() * 100).rename("porcentaje").reset_index()
        dist.columns = ["Salarios mínimos", "porcentaje"]

        k = st.columns(3)
        k[0].metric("Ingreso mediano", fmt_pesos(dd.weighted_quantile(oc["ingreso_laboral"], w, 0.5)))
        k[1].metric("Ganan menos de 0,95 SMLV", fmt_pct(100 * w[r < 0.95].sum() / w.sum()),
                    help="Por debajo del tramo ≈ 1 SMLV del indicador siguiente, para no contar a nadie dos veces.")
        k[2].metric("Ganan ≈ 1 SMLV (±5 %)", fmt_pct(100 * w[(r >= 0.95) & (r <= 1.05)].sum() / w.sum()),
                    help="La acumulación en el mínimo muestra cuánto 'muerde' el salario mínimo.")

        st.markdown("**Distribución de los ocupados según su ingreso en salarios mínimos**")
        grafico(barras(dist, x="Salarios mínimos", y="porcentaje", titulo_y="% de ocupados", pct=True))

        st.markdown("**Histograma del ingreso / salario mínimo** (hasta 4 SMLV)")
        hist, edges = np.histogram(r[r <= 4], bins=80, weights=w[r <= 4])
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
                   ", ".join(f"{a}: {fmt_pesos(dd.SMLV.get(a))}" for a in anios))
        codigo(f'''
import dane_data as dd

# Distribución ponderada del ingreso de los ocupados (año por año, guardada en caché)
f = dd.geih.serie_frecuencias({list(anios)!r}, "ingreso_laboral", poblacion="ocupado"\
{args_py(filtros=sel["filtros"], meses=sel["meses"], empalme=sel["empalme"])})
f = f[f.ingreso_laboral > 0]
ratio = f.ingreso_laboral / f.anio.map(dd.SMLV)
dd.weighted_quantile(f.ingreso_laboral, f.peso, 0.5)    # ingreso mediano
100 * f.peso[ratio < 0.95].sum() / f.peso.sum()         # % que gana menos de 1 SMLV
''')

# ---------------------------------------------------------------- Microdatos
with tab3:
    st.markdown(f"Vista previa de **{dd.MESES[mes_m]} {anio_m}**, el primer mes de la selección. Las variables en "
                "**minúscula** son armonizadas por `dane-data`; las de **MAYÚSCULA** son las originales del DANE "
                "que elija en «Variables DANE adicionales».")
    armonizadas = ["anio", "mes", "fex", "sexo", "edad", "grupo_edad", "departamento", "zona", "condicion",
                   "formal", "ingreso_laboral", "ratio_smlv", "horas_semana", "posicion_ocupacional",
                   "nivel_educativo", "rama2d"]
    # Las variables adicionales se ofrecen aunque falten en este mes: en otros meses pueden estar.
    todas = list(dict.fromkeys([*muestra.columns, *extra]))
    elegidas = st.multiselect("Columnas", todas, default=[c for c in armonizadas + list(extra) if c in todas])
    st.dataframe(muestra.reindex(columns=elegidas).head(1000), hide_index=True, width="stretch")
    st.caption(f"{fmt_num(len(muestra))} filas en {dd.MESES[mes_m].lower()} de {anio_m}; "
               f"{fmt_num(n_total)} en toda la selección.")
    if st.toggle("Descargar este mes (CSV, Excel o Stata)"):
        botones_descarga(muestra.reindex(columns=elegidas), f"microdatos_geih_{anio_m}_{mes_m:02d}", "micro")

    st.markdown("**Exportar todos los meses elegidos**")
    nombre = f"microdatos_geih_{anios[0]}" + (f"_{anios[-1]}" if len(anios) > 1 else "")
    # Una huella de la selección en el nombre: dos exportaciones distintas no se pisan
    seleccion = json.dumps([poblacion, sel["filtros"], sel["meses"], sorted(columnas), elegidas], default=str)
    huella = hashlib.sha1(seleccion.encode()).hexdigest()[:6]
    destino = (dd.get_path("geih_empalme" if sel["empalme"] else "geih") / "exportaciones"
               / f"{nombre}{'_empalme' if sel['empalme'] else ''}{f'_{poblacion}' if poblacion else ''}_{huella}.csv")
    st.caption(f"Se escribe un CSV de {fmt_num(n_total)} filas en `{destino}`, un mes a la vez: no hace falta "
               "tener todos los meses en memoria.")
    if st.button("Exportar a CSV", key="exportar"):
        barra, progreso = _barra("Exportando…")
        filas = dd.geih.exportar(list(anios), destino, variables=elegidas, poblacion=poblacion,
                                 filtros=sel["filtros"] or None, meses=sel["meses"], columns=list(columnas) or "core",
                                 empalme=sel["empalme"], progress=progreso)
        barra.empty()
        st.success(f"Listo: {fmt_num(filas)} filas en `{destino}`.")
        if destino.stat().st_size < 100e6:
            st.download_button("⬇️ Descargar el CSV", destino.read_bytes(), destino.name, "text/csv")
    codigo(f'''
import dane_data as dd

# Escribe los microdatos armonizados mes a mes, sin juntarlos en memoria
dd.geih.exportar({list(anios)!r}, "{destino.name}", variables={elegidas!r}{args_py(poblacion=poblacion)}{args_comunes})
''')
    st.caption("💡 `fex` es el factor de expansión **mensual**: si junta varios meses, divida por el número "
               "de meses (o use `dd.geih.serie_tabla`, que lo hace solo).")
