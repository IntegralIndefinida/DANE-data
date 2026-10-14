# Variables armonizadas

Los nombres, las preguntas y los códigos de la GEIH cambian entre épocas. {dd}`geih.harmonize()` (que
{dd}`geih.load()` aplica a cada mes) construye un conjunto de variables **en minúscula** que significan lo
mismo en todos los años. Cada una se calcula **fila a fila** desde la variable del DANE que exista en esa
época, así que se pueden juntar años distintos en un mismo `DataFrame`.

Las variables originales del DANE se conservan en **MAYÚSCULA**, sin cambios.

## Identificación y expansión

| Variable | Definición | Origen en los datos del DANE |
|---|---|---|
| `anio`, `mes` | Año y mes de la encuesta | La carpeta del mes |
| `fex` | {doc}`Factor de expansión <ponderacion>` mensual: cuántas personas representa el registro | `FEX_C18` (desde 2022), `FEX_C` (2020 y empalme), `FEX_C_2011` (2007–2021) |
| `dpto` | Código DIVIPOLA del departamento | `DPTO` |
| `departamento` | Nombre del departamento (categórica) | `DPTO` con `dd.DEPARTAMENTOS` |
| `zona` | `Urbano (cabecera)` o `Rural (centros poblados y disperso)` | `CLASE` (1 y 2) |

## Características de las personas

| Variable | Definición | Origen |
|---|---|---|
| `sexo` | `Hombre` o `Mujer` | `P3271` (desde 2022) o `P6020` |
| `edad` | Años cumplidos | `P6040` |
| `grupo_edad` | `0–14`, `15–24`, `25–34`, `35–44`, `45–54`, `55–64`, `65+` (ordenada) | `edad` |
| `jefe_hogar` | 1 si es el jefe o la jefa del hogar | `P6050 == 1` |
| `nivel_educativo` | `Ninguno`, `Primaria`, `Secundaria`, `Media`, `Superior` (ordenada) | `P3042` (desde 2022) o `P6210` |

El nivel educativo agrupa el mayor nivel alcanzado. Con `P3042`: ninguno y preescolar son `Ninguno`;
básica primaria, `Primaria`; básica secundaria, `Secundaria`; media académica, media técnica y normalista,
`Media`; técnica, tecnológica, universitaria y posgrados, `Superior`. Con `P6210` la correspondencia es la
misma por nivel.

## Condición de actividad

| Variable | Definición |
|---|---|
| `pet` | 1 si está en la población en edad de trabajar |
| `fuerza_trabajo` | 1 si está ocupado o desocupado |
| `ocupado` | 1 si está ocupado |
| `desocupado` | 1 si está desocupado (y no ocupado) |
| `inactivo` | 1 si está en la PET pero no en la fuerza de trabajo |
| `condicion` | `Ocupado`, `Desocupado`, `Inactivo` o `Fuera de la PET` |

Las marcas salen de las variables del DANE `OCI` (ocupado), `DSI` (desocupado), `PET`, `PETI` e `INI`
(inactivo). En los años en que no existen (2007), se deducen del archivo en que aparece cada persona: estar
en el archivo de Ocupados es ser ocupado, y así con Desocupados, Inactivos y Fuerza de trabajo.

La edad mínima de la PET depende del marco: 12 años en la zona urbana y 10 en la rural con el marco del
censo 2005, y 15 años con el del CNPV 2018. En la **serie de empalme** `dane-data` aplica 15 años a todos
los meses, como el DANE en sus cifras publicadas (el archivo de octubre de 2012 viene marcado con la
definición anterior; vea {doc}`diferencias`).

```python
>>> dd.tabla(df, por="condicion", estadistico="porcentaje").round(1)   # primer trimestre de 2024
         condicion       total  n_muestra  porcentaje
0          Ocupado  22387536.8      88396        43.6
1       Desocupado   3014781.9      14016         5.9
2         Inactivo  14504272.0      66245        28.2
3  Fuera de la PET  11450647.0      44858        22.3
```

## Empleo e ingresos

Estas variables solo tienen valor para los **ocupados**; para los demás quedan vacías (`NaN`).

| Variable | Definición | Origen |
|---|---|---|
| `formal` | 1 si está afiliado a salud **y** cotiza a pensión; 0 si no | `P6090 == 1` y `P6920 == 1` |
| `cotiza_pension` | 1 si cotiza a un fondo de pensiones | `P6920 == 1` |
| `ingreso_laboral` | Ingreso laboral mensual, en pesos corrientes, imputado por el DANE | `INGLABO` |
| `smlv` | Salario mínimo del año (para todas las personas) | `dd.SMLV` |
| `ratio_smlv` | Ingreso laboral en salarios mínimos | `ingreso_laboral / smlv` |
| `horas_semana` | Horas que trabaja normalmente a la semana en el empleo principal | `P6800` |
| `posicion_ocupacional` | Empleado particular, del gobierno, doméstico, cuenta propia, patrón… | `P6430` |
| `rama2d` | Rama de actividad a 2 dígitos de la CIIU | `RAMA2D_R4` o `RAMA2D` |
| `rama_rev` | Revisión de la CIIU de `rama2d`: 4 o 3 | La variable de origen |

```{admonition} Informalidad
:class: warning

`formal` es una definición por **seguridad social**. La tasa de informalidad oficial del DANE usa además
el tamaño de la empresa, así que las dos cifras no coinciden.
```

```{admonition} Posición ocupacional desde 2022
:class: note

Desde enero de 2022 el código 7 de `P6430` es *jornalero o peón* y el 8 *otro*; el 9 desaparece. El
diccionario oficial de 2022–2025 repite las categorías anteriores, pero los datos muestran el cambio.
`dane-data` etiqueta cada fila según su año. Vea {doc}`diferencias`.
```

La GEIH de 2007 no trae `INGLABO`, así que `ingreso_laboral` está vacío ese año.

## Categorías fijas

Las variables categóricas tienen categorías fijas, en `dd.geih.CATEGORIAS`. Así siguen siendo categóricas
después de juntar meses y años, y las tablas salen en un orden con sentido (por ejemplo, de `Ninguno` a
`Superior`):

```python
>>> dd.geih.CATEGORIAS["nivel_educativo"]
CategoricalDtype(categories=['Ninguno', 'Primaria', 'Secundaria', 'Media', 'Superior'], ordered=True, categories_dtype=str)
```

Las listas de categorías también están en `dd.geih.CONDICIONES`, `dd.geih.NIVELES_EDUC` y
`dd.geih.GRUPOS_EDAD`.

## Variables del DANE

Cualquier otra pregunta de la encuesta se puede cargar con `columns=` (vea {doc}`carga`). Para encontrar el
nombre:

```python
>>> dd.buscar_variable("arriendo")["variable"].tolist()
['P3064S1', 'P5090', 'P5130', 'P5140', 'P7495', 'P7500S1', 'P7500S1A1']
>>> dd.diccionario("geih")["P6920"]["categorias"]
{'1': 'Sí', '2': 'No', '3': 'Ya es pensionado'}
```

El diccionario es el de 2025: algunos nombres y categorías de años anteriores son distintos.
