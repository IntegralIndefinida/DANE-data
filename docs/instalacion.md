# Instalación

`dane-data` funciona en Windows, macOS y Linux, con Python 3.10 o más reciente.

::::{tab-set}
:::{tab-item} Con pip
```bash
pip install "dane-data[app]"    # librería + aplicación
pip install dane-data           # solo la librería
```

El extra `app` instala lo que necesita la aplicación (Streamlit, Plotly y openpyxl). Se recomienda un
entorno virtual (`python -m venv`) o de conda para no mezclar versiones con otros proyectos.
:::

:::{tab-item} Con uv
```bash
uv add "dane-data[app]"         # dentro de un proyecto de uv
uvx --from "dane-data[app]" dane-data app    # o abrir la aplicación sin instalar nada
```
:::

:::{tab-item} Sin Python (estudiantes)
1. Descargue [dane-data.zip](https://github.com/IntegralIndefinida/DANE-data/releases/latest/download/dane-data.zip) (siempre la última versión).
2. Descomprímalo (en Windows: clic derecho → *Extraer todo…*; abrirlo con doble clic no basta) en una
   carpeta fuera de OneDrive, por ejemplo `C:\dane-data`: la primera vez se crean miles de archivos
   (`.venv/`) que OneDrive se pondría a sincronizar.
3. Haga doble clic en el lanzador de su sistema:

   | Sistema | Archivo |
   |---|---|
   | Windows | `Abrir dane-data.exe` (o `Abrir dane-data (Windows).bat`, que hace lo mismo) |
   | Mac | `Abrir dane-data (Mac).command` |
   | Linux | `abrir-dane-data.sh` |

La primera vez necesita internet y tarda de 1 a 3 minutos: el lanzador instala
[uv](https://docs.astral.sh/uv/), que descarga Python 3.12, dane-data y las versiones exactas de las
librerías dentro de la carpeta, sin tocar el resto del sistema. Las siguientes veces abre en segundos y el navegador
se abre solo.

En **Windows**, si aparece «Windows protegió su PC»: *Más información* → *Ejecutar de todas formas*. En
**Mac**, si dice que no se puede verificar el desarrollador, cierre el aviso y abra *Configuración del
Sistema* → *Privacidad y seguridad* → *Abrir de todos modos* (el botón aparece abajo, durante una hora
después del intento). Hasta macOS 14 bastaba con clic derecho → *Abrir* → *Abrir*. El `.exe` de Windows
se firma según la [política de firma de código](https://github.com/IntegralIndefinida/DANE-data#política-de-firma-de-código-code-signing-policy).
:::

:::{tab-item} Para desarrollo
```bash
git clone https://github.com/IntegralIndefinida/DANE-data
cd DANE-data
uv run --extra app dane-data app        # o: pip install -e ".[app,dev,docs]"
```

Vea {doc}`desarrollo`.
:::
::::

## Comprobar la instalación

```bash
dane-data --help
python -c "import dane_data; print(dane_data.__version__)"
```

## Los datos

`dane-data` no trae los microdatos: los descarga del ANDA del DANE la primera vez. Elija dónde guardarlos
(por defecto, `~/dane_data_datos/`) y descargue lo que necesite:

```python
import dane_data as dd

dd.set_paths(geih="D:/datos/GEIH", eam="D:/datos/EAM", save=True)   # opcional
dd.geih.download(2025)
dd.eam.download(range(2014, 2025))
```

Un año de la GEIH ocupa unos 500 MB y toda la EAM unos 330 MB. Los detalles están en
{doc}`guia/datos`.

## Actualizar

Cuando sale una versión nueva, la página de inicio de la aplicación lo avisa y muestra qué cambia. Nada se
actualiza solo:

* Con el zip para estudiantes, el aviso trae un botón **Actualizar**: descarga la versión nueva, y al cerrar
  y volver a abrir el lanzador la aplicación abre con ella. Los datos descargados se conservan. Si su zip es
  anterior a este botón, baje el nuevo una última vez.
* Con pip:

  ```bash
  pip install --upgrade "dane-data[app]"
  ```

* Con uv, dentro de un proyecto: `uv sync --upgrade-package dane-data`. Con uvx:
  `uvx --upgrade --from "dane-data[app]" dane-data app`.

Para saber si hay una versión nueva, la aplicación consulta PyPI y GitHub como mucho una vez al día, sin
enviar ningún dato suyo. Para desactivarlo, defina la variable de entorno `DANE_DATA_SIN_ACTUALIZACIONES=1`.

Los cambios de cada versión están en {doc}`novedades`. Los resultados guardados en caché se recalculan solos
con la versión nueva.

## Desinstalar

* Con pip: `pip uninstall dane-data`.
* Con el zip para estudiantes: borre la carpeta del zip (incluye el entorno `.venv/`). Si no usa uv para
  nada más, bórrelo también. En Windows, en PowerShell:

  ```powershell
  & "$env:USERPROFILE\.local\bin\uv.exe" cache clean
  & "$env:USERPROFILE\.local\bin\uv.exe" python uninstall --all
  Remove-Item "$env:USERPROFILE\.local\bin\uv*.exe"
  ```

  En Mac y Linux: `~/.local/bin/uv cache clean`, `~/.local/bin/uv python uninstall --all` y
  `rm ~/.local/bin/uv ~/.local/bin/uvx`.
* Los datos descargados, las cachés y la configuración no se borran solos. Están en su carpeta de usuario:
  `dane_data_datos/` (la carpeta de datos por defecto), `.cache/dane_data/` y `.config/dane_data/`.
