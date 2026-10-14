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
