# Encuesta Nacional de Calidad de Vida

La Encuesta Nacional de Calidad de Vida (ECV) del DANE es una encuesta anual por muestreo a unos 90.000 hogares. Cada
capítulo del cuestionario es un archivo, de viviendas, de hogares o de personas, y los totales se expanden con el
{term}`factor de expansión` (`FEX_C`). Con ella el DANE calcula el **Índice de Pobreza Multidimensional** (IPM).
`dane-data` cubre 2018–2025, los años con factores basados en el CNPV 2018.

| Capítulo (`modulos=`) | Unidad | Contenido |
|---|---|---|
| `"vivienda"` | Vivienda | Datos de la vivienda: tipo, paredes, pisos, servicios públicos, departamento y área |
| `"servicios"` | Hogar | Servicios del hogar: cuartos, agua, sanitario, gas, energía para cocinar |
| `"tenencia"` | Hogar | Tenencia y financiación de la vivienda que ocupa el hogar |
| `"condiciones"` | Hogar | Condiciones de vida y tenencia de bienes: internet, computador, percepción de pobreza |
| `"caracteristicas"` | Persona | Características y composición del hogar: sexo, edad, parentesco, etnia |
| `"salud"` | Persona | Afiliación, régimen, uso de servicios de salud |
| `"primera_infancia"` | Persona | Atención integral de los niños y niñas menores de 5 años |
| `"educacion"` | Persona | Alfabetismo, asistencia, nivel y años aprobados (5 años y más) |
| `"fuerza_trabajo"` | Persona | Actividad, búsqueda de empleo, cotización a pensión (12 años y más) |
| `"tic"` | Persona | Uso de computador, internet y celular (5 años y más) |
| `"trabajo_infantil"` | Persona | Trabajo de niños y niñas de 5 a 17 años |

## Descargar y cargar

```python
import dane_data as dd

dd.ecv.download(2025)                                   # los once capítulos de 2025
dd.ecv.download(range(2018, 2026), modulos=["caracteristicas", "salud"])
dd.ecv.download()                                       # toda la serie: unos 4 GB de ZIP, 2 GB extraídos
```

Los ZIP de 2024 y 2025 pesan mucho más que los de antes: unos 1,4 GB por año con los once capítulos, contra 150 MB en
2018–2023. Ya extraídos, todos los años ocupan entre 200 y 300 MB.

{dd}`ecv.load()` devuelve una fila por persona con los capítulos pedidos, o una fila por hogar con `nivel="hogar"`. Siempre
trae Características (o Servicios, con hogares) y la geografía de la vivienda:

```python
df = dd.ecv.load(2025, modulos=["salud", "educacion"])          # personas, con Salud y Educación
hogares = dd.ecv.load(2025, modulos=["tenencia", "vivienda"], nivel="hogar")
df = dd.ecv.load(range(2018, 2026), modulos="salud", columns=["P6090", "P6100"])  # solo esas variables
```

Las llaves salen de la *Estructura de la base de datos* del DANE. La vivienda es `DIRECTORIO`; en las tablas de hogar, el
hogar es `SECUENCIA_ENCUESTA` (y `SECUENCIA_P` es siempre 1); en las de personas, el hogar es `SECUENCIA_P` y la persona,
`SECUENCIA_ENCUESTA`. `load` lleva todas las tablas a las mismas llaves: el hogar queda siempre en `SECUENCIA_P`
(`dd.ecv.KEYS_HOGAR`, `dd.ecv.KEYS_PERSONA`). Un capítulo de personas no es de todas (Educación es de 5 años y más, Fuerza
de trabajo de 12 y más): las demás quedan con sus columnas vacías.

En **2018** el `FEX_C` de los capítulos es anterior al CNPV 2018. El DANE publicó aparte los factores basados en el censo,
que son los de la serie oficial 2018–2025: `download` los baja con cualquier capítulo de 2018 y `load` los usa (el
original queda en `FEX_C_ORIGINAL`). Así 2018 da 48,6 millones de personas, como la serie, y no 50,0.

## Variables armonizadas

Las variables del DANE quedan en MAYÚSCULA y las armonizadas en minúscula. Las de un capítulo aparecen si se carga ese
capítulo.

### Personas

```{include} ../_generado/ecv_variables_persona.md
```

### Hogares

```{include} ../_generado/ecv_variables_hogar.md
```

`region` son las nueve regiones de la ECV. 2020 no trae la variable `REGION`, así que ese año sale del departamento: la
parte rural de Bogotá va en Oriental, como en los años que sí la traen.

## Indicadores

{dd}`ecv.indicadores()` calcula los de la serie que publica el DANE (*anexo de series* de la ECV), expandidos con `fex`, sobre
una tabla de personas: los de hogares (servicios, internet, tenencia, percepción de pobreza) se calculan sobre los jefes,
que son exactamente uno por hogar. {dd}`ecv.serie_indicadores()` hace lo mismo año por año, lee solo las columnas que
necesita y guarda cada resultado en disco:

```text
>>> r = dd.ecv.serie_indicadores(range(2018, 2026))
>>> r[["anio", "hogares", "personas_por_hogar", "pct_internet_hogar", "pct_afiliados", "anios_educacion_5_mas"]].round(2)
   anio      hogares  personas_por_hogar  pct_internet_hogar  pct_afiliados  anios_educacion_5_mas
0  2018  15402515.49                3.15               52.26          93.57                   8.15
1  2019  15999297.91                3.10               51.95          92.80                   8.21
2  2020  16416550.72                3.08               56.53          93.16                   8.26
3  2021  17068099.59                3.00               60.55          93.03                   8.34
4  2022  17525655.28                2.95               59.47          94.69                   8.36
5  2023  18009262.99                2.90               63.94          95.93                   8.44
6  2024  18489372.98                2.86               65.65          96.52                   8.52
7  2025  18952290.37                2.82               73.92          97.23                   8.71
```

Los años de educación se cuentan como en el Cuadro 18 de la serie: desde primero de primaria; quien no estudia, el grado
aprobado (la media va de 10 a 13, con la normal) o, en la superior, 11 más los años aprobados en ella; quien estudia, el
grado anterior al que cursa. El régimen contributivo incluye el especial, y los porcentajes de régimen son sobre los
afiliados. La lista completa está en la referencia de {dd}`ecv.indicadores()`.

## Índice de Pobreza Multidimensional

El IPM sigue la metodología de Alkire y Foster que el DNP adaptó para Colombia: 15 privaciones en 5 dimensiones de igual
peso. Un hogar es pobre si su puntaje, la suma ponderada de sus privaciones, es de 5/15 (33,3 %) o más, y todas sus
personas lo son.

```{include} ../_generado/ecv_privaciones.md
```

```python
personas = dd.ecv.load(2025, modulos=dd.ecv.MODULOS_IPM, columns=dd.ecv.COLUMNAS_IPM)
hogares = dd.ecv.privaciones(personas)     # una fila por hogar: las 15 privaciones, el puntaje y si es pobre
dd.ecv.ipm(hogares, por="area")            # incidencia, intensidad, IPM y % de hogares con cada privación
dd.ecv.serie_ipm(range(2018, 2026), por="departamento")   # año por año, con caché
```

```text
>>> dd.ecv.serie_ipm(range(2018, 2026))[["anio", "incidencia", "intensidad", "ipm"]].round(3)
   anio  incidencia  intensidad    ipm
0  2018      19.121      41.724  0.080
1  2019      17.452      41.373  0.072
2  2020      14.828      40.817  0.061
3  2021      15.966      40.809  0.065
4  2022      12.923      40.265  0.052
5  2023      12.134      40.083  0.049
6  2024      11.530      40.203  0.046
7  2025       9.913      40.380  0.040
```

* La **incidencia** (H) es el % de personas pobres; la **intensidad** (A), el puntaje promedio de los pobres; el **IPM**,
  H × A. Las privaciones (`pct_<privación>`) son % de **hogares**, como en los anexos del DANE.
* **La muestra cambia con la desagregación, como en el DANE.** Las cifras nacionales y por área van sin la parte rural de
  Arauca, Casanare, Putumayo, Amazonas, Guainía, Guaviare, Vaupés y Vichada; las regionales y las departamentales, con toda
  la muestra. {dd}`ecv.ipm()` lo decide por `por=`, y `muestra="nacional"` o `"completa"` lo fuerza.
* `region_ipm` son las seis regiones de los anexos del IPM (Caribe, Oriental, Central, Pacífica, Orinoquía-Amazonía y
  Bogotá cabecera), que no son las de la ECV: la parte rural de Bogotá va en Oriental y San Andrés no tiene región.
* **2020, con los colegios cerrados:** el DANE armó la inasistencia escolar con su base complementaria del IPM 2020
  (estrategias de estudio en casa, con información del SIMAT), que no es de la ECV. {dd}`ecv.download()` la baja con 2020 y
  {dd}`ecv.privaciones()` la usa; sin ella, 2020 da 14,8 % y no 18,1 %, y se avisa.

Las definiciones siguen el *Algoritmo para la construcción del IPM* del DANE. Donde el algoritmo no lo dice todo, se
ajustaron hasta reproducir la base oficial del IPM (`BDATOS-IPM`, en el ANDA) hogar por hogar; vea {dd}`ecv.privaciones()`:

* Los años de educación del IPM no son los del Cuadro 18: la media cuenta hasta 11, y la superior desde 11 (desde 16 en el
  posgrado) más el año aprobado en ese nivel.
* El desempleo de larga duración es de 52 semanas o más.
* Un hogar sin personas de 15 años y más se priva por logro educativo y por analfabetismo.
* Desde 2021, un niño que estudia solo de forma virtual cuenta como inasistente si el hogar no tiene internet o él no tuvo
  contacto con sus maestros la semana pasada.
* Las paredes de guadua, caña, zinc y desechos cambian de código en 2020, pero el DANE siguió con los códigos viejos ese
  año.
* En 2020, un niño que estudia es inasistente si no recibió estrategias de estudio en casa y el hogar no tiene internet y un
  equipo, o si las recibió, pero no por plataformas con internet y un equipo ni por guías con llamadas o visitas del
  colegio.

## Lo que cambia con los años

| Qué | Años | Qué hace `dane-data` |
|---|---|---|
| Factores de expansión del CNPV 2018 | 2018, publicados aparte | Los baja y los usa; el original queda en `FEX_C_ORIGINAL` |
| Departamento | `DPTO` en 2018, `P1_DEPARTAMENTO` desde 2019 | `departamento` con los dos |
| Región | 2020 no trae `REGION` | `region` sale del departamento ese año |
| Paredes (`P4005`) | Siete materiales hasta 2019; guadua y caña separados desde 2020 | `paredes` del IPM con los códigos de cada año (los viejos también en 2020, como el DANE) |
| Estrategias de estudio en casa | 2020, en la base complementaria del IPM (catálogo 679) | Se baja con 2020 y entra en la inasistencia escolar del IPM |
| Modalidad de estudio (`P3336`, `P3337`) | Desde 2021 | Entra en la inasistencia escolar del IPM |
| Nombres de los ZIP | Cambian en 2023, 2024 y 2025 | Tabla fija de catálogos y descargas (`dd.ecv.ANIOS_DISPONIBLES`) |
| Educación 2021 | ZIP en Deflate64, que Python no lee | Se descomprime con `inflate64` |

## Documentos del DANE

* *Metodología general Encuesta Nacional de Calidad de Vida*, DSO-ECV-MET-001 (versión 15 con la ECV 2024), y la *Ficha
  metodológica* de cada año, en la documentación de cada catálogo del ANDA.
* *Estructura de la base de datos* de cada año: las tablas y las llaves.
* *Anexo de series* de la ECV (`anex-ECV-Series-2025.xlsx`): de ahí salen las cifras de {doc}`validacion`.
* *Algoritmo para la construcción del Índice de Pobreza Multidimensional* y *Metodología general de pobreza* (DSO-EMP-MET-001),
  y los anexos del IPM (`anex-PMultidimensional-2025.xlsx` y el departamental).

```{seealso}
El ejemplo {doc}`../ejemplos/ecv` grafica el IPM por departamento y la caída de las privaciones de 2018 a 2025.
```
