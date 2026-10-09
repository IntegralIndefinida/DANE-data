import streamlit as st

import dane_data as dd
from dane_data.app._ui import disponibles_eam, disponibles_geih, rutas_actuales

st.title("📊 dane-data")
st.markdown(
    "#### Microdatos del DANE listos para analizar, sin escribir código\n"
    "Esta aplicación descarga, organiza y resume dos encuestas oficiales de Colombia:"
)

c1, c2 = st.columns(2)
with c1, st.container(border=True):
    st.markdown(
        "##### 👥 GEIH — Gran Encuesta Integrada de Hogares\n"
        "Encuesta **mensual** a ~70.000 personas. Es la fuente oficial del **desempleo**, la "
        "**informalidad** y los **ingresos laborales**. Cada fila es una persona; el *factor de "
        "expansión* dice a cuántas personas del país representa.\n\n"
        "**Úsela para:** brechas de género, desempleo juvenil, informalidad por región, "
        "ingresos frente al salario mínimo…"
    )
with c2, st.container(border=True):
    st.markdown(
        "##### 🏭 EAM — Encuesta Anual Manufacturera\n"
        "Censo **anual** de ~7.000 establecimientos industriales (1992–2024). Cada fila es una "
        "planta: producción, valor agregado, empleo, salarios, activos y energía.\n\n"
        "**Úsela para:** productividad por sector, participación laboral, concentración "
        "regional, funciones de producción y costos…"
    )

st.subheader("¿Cómo empiezo?")
st.markdown(
    "1. **Datos:** si aún no los tiene, vaya a **⬇️ Descargar datos** (menú izquierdo). "
    "Si ya los descargó, indique la carpeta abajo.\n"
    "2. **Explore:** abra **👥 Indicadores laborales** o **🏭 Indicadores industriales**, elija años y filtros.\n"
    "3. **Exporte:** cada tabla se descarga en CSV, Excel o Stata. Cada página muestra el "
    "**código Python** equivalente para pasar a un notebook cuando esté listo."
)

# ---------------------------------------------------------------- Estado de datos
st.subheader("Datos disponibles en este computador")
rutas = rutas_actuales()
g, e, ge = disponibles_geih(False, rutas), disponibles_eam(rutas), disponibles_geih(True, rutas)

m1, m2, m3 = st.columns(3)
m1.metric("GEIH (serie principal)", f"{g.anio.nunique()} años" if len(g) else "Sin datos",
          f"{g.anio.min()}–{g.anio.max()} · {len(g)} meses" if len(g) else None, delta_color="off")
m2.metric("GEIH (serie de empalme)", f"{ge.anio.nunique()} años" if len(ge) else "Sin datos",
          f"{ge.anio.min()}–{ge.anio.max()}" if len(ge) else None, delta_color="off")
m3.metric("EAM", f"{e.anio.nunique()} años" if len(e) else "Sin datos",
          f"{e.anio.min()}–{e.anio.max()}" if len(e) else None, delta_color="off")

incompletos = g[~g.completo] if len(g) else g
if len(incompletos):
    with st.expander(f"⚠️ {len(incompletos)} mes(es) de la GEIH están incompletos y se omitirán"):
        st.dataframe(incompletos[["anio", "nombre_mes", "carpeta", "faltantes"]], hide_index=True)
        st.caption("Vuelva a descargarlos en ⬇️ Descargar datos (borre antes la carpeta de ese mes).")

# ---------------------------------------------------------------- Configuración
with st.expander("⚙️ Carpetas de datos", expanded=not (len(g) or len(e))):
    st.caption(
        "Indique dónde están (o dónde quiere guardar) los datos. Para la GEIH, la carpeta que "
        "contiene `datos_csv/`; para la EAM, la que contiene `datos/`. Se recuerda para la próxima vez."
    )
    with st.form("rutas"):
        p_geih = st.text_input("GEIH serie principal", str(dd.get_path("geih")))
        p_emp = st.text_input("GEIH serie de empalme", str(dd.get_path("geih_empalme")))
        p_eam = st.text_input("EAM", str(dd.get_path("eam")))
        if st.form_submit_button("Guardar", type="primary"):
            dd.set_paths(geih=p_geih, geih_empalme=p_emp, eam=p_eam, save=True)
            st.cache_data.clear()
            st.cache_resource.clear()
            st.rerun()

st.divider()
st.caption(
    "Fuente: DANE — Archivo Nacional de Datos (ANDA), microdatos anonimizados de uso público. "
    "Cite: *DANE, Gran Encuesta Integrada de Hogares (GEIH)* / *Encuesta Anual Manufacturera (EAM)*."
)
