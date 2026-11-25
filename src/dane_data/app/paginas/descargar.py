import logging
import threading

import streamlit as st

import dane_data as dd
from dane_data.app._ui import (CERTIFICADOS, LogEnPantalla, args_py, disponibles, fmt_num, rutas_actuales)

def opciones_disco(periodo: str = "años", ahorro: str = "") -> tuple[bool, bool]:
    """Los dos interruptores que comparten todas las encuestas: borrar los ZIP y volver a bajar."""
    borrar = st.toggle(f"Borrar los ZIP después de extraer{ahorro}", value=True)
    forzar = st.toggle("Volver a bajar lo que ya está descargado",
                       help=f"Solo si el DANE corrigió o volvió a publicar esos {periodo}: reemplaza lo que hay.")
    return borrar, forzar


st.title("Descargar datos del DANE")
st.markdown(
    "Los archivos se bajan del **Archivo Nacional de Datos (ANDA)** del DANE y se guardan en su computador. "
    "La descarga es **incremental**: si se interrumpe, al repetirla continúa donde iba."
)

encuesta = st.radio("Encuesta", ["GEIH (hogares, mensual)", "EAM (industria, anual)", "Estadísticas Vitales (nacimientos y defunciones)",
                                 "EMICRON (micronegocios, anual)", "ECV (calidad de vida y pobreza multidimensional)",
                                 "Pobreza monetaria (hogares, anual)"],
                       horizontal=True)
rutas = rutas_actuales()

if encuesta.startswith("GEIH"):
    principal, emp = dd.geih.ANIOS_DISPONIBLES, dd.geih.ANIOS_EMPALME
    serie = st.radio("Serie", [f"Principal ({principal[0]}–{principal[-1]})", f"Empalme ({emp[0]}–{emp[-1]})"],
                     horizontal=True,
                     help="El empalme re-pondera 2010–2020 con el censo 2018 para empalmar con 2021 en adelante.")
    empalme = serie.startswith("Empalme")
    anios_ok = dd.geih.ANIOS_EMPALME if empalme else dd.geih.ANIOS_DISPONIBLES
    ya = disponibles("geih", rutas, empalme)
    tiene = set(ya.anio.unique()) if len(ya) else set()
    anios = st.multiselect("Años", anios_ok, default=[anios_ok[-1]], placeholder="Elija los años",
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
        "otros_ingresos": "Otros ingresos (arriendos, pensiones, ayudas, subsidios)",
        "migracion": "Migración (desde 2022)",
    }
    with st.expander("Opciones avanzadas"):
        modulos = st.multiselect("Módulos", list(NOMBRES), default=list(NOMBRES), format_func=NOMBRES.get,
                                 placeholder="Elija los módulos",
                                 help="Para los indicadores laborales se necesitan al menos: características, "
                                      "fuerza de trabajo, ocupados y desocupados.")
        prueba = st.toggle("Solo el primer mes de cada año (para probar)")
        borrar, forzar = opciones_disco("meses", " (ahorra ~40 % de espacio)")
    st.info(f"Tamaño aproximado: **{fmt_num(0.7 * len(anios) if not prueba else 0.05 * len(anios), 1)} GB** · "
            f"destino: `{dd.get_path('geih_empalme' if empalme else 'geih')}`")
    lanzar = lambda prog, stop: dd.geih.download(  # noqa: E731
        anios, modulos=modulos, empalme=empalme, borrar_zips=borrar, limite_archivos=1 if prueba else None,
        progreso=prog, detener=stop, forzar=forzar)
    # Con todas las opciones elegidas, para que el código haga lo mismo que el botón
    codigo_py = f"dd.geih.download({anios!r}" + args_py(
        modulos=modulos if set(modulos) != set(NOMBRES) else None, empalme=empalme, borrar_zips=borrar,
        limite_archivos=1 if prueba else None, forzar=forzar) + ")"
elif encuesta.startswith("Estadísticas"):
    ya = disponibles("eevv", rutas)
    elegidos = st.multiselect("Certificados", list(CERTIFICADOS), default=list(CERTIFICADOS), placeholder="Elija los certificados",
                              help="Defunciones desde 1979; nacimientos y defunciones fetales desde 1998.")
    tipos = [CERTIFICADOS[c] for c in elegidos]
    todos = sorted({a for t in tipos for a in dd.eevv.ANIOS_DISPONIBLES[t]})
    tiene = set(ya[ya.tipo.isin(tipos)].anio.unique()) if len(ya) else set()
    if "descargar_eevv_anios" not in st.session_state:
        st.session_state["descargar_eevv_anios"] = [2025]
    # Si se quita un certificado, un año elegido puede dejar de existir
    st.session_state["descargar_eevv_anios"] = [a for a in st.session_state["descargar_eevv_anios"] if a in todos]
    anios = st.multiselect("Años", todos, key="descargar_eevv_anios", placeholder="Elija los años",
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    st.button(f"Seleccionar toda la serie {todos[0]}–{todos[-1]}" if todos else "Seleccionar toda la serie", disabled=not todos,
              on_click=lambda: st.session_state.update(descargar_eevv_anios=list(todos)))
    st.caption("✓ = ya descargado. Algunos ZIP del DANE traen varios años (2008–2011, 2012–2013, 2017–2018): se baja el paquete "
               "entero aunque pida uno solo.")
    borrar, forzar = opciones_disco()
    # Promedio por año en disco, ya extraído (toda la serie ocupa unos 3,6 GB)
    peso = sum({"nacimientos": 90, "defunciones": 40, "fetales": 5}[t] for t in tipos) * len(anios)
    st.info(f"Tamaño aproximado en disco: **{peso} MB** · destino: `{dd.get_path('eevv')}`")
    lanzar = lambda prog, stop: dd.eevv.download(anios, tipos=tipos, borrar_zips=borrar, progreso=prog,  # noqa: E731
                                                 detener=stop, forzar=forzar)
    codigo_py = f"dd.eevv.download({anios!r}, tipos={tipos!r}" + args_py(borrar_zips=borrar, forzar=forzar) + ")"
elif encuesta.startswith("EMICRON"):
    ya = disponibles("emicron", rutas)
    tiene = set(ya.anio.unique()) if len(ya) else set()
    todos = dd.emicron.ANIOS_DISPONIBLES
    if "descargar_emicron_anios" not in st.session_state:
        st.session_state["descargar_emicron_anios"] = [a for a in todos if a <= 2024 and a not in tiene][-1:] or [2024]
    anios = st.multiselect("Años", todos, key="descargar_emicron_anios", placeholder="Elija los años",
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    st.button(f"Seleccionar toda la serie {todos[0]}–{todos[-1]}",
              on_click=lambda: st.session_state.update(descargar_emicron_anios=list(todos)))
    st.caption("✓ = ya descargado. 2025 solo cubre las 24 ciudades principales; 2019–2024, todo el país.")
    OPCIONALES = {m: n for m, n in dd.emicron.MODULOS.items() if m not in dd.emicron.FACTORES and m != "identificacion"}
    with st.expander("Opciones avanzadas"):
        modulos = st.multiselect("Módulos", list(OPCIONALES), default=list(OPCIONALES), format_func=OPCIONALES.get,
                                 placeholder="Elija los módulos",
                                 help="La identificación y los factores de expansión se bajan siempre: sin ellos no se "
                                      "puede cargar. No todos los módulos existen todos los años (el COVID solo en 2020).")
        borrar, forzar = opciones_disco()
    todos_mod = set(modulos) == set(OPCIONALES)
    # Unos 70 MB por año ya extraídos con todos los módulos; los ZIP pesan unos 45 MB
    st.info(f"Tamaño aproximado en disco: **{70 * len(anios) if todos_mod else 30 * len(anios)} MB** · "
            f"destino: `{dd.get_path('emicron')}`")
    lanzar = lambda prog, stop: dd.emicron.download(anios, modulos=None if todos_mod else modulos,  # noqa: E731
                                                    borrar_zips=borrar, progreso=prog, detener=stop, forzar=forzar)
    codigo_py = f"dd.emicron.download({anios!r}" + args_py(modulos=None if todos_mod else modulos, borrar_zips=borrar,
                                                          forzar=forzar) + ")"
elif encuesta.startswith("ECV"):
    ya = disponibles("ecv", rutas)
    tiene = set(ya.anio.unique()) if len(ya) else set()
    anios = st.multiselect("Años", dd.ecv.ANIOS_DISPONIBLES, default=[dd.ecv.ANIOS_DISPONIBLES[-1]], placeholder="Elija los años",
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    st.caption("✓ = ya descargado (total o parcialmente).")
    CAPITULOS = {
        "caracteristicas": "Características y composición del hogar", "vivienda": "Datos de la vivienda",
        "servicios": "Servicios del hogar", "tenencia": "Tenencia y financiación de la vivienda",
        "condiciones": "Condiciones de vida del hogar (internet, percepción de pobreza)", "salud": "Salud",
        "primera_infancia": "Atención a menores de 5 años", "educacion": "Educación", "fuerza_trabajo": "Fuerza de trabajo",
        "tic": "Tecnologías de información y comunicación", "trabajo_infantil": "Trabajo infantil",
    }
    with st.expander("Opciones avanzadas"):
        modulos = st.multiselect("Capítulos", list(CAPITULOS), default=list(CAPITULOS), format_func=CAPITULOS.get,
                                 placeholder="Elija los capítulos",
                                 help="Los indicadores usan todos menos trabajo infantil; el IPM, vivienda, servicios, "
                                      "condiciones, salud, primera infancia, educación y fuerza de trabajo.")
        borrar, forzar = opciones_disco()
    # Los ZIP de 2024 y 2025 pesan mucho más: unos 1,4 GB con los once capítulos, contra 150 MB de los años anteriores
    peso = sum(1.4 if a >= 2024 else 0.15 for a in anios) * len(modulos) / len(CAPITULOS)
    st.info(f"Tamaño aproximado de la descarga: **{fmt_num(peso, 1)} GB** · destino: `{dd.get_path('ecv')}`")
    lanzar = lambda prog, stop: dd.ecv.download(anios, modulos=modulos, borrar_zips=borrar, progreso=prog,  # noqa: E731
                                                detener=stop, forzar=forzar)
    codigo_py = f"dd.ecv.download({anios!r}" + args_py(
        modulos=modulos if set(modulos) != set(CAPITULOS) else None, borrar_zips=borrar, forzar=forzar) + ")"
elif encuesta.startswith("Pobreza"):
    ya = disponibles("pobreza", rutas)
    tiene = set(ya.anio.dropna().astype(int)) if len(ya) else set()  # las filas del empalme no tienen año
    todos = dd.pobreza.ANIOS_DISPONIBLES
    if "descargar_pobreza_anios" not in st.session_state:
        st.session_state["descargar_pobreza_anios"] = [a for a in todos if a not in tiene][-3:] or [todos[-1]]
    anios = st.multiselect("Años", todos, key="descargar_pobreza_anios", placeholder="Elija los años",
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    st.button(f"Seleccionar toda la serie {todos[0]}–{todos[-1]}",
              on_click=lambda: st.session_state.update(descargar_pobreza_anios=list(todos)))
    empalme = st.toggle("Bajar también los archivos del empalme", value=True,
                        help="Para la serie comparable 2012–2025 que publica el DANE: el factor de empalme, las líneas "
                             "actualizadas de 2012–2018 y los hogares empalmados de 2021 (unos 60 MB, una sola vez).")
    personas = st.toggle("Bajar también el archivo de personas",
                         help="Los componentes del ingreso de cada persona. Los indicadores solo necesitan el de hogares; "
                              "el de personas ocupa unas seis veces más.")
    borrar, forzar = opciones_disco()
    archivos = ["hogares", "personas"] if personas else ["hogares"]
    # Ya extraído: unos 36 MB por año los hogares y 220 MB las personas (toda la serie ocupa 3,7 GB)
    peso = (36 + 220 * personas) * len(anios) + 100 * empalme
    st.info(f"Tamaño aproximado en disco: **{peso} MB** · destino: `{dd.get_path('pobreza')}`")
    lanzar = lambda prog, stop: dd.pobreza.download(anios, archivos=archivos, empalme=empalme,  # noqa: E731
                                                    borrar_zips=borrar, progreso=prog, detener=stop, forzar=forzar)
    codigo_py = f"dd.pobreza.download({anios!r}, archivos={archivos!r}" + args_py(
        empalme=empalme, borrar_zips=borrar, forzar=forzar) + ")"
elif encuesta.startswith("EAM"):
    ya = disponibles("eam", rutas)
    tiene = set(ya.anio.unique()) if len(ya) else set()
    todos = dd.eam.ANIOS_DISPONIBLES
    faltan = [a for a in todos if a not in tiene]
    # Valor inicial por session_state (no `default`) para que el botón de abajo pueda
    # cambiar la selección: un `if st.button(...)` la perdía al pulsar "Descargar".
    if "descargar_eam_anios" not in st.session_state:
        st.session_state["descargar_eam_anios"] = faltan[-5:]
    anios = st.multiselect("Años", todos, key="descargar_eam_anios", placeholder="Elija los años",
                           format_func=lambda a: f"{a} ✓" if a in tiene else str(a))
    st.button(f"Seleccionar toda la serie {todos[0]}–{todos[-1]}",
              on_click=lambda: st.session_state.update(descargar_eam_anios=list(todos)))
    tic = st.toggle("Incluir módulo de TIC (2008–2018)")
    borrar, forzar = opciones_disco()
    st.info(f"Tamaño aproximado: **{10 * len(anios)} MB** · destino: `{dd.get_path('eam')}`")
    lanzar = lambda prog, stop: dd.eam.download(anios, incluir_tic=tic, borrar_zips=borrar,  # noqa: E731
                                                progreso=prog, detener=stop, forzar=forzar)
    codigo_py = f"dd.eam.download({anios!r}" + args_py(incluir_tic=tic, borrar_zips=borrar, forzar=forzar) + ")"

sin_modulos = encuesta.startswith(("GEIH", "ECV")) and not modulos  # sin módulos, la librería no sabe qué bajar
if sin_modulos:
    st.warning("Elija al menos un módulo en las opciones avanzadas.")
sin_certificados = encuesta.startswith("Estadísticas") and not tipos
if sin_certificados:
    st.warning("Elija al menos un certificado.")
if st.button("Descargar", type="primary", icon=":material/download:",
             disabled=not anios or sin_modulos or sin_certificados):
    barra = st.progress(0.0, text="Conectando con el DANE…")
    detalle = st.empty()
    logs = st.empty()
    handler = LogEnPantalla(logs)
    # El registro es uno para todas las sesiones: en modo aula, cada quien ve solo las líneas de su descarga
    handler.addFilter(lambda r, hilo=threading.get_ident(): r.thread == hilo)
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
            st.warning(f"No se pudo completar todo ({len(fallidos)}):\n\n"
                       + "\n".join(f"- {f}" for f in fallidos)
                       + "\n\nRevise su conexión y vuelva a pulsar **Descargar**: lo que ya está completo se salta.",
                       icon=":material/warning:")
        else:
            barra.progress(1.0, text="¡Listo!")
            st.success("Descarga terminada. Ya puede analizar los datos en las demás páginas.")
    except Exception as e:  # noqa: BLE001
        st.error(f"La descarga falló: {e}. Revise su conexión e intente de nuevo; lo ya descargado se conserva.")
    finally:
        logger.removeHandler(handler)

with st.expander("Hacerlo desde Python o la terminal", icon=":material/code:"):
    st.code(f"import dane_data as dd\n{codigo_py}", language="python")
    st.code("dane-data descargar geih --anios 2024 2025\ndane-data descargar eam --anios 2022 2023 2024\n"
            "dane-data descargar eevv --anios 2025 --tipos nacimientos defunciones\n"
            "dane-data descargar emicron --anios 2023 2024\n"
            "dane-data descargar ecv --anios 2025\n"
            "dane-data descargar pobreza --anios 2024 2025 --archivos hogares --empalme", language="bash")
