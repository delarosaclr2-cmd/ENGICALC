"""Componentes reutilizables de la interfaz (sin ecuaciones de ingeniería)."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QColor, QGuiApplication, QCursor
from PySide6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLineEdit, QLabel, QComboBox, QCheckBox, QGroupBox,
                               QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QPushButton,
                               QFileDialog, QFrame, QTextBrowser, QToolTip, QSizePolicy, QMenu)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from core import units as U
from validation.alerts import LEVEL_COLORS, LEVELS, count_by_level
from validation.decision_engine import DEC_COLORS


class UnitContext:
    """Sistema de unidades actual compartido por todos los campos."""
    system = "SI"
    listeners: list = []

    @classmethod
    def set(cls, system: str):
        cls.system = system
        for fn in list(cls.listeners):
            try:
                fn()
            except RuntimeError:
                cls.listeners.remove(fn)


def parse_float(txt: str) -> float | None:
    t = (txt or "").strip().replace(" ", "")
    if not t:
        return None
    if t.count(",") == 1 and "." not in t:
        t = t.replace(",", ".")
    else:
        t = t.replace(",", "")
    return float(t)


class QField(QWidget):
    """Campo numérico con unidad. Guarda el valor en SI y lo muestra en el sistema activo."""
    changed = Signal(object)

    def __init__(self, quantity: str | None = None, value_si: float | None = None, optional: bool = False,
                 minimum: float | None = None, maximum: float | None = None, digits: int = 5, unit_override: str | None = None,
                 scale: float = 1.0, width: int = 110):
        super().__init__()
        self.quantity = quantity
        self.optional = optional
        self.minimum, self.maximum = minimum, maximum
        self.digits = digits
        self.unit_override = unit_override
        self.scale = scale        # para mostrar fracciones como % (scale = 100)
        self._si = value_si
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        self.edit = QLineEdit()
        self.edit.setFixedWidth(width)
        self.edit.setAlignment(Qt.AlignRight)
        self.unit = QLabel()
        self.unit.setObjectName("note")
        self.unit.setMinimumWidth(52)
        lay.addWidget(self.edit)
        lay.addWidget(self.unit)
        lay.addStretch(1)
        self.edit.editingFinished.connect(self._commit)
        UnitContext.listeners.append(self.refresh)
        self.refresh()

    def _unit(self):
        if self.unit_override is not None:
            return self.unit_override
        return U.display_unit(self.quantity, UnitContext.system) if self.quantity else ""

    def refresh(self):
        self.unit.setText(self._unit())
        if self._si is None:
            self.edit.setText("")
            return
        v = self._si
        if self.quantity and self.unit_override is None:
            v = U.to_display(v, self.quantity, UnitContext.system)
        v = v * self.scale
        self.edit.setText(f"{v:.6g}")

    def _commit(self):
        try:
            v = parse_float(self.edit.text())
        except ValueError:
            self.edit.setProperty("invalid", True)
            self.edit.style().polish(self.edit)
            return
        self.edit.setProperty("invalid", False)
        self.edit.style().polish(self.edit)
        if v is None:
            if not self.optional:
                self.refresh()
                return
            new = None
        else:
            v = v / self.scale
            new = U.from_display(v, self.quantity, UnitContext.system) if (self.quantity and self.unit_override is None) else v
            if self.minimum is not None and new < self.minimum:
                self.edit.setProperty("invalid", True)
                self.edit.style().polish(self.edit)
                self.edit.setToolTip(f"Valor mínimo: {self.minimum}")
                return
            if self.maximum is not None and new > self.maximum:
                self.edit.setProperty("invalid", True)
                self.edit.style().polish(self.edit)
                self.edit.setToolTip(f"Valor máximo: {self.maximum}")
                return
        if new != self._si:
            self._si = new
            self.refresh()
            self.changed.emit(new)

    def value(self):
        return self._si

    def set_value(self, v):
        self._si = v
        self.refresh()


def combo(items: list[tuple[str, str]], current: str | None = None) -> QComboBox:
    c = QComboBox()
    for key, label in items:
        c.addItem(label, key)
    if current is not None:
        set_combo(c, current)
    return c


def set_combo(c: QComboBox, key):
    i = c.findData(key)
    if i >= 0:
        c.blockSignals(True)
        c.setCurrentIndex(i)
        c.blockSignals(False)


def group(title: str, layout=None) -> tuple[QGroupBox, QFormLayout]:
    g = QGroupBox(title)
    f = layout or QFormLayout()
    if isinstance(f, QFormLayout):
        f.setLabelAlignment(Qt.AlignLeft)
        f.setHorizontalSpacing(14)
        f.setVerticalSpacing(7)
    g.setLayout(f)
    return g, f


def note(text: str) -> QLabel:
    lb = QLabel(text)
    lb.setObjectName("note")
    lb.setWordWrap(True)
    return lb


class ResultTable(QTableWidget):
    """Tabla de solo lectura con copiar al portapapeles."""

    def __init__(self, hdr=None, rows=None, stretch_last=True):
        super().__init__()
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)
        self.setWordWrap(True)
        self.horizontalHeader().setStretchLastSection(stretch_last)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        if hdr is not None:
            self.set_data(hdr, rows or [])

    def set_data(self, hdr, rows, colors: dict | None = None):
        self.clear()
        self.setColumnCount(len(hdr))
        self.setRowCount(len(rows))
        self.setHorizontalHeaderLabels([str(h) for h in hdr])
        for i, r in enumerate(rows):
            for j, v in enumerate(r):
                it = QTableWidgetItem("" if v is None else str(v))
                it.setToolTip(str(v))
                if colors and (i, j) in colors:
                    it.setForeground(QColor(colors[(i, j)]))
                    f = it.font()
                    f.setBold(True)
                    it.setFont(f)
                self.setItem(i, j, it)
        self.resizeColumnsToContents()
        for j in range(self.columnCount()):
            if self.columnWidth(j) > 320:
                self.setColumnWidth(j, 320)
        self.resizeRowsToContents()

    def _menu(self, pos):
        m = QMenu(self)
        a = m.addAction("Copiar tabla")
        if m.exec(self.mapToGlobal(pos)) == a:
            self.copy_all()

    def copy_all(self):
        lines = ["\t".join(self.horizontalHeaderItem(j).text() for j in range(self.columnCount()))]
        for i in range(self.rowCount()):
            lines.append("\t".join(self.item(i, j).text() if self.item(i, j) else "" for j in range(self.columnCount())))
        QGuiApplication.clipboard().setText("\n".join(lines))


class AlertsView(QWidget):
    def __init__(self, modules: list[str] | None = None):
        super().__init__()
        self.modules = modules
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.summary = QLabel()
        self.summary.setObjectName("note")
        self.table = ResultTable()
        lay.addWidget(self.summary)
        lay.addWidget(self.table)

    def set_alerts(self, alerts, system="SI"):
        al = [a for a in alerts if self.modules is None or a.module in self.modules]
        cnt = count_by_level(al)
        self.summary.setText("  ·  ".join(f"<b style='color:{LEVEL_COLORS[k]}'>{k}</b> {v}" for k, v in cnt.items() if v)
                             or "Sin alertas para este módulo.")
        hdr = ["Nivel", "Parámetro", "Elemento", "Qué se detectó", "Valor", "Criterio", "Consecuencia", "Recomendación",
               "Fuente / base"]
        rows, colors = [], {}
        for i, a in enumerate(al):
            rows.append([a.level, a.parameter, a.item, a.detected, a.value_str(system), a.criterion, a.consequence,
                         a.recommendation, f"{a.source} ({a.basis})" if a.source else a.basis])
            colors[(i, 0)] = LEVEL_COLORS[a.level]
        self.table.set_data(hdr, rows, colors)


class DecisionPanel(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        self.badge = QLabel("—")
        self.badge.setObjectName("badge")
        self.badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        self.text = QTextBrowser()
        self.text.setMinimumHeight(140)
        lay.addWidget(QLabel("<b>Decisión técnica del módulo</b>"))
        lay.addWidget(self.badge)
        lay.addWidget(self.text)

    def set_decision(self, d):
        if d is None:
            self.badge.setText("Sin cálculo")
            self.badge.setStyleSheet("background:#5B6577;")
            self.text.setHtml("")
            return
        self.badge.setText(d.decision)
        self.badge.setStyleSheet(f"background:{d.color};")
        esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
        html = f"<p><b>A. Diagnóstico.</b> {' '.join(esc(x) for x in d.diagnosis)} <i>¿Viable?</i> {esc(d.viable)}</p>"
        if d.satisfactory:
            html += "<p><b>Satisfactorio:</b><br>" + "<br>".join("✔ " + esc(x) for x in d.satisfactory) + "</p>"
        if d.problems:
            html += "<p><b>Problemas:</b><br>" + "<br>".join("• " + esc(x) for x in d.problems) + "</p>"
        html += "<p><b>C. Justificación.</b><br>" + "<br>".join(esc(x) for x in d.justification) + "</p>"
        html += "<p><b>D. Acción recomendada.</b><br>" + "<br>".join("→ " + esc(x) for x in d.actions) + "</p>"
        self.text.setHtml(html)


class TracePanel(ResultTable):
    def set_steps(self, steps):
        hdr = ["Cálculo", "Ecuación", "Variables", "Sustitución", "Resultado", "Fuente", "Tipo"]
        rows = [[s.title, s.equation, "; ".join(v.text() for v in s.variables), s.substitution, s.result_text(), s.source,
                 s.kind] for s in steps]
        self.set_data(hdr, rows)


class PlotCanvas(QWidget):
    """Lienzo Matplotlib con barra de herramientas, exportación PNG y tooltip al pasar el cursor."""

    def __init__(self, min_height=360):
        super().__init__()
        self.lay = QVBoxLayout(self)
        self.lay.setContentsMargins(0, 0, 0, 0)
        self.canvas = None
        self.toolbar = None
        self.fig = None
        self.setMinimumHeight(min_height)
        self.placeholder = QLabel("El gráfico se mostrará después del cálculo.")
        self.placeholder.setObjectName("note")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.lay.addWidget(self.placeholder)

    def set_figure(self, fig):
        if self.canvas is not None:
            self.lay.removeWidget(self.canvas)
            self.lay.removeWidget(self.toolbar)
            self.canvas.setParent(None)
            self.toolbar.setParent(None)
        if self.placeholder is not None:
            self.placeholder.setParent(None)
            self.placeholder = None
        self.fig = fig
        self.canvas = FigureCanvasQTAgg(fig)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.lay.addWidget(self.toolbar)
        self.lay.addWidget(self.canvas)
        self.canvas.mpl_connect("motion_notify_event", self._hover)
        self.canvas.draw_idle()

    def _hover(self, ev):
        if self.fig is None or ev.inaxes is None:
            QToolTip.hideText()
            return
        best = None
        for kind, ax, xs, ys, labels in getattr(self.fig, "_hover", []):
            if ax is not ev.inaxes:
                continue
            if kind == "line":
                pts = ax.transData.transform(list(zip(xs, ys)))
                for (px, py), lb in zip(pts, labels):
                    d = math.hypot(px - ev.x, py - ev.y)
                    if d < 14 and (best is None or d < best[0]):
                        best = (d, lb)
            elif kind == "bar":
                for x, y, lb in zip(xs, ys, labels):
                    if abs(ev.xdata - x) < 0.35 and 0 <= ev.ydata <= max(y, 0) * 1.05:
                        best = (0, lb)
            elif kind == "barh":
                for yv, xv, lb in zip(xs, ys, labels):
                    if abs(ev.ydata - yv) < 0.35 and 0 <= ev.xdata <= xv * 1.05:
                        best = (0, lb)
        if best:
            QToolTip.showText(QCursor.pos() + QPoint(12, 12), best[1], self)
        else:
            QToolTip.hideText()

    def save_png(self, parent=None):
        if self.fig is None:
            return
        path, _ = QFileDialog.getSaveFileName(parent or self, "Guardar gráfica", "grafica.png", "PNG (*.png)")
        if path:
            self.fig.savefig(path, dpi=180, facecolor=self.fig.get_facecolor(), bbox_inches="tight")


class KpiCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setSpacing(2)
        self.t = QLabel(title)
        self.t.setObjectName("kpiTitle")
        self.v = QLabel("—")
        self.v.setObjectName("kpiValue")
        self.s = QLabel("")
        self.s.setObjectName("kpiSub")
        self.s.setWordWrap(True)
        lay.addWidget(self.t)
        lay.addWidget(self.v)
        lay.addWidget(self.s)

    def set(self, value: str, sub: str = "", color: str | None = None):
        self.v.setText(value)
        self.s.setText(sub)
        self.v.setStyleSheet(f"color:{color};" if color else "")


def level_badges(alerts) -> str:
    cnt = count_by_level(alerts)
    return " ".join(f"<span style='background:{LEVEL_COLORS[k]};color:white;border-radius:8px;padding:2px 8px;'>"
                    f"&nbsp;{k}: {v}&nbsp;</span>" for k, v in cnt.items())
