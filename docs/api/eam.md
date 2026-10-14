# `dd.eam`: Encuesta Anual Manufacturera

Microdatos de establecimientos industriales, 1992–2024: un establecimiento-año por fila, con los montos en
miles de pesos corrientes. Vea {doc}`../guia/eam`.

```{eval-rst}
.. currentmodule:: dane_data.eam
```

## Descarga

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   download
   available
   find_files
```

## Carga y armonización

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   load
   harmonize
```

## Agregados industriales

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   resumen
   participacion
   crecimiento
   deflactar
```

## Panel de establecimientos

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   panel
   supervivencia
```

## Constantes

| Nombre | Contenido |
|---|---|
| `ANIOS_DISPONIBLES` | Años con catálogo conocido en el ANDA (1992–2024) |
| `VARIABLES_COMUNES` | Variables presentes en todos los años 1992–2024 |
| `CORE` | `VARIABLES_COMUNES` más las que existen desde 2000; es lo que `load` lee por defecto |
| `ETIQUETAS` | Nombre legible de cada variable de `CORE` |
| `SECTORES` | Nombre de cada división CIIU, por revisión: `{revisión: {división: nombre}}` |
| `GLOSARIO` | Definiciones de los agregados; es la fuente del {doc}`../glosario` |
