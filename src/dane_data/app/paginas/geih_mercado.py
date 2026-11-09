import pandas as pd
import streamlit as st

import dane_data as dd
from dane_data.app._ui import (GRIS, fmt_num, MAX_SERIES, _valor, args_py, barras, botones_descarga, codigo, fmt_grande,
                             fmt_pct, fmt_pesos, grafico, linea, rutas_actuales, seleccion_geih, serie_geih, variacion)

st.title("Indicadores del mercado laboral")
sel = seleccion_geih(clave="geih")


def calcular(por, anual):
    """Indicadores año por año, guardados en disco (con los filtros y meses de la barra lateral)."""
    return serie_geih(tuple(sel["anios"]), por, anual, sel["empalme"], sel["filtros"],
                      tuple(sel["meses"]) if sel["meses"] else None, sel["meses_disponibles"], rutas_actuales())


total = calcular(None, True)
if total.empty or not total["n_muestra"].sum():
    st.warning("Ninguna persona cumple los filtros elegidos.")
    st.stop()
mensual = calcular(None, False)
meses_ult = int((mensual["anio"] == total["anio"].iloc[-1]).sum())
st.caption(f"**Datos:** {sel['descripcion']} · {fmt_num(total['n_muestra'].sum())} personas en la muestra")

INDICADORES = {
    "Tasa de desocupación (TD)": ("td", True),
    "Tasa global de participación (TGP)": ("tgp", True),
    "Tasa de ocupación (TO)": ("to", True),
    "Tasa de informalidad": ("tasa_informalidad", True),
    "Tasa de informalidad (medición anterior, hasta 2021)": ("tasa_informalidad_marco2005", True),
    "Ingreso laboral mediano": ("ingreso_mediano", False),
    "Ingreso laboral medio": ("ingreso_medio", False),
    "Ocupados (personas)": ("ocupados", False),
    "Desocupados (personas)": ("desocupados", False),
    "Fuerza de trabajo (personas)": ("fuerza_trabajo", False),
}
DESAGREGAR = {
    "Total nacional": None,
    "Sexo": "sexo",
    "Zona (urbano/rural)": "zona",
    "Grupo de edad": "grupo_edad",
    "Nivel educativo": "nivel_educativo",
    "Departamento": "departamento",
}

# ---------------------------------------------------------------- KPIs
ult = total.iloc[-1]
prev = total.iloc[-2] if len(total) > 1 else None


def delta(col, pct=True, inversa=False):
    if prev is None:  # la informalidad no existe antes de 2022: variacion() no muestra nada si falta un valor
        return {}
    return variacion(ult[col], prev[col], int(prev["anio"]), pp=pct, inversa=inversa)


st.markdown(f"##### Resumen {int(ult['anio'])}")
k = st.columns(5)
k[0].metric("Desocupación", fmt_pct(ult.td), **delta("td", inversa=True),
            help=dd.geih.GLOSARIO["TD"])
k[1].metric("Participación (TGP)", fmt_pct(ult.tgp), **delta("tgp"), help=dd.geih.GLOSARIO["TGP"])
k[2].metric("Ocupación (TO)", fmt_pct(ult.to), **delta("to"), help=dd.geih.GLOSARIO["TO"])
k[3].metric("Informalidad", fmt_pct(ult.tasa_informalidad), **delta("tasa_informalidad", inversa=True),
            help=dd.geih.GLOSARIO["Informalidad"])
k[4].metric("Ingreso laboral mediano", fmt_pesos(ult.ingreso_mediano), **delta("ingreso_mediano", pct=False),
            help=dd.geih.GLOSARIO["Ingreso laboral"] + " Pesos corrientes (sin ajustar por inflación).")
if meses_ult < 12:
    st.info(f"{int(ult['anio'])} tiene solo {meses_ult} mes(es) en la selección. La comparación con el año "
            "anterior mezcla temporadas distintas (el desempleo es estacional); para comparar bien elija los "
            "mismos meses en ambos años (desactive «Todos los meses»).", icon=":material/info:")
st.caption(f"Ocupados: **{fmt_grande(ult.ocupados)}** · Desocupados: **{fmt_grande(ult.desocupados)}** · "
           f"Población en edad de trabajar: **{fmt_grande(ult.pet)}** (promedio mensual).")

st.divider()

# ---------------------------------------------------------------- Gráfico
c1, c2, c3 = st.columns([3, 3, 2])
nombre_ind = c1.selectbox("Indicador", list(INDICADORES))
nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR))
col, es_pct = INDICADORES[nombre_ind]
por = DESAGREGAR[nombre_por]
# El trimestre móvil no puede dar la mediana ni la media del ingreso con los resultados de cada mes, y con solo
# algunos meses le faltan los dos anteriores: la gráfica quedaba vacía
movil_posible = col not in ("ingreso_medio", "ingreso_mediano") and not sel["meses"]
frecuencias = ["Anual", "Mensual"] + (["Trimestre móvil"] if movil_posible else [])
# Con pocos años, la serie anual son 2 o 3 puntos casi en línea recta: por defecto, la mensual; por departamento, el
# trimestre móvil, porque un departamento en un solo mes tiene poca muestra y la tasa salta mucho
defecto = ("Anual" if len(sel["anios"]) > 3 else
           "Trimestre móvil" if por == "departamento" and movil_posible else "Mensual")
# Lo que la persona eligió se mantiene al cambiar el indicador o la desagregación; sin elección, el defecto. Sin
# esto, Streamlit volvía al defecto cada vez que cambiaban las opciones o el índice.
elegida = st.session_state.get("geih_frecuencia_elegida")
st.session_state["geih_frecuencia"] = elegida if elegida in frecuencias else defecto
frecuencia = c3.radio("Frecuencia", frecuencias, horizontal=True, key="geih_frecuencia",
                      on_change=lambda: st.session_state.update(geih_frecuencia_elegida=st.session_state["geih_frecuencia"]))
anual = frecuencia == "Anual"
movil = frecuencia == "Trimestre móvil"
if col == "tasa_informalidad" and min(sel["anios"]) < 2022:
    st.info("La informalidad sigue la medición del DANE, que necesita preguntas del cuestionario de 2022: "
            "antes de 2022 queda vacía. Para 2007–2021, elija «Tasa de informalidad (medición anterior)».",
            icon=":material/info:")
if col == "tasa_informalidad_marco2005" and max(sel["anios"]) >= 2022:
    st.info("La medición anterior del DANE (empresas de hasta 5 personas) llega hasta 2021: desde 2022 queda "
            "vacía. El DANE la publicaba para 13 y 23 ciudades; no es comparable con la actual.",
            icon=":material/info:")
if col == "tasa_informalidad_marco2005" and 2020 in sel["anios"] and not sel["empalme"]:
    st.info("En marzo y abril de 2020, por el operativo telefónico, unos tres cuartos de los ocupados no "
            "tienen tamaño de empresa: la medición anterior queda vacía esos meses y en el total de 2020.",
            icon=":material/info:")

def serie(por_):
    r = calcular(por_, anual)
    return dd.geih.trimestre_movil(r) if movil else r


res = serie(por)
if por:  # grupos sin dato (p. ej. 0–14 años no está en la PET)
    res = res[res.groupby(por, observed=True)[col].transform("count") > 0]
if not anual:
    res["periodo"] = pd.to_datetime(dict(year=res["anio"], month=res["mes"], day=1))
x = "anio" if anual else "periodo"

grupos = list(res[por].dropna().unique()) if por else []
if por and len(grupos) > MAX_SERIES and res[x].nunique() > 1:
    orden = res.groupby(por, observed=True)["ocupados"].sum().sort_values(ascending=False).index.tolist()
    elegidos = st.multiselect(f"Hay {len(grupos)} grupos; elija hasta {MAX_SERIES} para comparar en el tiempo",
                              orden, default=orden[:5], max_selections=MAX_SERIES, placeholder="Elija los grupos")
    res_graf = res[res[por].isin(elegidos)]
else:
    res_graf = res

titulo = nombre_ind + (" (pesos corrientes)" if col.startswith("ingreso") else "")
total_txt = "Total de la selección" if sel["filtrada"] else "Total nacional"
subtitulo = f"{'Por ' + nombre_por.lower() if por else total_txt}, {frecuencia.lower()} · {sel['descripcion']}"
if res_graf[x].nunique() > 1:
    fig = linea(res_graf, x=x, y=col, color=por, pct=es_pct)
    # El total en gris, para leer cada grupo contra algo; no en los niveles (ocupados...), donde es la suma de los
    # grupos y aplastaba sus líneas contra el eje
    if por and (es_pct or col.startswith("ingreso")):
        nacional = serie(None)
        if not anual:
            nacional["periodo"] = pd.to_datetime(dict(year=nacional["anio"], month=nacional["mes"], day=1))
        fig.add_scatter(x=nacional[x], y=nacional[col], name=total_txt, mode="lines", line=dict(color=GRIS, width=2),
                        hovertemplate=f"{total_txt}: {_valor('y', es_pct)}<extra></extra>")
        fig.data = fig.data[-1:] + fig.data[:-1]  # primero en la leyenda
else:
    fig = barras(res_graf, x=por or x, y=col, pct=es_pct,
                 horizontal=bool(por) and len(grupos) > 6)
grafico(fig, titulo, "geih", subtitulo)
if movil:
    st.caption("Cada punto es el trimestre que termina en ese mes: marzo junta enero, febrero y marzo, como en el "
               "trimestre móvil del DANE. Los niveles son el promedio de los tres meses.")

pocos = res[res["n_muestra"] < 100]
if len(pocos):
    st.warning(f"{len(pocos)} celda(s) tienen menos de 100 personas en la muestra: esas cifras son "
               "poco confiables (mucho error de muestreo). Considere agrupar más meses o menos categorías.",
               icon=":material/warning:")

# ---------------------------------------------------------------- Tabla
with st.expander("Tabla completa", icon=":material/table:", expanded=False):
    tabla = res.drop(columns=["periodo"], errors="ignore")
    st.dataframe(
        tabla, hide_index=True, width="stretch",
        column_config={
            "anio": st.column_config.NumberColumn("Año", format="%d"),
            "mes": st.column_config.NumberColumn("Mes", format="%d"),
            **{c: st.column_config.NumberColumn(c.upper(), format="%.1f %%") for c in ("tgp", "to", "td")},
            "tasa_informalidad": st.column_config.NumberColumn("Informalidad", format="%.1f %%"),
            "tasa_informalidad_marco2005": st.column_config.NumberColumn("Informalidad (marco 2005)",
                                                                         format="%.1f %%"),
            **{c: st.column_config.NumberColumn(c.replace("_", " ").capitalize(), format="localized")
               for c in ("pet", "fuerza_trabajo", "ocupados", "desocupados", "inactivos", "ingreso_medio",
                         "ingreso_mediano", "n_muestra")},
        },
    )
    botones_descarga(tabla, f"indicadores_geih_{'_'.join(map(str, sel['anios']))}", "ind")

with st.expander("¿Qué significa cada indicador?", icon=":material/menu_book:"):
    for k_, v in dd.geih.GLOSARIO.items():
        st.markdown(f"**{k_}.** {v}")
    st.markdown(
        "**Promedio mensual.** La GEIH es mensual: al juntar varios meses, los niveles (personas) son el "
        "promedio de los meses y las tasas se calculan sobre esos promedios, como hace el DANE.\n\n"
        "**Muestra vs población.** `n_muestra` es cuántas personas se encuestaron; los niveles usan el "
        "factor de expansión para representar a todo el país."
    )

argumentos = f'{f", por={por!r}" if por else ""}{", anual=False" if not anual else ""}'
codigo(f'''
import dane_data as dd

# Igual a dd.geih.indicadores(...) sobre los microdatos filtrados, pero año por año y
# guardado en caché: la segunda vez es instantáneo.
ind = dd.geih.serie_indicadores({sel["anios"]!r}{argumentos}{args_py(empalme=sel["empalme"], filtros=sel["filtros"], meses=sel["meses"])})
{"ind = dd.geih.trimestre_movil(ind)  # cada mes junta ese mes y los dos anteriores" + chr(10) if movil else ""}ind
''')
