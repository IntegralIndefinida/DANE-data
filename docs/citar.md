# Cómo citar

## Los datos

Los microdatos son del DANE. Cite la encuesta y el catálogo del ANDA que usó:

> DANE. *Gran Encuesta Integrada de Hogares (GEIH)* [microdatos]. Archivo Nacional de Datos (ANDA).
> <https://microdatos.dane.gov.co>

> DANE. *Encuesta Anual Manufacturera (EAM)* [microdatos]. Archivo Nacional de Datos (ANDA).
> <https://microdatos.dane.gov.co>

> DANE. *Estadísticas Vitales (EEVV)* [microdatos]. Archivo Nacional de Datos (ANDA).
> <https://microdatos.dane.gov.co>

Si usó tasas de las Estadísticas Vitales o {dd}`poblacion()`, cite también las proyecciones de población, que
`dane-data` trae incluidas:

> DANE. *Proyecciones de población*.
> <https://www.dane.gov.co/index.php/estadisticas-por-tema/demografia-y-poblacion/proyecciones-de-poblacion>

## dane-data

Si `dane-data` le sirvió en un trabajo, puede citarlo así. En GitHub, el botón *Cite this repository* da la
misma cita en APA y BibTeX, tomada de
[`CITATION.cff`](https://github.com/IntegralIndefinida/DANE-data/blob/main/CITATION.cff). La página *Cómo citar* de
la {doc}`aplicación <guia/app>` da el BibTeX con el campo `version` de la versión instalada.

> Ramírez, L. (2026). *dane-data: microdatos del DANE (GEIH, EAM y Estadísticas Vitales) listos para analizar* (versión
> {{ version }}) [software]. <https://github.com/IntegralIndefinida/DANE-data>

```bibtex
@software{dane_data,
  author  = {Ramírez, Luis},
  title   = {dane-data: microdatos del DANE (GEIH, EAM y Estadísticas Vitales) listos para analizar},
  year    = {2026},
  url     = {https://github.com/IntegralIndefinida/DANE-data},
}
```

Mencione también las decisiones metodológicas que afecten sus resultados, por ejemplo la serie usada
(principal o de empalme) y qué medición de informalidad usó: la actual del DANE, desde 2022 (`formal`), o la
anterior, para 2007–2021 (`formal_marco2005`) (vea {doc}`guia/advertencias`).

## Licencia

El código de `dane-data` tiene licencia MIT. Los datos son del DANE y se rigen por sus condiciones de uso.
