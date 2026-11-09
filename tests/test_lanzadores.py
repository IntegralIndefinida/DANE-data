"""El lanzador de macOS y Linux (abrir-dane-data.sh), sin red: curl y uv son falsos."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

LANZADOR = Path(__file__).resolve().parents[1] / "abrir-dane-data.sh"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="sin bash")


def _sin_uv(tmp_path: Path) -> dict:
    """Un PATH con solo lo que usa el lanzador (sin uv) y un curl que «instala» un uv falso y anota el entorno."""
    binarios = tmp_path / "bin"
    binarios.mkdir()
    for programa in ("bash", "sh", "dirname", "mkdir", "chmod", "cat"):
        (binarios / programa).symlink_to(shutil.which(programa))
    (binarios / "curl").write_text(
        "#!/bin/sh\n"
        "cat <<'FIN'\n"
        'printf "%s" "${UV_NO_MODIFY_PATH:-}" > "$HOME/no_modificar_path"\n'
        'mkdir -p "$HOME/.local/bin"\n'
        "printf '#!/bin/sh\\nexit 0\\n' > \"$HOME/.local/bin/uv\"\n"
        'chmod +x "$HOME/.local/bin/uv"\n'
        "FIN\n")
    (binarios / "curl").chmod(0o755)
    casa = tmp_path / "casa"
    casa.mkdir()
    return {"PATH": str(binarios), "HOME": str(casa)}


def test_instala_uv_sin_cambiar_el_path_del_usuario(tmp_path):
    """Como el .bat y el .exe: el instalador de uv no toca ~/.zshrc ni ~/.bashrc (UV_NO_MODIFY_PATH)."""
    carpeta = tmp_path / "dane-data"
    carpeta.mkdir()
    shutil.copy(LANZADOR, carpeta)
    (carpeta / "pyproject.toml").write_text("")
    entorno = _sin_uv(tmp_path)
    r = subprocess.run(["bash", str(carpeta / LANZADOR.name)], env=entorno, input="", capture_output=True,
                       text=True, timeout=30)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (Path(entorno["HOME"]) / "no_modificar_path").read_text() == "1"


def test_avisa_si_no_esta_descomprimido(tmp_path):
    """Sin pyproject.toml al lado (abierto desde el .zip), dice qué hacer en vez del error de uv."""
    shutil.copy(LANZADOR, tmp_path)
    r = subprocess.run(["bash", str(tmp_path / LANZADOR.name)], env={**os.environ}, input="\n",
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 1 and "descomprimida" in r.stdout
