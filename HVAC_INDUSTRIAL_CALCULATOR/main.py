"""HVAC INDUSTRIAL ENGINEERING CALCULATOR — punto de entrada.

Uso:
    python main.py                      # abre el banco de pruebas industrial
    python main.py proyecto.hvac.json   # abre un proyecto
    python main.py --nuevo              # proyecto nuevo con red mínima
    python main.py --verificar          # sin interfaz: calcula el banco de pruebas y genera la memoria PDF
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def verify() -> int:
    """Verificación de instalación sin interfaz gráfica."""
    import tempfile
    from config.settings import load_settings, app_root
    from core.calculation import run_project
    from core.project import Project
    from database.db import load_db
    from reports.pdf_report import generate_pdf
    p = Project.load(os.path.join(app_root(), "examples", "nave_industrial_4_campanas.hvac.json"))
    r = run_project(p, load_db(), load_settings())
    errs = {k: v for k, v in r.errors.items() if not k.startswith("trace")}
    out = os.path.join(tempfile.gettempdir(), "hvac_verificacion.pdf")
    generate_pdf(p, r, load_db(), load_settings(), out)
    fe = r.selected_fan
    print(f"Densidad del aire: {r.air.rho:.4f} kg/m³")
    print(f"Diseño: Q = {r.network_design.state.Q_fan:.4f} m³/s, FTP = {r.network_design.state.FTP:.1f} Pa")
    if fe and fe.op:
        print(f"Operación: Q = {fe.op.Q:.4f} m³/s, FTP = {fe.op.FTP:.1f} Pa")
    print(f"Dictamen: {r.dictamen.decision}")
    print(f"Memoria PDF de verificación: {out}")
    print("Errores:", errs or "ninguno")
    return 1 if errs else 0


def main() -> int:
    if "--verificar" in sys.argv:
        return verify()
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QIcon, QFont
    from PySide6.QtWidgets import QApplication, QMessageBox

    from config.settings import load_settings, app_root
    from core.project import Project
    from database.db import load_db
    from interface.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("HVAC Industrial Engineering Calculator")
    app.setOrganizationName("HVAC_IEC")
    icon = os.path.join(app_root(), "assets", "icon.png")
    if os.path.exists(icon):
        app.setWindowIcon(QIcon(icon))
    settings = load_settings()
    db = load_db()
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    project, path = None, None
    try:
        if args:
            path = args[0]
            project = Project.load(path)
        elif "--nuevo" not in sys.argv:
            path = os.path.join(app_root(), "examples", "nave_industrial_4_campanas.hvac.json")
            project = Project.load(path) if os.path.exists(path) else None
            path = None   # el ejemplo no se sobrescribe: "Guardar" pedirá un nombre nuevo
    except Exception as exc:  # noqa: BLE001
        QMessageBox.critical(None, "Error", f"No se pudo abrir el proyecto:\n{exc}")
        project, path = None, None
    win = MainWindow(db, settings, project, path)
    win.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
