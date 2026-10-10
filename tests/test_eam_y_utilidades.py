import json

import numpy as np
import pandas as pd
import pytest

import dane_data as dd
from dane_data.cli import main as cli_main


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
