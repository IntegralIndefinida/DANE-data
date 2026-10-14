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

Carpetas de datos, tablas y estadísticas ponderadas, diccionario de variables y datos de referencia
(salario mínimo, departamentos).
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
::::

```{toctree}
:hidden:

general
geih
eam
```
