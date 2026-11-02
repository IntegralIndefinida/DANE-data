## Novedades de la versión 0.4.0

Llegan las Estadísticas Vitales: los nacimientos y las defunciones de Colombia desde 1979, con tasas calculadas
como las calcula el DANE y las proyecciones de población incluidas. La lista completa está en
[Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Nuevo**
- Estadísticas Vitales (`dd.eevv`): los certificados de defunción (1979–2025), de nacimiento y de defunción
  fetal (1998–2025), descargados, armonizados y comprobados contra los cuadros del DANE. En la aplicación, la
  página *Nacimientos y defunciones*; en la terminal, `dane-data descargar eevv`.
- `dd.eevv.tasas` y `dd.eevv.tasas_especificas`: natalidad, mortalidad, fecundidad, mortalidad infantil,
  neonatal, perinatal y materna, con las fórmulas de las fichas técnicas del DANE. Son de hechos registrados,
  sin ajustar por subregistro.
- `dd.poblacion`: las proyecciones de población del DANE por departamento, sexo, edad simple y área. Vienen con
  la librería, sin descargar nada.
- Los diccionarios oficiales de los tres certificados, en `describir`, `buscar_variable` y la página
  *Diccionario* de la aplicación.

**Al actualizar**
- La caché de cada mes de la GEIH se vuelve a crear una vez. Desde ahora se rehace sola cuando cambia el código
  que lee los archivos.
- dane-data ya no depende de `beautifulsoup4`.

**Correcciones**
- `dd.eam.download(delete_zips=True)` (en la terminal `--borrar-zips`) ya borra los ZIP de los años que se
  extraen bien; en la 0.3.2 solo borraba los de los años que fallaban.
- `download(root="~/...")` descarga en la carpeta personal, donde `load` la busca, y no en una carpeta llamada
  `~` dentro de la carpeta actual.
- `dd.tabla` con un estadístico mal escrito dice cuáles son los válidos.

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
