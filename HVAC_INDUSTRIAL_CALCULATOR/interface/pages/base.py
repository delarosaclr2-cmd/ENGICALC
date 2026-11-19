"""Clase base de las páginas y contexto compartido."""
from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea, QLabel, QHBoxLayout, QFrame, QTabWidget

from ..widgets import UnitContext, AlertsView, DecisionPanel, TracePanel


class AppContext:
    def __init__(self, project, db, settings):
        self.project = project
        self.db = db
        self.settings = settings
        self.results = None
        self.comparison = None
        self.comparison_fp = ""     # huella de las entradas con que se calculó ``comparison``

    @property
    def system(self):
        return UnitContext.system


class BasePage(QWidget):
    changed = Signal()
    title = ""
    subtitle = ""
    modules: list[str] = []

    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self._stale = True
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.body = QWidget()
        self.body.setObjectName("central")
        self.lay = QVBoxLayout(self.body)
        self.lay.setContentsMargins(18, 14, 18, 18)
        self.lay.setSpacing(12)
        scroll.setWidget(self.body)
        outer.addWidget(scroll)
        self._loading = False

    # --- utilidades ---
    def emit_changed(self, *_):
        if not self._loading:
            self.changed.emit()

    def results_tabs(self, with_trace=True) -> tuple[QTabWidget, AlertsView, DecisionPanel, TracePanel | None]:
        tabs = QTabWidget()
        alerts = AlertsView(self.modules)
        dec = DecisionPanel()
        tabs.addTab(dec, "Dictamen del módulo")
        tabs.addTab(alerts, "Alertas")
        trace = None
        if with_trace:
            trace = TracePanel()
            tabs.addTab(trace, "Memoria (ecuaciones)")
        tabs.setMinimumHeight(330)
        return tabs, alerts, dec, trace

    def fill_common(self, alerts: AlertsView | None, dec: DecisionPanel | None, trace: TracePanel | None, module: str):
        r = self.ctx.results
        if r is None:
            return
        if alerts is not None:
            alerts.set_alerts(r.alerts, self.ctx.system)
        if dec is not None:
            dec.set_decision(r.decisions.get(module))
        if trace is not None:
            trace.set_steps([s for s in r.trace.steps if s.module in (self.modules or [module])])

    # --- ciclo de vida ---
    def load(self):
        """Lee el proyecto en los controles (implementar)."""

    def set_results(self):
        self._stale = True
        if self.isVisible():
            self._safe_render()

    def showEvent(self, ev):
        super().showEvent(ev)
        if self._stale:
            self._safe_render()

    def _safe_render(self):
        self._stale = False
        try:
            self.render()
        except Exception as exc:  # noqa: BLE001
            import traceback
            traceback.print_exc()
            self.setToolTip(f"Error al actualizar: {exc}")

    def render(self):
        """Actualiza resultados (implementar)."""


def header(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 4)
    t = QLabel(title)
    t.setObjectName("pageTitle")
    s = QLabel(subtitle)
    s.setObjectName("pageSub")
    s.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(s)
    return w


def hrow(*widgets, stretch_last=False) -> QWidget:
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(12)
    for x in widgets:
        lay.addWidget(x, 1)
    if stretch_last:
        lay.addStretch(1)
    return w
