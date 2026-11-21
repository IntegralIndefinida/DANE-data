# Validación

Las cifras de `dane-data` se comparan con las que publica el DANE. Las pruebas automáticas (`pytest`)
hacen dos tipos de comprobaciones.

## Con datos sintéticos

`tests/conftest.py` construye carpetas de la GEIH, la EAM, las Estadísticas Vitales y la EMICRON con las rarezas de cada época: archivos partidos
en Área, {term}`Cabecera` y {term}`Resto`; separadores `;` con coma decimal; codificación Latin-1; módulos en subcarpetas;
meses incompletos; archivos de texto tabulados. Las pruebas revisan que la carga, la armonización y los
cálculos den lo esperado en cada caso, que las funciones `serie_*` den exactamente lo mismo que el cálculo
con los {term}`microdatos`, y que los ejemplos de esta documentación funcionen. Corren en cada versión que se
publica.

## Con los datos reales

Si encuentran los microdatos en el computador, las pruebas comparan **cada mes** con los anexos del
mercado laboral del DANE:

| Serie | Meses | Anexo del DANE |
|---|---|---|
| Principal, 2007–2019 y 2021 (marco del censo 2005) | Todos | Anexo de diciembre de 2021 |
| Principal, 2020 y desde 2022 (marco CNPV 2018) | Todos | Anexo vigente |
| Empalme, 2010–2020 | Todos | Anexo vigente |

Se comparan la {term}`TD`, la {term}`TGP` y la TO (diferencias menores a 0,01 puntos) y el número de ocupados (diferencias
menores a 0,01 %), para el total nacional y, en el marco del CNPV 2018, también para las cabeceras y para
cada sexo. Coinciden también los promedios anuales: por ejemplo, la desocupación fue 10,5 % en 2019 y 10,2 %
en 2023.

Las únicas cifras que no se comparan son las de hombres y mujeres de abril y mayo de 2017 en el empalme,
por un defecto de los archivos del {term}`ANDA` que no tiene arreglo (vea {doc}`diferencias`).

Además, una prueba recorre toda la serie mes a mes buscando huecos y saltos bruscos: cambios de la {term}`PET` de
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

## EMICRON

Con los datos reales, las pruebas recalculan 8 507 cifras de los anexos anuales vigentes del DANE (nacional 2019–2024 y 24
ciudades 2019–2025): los cuadros A1.10 (situación en el empleo), A1.12 (sexo), B.1 (actividad), D.1 (sitio), E.1.1
(aporte a salud y pensión), F.1 (RUT), F.6 (Cámara de Comercio) e I.1 (micronegocios, personal ocupado, ventas,
consumo intermedio, valor agregado, remuneraciones, ingreso mixto y coeficiente técnico), para el total nacional, las
cabeceras, los centros poblados y rural disperso, las 24 ciudades juntas y cada una. Coinciden con una tolerancia
relativa de una milmillonésima, salvo tres diferencias de 2019 que los microdatos no permiten reproducir y que están
en {doc}`diferencias`: los montos que no trae, unos 48 549 micronegocios que el anexo clasifica en servicios y los
trabajadores remunerados (0,2 %). Las cifras están en `tests/datos/dane_emicron_publicado.csv`.

Los mismos cuadros de los anexos departamentales de 2020–2024 (los 24 departamentos y Bogotá, con `fex_dpto`): 5 330
cifras en `tests/datos/dane_emicron_departamentos.csv`, que coinciden todas salvo una errata del propio anexo (las
prestaciones de Atlántico en 2023 no cuadran con su remuneración). El DANE no publica anexos departamentales de 2019
ni de 2025.

Las cifras trimestrales no se pueden reproducir: usan factores de expansión trimestrales que no vienen en los microdatos.

## ECV e IPM

Con los datos reales de 2018–2025, las pruebas comparan los 27 indicadores de {dd}`ecv.indicadores()` con el anexo de series
de la ECV del DANE, y el IPM con los anexos de pobreza multidimensional:

| Qué | Resultado |
|---|---|
| Indicadores de la ECV, total nacional y por área (cabecera y centros poblados y rural disperso), 2018–2025 | Exactos |
| Indicadores de la ECV por departamento | A menos de 0,1 puntos; 5 cifras de 2023 y 2024 difieren entre 0,004 y 0,08 puntos |
| Las 15 privaciones y la condición de pobre, hogar por hogar, contra la base oficial del IPM (`BDATOS-IPM`) | Exactas en 2018, 2019, 2023, 2024 y 2025; en 2020, 2021 y 2022 difieren 5, 25 y 3 hogares de unos 89.000 |
| Incidencia, IPM y privaciones de los anexos: nacional, área, región y departamento | Iguales al redondeo del anexo; en 2020 y 2021, a menos de 0,15 puntos (abajo) |

**Diferencias conocidas:**

* **2020:** el DANE armó la inasistencia escolar con su base complementaria (estrategias de estudio en casa, con
  información del SIMAT), que `dane-data` baja y usa. 4 de 88.310 hogares quedan privados de más: Cauca da 28,3 % y no 28,2 %.
* **2021:** 21 de 89.203 hogares tienen otra inasistencia escolar en la base del DANE, sin que las variables publicadas
  expliquen por qué. La incidencia de dos departamentos difiere en 0,1 puntos.
* El anexo de series de 2024 trae intercambiado el uso de celular de Chocó (88,8 %) y de Córdoba (70,9 %).

Las proyecciones de población se comprueban al generarlas: las áreas suman el total del archivo, los departamentos suman el
total nacional en cada año y la serie no salta entre los archivos del DANE.

```{seealso}
El ejemplo {doc}`../ejemplos/validacion` grafica la tasa de desocupación de `dane-data` sobre la publicada
por el DANE, mes a mes desde 2007.
```
