import os

import pytest

from tanque_pulmon.caso import CasoUsuario, Magnitud
from tanque_pulmon.reporte import a_texto, ejecutar, exportar_excel, exportar_pdf

CASOS = os.path.join(os.path.dirname(__file__), "..", "casos")
CASO3 = os.path.join(CASOS, "PCGV-DM-014_caso3_ESCENARIO_FAD300.json")


def test_ida_y_vuelta_json(tmp_path):
    c = CasoUsuario.cargar(CASO3)
    ruta = tmp_path / "c.json"
    c.guardar(ruta)
    c2 = CasoUsuario.cargar(ruta)
    assert c2.to_dict() == c.to_dict() and c2.huella() == c.huella()


def test_huella_cambia_con_entradas():
    c = CasoUsuario.cargar(CASO3)
    h = c.huella()
    c.t_aire = Magnitud(35.0, "°C")
    assert c.huella() != h


def test_exportaciones(tmp_path):
    inf = ejecutar(CasoUsuario.cargar(CASO3))
    pdf, xlsx = exportar_pdf(inf, str(tmp_path / "r.pdf")), exportar_excel(inf, str(tmp_path / "r.xlsx"))
    assert os.path.getsize(pdf) > 2000 and open(pdf, "rb").read(4) == b"%PDF"
    from openpyxl import load_workbook
    wb = load_workbook(xlsx)
    assert set(wb.sheetnames) == {"Entradas", "Resultados", "Verificaciones", "Ecuaciones y avisos"}
    txt = a_texto(inf)
    assert inf.huella in txt and "Categoría III" in txt


def test_verificacion_retencion_no_cumple():
    c = CasoUsuario.cargar(os.path.join(CASOS, "PCGV-DM-014_caso2_casa_filtros_200Nm3h.json"))
    inf = ejecutar(c)
    v = [x for x in inf.verificaciones if x.criterio == "Tiempo de retención"][0]
    assert v.estado == "NO CUMPLE"
