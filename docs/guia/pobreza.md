# Pobreza monetaria

La Medición de Pobreza Monetaria y Desigualdad del DANE sale de la GEIH: el DANE junta los ingresos de cada hogar, les
imputa lo que falta, los pasa a la {term}`unidad de gasto` y los compara con el costo de una canasta básica, la línea de
pobreza. `dd.pobreza` trae esos microdatos ya calculados, así que no hay que replicar las reglas de imputación del DANE: cada
hogar tiene su ingreso per cápita, las líneas de su dominio y mes, y si es pobre.

| Archivo (`archivos=`) | Qué trae | Años |
|---|---|---|
| `"hogares"` | Ingreso per cápita, líneas de pobreza, pobre, factor de expansión. Basta para los indicadores | 2012–2025 |
| `"personas"` | Los componentes del ingreso de cada persona (laboral, pensiones, transferencias…) | 2012–2025 |

## Descargar y cargar

```python
import dane_data as dd

dd.pobreza.download(2025)                           # hogares y personas de 2025
dd.pobreza.download(empalme=True)                   # toda la serie y los archivos del empalme: 1,4 GB de ZIP
dd.pobreza.download(range(2012, 2026), archivos="hogares", empalme=True)  # solo lo que necesitan los indicadores

hog = dd.pobreza.load(2025)                         # un hogar por fila
```

```text
>>> hog[["anio", "mes", "dominio", "personas", "ingreso_pc", "linea_pobreza", "pobre", "fex"]].head(3)
   anio  mes dominio  personas    ingreso_pc  linea_pobreza  pobre         fex
0  2025    1   Rural         1  1.390000e+06   308654.56309  False  182.062690
1  2025    1   Rural         3  8.402778e+05   308654.56309  False  100.707518
2  2025    1   Rural         1  3.084000e+06   308654.56309  False  175.342825
```

Un año tiene de 230 000 (2012) a 285 000 hogares (2022) y carga en uno o dos segundos. Toda la serie ocupa 3,7 GB extraída: 0,5 GB los hogares, 3,1 GB las personas y 0,1 GB el empalme. Desde 2023 el DANE publica hogares y personas en un solo
ZIP: pedir solo los hogares lo baja entero, aunque extrae solo lo pedido.

## Variables armonizadas

Las variables en minúscula las crea `dane-data` y significan lo mismo en todos los años; las llaves `DIRECTORIO` y
`SECUENCIA_P` quedan como en la GEIH. Para agregar variables del DANE, use `columns=["P5090", "NPOBRES"]` o `columns="all"`.

```{include} ../_generado/pobreza_variables.md
```

`pobre` y `pobre_extremo` se calculan del ingreso y las líneas, no se toman de `POBRE` e `INDIGENTE` del DANE (que coinciden
en todos los años publicados): así siguen valiendo cuando el empalme cambia las líneas o el ingreso.

## Dos metodologías y el empalme

Las cifras de 2012–2018 y las de 2019 en adelante no se pueden comparar tal como vienen en los microdatos:

| | 2012–2018 | 2019–2021 | 2022–2025 |
|---|---|---|---|
| Líneas de pobreza (`metodologia`) | MESEP: ENIG 2006–2007 (`"mesep"`) | Actualizadas: ENPH 2016–2017 (`"actualizacion"`) | Actualizadas |
| Marco muestral de la GEIH | Censo 2005 | Censo 2005 | CNPV 2018 |

`load` avisa cuando se juntan años de metodologías o marcos distintos. La serie que publica el DANE, comparable en 2012–2025,
es la empalmada: con `empalme=True`, `dane-data` la reproduce como el DANE.

| Años | Qué cambia con `empalme=True` |
|---|---|
| 2012–2018 | Las líneas de pobreza actualizadas del DANE para esos años (catálogo 689) y el factor de empalme al marco 2018 (`FEX_G`, catálogo 842) |
| 2019–2020 | El factor de empalme |
| 2021 | El ingreso y el factor de expansión del archivo de hogares empalmados |
| 2022–2025 | Nada: ya están en el marco 2018 |

El empalme exige que cada hogar encuentre su fila en los archivos del DANE; si no, falla en vez de dar una cifra a medias.
Con él, todos los años quedan `metodologia == "actualizacion"` y `empalmado == True`. Los archivos se bajan con
`download(empalme=True)` a `<carpeta>/datos/empalme/`.

## Indicadores

{dd}`pobreza.indicadores()` calcula la incidencia, la brecha y la severidad de la pobreza y de la pobreza extrema, el
{term}`coeficiente de Gini` y los promedios del ingreso per cápita y las líneas. Son cifras de personas: cada hogar pesa
`fex * personas`, y cada persona, también el servicio doméstico, cuenta con el ingreso per cápita de su unidad de gasto.

```python
dd.pobreza.indicadores(hog)                       # 2025, total nacional
dd.pobreza.indicadores(hog, por="grupo_dominio")  # 13 ciudades, otras cabeceras, rural
dd.pobreza.serie_indicadores(range(2012, 2026), empalme=True)
```

```text
>>> dd.pobreza.indicadores(hog)[["personas", "incidencia", "incidencia_extrema", "gini", "ingreso_pc"]].round(3)
       personas  incidencia  incidencia_extrema   gini   ingreso_pc
0  5.159008e+07      28.003               9.638  0.531  1281590.119

>>> s = dd.pobreza.serie_indicadores(range(2012, 2026), empalme=True)
>>> s[["anio", "incidencia", "incidencia_extrema", "brecha", "gini"]].round(2)
 anio  incidencia  incidencia_extrema  brecha  gini
 2012       41.04               13.02   17.39  0.55
 2013       38.72               11.45   16.13  0.55
  ...
 2020       43.14               17.25   19.88  0.55
 2021       39.67               13.69   16.55  0.56
 2022       36.63               13.80   14.71  0.56
 2023       34.62               12.64   13.58  0.55
 2024       31.79               11.69   12.59  0.55
 2025       28.00                9.64   10.73  0.53
```

Es la serie del boletín del DANE (41,0 % en 2012, 28,0 % en 2025). Si los datos mezclan años, metodologías o datos con y sin
empalme, `indicadores` pide agruparlos (`por="anio"`): un promedio de ellos no es ninguna cifra publicada.
{dd}`pobreza.serie_indicadores()` lee un año a la vez y guarda cada año armonizado en `~/.cache/dane_data/pobreza`: la
segunda vez tarda un segundo. {dd}`pobreza.clear_cache()` libera el espacio.

### Por departamento

Las cifras departamentales del DANE usan el factor de expansión departamental y, en 2021, un ingreso empalmado propio:

```python
dd.pobreza.indicadores(hog, por="departamento", departamental=True)
```

Sin `departamental=True`, agrupar por departamento usa el factor nacional y avisa. El DANE publica la serie departamental
empalmada desde 2021: con `empalme=True`, los años anteriores no tienen factor departamental y `departamental=True` da un
error. La pobreza se mide en 23 departamentos y Bogotá; los otros nueve (San Andrés, Arauca, Casanare, Putumayo y los de la
Amazonía y la Orinoquía) no están en los microdatos.

## Unir con la GEIH

Cada hogar de la medición es un hogar de la GEIH del mismo año y mes. {dd}`pobreza.unir_geih()` pega a cada persona de la
GEIH el ingreso per cápita, las líneas y si su hogar es pobre, para ver la pobreza por características que solo están en la
GEIH: ocupación, informalidad, nivel educativo.

```python
per = dd.pobreza.unir_geih(dd.geih.load(2025))
pobres = per[per.pobre.notna()]
pobres.groupby("sexo").apply(lambda d: dd.weighted_mean(d.pobre, d.fex_pobreza))
```

El peso de cada persona para estas cifras es `fex_pobreza`, el factor anual de la medición de pobreza, no `fex`, el factor
mensual de la GEIH. En enero de 2025 todas las personas de los 24 departamentos medidos encontraron su hogar; las de los otros
nueve quedan vacías. La cobertura queda en `per.attrs["union_pobreza"]` y hay un aviso si es baja.

## Línea de comandos

```bash
dane-data descargar pobreza --anios 2024 2025 --empalme
dane-data estado
```

```{seealso}
{doc}`validacion`, con la comparación contra los anexos del DANE, y {doc}`diferencias`, con lo que los microdatos
escriben distinto según el año.
```
