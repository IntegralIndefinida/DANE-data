from pathlib import Path

import streamlit as st

import dane_data as dd
from dane_data.app._ui import aviso_version_nueva, disponibles_eam, disponibles_geih, rutas_actuales

st.title("📊 DANE-data")
# El aviso va arriba pero se llena al final: sin internet, la consulta no demora el resto de la página
hueco_version = st.empty()
st.markdown(
    "#### Microdatos del DANE listos para analizar\n"
    "Esta aplicación descarga, organiza y resume dos encuestas oficiales de Colombia publicadas por el DANE:"
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
st.info(
    "**¿Usa dane-data en una tesis, un trabajo o un artículo?** Por favor cítelo, junto con los datos del "
    "DANE: así otras personas lo encuentran y el proyecto puede seguir creciendo. La cita lista para copiar "
    "(APA y BibTeX) está en **📝 Cómo citar** (menú izquierdo).",
    icon="🎓",
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
        st.caption("Vuelva a descargarlos en ⬇️ Descargar datos. Si siguen incompletos, active «Volver a bajar "
                   "lo que ya está descargado» en las opciones avanzadas.")

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
            # Solo las que cambiaron: así no se fija en el archivo una ruta que viene de una variable de entorno
            cambios = {k: v.strip() for k, v in (("geih", p_geih), ("geih_empalme", p_emp), ("eam", p_eam))
                       if v.strip() != str(dd.get_path(k))}
            # La app corre dentro de la carpeta del paquete: una ruta relativa quedaría ahí (y uv la borra al
            # reinstalar), lejos de donde la buscaría un notebook.
            relativas = [v for v in cambios.values() if v and not Path(v).expanduser().is_absolute()]
            if relativas:
                st.error(f"Escriba la ruta completa de la carpeta, no solo su nombre ({', '.join(relativas)}). "
                         r"Por ejemplo `~/datos_dane` o `C:\Users\ana\datos_dane`.")
            else:
                try:
                    dd.set_paths(**cambios, save=True)
                except ValueError as e:
                    st.error(str(e))
                else:
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.rerun()

st.divider()
st.caption(
    "Fuente: DANE — Archivo Nacional de Datos (ANDA), microdatos anonimizados de uso público. "
    "Cite: *DANE, Gran Encuesta Integrada de Hogares (GEIH)* / *Encuesta Anual Manufacturera (EAM)*."
)

with hueco_version.container():
    aviso_version_nueva()
