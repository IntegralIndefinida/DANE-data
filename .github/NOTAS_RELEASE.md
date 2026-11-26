## Novedades de la versión 0.6.0

Tres fuentes nuevas del DANE, en la librería, la línea de comandos y la aplicación: la Encuesta de Micronegocios
(EMICRON, 2019–2025), la Encuesta Nacional de Calidad de Vida (ECV, 2018–2025) con el Índice de Pobreza
Multidimensional, y la pobreza monetaria (la Medición de Pobreza Monetaria y Desigualdad 2012–2025, con la serie
empalmada que publica el DANE). Todas se comprueban contra los anexos del DANE: en la pobreza monetaria coinciden las
5 644 cifras comparables del boletín de junio de 2026. Los parámetros de la API ahora se llaman igual en todas las
encuestas, en español, y hay varias correcciones en los ingresos de la GEIH. La lista completa está en
[Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Al actualizar**
- **Los parámetros cambian de nombre** y los de antes ya no se aceptan: el código que los pase con nombre da
  `TypeError`. Por ejemplo, `dd.geih.load(2025, months=[1, 2], columns=["P6500"])` ahora es
  `dd.geih.load(2025, meses=[1, 2], columnas=["P6500"])`. También `modules` → `modulos`, `root` → `raiz`,
  `progress` → `progreso`, `harmonize_vars` → `armonizar` y `anios` → `years` en las `serie_*`. La tabla completa está
  en Novedades. Los nombres de las funciones no cambian, y los argumentos pasados por posición siguen funcionando.
- `dd.geih.indicadores` deja fuera por defecto a quien no tiene valor en la variable de `por` (`dropna=True`), como
  `dd.geih.serie_indicadores`. Para conservar el grupo vacío, use `dropna=False`.
- `dd.tabla` deja fuera las filas con el peso vacío, con un aviso, en vez de sumarlas como cero.
- La caché de cada mes de la GEIH se vuelve a crear una vez.
- Dependencia nueva: `inflate64`, para los ZIP del ANDA comprimidos en Deflate64.
- Carpetas nuevas: `~/dane_data_datos/emicron`, `~/dane_data_datos/ecv` y `~/dane_data_datos/pobreza`
  (`dd.set_paths(emicron=..., ecv=..., pobreza=...)` o `dane-data config`).

**Nuevo**
- `dd.emicron`: la Encuesta de Micronegocios, con los indicadores del cuadro I.1 del DANE y la informalidad empresarial.
  En la aplicación, la página *Micronegocios*.
- `dd.ecv`: la Encuesta Nacional de Calidad de Vida, con los 27 indicadores de la serie del DANE y el Índice de Pobreza
  Multidimensional (`dd.ecv.ipm`, `dd.ecv.serie_ipm`). En la aplicación, la página *Calidad de vida y pobreza*.
- `dd.pobreza`: descarga (`dd.pobreza.download`, `dane-data descargar pobreza`) y carga de los hogares de 2012–2025,
  con el ingreso per cápita de la unidad de gasto, las líneas de pobreza y quién es pobre, ya calculados por el DANE.
  `empalme=True` reproduce la serie empalmada del DANE, comparable en 2012–2025.
- `dd.pobreza.indicadores` y `dd.pobreza.serie_indicadores`: incidencia, brecha y severidad de la pobreza y la pobreza
  extrema, Gini e ingreso per cápita, nacional, por zona, gran dominio, ciudad y, con `departamental=True`, por
  departamento. `dd.pobreza.unir_geih` pega la pobreza del hogar a cada persona de la GEIH.
- `dd.weighted_gini`: el coeficiente de Gini ponderado.
- `dd.buscar_variable` también encuentra las variables armonizadas (`fex`, `condicion`, `ingreso_laboral`…), y
  `dd.geih.ETIQUETAS` describe las de la GEIH.
- La EAM se compara con las cifras publicadas por el DANE (1992–2011 y 2015–2024), y `dd.eam.indicadores` es otro
  nombre de `dd.eam.resumen`.
- En la aplicación, la página *Pobreza monetaria*, y la pobreza en *Descargar datos* e *Inicio*.

**Correcciones**
- GEIH, septiembre a diciembre de 2017: `ingreso_laboral` y `ratio_smlv` salían en infinito para unos 4.500 ocupados
  por mes (las celdas vacías de esos CSV del ANDA vienen como `1.79769313486232e+308`). Los promedios de ingreso de
  2017 salían infinitos y las medianas, sesgadas hacia arriba.
- GEIH, noviembre de 2021: los CSV usan la coma para los miles. `ingreso_no_laboral` salía en 0 para casi todos, y los
  montos del DANE (`P6500`, `P7070`…) quedaban como texto o divididos por mil.
- GEIH: un monto de 999.999.999 («no informa») contaba como mil millones de pesos en `ingreso_no_laboral`, y en abril
  de 2010 en un `INGLABO`. Ahora queda vacío.
- GEIH: `cotiza_pension` contaba como que no cotiza a quien no respondió `P6920`. En marzo y abril de 2020 eran nueve
  de cada diez ocupados.
- `dd.geih.load` con módulos de nombre desconocido, o con los nombres de `download`, daba una desocupación de 0 % sin
  aviso; un filtro con un valor mal escrito devolvía una tabla vacía; `download` con los años en un generador no bajaba
  nada. Ahora fallan o funcionan, según el caso.
- Las diferencias nuevas con la documentación del DANE (`P6050` con 13 códigos desde 2022, el 9 de `P6920` en 2015,
  los formatos de 2017 y 2021) están en la guía *Diferencias con la documentación del DANE*.
