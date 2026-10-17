# Novedades

## Sin publicar

* Corregido: {dd}`geih.exportar()` sin `variables` escribía solo `anio`, `mes` y las columnas de los
  filtros. Ahora escribe todas las variables armonizadas, como dice su documentación.
* Corregido: en {dd}`geih.serie_indicadores()`, {dd}`geih.serie_tabla()` y
  {dd}`geih.serie_frecuencias()`, un filtro de rango (`{"edad": (15, 28)}`) y uno de valores
  (`{"edad": [15, 28]}`) compartían la caché, así que el segundo devolvía el resultado del primero. Las
  cachés anteriores se recalculan solas.
* Las descargas ya no dejan archivos a medias: si se interrumpe la extracción (Ctrl+C, disco lleno), el
  archivo no queda con su nombre final, y un archivo de distinto tamaño que el del ZIP se vuelve a extraer.
  Antes, la próxima descarga daba el mes o el año por completo con los datos cortados.
* Si un mes del paquete anual del empalme no se puede abrir, el año ya no queda marcado como completo:
  la próxima descarga lo vuelve a intentar.
* Corregido: si un mes completo estaba en dos carpetas (por ejemplo, descomprimido dos veces), se sumaban
  las dos y el mes contaba doble. Ahora se usa una sola, con un aviso.
* Un ZIP dañado ya no se queda en disco para siempre: si lo descargado no es un ZIP válido (descarga
  cortada o página de error del DANE) se reintenta, y un ZIP en disco que no se puede abrir o extraer se
  borra y se vuelve a descargar.
* Corregido: las páginas de la EAM en la aplicación se caían (`ValueError: ... is not in iterable`) cuando
  los años descargados no eran consecutivos, por ejemplo 2005 y 2020.
* Corregido: en la aplicación, la página de indicadores industriales se caía con `IndexError` si ningún
  establecimiento cumplía los filtros (un sector que no hay en el departamento elegido). Ahora muestra un
  aviso, como las páginas de la GEIH.
* Corregido: en {dd}`geih.serie_indicadores()`, {dd}`geih.serie_tabla()` y
  {dd}`geih.serie_frecuencias()`, si un filtro dejaba algún mes sin ninguna persona (un grupo pequeño), el
  promedio mensual de los niveles se dividía por menos meses y salía más alto. Ahora un mes vacío cuenta como
  0, como en el promedio de los totales mensuales del DANE. Las tasas no cambian. Con microdatos,
  `dd.tabla` e {dd}`geih.indicadores()` siguen contando los meses que quedan en los datos; para promediar
  sobre los meses cargados, ponga `df.attrs["meses_por_anio"] = {año: número de meses}`.
* La aplicación requiere Streamlit 1.51 o más reciente (`pip install "dane-data[app]"` lo actualiza). Con
  versiones anteriores, las tablas no aceptaban `width="stretch"` y cada gráfica mostraba un aviso de
  función obsoleta. Los lanzadores ya usaban una versión reciente.
* La caché ya no puede quedar a medias: {dd}`geih.load()` también la escribe con otro nombre y la renombra
  al terminar, y los nombres temporales son únicos, así que dos personas usando la misma aplicación a la
  vez (`--address 0.0.0.0`) no escriben el mismo archivo. {dd}`geih.clear_cache()` borra también los
  temporales que dejó una escritura interrumpida.
* Corregido: un solo valor o nombre en vez de una lista se partía en letras. `filtros={"sexo": "Mujer"}`
  no dejaba a nadie, y `columns="P6500"` o `modules="ocupados"` no agregaban nada. Ahora valen igual que
  `["Mujer"]`, `["P6500"]` o `["ocupados"]` en {dd}`geih.load()`, {dd}`geih.load_month()`,
  {dd}`geih.filtrar()`, las funciones `serie_*` y {dd}`eam.load()`.
* Corregido: `dd.geih.download([])` y `dd.eam.download([])` descargaban la serie entera; ahora no descargan
  nada (`None` sigue siendo "todos"). Un año que no está en el ANDA, como 2030, ya no se ignora en silencio:
  se avisa. En {dd}`geih.download()`, `modules=[]` (que bajaba todos los módulos) o un nombre mal escrito
  lanzan `ValueError`, y en la aplicación el botón de descargar se desactiva si no hay módulos elegidos.

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
