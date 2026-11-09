#!/usr/bin/env bash
# Lanzador de dane-data para macOS y Linux.
# La primera vez instala "uv" (que a su vez trae Python y las librerías); luego solo abre la app.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

pausa() { echo; read -r -p "Presione Enter para cerrar esta ventana..." _; }

echo "=============================================="
echo "  dane-data - Microdatos del DANE"
echo "=============================================="

# Abierto desde un visor de archivos comprimidos, el lanzador queda solo en una carpeta temporal: sin
# pyproject.toml, uv da un error que no dice qué pasó (lo mismo revisan el .bat y el .exe)
if [ ! -f pyproject.toml ]; then
    echo
    echo "Este lanzador tiene que estar dentro de la carpeta de dane-data ya descomprimida."
    echo "Descomprima el .zip y abra el lanzador desde la carpeta extraída."
    pausa
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "Primera vez: instalando el asistente 'uv' (unos segundos)..."
    # Sin tocar ~/.zshrc ni ~/.bashrc: este lanzador ya agrega ~/.local/bin a su propio PATH (arriba), como
    # el .bat y el .exe en Windows. Sin esto, el instalador de uv cambia el PATH del usuario.
    export UV_NO_MODIFY_PATH=1
    if command -v curl >/dev/null 2>&1; then
        curl -LsSf https://astral.sh/uv/install.sh | sh
    else
        wget -qO- https://astral.sh/uv/install.sh | sh
    fi
    if ! command -v uv >/dev/null 2>&1; then
        echo
        echo "No se pudo instalar 'uv'. Revise su conexión a internet e intente de nuevo."
        pausa
        exit 1
    fi
fi

echo
echo "Preparando la aplicación... la primera vez tarda 1 a 3 minutos (descarga Python y librerías)."
echo
if ! uv run --frozen --quiet --extra app dane-data app; then
    echo
    echo "La aplicación se cerró con un error. Si persiste, envíe una captura de esta ventana."
    pausa
    exit 1
fi
