# DANE-data

[Documentación](https://integralindefinida.github.io/DANE-data/) · [PyPI](https://pypi.org/project/dane-data/)

Microdatos del DANE listos para analizar: la Gran Encuesta Integrada de Hogares (GEIH, 2007–2026), la
Encuesta Anual Manufacturera (EAM, 1992–2024), las Estadísticas Vitales (nacimientos y defunciones, 1979–2025), la
Encuesta de Micronegocios (EMICRON, 2019–2025), la Encuesta Nacional de Calidad de Vida (ECV, 2018–2025), con el Índice
de Pobreza Multidimensional, y la Medición de Pobreza Monetaria y Desigualdad (2012–2025).

[![Tasa de desocupación mensual y promedio de 12 meses, total nacional, 2007–2026, calculada con dane-data](https://raw.githubusercontent.com/IntegralIndefinida/DANE-data/main/docs/_static/galeria/desempleo.png)](https://integralindefinida.github.io/DANE-data/ejemplos/desempleo.html)

*La tasa de desocupación de cada mes desde 2007, calculada con dane-data a partir de los microdatos de la GEIH
([ejemplo completo](https://integralindefinida.github.io/DANE-data/ejemplos/desempleo.html)).*

Dos formas de usarlo:

| | Para quién | Cómo |
|---|---|---|
| Aplicación | Estudiantes que empiezan, clases, consultas rápidas | `dane-data app`, que se abre en el navegador |
| Librería de Python | Automatización, investigación, estudiantes avanzados | `import dane_data as dd` |

Ambas usan el mismo motor: descargan del ANDA del DANE, unen los módulos, armonizan las variables
entre épocas (nombres, separadores, coma decimal, factores de expansión, revisiones CIIU) y calculan
indicadores ponderados como lo hace el DANE.

## Instalación de la app

1. Descargue [dane-data.zip](https://github.com/IntegralIndefinida/DANE-data/releases/latest/download/dane-data.zip) (siempre la última versión).
2. Descomprímalo (en Windows: clic derecho → *Extraer todo…*; abrirlo con doble clic no basta) en una
   carpeta fuera de OneDrive, por ejemplo `C:\dane-data`: la primera vez se crean miles de archivos
   (`.venv/`) que OneDrive se pondría a sincronizar.
3. Haga doble clic en el lanzador de su sistema:

   | Sistema | Archivo |
   |---|---|
   | Windows | `Abrir dane-data.exe` (o `Abrir dane-data (Windows).bat`, que hace lo mismo) |
   | Mac | `Abrir dane-data (Mac).command` |
   | Linux | `abrir-dane-data.sh` |

La primera vez necesita internet y tarda 1–3 minutos: el lanzador instala [uv](https://docs.astral.sh/uv/),
que descarga Python 3.12 y las librerías exactas de `uv.lock` dentro de la carpeta (`.venv/`), sin tocar el
resto del sistema. Las siguientes veces abre en segundos. El navegador se abre solo; para cerrar la
app basta cerrar la ventana de la terminal.

> Primera vez en **Windows**: si aparece "Windows protegió su PC", haga clic en *Más información* → *Ejecutar de
> todas formas*. En **Mac**: si dice que no se puede verificar el desarrollador, cierre el aviso y abra
> *Configuración del Sistema* → *Privacidad y seguridad* → *Abrir de todos modos* (hasta macOS 14 bastaba
> con clic derecho → *Abrir* → *Abrir*).

## Instalación con pip

```bash
pip install "dane-data[app]"   # librería + aplicación
pip install dane-data          # solo la librería
dane-data app
```

## Instalación para desarrollo

```bash
git clone https://github.com/IntegralIndefinida/DANE-data
cd DANE-data
pip install -e ".[app]"        # librería + aplicación
# pip install -e .             # solo la librería
# o con uv:  uv run --extra app dane-data app
```

Requiere Python ≥ 3.10.

## La aplicación

```bash
dane-data app          # o doble clic en el lanzador; el navegador se abre solo
```

| Página | Qué hace |
|---|---|
| Inicio | Explica las encuestas, muestra qué datos hay y configura las carpetas |
| Descargar datos | Elige encuesta y años y descarga |
| Indicadores laborales | TD, TGP, TO, informalidad e ingresos, por sexo, edad, zona, educación o departamento; anual o mensual |
| Tablas y microdatos | Tablas ponderadas a la medida, distribución de ingresos frente al salario mínimo, exportación |
| Indicadores industriales | Producción, valor agregado, empleo, productividad y participación laboral por sector o departamento |
| Panel y microdatos EAM | Panel de establecimientos (balanceado o no), supervivencia, exportación |
| Pobreza monetaria | Incidencia, brecha y severidad de la pobreza y la pobreza extrema, Gini e ingreso per cápita, con la serie empalmada 2012–2025 |
| Nacimientos y defunciones | Indicadores de los tres certificados, tasas sobre la población y causas de muerte |
| Micronegocios | Indicadores de la EMICRON: ventas, valor agregado, empleo y registros, por ciudad o zona, sexo del propietario, actividad o sitio del negocio |
| Calidad de vida y pobreza | Indicadores de la ECV (servicios, internet, salud, educación, TIC) y el Índice de Pobreza Multidimensional, por área, región, departamento o sexo del jefe |
| Diccionario | Buscador de variables con las etiquetas y categorías oficiales del DANE |
| Cómo citar | La cita de dane-data y de los datos del DANE, en APA y BibTeX |

Cada tabla se descarga en CSV, Excel o Stata, y cada página muestra el código Python equivalente, que se
puede copiar a un notebook para seguir desde ahí.

Para usarla en un aula (el profesor la sirve y los estudiantes entran desde la red local):
`dane-data app --address 0.0.0.0`. La aplicación no tiene usuarios ni contraseña: cualquiera en esa red
puede cambiar las carpetas de datos, descargar y exportar en el computador del profesor. Úsela solo en
una red de confianza.

## La librería

```python
import dane_data as dd

# 1. ¿Dónde están (o estarán) los datos?  Se recuerda para siempre.
dd.set_paths(geih="~/datos/GEIH/data", eam="~/datos/EAM/data", guardar=True)

# 2. Descargar (incremental: lo ya bajado se salta)
dd.geih.download([2024, 2025])
dd.eam.download(range(2014, 2025))

# 3. Cargar: una persona por fila, módulos ya unidos y variables armonizadas
df = dd.geih.load(2025)                                  # todos los meses
df = dd.geih.load([2024, 2025], meses=[1, 2, 3])         # primer trimestre
df = dd.geih.load(2025, columnas=["P6500", "P7070"])     # + variables DANE extra
df = dd.geih.load(2016, empalme=True)                    # serie de empalme (marco 2018)
pocas = dd.geih.load(range(2015, 2026), variables=["fex", "sexo", "ocupado"])  # solo esas columnas

# 4. Indicadores laborales ponderados
dd.geih.indicadores(df)                                  # TGP, TO, TD, informalidad, ingresos…
dd.geih.indicadores(df, por=["sexo", "zona"])
dd.geih.indicadores(df, por="grupo_edad", anual=False)   # mensual
dd.geih.serie_indicadores(range(2007, 2027), por="sexo")  # precalculado por año, sin cargar microdatos
dd.geih.serie_indicadores(range(2015, 2027), filtros={"edad": (15, 28)})   # jóvenes

# 5. Tablas ponderadas de cualquier cosa
dd.tabla(df, por=["anio", "nivel_educativo"], estadistico="porcentaje")
dd.tabla(df[df.ocupado == 1], por="departamento", variable="ingreso_laboral", estadistico="mediana")
# lo mismo, año por año y guardado en caché (sirve para muchos años sin cargarlos en memoria)
dd.geih.serie_tabla(range(2007, 2027), por="departamento", variable="ingreso_laboral", estadistico="mediana",
                    poblacion="ocupado", filtros={"sexo": ["Mujer"]})
dd.geih.exportar(range(2015, 2026), "ocupados.csv", poblacion="ocupado")  # CSV armonizado, mes a mes

# 6. EAM
eam = dd.eam.load(range(2012, 2025))                     # un establecimiento-año por fila
dd.eam.resumen(eam, por=["anio", "sector"])              # VA, empleo, productividad, participación laboral
panel = dd.eam.panel(eam, balanceado=True)               # índice (nordest, anio)
dd.eam.supervivencia(eam)                                # % de plantas que reaparecen cada año
dd.eam.deflactar(eam, ["valagri"], ipp_por_anio)         # a precios constantes

# 7. Estadísticas Vitales: certificados de nacimiento y de defunción
dd.eevv.download(2025)
nac = dd.eevv.load(2025, tipo="nacimientos")             # un certificado por fila
dd.eevv.indicadores(nac, por="edad_madre")               # bajo peso, prematuros, cesáreas…
dd.eevv.tasas(range(2015, 2026), por="departamento")     # natalidad, mortalidad, fecundidad, mortalidad infantil
dd.poblacion(2025, sexo="Mujer", edades=(15, 49))        # las proyecciones del DANE, sin descargar nada

# 8. EMICRON: micronegocios (hasta 9 personas ocupadas)
dd.emicron.download(2024)
emi = dd.emicron.load(range(2019, 2025))                # un micronegocio por fila, módulos ya unidos
dd.emicron.indicadores(emi, por=["anio", "clase"])      # el cuadro I.1 del DANE: ventas, valor agregado, RUT…
dd.tabla(emi, por=["anio", "sitio"], estadistico="porcentaje")

# 9. ECV e Índice de Pobreza Multidimensional
dd.ecv.download(2025)                                    # los once capítulos del cuestionario
df = dd.ecv.load(2025, modulos=["salud", "educacion"])   # una persona por fila, capítulos unidos
dd.ecv.serie_indicadores(range(2018, 2026), por="area")  # servicios, internet, salud, educación… como el DANE
dd.ecv.serie_ipm(range(2018, 2026), por="departamento")  # incidencia, intensidad, IPM y las 15 privaciones

# 10. Pobreza monetaria: la serie empalmada 2012–2025 del DANE
dd.pobreza.download(empalme=True)
dd.pobreza.serie_indicadores(range(2012, 2026), empalme=True)   # incidencia, brecha, severidad, Gini
hog = dd.pobreza.load(2025)                              # un hogar por fila: ingreso per cápita, líneas, pobre
dd.pobreza.indicadores(hog, por="departamento", departamental=True)
per = dd.pobreza.unir_geih(dd.geih.load(2025))           # la pobreza del hogar en cada persona de la GEIH

# 11. Diccionario oficial
dd.buscar_variable("pensión")
dd.describir("P6920")
```

También en terminal:

```bash
dane-data estado                               # rutas y años/meses disponibles
dane-data descargar geih --anios 2024 2025
dane-data descargar geih --anios 2016 --empalme
dane-data descargar eam --anios 2022 2023 2024
dane-data descargar emicron --anios 2023 2024
dane-data descargar ecv --anios 2025 --modulos caracteristicas salud
dane-data config --geih RUTA --empalme RUTA --eam RUTA --ecv RUTA
```

Vea [Primeros pasos](https://integralindefinida.github.io/DANE-data/primeros_pasos.html) para un recorrido completo,
con los resultados de cada paso.

### Variables armonizadas

Las variables en minúscula las crea `dane-data` y significan lo mismo en todos los años. Las de
MAYÚSCULA (GEIH) son las originales del DANE.

**GEIH**: `anio`, `mes`, `fex`, `sexo`, `edad`, `grupo_edad`, `dpto`, `departamento`, `zona`,
`condicion` (Ocupado / Desocupado / Inactivo / Fuera de la PET), `pet`, `fuerza_trabajo`, `ocupado`,
`desocupado`, `inactivo`, `formal`, `formal_marco2005`, `cotiza_pension`, `ingreso_laboral`, `smlv`, `ratio_smlv`,
`horas_semana`, `posicion_ocupacional`, `rama2d`, `rama_rev`, `nivel_educativo`, `jefe_hogar`,
`ingreso_no_laboral`, `lugar_nacimiento`, `residencia_hace_12_meses`, `residencia_hace_5_anios`.

**EAM**: todas las columnas en minúscula, más `anio`, `ciiu`, `ciiu_rev`, `division`, `sector`,
`departamento`, `microagregado`, `grupo_microagregacion`.

**Estadísticas Vitales**: en todos, `anio`, `mes`, `sexo`, `departamento_ocurrencia`, `departamento_residencia`, sus códigos,
`mpio_ocurrencia`, `mpio_residencia`, `area_ocurrencia`, `area_residencia` y `regimen_salud`. En defunciones, además,
`grupo_edad`, `grupo_edad_amplio`, `menor_un_anio`, `neonatal`, `neonatal_precoz`, `causa_cie`, `cie_rev`, `causa_105`, `causa_667`, `gran_causa`,
`manera_muerte`, `materna`, `materna_tardia`, `sitio`, `estado_civil`, `nivel_educativo` y `etnia`. En nacimientos, `edad_madre`,
`madre_adolescente`, `peso_grupo`, `bajo_peso`, `gestacion_grupo`, `prematuro`, `cesarea`, `parto_multiple`, `consultas` y otras. En fetales, las de la madre y las causas, más `mortinato`.

**EMICRON**: la clave del propietario en la GEIH (`directorio`, `secuencia_p`, `secuencia_encuesta`), `anio`, `mes_ref`,
`fex`, `fex_dpto`, `departamento`, `ciudad`, `clase`, `sexo`, `edad`, `situacion_empleo`, `actividad`, `actividad12`,
`trabajadores_remunerados`, `socios`, `familiares_sin_remuneracion`, `personal_ocupado`, `rut`, `camara_comercio`,
`salud_pension`, `sitio` y los montos mensuales del DANE (`ventas_mes_anterior`, `consumo_intermedio`, `valor_agregado`,
`ingreso_mixto`, `sueldos`, `prestaciones`, `remuneracion_total`).

### Lo que `dane-data` resuelve por usted

| Problema en los archivos del DANE | Solución |
|---|---|
| 2007–2021: cada módulo partido en Área / Cabecera / Resto | Nacional = Cabecera + Resto (Área es un subconjunto de Cabecera) |
| Separadores `;` `,` `\t`, UTF-8 / Latin-1, coma decimal, blancos `" "` | Detección automática; columnas numéricas quedan numéricas |
| Factor de expansión `FEX_C_2011` / `FEX_C` / `FEX_C18` | Unificado en `fex` |
| Sexo en `P6020` o `P3271`, educación en `P6210` o `P3042`, rama en `RAMA2D` o `RAMA2D_R4` | Unificados fila a fila (sirve al juntar años de distintas épocas) |
| 2007 sin marcas `OCI`/`DSI`; 2020 y empalme con marcas en Características | La condición se deduce del módulo en que aparece cada persona |
| Archivos en subcarpetas (`CSV 13/No ocupados.CSV`) | Búsqueda recursiva |
| Nombres con erratas: «Deocupados» (2013), «Desoucpados», «Inativos» (octubre de 2020; septiembre en el empalme), «Fuerzo de trabajo» (noviembre de 2020) | Se reconocen igual |
| Meses a los que les falta un módulo | Se omiten con aviso (si no, el desempleo saldría 0 %); `incluir_incompletos=True` los carga |
| Marzo–julio de 2020 sin Vivienda, Otras actividades, Otros ingresos ni (serie principal) Desocupados e Inactivos: formulario telefónico | Se cargan con un aviso: las variables de esos módulos quedan vacías en esos meses |
| Varios meses juntos | Niveles = promedio mensual, como el DANE |
| EAM: `CIIU2N4`, `ciiu2`, `CIIU`, `ciiu3`, `ciiu4`, `ciiu_4`, códigos a 2–3 dígitos | `ciiu`, `ciiu_rev`, `division`, `sector` |
| EAM: valores reemplazados por el promedio de un grupo de establecimientos | Marcados en `microagregado`; `dd.eam.panel(..., excluir_microagregados=True)` |
| EMICRON: un ZIP por módulo y año; factor de 2019–2021 en un archivo aparte | Módulos unidos por la clave; `fex` es el factor de la serie vigente en todos los años |
| EMICRON: la clave del módulo de personal ocupado con los nombres corridos | `load_personal` la corrige |

Las cargas de la GEIH se guardan en caché (`~/.cache/dane_data`, parquet): un año completo tarda ~6 s la
primera vez y ~1 s después. Los resultados de `dd.geih.serie_indicadores`, `serie_tabla` y
`serie_frecuencias` se calculan un año a la vez y se guardan por año: toda la serie 2007–2026 tarda alrededor
de un minuto la primera vez y es instantánea después. Se recalculan solos si cambia algún archivo del año,
la consulta (filtros, meses, variables) o el código de dane-data. Todas las tablas y gráficas de la app salen
de ahí, así que la app nunca tiene más de un año de microdatos en memoria. `dd.geih.clear_cache()` borra
estas cachés.

### Validación

Con los datos reales, TD, TGP, TO y ocupados de cada mes de 2007–2026 y del empalme 2010–2020 coinciden
con los anexos del DANE, con diferencias menores a 0,01 puntos. También coinciden las cabeceras y cada sexo
donde el DANE los publica por mes, y las tasas anuales, que son el promedio de los niveles mensuales. Por
ejemplo, la desocupación promedio fue 10,5 % en 2019 y 10,2 % en 2023. Las pruebas (`pytest`) usan datos
sintéticos con las rarezas de cada época. Si encuentran los datos reales, también los comparan mes a mes con
las cifras publicadas (`tests/datos/dane_publicado.csv`) y buscan huecos o saltos bruscos en la serie.

En la EAM, el número de establecimientos, el personal ocupado, la producción bruta, el consumo intermedio y el valor
agregado nacionales de 1992–2011 y 2015–2024 coinciden con la serie histórica y los anexos del DANE: los montos y los
establecimientos a menos de 0,05 % y el personal a menos de 0,15 %. En 2004–2011 el personal publicado no cuenta a los
aprendices, que `pertotal` sí incluye; sin ellos también coincide. Quedan sin explicar los montos de 2011 y los
establecimientos de 1992, que están abajo, en las diferencias con la documentación del DANE. 2012–2014 no tienen anexo en
la página del DANE.

En las Estadísticas Vitales, el total y el sexo de los tres certificados en 2008–2025 y los 33 departamentos en 2019–2025
coinciden exactamente con los cuadros definitivos del DANE. Antes de 2008 no hay cuadros en la página del DANE con qué
comparar.

En la EMICRON, 8 507 cifras de los anexos anuales vigentes (nacional 2019–2024 y 24 ciudades 2019–2025: micronegocios por
situación en el empleo, sexo, actividad, sitio, salud y pensión, RUT y Cámara de Comercio, y el cuadro I.1 con el
personal ocupado, las ventas, el valor agregado y el ingreso mixto) coinciden con una tolerancia relativa de una
milmillonésima, salvo tres diferencias de 2019 que están abajo, en las diferencias con la documentación del DANE. También
las 5 330 de los anexos departamentales de 2020–2024 (24 departamentos y Bogotá, con `fex_dpto`), salvo una errata del
anexo. Las trimestrales no: usan factores trimestrales que no vienen en los microdatos.

En la ECV, los 27 indicadores de la serie 2018–2025 del DANE coinciden exactamente en el total nacional y por área, y a menos
de 0,1 puntos por departamento. Las 15 privaciones del IPM coinciden hogar por hogar con la base oficial del DANE en 2018,
2019, 2023, 2024 y 2025, y en 2020–2022 salvo 5, 25 y 3 hogares (el IPM nacional de 2025 da 9,9 % y 0,040, y el de 2020,
18,1 %, como lo publicado).

En la pobreza monetaria, la serie empalmada 2012–2025 coincide con los anexos del boletín de junio de 2026: las 5 644 cifras
que se pueden comparar (incidencia, brecha y severidad de la pobreza y la pobreza extrema, Gini, ingreso per cápita, líneas,
población y pobres, nacional, por grandes dominios, 23 ciudades y 24 departamentos) quedan dentro del redondeo publicado.

## Advertencias metodológicas

Antes de usar las cifras, lea las
[advertencias metodológicas](https://integralindefinida.github.io/DANE-data/guia/advertencias.html):
las dos mediciones de informalidad, la serie de empalme y la PET, las revisiones de la CIIU y la
anonimización de la EAM, el subregistro en las Estadísticas Vitales, la cobertura de la EMICRON y los
tamaños de muestra.

## Diferencias con la documentación del DANE (ANDA)

Cuando los datos contradicen la documentación oficial del ANDA (diccionarios DDI, etiquetas de
categorías), `dane-data` sigue los datos. Cada caso, con lo que dice el ANDA, lo que muestran los datos
y lo que hace `dane-data`, está en
[Diferencias con la documentación del DANE](https://integralindefinida.github.io/DANE-data/guia/diferencias.html).

## Estructura

```
src/dane_data/
├── config.py          rutas (set_paths, variables de entorno, ~/.config/dane_data/config.json)
├── _io.py             lectura robusta de CSV/TXT/Stata del DANE
├── _hooks.py          lo común de los descargadores: progreso, cancelación, descarga y extracción
├── stats.py           tablas, medias y cuantiles ponderados
├── referencias.py     SMLV, departamentos, diccionarios DDI
├── proyecciones.py    proyecciones de población del DANE (dd.poblacion)
├── data/              diccionarios DDI oficiales, causas de muerte y proyecciones de población
├── geih/              downloader.py · loader.py · indicadores.py · agregados.py (serie_*, exportar)
├── eam/               downloader.py · loader.py · indicadores.py
├── eevv/              downloader.py · loader.py · indicadores.py · agregados.py (serie_*, tasas)
├── emicron/           downloader.py · loader.py · indicadores.py
├── ecv/               downloader.py · loader.py · indicadores.py · ipm.py · agregados.py (serie_*)
├── pobreza/           downloader.py · loader.py (empalme) · indicadores.py · agregados.py · union.py (unir_geih)
├── cli.py             comando `dane-data`
└── app/               aplicación Streamlit (Inicio.py + paginas/)
```

Los descargadores provienen de los repositorios `GEIH` y `EAM` originales; se adaptaron para reportar
progreso y permitir cancelar.

## Privacidad

`dane-data` no envía información a otros sistemas a menos que usted, o quien lo instala o lo usa, lo pida.
La única excepción es la consulta de versiones nuevas que se describe abajo, que no envía ningún dato suyo.
Solo se conecta a internet para lo siguiente:

- El lanzador, la primera vez, instala [uv](https://docs.astral.sh/uv/) desde `astral.sh` en
  `%USERPROFILE%\.local\bin` (Windows) o `~/.local/bin` (Mac y Linux), sin cambiar el `PATH` del usuario ni
  archivos como `~/.zshrc` o `~/.bashrc`. uv descarga Python y las librerías de
  `uv.lock` (desde GitHub y PyPI): Python y la caché quedan en las carpetas de uv del usuario, y el entorno
  en `.venv/`, dentro de la carpeta del zip.
- La app y la librería descargan los microdatos del ANDA del DANE (`microdatos.dane.gov.co`) solo cuando
  usted lo pide.
- La app, al abrir la página de inicio y como mucho una vez al día, consulta en `pypi.org` cuál es la última
  versión de dane-data y, si hay una nueva, lee qué cambia en `raw.githubusercontent.com`. No envía ningún
  dato suyo; se desactiva con la variable de entorno `DANE_DATA_SIN_ACTUALIZACIONES=1`. La versión nueva
  solo se instala si usted lo pide con el botón «Actualizar»: entonces uv la descarga de PyPI.
- La app usa [Streamlit](https://streamlit.io) con las estadísticas de uso desactivadas
  (`gatherUsageStats = false`) y, salvo que se pida `--address`, solo abre su servidor en este computador.

Para desinstalar, vea [Desinstalar](https://integralindefinida.github.io/DANE-data/instalacion.html#desinstalar).

## Licencia y cita

Código: MIT. Datos: DANE, Archivo Nacional de Datos (ANDA). Cite como
*DANE. Gran Encuesta Integrada de Hogares (GEIH) [microdatos]* / *Encuesta Anual Manufacturera (EAM) [microdatos]* /
*Estadísticas Vitales (EEVV) [microdatos]* / *Encuesta Nacional de Calidad de Vida (ECV) [microdatos]* /
*Medición de Pobreza Monetaria y Desigualdad [microdatos]*.

Si `dane-data` le sirvió en un trabajo, cítelo también, con la versión que usó (`dd.__version__`):

> Ramírez, L. (2026). *dane-data: microdatos del DANE (GEIH, EAM, Estadísticas Vitales, EMICRON, ECV y pobreza monetaria) listos para analizar* (versión X.Y.Z)
> [software]. https://github.com/IntegralIndefinida/DANE-data

```bibtex
@software{dane_data,
  author  = {Ramírez, Luis},
  title   = {dane-data: microdatos del DANE (GEIH, EAM, Estadísticas Vitales, EMICRON, ECV y pobreza monetaria) listos para analizar},
  version = {X.Y.Z},
  year    = {2026},
  url     = {https://github.com/IntegralIndefinida/DANE-data},
}
```

El botón *Cite this repository* de GitHub da la misma cita con la última versión (sale de
[`CITATION.cff`](CITATION.cff)). Más detalles en [Cómo citar](https://integralindefinida.github.io/DANE-data/citar.html).
