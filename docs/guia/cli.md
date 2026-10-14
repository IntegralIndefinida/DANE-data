# Línea de comandos

La instalación agrega el comando `dane-data` a la terminal:

```bash
dane-data app                                       # abrir la aplicación
dane-data estado                                    # carpetas y datos descargados
dane-data config --geih RUTA --empalme RUTA --eam RUTA
dane-data descargar geih --anios 2024 2025
dane-data descargar geih --anios 2016 --empalme
dane-data descargar eam --anios 2022 2023 2024
```

Si el comando no está en la terminal (por ejemplo, con `uv`), use `uv run dane-data ...` o
`python -m dane_data ...`.

## Referencia

```{include} ../_generado/cli.md
```
