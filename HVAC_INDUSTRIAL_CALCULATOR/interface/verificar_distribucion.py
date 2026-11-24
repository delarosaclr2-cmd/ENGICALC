"""Prueba del ejecutable Qt, activada únicamente por argumento de diagnóstico."""
from __future__ import annotations

import json
import os
from pathlib import Path
import time
import traceback


def comprobar(carpeta: str) -> int:
    salida = Path(carpeta).resolve()
    salida.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    os.environ['ENGICALC_HVAC_DATOS'] = str(salida / 'perfil')
    informe = {'correcto': False, 'paginas': 0}
    ventana = None
    try:
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        from config.settings import app_root, load_settings
        from database.db import load_db
        from core.project import Project
        from interface.main_window import MainWindow
        from reports.pdf_report import generate_pdf
        from reports.excel_export import export_excel

        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, str(salida / 'perfil'))
        app = QApplication.instance() or QApplication([])
        proyecto = Project.load(os.path.join(app_root(), 'examples', 'nave_industrial_4_campanas.hvac.json'))
        db, settings = load_db(), load_settings()
        settings.data['app']['autosave_minutes'] = 0
        ventana = MainWindow(db, settings, proyecto, None)
        limite = time.monotonic() + 60
        while ventana.ctx.results is None and time.monotonic() < limite:
            app.processEvents()
            time.sleep(0.02)
        if ventana.ctx.results is None:
            raise RuntimeError('HVAC no terminó de calcular en 60 segundos')
        for i in range(12):
            ventana.nav.setCurrentRow(i)
            app.processEvents()
            informe['paginas'] += 1
        errores = {k: v for k, v in ventana.ctx.results.errors.items() if not k.startswith('trace')}
        if errores:
            raise RuntimeError(str(errores))
        pdf = Path(generate_pdf(proyecto, ventana.ctx.results, db, settings, str(salida / 'hvac.pdf')))
        excel = Path(export_excel(proyecto, ventana.ctx.results, db, settings, str(salida / 'hvac.xlsx')))
        if not pdf.read_bytes().startswith(b'%PDF-') or not excel.read_bytes().startswith(b'PK'):
            raise RuntimeError('Reportes HVAC inválidos')
        informe['correcto'] = True
    except Exception:
        informe['error'] = traceback.format_exc()
    finally:
        if ventana is not None:
            if ventana.calc_thread is not None:
                ventana.calc_thread.wait(60000)
            ventana.dirty = False
            ventana.close()
        (salida / 'resultado.json').write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if informe['correcto'] else 1
