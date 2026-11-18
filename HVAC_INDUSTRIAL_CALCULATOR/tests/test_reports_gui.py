"""Generación de reportes y prueba de humo de la interfaz (sin pantalla: QT_QPA_PLATFORM=offscreen)."""
import os
import time

import pytest

from core.calculation import run_project
from validation.comparator import run_alternatives

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_pdf_and_excel(tmp_path, example_project, db, settings):
    from reports.pdf_report import generate_pdf
    from reports.excel_export import export_excel
    from pypdf import PdfReader
    import openpyxl
    r = run_project(example_project, db, settings)
    comp = run_alternatives(example_project, db, settings)
    pdf = generate_pdf(example_project, r, db, settings, str(tmp_path / "memoria.pdf"), comp)
    rd = PdfReader(pdf)
    assert len(rd.pages) >= 20
    text = " ".join(p.extract_text() or "" for p in rd.pages)
    for must in ("DICTAMEN Y RECOMENDACIONES DE INGENIERÍA", "Camino crítico", "Selección del ventilador",
                 "Hipótesis y limitaciones", "Comparador de alternativas", "Anexo A", "Página 2 de"):
        assert must in text, must
    xl = export_excel(example_project, r, db, settings, str(tmp_path / "res.xlsx"), comp)
    wb = openpyxl.load_workbook(xl)
    for sh in ("Resumen", "Aire", "Flujo y pérdidas", "Ventiladores", "Potencia", "Alertas", "Dictamen", "Comparador",
               "Trazabilidad", "Gráficos"):
        assert sh in wb.sheetnames, sh


def test_ip_units_report(tmp_path, example_project, db, settings):
    from reports.pdf_report import generate_pdf
    p = example_project.clone()
    p.units = "IP"
    r = run_project(p, db, settings)
    generate_pdf(p, r, db, settings, str(tmp_path / "ip.pdf"))
    assert os.path.getsize(tmp_path / "ip.pdf") > 50000


def test_project_roundtrip(tmp_path, example_project, check):
    from core.project import Project
    f = tmp_path / "p.hvac.json"
    example_project.save(str(f))
    q = Project.load(str(f))
    assert q.to_dict()["network"] == example_project.to_dict()["network"]
    check("ida y vuelta JSON: n.º de alternativas", {}, len(example_project.alternatives), len(q.alternatives), 0,
          reference="Persistencia")


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _wait(app, cond, timeout=60):
    t = time.time()
    while not cond() and time.time() - t < timeout:
        app.processEvents()
        time.sleep(0.02)
    return cond()


def test_gui_smoke(qapp, example_project, db, settings, tmp_path):
    from interface.main_window import MainWindow
    from interface.widgets import UnitContext
    w = MainWindow(db, settings.copy(), example_project.clone(), None)
    w.resize(1500, 950)
    w.show()
    assert _wait(qapp, lambda: w.ctx.results is not None)
    shots = os.path.join(ROOT, "tests", "results", "screens")
    os.makedirs(shots, exist_ok=True)
    for i in range(12):
        w.nav.setCurrentRow(i)
        for _ in range(20):
            qapp.processEvents()
        w.grab().save(os.path.join(shots, f"{i:02d}.png"))
    # editar la temperatura del aire desde el control → el proyecto cambia y se recalcula
    air_page = w.pages[1]
    first = w.ctx.results
    air_page.t.edit.setText("35")
    air_page.t._commit()
    assert abs(w.ctx.project.air.t_c - 35.0) < 1e-9
    w.calculate()
    assert _wait(qapp, lambda: w.ctx.results is not first and w.ctx.results.air.t_c == 35.0)
    # cambio a unidades imperiales: los campos muestran °F
    w.set_units("IP")
    assert UnitContext.system == "IP"
    assert abs(float(air_page.t.edit.text()) - 95.0) < 1e-6
    w.set_units("SI")
    # guardar y abrir
    w.path = str(tmp_path / "gui.hvac.json")
    assert w.save()
    assert os.path.exists(w.path)
    w.dirty = False
    w.close()
