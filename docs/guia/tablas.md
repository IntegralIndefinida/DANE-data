# Tablas ponderadas

{dd}`tabla()` hace tablas expandidas de cualquier variable: cuántas personas hay en cada grupo, cómo se
reparten, cuál es la media o la mediana de una variable numérica. Usa el factor de expansión y convierte
los totales de varios meses en promedios mensuales (vea {doc}`ponderacion`).

```python
df = dd.geih.load(2024, months=[1, 2, 3])
ocupados = df[df.ocupado == 1]
```

## Totales y porcentajes

`estadistico="total"` (el valor por defecto) da el número de personas en cada grupo, y
`estadistico="porcentaje"` la distribución de la **última** variable de `por` dentro de las demás:

```python
>>> dd.tabla(ocupados, por="posicion_ocupacional", estadistico="porcentaje").round(1)
        posicion_ocupacional      total  n_muestra  porcentaje
0        Empleado particular  9833758.4      36871        43.9
1      Empleado del gobierno   907276.2       4969         4.1
2         Empleado doméstico   680135.8       3000         3.0
3              Cuenta propia  9129209.3      37705        40.8
4         Patrón o empleador   581230.9       2201         2.6
5  Familiar sin remuneración   456075.5       1529         2.0
6           Jornalero o peón   790678.7       2090         3.5
7                       Otro     9172.0         31         0.0
```

Con dos variables, por ejemplo `por=["sexo", "posicion_ocupacional"]`, los porcentajes suman 100 dentro
de cada sexo. Para el porcentaje de cada sexo dentro de cada posición, invierta el orden:
`por=["posicion_ocupacional", "sexo"]`.

## Medias y medianas

```python
>>> dd.tabla(ocupados, por="nivel_educativo", variable="ingreso_laboral", estadistico="mediana")
  nivel_educativo    mediana  n_muestra
0         Ninguno   500000.0       2275
1        Primaria   700000.0      14938
2      Secundaria   900000.0       9276
3           Media  1200000.0      28770
4        Superior  1900000.0      29325
```

Las filas donde `variable` está vacía se descartan: aquí, los ocupados sin ingreso reportado. Por eso
`n_muestra` es el número de observaciones que entran en cada cifra.

## Cualquier pregunta de la encuesta

La tabla funciona con cualquier columna, también las variables del DANE que se cargan con `columns`:

```python
>>> df = dd.geih.load(2024, months=1, columns=["P6920"])    # P6920: ¿cotiza a pensión? 1 sí, 2 no, 3 pensionado
>>> dd.tabla(df[df.ocupado == 1], por=["sexo", "P6920"], estadistico="porcentaje").round(1)
     sexo  P6920      total  n_muestra  porcentaje
0  Hombre    1.0  5461614.6       6701        41.6
1  Hombre    2.0  7441621.8       9386        56.7
2  Hombre    3.0   220234.5        276         1.7
3   Mujer    1.0  4015180.4       5444        45.1
4   Mujer    2.0  4755881.0       6829        53.4
5   Mujer    3.0   130070.0        179         1.5
```

Y con cualquier condición que se pueda escribir en pandas. Por ejemplo, el porcentaje de ocupados que gana
alrededor de un salario mínimo:

```python
>>> con_ingreso = ocupados[ocupados.ingreso_laboral.notna()]
>>> cerca = con_ingreso.assign(cerca_del_minimo=con_ingreso.ratio_smlv.between(0.95, 1.05))
>>> dd.tabla(cerca, por="cerca_del_minimo", estadistico="porcentaje").round(1)
   cerca_del_minimo       total  n_muestra  porcentaje
0             False  18305861.3      72128        86.1
1              True   2949615.9      12456        13.9
```

En el primer trimestre de 2024, el 13,9 % de los ocupados con ingreso ganaba entre 0,95 y 1,05 salarios
mínimos.

## Muchos años: `serie_tabla`

{dd}`geih.serie_tabla()` da la misma tabla para muchos años, cargando uno a la vez y guardando el resultado
de cada año (vea {doc}`series_largas`). Recibe los años, la población y los filtros en vez del
`DataFrame`:

```python
>>> dd.geih.serie_tabla(range(2022, 2026), por=["anio", "sexo"], variable="ingreso_laboral",
...                     estadistico="mediana", poblacion="ocupado")
   anio    sexo    mediana  n_muestra
0  2022  Hombre  1000000.0     207355
1  2022   Mujer  1000000.0     156666
2  2023  Hombre  1160000.0     197631
3  2023   Mujer  1160000.0     154259
4  2024  Hombre  1300000.0     189465
5  2024   Mujer  1300000.0     149087
6  2025  Hombre  1423500.0     195535
7  2025   Mujer  1423500.0     154295
```

La mediana del ingreso laboral es exactamente el salario mínimo de cada año, para hombres y mujeres:
muchos ocupados ganan justo el mínimo. Para ver diferencias, use otros cuantiles con
{dd}`geih.serie_frecuencias()` o la media.

`poblacion` restringe a una de `dd.geih.POBLACIONES` (`"pet"`, `"fuerza_trabajo"`, `"ocupado"`,
`"desocupado"`, `"inactivo"`), y `filtros` usa el formato de {dd}`geih.filtrar()`. Con `dropna=True` se
dejan fuera las personas con valor vacío en alguna variable de `por`.

### Frecuencias: cualquier estadístico sobre varios años

{dd}`geih.serie_frecuencias()` devuelve la distribución ponderada completa de una variable: una fila por
año, grupo y valor, con su `peso`. De ella sale cualquier estadístico, también juntando años:

```python
>>> f = dd.geih.serie_frecuencias([2024, 2025], "ingreso_laboral", poblacion="ocupado")
>>> dd.weighted_quantile(f["ingreso_laboral"], f["peso"], 0.5)     # mediana de 2024 y 2025 juntos
1300000.0
>>> dd.weighted_quantile(f["ingreso_laboral"], f["peso"], 0.9)     # percentil 90
3500000.0
```

{dd}`geih.tabla_de_frecuencias()` convierte esas frecuencias en la tabla de `dd.tabla`.

## Exportar

Todo resultado es un `DataFrame` de pandas, así que se guarda con sus métodos:

```python
res = dd.geih.serie_indicadores(range(2015, 2026), por="departamento")
res.to_excel("indicadores_departamento.xlsx", index=False)
res.to_stata("indicadores_departamento.dta", write_index=False)
```

Para exportar los **microdatos** de muchos años sin cargarlos en memoria, {dd}`geih.exportar()` escribe un
CSV un mes a la vez:

```python
dd.geih.exportar(range(2015, 2026), "ocupados.csv", poblacion="ocupado",
                 variables=["fex", "sexo", "edad", "nivel_educativo", "formal", "ingreso_laboral"])
```
