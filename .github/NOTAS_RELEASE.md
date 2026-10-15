## Novedades de la versión 0.2.2

**Corregido: la GEIH de 2021 en Google Colab.** Con pandas 2 (el que trae Colab), `dd.geih.download([2021])`
y la carga de 2021 fallaban con `ValueError: Version of given Stata file is 110`. El DANE publica septiembre
de 2021 en Stata 7 (formato 110), que pandas solo lee desde la versión 3; ahora se lee con cualquier pandas
desde la 2.0. Las cifras no cambian, y si ya tenía 2021 descargado no hace falta volver a descargarlo.

Para actualizar: `pip install -U "dane-data[app]"` (en Colab, reinicie la sesión después).

**Documentación nueva** en <https://integralindefinida.github.io/DANE-data/>: guía de usuario, galería de
ejemplos con datos reales y referencia de la API con una página por función.

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

**Si ya tiene Python:** `pip install "dane-data[app]"` y luego `dane-data app`.
