# Glosario

## Mercado laboral (GEIH)

Las definiciones de los indicadores que calcula {dd}`geih.indicadores()` (vienen de `dd.geih.GLOSARIO`).

```{include} _generado/glosario_geih.md
```

## Industria (EAM)

Los agregados de {dd}`eam.resumen()` (vienen de `dd.eam.GLOSARIO`).

```{include} _generado/glosario_eam.md
```

## Términos de las encuestas

```{glossary}
:sorted:

ANDA
   Archivo Nacional de Datos del DANE (<https://microdatos.dane.gov.co>), donde se publican los microdatos
   y su documentación.

DDI
   Documentación de cada catálogo del ANDA en el estándar Data Documentation Initiative: el diccionario de
   variables con etiquetas, preguntas y categorías. Vea {dd}`diccionario()`.

Factor de expansión
   Número de personas de la población que representa cada persona encuestada (`fex`). Es mensual. Vea
   {doc}`guia/ponderacion`.

Marco muestral
   Proyecciones de población con que se calculan los factores de expansión: las del censo 2005 o las del
   CNPV 2018. Las cifras de marcos distintos no son comparables. Vea {dd}`geih.marco_muestral()`.

Serie de empalme
   Los años 2010–2020 de la GEIH vueltos a expandir con el marco del CNPV 2018 y la PET de 15 años o más,
   para compararlos con los años recientes. Se usa con `empalme=True`.

Cabecera
   Zona urbana: la cabecera municipal. En la GEIH hasta 2021, cada módulo trae un archivo de Cabecera.

Resto
   Zona rural: centros poblados y rural disperso. El total nacional es Cabecera + Resto.

Área
   Las 13 o 23 ciudades principales con sus áreas metropolitanas. Es un subconjunto de Cabecera.

CIIU
   Clasificación Industrial Internacional Uniforme de las actividades económicas. La EAM usa la Rev. 2
   hasta 2000, la Rev. 3 en 2001–2011 y la Rev. 4 desde 2012.

SMLV
   Salario mínimo legal mensual vigente. Por año en `dd.SMLV`.

Microdatos
   Los registros individuales de una encuesta (una fila por persona, hogar o establecimiento), a
   diferencia de las cifras agregadas que publica el DANE.
```
