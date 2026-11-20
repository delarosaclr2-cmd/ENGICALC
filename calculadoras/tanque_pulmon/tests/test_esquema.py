"""El esquema y la memoria del tanque reflejan los resultados del motor."""
import glob
import json
import os

import pytest

from tanque_pulmon.caso import CasoUsuario
from tanque_pulmon.memoria import evaluar
from tanque_pulmon.reporte import ejecutar
from tanque_pulmon.ui.memoria_pdf import exportar_excel, exportar_pdf

CASOS = sorted(glob.glob(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos", "*.json")))


@pytest.mark.parametrize("ruta", CASOS, ids=os.path.basename)
def test_grafica_usa_los_tiempos_calculados(ruta):
    d = json.load(open(ruta, encoding="utf-8"))
    r = ejecutar(CasoUsuario.from_dict(d)).resultados
    m = evaluar(d)
    textos = " ".join(m.escena.textos())
    if r.t_carga_min:
        assert f"vacío {r.t_retencion_min:.2f} min" in textos and f"{r.ciclos_por_hora:.2f} ciclos/h" in textos
    else:
        assert f"t = {r.t_retencion_min:.2f} min" in textos
    assert "NOM-020" in textos
    assert [v[3] for v in m.verificaciones] == [v.estado for v in ejecutar(CasoUsuario.from_dict(d)).verificaciones]


def test_memoria_pdf_y_excel(tmp_path):
    m = evaluar(json.load(open(CASOS[0], encoding="utf-8")))
    exportar_pdf(m, str(tmp_path / "m.pdf"))
    exportar_excel(m, str(tmp_path / "m.xlsx"))
    assert (tmp_path / "m.pdf").stat().st_size > 20000 and (tmp_path / "m.xlsx").stat().st_size > 4000
