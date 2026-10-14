# La aplicación

`dane-data` trae una aplicación que se abre en el navegador, pensada para clases y para quien empieza:
descarga los datos, calcula los indicadores, hace tablas y gráficas y exporta los resultados, sin escribir
código.

```bash
dane-data app
```

La primera vez tarda unos segundos; el navegador se abre solo. Para cerrarla, cierre la ventana de la
terminal (o `Ctrl+C`). Si no tiene Python, use los lanzadores del zip para estudiantes (vea
{doc}`../instalacion`).

```{figure} ../_static/app/indicadores_laborales.jpg
:alt: Página de indicadores laborales de la aplicación, con la tasa de desocupación mensual por grupo de edad
:class: captura

*Indicadores laborales*: la tasa de desocupación mensual por grupo de edad, 2023–2026.
```

## Páginas

| Página | Qué hace |
|---|---|
| 🏠 **Inicio** | Explica las encuestas, muestra qué datos hay descargados y configura las carpetas |
| 👥 **Indicadores laborales** | TD, TGP, TO, informalidad e ingresos, por sexo, edad, zona, educación o departamento; anual o mensual; con filtros |
| 🔎 **Tablas y microdatos** | Tablas ponderadas a la medida, distribución de ingresos frente al salario mínimo, vista de los microdatos y exportación a CSV |
| 🏭 **Indicadores industriales** | Producción, valor agregado, empleo, productividad y participación laboral por sector o departamento |
| 🧱 **Panel y microdatos EAM** | Panel de establecimientos (balanceado o no), supervivencia y exportación |
| ⬇️ **Descargar datos** | Elige encuesta y años y descarga, con barra de progreso y botón para cancelar |
| 📚 **Diccionario de variables** | Buscador de variables con las etiquetas y categorías oficiales del DANE |

```{figure} ../_static/app/indicadores_industriales.jpg
:alt: Página de indicadores industriales de la aplicación, con el resumen de la EAM de 2024
:class: captura

*Indicadores industriales*: el resumen de la EAM de 2024 y la evolución del valor agregado.
```

## De la aplicación a Python

Cada página muestra el **código Python equivalente** a lo que se está viendo: los mismos datos, filtros y
cálculos con la librería. Así se pasa de la aplicación a un notebook sin empezar de cero.

Cada tabla se descarga en **CSV, Excel o Stata**.

## Cómo calcula

La aplicación usa la misma librería, con las funciones que trabajan año por año
({dd}`geih.serie_indicadores()`, {dd}`geih.serie_tabla()`, {dd}`geih.serie_frecuencias()`): nunca tiene más
de un año de microdatos en memoria y funciona en computadores modestos con toda la serie 2007–2026. La
primera consulta de una combinación nueva tarda unos segundos por año; las siguientes son instantáneas (vea
{doc}`series_largas`).

Cuando los años elegidos mezclan marcos muestrales de la GEIH, la aplicación lo advierte (vea
{doc}`encuestas`).

## En un aula

El profesor puede servir la aplicación desde su computador y los estudiantes entran desde la red local:

```bash
dane-data app --address 0.0.0.0
```

Los estudiantes abren `http://<IP del profesor>:8501` en su navegador. Las demás opciones están en
{doc}`cli`.
