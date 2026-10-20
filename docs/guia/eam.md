# La EAM: industria manufacturera

{dd}`eam.load()` carga la Encuesta Anual Manufacturera con **un establecimiento-año por fila**:

```python
>>> eam = dd.eam.load(range(2012, 2025))
>>> eam.shape
(104010, 30)
>>> eam[["anio", "ciiu", "ciiu_rev", "division", "sector", "departamento"]].head(3)
```

Entre 1992 y 2024 cambian el separador de los archivos, las mayúsculas de los nombres y el nombre de la
variable CIIU (`CIIU2N4`, `ciiu2`, `CIIU`, `ciiu3`, `ciiu4`, `ciiu_4`). `load` deja todos los nombres en
minúscula y agrega:

| Variable | Contenido |
|---|---|
| `anio` | Año de referencia |
| `ciiu` | Código CIIU como texto (normalmente 4 dígitos; algunos años lo publican con 2 o 3 por anonimización) |
| `ciiu_rev` | Revisión de la CIIU: 2, 3 o 4, según la variable de origen |
| `division` | Los dos primeros dígitos del código |
| `sector` | Nombre de la división (de `dd.eam.SECTORES`) |
| `departamento` | Nombre del departamento |

## Variables

Por defecto se leen las variables comparables entre años (`dd.eam.CORE`):

```{include} ../_generado/eam_variables.md
```

Los **montos están en miles de pesos corrientes**: el valor agregado total de 2024 suma unos 1,48 × 10¹¹,
es decir, unos 148 billones de pesos. Para otras variables use `columns=["c3r10c1", ...]` o
`columns="all"`, y {dd}`buscar_variable()` con `encuesta="eam"` para encontrarlas.

## Revisiones de la CIIU

| Años | Revisión | Divisiones manufactureras |
|---|---|---|
| 1992–2000 | Rev. 2 | 31–39 |
| 2001–2011 | Rev. 3 | 15–37 |
| 2012–2024 | Rev. 4 | 10–33 (en 2012 también 58, 59 y 73) |

Los códigos de una revisión no corresponden a los de otra: el `sector` «Alimentos» de la Rev. 4 (división
10) no es el mismo agregado que «Alimentos y bebidas» de la Rev. 3 (división 15). Para comparar sectores
entre revisiones hace falta una tabla correlativa. Los totales de toda la industria sí se pueden comparar.
La documentación del ANDA ubica los cambios de revisión en otros años; `dane-data` sigue lo que muestran
los archivos (vea {doc}`diferencias`).

## Anonimización: lo que los totales no muestran

Los microdatos del ANDA están anonimizados por la reserva estadística (Ley 79 de 1993, art. 5). El DANE no
publica la técnica, pero en los archivos se ven dos efectos. Ninguno cambia los totales de toda la
industria ni los de cada departamento: en 2024 el valor agregado suma 148,27 billones de pesos y hay 6 583
establecimientos, igual que en el boletín. Sí cambian los resultados por sector y por planta.

### Actividad bajo reserva: CIIU 3290

En 2012–2015 y 2018–2024 varios establecimientos aparecen con CIIU **3290** («Otras industrias
manufactureras n.c.p.») en lugar de su actividad. En 2016–2017 la actividad se protege de otra forma: el
código se publica truncado a 2 o 3 dígitos (`110`, `29`...), que conserva la división.

| Años | Cómo se protege la actividad | Bebidas (% del valor agregado) | División 32 (% del valor agregado) |
|---|---|---|---|
| 2012–2015 | Código 3290 | 3,9–5,1 | 11,9–12,9 |
| 2016–2017 | Código truncado a 2–3 dígitos | 10,0–10,3 | 3,3–3,8 |
| 2018–2024 | Código 3290 | 4,2–5,8 | 9,3–14,2 |

El boletín de 2024 da a bebidas el 9,7 % del valor agregado y no pone a «otras manufacturas» entre los
grupos principales. Así, con `sector` o `division`:

- «Otras manufacturas» queda inflada y bebidas subestimada, salvo en 2016–2017.
- Las series por sector tienen saltos que no ocurrieron: la división 32 pasa de 3,4 a 13,4 billones de
  pesos de valor agregado entre 2017 y 2018.
- Un mismo establecimiento puede cambiar de sector. Los dos de la refinería de Cartagena (`nordest` 867619 y
  981842) son 1921 (refinación) en 2014–2017 y 3290 desde 2018; en 2024 suman el 18 % de los activos fijos
  de la industria. La de Barrancabermeja sigue como 1921.

Para encontrar los establecimientos afectados en sus datos:

```python
eam = dd.eam.load(range(2012, 2025))
truncado = eam["ciiu"].str.len() < 4
# 3290 en algún año y otro código de 4 dígitos en otro: casi seguro bajo reserva
otro = eam[(eam["ciiu"] != "3290") & ~truncado].groupby("nordest")["ciiu"].last()
reservado = (eam["ciiu"] == "3290") & eam["nordest"].isin(otro.index)
```

Un establecimiento que siempre tuvo 3290 puede ser de otras manufacturas o estar bajo reserva todos los
años; los datos no permiten distinguirlos. Para un análisis por sector, compare con los años 2016–2017 o
con el boletín del DANE, y prefiera los resultados por departamento, que no se alteran.

### Valores promediados en grupos de establecimientos

En todos los años, entre 13 % y 25 % de los registros vienen en grupos (casi siempre de 3, a veces de 2 a 11)
de establecimientos distintos que tienen **exactamente los mismos valores** en las variables numéricas
(25 % en 2022–2024). Dentro de cada grupo el departamento y el CIIU son los mismos, pero `nordest` y casi
siempre `nordemp` son distintos: no son duplicados. Los grupos se concentran en celdas pequeñas de
departamento y actividad y en plantas grandes. Es el patrón de una microagregación: cada planta recibe el
promedio de su grupo, lo que conserva las sumas. Algunos archivos lo delatan, porque traen valores como
`83779570,6666667`, el promedio de tres números enteros. El DANE no lo ha confirmado.

Consecuencias:

- **Agregados** ({dd}`eam.resumen()`, {dd}`eam.participacion()`, totales por año, sector o departamento):
  no se afectan.
- **Análisis por planta** (productividad por establecimiento y su dispersión, funciones de producción,
  markups, mala asignación): una cuarta parte de las plantas tiene el promedio de su grupo, así que la
  varianza entre plantas queda subestimada y las estimaciones se sesgan.
- **Panel y crecimiento por planta**: el valor de una planta agrupada cambia cuando cambian los otros
  miembros de su grupo, de modo que su «crecimiento» mezcla plantas distintas. {dd}`eam.supervivencia()`
  no se afecta: los identificadores son reales.

Para marcar los registros agrupados:

```python
num = ["valagri", "prodbr2", "consin2", "pertotal", "activfi", "salpeyte", "eelec", "invebrta"]
eam["grupo"] = eam.groupby(["anio", "dpto", "ciiu", *num], dropna=False).ngroup()
eam["microagregado"] = (eam.groupby("grupo")["grupo"].transform("size") > 1) & eam["valagri"].fillna(0).ne(0)
```

y repita el análisis por planta sin ellos o con una variable que los identifique.

## Agregados industriales

{dd}`eam.resumen()` suma los establecimientos de cada grupo y calcula los indicadores derivados:

```python
>>> res = dd.eam.resumen(eam, por="anio")
>>> res[["anio", "establecimientos", "personal_total", "productividad_laboral",
...      "participacion_laboral"]].tail(4).round(1)
    anio  establecimientos  personal_total  productividad_laboral  participacion_laboral
9   2021              7138        681246.0               171697.9                   19.6
10  2022              6775        710060.0               210122.1                   16.7
11  2023              6714        718730.0               207094.9                   19.2
12  2024              6583        730236.0               203039.1                   21.7
```

| Columna | Cálculo |
|---|---|
| `produccion_bruta`, `consumo_intermedio`, `valor_agregado`, `ventas`, `activos_fijos`, `inversion_bruta` | Sumas, en miles de pesos |
| `personal_total`, `empleados_perm_temp` | Personas |
| `remuneraciones` | Salarios más prestaciones de permanentes y temporales (`salpeyte + prespyte`) |
| `productividad_laboral` | Valor agregado por persona ocupada (miles de pesos) |
| `remuneracion_media` | Remuneraciones por empleado permanente o temporal |
| `participacion_laboral` | Remuneraciones / valor agregado × 100 |
| `tasa_valor_agregado` | Valor agregado / producción bruta × 100 |
| `establecimientos`, `empresas` | Número de `nordest` y `nordemp` distintos |

Las definiciones están también en el {doc}`../glosario`.

```python
dd.eam.resumen(eam, por=["anio", "sector"])
dd.eam.resumen(eam[eam.anio == 2024], por="departamento")
```

### Participación y crecimiento

```python
# Qué parte del valor agregado de cada año genera cada sector
dd.eam.participacion(eam, variable="valagri", por="sector")
```

```python
>>> dd.eam.crecimiento(res, "personal_total")[["anio", "personal_total", "crec_personal_total"]].tail(3).round(1)
    anio  personal_total  crec_personal_total
10  2022        710060.0                  4.2
11  2023        718730.0                  1.2
12  2024        730236.0                  1.6
```

### Precios constantes

Los montos son corrientes: para comparar en el tiempo hay que deflactarlos. `dane-data` no trae
deflactores; para la industria se suele usar el índice de precios del productor (IPP) del DANE.
{dd}`eam.deflactar()` acepta un deflactor por año o por año y división:

```python
ipp = pd.Series({2022: 100.0, 2023: 105.0, 2024: 108.0})   # ilustrativo: use la serie del IPP del DANE
eam_real = dd.eam.deflactar(eam, ["valagri", "prodbr2"], ipp)          # agrega valagri_real, prodbr2_real
```

## Panel de establecimientos

{dd}`eam.panel()` indexa los datos por establecimiento y año, listo para modelos de panel (por ejemplo, con
[linearmodels](https://bashtage.github.io/linearmodels/)):

```python
>>> panel = dd.eam.panel(eam, balanceado=True)
>>> panel.index.get_level_values("nordest").nunique()
5428
```

Con `balanceado=True` solo quedan los establecimientos presentes en todos los años: aquí, 5 428 plantas
observadas de 2012 a 2024.

Antes de armar un panel largo revise que los identificadores se mantengan. El ANDA anonimiza cada catálogo
y los identificadores pueden cambiar entre años; {dd}`eam.supervivencia()` muestra cuántos
establecimientos de cada año reaparecen al siguiente:

```python
>>> dd.eam.supervivencia(eam).tail(4).round(1)
    anio  siguiente  establecimientos  siguen_al_anio_siguiente  pct_siguen
8   2020       2021              7343                      7094        96.6
9   2021       2022              7138                      6711        94.0
10  2022       2023              6775                      6605        97.5
11  2023       2024              6714                      6420        95.6
```

Una caída brusca de `pct_siguen` suele indicar un cambio de identificadores, no el cierre de plantas.
Además, hasta una de cada cuatro plantas trae el promedio de su grupo y no sus propios valores, y algunas cambian
de sector por la reserva estadística: vea [Anonimización](#anonimización-lo-que-los-totales-no-muestran)
antes de estimar con el panel.
