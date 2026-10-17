import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import dane_data as dd
from dane_data.cli import main as cli_main


def test_crecimiento_no_salta_anios():
    res = pd.DataFrame({"anio": [2014, 2015, 2018, 2019], "valor_agregado": [100.0, 110.0, 200.0, 220.0]})
    crec = dd.eam.crecimiento(res, "valor_agregado")["crec_valor_agregado"]
    assert crec.isna().tolist() == [True, False, True, False]      # 2018 no sigue a 2017
    assert crec.dropna().tolist() == pytest.approx([10.0, 10.0])
    por = pd.concat([res.assign(sector="A"), res.iloc[[0, 1]].assign(sector="B")])
    crec = dd.eam.crecimiento(por, "valor_agregado", por="sector")
    assert crec["crec_valor_agregado"].notna().sum() == 3


def test_deflactar_repetido_o_dos_veces():
    eam = pd.DataFrame({"anio": [2023, 2024], "valagri": [100.0, 110.0], "prodbr2": [200.0, 220.0]})
    ipp = pd.Series({2023: 100.0, 2024: 110.0})
    d = dd.eam.deflactar(dd.eam.deflactar(eam, ["valagri"], ipp), ["prodbr2"], ipp)   # antes: error de sufijos
    assert len(d) == 2 and d["prodbr2_real"].tolist() == pytest.approx([200.0, 200.0])
    assert [c for c in d.columns if c.startswith("deflactor")] == ["deflactor"]
    repetido = pd.DataFrame({"anio": [2023, 2023, 2024], "deflactor": [100.0, 101.0, 110.0]})
    with pytest.raises(ValueError, match="repite"):
        dd.eam.deflactar(eam, ["valagri"], repetido)


def test_eam_sin_departamento(tmp_path):
    """Un archivo sin columna de departamento: departamento vacío, no AttributeError."""
    archivo = tmp_path / "datos" / "2016" / "EAM_2016.csv"
    archivo.parent.mkdir(parents=True)
    archivo.write_text("nordest;ciiu4;valagri\n10;1011;80\n", encoding="utf-8")
    eam = dd.eam.load(2016, root=tmp_path)
    assert eam["departamento"].isna().all() and eam["sector"].notna().all()


def test_eam_load_harmonizes(eam_root):
    eam = dd.eam.load(root=eam_root)
    assert sorted(eam["anio"].unique()) == [1992, 2016, 2024]
    assert all(c == c.lower() for c in eam.columns)
    r = eam.set_index(["anio", "nordest"])
    assert r.loc[(1992, 10), "ciiu_rev"] == 2 and r.loc[(1992, 10), "sector"] == "Alimentos, bebidas y tabaco"
    assert r.loc[(1992, 20), "division"] == "38"  # código publicado a 2 dígitos
    assert r.loc[(2016, 30), "sector"] == "Bebidas"  # "110" = grupo de 3 dígitos
    assert r.loc[(2024, 10), "ciiu"] == "1011"  # 1011.0 de Stata -> "1011"
    assert r.loc[(2024, 10), "departamento"] == "Antioquia"
    assert not any(c.startswith("ciiu") and c not in ("ciiu", "ciiu_rev") for c in eam.columns)


def test_eam_resumen(eam_root):
    eam = dd.eam.load(root=eam_root)
    r = dd.eam.resumen(eam, por="anio").set_index("anio")
    assert r.loc[1992, "valor_agregado"] == 60
    assert r.loc[1992, "establecimientos"] == 2
    assert r.loc[1992, "productividad_laboral"] == pytest.approx(60 / 15)
    assert r.loc[1992, "participacion_laboral"] == pytest.approx(100 * 18 / 60)


def test_eam_resumen_sin_por(eam_root):
    eam = dd.eam.load(root=eam_root)
    r = dd.eam.resumen(eam, por=None)
    assert len(r) == 1
    assert r["valor_agregado"].item() == 300
    assert r["establecimientos"].item() == 3
    assert r["productividad_laboral"].item() == pytest.approx(300 / 48)


def test_eam_panel_and_survival(eam_root):
    eam = dd.eam.load(root=eam_root)
    bal = dd.eam.panel(eam, balanceado=True)
    assert set(bal.index.get_level_values("nordest")) == {10}
    s = dd.eam.supervivencia(eam)
    assert s["siguen_al_anio_siguiente"].tolist() == [1, 1]


def test_eam_deflactar(eam_root):
    eam = dd.eam.load(root=eam_root)
    defl = pd.Series({1992: 50.0, 2016: 100.0, 2024: 200.0})
    d = dd.eam.deflactar(eam, ["valagri"], defl)
    assert d.loc[d.anio.eq(2024), "valagri_real"].item() == pytest.approx(60)


def test_coma_decimal_minoritaria_no_se_pierde(tmp_path):
    """EAM 1998: casi todo entero, pero las plantas anonimizadas por promedio traen coma decimal."""
    filas = [f"{i};{i};5;3111;1998;100;60;40;10;8;10;2" for i in range(1, 301)]
    filas += ["301;301;5;3111;1998;83779570,6666667;42797617,3333333;40981953,3333333;10;8;10;2",
              "302;302;5;3111;1998;100;60;-2746,5;10;8;10;2"]
    encabezado = "nordemp;nordest;dpto;ciiu2;periodo;prodbr2;consin2;valagri;pertotal;pperytem;salpeyte;prespyte\n"
    (tmp_path / "datos" / "1998").mkdir(parents=True)
    (tmp_path / "datos" / "1998" / "EAM_1998.csv").write_text(encabezado + "\n".join(filas) + "\n", encoding="utf-8")
    eam = dd.eam.load(1998, root=tmp_path)
    assert eam["valagri"].notna().all()
    assert eam["valagri"].sum() == pytest.approx(300 * 40 + 40981953.3333333 - 2746.5)


def test_weighted_quantile():
    assert dd.weighted_quantile([1, 2, 3], [1, 1, 1], 0.5) == pytest.approx(2)
    assert dd.weighted_quantile([1, 10], [9, 1], 0.5) == pytest.approx(1)
    assert np.isnan(dd.weighted_quantile([], [], 0.5))


def test_diccionario_y_busqueda():
    assert "pensiones" in dd.describir("P6920").lower()
    res = dd.buscar_variable("pension")  # sin tilde también encuentra
    assert "P6920" in res["variable"].tolist()
    assert dd.diccionario("eam")["VALAGRI"]["etiqueta"] == "Valor agregado"


def test_config_persistence(tmp_path, monkeypatch):
    monkeypatch.setattr(dd.config, "CONFIG_FILE", tmp_path / "c.json")
    monkeypatch.setattr(dd.config, "_session", {})
    monkeypatch.delenv("DANE_DATA_EAM", raising=False)
    dd.set_paths(eam=tmp_path / "x", save=True)
    assert json.loads((tmp_path / "c.json").read_text())["eam"] == str(tmp_path / "x")
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("eam") == tmp_path / "x"
    monkeypatch.setenv("DANE_DATA_EAM", str(tmp_path / "env"))
    assert dd.get_path("eam") == tmp_path / "env"


def test_cli_estado(capsys, geih_root, eam_root, monkeypatch):
    monkeypatch.setattr(dd.config, "_session", {"geih": geih_root, "geih_empalme": geih_root / "no",
                                                "eam": eam_root})
    assert cli_main(["estado"]) == 0
    out = capsys.readouterr().out
    assert "GEIH principal" in out and "EAM: 3 años (1992–2024)" in out


class _DescargadorFalso:
    """Anota cómo lo construyen y qué años le piden, sin red."""

    creados = []

    def __init__(self, **kw):
        self.kw = kw
        _DescargadorFalso.creados.append(self)

    def run_pipeline(self, target_years=None, **kw):
        self.anios, self.extra = target_years, kw


@pytest.fixture
def descargador_falso(monkeypatch, tmp_path):
    _DescargadorFalso.creados = []
    monkeypatch.setattr(dd.geih, "GEIHDownloader", _DescargadorFalso)
    monkeypatch.setattr(dd.eam, "EAMDownloader", _DescargadorFalso)
    monkeypatch.setattr(dd.config, "_session", {"geih": tmp_path / "g", "geih_empalme": tmp_path / "e",
                                                "eam": tmp_path / "eam"})
    return _DescargadorFalso.creados


def test_cli_descargar_geih_y_eam(descargador_falso, tmp_path):
    assert cli_main(["descargar", "geih", "--anios", "2024", "2025", "--modulos", "ocupados",
                     "--empalme", "--limite", "1", "--borrar-zips"]) == 0
    dl = descargador_falso[-1]
    assert dl.anios == [2024, 2025] and dl.extra == {"limit_files": 1}
    assert dl.kw["base_dir"] == tmp_path / "e"              # empalme: su propia carpeta
    assert dl.kw["modules"] == ["ocupados"] and dl.kw["is_empalme"] and not dl.kw["keep_zips"]

    assert cli_main(["descargar", "eam", "--tic"]) == 0
    dl = descargador_falso[-1]
    assert dl.anios is None and dl.kw["include_tic"] and dl.kw["keep_zips"]
    assert dl.kw["base_dir"] == tmp_path / "eam"


@pytest.mark.parametrize("argv", [["descargar", "eam", "--modulos", "ocupados"], ["descargar", "eam", "--empalme"],
                                  ["descargar", "eam", "--limite", "1"], ["descargar", "geih", "--tic"]])
def test_cli_descargar_opciones_de_otra_encuesta(descargador_falso, capsys, argv):
    assert cli_main(argv) == 2
    assert "no aplica" in capsys.readouterr().err
    assert not descargador_falso                            # no descargó nada


def test_cli_config_avisa_variable_de_entorno(config_aislada, capsys, monkeypatch, tmp_path):
    monkeypatch.setenv("DANE_DATA_EAM", str(tmp_path / "env"))
    assert cli_main(["config", "--eam", str(tmp_path / "eam"), "--geih", str(tmp_path / "geih")]) == 0
    out = capsys.readouterr().out
    assert "DANE_DATA_EAM" in out and "DANE_DATA_GEIH " not in out


def test_download_un_anio_y_carpeta_explicita(descargador_falso, tmp_path):
    dd.geih.download(2024)
    assert descargador_falso[-1].anios == [2024]
    assert descargador_falso[-1].kw["base_dir"] == tmp_path / "g"
    dd.eam.download("2015", root=tmp_path / "otra")
    assert descargador_falso[-1].anios == ["2015"]
    assert descargador_falso[-1].kw["base_dir"] == tmp_path / "otra"


def test_cli_config_guarda_las_rutas(capsys, monkeypatch, tmp_path):
    archivo = tmp_path / "config" / "config.json"
    monkeypatch.setattr(dd.config, "CONFIG_FILE", archivo)
    monkeypatch.setattr(dd.config, "_session", {})
    for var in ("DANE_DATA_GEIH", "DANE_DATA_GEIH_EMPALME", "DANE_DATA_EAM"):
        monkeypatch.delenv(var, raising=False)
    assert cli_main(["config", "--geih", str(tmp_path / "geih"), "--eam", str(tmp_path / "eam")]) == 0
    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    assert Path(guardado["geih"]) == tmp_path / "geih" and Path(guardado["eam"]) == tmp_path / "eam"
    assert str(archivo) in capsys.readouterr().out
    monkeypatch.setattr(dd.config, "_session", {})
    assert dd.get_path("geih") == tmp_path / "geih"         # una sesión nueva lee el archivo


@pytest.fixture
def config_aislada(monkeypatch, tmp_path):
    archivo = tmp_path / "config" / "config.json"
    monkeypatch.setattr(dd.config, "CONFIG_FILE", archivo)
    monkeypatch.setattr(dd.config, "_session", {})
    for var in ("DANE_DATA_GEIH", "DANE_DATA_GEIH_EMPALME", "DANE_DATA_EAM"):
        monkeypatch.delenv(var, raising=False)
    return archivo


def test_set_paths_guarda_solo_lo_pedido(config_aislada, tmp_path):
    dd.set_paths(eam=tmp_path / "solo_sesion")                 # sin save: solo esta sesión
    dd.set_paths(geih=tmp_path / "geih", save=True)
    assert json.loads(config_aislada.read_text(encoding="utf-8")) == {"geih": str(tmp_path / "geih")}
    assert not list(config_aislada.parent.glob("*.tmp"))
    with pytest.raises(ValueError, match="vacía"):
        dd.set_paths(eam="  ", save=True)
    assert dd.get_path("eam") == tmp_path / "solo_sesion"     # el error no cambió nada


def test_config_que_no_es_un_objeto(config_aislada):
    config_aislada.parent.mkdir(parents=True)
    config_aislada.write_text("[1, 2]", encoding="utf-8")
    assert dd.get_path("geih") == dd.config.DEFAULT_HOME / "geih"
    dd.set_paths(eam="/datos/eam", save=True)
    assert json.loads(config_aislada.read_text(encoding="utf-8")) == {"eam": "/datos/eam"}


class _ProcesoFalso:
    def __init__(self, cmd, cwd=None, interrumpir=False):
        self.cmd, self.cwd, self.interrumpir, self.terminado = cmd, cwd, interrumpir, False

    def wait(self, timeout=None):
        if self.interrumpir and not self.terminado:
            raise KeyboardInterrupt
        return 0

    def terminate(self):
        self.terminado = True

    def poll(self):
        return 0


@pytest.mark.parametrize("interrumpir", [False, True])
def test_cli_app_lanza_streamlit(monkeypatch, capsys, interrumpir):
    from dane_data import cli

    procesos = []
    monkeypatch.setattr(cli.subprocess, "Popen",
                        lambda cmd, cwd=None: procesos.append(_ProcesoFalso(cmd, cwd, interrumpir)) or procesos[-1])
    monkeypatch.setattr(cli, "_puerto_libre", lambda p: p + 1)
    assert cli_main(["app", "--no-browser", "--port", "8600"]) == 0
    p = procesos[0]
    assert p.cmd[1:4] == ["-m", "streamlit", "run"] and p.cmd[4].endswith("Inicio.py")
    assert p.cmd[p.cmd.index("--server.port") + 1] == "8601"
    assert p.cmd[p.cmd.index("--server.address") + 1] == "localhost"
    assert Path(p.cwd).name == "app"                        # para que lea app/.streamlit/config.toml
    assert p.terminado == interrumpir                       # Ctrl+C cierra Streamlit
    out = capsys.readouterr().out
    assert "http://localhost:8601" in out and "sin contraseña" not in out

    assert cli_main(["app", "--no-browser", "--address", "0.0.0.0"]) == 0
    assert "sin contraseña" in capsys.readouterr().out      # compartida en la red: se avisa


def test_cli_ctrl_c_devuelve_130(monkeypatch, capsys):
    from dane_data import cli

    def interrumpido(args):
        raise KeyboardInterrupt

    monkeypatch.setattr(cli, "_cmd_estado", interrumpido)
    assert cli_main(["estado"]) == 130
    assert "Interrumpido" in capsys.readouterr().out


def test_python_m_dane_data():
    import subprocess
    import sys

    r = subprocess.run([sys.executable, "-m", "dane_data", "--help"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "dane-data" in r.stdout and "descargar" in r.stdout


def test_puerto_libre_salta_ocupado():
    import socket

    from dane_data.cli import _puerto_libre
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        s.listen()
        ocupado = s.getsockname()[1]
        assert _puerto_libre(ocupado) != ocupado


def test_abre_navegador_cuando_responde(monkeypatch):
    import http.server
    import subprocess
    import threading

    from dane_data import cli
    srv = http.server.HTTPServer(("127.0.0.1", 0), type("H", (http.server.BaseHTTPRequestHandler,), {
        "do_GET": lambda self: (self.send_response(200), self.end_headers()),
        "log_message": lambda *a: None}))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    abiertos = []
    monkeypatch.setattr(cli.webbrowser, "open", abiertos.append)
    proc = subprocess.Popen(["sleep", "30"])
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        cli._abrir_navegador_cuando_lista(url, proc, espera_max=10)
    finally:
        proc.kill()
        srv.shutdown()
    assert abiertos == [url]
