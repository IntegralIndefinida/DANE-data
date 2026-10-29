## Novedades de la versión 0.3.2

La informalidad sigue ahora la medición del DANE, las descargas avisan cuando algo falla y la aplicación se
actualiza sola desde el zip para estudiantes. La lista completa está en
[Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Al actualizar**
- `formal` y `tasa_informalidad` siguen la medición de informalidad del DANE (17.ª CIET): los ocupados
  formales e informales de cada mes desde 2022 coinciden con los publicados. Antes de 2022 quedan vacías,
  porque la medición necesita preguntas del cuestionario de 2022.
- Nuevas `formal_marco2005` y `tasa_informalidad_marco2005`: la medición anterior del DANE, para 2007–2021.
- La caché de cada mes de la GEIH se vuelve a crear una vez.
- `serie_indicadores` ya no devuelve la fila del grupo vacío al desagregar con `por` (`dropna=False` la
  conserva).

**Estudiantes**
- El zip se llama ahora `dane-data.zip` y ya no trae el código: el lanzador instala dane-data desde PyPI. Si
  su zip es de una versión anterior, baje este una última vez.
- Cuando sale una versión nueva, la página de inicio lo avisa y el botón «Actualizar» la instala.

**Descargas**
- `forzar=True` (en la terminal `--forzar`; en la aplicación, «Volver a bajar lo que ya está descargado»)
  vuelve a bajar lo que el DANE corrigió.
- Una descarga en la que algo falló ya no se anuncia como terminada: se devuelve la lista de fallos.
- Un mes al que le falta un módulo, o una parte de un módulo (por ejemplo `Resto - Ocupados`), ya no se da
  por completo.

**Correcciones**
- Los niveles salían divididos por los meses equivocados al elegir meses después de `filtrar`: un trimestre
  salía 4 veces más bajo. Las tasas no cambiaban.
- La caché de la GEIH ya no crece sin límite: lo que no se usa en 90 días se borra solo.
- *Tablas y microdatos* exporta los microdatos para Excel en español (`;` y coma decimal).

**EAM**
- Nuevas columnas `microagregado` y `grupo_microagregacion`, y `panel(excluir_microagregados=True)`.
- Nueva advertencia: el ANDA publica la actividad de muchas plantas grandes con el código residual, así que
  la composición por sector no coincide con la del DANE, aunque los totales sí.

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
