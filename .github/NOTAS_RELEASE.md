## Novedades de la versión 0.2.0

**Si ya tenía datos de la GEIH descargados**
- Vuelva a descargar **2008, 2011 y 2021** desde la página ⬇️ *Descargar datos*. Los CSV que publica el DANE
  para 2008, 2011 y septiembre de 2021 están dañados: en 2008 y 2011 el factor de expansión perdió el punto
  decimal, y septiembre de 2021 viene separado por espacios. Ahora dane-data baja esos meses en otro formato
  del mismo catálogo (TXT o Stata). Mientras no los vuelva a descargar, la app los marca como incompletos y no
  los usa.
- La primera vez que abra cada página, los resultados se vuelven a calcular (unos segundos por año).

**La app ya no se cae con muchos años**
- Todas las tablas y gráficas de la GEIH se calculan un año a la vez y quedan guardadas. Con 2007–2026, la
  primera consulta tarda alrededor de un minuto y las siguientes son instantáneas, con menos de 1 GB de
  memoria.
- En *Tablas y microdatos*, la pestaña de microdatos muestra un mes de ejemplo y exporta a CSV todos los
  meses elegidos, uno a la vez, en la carpeta `exportaciones` junto a los datos.
- Los indicadores laborales aceptan filtros (sexo, zona, edad, departamento) y selección de meses.

**Cifras**
- La desocupación, la participación, la ocupación y el número de ocupados coinciden mes a mes con los anexos
  del DANE de 2007 a 2026 y en la serie de empalme 2010–2020.
- Corregido febrero de 2011: algunas personas tomaban el factor de expansión de otro módulo, y la
  desocupación daba 12,81 % en vez del 12,86 % publicado.
- Serie de empalme: octubre de 2012 venía con la definición anterior de población en edad de trabajar. Ahora
  todo el empalme usa la PET de 15 años o más, como lo publica el DANE.
- La app avisa cuando los años elegidos mezclan dos versiones de la GEIH que no son comparables (proyecciones
  del censo 2005 y del CNPV 2018).
- Las diferencias encontradas con lo que publica el DANE están en la tabla del README.

**Para quien usa la librería en Python**
- Nuevas funciones que trabajan año por año, con caché en disco: `dd.geih.serie_tabla`,
  `dd.geih.serie_frecuencias` y `dd.geih.exportar`. `dd.geih.serie_indicadores` ahora acepta `filtros` y
  `meses`. También son nuevas `dd.geih.filtrar` y `dd.geih.marco_muestral`.
- `dd.geih.load(..., variables=[...])` carga solo esas columnas.
- `departamento` y `posicion_ocupacional` ahora son categóricas.
- `dd.geih.clear_cache()` borra la caché, incluidos los resultados de versiones anteriores.

---

## Cómo instalar (estudiantes)

1. Descargue **`dane-data-….zip`** (abajo, en *Assets*) — no el "Source code".
2. Descomprímalo donde quiera (Documentos, Escritorio…).
3. Doble clic en el lanzador de su sistema:
   - **Windows:** `Abrir dane-data (Windows).bat`
   - **Mac:** `Abrir dane-data (Mac).command`
   - **Linux:** `abrir-dane-data.sh`

La primera vez necesita internet y tarda 1–3 minutos (instala lo necesario). Después abre en segundos y
el navegador se abre solo. No hace falta tener Python instalado.

**Avisos de seguridad la primera vez**
- *Windows* puede mostrar "Windows protegió su PC": clic en **Más información → Ejecutar de todas formas**.
- *Mac* puede decir que el archivo es de un desarrollador no identificado: **clic derecho → Abrir → Abrir**.
