"""
Línea de comandos de dane_data.

    dane-data app                                   # abre la aplicación gráfica
    dane-data estado                                # qué datos hay descargados
    dane-data config --geih RUTA --eam RUTA         # dónde están/estarán los datos
    dane-data descargar geih --anios 2024 2025
    dane-data descargar geih --anios 2016 --empalme
    dane-data descargar eam --anios 2022 2023 2024
    dane-data descargar eevv --anios 2025 --tipos nacimientos defunciones
    dane-data descargar emicron --anios 2023 2024 --modulos ventas costos
    dane-data descargar ecv --anios 2024 2025 --modulos caracteristicas salud
    dane-data descargar pobreza --anios 2024 2025 --empalme
"""

from __future__ import annotations

import argparse
import importlib.util
import logging
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

from . import config, eam, ecv, eevv, emicron, geih, pobreza


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
    if importlib.util.find_spec("streamlit") is None:  # si no, el subproceso solo dice "No module named streamlit"
        print('dane-data app: falta instalar la aplicación. Use  pip install "dane-data[app]"  o, en la carpeta '
              "de dane-data,  uv run --extra app dane-data app", file=sys.stderr)
        return 1
    app = Path(__file__).parent / "app" / "Inicio.py"
    puerto = _puerto_libre(args.port)
    url = f"http://localhost:{puerto}"
    # headless: Streamlit no abre el navegador ni pide correo la primera vez; lo abrimos nosotros.
    cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.port", str(puerto),
           "--server.address", args.address, "--server.headless", "true",
           "--browser.gatherUsageStats", "false"]
    print(f"\n  dane-data se está abriendo en {url}")
    if args.address not in ("localhost", "127.0.0.1", "::1"):
        print(f"  Aviso: compartida en la red ({args.address}) y sin contraseña: cualquiera en la red puede "
              "cambiar las carpetas y descargar en este computador.")
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
    for key, label in (("geih", "GEIH principal"), ("geih_empalme", "GEIH empalme"), ("eam", "EAM"),
                       ("eevv", "Est. Vitales"), ("emicron", "EMICRON"), ("ecv", "ECV"),
                       ("pobreza", "Pobreza")):
        print(f"{label:15s} {config.get_path(key)}")
    hay = False
    for emp in (False, True):
        av = geih.available(empalme=emp)
        hay |= not av.empty
        nombre = "GEIH empalme" if emp else "GEIH principal"
        if av.empty:
            print(f"\n{nombre}: sin datos")
            continue
        resumen = av.groupby("anio").agg(meses=("mes", "size"), incompletos=("completo", lambda s: (~s).sum()))
        print(f"\n{nombre}:")
        print(resumen.to_string())
    av = eam.available()
    hay |= not av.empty
    print("\nEAM:", "sin datos" if av.empty else f"{len(av)} años ({av.anio.min()}–{av.anio.max()})")
    av = eevv.available()
    hay |= not av.empty
    print("\nEstadísticas Vitales:", "sin datos" if av.empty else "")
    for tipo, d in av.groupby("tipo", sort=False):
        print(f"  {tipo}: {len(d)} años ({d.anio.min()}–{d.anio.max()})")
    av = emicron.available()
    hay |= not av.empty
    anios = sorted(av.anio.unique())
    print("\nEMICRON:", "sin datos" if av.empty else f"{len(anios)} años ({anios[0]}–{anios[-1]}), {len(av)} módulos")
    av = ecv.available()
    av = av[av["modulo"].isin(ecv.MODULOS)]
    hay |= not av.empty
    print("\nECV:", "sin datos" if av.empty else "")
    for anio, d in av.groupby("anio"):
        print(f"  {anio}: {len(d)} de {len(ecv.MODULOS)} capítulos")
    av = pobreza.available()
    hay |= not av.empty
    anios = av.anio.dropna()
    # Los que usa load(empalme=True); el departamental de 2021 todavía no
    empalme = "sí" if {"empalme_2012_2020", "lineas_2012_2018", "hogares_empalmado_2021"} <= set(av.archivo) else "no"
    print("\nPobreza monetaria:", "sin datos" if av.empty else
          (f"{anios.nunique()} años ({anios.min()}–{anios.max()})" if len(anios) else "sin años")
          + f"; archivos del empalme 2012–2021: {empalme}")
    if not hay:
        print("\nPara empezar:  dane-data descargar geih --anios 2025   (o abra la aplicación:  dane-data app)")
    return 0


def _cmd_config(args) -> int:
    # --empalme es la clave geih_empalme; las demás opciones se llaman como su clave
    carpetas = {clave: getattr(args, "empalme" if clave == "geih_empalme" else clave) for clave in config._KEYS}
    try:
        config.set_paths(**carpetas, guardar=True)
    except ValueError as e:  # una carpeta vacía
        print(f"dane-data config: {e}", file=sys.stderr)
        return 2
    print(f"Guardado en {config.CONFIG_FILE}")
    for k, v in config.show_paths().items():
        print(f"  {k:13s} {v}")
    for clave, valor in carpetas.items():
        env = config._KEYS[clave][0]
        if valor is not None and os.environ.get(env):
            print(f"  Aviso: la variable de entorno {env} ({os.environ[env]}) tiene prioridad sobre el archivo "
                  "en las próximas sesiones.")
    return 0


def _cmd_descargar(args) -> int:
    solo_geih = [("--modulos", args.modulos), ("--empalme", args.empalme), ("--limite", args.limite)]
    archivos = ("--archivos", args.archivos)
    otras = {"geih": [("--tic", args.tic), ("--tipos", args.tipos), archivos],
             "eam": [*solo_geih, ("--tipos", args.tipos), archivos],
             "eevv": [*solo_geih, ("--tic", args.tic), archivos],
             "emicron": [*solo_geih[1:], ("--tic", args.tic), ("--tipos", args.tipos), archivos],
             "ecv": [*solo_geih[1:], ("--tic", args.tic), ("--tipos", args.tipos), archivos],
             # --empalme sí: los archivos del empalme de la pobreza
             "pobreza": [("--modulos", args.modulos), ("--limite", args.limite), ("--tic", args.tic), ("--tipos", args.tipos)]}
    if sobran := [nombre for nombre, valor in otras[args.encuesta] if valor]:
        print(f"dane-data descargar {args.encuesta}: {', '.join(sobran)} no aplica a esta encuesta.", file=sys.stderr)
        return 2
    # --modulos sirve a la GEIH, la EMICRON y la ECV, cada una con los suyos
    validos = {"geih": geih.DEFAULT_MODULES, "emicron": emicron.MODULOS, "ecv": ecv.MODULOS}.get(args.encuesta, {})
    if args.modulos and (raros := [m for m in args.modulos if m not in validos]):
        print(f"dane-data descargar {args.encuesta}: módulos que no son de esta encuesta: {', '.join(raros)}. "
              f"Opciones: {', '.join(validos)}.", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if args.encuesta == "geih":
        fallidos = geih.download(anios=args.anios, modulos=args.modulos, empalme=args.empalme,
                                 borrar_zips=args.borrar_zips, limite_archivos=args.limite, forzar=args.forzar)
    elif args.encuesta == "eam":
        fallidos = eam.download(anios=args.anios, incluir_tic=args.tic, borrar_zips=args.borrar_zips,
                                forzar=args.forzar)
    elif args.encuesta == "eevv":
        fallidos = eevv.download(anios=args.anios, tipos=args.tipos, borrar_zips=args.borrar_zips, forzar=args.forzar)
    elif args.encuesta == "emicron":
        fallidos = emicron.download(anios=args.anios, modulos=args.modulos, borrar_zips=args.borrar_zips,
                                    forzar=args.forzar)
    elif args.encuesta == "ecv":
        fallidos = ecv.download(anios=args.anios, modulos=args.modulos, borrar_zips=args.borrar_zips, forzar=args.forzar)
    else:
        if args.anios is None:
            print("Se descarga toda la serie 2012–2025 (unos 1,4 GB de ZIP). Use --anios para elegir años.")
        fallidos = pobreza.download(anios=args.anios, archivos=args.archivos, empalme=args.empalme,
                                    borrar_zips=args.borrar_zips, forzar=args.forzar)
    return 1 if fallidos else 0  # el resumen de lo que falló ya quedó en el registro


# argparse escribe en inglés el uso, los errores y la ayuda (-h); la CLI es para estudiantes. El orden importa:
# "argument " va al final porque está dentro de otros textos.
_ARGPARSE_ES = (("usage:", "uso:"), ("positional arguments:", "argumentos:"), ("options:", "opciones:"),
                ("show this help message and exit", "mostrar esta ayuda y salir"),
                ("the following arguments are required", "faltan los argumentos"),
                ("invalid choice", "opción no válida"), ("choose from", "elija entre"),
                ("unrecognized arguments", "argumentos desconocidos"),
                ("expected at least one argument", "falta al menos un valor"), ("expected one argument", "falta un valor"),
                ("invalid int value", "no es un número entero"), ("argument ", "argumento "))


def _es(texto: str) -> str:
    for en, es in _ARGPARSE_ES:
        texto = texto.replace(en, es)
    return texto


class _Parser(argparse.ArgumentParser):
    def format_help(self) -> str:
        return _es(super().format_help())

    def format_usage(self) -> str:
        return _es(super().format_usage())

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, f"{self.prog}: error: {_es(message)}\n")


def _parser() -> argparse.ArgumentParser:
    """Argumentos del comando; ``docs/conf.py`` arma con ellos la referencia de la línea de comandos."""
    p = _Parser(prog="dane-data", description="Microdatos DANE (GEIH, EAM, Estadísticas Vitales, EMICRON, ECV y pobreza monetaria) para economistas.")
    sub = p.add_subparsers(dest="cmd")  # sin subcomando, main muestra la ayuda

    a = sub.add_parser("app", help="Abrir la aplicación gráfica en el navegador")
    a.add_argument("--port", type=int, default=8501, help="Puerto preferido (si está ocupado se usa el siguiente)")
    a.add_argument("--no-browser", action="store_true", help="No abrir el navegador automáticamente")
    a.add_argument("--address", default="localhost",
                   help="Use 0.0.0.0 para compartir en la red local (aula). Sin contraseña: cualquiera en la red "
                        "puede cambiar las carpetas y descargar en este computador")
    a.set_defaults(fn=_cmd_app)

    e = sub.add_parser("estado", help="Mostrar rutas y datos disponibles")
    e.set_defaults(fn=_cmd_estado)

    c = sub.add_parser("config", help="Configurar carpetas de datos (se guarda para siempre)")
    c.add_argument("--geih", help="Carpeta de la GEIH principal (la que contiene datos_csv/)")
    c.add_argument("--empalme", help="Carpeta de la GEIH empalme (la que contiene datos_csv/)")
    c.add_argument("--eam", help="Carpeta de la EAM (la que contiene datos/)")
    c.add_argument("--eevv", help="Carpeta de las Estadísticas Vitales (la que contiene datos/)")
    c.add_argument("--emicron", help="Carpeta de la EMICRON (la que contiene datos/)")
    c.add_argument("--ecv", help="Carpeta de la Encuesta Nacional de Calidad de Vida (la que contiene datos/)")
    c.add_argument("--pobreza", help="Carpeta de la pobreza monetaria (la que contiene datos/)")
    c.set_defaults(fn=_cmd_config)

    d = sub.add_parser("descargar", help="Descargar microdatos del DANE")
    d.add_argument("encuesta", choices=["geih", "eam", "eevv", "emicron", "ecv", "pobreza"])
    d.add_argument("--anios", nargs="+", type=int, help="Años (por defecto todos)")
    # Sin choices: los de las tres encuestas juntos daban un error en inglés con 29 nombres; _cmd_descargar
    # valida los de cada encuesta
    d.add_argument("--modulos", nargs="+", help="GEIH, EMICRON o ECV: módulos a bajar (por defecto todos)")
    d.add_argument("--empalme", action="store_true",
                   help="GEIH: serie de empalme 2010–2020. Pobreza: también los archivos para comparar 2012–2021 con el "
                        "marco 2018")
    d.add_argument("--limite", type=int, help="GEIH: máximo de archivos mensuales por año (pruebas)")
    d.add_argument("--tic", action="store_true", help="EAM: incluir módulo TIC 2008–2018")
    d.add_argument("--tipos", nargs="+", choices=list(eevv.TIPOS), help="Estadísticas Vitales (por defecto los tres)")
    d.add_argument("--archivos", nargs="+", choices=list(pobreza.ARCHIVOS),
                   help="Pobreza: hogares (basta para los indicadores) o personas (componentes del ingreso); por defecto "
                        "los dos. Desde 2023 vienen en el mismo ZIP")
    d.add_argument("--borrar-zips", action="store_true", help="Borrar los ZIP tras extraer")
    d.add_argument("--forzar", action="store_true",
                   help="Volver a bajar lo que ya está en disco (si el DANE corrigió los archivos)")
    d.set_defaults(fn=_cmd_descargar)
    return p


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.cmd is None:  # antes: «error: the following arguments are required: cmd»
        parser.print_help()
        return 0
    try:
        return args.fn(args)
    except KeyboardInterrupt:
        print("\nInterrumpido.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
