"""
Índice de Pobreza Multidimensional (IPM) del DANE con la ECV.

Metodología de Alkire y Foster adaptada por el DNP: 15 privaciones en 5 dimensiones de igual peso
(y las privaciones de cada dimensión también de igual peso). Un hogar es pobre si su puntaje (la
suma ponderada de sus privaciones) es de 5/15 o más, y todas sus personas lo son. Las definiciones
siguen el *Algoritmo para la construcción del IPM* del DANE, ajustadas para reproducir la base
oficial del IPM (``BDATOS-IPM``) hogar por hogar (exacta en 2018, 2019 y 2023–2025; en 2020–2022
difieren 5, 25 y 3 de unos 89.000 hogares); donde el algoritmo no dice todo, el comentario lo
indica.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from ..stats import _avisar, _con_categorias
from .indicadores import _lista
from .loader import KEYS_HOGAR

# Privación -> (dimensión, peso)
PRIVACIONES = {
    "logro_educativo": ("Condiciones educativas del hogar", 0.1),
    "analfabetismo": ("Condiciones educativas del hogar", 0.1),
    "inasistencia_escolar": ("Condiciones de la niñez y la juventud", 0.05),
    "rezago_escolar": ("Condiciones de la niñez y la juventud", 0.05),
    "atencion_integral": ("Condiciones de la niñez y la juventud", 0.05),
    "trabajo_infantil": ("Condiciones de la niñez y la juventud", 0.05),
    "desempleo_larga_duracion": ("Trabajo", 0.1),
    "empleo_formal": ("Trabajo", 0.1),
    "aseguramiento_salud": ("Salud", 0.1),
    "barreras_acceso_salud": ("Salud", 0.1),
    "acueducto": ("Acceso a servicios públicos domiciliarios y condiciones de la vivienda", 0.04),
    "alcantarillado": (
        "Acceso a servicios públicos domiciliarios y condiciones de la vivienda",
        0.04,
    ),
    "pisos": ("Acceso a servicios públicos domiciliarios y condiciones de la vivienda", 0.04),
    "paredes": ("Acceso a servicios públicos domiciliarios y condiciones de la vivienda", 0.04),
    "hacinamiento": (
        "Acceso a servicios públicos domiciliarios y condiciones de la vivienda",
        0.04,
    ),
}
UMBRAL = 5 / 15
# Capítulos y variables del DANE que necesita el IPM
MODULOS_IPM = (
    "vivienda",
    "servicios",
    "condiciones",
    "salud",
    "primera_infancia",
    "educacion",
    "fuerza_trabajo",
)
# fmt: off
COLUMNAS_IPM = ("P4005", "P4015", "P8520S3", "P8520S5", "P5010", "P8526", "P8530", "P1075",
                "P6090", "P5665", "P8563", "P51", "P55", "P774", "P6160", "P8586", "P8587",
                "P8587S1", "P1088", "P1088S1", "P6180", "P3336S1", "P3336S2", "P3336S3", "P3337",
                "P6240", "P6250", "P6260", "P6270", "P6351", "P7250", "P6920", "P1077S21",
                "P1077S22", "P1077S23", "ESTRATEGIAS", "EST_PLATAFORMAS", "EST_GUIAS",
                "EST_LLAMADA", "EST_VISITA", "CELULAR_INTELIGENTE", "CELULAR", "P5305")
# fmt: on
# Las de la asistencia virtual (desde 2021) y las de la base complementaria de 2020 no están en
# todos los años
# fmt: off
_DE_ALGUNOS_ANIOS = ("P1075", "P3336S1", "P3336S2", "P3336S3", "P3337", "P1077S21", "P1077S22",
                     "P1077S23", "ESTRATEGIAS", "EST_PLATAFORMAS", "EST_GUIAS", "EST_LLAMADA",
                     "EST_VISITA", "CELULAR_INTELIGENTE", "CELULAR", "P5305")
# fmt: on
_NECESARIAS = tuple(c for c in COLUMNAS_IPM if c not in _DE_ALGUNOS_ANIOS)
# El DANE calcula las cifras nacionales y por área sin la parte rural de estos departamentos (las
# regionales y las departamentales, con toda la muestra)
_SIN_RURAL_EN_LO_NACIONAL = (
    "Arauca",
    "Casanare",
    "Putumayo",
    "Amazonas",
    "Guainía",
    "Guaviare",
    "Vaupés",
    "Vichada",
)
_RURAL = "Centros poblados y rural disperso"
# Las 6 regiones de los anexos del IPM, que no son las 9 de la ECV: la parte rural de Bogotá va en
# Oriental y San Andrés no tiene región
_REGIONES_IPM = {
    "Caribe": ("Atlántico", "Bolívar", "Cesar", "Córdoba", "La Guajira", "Magdalena", "Sucre"),
    "Oriental": ("Boyacá", "Cundinamarca", "Meta", "Norte de Santander", "Santander"),
    "Central": ("Antioquia", "Caldas", "Caquetá", "Huila", "Quindío", "Risaralda", "Tolima"),
    "Pacífica": ("Cauca", "Chocó", "Nariño", "Valle del Cauca"),
    "Orinoquía-Amazonía": _SIN_RURAL_EN_LO_NACIONAL,
}
_REGION_IPM = {d: r for r, dptos in _REGIONES_IPM.items() for d in dptos}
REGIONES_IPM = pd.CategoricalDtype([*_REGIONES_IPM, "Bogotá (cabecera)"])
MUESTRAS = ("nacional", "completa")


def _anios_ipm(num, estudia: pd.Series) -> pd.Series:
    """
    Años de educación del IPM, que no son los del Cuadro 18 de la ECV: la media se cuenta hasta 11
    y la superior desde 11 (desde 16 en posgrado) más el año aprobado (P8587S1) o, si estudia, el
    que cursa menos uno (P1088S1). Así da la base oficial del DANE hogar por hogar.
    """
    nivel, grado = num("P8587"), num("P8587S1")
    no_estudia = np.select(
        [nivel.isin([1, 2]), nivel.between(3, 4), nivel.eq(5), nivel >= 6],
        [0, grado, np.minimum(grado, 11), np.where(nivel >= 12, 16, 11) + grado.fillna(0)],
        np.nan,
    )
    matricula, cursa = num("P1088"), num("P1088S1")
    estudiante = np.select(
        [matricula.eq(1), matricula.between(2, 4), matricula >= 5],
        [0, np.minimum(cursa - 1, 11), np.where(matricula >= 8, 16, 11) + cursa - 1],
        np.nan,
    )
    return pd.Series(
        np.where(estudia, estudiante, no_estudia), index=estudia.index, dtype="float64"
    )


def privaciones(df: pd.DataFrame) -> pd.DataFrame:
    """
    Las 15 privaciones del IPM de cada hogar, su puntaje y si es pobre.

    Parámetros
    ----------
    df
        Personas de :func:`load` con los capítulos del IPM: ``load(años,
        modulos=dd.ecv.MODULOS_IPM)`` (con ``columnas=dd.ecv.COLUMNAS_IPM`` basta).

    Devuelve
    --------
    DataFrame
        Una fila por hogar: ``anio``, ``DIRECTORIO``, ``SECUENCIA_P``, ``fex``, ``personas``,
        ``area``, ``region`` (la de la ECV), ``region_ipm`` (las 6 de los anexos del IPM: Caribe,
        Oriental, Central, Pacífica, Orinoquía-Amazonía y Bogotá (cabecera); la parte rural de
        Bogotá es Oriental y San Andrés queda vacía), ``departamento``, ``sexo_jefe``, una columna
        0/1 por privación (``dd.ecv.PRIVACIONES``), ``puntaje`` (la suma ponderada, de 0 a 1) y
        ``pobre`` (puntaje de 5/15 o más).

    Lanza
    -----
    ValueError
        Si faltan variables del DANE que necesita el IPM.

    Véase también
    -------------
    ipm : Incidencia, intensidad e IPM por grupo.

    Notas
    -----
    En 2020, con los colegios cerrados, el DANE armó la inasistencia escolar con la base
    complementaria del IPM 2020 (estrategias de estudio en casa, con información del SIMAT), que
    ``download`` baja con 2020 y ``load`` une: un niño que estudia cuenta como inasistente si no
    recibió estrategias y el hogar no tiene internet y un equipo, o si las recibió, pero no por
    plataformas con internet y un equipo ni por guías con llamadas (y teléfono) o visitas. Sin esa
    base, la incidencia de 2020 sale 14,8 % y no 18,1 %, y se avisa.

    Lo que no dice el algoritmo publicado y se ajustó a la base oficial: los años de educación (vea
    ``_anios_ipm``); el desempleo de larga duración es de 52 semanas o más; un hogar sin personas
    de 15 años y más se priva por logro educativo y por analfabetismo; un niño de 5 años que
    estudia y no tiene el dato de alimentación en el colegio no se priva; desde 2021, un niño que
    estudia solo de forma virtual cuenta como inasistente si el hogar no tiene internet o él no
    tuvo contacto con sus maestros la semana pasada. Las paredes de guadua, caña y otro vegetal son
    el código 7 en 2018–2019 y los códigos 7 y 8 desde 2020; el DANE siguió con los códigos viejos
    en 2020, así que ese año «sin paredes» (el código 10) no se priva.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> personas = dd.ecv.load(
    ...     2025, modulos=dd.ecv.MODULOS_IPM, columnas=dd.ecv.COLUMNAS_IPM
    ... )  # doctest: +SKIP
    >>> hogares = dd.ecv.privaciones(personas)  # doctest: +SKIP
    """
    faltan = [
        c
        for c in ("anio", "fex", "edad", "area", "parentesco", *KEYS_HOGAR, *_NECESARIAS)
        if c not in df.columns
    ]
    if faltan:
        raise ValueError(
            f"Faltan variables para el IPM: {faltan}. Cargue los datos con dd.ecv.load(años, "
            "modulos=dd.ecv.MODULOS_IPM)."
        )
    if df["anio"].eq(2020).any() and (
        "ESTRATEGIAS" not in df or df.loc[df["anio"].eq(2020), "ESTRATEGIAS"].isna().all()
    ):
        _avisar(
            "IPM 2020 sin la base complementaria del DANE (estrategias de estudio en casa): la "
            "inasistencia escolar y la incidencia salen más bajas que las publicadas. Bájela con "
            "dd.ecv.download(2020).",
            UserWarning,
        )

    def num(columna: str) -> pd.Series:
        if columna not in df.columns:
            return pd.Series(np.nan, index=df.index)
        return pd.to_numeric(df[columna], errors="coerce")

    hogar = [df["anio"], df["DIRECTORIO"], df["SECUENCIA_P"]]

    def alguno(mascara: pd.Series) -> pd.Series:
        return mascara.fillna(False).astype(bool).groupby(hogar).any()

    def cuantos(mascara: pd.Series) -> pd.Series:
        return mascara.fillna(False).astype(bool).groupby(hogar).sum()

    edad = df["edad"].astype("float64")
    estudia = num("P8586").eq(1)
    anios = _anios_ipm(num, estudia)
    mayor = edad >= 15
    sin_mayores = ~alguno(mayor)
    p = pd.DataFrame(index=edad.groupby(hogar).size().index)
    p["personas"] = edad.groupby(hogar).size()

    # Condiciones educativas: el promedio de los de 15 años y más, y si alguno no sabe leer y
    # escribir
    p["logro_educativo"] = (anios.where(mayor).groupby(hogar).mean() < 9) | sin_mayores
    p["analfabetismo"] = alguno(mayor & num("P6160").eq(2)) | sin_mayores
    # Niñez y juventud
    virtual = num("P3336S1").eq(2) & num("P3336S2").eq(1) & num("P3336S3").eq(2)
    sin_clase = virtual & (num("P1075").eq(2) | num("P3337").eq(2))
    # 2020, con la base complementaria: estudiar en casa cuenta si hubo plataformas con internet y
    # un equipo, o guías con llamadas (y teléfono) o visitas del colegio; sin estrategias, si el
    # hogar tiene internet y un equipo
    equipo = (
        num("P1077S21").eq(1)
        | num("P1077S22").eq(1)
        | num("P1077S23").eq(1)
        | num("CELULAR_INTELIGENTE").eq(1)
    )
    conectado = num("P1075").eq(1) & equipo
    telefono = num("CELULAR").eq(1) | num("P5305").eq(1)
    atendido = (num("EST_PLATAFORMAS").eq(1) & conectado) | (
        num("EST_GUIAS").eq(1) & ((num("EST_LLAMADA").eq(1) & telefono) | num("EST_VISITA").eq(1))
    )
    en_casa = (num("ESTRATEGIAS").eq(2) & ~conectado) | (num("ESTRATEGIAS").eq(1) & ~atendido)
    sin_clase = sin_clase | (df["anio"].eq(2020) & en_casa)
    p["inasistencia_escolar"] = alguno(edad.between(6, 16) & (num("P8586").eq(2) | sin_clase))
    p["rezago_escolar"] = alguno(edad.between(7, 17) & (anios < edad - 6))
    asegurado = num("P6090").eq(1)  # «no sabe» es no asegurado
    # Gratis o pago simbólico
    jardin_sin_comida = num("P51").eq(1) & ~(num("P55").eq(1) & num("P774").isin([2, 3]))
    menor_de_5 = edad.between(0, 4) & (~asegurado | num("P51").isin([3, 6, 7]) | jardin_sin_comida)
    de_5 = edad.eq(5) & (~asegurado | num("P8586").eq(2) | (estudia & num("P6180").eq(2)))
    p["atencion_integral"] = alguno(menor_de_5 | de_5)
    ocupado = num("P6240").eq(1) | num("P6250").eq(1) | num("P6260").eq(1) | num("P6270").eq(1)
    p["trabajo_infantil"] = alguno(edad.between(12, 17) & ocupado)
    # Trabajo
    pet = edad >= 12
    desocupado = pet & ~ocupado & num("P6351").eq(1)
    pea = pet & (ocupado | desocupado)
    larga = desocupado & (num("P7250") >= 52)
    pensionado = num("P6920").eq(3)
    solo_pensionados = cuantos(pensionado) == p["personas"]
    p["desempleo_larga_duracion"] = alguno(larga) | (cuantos(pea) == 0) | solo_pensionados
    # Sin los ya contados en trabajo infantil y desempleo
    pea_formal = pea & ~(ocupado & (edad < 18)) & ~larga
    formales = cuantos(pea_formal & ocupado & (num("P6920").eq(1) | pensionado))
    p["empleo_formal"] = (
        (formales != cuantos(pea_formal)) | (cuantos(pea_formal) == 0)
    ) & ~solo_pensionados
    # Salud
    p["aseguramiento_salud"] = alguno((edad > 5) & ~asegurado)
    # No acudió a la entidad o a un médico
    p["barreras_acceso_salud"] = alguno(num("P5665").eq(1) & ~num("P8563").isin([1, 2]))

    # Vivienda y servicios, y lo que describe al hogar: del jefe
    jefe = df["parentesco"].eq("Jefe(a) del hogar").fillna(False).astype(bool)
    j = df[jefe].set_index(["anio", *KEYS_HOGAR]).reindex(p.index)
    jn = lambda c: pd.to_numeric(j[c], errors="coerce")  # noqa: E731
    rural = j["area"].eq(_RURAL).fillna(False).astype(bool)
    p["acueducto"] = np.where(rural, jn("P8530").isin([4, 5, 6, 8, 9, 10]), ~jn("P8520S5").eq(1))
    p["alcantarillado"] = np.where(rural, jn("P8526").isin([3, 5, 6]), ~jn("P8520S3").eq(1))
    p["pisos"] = jn("P4015").eq(7)
    # Códigos de 2020 en adelante, pero el DANE siguió con los de 2018–2019 en 2020: «sin paredes»
    # (10) no se priva
    recientes = j.index.get_level_values("anio") >= 2021
    vegetal_y_desechos = np.where(
        recientes, jn("P4005").isin([7, 8, 9, 10]), jn("P4005").isin([7, 8, 9])
    )
    # Madera burda: privación solo urbana
    p["paredes"] = vegetal_y_desechos | (~rural & jn("P4005").eq(5))
    por_cuarto = p["personas"] / jn("P5010").where(lambda v: v > 0)
    p["hacinamiento"] = np.where(rural, por_cuarto > 3, por_cuarto >= 3)

    for nombre in PRIVACIONES:
        p[nombre] = p[nombre].fillna(False).astype(bool).astype("int8")
    p["puntaje"] = sum(p[nombre] * peso for nombre, (_, peso) in PRIVACIONES.items())
    p["pobre"] = p["puntaje"] >= UMBRAL - 1e-9
    departamento = (
        j["departamento"].astype("object")
        if "departamento" in j
        else pd.Series(np.nan, index=j.index)
    )
    region_ipm = departamento.map(_REGION_IPM).mask(
        departamento.eq("Bogotá D.C."), np.where(rural, "Oriental", "Bogotá (cabecera)")
    )
    describe = pd.DataFrame(
        {
            "fex": j["fex"],
            "area": j["area"],
            "region": j.get("region"),
            "region_ipm": region_ipm.astype(REGIONES_IPM),
            "departamento": j.get("departamento"),
            "sexo_jefe": j.get("sexo"),
        },
        index=p.index,
    )
    # fmt: off
    columnas = ["anio", *KEYS_HOGAR, "fex", "personas", "area", "region", "region_ipm",
                "departamento", "sexo_jefe", *PRIVACIONES, "puntaje", "pobre"]
    # fmt: on
    return pd.concat([describe, p], axis=1).reset_index()[columnas]


def _muestra_nacional(hogares: pd.DataFrame) -> pd.Series:
    return ~(
        hogares["departamento"].isin(_SIN_RURAL_EN_LO_NACIONAL) & hogares["area"].eq(_RURAL)
    ).fillna(False).astype(bool)


def ipm(
    df: pd.DataFrame,
    por: str | Iterable[str] | None = None,
    muestra: str | None = None,
    dropna: bool = True,
) -> pd.DataFrame:
    """
    Incidencia, intensidad e IPM por grupo, como los publica el DANE.

    Parámetros
    ----------
    df
        Personas con los capítulos del IPM (vea :func:`privaciones`), o lo que devuelve
        :func:`privaciones`.
    por
        Columna o lista de columnas de :func:`privaciones` para agrupar: ``"anio"``, ``"area"``,
        ``"region_ipm"`` (las regiones de los anexos del DANE), ``"region"`` (las de la ECV),
        ``"departamento"``, ``"sexo_jefe"``. ``None`` da una sola fila.
    muestra
        ``"nacional"``: sin la parte rural de Arauca, Casanare, Putumayo, Amazonas, Guainía,
        Guaviare, Vaupés y Vichada, como el DANE para las cifras nacionales y por área.
        ``"completa"``: todos los hogares, como el DANE para las regionales y las departamentales.
        Por defecto, la completa si se agrupa por ``departamento``, ``region_ipm`` o ``region``, y
        la nacional si no.
    dropna
        Quitar los hogares sin dato en ``por``.

    Devuelve
    --------
    DataFrame
        Una fila por grupo: ``personas``, ``personas_pobres``, ``incidencia`` (H, % de personas
        pobres), ``intensidad`` (A, % promedio de privaciones de los pobres) e ``ipm`` (H × A, de 0
        a 1), sobre las personas; ``hogares`` y ``pct_<privación>`` (% de hogares con esa
        privación, como los anexos del DANE), sobre los hogares. Todo se expande con ``fex``.

    Lanza
    -----
    ValueError
        Si ``muestra`` no es una de las dos, o si faltan variables (vea :func:`privaciones`).

    Véase también
    -------------
    serie_ipm : Lo mismo, año por año y con caché.

    Ejemplos
    --------
    >>> import dane_data as dd
    >>> personas = dd.ecv.load(
    ...     2025, modulos=dd.ecv.MODULOS_IPM, columnas=dd.ecv.COLUMNAS_IPM
    ... )  # doctest: +SKIP
    >>> dd.ecv.ipm(personas)[["incidencia", "intensidad", "ipm"]].round(3)  # doctest: +SKIP
       incidencia  intensidad    ipm
    0       9.912      40.379  0.040
    """
    llaves = _lista(por)
    automatica = muestra is None
    if automatica:
        muestra = (
            "completa" if {"departamento", "region_ipm", "region"} & set(llaves) else "nacional"
        )
    if muestra not in MUESTRAS:
        raise ValueError(f"Muestra desconocida {muestra!r}. Opciones: {list(MUESTRAS)}")
    hogares = df if "puntaje" in df.columns else privaciones(df)
    if muestra == "nacional":
        nacional = _muestra_nacional(hogares)
        if (
            automatica and len(hogares) and (~nacional).mean() > 0.5
        ):  # p. ej. solo hogares de Arauca: casi todo es rural
            _avisar(
                f"La muestra nacional deja fuera {(~nacional).sum()} de {len(hogares)} hogares "
                "(la parte rural de los departamentos de la Orinoquía-Amazonía). Para un solo "
                "departamento "
                'use por="departamento" '
                'o muestra="completa".',
                UserWarning,
            )
        hogares = hogares[nacional]
    if llaves and dropna:
        hogares = hogares.dropna(subset=llaves)
    grupos = [hogares[k] for k in llaves] if llaves else [pd.Series(0, index=hogares.index)]
    peso = hogares["fex"].astype("float64") * hogares["personas"]  # cada persona del hogar

    def suma(valores) -> pd.Series:
        return (peso * valores).groupby(grupos, observed=True, dropna=False, sort=True).sum()

    personas = suma(1.0)
    pobres = suma(hogares["pobre"].astype("float64"))
    res = pd.DataFrame({"personas": personas, "personas_pobres": pobres})
    res["incidencia"] = 100 * pobres / personas.where(lambda v: v > 0)
    res["intensidad"] = (
        100 * suma(hogares["puntaje"].where(hogares["pobre"], 0)) / pobres.where(lambda v: v > 0)
    )
    res["ipm"] = res["incidencia"] * res["intensidad"] / 1e4
    # Las privaciones, como en los anexos del DANE, son % de hogares: sin multiplicar por las
    # personas
    fex = hogares["fex"].astype("float64")

    def por_hogar(valores):
        return (fex * valores).groupby(grupos, observed=True, dropna=False, sort=True).sum()

    res["hogares"] = por_hogar(1.0)
    for nombre in PRIVACIONES:
        res[f"pct_{nombre}"] = (
            100
            * por_hogar(hogares[nombre].astype("float64"))
            / res["hogares"].where(lambda v: v > 0)
        )
    if llaves:
        res.index.names = llaves
        return _con_categorias(res.reset_index(), hogares, llaves)
    return res.reset_index(drop=True)
