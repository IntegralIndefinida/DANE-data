# Factores de expansión

La GEIH es una muestra: cada persona entrevistada representa a muchas otras. El **factor de expansión**
(`fex`) dice a cuántas. Toda cifra sobre la población (cuántos ocupados hay, qué porcentaje gana el mínimo,
cuál es el ingreso mediano) tiene que usarlo; un promedio simple de la muestra describe a los
encuestados, no al país.

## Un mes

En un mes, la suma de `fex` es la población:

```python
>>> df = dd.geih.load(2024, months=[1, 2, 3])
>>> (df.groupby("mes")["fex"].sum() / 1e6).round(2)     # millones de personas
mes
1    51.31
2    51.36
3    51.40
Name: fex, dtype: float64
```

Con $w_i$ el factor de expansión de la persona $i$, el número de personas con una característica en el mes
$m$ es

$$
N_m = \sum_{i \in m} w_i \, \mathbb{1}[\text{la persona } i \text{ tiene la característica}].
$$

## Varios meses: promedios mensuales

El factor de expansión es **mensual**. Si se juntan tres meses, la suma de `fex` es tres veces la
población:

```python
>>> round(df["fex"].sum() / 1e6, 2)
154.07
```

Por eso el DANE publica los agregados de un trimestre o de un año como el **promedio de los meses**:

$$
\bar N = \frac{1}{M} \sum_{m=1}^{M} N_m = \sum_i \frac{w_i}{M} \, \mathbb{1}[\cdot],
$$

donde $M$ es el número de meses del año en los datos. `dane-data` hace exactamente eso: divide `fex` por el
número de meses distintos de cada año (`dane_data.stats.peso_mensual_promedio`) en {dd}`tabla()`,
{dd}`geih.indicadores()` y todas las funciones `serie_*`. No hay que hacer nada a mano:

```python
>>> dd.tabla(df)            # personas en el primer trimestre de 2024 (promedio mensual)
          total  n_muestra
0  5.135724e+07     213515
```

```{admonition} Si calcula a mano
:class: warning

Con `df.groupby(...)["fex"].sum()` sobre varios meses, divida por el número de meses. Un error frecuente
es sumar `fex` de un año completo y reportar una población 12 veces mayor.
```

## Tasas

Las tasas son cocientes de niveles promedio. Por ejemplo, la tasa de desocupación de un año es

$$
\mathrm{TD} = 100 \, \frac{\bar D}{\overline{FT}},
$$

el promedio mensual de desocupados sobre el promedio mensual de la fuerza de trabajo. No es el promedio de
las doce tasas mensuales (aunque suelen ser muy parecidos). Así las publica el DANE, y así las calcula
{dd}`geih.indicadores()`.

Un trimestre se calcula igual: cargue los tres meses y pida el resultado anual.

```python
>>> dd.geih.indicadores(dd.geih.load(2024, months=[1, 2, 3]))[["tgp", "to", "td"]].round(1)
    tgp    to    td
0  63.7  56.1  11.9
```

## Varios años

Con `por` que incluye `anio`, cada año se expande por separado (promedio de sus meses). Sin `anio`, los
totales suman los promedios de cada año, lo que rara vez tiene sentido como población; los
**porcentajes, medias y medianas** sí se pueden calcular sobre varios años juntos y son exactos.

## Medias y medianas ponderadas

{dd}`weighted_mean()` y {dd}`weighted_quantile()` usan `fex` como peso:

$$
\bar y = \frac{\sum_i w_i y_i}{\sum_i w_i}, \qquad
q_p = \min \left\{ y_{(k)} : \sum_{j \le k} w_{(j)} \ge p \sum_i w_i \right\}.
$$

El cuantil es el menor valor que acumula la fracción $p$ del peso total, la misma definición de `_pctile`
en Stata. Devuelve siempre un valor observado, sin interpolar. Eso importa con los ingresos, que se
amontonan en valores redondos: la mediana del ingreso laboral de 2024 es exactamente el salario mínimo
(1 300 000 pesos), porque una gran parte de los ocupados gana justo eso.

## Tamaño de muestra

Todas las tablas traen `n_muestra`, el número de personas encuestadas detrás de cada cifra. Una cifra
expandida de un grupo con pocas observaciones (por ejemplo, un departamento pequeño en un mes) tiene mucho
error de muestreo. Como regla práctica, desconfíe de los grupos con menos de 100 observaciones. `dane-data`
no calcula errores estándar.

## La EAM no se expande

La EAM no tiene factor de expansión: cada registro es un establecimiento, y los agregados de
{dd}`eam.resumen()` son sumas.
