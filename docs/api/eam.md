# dd.eam: Encuesta Anual Manufacturera

Microdatos de establecimientos industriales, 1992–2024: un establecimiento-año por fila. Los montos vienen
en miles de pesos corrientes.

## Descarga

```{eval-rst}
.. autofunction:: dane_data.eam.download
.. autofunction:: dane_data.eam.available
.. autofunction:: dane_data.eam.find_files
```

## Carga

```{eval-rst}
.. autofunction:: dane_data.eam.load
.. autofunction:: dane_data.eam.harmonize
```

## Indicadores

```{eval-rst}
.. autofunction:: dane_data.eam.resumen
.. autofunction:: dane_data.eam.participacion
.. autofunction:: dane_data.eam.crecimiento
.. autofunction:: dane_data.eam.deflactar
```

## Panel

```{eval-rst}
.. autofunction:: dane_data.eam.panel
.. autofunction:: dane_data.eam.supervivencia
```

## Constantes

| Nombre | Contenido |
|---|---|
| `ANIOS_DISPONIBLES` | Años disponibles en el ANDA |
| `CORE`, `VARIABLES_COMUNES` | Variables comparables entre años que `load` lee por defecto |
| `ETIQUETAS` | Nombre legible de cada variable |
| `SECTORES` | Nombre de cada división CIIU, por revisión (`{revisión: {división: nombre}}`) |
| `GLOSARIO` | Definiciones de los agregados (producción bruta, valor agregado…) |
