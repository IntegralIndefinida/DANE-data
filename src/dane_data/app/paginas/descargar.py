import logging

import streamlit as st

import dane_data as dd
from dane_data.app._ui import LogEnPantalla, disponibles_eam, disponibles_geih, rutas_actuales

st.title("⬇️ Descargar datos del DANE")
st.markdown(
    "Los archivos se bajan del **Archivo Nacional de Datos (ANDA)** del DANE y se guardan en su computador. "
    "La descarga es **incremental**: si se interrumpe, al repetirla continúa donde iba."
)

encuesta = st.radio("Encuesta", ["GEIH (hogares, mensual)", "EAM (industria, anual)"], horizontal=True)
rutas = rutas_actuales()

if encuesta.startswith("GEIH"):
    serie = st.radio("Serie", ["Principal (2007–2026)", "Empalme (2010–2020)"], horizontal=True,
                     help="El empalme re-pondera 2010–2020 con el censo 2018 para empalmar con 2021 en adelante.")
    empalme = serie.startswith("Empalme")
    anios_ok = dd.geih.ANIOS_EMPALME if empalme else dd.geih.ANIOS_DISPONIBLES
    ya = disponibles_geih(empalme, rutas)
    tiene = set(ya.anio.unique()) if len(ya) else set()
    anios = st.multiselect("Años", anios_ok, default=[anios_ok[-1]],
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    st.caption("✓ = ya descargado (total o parcialmente).")
    NOMBRES = {
        "caracteristicas": "Características generales (edad, sexo, educación, salud)",
        "fuerza_trabajo": "Fuerza de trabajo",
        "ocupados": "Ocupados (empleo, ingresos, formalidad)",
        "desocupados": "Desocupados",
        "inactivos": "Inactivos",
        "vivienda": "Vivienda y hogar",
        "otras_formas_trabajo": "Otras formas de trabajo",
    }
    with st.expander("Opciones avanzadas"):
        modulos = st.multiselect("Módulos", list(NOMBRES), default=list(NOMBRES), format_func=NOMBRES.get,
                                 help="Para los indicadores laborales se necesitan al menos: características, "
                                      "fuerza de trabajo, ocupados y desocupados.")
        prueba = st.toggle("Solo el primer mes de cada año (para probar)")
        borrar = st.toggle("Borrar los ZIP después de extraer (ahorra ~40 % de espacio)", value=True)
    st.info(f"📦 Tamaño aproximado: **{0.6 * len(anios) if not prueba else 0.05 * len(anios):.1f} GB** · "
            f"destino: `{dd.get_path('geih_empalme' if empalme else 'geih')}`")
    lanzar = lambda prog, stop: dd.geih.download(  # noqa: E731
        anios, modules=modulos, empalme=empalme, delete_zips=borrar, limit_files=1 if prueba else None,
        progress=prog, should_stop=stop)
    codigo_py = (f"dd.geih.download({anios!r}" + (", empalme=True" if empalme else "")
                 + (", limit_files=1" if prueba else "") + ")")
else:
    ya = disponibles_eam(rutas)
    tiene = set(ya.anio.unique()) if len(ya) else set()
    todos = dd.eam.ANIOS_DISPONIBLES
    faltan = [a for a in todos if a not in tiene]
    # Valor inicial por session_state (no `default`) para que el botón de abajo pueda
    # cambiar la selección: un `if st.button(...)` la perdía al pulsar "Descargar".
    if "descargar_eam_anios" not in st.session_state:
        st.session_state["descargar_eam_anios"] = faltan[-5:]
    anios = st.multiselect("Años", todos, key="descargar_eam_anios",
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    c1, c2 = st.columns(2)
    c1.button("Seleccionar toda la serie 1992–2024",
              on_click=lambda: st.session_state.update(descargar_eam_anios=list(todos)))
    tic = st.toggle("Incluir módulo de TIC (2008–2018)")
    borrar = st.toggle("Borrar los ZIP después de extraer", value=True)
    st.info(f"📦 Tamaño aproximado: **{10 * len(anios)} MB** · destino: `{dd.get_path('eam')}`")
    lanzar = lambda prog, stop: dd.eam.download(anios, include_tic=tic, delete_zips=borrar,  # noqa: E731
                                                progress=prog, should_stop=stop)
    codigo_py = f"dd.eam.download({anios!r})"

sin_modulos = encuesta.startswith("GEIH") and not modulos  # sin módulos, la librería no sabe qué bajar
if sin_modulos:
    st.warning("Elija al menos un módulo en las opciones avanzadas.")
if st.button("⬇️ Descargar", type="primary", disabled=not anios or sin_modulos):
    barra = st.progress(0.0, text="Conectando con el DANE…")
    detalle = st.empty()
    logs = st.empty()
    handler = LogEnPantalla(logs)
    logger = logging.getLogger("dane_data")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    estado = {"f": 0.0}

    def progreso(f, msg):
        if f is not None:
            estado["f"] = f
            barra.progress(min(f, 1.0), text=msg)
        else:
            detalle.caption(msg)

    try:
        with st.spinner("Descargando… (puede tardar varios minutos; para cancelar use **Stop** arriba a la derecha)"):
            fallidos = lanzar(progreso, None) or []
        st.cache_data.clear()
        st.cache_resource.clear()
        if fallidos:
            barra.progress(1.0, text="Terminó con problemas")
            st.warning(f"⚠️ No se pudo completar todo ({len(fallidos)}):\n\n"
                       + "\n".join(f"- {f}" for f in fallidos)
                       + "\n\nRevise su conexión y vuelva a pulsar **Descargar**: lo que ya está completo se salta.")
        else:
            barra.progress(1.0, text="¡Listo!")
            st.success("Descarga terminada. Ya puede analizar los datos en las demás páginas.")
    except Exception as e:  # noqa: BLE001
        st.error(f"La descarga falló: {e}. Revise su conexión e intente de nuevo; lo ya descargado se conserva.")
    finally:
        logger.removeHandler(handler)

with st.expander("🐍 Hacerlo desde Python o la terminal"):
    st.code(f"import dane_data as dd\n{codigo_py}", language="python")
    st.code("dane-data descargar geih --anios 2024 2025\ndane-data descargar eam --anios 2022 2023 2024", language="bash")
