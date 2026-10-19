## Novedades de la versión 0.3.1

Una versión pequeña: un lanzador `.exe` para Windows y una forma fácil de citar `dane-data`. La librería y las
cifras no cambian. La lista completa está en
[Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Windows**
- El zip trae `Abrir dane-data.exe`, que hace lo mismo que el `.bat` (que sigue en el zip). En esta versión
  todavía va sin firmar (vea la política de firma de código abajo).
- Los lanzadores instalan uv sin cambiar el `PATH` del usuario.

**Cómo citar**
- Nueva página **📝 Cómo citar** en la aplicación (en *Herramientas*): la cita de `dane-data` en APA y BibTeX,
  con la versión instalada, y la de los datos del DANE.
- En GitHub, el botón *Cite this repository* da la cita (sale del nuevo `CITATION.cff`).

**Documentación**
- Nueva sección [Desinstalar](https://integralindefinida.github.io/DANE-data/instalacion.html#desinstalar) en
  la instalación.

---

## Cómo instalar (estudiantes)

1. Descargue **`dane-data-….zip`** (abajo, en *Assets*) — no el "Source code".
2. Descomprímalo donde quiera (Documentos, Escritorio…).
3. Doble clic en el lanzador de su sistema:
   - **Windows:** `Abrir dane-data.exe` (o `Abrir dane-data (Windows).bat`, que hace lo mismo)
   - **Mac:** `Abrir dane-data (Mac).command`
   - **Linux:** `abrir-dane-data.sh`

La primera vez necesita internet y tarda 1–3 minutos (instala lo necesario). Después abre en segundos y
el navegador se abre solo. No hace falta tener Python instalado.

**Avisos de seguridad la primera vez**
- *Windows* puede mostrar "Windows protegió su PC": clic en **Más información → Ejecutar de todas formas**.
- *Mac* puede decir que el archivo es de un desarrollador no identificado: **clic derecho → Abrir → Abrir**.

El `.exe` de Windows se firma según la [Code signing policy (política de firma de código)](https://github.com/IntegralIndefinida/DANE-data#política-de-firma-de-código-code-signing-policy).

**Si ya tiene Python:** `pip install "dane-data[app]"` y luego `dane-data app`.
