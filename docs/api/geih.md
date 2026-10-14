# `dd.geih`: Gran Encuesta Integrada de Hogares

Microdatos de personas: mercado laboral, ingresos y características de los hogares. Serie principal
2007–2026 y serie de empalme 2010–2020 (`empalme=True`). Vea {doc}`../guia/encuestas`.

```{eval-rst}
.. currentmodule:: dane_data.geih
```

## Descarga

Vea {doc}`../guia/datos`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   download
   available
   find_months
```

## Carga y armonización

Vea {doc}`../guia/carga` y {doc}`../guia/variables`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   load
   load_month
   harmonize
   marco_muestral
   clear_cache
```

## Indicadores del mercado laboral

Vea {doc}`../guia/indicadores`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   indicadores
   serie_indicadores
```

## Tablas y distribuciones de muchos años

Vea {doc}`../guia/tablas` y {doc}`../guia/series_largas`.

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   serie_tabla
   serie_frecuencias
   tabla_de_frecuencias
```

## Filtros y exportación

```{eval-rst}
.. autosummary::
   :toctree: generated
   :nosignatures:

   filtrar
   exportar
```

## Constantes

| Nombre | Contenido |
|---|---|
| `ANIOS_DISPONIBLES` | Años de la serie principal con catálogo conocido en el ANDA |
| `ANIOS_EMPALME` | Años de la serie de empalme (2010–2020) |
| `MODULOS` | Módulos que `load` une en cada mes: `caracteristicas`, `fuerza`, `ocupados`, `no_ocupados`, `otras`, `vivienda` |
| `DEFAULT_MODULES` | Módulos que `download` baja por defecto (nombres del descargador) |
| `MODULE_PATTERNS` | Fragmentos del nombre de archivo con que `download` reconoce cada módulo |
| `CORE_RAW` | Variables DANE que `load` lee siempre, las que necesita `harmonize` |
| `VARIABLES_INDICADORES` | Variables que leen `indicadores` y `serie_indicadores` |
| `POR_PRECALCULADOS` | Desagregaciones de `serie_indicadores`: `None`, `sexo`, `zona`, `grupo_edad`, `nivel_educativo`, `departamento` |
| `POBLACIONES` | Poblaciones para `filtrar`, `serie_tabla` y `exportar`: `pet`, `fuerza_trabajo`, `ocupado`, `desocupado`, `inactivo` |
| `CONDICIONES` | Categorías de `condicion`: Ocupado, Desocupado, Inactivo, Fuera de la PET |
| `NIVELES_EDUC` | Categorías (ordenadas) de `nivel_educativo` |
| `GRUPOS_EDAD` | Categorías (ordenadas) de `grupo_edad` |
| `CATEGORIAS` | Tipos categóricos fijos de las variables armonizadas (`sexo`, `zona`, `condicion`...) |
| `MARCOS` | Marcos muestrales de los factores de expansión y su definición de PET (vea `marco_muestral`) |
| `GLOSARIO` | Definiciones de los indicadores; es la fuente del {doc}`../glosario` |
