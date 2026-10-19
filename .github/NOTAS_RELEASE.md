## Novedades de la versión 0.3.0

Una revisión completa de la librería: correcciones en cifras, descargas más seguras y una aplicación que ya
no se cae en casos raros. La lista completa está en
[Novedades](https://integralindefinida.github.io/DANE-data/novedades.html).

**Al actualizar**
- La aplicación requiere **Streamlit 1.51** o más reciente: `pip install -U "dane-data[app]"` lo actualiza (los
  lanzadores del zip ya lo hacen solos).
- `dd.geih.download([])` y `dd.eam.download([])` ya no descargan la serie entera: una lista vacía es ningún año
  (`None` sigue siendo "todos").
- **EAM 2024** se guarda en el Stata original del DANE y se lee con sus códigos. Si quiere los códigos en vez
  de las etiquetas, borre la carpeta de 2024 y vuelva a descargarla.

**Cifras**
- Si un filtro deja un mes sin nadie (un grupo pequeño), ese mes cuenta como 0 en el promedio mensual, como
  hace el DANE; antes los niveles salían más altos. Las tasas no cambian.
- Un filtro de rango (`{"edad": (15, 28)}`) y uno de valores (`{"edad": [15, 28]}`) ya no comparten caché.
- Un mes descomprimido dos veces ya no cuenta doble.
- `estadistico="porcentaje"` incluye las filas con el primer grupo vacío, y `eam.crecimiento` no calcula tasas
  anuales entre años no consecutivos.
- `exportar()` sin `variables` escribe todas las variables armonizadas, y un solo valor (`{"sexo": "Mujer"}`,
  `columns="P6500"`) ya no se parte en letras.

**Descargas**
- Una descarga interrumpida o un ZIP dañado ya no dejan datos cortados que se den por buenos: se detectan y se
  vuelven a bajar.
- Solo se siguen enlaces https del ANDA.

**Aplicación**
- Las páginas de la EAM ya no se caen con años no consecutivos ni con filtros sin establecimientos.
- Cada exportación de microdatos tiene su propio archivo.
- En un aula (`dane-data app --address 0.0.0.0`) avisa que queda en la red sin contraseña.

Las cifras de la GEIH siguen coincidiendo mes a mes con los anexos del DANE (2007–2026 y empalme 2010–2020).

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
