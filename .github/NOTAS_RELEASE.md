## Novedades de la versión 0.6.0

Tres fuentes nuevas del DANE, en la librería, la línea de comandos y la aplicación: la Encuesta de Micronegocios
(EMICRON, 2019–2025), la Encuesta Nacional de Calidad de Vida (ECV, 2018–2025) con el Índice de Pobreza
Multidimensional, y la pobreza monetaria (la Medición de Pobreza Monetaria y Desigualdad 2012–2025, con la serie
empalmada que publica el DANE). Todas se comprueban contra los anexos del DANE: en la pobreza monetaria coinciden las
5 644 cifras comparables del boletín de junio de 2026. La lista completa
está en [Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Nuevo**
- `dd.emicron`: la Encuesta de Micronegocios, con los indicadores del cuadro I.1 del DANE y la informalidad empresarial.
  En la aplicación, la página *Micronegocios*.
- `dd.ecv`: la Encuesta Nacional de Calidad de Vida, con los 27 indicadores de la serie del DANE y el Índice de Pobreza
  Multidimensional (`dd.ecv.ipm`, `dd.ecv.serie_ipm`). En la aplicación, la página *Calidad de vida y pobreza*.
- `dd.pobreza`: descarga (`dd.pobreza.download`, `dane-data descargar pobreza`) y carga de los hogares de 2012–2025,
  con el ingreso per cápita de la unidad de gasto, las líneas de pobreza y quién es pobre, ya calculados por el DANE.
- `empalme=True` reproduce la serie empalmada del DANE, comparable en 2012–2025: factor de empalme al marco 2018,
  líneas actualizadas de 2012–2018 e ingreso empalmado de 2021.
- `dd.pobreza.indicadores` y `dd.pobreza.serie_indicadores`: incidencia, brecha y severidad de la pobreza y la pobreza
  extrema, Gini e ingreso per cápita, nacional, por zona, gran dominio, ciudad y, con `departamental=True`, por
  departamento.
- `dd.pobreza.unir_geih`: la pobreza del hogar en cada persona de la GEIH, con su factor de expansión anual.
- `dd.weighted_gini`: el coeficiente de Gini ponderado.
- En la aplicación, la página *Pobreza monetaria*, y la pobreza en *Descargar datos* e *Inicio*.

**Al actualizar**
- `dd.tabla` deja fuera las filas con el peso vacío, con un aviso, en vez de sumarlas como cero.
- Dependencia nueva: `inflate64`, para los ZIP del ANDA comprimidos en Deflate64.
- Carpetas nuevas: `~/dane_data_datos/emicron` y `~/dane_data_datos/ecv` (`dd.set_paths(emicron=..., ecv=...)`).
- La carpeta nueva de la pobreza es `~/dane_data_datos/pobreza` (`dd.set_paths(pobreza=...)`, `DANE_DATA_POBREZA` o
  `dane-data config --pobreza`).
