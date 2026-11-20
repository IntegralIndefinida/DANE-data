# `dd.pobreza`: pobreza monetaria y desigualdad

Microdatos de la Medición de Pobreza Monetaria y Desigualdad (2012–2025): un hogar por fila, con su ingreso per cápita,
las líneas de pobreza y si es pobre. Vea {doc}`../guia/pobreza`.

```{eval-rst}
.. currentmodule:: dane_data.pobreza
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

## Unión con la GEIH

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   unir_geih
```

## Constantes

| Nombre | Contenido |
|---|---|
| `ARCHIVOS` | Los dos archivos de cada año: `"hogares"` y `"personas"` |
| `ARCHIVOS_EMPALME` | Los archivos del empalme al marco 2018 que baja `download(empalme=True)` |
| `ANIOS_DISPONIBLES` | Años con microdatos en el ANDA |
| `CORE` | Variables del DANE que lee la armonización |
| `ETIQUETAS` | Qué es cada variable armonizada |
| `CATEGORIAS` | Los tipos categóricos de las variables armonizadas |
| `DOMINIOS` | Nombre de cada dominio del DANE en `dominio` |
| `GRUPOS_DOMINIO` | Los tres grandes dominios de `grupo_dominio` |
| `TRECE_CIUDADES` | Los dominios de las 13 ciudades y áreas metropolitanas |
| `METODOLOGIAS` | Los valores de `metodologia`: `"mesep"` y `"actualizacion"` |
| `GLOSARIO` | Definiciones de los indicadores |
| `VARIABLES_GEIH` | Las variables que `unir_geih` pega a la GEIH por defecto |
