# Carpetas y descargas

## Dónde quedan los datos

Cada encuesta tiene su carpeta raíz, con esta estructura:

```text
<raíz GEIH>/datos_csv/<año>/<mes>/*.csv     serie principal
<raíz empalme>/datos_csv/<año>/<mes>/*.csv  serie de empalme
<raíz EAM>/datos/<año>/*.csv|*.txt
```

Las carpetas de los meses conservan el nombre que trae el ZIP del DANE (`Enero 2024`, `ENE_2021`…);
`dane-data` reconoce el mes en el nombre y busca los archivos también en subcarpetas.

### Elegir las carpetas

Por defecto todo queda en `~/dane_data_datos/`. Para usar otras carpetas (por ejemplo, en un disco externo):

```python
import dane_data as dd

dd.set_paths(geih="D:/datos/GEIH", geih_empalme="D:/datos/GEIH_empalme", eam="D:/datos/EAM", save=True)
```

Con `save=True` quedan guardadas en `~/.config/dane_data/config.json` para las próximas sesiones, para la
línea de comandos y para la aplicación; sin él, valen solo para la sesión actual. Lo mismo se hace desde la
terminal con `dane-data config --geih RUTA --empalme RUTA --eam RUTA` o desde la página de inicio de la
aplicación.

Cada carpeta se resuelve en este orden:

1. {dd}`set_paths()` en la sesión actual.
2. Las variables de entorno `DANE_DATA_GEIH`, `DANE_DATA_GEIH_EMPALME` y `DANE_DATA_EAM`.
3. El archivo `~/.config/dane_data/config.json`.
4. `~/dane_data_datos/geih`, `~/dane_data_datos/geih/empalme` y `~/dane_data_datos/eam`.

{dd}`show_paths()` muestra las carpetas que se están usando, y {dd}`get_path()` una sola.

Todas las funciones que leen o descargan aceptan además `root=` para usar otra carpeta en una sola llamada.

## Descargar

```python
dd.geih.download([2024, 2025])          # serie principal
dd.geih.download(2016, empalme=True)    # serie de empalme
dd.geih.download(2025, limit_files=1)   # solo enero, para probar
dd.eam.download(range(2014, 2025))      # EAM
dd.eam.download()                       # toda la EAM, 1992–2024
```

{dd}`geih.download()` y {dd}`eam.download()` buscan los archivos en el catálogo del ANDA de cada año, bajan
los ZIP y extraen los módulos. Las descargas son **incrementales**:

* Al terminar un mes se escribe un marcador (`.dane_data_ok`) que registra qué módulos se extrajeron. Una
  descarga posterior salta los meses que ya tienen esos módulos.
* Si se interrumpe (se cierra la ventana, se cae la conexión), basta con volver a correrla: sigue donde iba.
* Para bajar solo algunos módulos, `modules=["caracteristicas", "ocupados"]`; los nombres están en
  `dd.geih.DEFAULT_MODULES`.

Las dos funciones aceptan `progress=` (una función que recibe el avance) y `should_stop=` (una función
que, si devuelve True, detiene la descarga con {dd}`DownloadCancelled`). La aplicación los usa para la
barra de progreso y el botón de cancelar.

(archivos-danados)=
### Archivos dañados del ANDA

Algunos CSV que publica el ANDA no se pueden usar:

| Año | Problema del CSV | Qué baja `dane-data` |
|---|---|---|
| 2008 y 2011 | El factor de expansión perdió el punto decimal (`849.491.032.387.525` es 84,949…) | La versión TXT del mismo catálogo |
| Septiembre de 2021 | Separado por espacios, que también aparecen dentro del texto | La versión Stata del mismo catálogo |

Si los datos se descargaron con una versión anterior a la 0.2.0, esos meses quedan con el CSV dañado:
`dane-data` los detecta, los omite con un aviso y pide volver a descargar esos años. Los detalles están en
{doc}`diferencias`.

## Qué hay descargado

```python
>>> av = dd.geih.available()
>>> av.groupby("anio")["completo"].sum().tail(3)
anio
2024    12
2025    12
2026     8
Name: completo, dtype: int64
```

{dd}`geih.available()` trae una fila por mes con los módulos que encontró, si está completo y qué le falta.
Desde la terminal, `dane-data estado` muestra lo mismo resumido por año. Para la EAM,
{dd}`eam.available()`.

## Espacio en disco

| | Tamaño aproximado |
|---|---|
| Un año de la GEIH extraído | 500 MB, más los ZIP si se conservan (`delete_zips=False`, el valor por defecto) |
| Toda la serie principal 2007–2026 | 11 GB extraída |
| Toda la EAM 1992–2024 | 330 MB |
| Caché de `dane-data` con toda la GEIH leída | 700 MB en `~/.cache/dane_data` |

La caché se puede borrar cuando se quiera con {dd}`geih.clear_cache()`; se vuelve a crear al leer los datos.
