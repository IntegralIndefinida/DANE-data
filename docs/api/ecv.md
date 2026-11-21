# `dd.ecv`: Encuesta Nacional de Calidad de Vida

Microdatos de la ECV 2018–2025, un capítulo del cuestionario por archivo, y el Índice de Pobreza Multidimensional (IPM) del
DANE. Vea {doc}`../guia/ecv`.

```{eval-rst}
.. currentmodule:: dane_data.ecv
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

## Indicadores

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   indicadores
   serie_indicadores
   clear_cache
```

## Índice de Pobreza Multidimensional

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   privaciones
   ipm
   serie_ipm
```

## Constantes

| Nombre | Contenido |
|---|---|
| `MODULOS` | Los once capítulos que se descargan y se cargan |
| `UNIDADES` | Si cada capítulo es de viviendas, de hogares o de personas |
| `NIVELES` | Los niveles de `load`: `"persona"` y `"hogar"` |
| `KEYS_PERSONA` | Llaves de una persona: `DIRECTORIO`, `SECUENCIA_P` (el hogar) y `SECUENCIA_ENCUESTA` |
| `KEYS_HOGAR` | Llaves de un hogar: `DIRECTORIO` y `SECUENCIA_P` |
| `ETIQUETAS` | Qué es cada variable armonizada, por nivel |
| `CATEGORIAS` | Los tipos categóricos de las variables armonizadas |
| `GLOSARIO` | Definiciones de los indicadores |
| `PRIVACIONES` | Las 15 privaciones del IPM: `{privación: (dimensión, peso)}` |
| `MODULOS_IPM` | Los capítulos que necesita el IPM |
| `COLUMNAS_IPM` | Las variables del DANE que necesita el IPM |
| `ANIOS_DISPONIBLES` | Años de la ECV en el ANDA |
