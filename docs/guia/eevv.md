# Estadísticas Vitales

Las Estadísticas Vitales (EEVV) son el registro de los certificados de nacimiento y de defunción de Colombia. **No son una
encuesta:** no hay muestra ni {term}`factor de expansión`. Cada fila es un hecho registrado, y los agregados son conteos.

| Tipo (`tipo=`) | Certificado | Años |
|---|---|---|
| `"defunciones"` | Defunciones no fetales | 1979–2025 |
| `"nacimientos"` | Nacidos vivos | 1998–2025 |
| `"fetales"` | Defunciones fetales | 1998–2025 |

## Descargar y cargar

```python
import dane_data as dd

dd.eevv.download(2025)                                  # los tres certificados de 2025
dd.eevv.download(range(2015, 2026), tipos="nacimientos")
dd.eevv.download()                                      # toda la serie: 1,6 GB de descarga, 3,6 GB extraídos

nac = dd.eevv.load(2025, tipo="nacimientos")
```

```text
>>> nac[["anio", "mes", "sexo", "departamento_residencia", "peso_grupo", "bajo_peso", "edad_madre", "cesarea"]].head(3)
   anio  mes    sexo departamento_residencia     peso_grupo  bajo_peso       edad_madre  cesarea
0  2025   11  Hombre                Casanare  3.000 a 3.499      False  De 25 a 29 años    False
1  2025   10  Hombre                 Bolívar  1.500 a 1.999       True  De 15 a 19 años     True
2  2025    7   Mujer                 Bolívar  3.000 a 3.499      False  De 25 a 29 años     True
```

Algunos ZIP del ANDA traen varios años (2008–2011, 2012–2013, 2017–2018): pedir un solo año baja el paquete entero, aunque
se extrae solo el año pedido. Los nacimientos de 2008–2011 pesan 192 MB.

Un año de nacimientos tiene hasta 750 000 filas, pero ocupa unos 40 MB en memoria y carga en unos 2 segundos. Para series
largas, {dd}`eevv.serie_indicadores()` y {dd}`eevv.serie_conteos()` leen un año a la vez y guardan los resultados en disco.

## Variables armonizadas

Las variables en minúscula las crea `dane-data` y significan lo mismo en todos los años. `load` devuelve solo estas, porque
las originales ocupan mucho más. Para agregar variables del DANE, use `columns=["HORA", "GRU_ED1"]` o `columns="all"`; las
puede buscar en {dd}`buscar_variable()` con `encuesta="eevv_defunciones"`, `"eevv_nacimientos"` o `"eevv_fetales"`.

### Defunciones

```{include} ../_generado/eevv_variables_defunciones.md
```

### Nacimientos

```{include} ../_generado/eevv_variables_nacimientos.md
```

### Defunciones fetales

```{include} ../_generado/eevv_variables_fetales.md
```

## Indicadores

{dd}`eevv.indicadores()` da conteos y porcentajes por grupo. Los porcentajes se calculan sobre quienes tienen el dato, salvo
los de la ficha metodológica del DANE, que van sobre el total como en ella: partos en institución de salud y cuatro o más
consultas prenatales sobre todos los nacidos vivos, y causas mal definidas sobre todas las defunciones.

```text
>>> dd.eevv.indicadores(nac, por="edad_madre")[["edad_madre", "nacimientos", "pct_bajo_peso", "pct_prematuro", "pct_cesarea"]].round(1)
        edad_madre  nacimientos  pct_bajo_peso  pct_prematuro  pct_cesarea
0  De 10 a 14 años         2967           16.4           18.2         51.6
1  De 15 a 19 años        59104           12.4           12.3         46.7
2  De 20 a 24 años       114433           10.9           10.9         49.9
3  De 25 a 29 años       117656           10.1           10.4         53.8
4  De 30 a 34 años        88219           10.6           11.0         58.4
5  De 35 a 39 años        45317           11.5           12.0         61.8
6  De 40 a 44 años        12198           14.6           14.1         64.0
7  De 45 a 49 años          811           17.6           18.7         64.0
8  De 50 a 54 años           72           26.5           19.4         46.2
9  Sin información          760            NaN            NaN          NaN
```

{dd}`eevv.serie_indicadores()` hace lo mismo año por año, sin tener todo en memoria:

```text
>>> r = dd.eevv.serie_indicadores(range(2019, 2026))
>>> r[["anio", "defunciones", "menores_un_anio", "neonatales", "maternas", "maternas_tardias", "homicidios"]]
   anio  defunciones  menores_un_anio  neonatales  maternas  maternas_tardias  homicidios
0  2019       244355           7291.0      4452.0     326.0             193.0     13077.0
1  2020       300853           6368.0      4196.0     414.0             224.0     12415.0
2  2021       363089           6751.0      4361.0     513.0             214.0     14457.0
3  2022       287251           6689.0      4177.0     280.0             181.0     14490.0
4  2023       268411           5610.0      3461.0     242.0             171.0     14323.0
5  2024       275778           4759.0      2983.0     207.0             147.0     14155.0
6  2025       284254           4526.0      2988.0     200.0             151.0     15003.0
```

`maternas` son las muertes maternas de la razón de mortalidad materna del DANE: causa básica del capítulo O de la CIE-10, salvo
O96 (tardías, de 43 días a un año) y O97 (secuelas). Los cuadros 7 y 8 de defunciones maternas del DANE sí cuentan todo el
capítulo: en 2025 son 355, de las que 200 entran en la razón, 151 son tardías (`maternas_tardias`) y 4 son secuelas.

## Causas de muerte

La causa básica está en `causa_cie`, con CIE-9 hasta 1996 y CIE-10 desde 1997 (`cie_rev` dice cuál). Las agrupaciones
sirven para comparar:

| Variable | Lista | Años |
|---|---|---|
| `causa_105`, `causa_105_nombre` | Lista Colombia 105 | Toda la serie, 1979–2025: es la que sirve para series largas |
| `causa_667`, `causa_667_nombre` | Lista 6/67 de la OPS | 2008–2011 y 2014–2025 |
| `gran_causa` | Los grandes grupos de la OPS | Desde 1998, salvo en fetales 1998 |

{dd}`eevv.serie_conteos()` cuenta por cualquier variable:

```text
>>> dd.eevv.serie_conteos(2025, por="causa_105_nombre").nlargest(5, "n")[["causa_105_nombre", "n"]]
                                              causa_105_nombre      n
31                         Enfermedades isquémicas del corazón  49261
18  Enfermedades crónicas de las vías respiratorias inferiores  18187
17                              Enfermedades cerebrovasculares  17037
2                           Agresiones (homicidios) y secuelas  15003
56                                                    Neumonía  11213
```

## Tasas sobre la población

Los certificados no traen la población, así que `dane-data` incluye las proyecciones de población del DANE. {dd}`poblacion()`
las da por departamento (1985–2050) y en total nacional (1950–2070), por sexo, edad simple y área. No hay que descargar nada:

```python
>>> dd.poblacion(2018)
   anio  poblacion
0  2018   48258494
>>> dd.poblacion(2025, sexo="Mujer", edades=(15, 49))
   anio  poblacion
0  2025   14052801
```

{dd}`eevv.tasas()` las combina con los tres certificados:

```text
>>> r = dd.eevv.tasas(range(2019, 2026))
>>> r[["anio", "tasa_natalidad", "tasa_mortalidad", "tasa_global_fecundidad"]].round(2)
   anio  tasa_natalidad  tasa_mortalidad  tasa_global_fecundidad
0  2019           13.04             4.96                    1.60
1  2020           12.49             5.97                    1.52
2  2021           12.07             7.10                    1.47
3  2022           11.11             5.56                    1.36
4  2023            9.89             5.15                    1.21
5  2024            8.63             5.24                    1.06
6  2025            8.32             5.36                    1.02
>>> r[["anio", "mortalidad_infantil", "mortalidad_neonatal", "mortalidad_perinatal", "razon_mortalidad_materna"]].round(2)
   anio  mortalidad_infantil  mortalidad_neonatal  mortalidad_perinatal  razon_mortalidad_materna
0  2019                11.35                 6.93                 14.48                     50.73
1  2020                10.12                 6.67                 14.77                     65.78
2  2021                10.94                 7.07                 15.00                     83.16
3  2022                11.66                 7.28                 15.33                     48.81
4  2023                10.88                 6.71                 13.83                     46.94
5  2024                10.48                 6.57                 13.40                     45.60
6  2025                10.25                 6.77                 13.49                     45.30
```

Cada tasa sigue su ficha técnica del DANE (*Fichas técnicas de indicadores EEVV*, 2026):

* **Mortalidad infantil y neonatal**: defunciones de menores de un año, y de 0 a 27 días, por 1.000 nacidos vivos. Antes de
  1998 la neonatal queda vacía, porque los grupos de edad juntan de 7 a 29 días.
* **Mortalidad perinatal**: mortinatos y defunciones de 0 a 6 días, por 1.000 nacidos vivos más mortinatos. Un mortinato
  es una defunción fetal de 22 semanas o más, o de 500 gramos o más. Los microdatos agrupan el peso desde «menos de 1.000
  gramos», así que `mortinato` solo confirma el peso desde 1.000 y queda vacío sin gestación y con menos de 1.000 gramos
  (2 309 de las 19 620 defunciones fetales de 2025): la tasa puede quedar algo por debajo de la del DANE. Las demás
  defunciones fetales, la mayoría de menos de 22 semanas, son abortos y no entran.
* **Razón de mortalidad materna**: muertes maternas de hasta 42 días por 100.000 nacidos vivos.
* **Tasas específicas**: la fecundidad por 1.000 mujeres del grupo de edad, la mortalidad por 100.000 personas.

Se puede desagregar por `"departamento"`, `"sexo"` o `"area"`. Por sexo solo quedan la mortalidad general, la infantil y la
neonatal: los nacimientos se cuentan por el sexo del nacido, así que la natalidad, la fecundidad y la mortalidad materna no se
pueden partir así, y las defunciones fetales casi siempre tienen sexo indeterminado.
{dd}`eevv.tasas_especificas()` da las tasas por edad:

```text
>>> r = dd.eevv.tasas_especificas(2025, "nacimientos").round(2)
>>> r[["edad_madre", "nacimientos", "mujeres", "tasa"]]
        edad_madre  nacimientos  mujeres   tasa
0  De 10 a 14 años       2967.0  2016446   1.47
1  De 15 a 19 años      59104.0  2126519  27.79
2  De 20 a 24 años     114433.0  2195880  52.11
3  De 25 a 29 años     117656.0  2237801  52.58
4  De 30 a 34 años      88219.0  2139399  41.24
5  De 35 a 39 años      45317.0  1916019  23.65
6  De 40 a 44 años      12198.0  1803706   6.76
7  De 45 a 49 años        811.0  1633477   0.50
8  De 50 a 54 años         72.0  1465677   0.05
```

```{admonition} Son tasas de hechos registrados
:class: warning

No se ajustan por subregistro, así que **no tienen por qué coincidir con los indicadores demográficos que publica el DANE**,
que salen del modelo de sus proyecciones. Los años antiguos, con más subregistro, salen más bajos que los reales: al comparar
en el tiempo, parte del cambio puede ser mejor registro.
```

Reglas del cálculo:

* Por departamento y por área se usa la **residencia**: de la persona en las defunciones, de la madre en los nacimientos y en
  las defunciones fetales. Los registros sin departamento o de residentes en el extranjero quedan por fuera; por eso la suma de
  los departamentos es menor que el total nacional, que sí los incluye para coincidir con lo publicado.
* Por área se comparan «Cabecera» y «Centros poblados y rural disperso», como en las proyecciones.
* La tasa global de fecundidad suma las mujeres de 15 a 49 años. Los nacimientos sin edad de la madre no entran.
* Por sexo solo hay mortalidad general, infantil y neonatal.
* Antes de 1985 no hay población por departamento: esos años quedan sin tasa, con un aviso.

## Lo que cambia con los años

| Qué | Antes | Después | Qué hace `dane-data` |
|---|---|---|---|
| Grupos de edad (`GRU_ED1`) | 25 grupos en 1979–1997; 26 en 1998–2007 | 30 desde 2008, hasta «100 años y más» | `grupo_edad` usa los comparables: menor de 1, de 1 a 4, quinquenios y 85 o más |
| Causa básica | CIE-9 hasta 1996 | CIE-10 desde 1997 | `cie_rev`, y `causa_105` para toda la serie |
| Manera de muerte | `PMAN_MUER` y `MAN_MUER`, 1997–2018 | `P_PMAN_IRIS` desde 2019 | `manera_muerte`. No hay antes de 1997, y en 1997 no se sabe el tipo de muerte violenta |
| Área | Cabecera y resto hasta 1997 | Cabecera, centro poblado y rural disperso | `area_*`. La de residencia no existe antes de 1992 |
| Educación | 9 códigos hasta 2007 | 13 desde 2008 | `nivel_educativo` en cinco niveles comunes. Primaria completa e incompleta quedan juntas |
| Estado civil | Tres esquemas: 1979–1997, 1998–2007 y desde 2008 | | `estado_civil`. Hasta 1997, «unión libre» incluye divorciados |
| Régimen de salud | Vinculado y particular hasta 2007 | Excepción, especial y no asegurado | `regimen_salud`, desde 1998. No son las mismas categorías |
| Prematuridad | Sin dato antes de 2008, ni en 2012, 2013 y 2020 | `T_GES_AGRU_CIE` | `prematuro`. `T_GES` no sirve, porque agrupa «de 28 a 37» semanas |
| Período neonatal | Hasta 1997, `GRU_ED1` junta de 7 a 29 días | Desde 1998 separa de 7 a 27 días | `neonatal` queda vacía antes de 1998; `neonatal_precoz` (0 a 6 días) está en toda la serie |
| Fuentes | Hasta 2021, solo certificados del sector salud (RUAF-ND) | Desde 2022 también registros de la Registraduría sin contacto con el sector salud y formatos de notificación étnica (`TIPOFORMULARIO` 3 y 2) | Entran en los conteos, como en los cuadros del DANE. Los de la Registraduría no traen consultas, peso, sitio del parto ni departamento de residencia: en 2025 son 7 413 nacimientos, 1,7 % del total |

## Problemas conocidos de los archivos

* **1979 y 1980 están incompletos.** En 1979 faltan Caldas, Norte de Santander, Quindío, Risaralda, Santander y Arauca, y en
  1980 Caldas, Quindío y Risaralda traen cerca de la mitad. Los totales nacionales de esos años no son comparables.
* **Enero–junio de 1991** no separa las edades de los menores de 10 años, así que no hay mortalidad infantil de 1991.
* **La costa Caribe sube 42 % en 1983** y vuelve al año siguiente, sin explicación. **El total nacional sube 12 % en 1985**, en
  todo el país, tampoco explicado. Los datos se dejan como están.
* **Las defunciones fetales varían mucho hasta 2012** (entre 14 000 y 43 000 al año) porque el registro fue mejorando: no
  son cambios de la mortalidad.

Los detalles están en {doc}`diferencias`. `load`, `tasas` y las funciones `serie_*` avisan de los dos primeros.

## Documentos del DANE

* *Metodología General Estadísticas Vitales*, DSO-EEVV-MET-001, versión 3 (1 de septiembre de 2022). El archivo de la página
  del DANE se llama `EEVV-MET-001-V2.pdf`, pero es la versión 3.
* *Ficha metodológica Estadísticas Vitales*, DSO-EEVV-FME-001, versión 10 (2022): de ella salen los indicadores de partos en
  institución de salud, consultas prenatales, bajo peso y causas mal definidas.
* *Fichas técnicas de indicadores EEVV* (versión 1, 24 de septiembre de 2026): de ellas salen las fórmulas de {dd}`eevv.tasas()`.
* *Normas y recomendaciones para la codificación de la mortalidad materna* y *de la mortalidad fetal y neonatal* (2017).

```{seealso}
El ejemplo {doc}`../ejemplos/vitales` grafica la caída de la natalidad, la mortalidad infantil por departamento y los homicidios
desde 1980.
```
