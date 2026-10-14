# Las encuestas

`dane-data` trabaja con dos operaciones estadísticas del DANE cuyos microdatos se publican en el
[Archivo Nacional de Datos (ANDA)](https://microdatos.dane.gov.co): la Gran Encuesta Integrada de Hogares
(GEIH) y la Encuesta Anual Manufacturera (EAM).

## GEIH: Gran Encuesta Integrada de Hogares

Es la encuesta de hogares de la que salen las cifras oficiales de empleo y desempleo del país. Se hace
todos los meses: en cada mes se entrevistan entre 60 000 y 70 000 personas, que representan a toda la
población (unos 51 millones en 2024) gracias al {doc}`factor de expansión <ponderacion>`.

### Personas, hogares y viviendas

Cada registro es una persona de un hogar que vive en una vivienda. Tres variables la identifican:

| Llave | Identifica |
|---|---|
| `DIRECTORIO` | la vivienda |
| `SECUENCIA_P` | el hogar dentro de la vivienda |
| `ORDEN` | la persona dentro del hogar |

### Módulos

El DANE publica cada mes en varios archivos, uno por módulo del cuestionario. {dd}`geih.load()` los une
en una sola tabla de personas:

| Módulo (`dd.geih.MODULOS`) | Contenido | Archivos del DANE |
|---|---|---|
| `caracteristicas` | Sexo, edad, parentesco, educación, salud: una fila por persona | «Características generales», «Personas» |
| `fuerza` | Quiénes están en edad de trabajar (PET) | «Fuerza de trabajo» |
| `ocupados` | Empleo, ingresos, horas, rama, posición ocupacional | «Ocupados» |
| `no_ocupados` | Desocupados e inactivos (desde 2022 en un solo archivo) | «No ocupados», «Desocupados», «Inactivos» |
| `otras` | Otras formas de trabajo y actividades | «Otras actividades y ayudas», «Otras formas de trabajo» |
| `vivienda` | Vivienda y hogar (una fila por hogar) | «Vivienda y hogares» |

### Dominios: Cabecera y Resto

Hasta 2021 cada módulo viene partido en tres archivos: **Área** (las 13 o 23 ciudades principales),
**Cabecera** (zonas urbanas) y **Resto** (zonas rurales). Área es un subconjunto de Cabecera, así que el
total nacional es Cabecera + Resto; sumar Área contaría dos veces a las personas de las ciudades.
`dane-data` arma siempre el total nacional.

### Épocas de la encuesta

La estructura de los archivos cambia con los años. `dane-data` reconoce cada época sola:

| Años | Archivos | Factor de expansión | Marco |
|---|---|---|---|
| 2007–2019, 2021 | Un archivo por módulo y dominio; desocupados e inactivos por separado | `FEX_C_2011` | Proyecciones del censo 2005, PET de 12 años o más (10 en la zona rural) |
| 2020 | Un archivo por módulo | `FEX_C` | Proyecciones del CNPV 2018, PET de 15 años o más |
| 2022 en adelante | Un archivo por módulo; desocupados e inactivos en «No ocupados» | `FEX_C18` | Proyecciones del CNPV 2018, PET de 15 años o más |

Además cambian los nombres de algunas variables (por ejemplo, el sexo pasa de `P6020` a `P3271` en 2022 y
el nivel educativo de `P6210` a `P3042`), los separadores y la codificación de los archivos. La
{doc}`armonización <variables>` resuelve esas diferencias.

### Serie principal y serie de empalme

El **marco muestral** son las proyecciones de población con que se calculan los factores de expansión.
Cuando cambia, cambian los niveles (cuántas personas hay) y la edad mínima de la población en edad de
trabajar, así que **las cifras de marcos distintos no son comparables**: la PET salta alrededor de un 5 %
por el método, no por el mercado laboral. {dd}`geih.marco_muestral()` dice qué marco tiene cada año:

```python
>>> dd.geih.marco_muestral(2021)
'censo 2005'
>>> dd.geih.marco_muestral(2022)
'CNPV 2018'
```

Para tener series largas comparables, el DANE publica la **serie de empalme**: los años 2010–2020 vueltos
a expandir con las proyecciones del CNPV 2018 y la PET de 15 años o más. En `dane-data` se pide con
`empalme=True`:

```python
df = dd.geih.load(2015, empalme=True)
dd.geih.serie_indicadores(range(2010, 2021), empalme=True)
```

```{admonition} ¿Qué serie usar?
:class: tip

* Para un año o para comparar años del mismo marco, la **serie principal**.
* Para una serie larga hasta hoy, la **serie de empalme** de 2010 a 2020 y la **principal** desde 2022.
  En la serie principal, 2021 todavía tiene el marco del censo 2005.
* La aplicación avisa cuando los años elegidos mezclan marcos.
```

## EAM: Encuesta Anual Manufacturera

Es la encuesta anual de la industria manufacturera. Cada registro es un **establecimiento** (una planta) en
un año: entre 6 500 y 10 000 establecimientos por año entre 1992 y 2024. Trae producción, consumo
intermedio, valor agregado, empleo, salarios, activos e inversión.

* `nordest` identifica el establecimiento y `nordemp` la empresa a la que pertenece. Con ellos se arma un
  {doc}`panel <eam>`.
* Los montos están en **miles de pesos corrientes**.
* No hay factor de expansión: los agregados son sumas sobre los establecimientos.
* La actividad se clasifica con la CIIU, que cambia de revisión: Rev. 2 hasta 2000, Rev. 3 en 2001–2011 y
  Rev. 4 desde 2012. Los sectores de revisiones distintas no se pueden comparar directamente.

## Los diccionarios oficiales

`dane-data` trae los diccionarios de variables (DDI) que publica el ANDA: el de la GEIH 2025 y el de la EAM
2024. Sirven para encontrar variables sin salir de Python:

```python
>>> dd.buscar_variable("arriendo")["variable"].tolist()
['P3064S1', 'P5090', 'P5130', 'P5140', 'P7495', 'P7500S1', 'P7500S1A1']
>>> dd.describir("P6920")
'¿está ... Cotizando actualmente a un fondo de pensiones?'
```

Los diccionarios se dejan tal como los publica el DANE, aunque a veces no coincidan con los datos; esos
casos están en {doc}`diferencias`.
