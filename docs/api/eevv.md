# `dd.eevv`: Estadísticas Vitales

Microdatos de los certificados de nacimiento (1998–2025), de defunción (1979–2025) y de defunción fetal (1998–2025): un
certificado por fila. Vea {doc}`../guia/eevv`.

```{eval-rst}
.. currentmodule:: dane_data.eevv
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
   causas
```

## Indicadores

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   indicadores
   serie_indicadores
   serie_conteos
   clear_cache
```

## Tasas sobre la población

Usan {dd}`poblacion()`, las proyecciones del DANE que vienen con la librería.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   tasas
   tasas_especificas
```

## Constantes

| Nombre | Contenido |
|---|---|
| `TIPOS` | Los tres certificados: `"defunciones"`, `"nacimientos"` y `"fetales"` |
| `ANIOS_DISPONIBLES` | Años de cada certificado en el ANDA: `{tipo: [años]}` |
| `CORE` | Variables del DANE que lee la armonización, por certificado |
| `ETIQUETAS` | Qué es cada variable armonizada, por certificado |
| `CATEGORIAS` | Los tipos categóricos de las variables armonizadas |
| `GRUPOS_EDAD` | Grupos de `grupo_edad`, en orden |
| `GRUPOS_EDAD_AMPLIOS` | Grupos de `grupo_edad_amplio`, en orden |
| `GRANDES_CAUSAS` | Nombre de `gran_causa` según el primer dígito de la lista de la OPS |
| `GLOSARIO` | Definiciones de los indicadores y las tasas |
