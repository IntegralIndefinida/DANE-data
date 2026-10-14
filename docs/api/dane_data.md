# dd: funciones generales

```python
import dane_data as dd
```

## Carpetas de datos

```{eval-rst}
.. autofunction:: dane_data.set_paths
.. autofunction:: dane_data.get_path
.. autofunction:: dane_data.show_paths
```

## Tablas y estadísticas ponderadas

```{eval-rst}
.. autofunction:: dane_data.tabla
.. autofunction:: dane_data.weighted_mean
.. autofunction:: dane_data.weighted_quantile
```

## Diccionario de variables

```{eval-rst}
.. autofunction:: dane_data.buscar_variable
.. autofunction:: dane_data.describir
.. autofunction:: dane_data.diccionario
```

## Datos de referencia

| Nombre | Contenido |
|---|---|
| `dd.SMLV` | Salario mínimo legal mensual vigente por año, en pesos (`{año: valor}`), tomado de los decretos |
| `dd.DEPARTAMENTOS` | Código DIVIPOLA → nombre del departamento |
| `dd.MESES` | Número → nombre del mes |

## Descargas

```{eval-rst}
.. autoexception:: dane_data.DownloadCancelled
```
