#!/usr/bin/env bash
# Compila el lanzador de Windows "Abrir dane-data.exe" desde Linux o macOS (también en el release de
# GitHub Actions). El compilador cruzado es zig, que uv descarga de PyPI: no hay que instalar nada más.
# La versión del ejecutable sale de pyproject.toml.
#
# Uso: lanzador/compilar.sh [archivo de salida]      (por defecto: build/Abrir dane-data.exe)
set -euo pipefail
cd "$(dirname "$0")/.."

SALIDA="${1:-build/Abrir dane-data.exe}"
VERSION=$(grep -m1 '^version = ' pyproject.toml | cut -d'"' -f2)
# FILEVERSION pide cuatro números: 0.3.0 -> 0,3,0,0 (un sufijo como rc1 se descarta)
IFS=. read -r A B C _ <<< "$(grep -oE '^[0-9]+(\.[0-9]+)*' <<< "$VERSION")"
NUMEROS="${A:-0},${B:-0},${C:-0},0"

# Los recursos se compilan desde una carpeta temporal junto a version.h (zig no pasa -I al compilador de .rc)
TEMPORAL=$(mktemp -d)
trap 'rm -rf "$TEMPORAL"' EXIT
cp lanzador/lanzador.rc lanzador/lanzador.manifest lanzador/dane-data.ico "$TEMPORAL"
printf '#define VERSION_TEXTO "%s"\n#define VERSION_NUMEROS %s\n' "$VERSION" "$NUMEROS" > "$TEMPORAL/version.h"

mkdir -p "$(dirname "$SALIDA")"
uvx --from ziglang==0.16.0 python -m ziglang cc -target x86_64-windows-gnu -Os -s -municode -Wall \
    lanzador/lanzador.c "$TEMPORAL/lanzador.rc" -o "$SALIDA"
echo "Compilado: $SALIDA (versión $VERSION)"
