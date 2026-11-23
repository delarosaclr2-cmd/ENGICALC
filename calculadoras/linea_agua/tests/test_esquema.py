"""El esquema y la memoria reflejan los resultados del motor."""
import glob
import json
import os

import pytest

from linea_agua.memoria import evaluar
from linea_agua.motor import calcular
from linea_agua.ui.memoria_pdf import exportar_excel, exportar_pdf

CASOS = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos", "*.json")))


@pytest.mark.parametrize("ruta", CASOS, ids=os.path.basename)
def test_esquema_muestra_la_velocidad_calculada(ruta):
    c = json.load(open(ruta, encoding="utf-8"))
    r = calcular(c)
    v = r["tramo"]["v"] if "tramo" in r else max(r["v1"], r["v2"])
    m = evaluar(c)
    assert f"{v:.2f}" in m.escena.textos()
    assert m.escena.a_svg().startswith("<svg")
    assert [x[3] for x in m.verificaciones] == [x[3] for x in r["verificaciones"]]


def test_memoria_pdf_y_excel(tmp_path):
    m = evaluar(json.load(open(CASOS[0], encoding="utf-8")))
    exportar_pdf(m, str(tmp_path / "m.pdf"))
    exportar_excel(m, str(tmp_path / "m.xlsx"))
    assert (tmp_path / "m.pdf").stat().st_size > 20000 and (tmp_path / "m.xlsx").stat().st_size > 4000
