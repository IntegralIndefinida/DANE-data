import pandas as pd
import streamlit as st

import dane_data as dd
from dane_data.app._ui import (MAX_SERIES, args_py, barras, botones_descarga, codigo, conteos_eevv, fmt_grande, fmt_num,
                               fmt_pct, grafico, indicadores_eevv, linea, rutas_actuales, seleccion_eevv, tasas_eevv)

st.title("👶 Nacimientos y defunciones")
st.caption("**Estadísticas Vitales del DANE.** Es el registro de los certificados, no una encuesta: no hay factor de "
           "expansión y cada fila es un hecho registrado.")
sel = seleccion_eevv()
tipo, anios, filtros = sel["tipo"], sel["anios"], sel["filtros"]
rutas = rutas_actuales()
st.caption(f"**Datos:** {sel['descripcion']}")

VARIABLES = {
    "defunciones": {
        "Defunciones": ("defunciones", "conteo"), "Hombres": ("hombres", "conteo"), "Mujeres": ("mujeres", "conteo"),
        "Menores de un año": ("menores_un_anio", "conteo"), "Neonatales (0 a 27 días)": ("neonatales", "conteo"),
        "Neonatales precoces (0 a 6 días)": ("neonatales_precoces", "conteo"), "Defunciones maternas": ("maternas", "conteo"),
        "Defunciones maternas tardías": ("maternas_tardias", "conteo"),
        "Homicidios": ("homicidios", "conteo"), "Suicidios": ("suicidios", "conteo"), "Accidentes": ("accidentes", "conteo"),
        "Menores de un año (% de las defunciones)": ("pct_menores_un_anio", "pct"),
        "Causas mal definidas (%)": ("pct_mal_definidas", "pct"),
    },
    "nacimientos": {
        "Nacimientos": ("nacimientos", "conteo"), "Bajo peso al nacer (%)": ("pct_bajo_peso", "pct"),
        "Bajo peso al nacer, pretérmino (%)": ("pct_bajo_peso_pretermino", "pct"),
        "Bajo peso al nacer, a término (%)": ("pct_bajo_peso_a_termino", "pct"),
        "Prematuros (%)": ("pct_prematuro", "pct"), "Cesáreas (%)": ("pct_cesarea", "pct"),
        "Madres adolescentes (%)": ("pct_madre_adolescente", "pct"), "Partos múltiples (%)": ("pct_parto_multiple", "pct"),
        "Partos en institución de salud (%)": ("pct_parto_institucional", "pct"),
        "Cuatro o más consultas prenatales (%)": ("pct_cuatro_consultas", "pct"),
        "Consultas prenatales (promedio)": ("consultas_promedio", "numero"), "Hombres por cada 100 mujeres": ("razon_sexo", "numero"),
    },
    "fetales": {
        "Defunciones fetales": ("fetales", "conteo"), "Mortinatos (22 semanas o más)": ("mortinatos", "conteo"),
        "Madres adolescentes (%)": ("pct_madre_adolescente", "pct"),
    },
}
DESAGREGAR = {
    "defunciones": {"Total": None, "Sexo": "sexo", "Grupo de edad": "grupo_edad_amplio", "Gran causa": "gran_causa",
                    "Manera de muerte": "manera_muerte", "Departamento de residencia": "departamento_residencia",
                    "Área de residencia": "area_residencia"},
    "nacimientos": {"Total": None, "Edad de la madre": "edad_madre", "Nivel educativo de la madre": "nivel_educativo_madre",
                    "Régimen de salud": "regimen_salud", "Departamento de residencia": "departamento_residencia",
                    "Área de residencia": "area_residencia"},
    "fetales": {"Total": None, "Edad de la madre": "edad_madre", "Gran causa": "gran_causa",
                "Departamento de residencia": "departamento_residencia"},
}
TASAS = {
    "Tasa bruta de natalidad (por 1.000 habitantes)": "tasa_natalidad",
    "Tasa bruta de mortalidad (por 1.000 habitantes)": "tasa_mortalidad",
    "Tasa global de fecundidad (hijos por mujer)": "tasa_global_fecundidad",
    "Mortalidad infantil (por 1.000 nacidos vivos)": "mortalidad_infantil",
    "Razón de mortalidad materna (por 100.000 nacidos vivos)": "razon_mortalidad_materna",
    "Mortalidad neonatal (por 1.000 nacidos vivos)": "mortalidad_neonatal",
    "Mortalidad perinatal (por 1.000 nacidos vivos y mortinatos)": "mortalidad_perinatal",
}
POR_TASAS = {"Total nacional": None, "Departamento de residencia": "departamento", "Sexo": "sexo", "Área de residencia": "area"}
# dd.eevv.tasas las deja vacías por sexo: los nacimientos son del sexo del nacido, no de quien los tiene
SOLO_POR_SEXO = {"tasa_mortalidad", "mortalidad_infantil", "mortalidad_neonatal"}
TITULO = {"defunciones": "Defunciones", "nacimientos": "Nacimientos", "fetales": "Defunciones fetales"}


def serie(res: pd.DataFrame, columna: str, por: str | None, tipo_valor: str, titulo: str) -> None:
    """Gráfico de la variable por año, o por grupo en el único año elegido."""
    g = res[res[columna].notna()].copy()
    if por:
        g = g[g[por].notna()]
        g[por] = g[por].astype(str)
    if g.empty:
        st.info("Esta variable no existe en los años elegidos.")
        return
    if por and g["anio"].nunique() == 1:
        grafico(barras(g, x=por, y=columna, titulo_y=titulo, pct=tipo_valor == "pct", horizontal=True))
        return
    if por and g[por].nunique() > MAX_SERIES:
        orden = g.groupby(por)[columna].sum().sort_values(ascending=False).index.tolist()
        elegidos = st.multiselect(f"Hay {len(orden)} grupos; elija hasta {MAX_SERIES}", orden, default=orden[:5],
                                  max_selections=MAX_SERIES, placeholder="Elija los grupos")
        g = g[g[por].isin(elegidos)]
    grafico(linea(g, x="anio", y=columna, color=por, titulo_y=titulo, pct=tipo_valor == "pct"))


vistas = ["Indicadores", "Tasas sobre la población"] + (["Causas de muerte"] if tipo != "nacimientos" else [])
vista = st.radio("Vista", vistas, horizontal=True)

# ---------------------------------------------------------------- Indicadores
if vista == "Indicadores":
    total = indicadores_eevv(anios, tipo, None, filtros, rutas)
    if total.empty:  # p. ej. un departamento sin registros en los años elegidos
        st.warning("Ningún certificado cumple los filtros elegidos.")
        st.stop()
    u = total.iloc[-1]
    st.markdown(f"##### Resumen {int(u['anio'])}")
    if tipo == "defunciones":
        k = st.columns(4)
        k[0].metric("Defunciones", fmt_num(u.defunciones))
        k[1].metric("Menores de un año", fmt_num(u.menores_un_anio))
        k[2].metric("Homicidios", fmt_num(u.homicidios))
        k[3].metric("Defunciones maternas", fmt_num(u.maternas))
    elif tipo == "nacimientos":
        k = st.columns(4)
        k[0].metric("Nacimientos", fmt_num(u.nacimientos))
        k[1].metric("Bajo peso al nacer", fmt_pct(u.pct_bajo_peso), help=dd.eevv.GLOSARIO["Bajo peso al nacer"])
        k[2].metric("Cesáreas", fmt_pct(u.pct_cesarea))
        k[3].metric("Madres adolescentes", fmt_pct(u.pct_madre_adolescente), help=dd.eevv.GLOSARIO["Madre adolescente"])
    else:
        k = st.columns(3)
        k[0].metric("Defunciones fetales", fmt_num(u.fetales))
        k[1].metric("Mortinatos", fmt_num(u.mortinatos), help=dd.eevv.GLOSARIO["Mortinato"])
        k[2].metric("Madres adolescentes", fmt_pct(u.pct_madre_adolescente))
    st.divider()

    c1, c2 = st.columns(2)
    nombre = c1.selectbox("Variable", list(VARIABLES[tipo]))
    nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR[tipo]))
    columna, tipo_valor = VARIABLES[tipo][nombre]
    por = DESAGREGAR[tipo][nombre_por]
    res = indicadores_eevv(anios, tipo, por, filtros, rutas) if por else total
    serie(res, columna, por, tipo_valor, nombre)
    if tipo != "defunciones" and columna == "pct_prematuro":
        st.caption("💡 " + dd.eevv.GLOSARIO["Prematuro"])
    if columna.startswith("pct_bajo_peso"):
        st.caption("💡 " + dd.eevv.GLOSARIO["Bajo peso al nacer"])

    with st.expander("📋 Tabla completa"):
        st.dataframe(res, hide_index=True, width="stretch",
                     column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
        botones_descarga(res, f"{tipo}_{anios[0]}_{anios[-1]}", "eevvind")
    codigo(f"""
import dane_data as dd

res = dd.eevv.serie_indicadores({anios!r}, tipo={tipo!r}{args_py(por=por, filtros=filtros)})
res
""")

# ---------------------------------------------------------------- Tasas
elif vista == "Tasas sobre la población":
    st.info("📐 Usan las proyecciones de población del DANE, que vienen con la aplicación. Son tasas de **hechos registrados, "
            "sin ajustar por subregistro**: no tienen por qué coincidir con los indicadores demográficos que publica el DANE, "
            "que salen de un modelo. Los años antiguos, con más subregistro, salen más bajos. Los filtros de la barra lateral "
            "no aplican aquí.")
    c1, c2 = st.columns(2)
    nombre = c1.selectbox("Tasa", list(TASAS))
    columna = TASAS[nombre]
    opciones_por = [k for k, v in POR_TASAS.items() if v != "sexo" or columna in SOLO_POR_SEXO]
    nombre_por = c2.selectbox("Desagregar por", opciones_por,
                              help=None if "Sexo" in opciones_por else "Esta tasa no se puede partir por sexo: los nacimientos "
                                                                       "se cuentan por el sexo del nacido.")
    por = POR_TASAS[nombre_por]
    res = tasas_eevv(anios, por, rutas)
    if por == "departamento" and min(anios) < 1985:
        st.warning("Las proyecciones por departamento empiezan en 1985: los años anteriores quedan sin tasa.")
    serie(res, columna, por, "numero", nombre)
    with st.expander("📋 Tabla completa"):
        st.dataframe(res, hide_index=True, width="stretch",
                     column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
        botones_descarga(res, f"tasas_{anios[0]}_{anios[-1]}", "eevvtasas")
    with st.expander("📖 Glosario"):
        for clave in ("Tasa bruta de natalidad", "Tasa bruta de mortalidad", "Tasa global de fecundidad",
                      "Mortalidad infantil registrada", "Mortalidad neonatal", "Mortalidad perinatal", "Mortinato",
                      "Razón de mortalidad materna"):
            st.markdown(f"**{clave}.** {dd.eevv.GLOSARIO[clave]}")
    codigo(f"""
import dane_data as dd

res = dd.eevv.tasas({anios!r}{args_py(por=por)})
res
""")

# ---------------------------------------------------------------- Causas
else:
    anio = st.select_slider("Año", anios, value=anios[-1]) if len(anios) > 1 else anios[0]
    n = st.slider("Cuántas causas mostrar", 5, 30, 10)
    res = conteos_eevv(anio, tipo, "causa_105_nombre", filtros, rutas)
    if res.empty:
        st.warning("Ningún certificado cumple los filtros elegidos.")
        st.stop()
    primeras = res.nlargest(n, "n").assign(causa=lambda d: d["causa_105_nombre"].astype(str))
    grafico(barras(primeras, x="causa", y="n", titulo_y=f"{TITULO[tipo]} en {anio}", horizontal=True))
    st.caption(f"Lista Colombia 105, disponible en toda la serie. Las {n} primeras suman el "
               f"**{fmt_pct(100 * primeras['n'].sum() / res['n'].sum())}** de {fmt_grande(res['n'].sum())} {TITULO[tipo].lower()}.")
    with st.expander("📋 Tabla completa"):
        tabla = res.sort_values("n", ascending=False)
        st.dataframe(tabla, hide_index=True, width="stretch",
                     column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
        botones_descarga(tabla, f"causas_{tipo}_{anio}", "eevvcausas")
    codigo(f"""
import dane_data as dd

res = dd.eevv.serie_conteos({anio!r}, tipo={tipo!r}, por="causa_105_nombre"{args_py(filtros=filtros)})
res.nlargest({n}, "n")
""")
