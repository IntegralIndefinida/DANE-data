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
1. En la página de [versiones](https://github.com/IntegralIndefinida/DANE-data/releases) descargue
   `dane-data-<versión>.zip` (en *Assets*, no el «Source code»).
2. Descomprímalo donde quiera.
3. Haga doble clic en el lanzador de su sistema:

   | Sistema | Archivo |
   |---|---|
   | Windows | `Abrir dane-data (Windows).bat` |
   | Mac | `Abrir dane-data (Mac).command` |
   | Linux | `abrir-dane-data.sh` |

La primera vez necesita internet y tarda de 1 a 3 minutos: el lanzador instala
[uv](https://docs.astral.sh/uv/), que descarga Python 3.12 y las versiones exactas de las librerías
dentro de la carpeta, sin tocar el resto del sistema. Las siguientes veces abre en segundos y el navegador
se abre solo.

En **Windows**, si aparece «Windows protegió su PC»: *Más información* → *Ejecutar de todas formas*. En
**Mac**, si dice «desarrollador no identificado»: clic derecho → *Abrir* → *Abrir*.
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

```bash
pip install --upgrade "dane-data[app]"
```

Los cambios de cada versión están en {doc}`novedades`. Los resultados guardados en caché se recalculan solos
con la versión nueva.
