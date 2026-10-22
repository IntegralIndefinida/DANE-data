# Indicadores del mercado laboral

{dd}`geih.indicadores()` calcula los indicadores que publica el DANE en su boletín de mercado laboral,
para cualquier grupo de población.

## Definiciones

La población se divide así:

```text
Población total
├── Fuera de la PET (menores de la edad mínima)
└── PET: población en edad de trabajar
    ├── Fuerza de trabajo (FT)
    │   ├── Ocupados (O)
    │   └── Desocupados (D)
    └── Inactivos: fuera de la fuerza de trabajo
```

Y los indicadores son:

| Indicador | Columna | Fórmula | Qué mide |
|---|---|---|---|
| Tasa global de participación | `tgp` | $100 \cdot FT / PET$ | Qué parte de quienes pueden trabajar participa en el mercado laboral |
| Tasa de ocupación | `to` | $100 \cdot O / PET$ | Qué parte de quienes pueden trabajar está trabajando |
| Tasa de desocupación | `td` | $100 \cdot D / FT$ | El «desempleo»: qué parte de quienes participan no consigue trabajo |
| Tasa de informalidad | `tasa_informalidad` | $100 \cdot \text{O informales} / O$ | La medición del DANE, desde 2022 (ver {doc}`variables`) |
| Tasa de informalidad, marco 2005 | `tasa_informalidad_marco2005` | $100 \cdot \text{O informales} / O$ | La medición anterior del DANE, 2007–2021 (ver {doc}`variables`) |
| Ingreso medio y mediano | `ingreso_medio`, `ingreso_mediano` | Media y mediana ponderadas de `ingreso_laboral` | Entre los ocupados con ingreso positivo, en pesos corrientes |

Cada nivel es la suma de los {doc}`factores de expansión <ponderacion>`; con varios meses, el promedio
mensual. Las definiciones de cada término están también en el {doc}`../glosario`.

## Uso

```python
>>> df = dd.geih.load(2024, months=[1, 2, 3])
>>> dd.geih.indicadores(df).round(1).T
                                      0
anio                             2024.0
pet                          39906590.7
fuerza_trabajo               25402318.6
ocupados                     22387536.8
desocupados                   3014781.9
inactivos                    14504272.0
tgp                                63.7
to                                 56.1
td                                 11.9
tasa_informalidad                  56.3
tasa_informalidad_marco2005         NaN
ingreso_medio                 1693374.4
ingreso_mediano               1300000.0
n_muestra                      213515.0
```

Los niveles están en personas y las tasas en porcentaje. `n_muestra` es el número de personas encuestadas
en el grupo.

### Por grupos

`por` acepta cualquier variable o lista de variables:

```python
dd.geih.indicadores(df, por="sexo")
dd.geih.indicadores(df, por=["zona", "nivel_educativo"])
dd.geih.indicadores(df, por="departamento")
```

### Por mes

Con `anual=False` hay un resultado por mes en vez del promedio del año (o del periodo cargado):

```python
dd.geih.indicadores(df, por="grupo_edad", anual=False)
```

### Por trimestre

El DANE publica también trimestres. Un trimestre es el promedio de sus tres meses: cargue esos meses y use
`anual=True`, como en el ejemplo de arriba (enero a marzo de 2024).

## Muchos años: `serie_indicadores`

Para series largas, {dd}`geih.serie_indicadores()` da exactamente el mismo resultado sin cargar todos los
años en memoria: calcula cada año por separado y lo guarda en disco (vea {doc}`series_largas`).

```python
>>> dd.geih.serie_indicadores(range(2019, 2026))[["anio", "tgp", "to", "td", "tasa_informalidad"]].round(1)
   anio   tgp    to    td  tasa_informalidad
0  2019  63.3  56.6  10.5                NaN
1  2020  60.4  50.4  16.5                NaN
2  2021  60.6  52.3  13.7                NaN
3  2022  63.6  56.5  11.2               57.9
4  2023  64.1  57.6  10.2               56.4
5  2024  63.9  57.4  10.2               55.9
6  2025  64.3  58.6   8.9               55.7
```

`por` puede ser `"sexo"`, `"zona"`, `"grupo_edad"`, `"nivel_educativo"` o `"departamento"`
(`dd.geih.POR_PRECALCULADOS`):

```python
>>> dd.geih.serie_indicadores(2024, por="zona")[["zona", "tgp", "to", "td", "tasa_informalidad"]].round(1)
                                  zona   tgp    to    td  tasa_informalidad
0                    Urbano (cabecera)  64.9  57.9  10.8               48.6
1  Rural (centros poblados y disperso)  60.2  55.7   7.4               83.9
```

Quien no tiene valor en la variable de `por` queda fuera: por ejemplo, el `nivel_educativo` de los menores
que no responden educación, casi todos fuera de la PET. Con `dropna=False` forman una fila con el grupo
vacío, como en {dd}`geih.indicadores()`, que los conserva por defecto para que los grupos sumen el total.

### Filtros

`filtros` restringe la población antes de calcular, con el formato de {dd}`geih.filtrar()`: una lista de
valores o un rango `(mínimo, máximo)` con los extremos incluidos.

```python
# Desempleo juvenil (15 a 28 años)
dd.geih.serie_indicadores(range(2015, 2026), filtros={"edad": (15, 28)})

# Mujeres de Bogotá, por nivel educativo
dd.geih.serie_indicadores(range(2022, 2026), por="nivel_educativo",
                          filtros={"sexo": ["Mujer"], "departamento": ["Bogotá D.C."]})

# Solo el primer semestre de cada año
dd.geih.serie_indicadores(range(2015, 2026), meses=range(1, 7))
```

Para desagregar por una variable que no está en `POR_PRECALCULADOS`, cargue los datos con las variables
necesarias y use {dd}`geih.indicadores()`:

```python
df = dd.geih.load(range(2022, 2026), variables=[*dd.geih.VARIABLES_INDICADORES, "posicion_ocupacional"])
dd.geih.indicadores(df, por="posicion_ocupacional")
```

## Comparar años

Antes de comparar años, revise que tengan el mismo **marco muestral** ({doc}`encuestas`). La TGP, la TO y
los niveles saltan entre 2021 y 2022 por el cambio de las proyecciones de población y de la edad mínima de
la PET, no por el mercado laboral. Para series largas sin saltos use la serie de empalme (2010–2020) con
`empalme=True`.

```{seealso}
* {doc}`validacion`: las cifras coinciden con las que publica el DANE.
* {doc}`../ejemplos/index`: series de desempleo, brechas de género y desempleo juvenil con gráficas.
```
