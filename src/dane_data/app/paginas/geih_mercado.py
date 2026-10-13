import pandas as pd
import streamlit as st

import dane_data as dd
from dane_data.app._ui import (fmt_num, MAX_SERIES, barras, botones_descarga, codigo, fmt_grande, fmt_pct, fmt_pesos,
                             grafico, indicadores_geih, linea, rutas_actuales, seleccion_geih, selector_geih,
                             serie_geih)

st.title("👥 Indicadores del mercado laboral")
sel = seleccion_geih(clave="geih", ayuda_anios="Sin filtros ni selección de meses, los indicadores salen de una "
                                              "tabla precalculada y puede elegir todos los años: la primera vez "
                                              "se calculan (unos segundos por año) y quedan guardados.")
# Sin filtros: tabla precalculada por año (instantánea, sin cargar microdatos). Con filtros o
# meses: microdatos con solo las variables necesarias (todos los años completos no caben en memoria).
precalculada = not sel["filtrada"]
if precalculada:
    def calcular(por, anual):
        return serie_geih(tuple(sel["anios"]), por, anual, sel["empalme"], sel["meses_disponibles"],
                          rutas_actuales())

    total = calcular(None, True)
    n_personas = total["n_muestra"].sum()
    mensual = calcular(None, False)
    meses_ult = int((mensual["anio"] == total["anio"].iloc[-1]).sum())
    descripcion = sel["descripcion"]
else:
    df, descripcion, params = selector_geih(variables=dd.geih.VARIABLES_INDICADORES, sel=sel)

    def calcular(por, anual):
        return indicadores_geih(df, params["carga"] + repr(rutas_actuales()), por, anual)

    total = calcular(None, True)
    n_personas = len(df)
    meses_ult = df.loc[df["anio"] == total["anio"].iloc[-1], "mes"].nunique()
st.caption(f"**Datos:** {descripcion} · {fmt_num(n_personas)} personas en la muestra")
if not precalculada:
    st.caption("ℹ️ Con filtros o meses elegidos, los indicadores se calculan desde los microdatos (más lento). "
               "Sin ellos salen de una tabla precalculada.")

INDICADORES = {
    "Tasa de desocupación (TD)": ("td", True),
    "Tasa global de participación (TGP)": ("tgp", True),
    "Tasa de ocupación (TO)": ("to", True),
    "Tasa de informalidad": ("tasa_informalidad", True),
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


def delta(col, pct=True):
    if prev is None or pd.isna(prev[col]):
        return None
    d = ult[col] - prev[col]
    return f"{d:+.1f} p.p. vs {int(prev['anio'])}" if pct else f"{100 * d / prev[col]:+.1f} % vs {int(prev['anio'])}"


st.markdown(f"##### Resumen {int(ult['anio'])}")
k = st.columns(5)
k[0].metric("Desocupación", fmt_pct(ult.td), delta("td"), delta_color="inverse",
            help=dd.geih.GLOSARIO["TD"])
k[1].metric("Participación (TGP)", fmt_pct(ult.tgp), delta("tgp"), help=dd.geih.GLOSARIO["TGP"])
k[2].metric("Ocupación (TO)", fmt_pct(ult.to), delta("to"), help=dd.geih.GLOSARIO["TO"])
k[3].metric("Informalidad", fmt_pct(ult.tasa_informalidad), delta("tasa_informalidad"), delta_color="inverse",
            help=dd.geih.GLOSARIO["Informalidad"])
k[4].metric("Ingreso laboral mediano", fmt_pesos(ult.ingreso_mediano), delta("ingreso_mediano", pct=False),
            help=dd.geih.GLOSARIO["Ingreso laboral"] + " Pesos corrientes (sin ajustar por inflación).")
if meses_ult < 12:
    st.info(f"ℹ️ {int(ult['anio'])} tiene solo {meses_ult} mes(es) en la selección. La comparación con el año "
            "anterior mezcla temporadas distintas (el desempleo es estacional); para comparar bien elija los "
            "mismos meses en ambos años (desactive «Todos los meses»).")
st.caption(f"Ocupados: **{fmt_grande(ult.ocupados)}** · Desocupados: **{fmt_grande(ult.desocupados)}** · "
           f"Población en edad de trabajar: **{fmt_grande(ult.pet)}** (promedio mensual).")

st.divider()

# ---------------------------------------------------------------- Gráfico
c1, c2, c3 = st.columns([2, 2, 1])
nombre_ind = c1.selectbox("Indicador", list(INDICADORES))
nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR))
frecuencia = c3.radio("Frecuencia", ["Anual", "Mensual"], horizontal=True)
col, es_pct = INDICADORES[nombre_ind]
por = DESAGREGAR[nombre_por]
anual = frecuencia == "Anual"

res = calcular(por, anual)
if por:
    res = res[res[por].notna()]
if por:  # grupos sin dato (p. ej. 0–14 años no está en la PET)
    res = res[res.groupby(por, observed=True)[col].transform("count") > 0]
if not anual:
    res["periodo"] = pd.to_datetime(dict(year=res["anio"], month=res["mes"], day=1))
x = "anio" if anual else "periodo"

grupos = list(res[por].dropna().unique()) if por else []
if por and len(grupos) > MAX_SERIES and res[x].nunique() > 1:
    orden = res.groupby(por, observed=True)["ocupados"].sum().sort_values(ascending=False).index.tolist()
    elegidos = st.multiselect(f"Hay {len(grupos)} grupos; elija hasta {MAX_SERIES} para comparar en el tiempo",
                              orden, default=orden[:5], max_selections=MAX_SERIES)
    res_graf = res[res[por].isin(elegidos)]
else:
    res_graf = res

titulo = nombre_ind + (" (%)" if es_pct else "")
if res_graf[x].nunique() > 1:
    fig = linea(res_graf, x=x, y=col, color=por, titulo_y=titulo, pct=es_pct)
else:
    fig = barras(res_graf, x=por or x, y=col, titulo_y=titulo, pct=es_pct,
                 horizontal=bool(por) and len(grupos) > 6)
grafico(fig)

pocos = res[res["n_muestra"] < 100]
if len(pocos):
    st.warning(f"⚠️ {len(pocos)} celda(s) tienen menos de 100 personas en la muestra: esas cifras son "
               "poco confiables (mucho error de muestreo). Considere agrupar más meses o menos categorías.")

# ---------------------------------------------------------------- Tabla
with st.expander("📋 Tabla completa", expanded=False):
    tabla = res.drop(columns=["periodo"], errors="ignore")
    st.dataframe(
        tabla, hide_index=True, width="stretch",
        column_config={
            "anio": st.column_config.NumberColumn("Año", format="%d"),
            "mes": st.column_config.NumberColumn("Mes", format="%d"),
            **{c: st.column_config.NumberColumn(c.upper(), format="%.1f %%") for c in ("tgp", "to", "td")},
            "tasa_informalidad": st.column_config.NumberColumn("Informalidad", format="%.1f %%"),
            **{c: st.column_config.NumberColumn(c.replace("_", " ").capitalize(), format="localized")
               for c in ("pet", "fuerza_trabajo", "ocupados", "desocupados", "inactivos", "ingreso_medio",
                         "ingreso_mediano", "n_muestra")},
        },
    )
    botones_descarga(tabla, f"indicadores_geih_{'_'.join(map(str, sel['anios']))}", "ind")

with st.expander("📖 ¿Qué significa cada indicador?"):
    for k_, v in dd.geih.GLOSARIO.items():
        st.markdown(f"**{k_}.** {v}")
    st.markdown(
        "**Promedio mensual.** La GEIH es mensual: al juntar varios meses, los niveles (personas) son el "
        "promedio de los meses y las tasas se calculan sobre esos promedios, como hace el DANE.\n\n"
        "**Muestra vs población.** `n_muestra` es cuántas personas se encuestaron; los niveles usan el "
        "factor de expansión para representar a todo el país."
    )

argumentos = f'{f", por={por!r}" if por else ""}{", anual=False" if not anual else ""}'
if precalculada:
    codigo(f'''
import dane_data as dd

# Igual a dd.geih.indicadores(dd.geih.load(...){argumentos}), pero año por año y guardado
# en caché: la segunda vez es instantáneo.
ind = dd.geih.serie_indicadores({sel["anios"]!r}{argumentos}{", empalme=True" if sel["empalme"] else ""})
ind
''')
else:
    codigo(f'''
import dane_data as dd

{params["carga"]}
ind = dd.geih.indicadores(df{argumentos})
ind
''')
