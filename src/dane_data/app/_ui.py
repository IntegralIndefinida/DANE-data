"""Piezas compartidas de la app: gráficos, caché de datos, descargas y avisos."""

from __future__ import annotations

import io
import logging
import re
import warnings
from collections import deque

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dane_data as dd
from dane_data.app import _actualizacion

# Paleta categórica validada (orden fijo; nunca se recicla). Ver skill dataviz. Es la misma en los dos modos: pasa las
# pruebas sobre el fondo claro y sobre el oscuro (#1a1a19). Una por modo no sirve: al elegir otro modo en el menú,
# Streamlit no vuelve a dibujar las gráficas y quedaban con los colores del modo anterior.
PALETA = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9", "#e66767"]
MAX_SERIES = len(PALETA)
# Grupos con orden (edades, niveles educativos, años): un solo tono, de claro a oscuro, para que el orden se vea en el
# color. Seis pasos entre el 250 (#86b6ef) y el 600 (#184f95) del azul de la skill dataviz, interpolados en OKLab:
# validados como ordinales sobre los dos fondos, y no caben más con un salto visible entre vecinos.
RAMPA = ["#86b6ef", "#70a1dd", "#5a8ccb", "#4477b9", "#2f63a7", "#184f95"]
GRIS = "#898781"  # «Sin información» y parecidos, que no van en el orden
SIN_DATO = re.compile(r"desconocid|sin informaci|sin detalle", re.IGNORECASE)


def _rampa(n: int) -> list[str]:
    """``n`` tonos de RAMPA, repartidos de punta a punta."""
    return [PALETA[0]] if n == 1 else [RAMPA[round(i * (len(RAMPA) - 1) / (n - 1))] for i in range(n)]


def _grupos_posibles(s: pd.Series) -> list[str]:
    """Todos los grupos de una columna, en su orden: las categorías, aunque los filtros dejen solo algunas."""
    if isinstance(s.dtype, pd.CategoricalDtype):
        return [str(c) for c in s.cat.categories]
    return [str(v) for v in sorted(s.dropna().unique())]


def colores(grupos: list[str], universo: list[str], ordenados: bool = False) -> dict[str, str]:
    """
    El color de cada grupo sigue al grupo, no a su posición: quitar Antioquia no pinta a Atlántico de otro color.
    Si todos los grupos posibles (``universo``) caben en la paleta, cada uno lleva el de su lugar ahí. Si no caben
    (33 departamentos), cada grupo guarda su color en la sesión mientras siga elegido, y uno nuevo toma el primero libre.
    Los ``ordenados`` van en RAMPA si caben (si todos los posibles no caben, los tonos se reparten entre los visibles).
    """
    if ordenados:
        reales = [g for g in universo if not SIN_DATO.search(g)]
        base = reales if len(reales) <= len(RAMPA) else [g for g in grupos if g in reales]
        if len(base) <= len(RAMPA):
            tonos = dict(zip(base, _rampa(len(base))))
            return {g: tonos.get(g, GRIS) for g in grupos}
    if len(universo) <= len(PALETA):
        return {g: PALETA[universo.index(g)] for g in grupos}
    memoria = st.session_state.setdefault("colores_grupos", {}).setdefault(tuple(universo), {})
    for g in [g for g in memoria if g not in grupos]:
        del memoria[g]
    for g in grupos:
        if g not in memoria:
            memoria[g] = [c for c in PALETA if c not in memoria.values()][0]  # los llamadores eligen <= MAX_SERIES
    return {g: memoria[g] for g in grupos}


def _por_grupo(df: pd.DataFrame, color: str | None, todos: pd.Series | None) -> tuple[pd.DataFrame, dict]:
    """``df`` con el grupo como texto, y los colores y el orden de la leyenda para px."""
    if not color:
        return df, {"color_discrete_sequence": PALETA}
    s = df[color] if todos is None else todos
    universo = _grupos_posibles(s)
    ordenados = (isinstance(s.dtype, pd.CategoricalDtype) and bool(s.cat.ordered)) or pd.api.types.is_numeric_dtype(s)
    df = df.assign(**{color: df[color].astype(str)})
    presentes = set(df[color])
    universo += [g for g in sorted(presentes) if g not in universo]
    grupos = [g for g in universo if g in presentes]
    return df, {"color_discrete_map": colores(grupos, universo, ordenados), "category_orders": {color: grupos}}


# --------------------------------------------------------------------------- #
# Formato
# --------------------------------------------------------------------------- #
def fmt_num(x: float, dec: int = 0) -> str:
    if pd.isna(x):
        return "—"
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pesos(x: float) -> str:
    return "—" if pd.isna(x) else "$ " + fmt_num(x)


def fmt_pct(x: float) -> str:
    return "—" if pd.isna(x) else fmt_num(x, 1) + " %"


def variacion(actual: float, anterior: float, anio: int, pp: bool = False, inversa: bool = False) -> dict:
    """
    ``delta`` y ``delta_color`` de st.metric, con coma decimal: en puntos porcentuales (``pp``) o en %.
    Una variación que redondea a cero va en gris y sin flecha (antes salía «-0.0» en verde).
    """
    if pd.isna(actual) or pd.isna(anterior) or (not pp and anterior == 0):
        return {}
    d = round(actual - anterior if pp else 100 * (actual / anterior - 1), 1)
    unidad = "p.p." if pp else "%"
    if d == 0:
        return {"delta": f"0,0 {unidad} vs {anio}", "delta_color": "off", "delta_arrow": "off"}
    return {"delta": f"{'+' if d > 0 else ''}{fmt_num(d, 1)} {unidad} vs {anio}",
            "delta_color": "inverse" if inversa else "normal"}


def fmt_grande(x: float) -> str:
    """12.345.678 → '12,3 millones'."""
    if pd.isna(x):
        return "—"
    for div, suf in ((1e12, "billones"), (1e9, "mil millones"), (1e6, "millones"), (1e3, "mil")):
        if abs(x) >= div:
            return f"{fmt_num(x / div, 1)} {suf}"
    return fmt_num(x)


# --------------------------------------------------------------------------- #
# Gráficos
# --------------------------------------------------------------------------- #
def _estilo(fig: go.Figure, titulo_y: str | None = None, pct: bool = False) -> go.Figure:
    fig.update_layout(
        separators=",.",  # decimales con coma y miles con punto (español)
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        hoverlabel=dict(namelength=-1),
        font=dict(size=13),
    )
    fig.update_xaxes(showgrid=False, title=None)
    # Eje desde cero: evita que cambios de décimas parezcan enormes.
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.18)", zeroline=False, title=titulo_y, rangemode="tozero",
                     ticksuffix=" %" if pct else None, tickformat=",~f")
    return fig


MAX_PUNTOS = 24  # más puntos por línea y la gráfica va sin marcadores


def _valor(eje: str, pct: bool) -> str:
    """El valor en el recuadro al pasar el mouse: redondeado, con coma decimal (``separators``) y «%» si es tasa."""
    return f"%{{{eje}:,.1f}} %" if pct else f"%{{{eje}:,.2~f}}"


def linea(df: pd.DataFrame, x: str, y: str, color: str | None = None, titulo_y: str | None = None,
          pct: bool = False, todos: pd.Series | None = None) -> go.Figure:
    """``todos``: la columna de grupos original, si ``df`` ya no tiene sus categorías (filtrada o como texto)."""
    df, colores_px = _por_grupo(df, color, todos)
    # Un punto en cada dato solo si son pocos: en una serie mensual larga (240 meses) tapaban la línea
    puntos = df.groupby(color)[x].nunique().max() if color else df[x].nunique()
    fig = px.line(df, x=x, y=y, color=color, markers=puntos <= MAX_PUNTOS, **colores_px)
    # Sin esto, el recuadro repetía la fecha y mostraba el nombre de la columna con seis decimales («td=7,977104 %»)
    fig.update_traces(line=dict(width=2), marker=dict(size=8),
                      hovertemplate=("%{fullData.name}: " if color else "") + _valor("y", pct) + "<extra></extra>")
    fig = _estilo(fig, titulo_y, pct)
    fig.update_layout(hovermode="x unified")
    if pd.api.types.is_integer_dtype(df[x]) or x == "anio":
        fig.update_xaxes(dtick=1 if df[x].nunique() <= 15 else None, tickformat="d")
    elif pd.api.types.is_datetime64_any_dtype(df[x]):  # series mensuales (día 1): «marzo de 2025», no «mar 1, 2025»
        fig.update_xaxes(hoverformat="%B de %Y")
    return fig


def barras(df: pd.DataFrame, x: str, y: str, color: str | None = None, titulo_y: str | None = None,
           pct: bool = False, horizontal: bool = False, todos: pd.Series | None = None) -> go.Figure:
    df, colores_px = _por_grupo(df, color, todos)
    if horizontal:
        fig = px.bar(df, y=x, x=y, color=color, orientation="h", barmode="group", **colores_px)
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(gridcolor="rgba(128,128,128,0.18)", title=titulo_y, ticksuffix=" %" if pct else None,
                         tickformat=",~f")
        fig.update_layout(separators=",.", margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=1.02, title=None),
                          height=max(350, 24 * df[x].nunique() * (df[color].nunique() if color else 1)))
    else:
        fig = px.bar(df, x=x, y=y, color=color, barmode="group", **colores_px)
        fig = _estilo(fig, titulo_y, pct)
    # «Hombre: 58,5 %», con el grupo de color delante si lo hay; no «anio=2025<br>sexo=Hombre<br>porcentaje=58.4567»
    categoria, valor = ("%{y}", _valor("x", pct)) if horizontal else ("%{x}", _valor("y", pct))
    fig.update_traces(marker_line_width=0, hovertemplate=("%{fullData.name} · " if color else "") + categoria + ": "
                      + valor + "<extra></extra>")
    # Barras delgadas (skill dataviz: <= 24 px, con aire alrededor) y punta redondeada de 4 px. Plotly no fija el ancho
    # en píxeles: el hueco sale de cuántas barras hay, para unos 24 px en una gráfica de ~950 px de ancho. Las horizontales
    # ya miden 18 px (24 px de alto por barra, menos el hueco).
    por_grupo = df[color].nunique() if color else 1
    hueco = 0.25 if horizontal else min(0.9, max(0.2, 1 - 24 * por_grupo * df[x].nunique() / 950))
    fig.update_layout(bargap=hueco, bargroupgap=0.08, barcornerradius=4)
    return fig


# Meses y días en español para las fechas de Plotly: config "locale": "es" solo no basta, porque el archivo de ese
# idioma no viene con Streamlit y las fechas salían en inglés («Jan 2025»).
_MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
          "noviembre", "diciembre"]
_DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"]
LOCALE_ES = {"format": {"months": _MESES, "shortMonths": [m[:3] for m in _MESES], "days": _DIAS,
                        "shortDays": [d[:3] for d in _DIAS], "date": "%d/%m/%Y"}}


def grafico(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "locale": "es", "locales": {"es": LOCALE_ES}})


# --------------------------------------------------------------------------- #
# Datos (caché en memoria de la sesión del servidor)
# --------------------------------------------------------------------------- #
def _barra(texto: str):
    barra = st.progress(0.0, text=texto)
    return barra, lambda f, m: barra.progress(min(f, 1.0), text=m)


# Los resultados de la GEIH salen de dd.geih.serie_*: se calculan año por año y quedan en disco, así
# que nunca hay más de un año de microdatos en memoria. `meses_disp` va en la llave para que un mes
# recién descargado se vea.
@st.cache_data(max_entries=50, show_spinner=False)
def serie_geih(anios: tuple, por: str | None, anual: bool, empalme: bool, filtros: dict, meses: tuple | None,
               meses_disp: tuple, rutas: tuple) -> pd.DataFrame:
    barra, progreso = _barra("Preparando indicadores…")
    res = dd.geih.serie_indicadores(list(anios), por=por, anual=anual, empalme=empalme, progress=progreso,
                                    filtros=filtros or None, meses=list(meses) if meses else None)
    barra.empty()
    return res


@st.cache_data(max_entries=100, show_spinner=False)
def tabla_geih(anios: tuple, por: tuple, variable: str | None, estadistico: str, poblacion: str | None,
               filtros: dict, meses: tuple | None, dropna: bool, columnas: tuple, empalme: bool,
               meses_disp: tuple, rutas: tuple) -> pd.DataFrame:
    barra, progreso = _barra("Preparando la tabla…")
    res = dd.geih.serie_tabla(list(anios), list(por), variable, estadistico, poblacion, filtros or None,
                              list(meses) if meses else None, dropna, list(columnas) or "core", empalme,
                              progress=progreso)
    barra.empty()
    return res


@st.cache_data(max_entries=50, show_spinner=False)
def frecuencias_geih(anios: tuple, variable: str | None, por: tuple, poblacion: str | None, filtros: dict,
                     meses: tuple | None, columnas: tuple, empalme: bool, meses_disp: tuple,
                     rutas: tuple) -> pd.DataFrame:
    barra, progreso = _barra("Preparando la distribución…")
    res = dd.geih.serie_frecuencias(list(anios), variable, list(por), poblacion, filtros or None,
                                    list(meses) if meses else None, list(columnas) or "core", empalme,
                                    progress=progreso)
    barra.empty()
    return res


@st.cache_data(max_entries=5, show_spinner="Leyendo un mes de microdatos…")
def muestra_geih(anio: int, mes: int, variables: tuple, columnas: tuple, empalme: bool, rutas: tuple) -> pd.DataFrame:
    """Un solo mes de microdatos (vista previa, tipos de las variables adicionales)."""
    return dd.geih.load(anio, months=mes, columns=list(columnas) or "core", empalme=empalme,
                        variables=list(variables))


def args_py(**kw) -> str:
    """Argumentos para el código equivalente: solo los que no tienen su valor por defecto."""
    return "".join(f", {k}={v!r}" for k, v in kw.items() if v not in (None, False, {}, (), [], "core"))


@st.cache_resource(max_entries=2, show_spinner=False)
def cargar_eam(anios: tuple, extra: tuple, rutas: tuple) -> pd.DataFrame:
    return dd.eam.load(list(anios), columns=list(extra) or "core")


# Como en la GEIH: las Estadísticas Vitales salen de dd.eevv.serie_* y tasas, año por año, y quedan en disco. Sus avisos
# de cobertura se muestran en la barra lateral (seleccion_eevv): aquí solo llegarían a la terminal. ``rutas``
# (rutas_actuales()) es parte de la llave: si la carpeta cambia por fuera de la app, se recalcula.
@st.cache_data(max_entries=50, show_spinner=False)
def indicadores_eevv(anios, tipo: str, por: str | None, filtros: dict, rutas: tuple) -> pd.DataFrame:
    barra, progreso = _barra("Preparando indicadores…")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        res = dd.eevv.serie_indicadores(anios, tipo, por=por, filtros=filtros or None, progress=progreso)
    barra.empty()
    return res


@st.cache_data(max_entries=50, show_spinner=False)
def conteos_eevv(anios, tipo: str, por: str | None, filtros: dict, rutas: tuple) -> pd.DataFrame:
    barra, progreso = _barra("Preparando la tabla…")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        res = dd.eevv.serie_conteos(anios, tipo, por=por, filtros=filtros or None, progress=progreso)
    barra.empty()
    return res


@st.cache_data(max_entries=20, show_spinner=False)
def tasas_eevv(anios, por: str | None, rutas: tuple) -> pd.DataFrame:
    barra, progreso = _barra("Calculando las tasas…")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        res = dd.eevv.tasas(anios, por=por, progress=progreso)
    barra.empty()
    return res


def rutas_actuales() -> tuple:
    """Parte de la llave de caché: si el usuario cambia de carpeta, se recarga."""
    return tuple(sorted(dd.show_paths().items()))


@st.cache_data(ttl=30, show_spinner=False)
def disponibles_geih(empalme: bool, rutas: tuple) -> pd.DataFrame:
    return dd.geih.available(empalme=empalme)


@st.cache_data(ttl=30, show_spinner=False)
def disponibles_eam(rutas: tuple) -> pd.DataFrame:
    return dd.eam.available()


@st.cache_data(ttl=30, show_spinner=False)
def disponibles_eevv(rutas: tuple) -> pd.DataFrame:
    return dd.eevv.available()


# --------------------------------------------------------------------------- #
# Exportar
# --------------------------------------------------------------------------- #
def _excel(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


def _stata(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    d = df.copy()
    largos = []
    # Stata no acepta categorías/nullable, objetos que no son todos texto ni nombres largos. Se decide por el
    # tipo de la columna y no por sus valores, para que una muestra (botones_descarga) diga si se puede.
    for c in d.columns:
        if isinstance(d[c].dtype, pd.CategoricalDtype) or pd.api.types.is_string_dtype(d[c].dtype) \
                or pd.api.types.is_object_dtype(d[c].dtype):
            d[c] = d[c].astype(object).where(d[c].notna(), "").astype(str)
            if d[c].str.len().max() > 2045:  # más largo, solo como strL
                largos.append(c[:32])
        elif pd.api.types.is_extension_array_dtype(d[c]):
            d[c] = d[c].astype("float64")
    d.columns = [c[:32] for c in d.columns]
    d.to_stata(buf, write_index=False, version=118, convert_strl=largos)
    return buf.getvalue()


def botones_descarga(df: pd.DataFrame, nombre: str, key: str) -> None:
    # Cada archivo se arma al hacer clic (data como función): armar los tres formatos en cada interacción
    # hacía lenta la página aunque nadie descargara.
    c1, c2, c3 = st.columns(3)
    c1.download_button("CSV", lambda: df.to_csv(index=False).encode("utf-8-sig"), f"{nombre}.csv",
                       "text/csv", key=f"{key}_csv", width="stretch", icon=":material/download:")
    if len(df) < 1_000_000:
        c2.download_button("Excel", lambda: _excel(df), f"{nombre}.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           key=f"{key}_xlsx", width="stretch", icon=":material/download:")
    else:
        c2.caption("Excel no admite más de 1 millón de filas.")
    try:
        _stata(df.head(50))  # basta una muestra: _stata decide por el tipo de cada columna, no por sus valores
    except Exception as e:  # noqa: BLE001
        c3.caption(f"Stata no disponible: {e}")
    else:
        c3.download_button("Stata (.dta)", lambda: _stata(df), f"{nombre}.dta", "application/x-stata-dta",
                           key=f"{key}_dta", width="stretch", icon=":material/download:")


def aviso_version_nueva() -> None:
    """
    Si hay una versión nueva en PyPI: sus novedades y cómo instalarla, con un botón en el zip para
    estudiantes. Se revisa una vez por sesión (y como mucho una vez al día en internet); nada se actualiza
    sin el clic.
    """
    if "version_nueva" not in st.session_state:
        st.session_state["version_nueva"] = _actualizacion.revisar()
    if st.session_state["version_nueva"] is None:
        return
    version, novedades = st.session_state["version_nueva"]
    with st.container(border=True):
        st.markdown(f"#### Hay una versión nueva de dane-data: {version}\n"
                    f"Usted tiene la {dd.__version__}. Actualizar no borra sus datos descargados.")
        with st.expander("Qué cambia en la versión nueva"):
            st.markdown(novedades or f"Vea las [novedades]({_actualizacion.URL_DOCS}novedades.html).")
        carpeta = _actualizacion.carpeta_zip()
        if carpeta is None:
            st.markdown("Para actualizar, en la terminal:")
            st.code('pip install --upgrade "dane-data[app]"', language="bash")
        elif st.session_state.get("actualizado") == version:
            st.success("Listo. Cierre esta pestaña y la ventana negra de dane-data, y vuelva a abrir el lanzador: "
                       "abrirá con la versión nueva.")
        elif st.button(f"Actualizar a la {version}", type="primary"):
            with st.spinner("Descargando la versión nueva… puede tardar unos minutos."):
                error = _actualizacion.actualizar_zip(carpeta, version)
            if error:
                st.error("No se pudo actualizar. Revise su conexión a internet e intente de nuevo; se sigue usando "
                         f"la versión {dd.__version__}.\n\nDetalle: {error}")
            else:
                st.session_state["actualizado"] = version
                st.rerun()


def codigo(texto: str) -> None:
    with st.expander("Ver el código Python equivalente", icon=":material/code:"):
        st.caption("Copie esto en un notebook para reproducir o extender el análisis con la librería `dane-data`.")
        st.code(texto.strip(), language="python")


# --------------------------------------------------------------------------- #
# Logs de descarga en pantalla
# --------------------------------------------------------------------------- #
class LogEnPantalla(logging.Handler):
    def __init__(self, contenedor, lineas: int = 12):
        super().__init__(level=logging.INFO)
        self.contenedor = contenedor
        self.buffer: deque[str] = deque(maxlen=lineas)
        self.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))

    def emit(self, record):
        msg = self.format(record).strip()
        if msg:
            self.buffer.append(msg)
            self.contenedor.code("\n".join(self.buffer), language=None)


def sin_datos(encuesta: str, aviso: str | None = None) -> None:
    """Aviso en la página, no en la barra lateral: en el celular la barra está cerrada y la página quedaba en blanco."""
    st.warning(aviso or f"No se encontraron datos de la {encuesta} en la carpeta configurada.")
    with st.container(horizontal=True, vertical_alignment="center"):
        if st.button("Ir a Descargar datos", type="primary", icon=":material/download:"):
            st.switch_page("paginas/descargar.py")
        st.page_link("paginas/inicio.py", label="o configurar la carpeta en Inicio", icon=":material/folder:")
    st.stop()


# --------------------------------------------------------------------------- #
# Selector GEIH (barra lateral compartida)
# --------------------------------------------------------------------------- #
AYUDA_ANIOS = ("Los resultados se calculan año por año y quedan guardados: la primera vez tardan unos "
               "segundos por año y después son instantáneos.")


def _rangos(anios) -> str:
    """[2007, 2008, 2009, 2021] -> "2007–2009 y 2021"."""
    tramos = []
    for a in sorted(anios):
        if tramos and a == tramos[-1][1] + 1:
            tramos[-1][1] = a
        else:
            tramos.append([a, a])
    textos = [f"{i}–{f}" if f > i else str(i) for i, f in tramos]
    return textos[0] if len(textos) == 1 else ", ".join(textos[:-1]) + " y " + textos[-1]


def aviso_marcos(anios, empalme: bool) -> None:
    """Advierte cuando los años elegidos mezclan marcos de la GEIH: la serie salta por método, no por el mercado."""
    grupos: dict[str, list[int]] = {}
    for a in anios:
        grupos.setdefault(dd.geih.marco_muestral(a, empalme), []).append(a)
    if len(grupos) < 2:
        return
    partes = [f"{_rangos(v)} {'usan' if len(v) > 1 else 'usa'} {dd.geih.MARCOS[k]}" for k, v in grupos.items()]
    texto = ("**Los años elegidos mezclan dos versiones de la GEIH que no son comparables.** "
             + "; ".join(partes) + ". Entre esos años la serie salta por el cambio de método, no por el mercado "
             "laboral (la población en edad de trabajar cambia ~5 %).")
    if any(2010 <= a <= 2020 for a in anios):
        texto += " Para comparar 2010–2020 sin saltos use la serie de empalme."
    st.warning(texto, icon=":material/warning:")


def seleccion_geih(clave: str = "geih", varios_anios: bool = True, ayuda_anios: str = AYUDA_ANIOS) -> dict:
    """Dibuja la barra lateral de la GEIH y devuelve la selección, sin cargar datos."""
    with st.sidebar:
        st.header("Datos GEIH")
        serie = st.radio("Serie", ["Principal", "Empalme (2010–2020)"], horizontal=True, key=f"{clave}_serie",
                         help="La serie de empalme re-pondera 2010–2020 con el censo 2018, para comparar "
                              "con los datos desde 2021 sin saltos.")
    empalme = serie != "Principal"
    av = disponibles_geih(empalme, rutas_actuales())
    if av.empty:
        sin_datos("GEIH")
    av = av[av.completo]
    if av.empty:  # hay meses, pero a todos les falta algo: sin esto, pedía elegir un año de una lista vacía
        sin_datos("GEIH", "Los meses de la GEIH que hay en la carpeta están incompletos y no se pueden usar. "
                          "Vea cuáles y qué les falta en Inicio, y vuelva a descargarlos.")
    with st.sidebar:
        anios_disp = sorted(av.anio.unique())
        defecto = anios_disp[-2:] if varios_anios else anios_disp[-1:]
        anios = st.multiselect("Años", anios_disp, default=defecto, key=f"{clave}_anios", help=ayuda_anios,
                               placeholder="Elija los años")
        if not anios:
            st.info("Elija al menos un año.")
            st.stop()
        meses_disp = sorted(av[av.anio.isin(anios)].mes.unique())
        todos = st.toggle("Todos los meses", True, key=f"{clave}_todos")
        meses = None
        if not todos:
            meses = st.multiselect("Meses", meses_disp, default=meses_disp[:1], format_func=dd.MESES.get,
                                   placeholder="Elija los meses",
                                   key=f"{clave}_meses")
            if not meses:
                st.stop()

        st.header("Filtros")
        sexo = st.multiselect("Sexo", ["Hombre", "Mujer"], key=f"{clave}_sexo", placeholder="Todos")
        zona = st.multiselect("Zona", ["Urbano (cabecera)", "Rural (centros poblados y disperso)"],
                              key=f"{clave}_zona", placeholder="Todas")
        edad = st.slider("Edad", 0, 100, (0, 100), key=f"{clave}_edad")
        dptos = st.multiselect("Departamento", sorted(dd.DEPARTAMENTOS.values()), key=f"{clave}_dpto",
                               placeholder="Todos")

    partes = [f"{'empalme ' if empalme else ''}{', '.join(map(str, sorted(anios)))}"]
    if meses:
        partes.append(", ".join(dd.MESES[m] for m in sorted(meses)))
    for nombre, val in (("sexo", sexo), ("zona", zona), ("dpto", dptos)):
        if val:
            partes.append(f"{nombre}: {', '.join(val)}")
    if edad != (0, 100):
        partes.append(f"edad {edad[0]}–{edad[1]}")

    elegidos = av[av.anio.isin(anios)]
    seleccion = {
        "anios": sorted(map(int, anios)), "meses": sorted(map(int, meses)) if meses else None, "empalme": empalme,
        "sexo": sexo, "zona": zona, "edad": edad, "dptos": dptos, "descripcion": " · ".join(partes),
        "meses_disponibles": tuple(zip(elegidos.anio.tolist(), elegidos.mes.tolist())),
        "filtrada": bool(meses or sexo or zona or dptos or edad != (0, 100)),
        # en el formato de dd.geih.filtrar
        "filtros": {k: v for k, v in (("sexo", list(sexo)), ("zona", list(zona)),
                                      ("edad", tuple(edad) if edad != (0, 100) else None),
                                      ("departamento", list(dptos))) if v},
    }
    aviso_marcos(seleccion["anios"], empalme)
    return seleccion


# --------------------------------------------------------------------------- #
# Selector de las Estadísticas Vitales (barra lateral)
# --------------------------------------------------------------------------- #
CERTIFICADOS = {"Defunciones": "defunciones", "Nacimientos": "nacimientos", "Defunciones fetales": "fetales"}


def seleccion_eevv(clave: str = "eevv") -> dict:
    """Dibuja la barra lateral de las Estadísticas Vitales y devuelve la selección, sin cargar datos."""
    av = disponibles_eevv(rutas_actuales())
    if av.empty:
        sin_datos("serie de Estadísticas Vitales")
    with st.sidebar:
        st.header("Estadísticas Vitales")
        presentes = {nombre: t for nombre, t in CERTIFICADOS.items() if t in set(av["tipo"])}
        tipo = presentes[st.radio("Certificado", list(presentes), key=f"{clave}_tipo")]
        anios_disp = sorted(int(a) for a in av.loc[av["tipo"] == tipo, "anio"])
        inicio = next(a for a in anios_disp if a >= anios_disp[-1] - 9)
        # La llave lleva el tipo: los años disponibles cambian, y un rango viejo de otro tipo no sería válido
        lo, hi = st.select_slider("Años", options=anios_disp, value=(inicio, anios_disp[-1]), key=f"{clave}_rango_{tipo}",
                                  help=AYUDA_ANIOS) if len(anios_disp) > 1 else (anios_disp[0], anios_disp[0])
        anios = [a for a in anios_disp if lo <= a <= hi]

        st.header("Filtros")
        # Fetales casi siempre traen sexo indeterminado
        sexo = [] if tipo == "fetales" else st.multiselect("Sexo", ["Hombre", "Mujer"], key=f"{clave}_sexo", placeholder="Todos")
        dptos = st.multiselect("Departamento de residencia", sorted(dd.DEPARTAMENTOS.values()), key=f"{clave}_dpto",
                               placeholder="Todos")
    if tipo == "defunciones" and (lo <= 1980):
        st.warning("Los archivos de 1979 y 1980 están incompletos: faltan departamentos enteros en 1979 y parte de otros en "
                   "1980. Esos totales nacionales no son comparables con los de otros años.", icon=":material/warning:")
    if tipo == "defunciones" and lo <= 1991 <= hi:
        st.warning("En enero–junio de 1991 no se pueden separar las edades de los menores de 10 años: las defunciones de "
                   "menores de un año de ese año quedan vacías.", icon=":material/warning:")
    partes = [f"{TITULOS_CERTIFICADO[tipo]} {lo}–{hi}" if lo != hi else f"{TITULOS_CERTIFICADO[tipo]} {lo}"]
    for nombre, val in (("sexo", sexo), ("residencia", dptos)):
        if val:
            partes.append(f"{nombre}: {', '.join(val)}")
    return {"tipo": tipo, "anios": anios, "descripcion": " · ".join(partes),
            # en el formato de dd.eevv.serie_indicadores
            "filtros": {k: v for k, v in (("sexo", list(sexo)), ("departamento_residencia", list(dptos))) if v}}


TITULOS_CERTIFICADO = {v: k for k, v in CERTIFICADOS.items()}


# --------------------------------------------------------------------------- #
# Selector EAM (barra lateral compartida)
# --------------------------------------------------------------------------- #
def selector_eam(extra: tuple = (), clave: str = "eam"):
    av = disponibles_eam(rutas_actuales())
    if av.empty:
        sin_datos("EAM")
    with st.sidebar:
        st.header("Datos EAM")
        anios_disp = sorted(av.anio.unique())
        # Los últimos 10 años; el inicio tiene que ser un año descargado (pueden no ser consecutivos)
        inicio = next(a for a in anios_disp if a >= anios_disp[-1] - 9)
        lo, hi = st.select_slider("Años", options=anios_disp, value=(inicio, anios_disp[-1]),
                                  key=f"{clave}_rango")
        anios = [a for a in anios_disp if lo <= a <= hi]
        st.caption("CIIU Rev. 2 hasta 2000, Rev. 3 2001–2011 y Rev. 4 desde 2012 (según los archivos del DANE): "
                   "los sectores no son comparables entre revisiones.")
    df = cargar_eam(tuple(anios), tuple(sorted(extra)), rutas_actuales())
    with st.sidebar:
        st.header("Filtros")
        sectores = st.multiselect("Sector (división CIIU)", sorted(df["sector"].dropna().unique()),
                                  key=f"{clave}_sector", placeholder="Todos")
        dptos = st.multiselect("Departamento", sorted(df["departamento"].dropna().unique()),
                               key=f"{clave}_dpto", placeholder="Todos")
    if sectores:
        df = df[df["sector"].isin(sectores)]
    if dptos:
        df = df[df["departamento"].isin(dptos)]
    if df.empty:  # p. ej. un sector que no existe en los departamentos elegidos
        st.warning("Ningún establecimiento cumple los filtros elegidos.")
        st.stop()
    carga = f"eam = dd.eam.load(range({lo}, {hi + 1})" + (f", columns={sorted(extra)!r}" if extra else "") + ")"
    if sectores:
        carga += f'\neam = eam[eam["sector"].isin({sectores!r})]'
    if dptos:
        carga += f'\neam = eam[eam["departamento"].isin({dptos!r})]'
    desc = f"{lo}–{hi}" + (f" · {', '.join(sectores)}" if sectores else "") + (f" · {', '.join(dptos)}" if dptos else "")
    return df, desc, {"carga": carga, "anios": anios}
