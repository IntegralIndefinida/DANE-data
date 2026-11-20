## Novedades de la versión 0.6.0

La pobreza monetaria del DANE: los microdatos de la Medición de Pobreza Monetaria y Desigualdad 2012–2025, con la
serie empalmada que publica el DANE y sus indicadores, en la librería, la línea de comandos y la aplicación. Con los
microdatos reales, las 6 656 cifras comparables de los anexos del boletín de junio de 2026 coinciden. La lista completa
está en [Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Nuevo**
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
- La carpeta nueva de la pobreza es `~/dane_data_datos/pobreza` (`dd.set_paths(pobreza=...)`, `DANE_DATA_POBREZA` o
  `dane-data config --pobreza`).
