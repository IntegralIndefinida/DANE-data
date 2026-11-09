# Validación

Las cifras de `dane-data` se comparan con las que publica el DANE. Las pruebas automáticas (`pytest`)
hacen dos tipos de comprobaciones.

## Con datos sintéticos

`tests/conftest.py` construye carpetas de la GEIH, la EAM y las Estadísticas Vitales con las rarezas de cada época: archivos partidos
en Área, Cabecera y Resto; separadores `;` con coma decimal; codificación Latin-1; módulos en subcarpetas;
meses incompletos; archivos de texto tabulados. Las pruebas revisan que la carga, la armonización y los
cálculos den lo esperado en cada caso, que las funciones `serie_*` den exactamente lo mismo que el cálculo
con los microdatos, y que los ejemplos de esta documentación funcionen. Corren en cada versión que se
publica.

## Con los datos reales

Si encuentran los microdatos en el computador, las pruebas comparan **cada mes** con los anexos del
mercado laboral del DANE:

| Serie | Meses | Anexo del DANE |
|---|---|---|
| Principal, 2007–2019 y 2021 (marco del censo 2005) | Todos | Anexo de diciembre de 2021 |
| Principal, 2020 y desde 2022 (marco CNPV 2018) | Todos | Anexo vigente |
| Empalme, 2010–2020 | Todos | Anexo vigente |

Se comparan la TD, la TGP y la TO (diferencias menores a 0,01 puntos) y el número de ocupados (diferencias
menores a 0,01 %), para el total nacional y, en el marco del CNPV 2018, también para las cabeceras y para
cada sexo. Coinciden también los promedios anuales: por ejemplo, la desocupación fue 10,5 % en 2019 y 10,2 %
en 2023.

Las únicas cifras que no se comparan son las de hombres y mujeres de abril y mayo de 2017 en el empalme,
por un defecto de los archivos del ANDA que no tiene arreglo (vea {doc}`diferencias`).

Además, una prueba recorre toda la serie mes a mes buscando huecos y saltos bruscos: cambios de la PET de
más de 1 % fuera de los cambios de metodología conocidos, y cambios de las tasas de más de 5 puntos fuera de
la pandemia (abril de 2020).

## Informalidad

Con los datos reales, las pruebas comparan también los ocupados informales de cada mes con los anexos de informalidad
del DANE (diferencias menores a 0,01 %):

| Medición | Qué se compara | Anexo del DANE |
|---|---|---|
| `formal`, la actual (desde 2022) | Total nacional, cada mes | Anexo vigente de *Empleo informal y seguridad social* |
| `formal_marco2005`, la anterior (2007–2019 y 2021) | 13 y 23 ciudades, cada trimestre móvil | Anexo de octubre a diciembre de 2021 |

Coinciden todos los meses salvo febrero de 2008 en las 23 ciudades (134 informales de 4,6 millones). 2020 no se compara
con la medición anterior: sus microdatos en el ANDA vienen con las proyecciones del CNPV 2018 y el anexo con las del
censo 2005. Las reglas de cada medición están en {doc}`variables`.

## EAM

La EAM no tiene una prueba automática con datos reales. Se comparó a mano con los anexos del DANE de 1998, 2008–2011
y 2024: los totales nacionales y por departamento coinciden, pero la composición por división industrial no, porque
el ANDA oculta la actividad de muchos establecimientos grandes para anonimizarlos (vea {doc}`eam` y {doc}`diferencias`).

## Estadísticas Vitales

Con los datos reales, las pruebas comparan los tres certificados con los cuadros definitivos del DANE, y coinciden
**exactamente**, sin ninguna diferencia:

| Qué | Años |
|---|---|
| Total nacional, hombres y mujeres | 2008–2025 |
| Total de cada uno de los 33 departamentos (de residencia en nacimientos y defunciones, de ocurrencia en fetales) | 2019–2025 |
| Defunciones maternas y de menores de un año | 2025 |

También comprueban que los grupos de edad armonizados den lo mismo que los que el DANE agrupa aparte (`GRU_ED2`), y buscan
años faltantes y saltos anuales de más de 10 % fuera de los conocidos.

**Antes de 2008 no hay contraste externo:** el DANE no publica esos cuadros en su página. Esos años solo tienen la revisión de
conteos y saltos, además de las rarezas que están en {doc}`diferencias`.

Las proyecciones de población se comprueban al generarlas: las áreas suman el total del archivo, los departamentos suman el
total nacional en cada año y la serie no salta entre los archivos del DANE.

```{seealso}
El ejemplo {doc}`../ejemplos/validacion` grafica la tasa de desocupación de `dane-data` sobre la publicada
por el DANE, mes a mes desde 2007.
```
