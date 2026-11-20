# `dd.emicron`: Encuesta de Micronegocios

Microdatos de la EMICRON (2019–2025): los negocios de hasta 9 personas ocupadas de los dueños que encuentra la GEIH, un
micronegocio por fila. Vea {doc}`../guia/emicron`.

```{eval-rst}
.. currentmodule:: dane_data.emicron
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
   load_personal
   harmonize
```

## Indicadores

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   indicadores
   a_miles_anuales
```

## Constantes

| Nombre | Contenido |
|---|---|
| `MODULOS` | Los módulos de la encuesta y su nombre: `{clave: nombre}` |
| `FACTORES` | Los archivos de factores de expansión que se bajan siempre: `"fex_ajustado"` y `"fex_dpto"` |
| `ANIOS_DISPONIBLES` | Años en el ANDA |
| `CORE` | Las variables armonizadas que devuelve `load`, en orden |
| `ETIQUETAS` | Qué es cada variable de `CORE` |
| `CATEGORIAS` | Los tipos categóricos de las variables armonizadas |
| `CIUDADES` | Las 24 ciudades: `{código AREA: nombre}` |
| `CLAVE` | La clave del micronegocio: `directorio`, `secuencia_p`, `secuencia_encuesta` |
| `MONTOS` | Los montos mensuales y el módulo de donde salen |
| `GLOSARIO` | Definiciones de los indicadores |
