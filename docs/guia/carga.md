# Cargar la GEIH

{dd}`geih.load()` es la puerta de entrada a los microdatos: devuelve un `DataFrame` de pandas con **una
fila por persona y mes**, los módulos ya unidos y las {doc}`variables armonizadas <variables>`.

```python
>>> import dane_data as dd
>>> df = dd.geih.load(2024, months=[1, 2, 3])
>>> df.shape
(213515, 69)
>>> df[["anio", "mes", "fex", "sexo", "edad", "condicion", "ingreso_laboral"]].head()
   anio  mes          fex    sexo  edad        condicion  ingreso_laboral
0  2024    1  2540.569858  Hombre  39.0         Inactivo              NaN
1  2024    1  2540.569858   Mujer  32.0          Ocupado        1160000.0
2  2024    1  2540.569858   Mujer   3.0  Fuera de la PET              NaN
3  2024    1  2226.841958  Hombre  39.0          Ocupado        1600000.0
4  2024    1  2226.841958  Hombre  22.0          Ocupado        1500000.0
```

Las columnas en **minúscula** las crea `dane-data` y significan lo mismo en todos los años; las de
**MAYÚSCULA** son las originales del DANE.

## Qué años y meses

```python
dd.geih.load(2025)                          # todos los meses descargados de 2025
dd.geih.load([2023, 2024], months=[1, 2, 3]) # primer trimestre de cada año
dd.geih.load(range(2015, 2020), months=12)  # diciembre de cada año
dd.geih.load(2016, empalme=True)            # serie de empalme
```

## Qué variables

Por defecto se leen las variables del DANE de `dd.geih.CORE_RAW`, las que hacen falta para armonizar. Hay
dos formas de cambiarlo:

`columns`: variables del DANE **adicionales**
: Para usar una pregunta que no está en el núcleo, búsquela con {dd}`buscar_variable()` y pídala en
  `columns`:

  ```python
  >>> dd.describir("P6500")
  'Antes de descuentos ¿cuánto ganó ... El mes pasado en este empleo?'
  >>> dd.describir("P7070")
  '¿cuánto recibio o ganó ... El mes pasado en ese segundo trabajo?'
  >>> df = dd.geih.load(2024, columns=["P6500", "P7070"])
  ```

  `columns="all"` lee todas las variables de todos los módulos (cientos de columnas).

`variables`: **conservar** solo algunas columnas
: Recorta cada mes antes de juntarlos, así que la memoria depende solo de lo que se conserva. Es la forma
  de juntar muchos años en un portátil:

  ```python
  df = dd.geih.load(range(2007, 2027), variables=["fex", "sexo", "edad", "ocupado", "ingreso_laboral"])
  ```

  `anio` y `mes` se conservan siempre. Una variable del DANE fuera del núcleo hay que pedirla en los dos
  lugares: `columns=["P6500"], variables=["fex", "P6500"]`.

Como referencia, el primer trimestre de 2024 ocupa 66 MB con las variables por defecto y 7 MB con
`variables=["fex", "sexo", "ocupado", "ingreso_laboral"]`.

## Qué hace `load` por dentro

Para cada mes:

1. **Encuentra los archivos** ({dd}`geih.find_months()`): reconoce el mes en el nombre de la carpeta,
   busca en subcarpetas, clasifica cada archivo por módulo y dominio y se queda con el total nacional
   (Cabecera + Resto).
2. **Une los módulos** ({dd}`geih.load_month()`): parte de características generales (una fila por
   persona) y le agrega las columnas nuevas de los demás módulos con la llave de persona; vivienda se une
   con la llave de hogar. Detecta solo el separador, la codificación, la coma decimal y las celdas en
   blanco.
3. **Guarda el mes en caché** como parquet en `~/.cache/dane_data/geih/`. La siguiente lectura del mismo
   mes toma menos de un segundo.
4. **Armoniza** ({dd}`geih.harmonize()`): agrega las variables en minúscula.
5. **Recorta** las columnas si se pidió `variables`.

Al final junta los meses. Las variables categóricas (`sexo`, `zona`, `condicion`…) tienen categorías
fijas (`dd.geih.CATEGORIAS`), así que siguen siendo categóricas después de juntar años distintos.

## Meses incompletos

Si a un mes le falta un módulo necesario para los indicadores laborales (por ejemplo, el de desocupados),
la tasa de desocupación de ese mes saldría 0 %. Por eso `load` **omite los meses incompletos** con un aviso:

```text
Se omiten meses incompletos: Marzo 2024 (falta desocupados). Use incluir_incompletos=True para cargarlos.
```

Los meses omitidos quedan en `df.attrs["meses_omitidos"]`, y {dd}`geih.available()` muestra qué le falta a
cada mes. Para cargarlos de todas formas (por ejemplo, si solo necesita variables de características),
`incluir_incompletos=True`. También se omiten los meses cuyos archivos tienen los
{ref}`defectos conocidos del ANDA <archivos-danados>`.

## La caché

La caché de cada mes se invalida sola si cambia algún archivo del mes (tamaño o fecha), las columnas o
módulos pedidos, o la versión de la armonización. Nunca hace falta borrarla para tener resultados
correctos; {dd}`geih.clear_cache()` sirve para liberar espacio. La carpeta se puede cambiar con la variable
de entorno `XDG_CACHE_HOME`.

## Un mes, paso a paso

Las piezas de `load` también son públicas, por si se necesita controlar cada paso:

```python
>>> meses = dd.geih.find_months(2024)
>>> meses[0].anio, meses[0].mes, meses[0].modulos
(2024, 1, ['caracteristicas', 'fuerza', 'no_ocupados', 'ocupados', 'otras', 'vivienda'])
>>> crudo = dd.geih.load_month(meses[0])     # variables del DANE, sin armonizar
>>> crudo.shape
(70648, 29)
>>> df = dd.geih.harmonize(crudo)            # + variables armonizadas
```
