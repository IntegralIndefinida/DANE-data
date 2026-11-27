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

## Lo que `dane-data` resuelve

Trabajar con los microdatos tal como los publica el ANDA del DANE es un trabajo arduo. Hay que
encontrar el catálogo de cada año y bajar sus ZIP uno por uno. Adentro, la información está repartida en
varios archivos, a veces partidos por zona, y hay que saber cuáles se suman y cómo se unen. Los archivos
no se escriben igual todos los años: cambian el formato, el separador, la codificación y la forma de
escribir los decimales, y algunos llegan dañados o incompletos sin que nada lo advierta. Las variables
también cambian de nombre, de códigos y de clasificación de una época a otra, y la documentación oficial
no siempre coincide con lo que traen los datos. Y aun con todo unido, las cifras solo salen como las
publica el DANE si se ponderan y se agregan con la metodología del DANE.

`dane-data` hace todo ese trabajo. Descarga solo lo necesario y, sin archivos dañados.Encuentra los archivos
aunque cambien de nombre o de carpeta, reconoce el formato de cada uno, une los módulos y avisa cuando falta 
algo. Después crea variables que significan lo mismo en todos los años, así que épocas distintas caben en una
misma tabla, y calcula los indicadores con la misma ponderación del DANE. Los casos concretos de cada encuesta 
están en [la guía](https://integralindefinida.github.io/DANE-data/guia/encuestas.html#lo-que-dane-data-resuelve-por-usted).

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

Requiere Python ≥ 3.10. La organización del código, las pruebas y cómo publicar una versión están en
[Desarrollo](https://integralindefinida.github.io/DANE-data/desarrollo.html).

## La aplicación

```bash
dane-data app          # o doble clic en el lanzador; el navegador se abre solo
```

Tiene una página por tema: indicadores laborales, tablas y microdatos de la GEIH, indicadores industriales
y panel de la EAM, pobreza monetaria, nacimientos y defunciones, micronegocios, calidad de vida e IPM, la
descarga de los datos y el diccionario de variables
([qué hace cada una](https://integralindefinida.github.io/DANE-data/guia/app.html)). Cada tabla se
descarga en CSV, Excel o Stata, y cada página muestra el código Python equivalente, que se puede copiar a
un notebook para seguir desde ahí.

Para usarla en un aula o un servidor (el profesor la sirve y los estudiantes entran desde la red local):
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

Las variables en minúscula las crea `dane-data` y significan lo mismo en todos los años; las de MAYÚSCULA
son las originales del DANE. La guía explica cada una: las de la
[GEIH](https://integralindefinida.github.io/DANE-data/guia/variables.html), la
[EAM](https://integralindefinida.github.io/DANE-data/guia/eam.html), las
[Estadísticas Vitales](https://integralindefinida.github.io/DANE-data/guia/eevv.html), la
[EMICRON](https://integralindefinida.github.io/DANE-data/guia/emicron.html), la
[ECV](https://integralindefinida.github.io/DANE-data/guia/ecv.html) y la
[pobreza monetaria](https://integralindefinida.github.io/DANE-data/guia/pobreza.html).

## Validación

Las cifras de `dane-data` coinciden con las que publica el DANE:

| Encuesta | Qué se compara | Resultado |
|---|---|---|
| GEIH | TD, TGP, TO y ocupados de cada mes, 2007–2026 y empalme 2010–2020; informalidad | Tasas a menos de 0,01 puntos; ocupados e informales, a menos de 0,01 % |
| EAM | Establecimientos, personal, producción, consumo intermedio y valor agregado nacionales, 1992–2011 y 2015–2024 | Montos y establecimientos a menos de 0,05 %; personal, a menos de 0,15 % |
| Estadísticas Vitales | Nacimientos, defunciones y defunciones fetales por sexo (2008–2025) y por departamento (2019–2025) | Exactos |
| EMICRON | 13 837 cifras de los anexos anuales y departamentales, 2019–2025 | Iguales, salvo tres de 2019 y una errata del anexo |
| ECV e IPM | 27 indicadores, 2018–2025; las 15 privaciones del IPM, hogar por hogar | Exactos en el total nacional y por área; el IPM, salvo 33 hogares en 2020–2022 |
| Pobreza monetaria | 5 644 cifras de la serie empalmada 2012–2025 | Dentro del redondeo publicado |

Son pruebas automáticas (`pytest`), que hacen la comparación cuando encuentran los microdatos reales. Las
pocas cifras que no coinciden están documentadas junto a su justificación en
[Validación](https://integralindefinida.github.io/DANE-data/guia/validacion.html).

## Advertencias metodológicas

Antes de usar las cifras, lea las
[advertencias metodológicas](https://integralindefinida.github.io/DANE-data/guia/advertencias.html).

## Diferencias con la documentación del DANE (ANDA)

Cuando los datos contradicen la documentación oficial del ANDA (diccionarios DDI, etiquetas de
categorías), `dane-data` sigue los datos. Cada caso, con lo que dice el ANDA, lo que muestran los datos
y lo que hace `dane-data`, está en
[Diferencias con la documentación del DANE](https://integralindefinida.github.io/DANE-data/guia/diferencias.html).

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
