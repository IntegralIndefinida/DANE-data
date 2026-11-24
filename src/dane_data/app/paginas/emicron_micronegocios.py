import warnings

import streamlit as st

import dane_data as dd
from dane_data.app._ui import (AVISOS, MAX_SERIES, barras, botones_descarga, codigo, disponibles, fmt_num, fmt_pct,
                               grafico, linea, rutas_actuales, sin_datos, variacion)

st.title("Micronegocios")
st.markdown("Negocios de **hasta 9 personas ocupadas** de los patrones y trabajadores por cuenta propia que encuentra la GEIH "
            "(EMICRON). El *personal ocupado* incluye al propietario. Montos en pesos corrientes.")


# Los avisos de load se guardan con los datos: si no, solo se verían la primera vez (después la caché no los repite)
@st.cache_resource(max_entries=1, show_spinner="Cargando la EMICRON…")
def _cargar(anios: tuple, rutas: tuple):
    with AVISOS, warnings.catch_warnings(record=True) as avisos:
        warnings.simplefilter("always")
        df = dd.emicron.load(list(anios))
    return df, list(dict.fromkeys(str(a.message) for a in avisos))


rutas = rutas_actuales()
av = disponibles("emicron", rutas)
if av.empty:
    sin_datos("EMICRON")
NACIONAL, CIUDADES = "Total nacional (2019–2024)", "24 ciudades (2019–2025)"
cobertura = st.radio("Cobertura", [NACIONAL, CIUDADES], horizontal=True,
                     help="2025 solo cubre las 24 ciudades principales. Para compararlo con los años anteriores, todos los "
                          "años se calculan con las mismas 24 ciudades.")
en_ciudades = cobertura == CIUDADES
posibles = sorted(a for a in av.anio.unique() if en_ciudades or a <= 2024)
if not posibles:
    sin_datos("EMICRON", "Con esta cobertura no hay años descargados: 2025 solo está en «24 ciudades».")
anios = st.multiselect("Años", posibles, default=posibles, placeholder="Elija los años")
if not anios:
    st.info("Elija al menos un año.")
    st.stop()
datos, avisos = _cargar(tuple(sorted(anios)), rutas)
for aviso in avisos:
    if not (en_ciudades and "24 ciudades" in aviso):  # con esta cobertura ya se eligió mirar solo las ciudades
        st.warning(aviso, icon=":material/warning:")
emi = datos[datos["ciudad"].notna()] if en_ciudades else datos  # una copia: el objeto en caché no se toca
filtro = '\nemi = emi[emi["ciudad"].notna()]  # las 24 ciudades en todos los años' if en_ciudades else ""


def _indicadores(por: list[str]):
    with AVISOS, warnings.catch_warnings(record=True) as avisos_ind:
        warnings.simplefilter("always")
        res = dd.emicron.indicadores(emi, por=["anio", *por])
    return res, [str(a.message) for a in avisos_ind]


# ---------------------------------------------------------------- KPIs
tot, _ = _indicadores([])
u = tot.iloc[-1]
p = tot.iloc[-2] if len(tot) > 1 else None


def var(col, pp=False):
    return {} if p is None else variacion(u[col], p[col], int(p["anio"]), pp=pp)


st.markdown(f"##### {int(u['anio'])} · {cobertura.split(' (')[0].lower()}")
k = st.columns(4)
k[0].metric("Micronegocios", fmt_num(u["micronegocios"]), **var("micronegocios"))
k[1].metric("Personal ocupado", fmt_num(u["personal_ocupado"]), **var("personal_ocupado"),
            help=dd.emicron.GLOSARIO["Personal ocupado de un micronegocio"])
# Los montos de indicadores vienen en miles de pesos: un billón son 1e9 miles
k[2].metric("Valor agregado (billones de $)", fmt_num(u["valor_agregado"] / 1e9, 1), **var("valor_agregado"),
            help="Pesos corrientes del año; la variación es nominal (incluye la inflación).")
k[3].metric("Con RUT", fmt_pct(u["pct_rut"]), **var("pct_rut", pp=True))
st.divider()

# ---------------------------------------------------------------- Gráfico
VARIABLES = {
    "Número de micronegocios": ("micronegocios", "conteo"),
    "Personal ocupado": ("personal_ocupado", "conteo"),
    "Trabajadores remunerados": ("trabajadores_remunerados", "conteo"),
    "Ventas o ingresos": ("ventas", "monto"),
    "Consumo intermedio": ("consumo_intermedio", "monto"),
    "Valor agregado": ("valor_agregado", "monto"),
    "Remuneración del personal": ("remuneracion", "monto"),
    "Ingreso mixto": ("ingreso_mixto", "monto"),
    "Coeficiente técnico (%)": ("coeficiente_tecnico", "pct"),
    "Con RUT (%)": ("pct_rut", "pct"),
    "Con registro en Cámara de Comercio (%)": ("pct_camara_comercio", "pct"),
    "Propietario aporta a salud y pensión (%)": ("pct_salud_pension", "pct"),
}
DESAGREGAR = {"Total": None, **({"Ciudad": "ciudad"} if en_ciudades else {"Cabeceras y centros poblados": "clase"}),
              "Sexo del propietario": "sexo", "Situación en el empleo": "situacion_empleo",
              "Actividad (4 grupos)": "actividad", "Sitio del negocio": "sitio"}
c1, c2, c3 = st.columns([2, 2, 1.3])
nombre_var = c1.selectbox("Variable", list(VARIABLES))
nombre_por = c2.selectbox("Desagregar por", list(DESAGREGAR))
vista = c3.radio("Vista", ["Evolución", "Un año"], horizontal=True)
col, tipo = VARIABLES[nombre_var]
por = DESAGREGAR[nombre_por]
res, avisos_ind = _indicadores([por] if por else [])
for aviso in avisos_ind:
    st.info(aviso, icon=":material/info:")
res["_y"] = res[col] / 1e6 if tipo == "monto" else res[col]  # miles de pesos -> miles de millones
unidad = " (miles de millones de $)" if tipo == "monto" else ""

# Lo que se comparó con los anexos del DANE (tests/datos/dane_emicron_publicado.csv): el cuadro I.1 y los % por dominio
# geográfico, y el número de micronegocios por sexo, situación, actividad y sitio
publicado = por in (None, "clase", "ciudad") or col == "micronegocios"
st.caption("Estas cifras coinciden con las de los anexos del DANE (vea *Validación* en la documentación)."
           + (" En 2019 el anexo pasa unos 48.549 micronegocios de la industria a los servicios y cuenta 0,2 % más "
              "trabajadores remunerados." if 2019 in anios and (por == "actividad" or col in ("personal_ocupado",
                                                                                              "trabajadores_remunerados")) else "")
           if publicado else
           "El DANE no publica este cruce: se calcula con la misma metodología, pero no hay una cifra oficial con qué "
           "compararlo.")

if vista == "Evolución":
    g = res
    if por and g[por].nunique() > MAX_SERIES:
        orden = g.groupby(por, observed=True)[col].sum().sort_values(ascending=False).index.tolist()
        elegidos = st.multiselect(f"Hay {len(orden)} grupos; elija hasta {MAX_SERIES}", orden, default=orden[:5],
                                  max_selections=MAX_SERIES, placeholder="Elija los grupos")
        g = g[g[por].isin(elegidos)]
    grafico(linea(g, x="anio", y="_y", color=por, pct=tipo == "pct", todos=res[por] if por else None),
            nombre_var + unidad, "emicron", (f"Por {nombre_por.lower()} · " if por else "") + cobertura)
else:
    anio = st.select_slider("Año", sorted(res["anio"].unique()), value=res["anio"].max())
    g = res[res["anio"] == anio]
    if por:
        grafico(barras(g, x=por, y="_y", pct=tipo == "pct", horizontal=True), f"{nombre_var}{unidad}, {anio}", "emicron",
                f"Por {nombre_por.lower()} · {cobertura}")
    else:
        st.metric(nombre_var + unidad, fmt_pct(g[col].iloc[0]) if tipo == "pct" else fmt_num(g["_y"].iloc[0], 1))
if tipo == "monto":
    st.caption("Pesos corrientes: las variaciones entre años incluyen la inflación. Anuales: el mes de referencia por 12, "
               "como el DANE.")

with st.expander("Tabla completa", icon=":material/table:"):
    tabla = res.drop(columns="_y")
    st.dataframe(tabla, hide_index=True, width="stretch",
                 column_config={"anio": st.column_config.NumberColumn("Año", format="%d")})
    botones_descarga(tabla, f"emicron_{min(anios)}_{max(anios)}", "emicron")

with st.expander("Glosario", icon=":material/menu_book:"):
    for termino, definicion in dd.emicron.GLOSARIO.items():
        st.markdown(f"**{termino}.** {definicion}")

codigo(f'''
import dane_data as dd

emi = dd.emicron.load({sorted(anios)!r}){filtro}
dd.emicron.indicadores(emi, por={["anio"] + ([por] if por else [])!r})
''')
