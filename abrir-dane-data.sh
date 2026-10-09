#!/usr/bin/env bash
# Lanzador de dane-data para macOS y Linux.
# La primera vez instala "uv" (que a su vez trae Python y las librerías); luego solo abre la app.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"

pausa() { echo; read -r -p "Presione Enter para cerrar esta ventana..." _; }

echo "=============================================="
echo "  dane-data - Microdatos del DANE"
echo "=============================================="

if ! command -v uv >/dev/null 2>&1; then
    echo
    echo "Primera vez: instalando el asistente 'uv' (unos segundos)..."
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
if ! uv run --quiet --extra app dane-data app; then
    echo
    echo "La aplicación se cerró con un error. Si persiste, envíe una captura de esta ventana."
    pausa
    exit 1
fi
