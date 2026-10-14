---
html_theme.sidebar_secondary.remove: true
---

# dane-data

:::{div} lema
**Microdatos del DANE listos para analizar.** La Gran Encuesta Integrada de Hogares (GEIH, 2007–2026) y
la Encuesta Anual Manufacturera (EAM, 1992–2024), descargadas, unidas y armonizadas, en Python o en una
aplicación en el navegador.
:::

::::{grid} auto
:gutter: 2

:::{grid-item}
```{button-ref} primeros_pasos
:ref-type: doc
:color: primary

Primeros pasos
```
:::

:::{grid-item}
```{button-ref} instalacion
:ref-type: doc
:color: secondary
:outline:

Instalación
```
:::
::::

::::{tab-set}
:::{tab-item} Python
```python
import dane_data as dd

dd.geih.download([2024, 2025])                  # del ANDA del DANE, incremental
df = dd.geih.load(2025)                         # una persona por fila, variables armonizadas
dd.geih.indicadores(df, por="sexo")             # TGP, TO, TD, informalidad, ingresos
dd.geih.serie_indicadores(range(2007, 2027))    # 20 años sin cargarlos en memoria
```
:::

:::{tab-item} Aplicación
```bash
pip install "dane-data[app]"
dane-data app      # se abre en el navegador: indicadores, tablas, gráficas y descargas
```

Para estudiantes sin Python: descargue el zip de la página de
[versiones](https://github.com/IntegralIndefinida/DANE-data/releases) y haga doble clic en el lanzador.
:::

:::{tab-item} Terminal
```bash
dane-data descargar geih --anios 2024 2025
dane-data descargar eam --anios 2022 2023 2024
dane-data estado
```
:::
::::

```{image} _static/galeria/desempleo.png
:alt: Tasa de desocupación mensual de Colombia, 2007–2026, calculada con dane-data
:class: portada-figura
```

## Lo que resuelve

::::{grid} 1 2 3 3
:gutter: 3

:::{grid-item-card} {octicon}`download` Descarga incremental
Baja los ZIP del ANDA, extrae los módulos y salta lo que ya está. Reemplaza los archivos que el ANDA
publica dañados.
:::

:::{grid-item-card} {octicon}`git-merge` Armonización 2007–2026
Une los módulos de cada mes y crea variables que significan lo mismo en todas las épocas de la encuesta.
:::

:::{grid-item-card} {octicon}`law` Ponderación como el DANE
Factores de expansión, promedios mensuales, tasas como cocientes de niveles y medianas ponderadas.
:::

:::{grid-item-card} {octicon}`shield-check` Validada mes a mes
La desocupación, la participación, la ocupación y los ocupados coinciden con los anexos del DANE desde 2007.
:::

:::{grid-item-card} {octicon}`stack` Series largas en un portátil
Calcula año por año y guarda los resultados: veinte años de microdatos sin agotar la memoria.
:::

:::{grid-item-card} {octicon}`browser` Una aplicación para clase
Indicadores, tablas y gráficas sin escribir código, con el código Python equivalente en cada página.
:::
::::

## Documentación

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Primeros pasos
:link: primeros_pasos
:link-type: doc

Un recorrido de diez minutos con datos reales: cargar, calcular indicadores, hacer tablas y graficar.
:::

:::{grid-item-card} {octicon}`book` Guía de usuario
:link: guia/index
:link-type: doc

Las encuestas, las variables armonizadas, la ponderación y los indicadores, explicados en detalle.
:::

:::{grid-item-card} {octicon}`graph` Ejemplos
:link: ejemplos/index
:link-type: doc

Análisis completos con gráficas: desempleo, brechas de género, informalidad, salario mínimo e industria.
:::

:::{grid-item-card} {octicon}`code` Referencia de la API
:link: api/index
:link-type: doc

Cada función con sus parámetros, lo que devuelve y ejemplos.
:::
::::

```{toctree}
:hidden:

instalacion
primeros_pasos
guia/index
ejemplos/index
api/index
glosario
novedades
citar
desarrollo
```
