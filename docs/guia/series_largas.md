# Series largas sin agotar la memoria

Un año de la GEIH tiene del orden de 800 000 registros. Veinte años con todas las columnas no caben en la
memoria de un computador normal. `dane-data` ofrece tres formas de trabajar con muchos años.

## 1. Cargar solo las columnas necesarias

`variables` recorta cada mes antes de juntarlos, así que la memoria depende solo de las columnas que se
conservan:

```python
df = dd.geih.load(range(2007, 2027), variables=["fex", "sexo", "edad", "ocupado", "ingreso_laboral"])
```

Es la opción más flexible: después se puede calcular cualquier cosa con pandas. Para los indicadores
laborales, `dd.geih.VARIABLES_INDICADORES` tiene justo lo que necesita {dd}`geih.indicadores()`.

## 2. Resultados calculados año por año: las funciones `serie_*`

| Función | Equivale a |
|---|---|
| {dd}`geih.serie_indicadores()` | `indicadores(filtrar(load(anios), filtros), por, anual)` |
| {dd}`geih.serie_tabla()` | `dd.tabla(filtrar(load(anios), filtros, poblacion), por, variable, estadistico)` |
| {dd}`geih.serie_frecuencias()` | La distribución ponderada de una variable, de la que salen las dos anteriores |

Dan **exactamente** el mismo resultado que el camino con los microdatos (las pruebas de `dane-data` lo
comprueban), pero cargan un año a la vez y guardan el resultado de cada año en
`~/.cache/dane_data/geih/<tipo>/`. Nunca hay más de un año de microdatos en memoria.

```python
>>> res = dd.geih.serie_indicadores(range(2007, 2027), por="sexo")   # primera vez: alrededor de un minuto
>>> res = dd.geih.serie_indicadores(range(2007, 2027), por="sexo")   # después: instantáneo
```

Cada año se calcula una vez con **todas** las desagregaciones de `serie_indicadores` (total, sexo, zona,
grupo de edad, nivel educativo y departamento), anuales y mensuales. Cambiar `por` o `anual` no recalcula
nada; cambiar los filtros o los meses sí, porque es otra consulta.

### Cuándo se recalcula

El resultado guardado de un año se usa solo si no cambió nada de lo que lo produce:

* los archivos del año (tamaño y fecha de modificación de cada uno);
* la consulta: filtros, meses, población, variables;
* el código de `dane-data` (la versión y el contenido de los módulos que calculan).

Así, actualizar `dane-data`, volver a descargar un mes o cambiar un filtro dan resultados correctos sin
borrar nada a mano. {dd}`geih.clear_cache()` borra todo, por ejemplo para liberar espacio.

### Medianas de varios años

Las medias y medianas que juntan años se calculan sobre la distribución completa, no promediando las de
cada año:

```python
>>> dd.geih.serie_tabla(range(2015, 2020), variable="ingreso_laboral", estadistico="mediana",
...                     poblacion="ocupado")
```

## 3. Exportar los microdatos mes a mes

{dd}`geih.exportar()` escribe un CSV con los microdatos armonizados, leyendo y escribiendo un mes a la vez.
Sirve para llevar los datos a Stata, R o Excel, o para procesarlos por partes:

```python
filas = dd.geih.exportar(range(2007, 2027), "geih_ocupados.csv", poblacion="ocupado",
                         variables=["fex", "sexo", "edad", "departamento", "formal", "ingreso_laboral"])
```

El archivo se escribe primero con otro nombre y se renombra al terminar: nunca queda un CSV a medias.

## ¿Cuál usar?

| Necesito… | Use |
|---|---|
| Indicadores laborales (TD, TGP…) de muchos años, por sexo, zona, edad, educación o departamento | {dd}`geih.serie_indicadores()` |
| Totales, porcentajes, medias o medianas de muchos años | {dd}`geih.serie_tabla()` |
| Otros cuantiles o estadísticos de muchos años | {dd}`geih.serie_frecuencias()` |
| Un análisis propio (regresiones, variables nuevas) | {dd}`geih.load()` con `variables` |
| Los datos en otro programa | {dd}`geih.exportar()` |
