from pathlib import Path

import streamlit as st

import dane_data as dd
from dane_data.app._ui import (aviso_version_nueva, disponibles, rutas_actuales)

st.title("DANE-data")
# El aviso va arriba pero se llena al final: sin internet, la consulta no demora el resto de la página
hueco_version = st.empty()
st.markdown(
    "#### Microdatos del DANE listos para analizar\n"
    "Esta aplicación descarga, organiza y resume cuatro fuentes oficiales de Colombia publicadas por el DANE:"
)

c1, c2, c3, c4, c5 = st.columns(5)
with c1, st.container(border=True, height="stretch"):
    st.markdown(
        "##### GEIH — Gran Encuesta Integrada de Hogares\n"
        "Encuesta **mensual** a ~70.000 personas. Es la fuente oficial del **desempleo**, la "
        "**informalidad** y los **ingresos laborales**. Cada fila es una persona; el *factor de "
        "expansión* dice a cuántas personas del país representa.\n\n"
        "**Úsela para:** brechas de género, desempleo juvenil, informalidad por región, "
        "ingresos frente al salario mínimo…\n\n"
        "De la GEIH sale también la **pobreza monetaria** (2012–2025): el DANE publica aparte el ingreso per cápita de "
        "cada hogar y si es pobre, y la página **Pobreza monetaria** calcula sus cifras oficiales."
    )
with c2, st.container(border=True, height="stretch"):
    st.markdown(
        "##### EAM — Encuesta Anual Manufacturera\n"
        "Censo **anual** de ~7.000 establecimientos industriales (1992–2024). Cada fila es una "
        "planta: producción, valor agregado, empleo, salarios, activos y energía.\n\n"
        "**Úsela para:** productividad por sector, participación laboral, concentración "
        "regional, funciones de producción y costos…"
    )
with c3, st.container(border=True, height="stretch"):
    st.markdown(
        "##### EEVV — Estadísticas Vitales\n"
        "Registro de los **certificados** de nacimiento (desde 1998) y de defunción (desde 1979). Cada fila es un hecho "
        "registrado; no es una encuesta.\n\n"
        "**Úsela para:** natalidad y fecundidad, mortalidad infantil y materna, causas de muerte, homicidios, "
        "desigualdades entre departamentos…"
    )
with c4, st.container(border=True, height="stretch"):
    st.markdown(
        "##### EMICRON — Encuesta de Micronegocios\n"
        "Encuesta **anual** (2019–2025) a los negocios de hasta 9 personas ocupadas de los dueños y trabajadores por "
        "cuenta propia que encuentra la GEIH. Cada fila es un micronegocio: ventas, costos, empleo, registros.\n\n"
        "**Úsela para:** informalidad empresarial, productividad de los negocios pequeños, inclusión financiera, "
        "el puente entre los hogares (GEIH) y las empresas (EAM)…"
    )
with c5, st.container(border=True, height="stretch"):
    st.markdown(
        "##### ECV — Encuesta Nacional de Calidad de Vida\n"
        "Encuesta **anual** a ~90.000 hogares (2018–2025): vivienda, servicios, salud, educación, trabajo y tecnologías. "
        "Es la fuente del **Índice de Pobreza Multidimensional**.\n\n"
        "**Úsela para:** pobreza multidimensional por departamento, acceso a servicios, internet, afiliación a "
        "salud, educación…"
    )

st.subheader("¿Cómo empiezo?")
st.markdown(
    "1. **Datos:** si aún no los tiene, vaya a **Descargar datos** (menú izquierdo). "
    "Si ya los descargó, indique la carpeta abajo.\n"
    "2. **Explore:** abra **Indicadores laborales**, **Pobreza monetaria**, **Indicadores industriales**, "
    "**Nacimientos y defunciones**, **Micronegocios** o **Calidad de vida y pobreza**, "
    "elija años y filtros.\n"
    "3. **Exporte:** cada tabla se descarga en CSV, Excel o Stata. Cada página muestra el "
    "**código Python** equivalente para pasar a un notebook cuando esté listo."
)
st.info(
    "**¿Usa dane-data en una tesis, un trabajo o un artículo?** Por favor cítelo, junto con los datos del "
    "DANE: así otras personas lo encuentran y el proyecto puede seguir creciendo. La cita lista para copiar "
    "(APA y BibTeX) está en **Cómo citar** (menú izquierdo).",
    icon=":material/school:",
)

# ---------------------------------------------------------------- Estado de datos
st.subheader("Datos disponibles en este computador")
rutas = rutas_actuales()
g, e, ge = disponibles("geih", rutas, False), disponibles("eam", rutas), disponibles("geih", rutas, True)
v = disponibles("eevv", rutas)
mi = disponibles("emicron", rutas)
c = disponibles("ecv", rutas)
c = c[c["modulo"] == "caracteristicas"] if len(c) else c
pm = disponibles("pobreza", rutas)
pm_anios = pm.anio.dropna() if len(pm) else pm.anio  # las filas del empalme no tienen año

m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
m1.metric("GEIH (serie principal)", f"{g.anio.nunique()} años" if len(g) else "Sin datos",
          f"{g.anio.min()}–{g.anio.max()} · {len(g)} meses" if len(g) else None, delta_color="off")
m2.metric("GEIH (serie de empalme)", f"{ge.anio.nunique()} años" if len(ge) else "Sin datos",
          f"{ge.anio.min()}–{ge.anio.max()}" if len(ge) else None, delta_color="off")
m3.metric("EAM", f"{e.anio.nunique()} años" if len(e) else "Sin datos",
          f"{e.anio.min()}–{e.anio.max()}" if len(e) else None, delta_color="off")
m4.metric("Estadísticas Vitales", f"{v.anio.nunique()} años" if len(v) else "Sin datos",
          f"{v.anio.min()}–{v.anio.max()}" if len(v) else None, delta_color="off")
m5.metric("EMICRON", f"{mi.anio.nunique()} años" if len(mi) else "Sin datos",
          f"{mi.anio.min()}–{mi.anio.max()}" if len(mi) else None, delta_color="off")
m6.metric("ECV", f"{c.anio.nunique()} años" if len(c) else "Sin datos",
          f"{c.anio.min()}–{c.anio.max()}" if len(c) else None, delta_color="off")
m7.metric("Pobreza monetaria", f"{pm_anios.nunique()} años" if len(pm_anios) else "Sin datos",
          f"{pm_anios.min()}–{pm_anios.max()}" if len(pm_anios) else None, delta_color="off")

incompletos = g[~g.completo] if len(g) else g
if len(incompletos):
    with st.expander(f"{len(incompletos)} mes(es) de la GEIH están incompletos y se omitirán",
                     icon=":material/warning:"):
        st.dataframe(incompletos[["anio", "nombre_mes", "carpeta", "faltantes"]], hide_index=True)
        st.caption("Vuelva a descargarlos en Descargar datos. Si siguen incompletos, active «Volver a bajar "
                   "lo que ya está descargado» en las opciones avanzadas.")

# ---------------------------------------------------------------- Configuración
with st.expander("Carpetas de datos", icon=":material/folder:", expanded=not (len(g) or len(e) or len(v) or len(mi) or len(c) or len(pm))):
    st.caption(
        "Indique dónde están (o dónde quiere guardar) los datos. Para la GEIH, la carpeta que "
        "contiene `datos_csv/`; para la EAM, las Estadísticas Vitales, la EMICRON, la ECV y la pobreza, la que contiene `datos/`. Se recuerda para la "
        "próxima vez."
    )
    with st.form("rutas"):
        p_geih = st.text_input("GEIH serie principal", str(dd.get_path("geih")))
        p_emp = st.text_input("GEIH serie de empalme", str(dd.get_path("geih_empalme")))
        p_eam = st.text_input("EAM", str(dd.get_path("eam")))
        p_eevv = st.text_input("Estadísticas Vitales", str(dd.get_path("eevv")))
        p_emicron = st.text_input("EMICRON", str(dd.get_path("emicron")))
        p_ecv = st.text_input("ECV", str(dd.get_path("ecv")))
        p_pobreza = st.text_input("Pobreza monetaria", str(dd.get_path("pobreza")))
        if st.form_submit_button("Guardar", type="primary"):
            # Solo las que cambiaron: así no se fija en el archivo una ruta que viene de una variable de entorno
            cambios = {k: v.strip() for k, v in (("geih", p_geih), ("geih_empalme", p_emp), ("eam", p_eam), ("eevv", p_eevv),
                                                 ("emicron", p_emicron), ("ecv", p_ecv),
                                                 ("pobreza", p_pobreza))
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
    "Cite: *DANE, Gran Encuesta Integrada de Hogares (GEIH)* / *Encuesta Anual Manufacturera (EAM)* / *Estadísticas "
    "Vitales (EEVV)* / *Encuesta de Micronegocios (EMICRON)* / *Encuesta Nacional de Calidad de Vida (ECV)* / "
    "*Medición de Pobreza Monetaria y Desigualdad*."
)

with hueco_version.container():
    aviso_version_nueva()
