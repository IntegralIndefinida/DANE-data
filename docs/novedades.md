# Novedades

## Sin publicar

**Al actualizar**

* `formal` y `tasa_informalidad` siguen ahora la medición de informalidad del DANE (17.ª CIET), con el
  código SAS que el DANE publica en el anexo de *Empleo informal y seguridad social*: los ocupados formales e
  informales de cada mes desde 2022 coinciden con los publicados. Antes `formal` era una aproximación por
  seguridad social (afiliado a salud y cotizando a pensión), que contaba como cubiertos en salud al régimen
  subsidiado y a los beneficiarios, y como informales a los pensionados y a todos los independientes sin
  pensión. La medición necesita preguntas del cuestionario de 2022, así que antes de 2022 `formal` y
  `tasa_informalidad` quedan vacías; la guía de {doc}`guia/variables` explica cómo armar la aproximación
  anterior para series largas. `load` lee 17 variables más del DANE, y la caché de cada mes se vuelve a
  crear una vez.
* Nueva columna `formal_marco2005` y nueva `tasa_informalidad_marco2005` en {dd}`geih.indicadores()` y
  {dd}`geih.serie_indicadores()`: la medición anterior del DANE (marco 2005, empresas de hasta 5 personas),
  para 2007–2021. Coincide con la que el DANE publicó para 13 y 23 ciudades en cada trimestre móvil de
  2007–2019 y 2021. La aplicación la ofrece como «Tasa de informalidad (medición anterior, hasta 2021)».
  Queda vacía en marzo y abril de 2020 y en el total de 2020: unos tres cuartos de los ocupados de esos
  meses no tienen tamaño de empresa, por el operativo telefónico.
* {dd}`geih.serie_indicadores()` ya no devuelve la fila del grupo vacío al desagregar con `por`. Con
  `por="nivel_educativo"` esa fila juntaba a los menores que no responden educación: tenía una muestra
  grande y casi nadie en la PET. Para conservarla, use `dropna=False`. {dd}`geih.indicadores()` tiene el
  mismo parámetro, pero por defecto la sigue conservando, para que los grupos sumen el total.

**Descargas**

* {dd}`geih.download()` y {dd}`eam.download()` tienen `forzar=True` para volver a bajar lo que ya está en
  disco, por ejemplo si el DANE corrigió los archivos; antes había que borrar a mano las carpetas y los ZIP.
  En la terminal es `--forzar`, y en la aplicación, «Volver a bajar lo que ya está descargado». Lo nuevo
  reemplaza a lo de antes solo si se extrajo completo, y con `modules` solo en esos módulos.
* {dd}`eam.download()`: si un archivo fallaba a mitad de la extracción (disco lleno, ZIP dañado por dentro),
  los que ya se habían extraído quedaban y el año se daba por descargado. Ahora el año queda sin datos y en
  la lista de fallos, y la próxima descarga lo vuelve a intentar.

**Instalación**

* `dane-data app` sin el extra `[app]` decía «No module named streamlit»; ahora explica cómo instalarlo.
* Los lanzadores de Windows (`.exe` y `.bat`) abiertos desde dentro del zip, sin descomprimirlo, ahora
  explican que hay que extraerlo primero, en vez de «La aplicación se cerró con un error». La instalación
  recomienda descomprimir fuera de OneDrive, que se ponía a sincronizar los miles de archivos de `.venv/`.
* Las instrucciones para abrir el lanzador en Mac la primera vez se actualizaron para macOS 15 (Sequoia) y
  posteriores, que quitaron el atajo de clic derecho → *Abrir*: ahora es *Configuración del Sistema* →
  *Privacidad y seguridad* → *Abrir de todos modos*.

**Aplicación**

* *Tablas y microdatos* puede exportar los microdatos para Excel en español (columnas separadas por `;` y
  coma decimal): con la configuración regional de Colombia, Excel abría todo en una sola columna.
  {dd}`geih.exportar()` tiene para eso `sep` y `decimal`.
* *Tablas y microdatos*: la tabla con filas y columnas conserva el orden de las categorías (el nivel
  educativo va de *Ninguno* a *Superior*; antes salía en orden alfabético), y el indicador «Ganan menos de 1
  SMLV» se llama ahora «Ganan menos de 0,95 SMLV», que es lo que cuenta.
* EAM: la selección inicial de años son los últimos 10, no 11.
* Los botones de descarga (CSV, Excel y Stata) arman el archivo al hacer clic. Antes se armaban los tres en
  cada interacción con la página, aunque nadie descargara, y las tablas grandes la volvían lenta. Requiere
  Streamlit 1.52 o más reciente.

**Correcciones**

* La caché de la GEIH (`~/.cache/dane_data/geih/`) crecía sin límite: cada combinación de filtros, meses o
  columnas creaba archivos nuevos y los viejos no se borraban nunca. Ahora lo que no se usa en 90 días se
  borra solo, y {dd}`geih.clear_cache()` acepta `dias` para borrar solo lo que no se usa hace más de esos días.
* Un mes de 2007–2021 al que le faltaba una parte de un módulo (por ejemplo `Resto - Ocupados`) se daba por
  completo: los ocupados rurales quedaban como no ocupados y la desocupación nacional salía mal. Ahora el mes
  queda incompleto, con la parte que falta en `faltantes`, y la descarga lo vuelve a extraer. Todos los meses
  de la GEIH que se publican hoy traen las dos partes.
* Un mes de la GEIH al que el ZIP del DANE no le traía un módulo quedaba marcado como descargado: la
  siguiente descarga lo saltaba y terminaba sin errores. Ahora se revisa y se reporta cada vez hasta que esté
  completo; los marcadores escritos por 0.3.1 ya no cuentan, así que esos meses se revisan una vez. En la
  serie de empalme, además, un mes sin un módulo pedido no se reportaba.
* Al leer un archivo, una columna numérica con unos pocos valores de texto (hasta el 1 %) se convertía a
  número y esos valores se perdían sin aviso. Ahora se avisa con el archivo, la columna y ejemplos; en los
  archivos del DANE pasa con unos pocos códigos de `RAMA4DP8` como `"0  5"`.
* Un año o mes de numpy (`dd.geih.load(df.anio.max())`, `months=np.int64(1)`) lanzaba
  `TypeError: 'numpy.int64' object is not iterable`. Ahora se acepta en la carga, las funciones `serie_*` y
  las descargas.
* `dd.geih.load(2024, months="12")` cargaba enero y febrero: el texto se recorría letra por letra. Ahora un
  mes como texto es ese mes, como en las funciones `serie_*`.
* Con `XDG_CONFIG_HOME` o `XDG_CACHE_HOME` definidas pero vacías (o relativas), la configuración y la caché
  quedaban en la carpeta actual. Ahora se ignoran, como pide la norma XDG.
* {dd}`set_paths()` guarda las carpetas relativas (`"datos"`) completas. Antes quedaban relativas en el
  archivo de configuración y cada proceso las buscaba en su propia carpeta; la aplicación, que corre dentro
  del paquete instalado, descargaba en `site-packages`. La página de inicio ahora pide la ruta completa.
* Dos descargas del mismo año a la vez (dos pestañas, o la aplicación compartida en un aula) ya no escriben
  el mismo archivo temporal; en Windows la segunda fallaba por archivo en uso.
* Los catálogos del ANDA que encuentra la búsqueda ya no reemplazan a los verificados: solo agregan años que
  no están en la lista. Antes, un catálogo nuevo del DANE con un título parecido podía cambiar en silencio
  los datos de un año. En la EAM, además, solo se toman archivos ZIP.
* Una descarga en la que algo falló (un ZIP que no se pudo bajar, un año sin enlaces en el ANDA) se anunciaba
  como terminada con éxito. Ahora {dd}`geih.download()` y {dd}`eam.download()` devuelven la lista de lo que
  falló, `dane-data descargar` termina con código 1 y la aplicación lo muestra en vez de «Descarga
  terminada».
* Los niveles de {dd}`tabla()` y {dd}`geih.indicadores()` salían divididos por los meses equivocados si,
  después de {dd}`geih.filtrar()`, se elegían meses con `df[df.mes <= 3]`: se dividía por los 12 meses
  cargados y no por los 3 que quedan, así que un trimestre salía 4 veces más bajo. Las tasas no cambiaban.

**EAM**

* {dd}`eam.resumen()`: una planta con las prestaciones vacías perdía también sus salarios en
  `remuneraciones`, y un grupo o una variable sin ningún dato salía en 0 en vez de vacío. Con los archivos
  del DANE de 1992–2024 no cambia nada (no tienen esos vacíos), pero sí con datos propios o filtrados.
* Nueva advertencia sobre la composición por sector. Para anonimizar, el ANDA publica muchos
  establecimientos grandes con el código residual «otras industrias manufactureras» (3909, 3699 o 3290) o
  con el código truncado a 2–3 dígitos. Los totales coinciden con el DANE, pero la composición por división
  no: en 2024 la división 32 suma el 11,0 % del valor agregado en los microdatos y el 2,2 % en el anexo.
  Vea [Actividad anonimizada](guia/eam.md#actividad-anonimizada) y {doc}`guia/diferencias`. La aplicación
  lo advierte al desagregar por sector.
* Nuevas columnas `microagregado` y `grupo_microagregacion`. Cada año, los valores de 13–25 % de los
  establecimientos (la mitad del valor agregado o más) son el promedio de un grupo de establecimientos,
  casi siempre de 3, y no los propios. Sirven para agregados, no para análisis por planta. {dd}`eam.panel()`
  avisa cuántos establecimientos del panel están microagregados y los quita con
  `excluir_microagregados=True`; la página de panel de la aplicación tiene la misma opción. Vea
  [Microagregación](guia/eam.md#microagregación).

## 0.3.1 (19 de octubre de 2026)

* Windows: el zip para estudiantes trae `Abrir dane-data.exe`, un lanzador que hace lo mismo que el `.bat`
  (que sigue en el zip) y que se puede firmar; Windows no firma archivos `.bat`. Vea la
  [política de firma de código](https://github.com/IntegralIndefinida/DANE-data#política-de-firma-de-código-code-signing-policy).
* Los lanzadores de Windows instalan uv sin cambiar el `PATH` del usuario.
* Nueva sección [Desinstalar](instalacion.md#desinstalar) en la instalación.
* El repositorio trae `CITATION.cff`: en GitHub, *Cite this repository* da la cita de `dane-data` en APA y
  BibTeX (vea {doc}`citar`). El README también trae la cita.
* Aplicación: nueva página **📝 Cómo citar** (en *Herramientas*), con la cita de `dane-data` en APA y BibTeX
  con la versión instalada y la de los datos del DANE. El inicio pide citar el proyecto.

## 0.3.0 (17 de octubre de 2026)

**Al actualizar**

* La aplicación requiere Streamlit 1.51 o más reciente (`pip install "dane-data[app]"` lo actualiza). Con
  versiones anteriores, las tablas no aceptaban `width="stretch"` y cada gráfica mostraba un aviso de
  función obsoleta. Los lanzadores ya usaban una versión reciente.
* Corregido: `dd.geih.download([])` y `dd.eam.download([])` descargaban la serie entera; ahora no descargan
  nada (`None` sigue siendo "todos"). Un año que no está en el ANDA, como 2030, ya no se ignora en silencio:
  se avisa. En {dd}`geih.download()`, `modules=[]` (que bajaba todos los módulos) o un nombre mal escrito
  lanzan `ValueError`, y en la aplicación el botón de descargar se desactiva si no hay módulos elegidos.
* EAM 2024: el archivo de Stata del ANDA ya no se convierte a TXT al descargarlo; se guarda tal cual y
  {dd}`eam.load()` lo lee directamente. La conversión cambiaba los códigos por las etiquetas de valor del
  archivo, y cualquier variable con etiquetas quedaba como texto. Los TXT ya convertidos se siguen usando;
  para tener los códigos originales, borre la carpeta de 2024 y vuelva a descargar el año.

**Cifras**

* Corregido: si un filtro dejaba algún mes sin ninguna persona (un grupo pequeño), el promedio mensual de los
  niveles se dividía por menos meses y salía más alto. Ahora un mes vacío cuenta como 0, como en el promedio
  de los totales mensuales del DANE, en las funciones `serie_*` y en `dd.tabla` / {dd}`geih.indicadores()`
  después de {dd}`geih.filtrar()`, que anota los meses cargados en `df.attrs["meses_por_anio"]`. Las tasas
  no cambian. Elegir meses con `df[df.mes <= 3]` sigue contando solo esos meses.
* Corregido: en {dd}`geih.serie_indicadores()`, {dd}`geih.serie_tabla()` y
  {dd}`geih.serie_frecuencias()`, un filtro de rango (`{"edad": (15, 28)}`) y uno de valores
  (`{"edad": [15, 28]}`) compartían la caché, así que el segundo devolvía el resultado del primero. Las
  cachés anteriores se recalculan solas.
* Corregido: si un mes completo estaba en dos carpetas (por ejemplo, descomprimido dos veces), se sumaban
  las dos y el mes contaba doble. Ahora se usa una sola, con un aviso.
* Corregido: con `estadistico="porcentaje"`, las filas cuyo primer grupo estaba vacío (por ejemplo,
  `posicion_ocupacional` de quien no está ocupado) salían con porcentaje vacío en `dd.tabla` y
  {dd}`geih.serie_tabla()`. Ahora también suman 100 %.
* Corregido: {dd}`eam.crecimiento()` calculaba como anual el cambio entre años no consecutivos (por ejemplo,
  de 2015 a 2018 si faltaban los años de en medio). Ahora esa tasa queda vacía.
* {dd}`eam.deflactar()` se puede aplicar dos veces seguidas (antes fallaba por la columna `deflactor` repetida),
  y un deflactor con un año repetido lanza `ValueError` en vez de duplicar filas en silencio.
* Corregido: {dd}`geih.exportar()` sin `variables` escribía solo `anio`, `mes` y las columnas de los
  filtros. Ahora escribe todas las variables armonizadas, como dice su documentación.
* Corregido: un solo valor o nombre en vez de una lista se partía en letras. `filtros={"sexo": "Mujer"}`
  no dejaba a nadie, y `columns="P6500"` o `modules="ocupados"` no agregaban nada. Ahora valen igual que
  `["Mujer"]`, `["P6500"]` o `["ocupados"]` en {dd}`geih.load()`, {dd}`geih.load_month()`,
  {dd}`geih.filtrar()`, las funciones `serie_*`, {dd}`geih.exportar()` (`variables="fex"`),
  {dd}`eam.load()` y {dd}`eam.deflactar()`.

**Descargas**

* Las descargas ya no dejan archivos a medias: si se interrumpe la extracción (Ctrl+C, disco lleno), el
  archivo no queda con su nombre final, y un archivo de distinto tamaño que el del ZIP se vuelve a extraer.
  Antes, la próxima descarga daba el mes o el año por completo con los datos cortados.
* Si un mes del paquete anual del empalme (o un ZIP anidado de un mes) no se puede abrir, el año ya no queda
  marcado como completo y el ZIP se borra: la próxima descarga lo vuelve a bajar.
* Un ZIP dañado ya no se queda en disco para siempre: si lo descargado no es un ZIP válido (descarga
  cortada o página de error del DANE) se reintenta, y un ZIP en disco que no se puede abrir o extraer se
  borra y se vuelve a descargar.
* Con la aplicación abierta, un archivo de la GEIH reemplazado en la misma carpeta (por ejemplo, un CSV
  dañado que se vuelve a descargar) se revisa de nuevo; antes había que reiniciar la aplicación.
* Corregido: {dd}`eam.load()` fallaba con `AttributeError` si un archivo no traía la columna de departamento;
  ahora `departamento` queda vacío.

**Aplicación**

* Corregido: las páginas de la EAM en la aplicación se caían (`ValueError: ... is not in iterable`) cuando
  los años descargados no eran consecutivos, por ejemplo 2005 y 2020.
* Corregido: en la aplicación, la página de indicadores industriales se caía con `IndexError` si ningún
  establecimiento cumplía los filtros (un sector que no hay en el departamento elegido). Ahora muestra un
  aviso, como las páginas de la GEIH.
* En la aplicación, cada exportación de microdatos tiene su propio archivo (con la población y una huella
  de los filtros, meses y columnas en el nombre). Antes dos exportaciones de los mismos años con distinta
  selección se sobrescribían.
* `dane-data app --address 0.0.0.0` (para un aula) avisa al abrir que la aplicación queda en la red sin
  contraseña, y la documentación lo advierte. Las descargas solo siguen enlaces https del ANDA.
* La caché ya no puede quedar a medias: {dd}`geih.load()` también la escribe con otro nombre y la renombra
  al terminar, y los nombres temporales son únicos, así que dos personas usando la misma aplicación a la
  vez (`--address 0.0.0.0`) no escriben el mismo archivo. {dd}`geih.clear_cache()` borra también los
  temporales que dejó una escritura interrumpida.
* Los lanzadores para estudiantes usan siempre las versiones exactas de `uv.lock` (`uv run --frozen`).

**Configuración y línea de comandos**

* `dd.set_paths(..., save=True)` guarda solo las carpetas de esa llamada: las fijadas antes solo para la
  sesión ya no se vuelven permanentes. Una carpeta vacía lanza `ValueError` (antes quedaba la carpeta
  actual, `.`), un `config.json` dañado ya no hace fallar la librería y el archivo se escribe sin quedar
  nunca a medias. En la aplicación, "Guardar" solo guarda las carpetas que se cambiaron, así que ya no
  fija en el archivo las que venían de variables de entorno.
* Línea de comandos: `dane-data descargar eam` con `--modulos`, `--empalme` o `--limite`, o `descargar geih`
  con `--tic`, ya no ignora esas opciones en silencio: avisa que no aplican y no descarga. `dane-data config`
  avisa cuando una variable de entorno tiene prioridad sobre la carpeta que se acaba de guardar.

**Compatibilidad**

* Con pandas 2 (Google Colab) ya no aparecen avisos `FutureWarning` al calcular indicadores ni al
  armonizar; los resultados son los mismos.

## 0.2.2 (15 de octubre de 2026)

* **Documentación nueva** en <https://integralindefinida.github.io/DANE-data/>: guía de usuario, galería
  de ejemplos con datos reales y referencia de la API con una página por función.
* Todas las funciones públicas tienen docstrings completos (parámetros, lo que devuelven, ejemplos). Los
  ejemplos que no necesitan los microdatos se ejecutan en las pruebas.
* Corregido: con pandas 2 (el de Google Colab), descargar o cargar 2021 fallaba con
  `ValueError: Version of given Stata file is 110`. El Stata de septiembre de 2021 viene en formato 110
  (Stata 7), que pandas solo lee desde la versión 3; ahora se lee con cualquier pandas, sin perder las
  edades de más de 100 años.

## 0.2.1 (14 de octubre de 2026)

* `dane-data` está en PyPI: `pip install "dane-data[app]"`.
* Las funciones y las cifras son las mismas de la 0.2.0.

## 0.2.0 (14 de octubre de 2026)

**Si ya tenía datos de la GEIH descargados**

* Vuelva a descargar **2008, 2011 y 2021**. Los CSV que publica el DANE para 2008, 2011 y septiembre de
  2021 están dañados; ahora se baja otro formato del mismo catálogo (TXT o Stata). Mientras no se vuelvan a
  descargar, esos meses se omiten con un aviso.

**La aplicación ya no se cae con muchos años**

* Todas las tablas y gráficas de la GEIH se calculan un año a la vez y quedan guardadas: con 2007–2026, la
  primera consulta tarda alrededor de un minuto y las siguientes son instantáneas, con menos de 1 GB de
  memoria.
* En *Tablas y microdatos*, la pestaña de microdatos muestra un mes de ejemplo y exporta a CSV todos los
  meses elegidos, uno a la vez.
* Los indicadores laborales aceptan filtros (sexo, zona, edad, departamento) y selección de meses.
* La aplicación avisa cuando los años elegidos mezclan marcos muestrales.

**Cifras**

* La desocupación, la participación, la ocupación y el número de ocupados coinciden mes a mes con los anexos
  del DANE de 2007 a 2026 y en la serie de empalme 2010–2020.
* Corregido febrero de 2011: algunas personas tomaban el factor de expansión de otro módulo, y la
  desocupación daba 12,81 % en vez del 12,86 % publicado.
* Serie de empalme: octubre de 2012 venía con la definición anterior de la PET. Ahora todo el empalme usa la
  PET de 15 años o más, como lo publica el DANE.
* Posición ocupacional desde 2022 con las etiquetas que muestran los datos (código 7, jornalero o peón).
* EAM: la revisión de la CIIU se asigna según los códigos de cada archivo.

**Librería**

* Nuevas: {dd}`geih.serie_tabla()`, {dd}`geih.serie_frecuencias()`, {dd}`geih.exportar()`,
  {dd}`geih.filtrar()`, {dd}`geih.marco_muestral()` y {dd}`geih.serie_indicadores()`, que ahora acepta
  `filtros` y `meses`.
* {dd}`geih.load()` acepta `variables=[...]` para cargar solo esas columnas.
* `departamento` y `posicion_ocupacional` son categóricas.
* {dd}`geih.clear_cache()` borra también los resultados guardados por año.

## 0.1.0 (9 de octubre de 2026)

Primera versión: descarga, carga y armonización de la GEIH (2007–2026, y la serie de empalme 2010–2020) y
de la EAM (1992–2024); indicadores del mercado laboral, tablas ponderadas, agregados industriales y panel
de establecimientos; la aplicación y la línea de comandos.
