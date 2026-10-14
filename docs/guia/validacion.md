# Validación

Las cifras de `dane-data` se comparan con las que publica el DANE. Las pruebas automáticas (`pytest`)
hacen dos tipos de comprobaciones.

## Con datos sintéticos

`tests/conftest.py` construye carpetas de la GEIH y la EAM con las rarezas de cada época: archivos partidos
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

```{seealso}
El ejemplo {doc}`../ejemplos/validacion` grafica la tasa de desocupación de `dane-data` sobre la publicada
por el DANE, mes a mes desde 2007.
```
