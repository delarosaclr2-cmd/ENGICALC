"""El esquema y la memoria reflejan los resultados del motor (no recalculan por su cuenta)."""
import glob
import json
import os

import pytest

from linea_gas import unidades as u
from linea_gas.caso import ejecutar
from linea_gas.memoria import evaluar
from linea_gas.motor import perfil_presion
from linea_gas.ui.memoria_pdf import exportar_excel, exportar_pdf

CASOS = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos", "*.json")))


@pytest.mark.parametrize("ruta", CASOS, ids=os.path.basename)
def test_perfil_termina_en_la_presion_de_salida(ruta):
    e, r = ejecutar(json.load(open(ruta, encoding="utf-8")))
    perfil = perfil_presion(e, r, 40)
    assert perfil[0][1] == pytest.approx(e.p_entrada_pa, rel=1e-9)
    assert perfil[-1][1] == pytest.approx(r.p_salida_pa, rel=1e-6)
    assert all(b[1] <= a[1] for a, b in zip(perfil, perfil[1:]))      # la presión no sube


def test_esquema_muestra_las_presiones_calculadas():
    c = json.load(open(CASOS[0], encoding="utf-8"))
    e, r = ejecutar(c)
    m = evaluar(c)
    textos = " ".join(m.escena.textos())
    assert f"{r.p_salida_pa / u.PSI:.3f}" in textos
    assert m.escena.a_svg().startswith("<svg")


def test_memoria_pdf_y_excel(tmp_path):
    m = evaluar(json.load(open(CASOS[0], encoding="utf-8")))
    exportar_pdf(m, str(tmp_path / "m.pdf"))
    exportar_excel(m, str(tmp_path / "m.xlsx"))
    assert (tmp_path / "m.pdf").stat().st_size > 20000 and (tmp_path / "m.xlsx").stat().st_size > 4000
