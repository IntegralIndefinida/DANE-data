"""Piezas compartidas de la app: gráficos, caché de datos, descargas y avisos."""

from __future__ import annotations

import io
import logging
from collections import deque

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import dane_data as dd

# Paleta categórica validada (orden fijo; nunca se recicla). Ver skill dataviz.
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
COLOR_UNICO = PALETA[0]
MAX_SERIES = len(PALETA)


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


def linea(df: pd.DataFrame, x: str, y: str, color: str | None = None, titulo_y: str | None = None,
          pct: bool = False) -> go.Figure:
    fig = px.line(df, x=x, y=y, color=color, markers=True, color_discrete_sequence=PALETA)
    fig.update_traces(line=dict(width=2), marker=dict(size=8))
    fig = _estilo(fig, titulo_y, pct)
    fig.update_layout(hovermode="x unified")
    if pd.api.types.is_integer_dtype(df[x]) or x == "anio":
        fig.update_xaxes(dtick=1 if df[x].nunique() <= 15 else None, tickformat="d")
    return fig


def barras(df: pd.DataFrame, x: str, y: str, color: str | None = None, titulo_y: str | None = None,
           pct: bool = False, horizontal: bool = False) -> go.Figure:
    if horizontal:
        fig = px.bar(df, y=x, x=y, color=color, orientation="h", barmode="group",
                     color_discrete_sequence=PALETA)
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(gridcolor="rgba(128,128,128,0.18)", title=titulo_y, ticksuffix=" %" if pct else None,
                         tickformat=",~f")
        fig.update_layout(separators=",.", margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=1.02, title=None),
                          height=max(350, 24 * df[x].nunique() * (df[color].nunique() if color else 1)))
    else:
        fig = px.bar(df, x=x, y=y, color=color, barmode="group", color_discrete_sequence=PALETA)
        fig = _estilo(fig, titulo_y, pct)
    fig.update_traces(marker_line_width=0)
    fig.update_layout(bargap=0.25, bargroupgap=0.08)
    return fig


def grafico(fig: go.Figure) -> None:
    st.plotly_chart(fig, width="stretch", config={"displaylogo": False, "locale": "es"})


# --------------------------------------------------------------------------- #
# Datos (caché en memoria de la sesión del servidor)
# --------------------------------------------------------------------------- #
@st.cache_resource(max_entries=3, show_spinner=False)
def cargar_geih(anios: tuple, meses: tuple | None, extra: tuple, empalme: bool, variables: tuple | None,
                rutas: tuple) -> pd.DataFrame:
    barra = st.progress(0.0, text="Preparando datos…")
    df = dd.geih.load(list(anios), months=list(meses) if meses else None, columns=list(extra) or "core",
                      empalme=empalme, variables=list(variables) if variables else None,
                      progress=lambda f, m: barra.progress(min(f, 1.0), text=m))
    barra.empty()
    return df


@st.cache_data(max_entries=50, show_spinner=False)
def serie_geih(anios: tuple, por: str | None, anual: bool, empalme: bool, meses_disp: tuple,
               rutas: tuple) -> pd.DataFrame:
    """Indicadores precalculados; ``meses_disp`` en la llave hace que un mes recién descargado se vea."""
    barra = st.progress(0.0, text="Preparando indicadores…")
    res = dd.geih.serie_indicadores(list(anios), por=por, anual=anual, empalme=empalme,
                                    progress=lambda f, m: barra.progress(min(f, 1.0), text=m))
    barra.empty()
    return res


@st.cache_data(max_entries=50, show_spinner="Calculando indicadores…")
def indicadores_geih(_df: pd.DataFrame, clave: str, por: str | None, anual: bool) -> pd.DataFrame:
    """``indicadores`` sobre microdatos; ``clave`` (la carga y los filtros) reemplaza el hash de ``_df``."""
    return dd.geih.indicadores(_df, por=por, anual=anual)


@st.cache_resource(max_entries=2, show_spinner=False)
def cargar_eam(anios: tuple, extra: tuple, rutas: tuple) -> pd.DataFrame:
    return dd.eam.load(list(anios), columns=list(extra) or "core")


def rutas_actuales() -> tuple:
    """Parte de la llave de caché: si el usuario cambia de carpeta, se recarga."""
    return tuple(sorted(dd.show_paths().items()))


@st.cache_data(ttl=30, show_spinner=False)
def disponibles_geih(empalme: bool, rutas: tuple) -> pd.DataFrame:
    return dd.geih.available(empalme=empalme)


@st.cache_data(ttl=30, show_spinner=False)
def disponibles_eam(rutas: tuple) -> pd.DataFrame:
    return dd.eam.available()


# --------------------------------------------------------------------------- #
# Exportar
# --------------------------------------------------------------------------- #
def botones_descarga(df: pd.DataFrame, nombre: str, key: str) -> None:
    c1, c2, c3 = st.columns(3)
    c1.download_button("⬇️ CSV", df.to_csv(index=False).encode("utf-8-sig"), f"{nombre}.csv",
                       "text/csv", key=f"{key}_csv", width="stretch")
    if len(df) < 1_000_000:
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        c2.download_button("⬇️ Excel", buf.getvalue(), f"{nombre}.xlsx", key=f"{key}_xlsx", width="stretch")
    else:
        c2.caption("Excel no admite más de 1 millón de filas.")
    try:
        buf = io.BytesIO()
        d = df.copy()
        for c in d.columns:  # Stata no acepta categorías/nullable ni nombres largos
            if isinstance(d[c].dtype, pd.CategoricalDtype) or pd.api.types.is_string_dtype(d[c]):
                d[c] = d[c].astype(object).where(d[c].notna(), "").astype(str)
            elif pd.api.types.is_extension_array_dtype(d[c]):
                d[c] = d[c].astype("float64")
        d.columns = [c[:32] for c in d.columns]
        d.to_stata(buf, write_index=False, version=118)
        c3.download_button("⬇️ Stata (.dta)", buf.getvalue(), f"{nombre}.dta", key=f"{key}_dta", width="stretch")
    except Exception as e:  # noqa: BLE001
        c3.caption(f"Stata no disponible: {e}")


def codigo(texto: str) -> None:
    with st.expander("🐍 Ver el código Python equivalente"):
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


def sin_datos(encuesta: str) -> None:
    st.warning(f"No se encontraron datos de la {encuesta} en la carpeta configurada.")
    st.page_link("paginas/descargar.py", label="Ir a ⬇️ Descargar datos", icon="⬇️")
    st.page_link("paginas/inicio.py", label="o configurar la carpeta en 🏠 Inicio", icon="🏠")
    st.stop()


# --------------------------------------------------------------------------- #
# Selector GEIH (barra lateral compartida)
# --------------------------------------------------------------------------- #
AYUDA_ANIOS = "Cada año ocupa unos 70 MB de memoria, más cada variable DANE adicional."


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
    texto = ("⚠️ **Los años elegidos mezclan dos versiones de la GEIH que no son comparables.** "
             + "; ".join(partes) + ". Entre esos años la serie salta por el cambio de método, no por el mercado "
             "laboral (la población en edad de trabajar cambia ~5 %).")
    if any(2010 <= a <= 2020 for a in anios):
        texto += " Para comparar 2010–2020 sin saltos use la serie de empalme."
    st.warning(texto)


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
        anios_disp = sorted(av.anio.unique())
        defecto = anios_disp[-2:] if varios_anios else anios_disp[-1:]
        anios = st.multiselect("Años", anios_disp, default=defecto, key=f"{clave}_anios", help=ayuda_anios)
        if not anios:
            st.info("Elija al menos un año.")
            st.stop()
        meses_disp = sorted(av[av.anio.isin(anios)].mes.unique())
        todos = st.toggle("Todos los meses", True, key=f"{clave}_todos")
        meses = None
        if not todos:
            meses = st.multiselect("Meses", meses_disp, default=meses_disp[:1], format_func=dd.MESES.get,
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
    }
    aviso_marcos(seleccion["anios"], empalme)
    return seleccion


def selector_geih(extra: tuple = (), clave: str = "geih", varios_anios: bool = True,
                  variables: list | None = None, sel: dict | None = None):
    """
    Dibuja la barra lateral de la GEIH (o usa ``sel``, de ``seleccion_geih``) y
    devuelve (df_filtrado, descripcion, params).
    """
    sel = sel or seleccion_geih(clave, varios_anios)
    anios, meses, empalme = sel["anios"], sel["meses"], sel["empalme"]
    sexo, zona, edad, dptos = sel["sexo"], sel["zona"], sel["edad"], sel["dptos"]

    # Las variables de CORE_RAW se leen siempre: pedirlas en `columns` solo crearía otra caché.
    columnas = sorted(e for e in extra if e not in dd.geih.CORE_RAW)
    df = cargar_geih(tuple(anios), tuple(meses) if meses else None, tuple(columnas), empalme,
                     tuple(variables) if variables else None, rutas_actuales())
    mask = pd.Series(True, index=df.index)
    if sexo:
        mask &= df["sexo"].isin(sexo)
    if zona:
        mask &= df["zona"].isin(zona)
    if edad != (0, 100):
        mask &= df["edad"].between(*edad)
    if dptos:
        mask &= df["departamento"].isin(dptos)
    filtrado = df[mask] if not mask.all() else df

    filtros_py = []
    if sexo:
        filtros_py.append(f'df["sexo"].isin({sexo!r})')
    if zona:
        filtros_py.append(f'df["zona"].isin({zona!r})')
    if edad != (0, 100):
        filtros_py.append(f'df["edad"].between({edad[0]}, {edad[1]})')
    if dptos:
        filtros_py.append(f'df["departamento"].isin({dptos!r})')
    carga = f"df = dd.geih.load({anios!r}"
    if meses:
        carga += f", months={meses!r}"
    if columnas:
        carga += f", columns={columnas!r}"
    if empalme:
        carga += ", empalme=True"
    if variables and list(variables) == dd.geih.VARIABLES_INDICADORES:
        carga += ", variables=dd.geih.VARIABLES_INDICADORES"
    elif variables:
        carga = f"variables = {list(variables)!r}\n" + carga + ", variables=variables"
    carga += ")"
    if filtros_py:
        carga += "\ndf = df[" + " & ".join(f"({f})" for f in filtros_py) + "]"
    return filtrado, sel["descripcion"], {"carga": carga, "anios": anios, "meses": meses}


# --------------------------------------------------------------------------- #
# Selector EAM (barra lateral compartida)
# --------------------------------------------------------------------------- #
def selector_eam(extra: tuple = (), clave: str = "eam"):
    with st.sidebar:
        st.header("Datos EAM")
        av = disponibles_eam(rutas_actuales())
        if av.empty:
            sin_datos("EAM")
        anios_disp = sorted(av.anio.unique())
        lo, hi = st.select_slider("Años", options=anios_disp,
                                  value=(max(anios_disp[0], anios_disp[-1] - 10), anios_disp[-1]), key=f"{clave}_rango")
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
    carga = f"eam = dd.eam.load(range({lo}, {hi + 1})" + (f", columns={sorted(extra)!r}" if extra else "") + ")"
    if sectores:
        carga += f'\neam = eam[eam["sector"].isin({sectores!r})]'
    if dptos:
        carga += f'\neam = eam[eam["departamento"].isin({dptos!r})]'
    desc = f"{lo}–{hi}" + (f" · {', '.join(sectores)}" if sectores else "") + (f" · {', '.join(dptos)}" if dptos else "")
    return df, desc, {"carga": carga, "anios": anios}
