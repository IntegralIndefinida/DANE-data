# DANE-data 📊🇨🇴

📖 [Documentación](https://integralindefinida.github.io/DANE-data/) · 📦 [PyPI](https://pypi.org/project/dane-data/)

**Microdatos del DANE listos para analizar** — Gran Encuesta Integrada de Hogares (**GEIH**, 2007–2026) y
Encuesta Anual Manufacturera (**EAM**, 1992–2024).

Dos formas de usarlo:

| | Para quién | Cómo |
|---|---|---|
| 🖱️ **Aplicación** | Estudiantes que empiezan, clases, consultas rápidas | `dane-data app` → se abre en el navegador |
| 🐍 **Librería Python** | Automatización, investigación, estudiantes avanzados | `import dane_data as dd` |

Ambas usan el mismo motor: descargan del ANDA del DANE, unen los módulos, **armonizan las variables
entre épocas** (nombres, separadores, coma decimal, factores de expansión, revisiones CIIU) y calculan
indicadores ponderados como lo hace el DANE.

---

## Instalación de la app

1. En la página de **[Releases](https://github.com/IntegralIndefinida/DANE-data/releases)** descargue `dane-data-<versión>.zip` (en *Assets*).
2. Descomprímalo donde quiera.
3. Doble clic en el lanzador de su sistema:

   | Sistema | Archivo |
   |---|---|
   | Windows | `Abrir dane-data (Windows).bat` |
   | Mac | `Abrir dane-data (Mac).command` |
   | Linux | `abrir-dane-data.sh` |

La primera vez necesita internet y tarda 1–3 minutos: el lanzador instala [uv](https://docs.astral.sh/uv/),
que descarga Python 3.12 y las librerías exactas de `uv.lock` dentro de la carpeta (`.venv/`), sin tocar el
resto del sistema. Las siguientes veces abre en segundos. **El navegador se abre solo**; para cerrar la
app basta cerrar la ventana de la terminal.

> Primera vez en **Windows**: si aparece "Windows protegió su PC" → *Más información* → *Ejecutar de todas
> formas*. En **Mac**: si dice "desarrollador no identificado" → clic derecho → *Abrir* → *Abrir*.

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

## 🖱️ La aplicación

```bash
dane-data app          # o doble clic en el lanzador; el navegador se abre solo
```

| Página | Qué hace |
|---|---|
| 🏠 Inicio | Explica las encuestas, muestra qué datos hay y configura las carpetas |
| ⬇️ Descargar datos | Elige encuesta y años y descarga |
| 👥 Indicadores laborales | TD, TGP, TO, informalidad e ingresos, por sexo, edad, zona, educación o departamento; anual o mensual |
| 🔎 Tablas y microdatos | Tablas ponderadas a la medida, distribución de ingresos frente al salario mínimo, exportación |
| 🏭 Indicadores industriales | Producción, valor agregado, empleo, productividad y participación laboral por sector o departamento |
| 🧱 Panel y microdatos EAM | Panel de establecimientos (balanceado o no), supervivencia, exportación |
| 📚 Diccionario | Buscador de variables con las etiquetas y categorías oficiales del DANE |

Cada tabla se descarga en **CSV, Excel o Stata**, y cada página muestra el **código Python equivalente**:
así se pasa de la aplicación al notebook sin empezar de cero.

Para usarla en un aula (el profesor la sirve y los estudiantes entran desde la red local):
`dane-data app --address 0.0.0.0`. La aplicación no tiene usuarios ni contraseña: cualquiera en esa red
puede cambiar las carpetas de datos, descargar y exportar en el computador del profesor. Úsela solo en
una red de confianza.

## 🐍 La librería

```python
import dane_data as dd

# 1. ¿Dónde están (o estarán) los datos?  Se recuerda para siempre.
dd.set_paths(geih="~/datos/GEIH/data", eam="~/datos/EAM/data", save=True)

# 2. Descargar (incremental: lo ya bajado se salta)
dd.geih.download([2024, 2025])
dd.eam.download(range(2014, 2025))

# 3. Cargar: una persona por fila, módulos ya unidos y variables armonizadas
df = dd.geih.load(2025)                                  # todos los meses
df = dd.geih.load([2024, 2025], months=[1, 2, 3])        # primer trimestre
df = dd.geih.load(2025, columns=["P6500", "P7070"])      # + variables DANE extra
df = dd.geih.load(2016, empalme=True)                    # serie de empalme (marco 2018)
df = dd.geih.load(range(2015, 2026), variables=["fex", "sexo", "ocupado"])  # solo esas columnas

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

# 7. Diccionario oficial
dd.buscar_variable("pensión")
dd.describir("P6920")
```

También en terminal:

```bash
dane-data estado                               # rutas y años/meses disponibles
dane-data descargar geih --anios 2024 2025
dane-data descargar geih --anios 2016 --empalme
dane-data descargar eam --anios 2022 2023 2024
dane-data config --geih RUTA --empalme RUTA --eam RUTA
```

Vea [`examples/01_primeros_pasos.ipynb`](https://github.com/IntegralIndefinida/DANE-data/blob/main/examples/01_primeros_pasos.ipynb)
para un recorrido completo.

### Variables armonizadas

Las variables en **minúscula** las crea `dane-data` y significan lo mismo en todos los años. Las de
**MAYÚSCULA** (GEIH) son las originales del DANE.

**GEIH**: `anio`, `mes`, `fex`, `sexo`, `edad`, `grupo_edad`, `dpto`, `departamento`, `zona`,
`condicion` (Ocupado / Desocupado / Inactivo / Fuera de la PET), `pet`, `fuerza_trabajo`, `ocupado`,
`desocupado`, `inactivo`, `formal`, `cotiza_pension`, `ingreso_laboral`, `smlv`, `ratio_smlv`,
`horas_semana`, `posicion_ocupacional`, `rama2d`, `rama_rev`, `nivel_educativo`, `jefe_hogar`.

**EAM**: todas las columnas en minúscula, más `anio`, `ciiu`, `ciiu_rev`, `division`, `sector`, `departamento`.

### Lo que `dane-data` resuelve por usted

| Problema en los archivos del DANE | Solución |
|---|---|
| 2007–2021: cada módulo partido en Área / Cabecera / Resto | Nacional = Cabecera + Resto (Área es un subconjunto de Cabecera) |
| Separadores `;` `,` `\t`, UTF-8 / Latin-1, coma decimal, blancos `" "` | Detección automática; columnas numéricas quedan numéricas |
| Factor de expansión `FEX_C_2011` / `FEX_C` / `FEX_C18` | Unificado en `fex` |
| Sexo en `P6020` o `P3271`, educación en `P6210` o `P3042`, rama en `RAMA2D` o `RAMA2D_R4` | Unificados fila a fila (sirve al juntar años de distintas épocas) |
| 2007 sin marcas `OCI`/`DSI`; 2020 y empalme con marcas en Características | La condición se deduce del módulo en que aparece cada persona |
| Archivos en subcarpetas (`CSV 13/No ocupados.CSV`) | Búsqueda recursiva |
| Meses a los que les falta un módulo | Se omiten con aviso (si no, el desempleo saldría 0 %); `incluir_incompletos=True` los carga |
| Varios meses juntos | Niveles = promedio mensual, como el DANE |
| EAM: `CIIU2N4`, `ciiu2`, `CIIU`, `ciiu3`, `ciiu4`, `ciiu_4`, códigos a 2–3 dígitos | `ciiu`, `ciiu_rev`, `division`, `sector` |

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

## ⚠️ Advertencias metodológicas

- **Informalidad**: `formal` = afiliado a salud (P6090) **y** cotizando a pensión (P6920). Es una
  definición por seguridad social; la oficial del DANE incluye el tamaño de la empresa.
- **Serie principal vs. empalme**: para series largas 2010–2020 comparables con 2021+, use `empalme=True`.
- **PET**: desde 2022 son las personas de 15 años o más; antes, 12+ (urbano) y 10+ (rural).
- **Ingresos**: `INGLABO` en pesos corrientes; la GEIH 2007 no lo trae.
- **EAM**: los montos vienen en **miles de pesos corrientes**. Según los propios archivos, la CIIU es
  Rev. 2 hasta 2000, Rev. 3 en 2001–2011 y Rev. 4 desde 2012 (la documentación del ANDA dice otra
  cosa; vea las diferencias con la documentación del DANE); los sectores no se comparan entre revisiones sin una
  correlativa.
- **Muestras pequeñas**: con menos de ~100 observaciones (`n_muestra`) las cifras no son confiables.
- El salario mínimo histórico (`dd.SMLV`) está tomado de los decretos; verifíquelo antes de publicar.

## 📋 Diferencias con la documentación del DANE (ANDA)

Cuando los datos contradicen la documentación oficial del ANDA (diccionarios DDI, etiquetas de
categorías), `dane-data` sigue los datos y lo anota aquí. El buscador de variables
(`dd.buscar_variable`, `dd.describir` y la página 📚 Diccionario) muestra el DDI **tal como lo publica
el DANE**, así que en estos casos no coincide con las variables armonizadas.

| Variable | Qué dice el ANDA | Qué muestran los datos y qué hace `dane-data` |
|---|---|---|
| `P6430` → `posicion_ocupacional` (GEIH, desde 2022) | El DDI de 2022 (catálogo 771) y el de 2025 (catálogo 853) repiten las 9 categorías del cuestionario anterior: 7 = trabajador sin remuneración en negocios de otros hogares, 8 = jornalero o peón, 9 = otro. | Desde enero de 2022 el código 7 es **jornalero o peón** (100 % agropecuario y casi todos con ingreso), el 8 es **otro** y el 9 ya no aparece. Hasta 2021, y en el empalme, se usan las etiquetas anteriores, que sí coinciden con los datos. El código 6 se sigue llamando "familiar sin remuneración"; desde 2022 podría incluir también el trabajo sin remuneración en negocios de otros hogares (sin confirmar). |
| `ciiu` → `ciiu_rev`, `sector` (EAM 2000 y 2012) | La descripción del estudio (catálogos 491 a 888) dice que "en el año 2000 se incorpora en la EAM la CIIU Rev.3" y que la Rev. 4 se oficializó "con la difusión de las cifras referentes al año 2013". En otro pasaje del mismo texto los cambios de la Rev. 4 se ubican "a partir del año 2012". | El archivo de 2000 trae la variable `ciiu2` con códigos Rev. 2 (solo divisiones 31–39, igual que 1992–1999); la Rev. 3 aparece en 2001. El archivo de 2012 ya trae `ciiu4` con códigos Rev. 4 (divisiones 10–14, que no existen en la Rev. 3). `dane-data` asigna la revisión según la variable de cada año: Rev. 2 hasta 2000, Rev. 3 en 2001–2011 y Rev. 4 desde 2012. |
| Cobertura por división (EAM, archivos de 1995 en adelante) | La descripción de cada archivo dice que comprende "desde la división 11 a la 33 de la CIIU REV.4", también en los de 1995–2011. | Los archivos de 1995–2000 están en Rev. 2 (divisiones 31–39) y los de 2001–2011 en Rev. 3 (15–37). Los años en Rev. 4 incluyen la división 10, alimentos, que es el 18 % de los establecimientos en 2012–2024; el de 2012 incluye además las divisiones 58, 59 y 73. `dane-data` conserva todas las divisiones de cada archivo. |
| Títulos de los catálogos 871 y 888 (EAM) | El título de ambos catálogos en el DDI es "EAM_2022". | Sus archivos son de 2023 (871) y 2024 (888), como dice la versión de cada archivo. `dane-data` descarga 2023 del 871 y 2024 del 888. |
| `FEX_C_2011` → `fex` (GEIH 2008 y 2011, archivos CSV) | Los CSV de los catálogos 206 (2008) y 182 (2011) deberían traer el mismo factor de expansión que las versiones TXT y SPSS de esos catálogos. | Los CSV perdieron el punto decimal y traen puntos de miles: `849.491.032.387.525` es 84,9491032387525 en el TXT. Como la parte entera tiene de 1 a 5 dígitos, el valor no se puede recuperar del CSV. Algunos archivos traen además filas con un campo de más. Se confirmó persona por persona en marzo de 2011 contra el TXT. Para esos años `dane-data` descarga la versión TXT (tabulada) del mismo catálogo. Si en la carpeta solo están los CSV dañados, esos meses se omiten con un aviso para volver a descargarlos. |
| Septiembre de 2021 (GEIH, catálogo 701, `Septiembre.csv (2) (1).zip`) | Se publica como CSV. | Los archivos vienen separados por espacios, y el texto libre también tiene espacios, así que las columnas no se pueden separar. `dane-data` descarga ese mes en Stata (`Septiembre.zip`, del mismo catálogo). Si solo está el CSV, el mes se omite con un aviso para volver a descargarlo. |
| `PETI` → `pet` (empalme, octubre de 2012, catálogo 760) | Las cifras publicadas de la serie con proyecciones del CNPV 2018 usan la PET de 15 años o más en todos los meses. | El archivo de octubre de 2012 marca la PET con la definición anterior (12+ urbano, 10+ rural): la PET sube 9 % frente a septiembre y aparecen ~400 mil ocupados menores de 15 años. Con la PET del archivo, la TGP de ese mes saldría 64,5 % frente al 69,1 % publicado. `dane-data` aplica a todo el empalme la PET de 15 años o más (`harmonize(..., edad_minima_pet=15)`), lo que solo cambia octubre de 2012: así los 132 meses del empalme coinciden con el anexo del DANE. |
| `P6020` → `sexo` (empalme, abril y mayo de 2017, catálogo 763) | Las cifras mensuales por sexo del anexo (hoja "Total_nacional_IML_Sexo") suman el total nacional. | Son todos los hogares de Putumayo de esos meses (320 y 359 personas): solo traen edad y factor de expansión, y el resto de las características (sexo, parentesco, salud, educación) viene en blanco, también en las versiones Stata y SPSS del mismo ZIP. No se pueden recuperar: no están en ningún otro mes del empalme ni en la serie principal, y el catálogo de nuevos departamentos de 2017 (562) no tiene Mocoa en abril ni mayo (posiblemente por la avalancha del 31 de marzo; sin confirmar). `dane-data` deja `sexo` vacío para ellos: los totales coinciden con lo publicado, pero los ocupados de cada sexo quedan cerca de 0,1 % por debajo (unos 16 mil en total). |

## Estructura

```
src/dane_data/
├── config.py          rutas (set_paths, variables de entorno, ~/.config/dane_data/config.json)
├── _io.py             lectura robusta de CSV/TXT del DANE
├── stats.py           tablas, medias y cuantiles ponderados
├── referencias.py     SMLV, departamentos, diccionarios DDI (data/*.json)
├── geih/              downloader.py · loader.py · indicadores.py
├── eam/               downloader.py · loader.py · indicadores.py
├── cli.py             comando `dane-data`
└── app/               aplicación Streamlit (Inicio.py + paginas/)
```

Los descargadores provienen de los repositorios `GEIH` y `EAM` originales; se adaptaron para reportar
progreso y permitir cancelar.

## Licencia y cita

Código: MIT. Datos: DANE, Archivo Nacional de Datos (ANDA). Cite como
*DANE. Gran Encuesta Integrada de Hogares (GEIH) [microdatos]* / *Encuesta Anual Manufacturera (EAM) [microdatos]*.
