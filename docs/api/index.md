# Referencia de la API

Todas las funciones públicas de la librería, agrupadas por tema. Cada nombre lleva a su página con los
parámetros, lo que devuelve y ejemplos. La {doc}`guía de usuario <../guia/index>` explica cuándo usar cada
una.

```python
import dane_data as dd
```

::::{grid} 1 1 3 3
:gutter: 3

:::{grid-item-card} `dd`
:link: general
:link-type: doc

Carpetas de datos, tablas y estadísticas ponderadas, diccionario de variables, proyecciones de población y
datos de referencia (salario mínimo, departamentos).
:::

:::{grid-item-card} `dd.geih`
:link: geih
:link-type: doc

Gran Encuesta Integrada de Hogares: descarga, carga armonizada, indicadores del mercado laboral, series
largas y exportación.
:::

:::{grid-item-card} `dd.eam`
:link: eam
:link-type: doc

Encuesta Anual Manufacturera: descarga, carga armonizada, agregados industriales y panel de
establecimientos.
:::

:::{grid-item-card} `dd.eevv`
:link: eevv
:link-type: doc

Estadísticas Vitales: descarga, carga armonizada, indicadores y tasas de natalidad, mortalidad y fecundidad.
:::

:::{grid-item-card} `dd.emicron`
:link: emicron
:link-type: doc

Encuesta de Micronegocios: descarga, carga armonizada, indicadores del cuadro I.1 del DANE e informalidad
empresarial.
:::

:::{grid-item-card} `dd.ecv`
:link: ecv
:link-type: doc

Encuesta Nacional de Calidad de Vida: descarga, carga armonizada, indicadores de la serie del DANE e Índice de
Pobreza Multidimensional.
:::

:::{grid-item-card} `dd.pobreza`
:link: pobreza
:link-type: doc

Pobreza monetaria y desigualdad: descarga, carga con el empalme del DANE, incidencia, brecha, severidad, Gini y unión
con la GEIH.
:::
::::

```{toctree}
:hidden:

general
geih
eam
eevv
emicron
ecv
pobreza
```
