"""Memoria de cálculo: datos del proyecto, dictamen, comparador de alternativas y exportación."""
from __future__ import annotations

import copy
import os

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QLineEdit, QTextEdit, QTextBrowser, QPushButton, QHBoxLayout, QVBoxLayout, QWidget,
                               QFileDialog, QMessageBox, QInputDialog, QTabWidget, QApplication)
from PySide6.QtCore import Qt

from core.project import Alternative, Project
from graphics.plots import plot_alternatives
from reports import tables as T
from validation.comparator import run_alternatives
from validation.decision_engine import DEC_COLORS
from ..editable_table import EditableTable, Col
from ..widgets import group, note, ResultTable, PlotCanvas
from .base import BasePage, header, hrow


class ReportPage(BasePage):
    modules = []

    def __init__(self, ctx, main=None):
        super().__init__(ctx)
        self.main = main
        self.lay.addWidget(header("Memoria de cálculo y dictamen", "Datos del proyecto, DICTAMEN Y RECOMENDACIONES DE "
                                  "INGENIERÍA, comparador de alternativas y exportación a PDF y Excel."))
        g, f = group("Datos generales del proyecto")
        self.fields = {}
        for key, lbl in (("name", "Nombre del proyecto"), ("client", "Cliente"), ("location", "Ubicación"),
                         ("engineer", "Elaboró"), ("reviewer", "Revisó"), ("date", "Fecha"), ("revision", "Revisión"),
                         ("ventilation_type", "Tipo de ventilación")):
            w = QLineEdit()
            w.editingFinished.connect(lambda k=key, ww=w: self._info(k, ww.text()))
            self.fields[key] = w
            f.addRow(lbl, w)
        self.desc = QTextEdit()
        self.desc.setFixedHeight(70)
        self.obj = QTextEdit()
        self.obj.setFixedHeight(60)
        f.addRow("Descripción del sistema", self.desc)
        f.addRow("Objetivo del diseño", self.obj)
        self.desc.textChanged.connect(lambda: self._info("description", self.desc.toPlainText()))
        self.obj.textChanged.connect(lambda: self._info("objective", self.obj.toPlainText()))
        eg, el = group("Exportación", QVBoxLayout())
        b_pdf = QPushButton("Generar memoria PDF…")
        b_pdf.setObjectName("primary")
        b_xl = QPushButton("Exportar resultados a Excel…")
        b_pdf.clicked.connect(self.export_pdf)
        b_xl.clicked.connect(self.export_excel)
        el.addWidget(b_pdf)
        el.addWidget(b_xl)
        el.addWidget(note("La memoria incluye ecuaciones, sustituciones, unidades, fuentes, gráficas, advertencias, "
                          "referencias, hipótesis, dictamen, comparador, recomendaciones constructivas, anexo de "
                          "trazabilidad y anexo de validación del software."))
        el.addStretch(1)
        self.lay.addWidget(hrow(g, eg))
        dg, dl = group("DICTAMEN Y RECOMENDACIONES DE INGENIERÍA", QVBoxLayout())
        self.dict = QTextBrowser()
        self.dict.setMinimumHeight(520)
        dl.addWidget(self.dict)
        self.lay.addWidget(dg)
        cg, cl = group("Comparador de alternativas de diseño (mínimo 3)", QVBoxLayout())
        cl.addWidget(note("Guarde el estado actual del proyecto como alternativa, modifique el diseño (diámetros, "
                          "ventilador, velocidad…) y guarde otra. El comparador excluye primero las alternativas con riesgo "
                          "crítico, déficit de caudal o velocidad de transporte insuficiente y luego puntúa energía, "
                          "desempeño, riesgo, instalación y mantenimiento (pesos en Configuración)."))
        self.alts = EditableTable([Col("name", "Alternativa", width=330), Col("complexity", "Complejidad de instalación (1–5)", "int"),
                                   Col("maintenance", "Dificultad de mantenimiento (1–5)", "int"),
                                   Col("notes", "Notas", width=360)], self.ctx.project.alternatives, allow_move=True)
        self.alts.setMinimumHeight(180)
        self.alts.changed.connect(self.emit_changed)
        bsave = QPushButton("Guardar estado actual como alternativa")
        bload = QPushButton("Cargar alternativa seleccionada al proyecto")
        bcmp = QPushButton("Comparar alternativas")
        bcmp.setObjectName("primary")
        bsave.clicked.connect(self._save_alt)
        bload.clicked.connect(self._load_alt)
        bcmp.clicked.connect(self.compare)
        for b in (bsave, bload, bcmp):
            self.alts.extra_bar.addWidget(b)
        cl.addWidget(self.alts)
        self.cmp = ResultTable()
        self.cmp.setMinimumHeight(200)
        cl.addWidget(self.cmp)
        self.concl = QTextBrowser()
        self.concl.setMinimumHeight(140)
        cl.addWidget(self.concl)
        self.p_alt = PlotCanvas(300)
        cl.addWidget(self.p_alt)
        self.lay.addWidget(cg)
        rg, rl = group("Recomendaciones constructivas y de instalación", QVBoxLayout())
        self.cons = ResultTable()
        self.cons.setMinimumHeight(300)
        rl.addWidget(self.cons)
        self.lay.addWidget(rg)

    def load(self):
        self._loading = True
        info = self.ctx.project.info
        for k, w in self.fields.items():
            w.setText(str(getattr(info, k) or ""))
        self.desc.setPlainText(info.description)
        self.obj.setPlainText(info.objective)
        self.alts.set_items(self.ctx.project.alternatives)
        self._loading = False
        if self.ctx.comparison:
            self._show_comparison()

    def _info(self, k, v):
        if self._loading:
            return
        if getattr(self.ctx.project.info, k) != v:
            setattr(self.ctx.project.info, k, v)
            self.emit_changed()

    def _save_alt(self):
        name, ok = QInputDialog.getText(self, "Nueva alternativa", "Nombre de la alternativa:",
                                        text=f"Alternativa {len(self.ctx.project.alternatives) + 1}")
        if not ok or not name:
            return
        self.ctx.project.alternatives.append(Alternative(name, copy.deepcopy(self.ctx.project.to_dict(include_alternatives=False))))
        self.alts.rebuild()
        self.emit_changed()

    def _load_alt(self):
        i = self.alts.current_index()
        if not (0 <= i < len(self.ctx.project.alternatives)):
            return
        alt = self.ctx.project.alternatives[i]
        if QMessageBox.question(self, "Cargar alternativa", f"¿Reemplazar los datos actuales por '{alt.name}'? "
                                "(las alternativas guardadas se conservan)") != QMessageBox.Yes:
            return
        alts = self.ctx.project.alternatives
        new = Project.from_dict(copy.deepcopy(alt.project))
        new.alternatives = alts
        if self.main:
            self.main.set_project(new, keep_path=True)

    def compare(self):
        if len(self.ctx.project.alternatives) < 3:
            QMessageBox.information(self, "Comparador", "Guarde al menos tres alternativas para compararlas.")
            return
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.ctx.comparison = run_alternatives(self.ctx.project, self.ctx.db, self.ctx.settings)
        finally:
            QApplication.restoreOverrideCursor()
        self._show_comparison()

    def _show_comparison(self):
        mets, concl = self.ctx.comparison
        self.cmp.set_data(*T.comparison_table(mets, self.ctx.project, self.ctx.system))
        self.concl.setHtml("<br>".join(concl))
        self.p_alt.set_figure(plot_alternatives(mets, self.ctx.system))

    def export_pdf(self):
        if self.ctx.results is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Guardar memoria PDF", f"{self.ctx.project.info.name}.pdf", "PDF (*.pdf)")
        if not path:
            return
        from reports.pdf_report import generate_pdf
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            if self.ctx.comparison is None and len(self.ctx.project.alternatives) >= 3:
                self.ctx.comparison = run_alternatives(self.ctx.project, self.ctx.db, self.ctx.settings)
            generate_pdf(self.ctx.project, self.ctx.results, self.ctx.db, self.ctx.settings, path, self.ctx.comparison,
                         self.ctx.settings.data.get("report", {}).get("include_traces", True))
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"No se pudo generar el PDF:\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def export_excel(self):
        if self.ctx.results is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Exportar Excel", f"{self.ctx.project.info.name}.xlsx", "Excel (*.xlsx)")
        if not path:
            return
        from reports.excel_export import export_excel
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            export_excel(self.ctx.project, self.ctx.results, self.ctx.db, self.ctx.settings, path, self.ctx.comparison)
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error", f"No se pudo exportar:\n{exc}")
            return
        QApplication.restoreOverrideCursor()
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def render(self):
        r = self.ctx.results
        if r is None or r.dictamen is None:
            return
        d = r.dictamen
        esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
        html = (f"<div style='background:{DEC_COLORS[d.decision_code]};color:white;padding:8px;font-size:12pt'>"
                f"<b>Decisión técnica: {esc(d.decision)}</b></div>")
        for t, items in [("1. Descripción del sistema analizado", d.description), ("2. Objetivo del diseño", d.objective),
                         ("3. Datos de entrada e hipótesis", d.inputs), ("4. Resultados principales", d.results),
                         ("5. Evaluación de los resultados", d.evaluation), ("6. Problemas o desviaciones identificados", d.problems),
                         ("7. Decisión técnica", [d.decision]), ("8. Modificaciones recomendadas", d.modifications),
                         ("9. Alternativas que conviene estudiar", d.alternatives),
                         ("10. Información pendiente para cerrar el diseño", d.pending),
                         ("11. Referencias técnicas utilizadas", d.references),
                         ("12. Limitaciones y alcance del dictamen", d.limitations)]:
            html += f"<h3 style='color:#14213D'>{t}</h3><ul>" + "".join(f"<li>{esc(x)}</li>" for x in (items or ["—"])) + "</ul>"
        self.dict.setHtml(html)
        self.cons.set_data(["Tema", "Recomendación", "Tipo", "Fuente"],
                           [[c.topic, c.text, c.kind, c.source] for c in r.construction])
