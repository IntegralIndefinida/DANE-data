# dd.geih: Gran Encuesta Integrada de Hogares

Microdatos de personas: mercado laboral, ingresos, educación. Serie principal 2007–2026 y serie de empalme
2010–2020 (`empalme=True`).

## Descarga

```{eval-rst}
.. autofunction:: dane_data.geih.download
.. autofunction:: dane_data.geih.available
.. autofunction:: dane_data.geih.find_months
```

## Carga

```{eval-rst}
.. autofunction:: dane_data.geih.load
.. autofunction:: dane_data.geih.load_month
.. autofunction:: dane_data.geih.harmonize
.. autofunction:: dane_data.geih.marco_muestral
.. autofunction:: dane_data.geih.clear_cache
```

## Indicadores y tablas

```{eval-rst}
.. autofunction:: dane_data.geih.indicadores
.. autofunction:: dane_data.geih.serie_indicadores
.. autofunction:: dane_data.geih.serie_tabla
.. autofunction:: dane_data.geih.serie_frecuencias
.. autofunction:: dane_data.geih.tabla_de_frecuencias
```

## Filtros y exportación

```{eval-rst}
.. autofunction:: dane_data.geih.filtrar
.. autofunction:: dane_data.geih.exportar
```

## Constantes

| Nombre | Contenido |
|---|---|
| `ANIOS_DISPONIBLES`, `ANIOS_EMPALME` | Años de la serie principal y de la serie de empalme |
| `MODULOS` | Módulos que se unen en cada mes (`caracteristicas`, `fuerza`, `ocupados`…) |
| `DEFAULT_MODULES` | Módulos que `download` baja por defecto |
| `MODULE_PATTERNS` | Fragmentos de nombre de archivo con que `download` reconoce cada módulo |
| `CORE_RAW` | Variables DANE que `load` lee siempre |
| `VARIABLES_INDICADORES` | Variables que necesita `indicadores` |
| `POR_PRECALCULADOS` | Desagregaciones disponibles en `serie_indicadores` |
| `POBLACIONES` | Poblaciones para `filtrar`, `serie_tabla` y `exportar` (`pet`, `ocupado`…) |
| `CONDICIONES`, `NIVELES_EDUC`, `GRUPOS_EDAD` | Categorías de `condicion`, `nivel_educativo` y `grupo_edad` |
| `CATEGORIAS` | Tipos categóricos fijos de las variables armonizadas |
| `MARCOS` | Marcos muestrales de los factores de expansión (ver `marco_muestral`) |
| `GLOSARIO` | Definiciones de los indicadores (PET, TGP, TD…) |
