# Guía de usuario

La guía explica qué hace `dane-data` y por qué, de los datos crudos del DANE a los indicadores. Cada
capítulo es independiente; si es la primera vez, empiece por {doc}`../primeros_pasos` y vuelva aquí
cuando necesite el detalle.

::::{grid} 1 1 2 2
:gutter: 3

:::{grid-item-card} {octicon}`browser` La aplicación
Indicadores, tablas y gráficas en el navegador, sin escribir código.

* {doc}`app`
:::

:::{grid-item-card} {octicon}`database` Datos
Las dos encuestas, dónde quedan los archivos y cómo descargarlos.

* {doc}`encuestas`
* {doc}`datos`
:::

:::{grid-item-card} {octicon}`table` La GEIH en Python
Cargar los microdatos, qué significa cada variable armonizada y cómo se expanden.

* {doc}`carga`
* {doc}`variables`
* {doc}`ponderacion`
:::

:::{grid-item-card} {octicon}`graph` Resultados
Indicadores del mercado laboral, tablas ponderadas y series de muchos años.

* {doc}`indicadores`
* {doc}`tablas`
* {doc}`series_largas`
:::

:::{grid-item-card} {octicon}`tools` Industria
La Encuesta Anual Manufacturera: agregados por sector y panel de establecimientos.

* {doc}`eam`
:::

:::{grid-item-card} {octicon}`shield-check` Confiabilidad
Cómo se comprueban las cifras y qué tener en cuenta al interpretarlas.

* {doc}`validacion`
* {doc}`advertencias`
* {doc}`diferencias`
:::

:::{grid-item-card} {octicon}`terminal` Línea de comandos
Descargar los datos, ver el estado y abrir la aplicación desde la terminal.

* {doc}`cli`
:::
::::

```{toctree}
:hidden:
:caption: La aplicación

app
```

```{toctree}
:hidden:
:caption: Datos

encuestas
datos
```

```{toctree}
:hidden:
:caption: La GEIH en Python

carga
variables
ponderacion
```

```{toctree}
:hidden:
:caption: Resultados

indicadores
tablas
series_largas
```

```{toctree}
:hidden:
:caption: Industria

eam
```

```{toctree}
:hidden:
:caption: Confiabilidad

validacion
advertencias
diferencias
```

```{toctree}
:hidden:
:caption: Línea de comandos

cli
```
