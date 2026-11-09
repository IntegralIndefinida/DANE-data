## Novedades de la versión 0.5.0

Dos módulos de la GEIH que antes se descartaban, Otros ingresos y Migración, con sus variables armonizadas; el
trimestre móvil del DANE; gráficas listas para una tesis y modo oscuro en la aplicación; y una ronda de
correcciones en las descargas, las tablas y los lanzadores. La lista completa está en
[Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Nuevo**
- Los módulos **Otros ingresos** y **Migración** de la GEIH, con cuatro variables armonizadas:
  `ingreso_no_laboral` (arriendos, pensiones, ayudas e intereses, por mes y sin imputar), `lugar_nacimiento`,
  `residencia_hace_12_meses` y `residencia_hace_5_anios` (desde 2022). En la aplicación, en *Tablas y microdatos*.
- `dd.geih.trimestre_movil`: el trimestre móvil como lo publica el DANE, útil para grupos con poca muestra como
  los departamentos. En la aplicación, la frecuencia *Trimestre móvil* de *Indicadores laborales*.
- Cada gráfica de la aplicación lleva adentro su título, el período, los filtros y la fuente, y se descarga con el
  triple de resolución: la imagen sirve sola en una tesis o un informe. La aplicación tiene modo oscuro.
- Ejemplo nuevo en la documentación, *Recetas para investigar*: ecuación de Mincer, descomposición de
  Oaxaca-Blinder y tablas para LaTeX.

**Al actualizar**
- Los meses ya descargados no traen los módulos nuevos. Si sus ZIP siguen en `raw_zips/`, la próxima descarga los
  saca de ahí sin bajar nada; si no, `dd.geih.download(años, forzar=True, modules=["otros_ingresos", "migracion"])`,
  o en la aplicación *Descargar datos* → *Opciones avanzadas*. `dd.geih.load` y la página *Tablas y microdatos*
  avisan qué años faltan.
- La caché de cada mes de la GEIH se vuelve a crear una vez.
- `dd.geih.MODULE_PATTERNS` ya no existe; los módulos que se pueden pedir siguen en `dd.geih.DEFAULT_MODULES`.
- Mac y Linux: si instaló uv con el lanzador de la 0.4.0 o anterior, uv pudo agregar una línea a `~/.zshrc` o
  `~/.bashrc`; la sección *Desinstalar* de la documentación dice cómo quitarla. El lanzador nuevo ya no la agrega.

**Correcciones**
- En octubre y noviembre de 2020 no se extraían ni leían tres archivos con erratas del DANE en el nombre
  («Desoucpados», «Inativos», «Fuerzo de trabajo»). Los indicadores no cambian.
- `dd.geih.download(modules=["desocupados"])` no extraía «No ocupados» desde 2022.
- `dd.tabla` y `dd.geih.serie_tabla` con la media o la mediana por grupo ya no fallan cuando nadie tiene la
  variable (por ejemplo, el ingreso laboral en 2007); la página *Tablas y microdatos* se caía.
- Las descargas devuelven como fallo los años que no están en el ANDA, y `dane-data descargar` termina con error.
- Con `forzar=True`, la descarga del empalme ya no borra un mes que el paquete nuevo del DANE no trae.
- En la aplicación, el tope de 100 de la barra *Edad* es «100 o más»; las cifras van con coma decimal; los meses de
  las gráficas, en español; y cada grupo conserva su color al quitar otros.
- Lanzadores: `Abrir dane-data.exe` busca uv solo en el `PATH`, el zip trae `LEEME.txt`, y el lanzador de Mac y
  Linux avisa si se abre sin descomprimir el zip.

---

## Cómo instalar (estudiantes)

1. Descargue **`dane-data.zip`** (abajo, en *Assets*) — no el "Source code".
2. Descomprímalo (en Windows: clic derecho → *Extraer todo…*; abrirlo con doble clic no basta) en una
   carpeta fuera de OneDrive, por ejemplo `C:\dane-data`: la primera vez se crean miles de archivos
   (`.venv/`) que OneDrive se pondría a sincronizar.
3. Doble clic en el lanzador de su sistema:
   - **Windows:** `Abrir dane-data.exe` (o `Abrir dane-data (Windows).bat`, que hace lo mismo)
   - **Mac:** `Abrir dane-data (Mac).command`
   - **Linux:** `abrir-dane-data.sh`

La primera vez necesita internet y tarda 1–3 minutos (instala lo necesario). Después abre en segundos y
el navegador se abre solo. No hace falta tener Python instalado. Cuando salga una versión nueva, la página de
inicio de la aplicación lo avisa y la instala con un clic.

**Avisos de seguridad la primera vez**
- *Windows* puede mostrar "Windows protegió su PC": clic en **Más información → Ejecutar de todas formas**.
- *Mac* puede decir que no se puede verificar el desarrollador: cierre el aviso y abra **Configuración del
  Sistema → Privacidad y seguridad → Abrir de todos modos** (hasta macOS 14 bastaba con clic derecho → Abrir →
  Abrir).

**Si ya tiene Python:** `pip install "dane-data[app]"` y luego `dane-data app`.
