"""
Línea de comandos de dane_data.

    dane-data app                                   # abre la aplicación gráfica
    dane-data estado                                # qué datos hay descargados
    dane-data config --geih RUTA --eam RUTA         # dónde están/estarán los datos
    dane-data descargar geih --anios 2024 2025
    dane-data descargar geih --anios 2016 --empalme
    dane-data descargar eam --anios 2022 2023 2024
"""

from __future__ import annotations

import argparse
import logging
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from . import config, eam, geih


def _puerto_libre(preferido: int) -> int:
    """El puerto pedido si está libre; si no, el siguiente libre."""
    for puerto in range(preferido, preferido + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("127.0.0.1", puerto)) != 0:
                return puerto
    return preferido


def _abrir_navegador_cuando_lista(url: str, proceso: subprocess.Popen, espera_max: float = 120) -> None:
    """Espera a que Streamlit responda y abre el navegador (una sola vez)."""
    salud = url.rstrip("/") + "/_stcore/health"
    limite = time.time() + espera_max
    while time.time() < limite and proceso.poll() is None:
        try:
            with urllib.request.urlopen(salud, timeout=1) as r:
                if r.status == 200:
                    webbrowser.open(url)
                    return
        except OSError:
            pass
        time.sleep(0.5)


def _cmd_app(args) -> int:
    app = Path(__file__).parent / "app" / "Inicio.py"
    puerto = _puerto_libre(args.port)
    url = f"http://localhost:{puerto}"
    # headless: Streamlit no abre el navegador ni pide correo la primera vez; lo abrimos nosotros.
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(puerto),
           "--server.address", args.address, "--server.headless", "true",
           "--browser.gatherUsageStats", "false"]
    print(f"\n  dane-data se está abriendo en {url}")
    print("  Para cerrarla, cierre esta ventana o presione Ctrl+C.\n", flush=True)
    proceso = subprocess.Popen(cmd, cwd=app.parent)  # cwd: para que lea app/.streamlit/config.toml
    if not args.no_browser:
        threading.Thread(target=_abrir_navegador_cuando_lista, args=(url, proceso), daemon=True).start()
    try:
        return proceso.wait()
    except KeyboardInterrupt:
        proceso.terminate()
        try:
            proceso.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proceso.kill()
        return 0


def _cmd_estado(args) -> int:
    for key, label in (("geih", "GEIH principal"), ("geih_empalme", "GEIH empalme"), ("eam", "EAM")):
        print(f"{label:15s} {config.get_path(key)}")
    for emp in (False, True):
        av = geih.available(empalme=emp)
        nombre = "GEIH empalme" if emp else "GEIH principal"
        if av.empty:
            print(f"\n{nombre}: sin datos")
            continue
        resumen = av.groupby("anio").agg(meses=("mes", "size"), incompletos=("completo", lambda s: (~s).sum()))
        print(f"\n{nombre}:")
        print(resumen.to_string())
    av = eam.available()
    print("\nEAM:", "sin datos" if av.empty else f"{len(av)} años ({av.anio.min()}–{av.anio.max()})")
    return 0


def _cmd_config(args) -> int:
    config.set_paths(geih=args.geih, geih_empalme=args.empalme, eam=args.eam, save=True)
    print(f"Guardado en {config.CONFIG_FILE}")
    for k, v in config.show_paths().items():
        print(f"  {k:13s} {v}")
    return 0


def _cmd_descargar(args) -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if args.encuesta == "geih":
        geih.download(years=args.anios, modules=args.modulos, empalme=args.empalme,
                      delete_zips=args.borrar_zips, limit_files=args.limite)
    else:
        eam.download(years=args.anios, include_tic=args.tic, delete_zips=args.borrar_zips)
    return 0


def _parser() -> argparse.ArgumentParser:
    """Argumentos del comando (también los documenta ``docs/guia/cli.md`` con sphinx-argparse)."""
    p = argparse.ArgumentParser(prog="dane-data", description="Microdatos DANE (GEIH y EAM) para economistas.")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("app", help="Abrir la aplicación gráfica en el navegador")
    a.add_argument("--port", type=int, default=8501, help="Puerto preferido (si está ocupado se usa el siguiente)")
    a.add_argument("--no-browser", action="store_true", help="No abrir el navegador automáticamente")
    a.add_argument("--address", default="localhost", help="Use 0.0.0.0 para compartir en la red local (aula)")
    a.set_defaults(fn=_cmd_app)

    e = sub.add_parser("estado", help="Mostrar rutas y datos disponibles")
    e.set_defaults(fn=_cmd_estado)

    c = sub.add_parser("config", help="Configurar carpetas de datos (se guarda para siempre)")
    c.add_argument("--geih", help="Carpeta de la GEIH principal (la que contiene datos_csv/)")
    c.add_argument("--empalme", help="Carpeta de la GEIH empalme (la que contiene datos_csv/)")
    c.add_argument("--eam", help="Carpeta de la EAM (la que contiene datos/)")
    c.set_defaults(fn=_cmd_config)

    d = sub.add_parser("descargar", help="Descargar microdatos del DANE")
    d.add_argument("encuesta", choices=["geih", "eam"])
    d.add_argument("--anios", nargs="+", type=int, help="Años (por defecto todos)")
    d.add_argument("--modulos", nargs="+", choices=list(geih.MODULE_PATTERNS), help="Solo GEIH")
    d.add_argument("--empalme", action="store_true", help="GEIH: serie de empalme 2010–2020")
    d.add_argument("--limite", type=int, help="GEIH: máximo de archivos mensuales por año (pruebas)")
    d.add_argument("--tic", action="store_true", help="EAM: incluir módulo TIC 2008–2018")
    d.add_argument("--borrar-zips", action="store_true", help="Borrar los ZIP tras extraer")
    d.set_defaults(fn=_cmd_descargar)
    return p


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
