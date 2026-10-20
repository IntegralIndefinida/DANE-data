import warnings

import streamlit as st

import dane_data as dd
from dane_data.app._ui import fmt_num, barras, botones_descarga, codigo, grafico, linea, selector_eam

st.title("🧱 Panel y microdatos EAM")

dic = dd.diccionario("eam")
with st.sidebar:
    extra = st.multiselect(
        "Variables DANE adicionales", sorted(v.lower() for v in dic if v.lower() not in dd.eam.CORE),
        key="eamm_extra", format_func=lambda v: f"{v} — {dic.get(v.upper(), {}).get('etiqueta', '')[:60]}",
        help="Por ejemplo c3r10c1 (sueldos de obreros) o c4r5c1. Nombres del diccionario 2024; "
             "muchas variables de capítulo cambian de nombre entre épocas.",
    )
eam, descripcion, params = selector_eam(extra=tuple(extra), clave="eamm")
st.caption(f"**Datos:** EAM {descripcion} · {fmt_num(len(eam))} registros")

tab1, tab2 = st.tabs(["🔁 Panel de establecimientos", "🗂️ Microdatos"])

with tab1:
    st.markdown(
        "Cada establecimiento tiene un identificador (`nordest`) que se repite año tras año, lo que permite "
        "construir un **panel**. Un panel **balanceado** conserva solo las plantas observadas en *todos* los años."
    )
    sup = dd.eam.supervivencia(eam)
    if len(sup):
        grafico(linea(sup, x="anio", y="pct_siguen", titulo_y="% que reaparece al año siguiente", pct=True))
        st.caption("Caídas bruscas suelen indicar cambios de identificador o de cobertura, no cierres reales.")
    bal = st.toggle("Panel balanceado")
    sin_micro = st.toggle(
        "Excluir registros microagregados",
        help="El ANDA reemplaza los valores de grupos de establecimientos (casi siempre 3) por el promedio del "
             "grupo. Las sumas no cambian, pero esos valores no son los de cada planta: para análisis por "
             "establecimiento conviene excluirlos.")
    with warnings.catch_warnings():  # el aviso de dd.eam.panel se muestra abajo, en la página
        warnings.simplefilter("ignore", UserWarning)
        pan = dd.eam.panel(eam, balanceado=bal, excluir_microagregados=sin_micro)
    n_est = pan.index.get_level_values("nordest").nunique()
    if not sin_micro and pan["microagregado"].any():
        n_micro = pan.loc[pan["microagregado"], :].index.get_level_values("nordest").nunique()
        st.info(f"ℹ️ {fmt_num(n_micro)} de {fmt_num(n_est)} establecimientos tienen algún año con valores "
                "**microagregados** (el promedio de su grupo, no los propios). Sirven para sumas; para análisis "
                "por establecimiento, exclúyalos o contrólelos con la columna `microagregado`.")
    c = st.columns(3)
    c[0].metric("Establecimientos", f"{n_est:,}".replace(",", "."))
    c[1].metric("Años", pan.index.get_level_values("anio").nunique())
    c[2].metric("Observaciones", f"{fmt_num(len(pan))}")
    por_anio = pan.reset_index().groupby("anio").size().rename("establecimientos").reset_index()
    grafico(barras(por_anio, x="anio", y="establecimientos", titulo_y="Establecimientos"))
    if st.toggle("Preparar panel para descargar", key="pan_dl"):
        botones_descarga(pan.reset_index(), f"panel_eam{'_balanceado' if bal else ''}", "pan")
    codigo(f'''
import dane_data as dd

{params["carga"]}
panel = dd.eam.panel(eam, balanceado={bal}, excluir_microagregados={sin_micro})   # índice (nordest, anio)
dd.eam.supervivencia(eam)
''')

with tab2:
    st.markdown("Variables armonizadas: `anio`, `ciiu`, `ciiu_rev`, `division`, `sector`, `departamento`. "
                "El resto son las originales del DANE en minúscula.")
    with st.expander("¿Qué significa cada variable?"):
        st.dataframe([{"variable": k, "descripción": v} for k, v in dd.eam.ETIQUETAS.items()], hide_index=True)
    st.dataframe(eam.head(1000), hide_index=True, width="stretch")
    if st.toggle("Preparar archivos para descargar", key="micro_dl"):
        botones_descarga(eam, "microdatos_eam", "eammicro")
