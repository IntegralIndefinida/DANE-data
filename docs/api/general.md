# `dd`: funciones generales

```{eval-rst}
.. currentmodule:: dane_data
```

## Carpetas de datos

Dónde están (o estarán) los microdatos. Vea {doc}`../guia/datos`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   set_paths
   get_path
   show_paths
```

## Tablas y estadísticas ponderadas

Vea {doc}`../guia/ponderacion` y {doc}`../guia/tablas`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   tabla
   weighted_mean
   weighted_quantile
```

## Diccionario de variables

Los diccionarios oficiales (DDI) del ANDA, tal como los publica el DANE. Vea {doc}`../guia/variables`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   buscar_variable
   describir
   diccionario
```

## Datos de referencia

| Nombre | Contenido |
|---|---|
| `dd.SMLV` | Salario mínimo legal mensual vigente por año, en pesos corrientes (`{año: valor}`), 1992–2026, tomado de los decretos |
| `dd.DEPARTAMENTOS` | Código DIVIPOLA del departamento → nombre (`{5: "Antioquia", 8: "Atlántico", ...}`) |
| `dd.MESES` | Número del mes → nombre (`{1: "Enero", ...}`) |

## Excepciones

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   DownloadCancelled
```
