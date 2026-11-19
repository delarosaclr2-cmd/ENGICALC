"""Ventana principal: navegación, archivo de proyecto, cálculo en segundo plano y autoguardado."""
from __future__ import annotations

import os
import time

from PySide6.QtCore import Qt, QTimer, QThread, Signal, QSettings, QUrl
from PySide6.QtGui import QAction, QIcon, QKeySequence, QDesktopServices
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
                               QStackedWidget, QPushButton, QComboBox, QFileDialog, QMessageBox, QStatusBar, QApplication)

from config.settings import app_root, user_data_dir
from core import units as U
from core.calculation import run_project, results_are_current
from core.hood_design import HoodEntry
from core.network_solver import NetworkModel, NetNode, NetSegment
from core.fittings import FittingInstance
from core.project import Project, Hood, APP_VERSION
from validation.decision_engine import DEC_COLORS
from .pages.base import AppContext
from .pages.dashboard import DashboardPage
from .pages.air_flow import AirPage, AirflowPage
from .pages.hoods import HoodsPage
from .pages.ducts_losses import DuctsPage, LossesPage
from .pages.network import NetworkPage
from .pages.fans_power import FansPage, PowerPage
from .pages.report import ReportPage
from .pages.database_settings import DatabasePage, SettingsPage
from .theme import QSS
from .widgets import UnitContext

FILE_FILTER = "Proyecto HVAC (*.hvac.json);;JSON (*.json)"
NAV = ["Dashboard", "Propiedades del aire", "Caudales", "Campanas de extracción", "Diseño de ductos",
       "Pérdidas de presión", "Redes ramificadas", "Selección de ventiladores", "Potencia y motores",
       "Memoria de cálculo", "Base de datos", "Configuración"]
ICONS = ["▣", "☁", "⇉", "⌂", "◯", "↘", "⑂", "✇", "⚡", "▤", "☰", "⚙"]


def new_project_template() -> Project:
    """Proyecto nuevo con una red mínima editable (2 campanas, unión, ventilador, descarga)."""
    p = Project()
    p.info.name = "Proyecto nuevo"
    p.hoods = [Hood("C1", "Campana 1", "exterior_flanged", {"W": 0.4, "H": 0.3, "X": 0.25, "Vc": 0.75}),
               Hood("C2", "Campana 2", "exterior_flanged", {"W": 0.4, "H": 0.3, "X": 0.25, "Vc": 0.75})]
    m = NetworkModel()
    for nd in [NetNode("H1", "hood", hood_id="C1"), NetNode("H2", "hood", hood_id="C2"), NetNode("J1", "junction"),
               NetNode("FAN", "fan"), NetNode("OUT", "outlet", stack_height_above_roof_m=3.5)]:
        m.nodes[nd.id] = nd
    m.segments = [NetSegment("R1", "H1", "J1", "circular", 0.2, length=5.0, fittings=[FittingInstance("elbow90_RD2.0", 1)]),
                  NetSegment("R2", "H2", "J1", "circular", 0.2, length=5.0,
                             fittings=[FittingInstance("elbow90_RD2.0", 1), FittingInstance("branch_entry_30", 1)]),
                  NetSegment("M1", "J1", "FAN", "circular", 0.28, length=10.0),
                  NetSegment("D1", "FAN", "OUT", "circular", 0.28, length=6.0)]
    p.network = m
    return p


class CalcThread(QThread):
    done = Signal(object, float, int)
    failed = Signal(str)

    def __init__(self, project, db, settings, seq: int = 0):
        super().__init__()
        self.project, self.db, self.settings, self.seq = project, db, settings, seq

    def run(self):
        t = time.time()
        try:
            res = run_project(self.project, self.db, self.settings)
            self.done.emit(res, time.time() - t, self.seq)
        except Exception as exc:  # noqa: BLE001
            import traceback
            self.failed.emit(f"{exc}\n{traceback.format_exc()}")


class MainWindow(QMainWindow):
    def __init__(self, db, settings, project: Project | None = None, path: str | None = None):
        super().__init__()
        self.setStyleSheet(QSS)
        self.setWindowTitle("HVAC Industrial Engineering Calculator")
        icon = os.path.join(app_root(), "assets", "icon.png")
        if os.path.exists(icon):
            self.setWindowIcon(QIcon(icon))
        self.resize(1480, 920)
        self.qsettings = QSettings("HVAC_IEC", "HVAC Industrial Engineering Calculator")
        project = project or new_project_template()
        self.ctx = AppContext(project, db, settings)
        self.path = path
        self.dirty = False
        self.calc_thread = None
        self.pending = False
        self._calc_seq = 0          # número de cálculo solicitado
        self._applied_seq = -1      # número del cálculo cuyos resultados se muestran
        UnitContext.system = project.units
        U.DISPLAY_UNITS["SI"]["flow"] = settings.app("flow_unit_SI", "m³/h")
        self._build()
        self.debounce = QTimer(self)
        self.debounce.setSingleShot(True)
        self.debounce.setInterval(500)
        self.debounce.timeout.connect(self.calculate)
        self.autosave = QTimer(self)
        self.autosave.timeout.connect(self._autosave)
        mins = float(settings.app("autosave_minutes", 3) or 0)
        if mins > 0:
            self.autosave.start(int(mins * 60000))
        self.load_all()
        self.calculate()

    # ------------------------------------------------------------------ UI
    def _build(self):
        central = QWidget()
        central.setObjectName("central")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(250)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 0)
        t = QLabel("HVAC INDUSTRIAL\nENGINEERING\nCALCULATOR")
        t.setObjectName("appTitle")
        s = QLabel(f"Ventilación industrial · v{APP_VERSION}")
        s.setObjectName("appSub")
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        for i, name in enumerate(NAV):
            self.nav.addItem(QListWidgetItem(f"{ICONS[i]}   {i + 1}. {name}"))
        sl.addWidget(t)
        sl.addWidget(s)
        sl.addWidget(self.nav, 1)
        root.addWidget(side)
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        top = QWidget()
        top.setObjectName("topbar")
        tl = QHBoxLayout(top)
        tl.setContentsMargins(16, 8, 16, 8)
        self.proj_lbl = QLabel()
        self.proj_lbl.setObjectName("projectName")
        tl.addWidget(self.proj_lbl, 1)
        self.units = QComboBox()
        self.units.addItem("SI", "SI")
        self.units.addItem("Imperial (IP)", "IP")
        self.units.currentIndexChanged.connect(lambda: self.set_units(self.units.currentData()))
        tl.addWidget(QLabel("Unidades:"))
        tl.addWidget(self.units)
        for txt, fn, prim in (("Abrir", self.open, False), ("Guardar", self.save, False), ("Calcular", self.calculate, True),
                              ("Memoria PDF", lambda: self.pages[9].export_pdf(), False),
                              ("Excel", lambda: self.pages[9].export_excel(), False)):
            b = QPushButton(txt)
            if prim:
                b.setObjectName("primary")
            b.clicked.connect(fn)
            tl.addWidget(b)
        rl.addWidget(top)
        self.stack = QStackedWidget()
        c = self.ctx
        self.pages = [DashboardPage(c), AirPage(c), AirflowPage(c), HoodsPage(c), DuctsPage(c), LossesPage(c),
                      NetworkPage(c), FansPage(c), PowerPage(c), ReportPage(c, self), DatabasePage(c, self),
                      SettingsPage(c, self)]
        for p in self.pages:
            self.stack.addWidget(p)
            p.changed.connect(self.on_changed)
        rl.addWidget(self.stack, 1)
        root.addWidget(right, 1)
        self.setCentralWidget(central)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_dec = QLabel()
        self.status.addPermanentWidget(self.status_dec)
        self._menus()

    def _menus(self):
        mb = self.menuBar()
        m = mb.addMenu("&Archivo")
        for txt, fn, key in (("Nuevo proyecto", self.new, QKeySequence.New), ("Abrir…", self.open, QKeySequence.Open),
                             ("Abrir banco de pruebas industrial", self.open_example, None),
                             ("Guardar", self.save, QKeySequence.Save), ("Guardar como…", self.save_as, QKeySequence.SaveAs),
                             ("Recuperar autoguardado", self.recover, None), (None, None, None),
                             ("Exportar memoria PDF…", lambda: self.pages[9].export_pdf(), None),
                             ("Exportar Excel…", lambda: self.pages[9].export_excel(), None),
                             ("Exportar todas las gráficas (PNG)…", self.export_pngs, None), (None, None, None),
                             ("Salir", self.close, QKeySequence.Quit)):
            if txt is None:
                m.addSeparator()
                continue
            a = QAction(txt, self)
            if key:
                a.setShortcut(key)
            a.triggered.connect(fn)
            m.addAction(a)
        self.recent_menu = m.addMenu("Recientes")
        self._refresh_recent()
        c = mb.addMenu("&Cálculo")
        a = QAction("Calcular ahora", self)
        a.setShortcut("F5")
        a.triggered.connect(self.calculate)
        c.addAction(a)
        h = mb.addMenu("A&yuda")
        for txt, fn in (("Manual de usuario", lambda: self._open_doc("MANUAL_USUARIO.md")),
                        ("Auditoría técnica del PDF", lambda: self._open_doc("AUDITORIA_TECNICA.md")),
                        ("Validación del software", lambda: self._open_doc("VALIDACION.md")),
                        ("Acerca de", self.about)):
            a = QAction(txt, self)
            a.triggered.connect(fn)
            h.addAction(a)

    def _open_doc(self, name):
        p = os.path.join(app_root(), "docs", name)
        if os.path.exists(p):
            QDesktopServices.openUrl(QUrl.fromLocalFile(p))

    def about(self):
        QMessageBox.about(self, "Acerca de", f"<b>HVAC Industrial Engineering Calculator</b> v{APP_VERSION}<br><br>"
                          "Herramienta de apoyo para el diseño de ventilación industrial, extracción localizada, redes "
                          "de ductos y selección de ventiladores.<br><br>Sus resultados no constituyen certificación "
                          "normativa ni sustituyen la responsabilidad del ingeniero.")

    # -------------------------------------------------------------- proyecto
    def load_all(self):
        from .widgets import set_combo
        set_combo(self.units, self.ctx.project.units)
        for p in self.pages:
            p._loading = True
            try:
                p.load()
            finally:
                p._loading = False
        self._title()

    def _title(self):
        name = os.path.basename(self.path) if self.path else "sin guardar"
        self.proj_lbl.setText(f"{self.ctx.project.info.name}  ·  {name}{'  ●' if self.dirty else ''}")
        self.setWindowTitle(f"{self.ctx.project.info.name} — HVAC Industrial Engineering Calculator")

    def set_project(self, project: Project, path: str | None = None, keep_path=False):
        self.ctx.project = project
        self.ctx.results = None
        self.ctx.comparison = None
        self.ctx.comparison_fp = ""
        if not keep_path:
            self.path = path
        UnitContext.set(project.units)
        self.load_all()
        self.dirty = keep_path
        self._title()
        self.calculate()

    def set_units(self, system):
        if system not in ("SI", "IP"):
            return
        self.ctx.project.units = system
        UnitContext.set(system)
        from .widgets import set_combo
        set_combo(self.units, system)
        for p in self.pages:
            p.set_results()
        self.calculate()

    def on_changed(self):
        self.dirty = True
        self._title()
        if self.pages[11].auto_recalc():
            self.debounce.start()

    def _confirm_discard(self) -> bool:
        if not self.dirty:
            return True
        r = QMessageBox.question(self, "Cambios sin guardar", "¿Guardar los cambios del proyecto actual?",
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def new(self):
        if self._confirm_discard():
            self.set_project(new_project_template())

    def open_example(self):
        if not self._confirm_discard():
            return
        p = os.path.join(app_root(), "examples", "nave_industrial_4_campanas.hvac.json")
        self.set_project(Project.load(p), None)

    def open(self):
        if not self._confirm_discard():
            return
        start = self.qsettings.value("last_dir", os.path.join(app_root(), "examples"))
        path, _ = QFileDialog.getOpenFileName(self, "Abrir proyecto", start, FILE_FILTER)
        if path:
            self._open_path(path)

    def _open_path(self, path):
        try:
            p = Project.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo abrir el proyecto:\n{exc}")
            return
        self.qsettings.setValue("last_dir", os.path.dirname(path))
        self._add_recent(path)
        self.set_project(p, path)

    def save(self) -> bool:
        if not self.path:
            return self.save_as()
        try:
            self.ctx.project.save(self.path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error", f"No se pudo guardar:\n{exc}")
            return False
        self.dirty = False
        self._title()
        self.status.showMessage(f"Proyecto guardado en {self.path}", 5000)
        self._add_recent(self.path)
        return True

    def save_as(self) -> bool:
        start = self.qsettings.value("last_dir", os.path.expanduser("~"))
        path, _ = QFileDialog.getSaveFileName(self, "Guardar proyecto", os.path.join(start, f"{self.ctx.project.info.name}.hvac.json"),
                                              FILE_FILTER)
        if not path:
            return False
        if not path.endswith(".json"):
            path += ".hvac.json"
        self.path = path
        self.qsettings.setValue("last_dir", os.path.dirname(path))
        return self.save()

    def _autosave_path(self):
        return os.path.join(user_data_dir(), "autosave.hvac.json")

    def _autosave(self):
        if self.dirty:
            try:
                self.ctx.project.save(self._autosave_path())
                self.status.showMessage("Autoguardado realizado", 3000)
            except OSError:
                pass

    def recover(self):
        p = self._autosave_path()
        if not os.path.exists(p):
            QMessageBox.information(self, "Autoguardado", "No hay un autoguardado disponible.")
            return
        if self._confirm_discard():
            self.set_project(Project.load(p), None)
            self.dirty = True
            self._title()

    def _add_recent(self, path):
        rec = [x for x in (self.qsettings.value("recent", []) or []) if x != path]
        rec.insert(0, path)
        self.qsettings.setValue("recent", rec[: int(self.ctx.settings.app("recent_files_max", 8))])
        self._refresh_recent()

    def _refresh_recent(self):
        self.recent_menu.clear()
        for pth in self.qsettings.value("recent", []) or []:
            a = QAction(pth, self)
            a.triggered.connect(lambda _=False, x=pth: self._confirm_discard() and self._open_path(x))
            self.recent_menu.addAction(a)

    def export_pngs(self):
        if not self.ensure_current_results():
            return
        d = QFileDialog.getExistingDirectory(self, "Carpeta para las gráficas")
        if not d:
            return
        from graphics.plots import build_all, save_png
        figs = build_all(self.ctx.project, self.ctx.results, self.ctx.db, self.ctx.settings, self.ctx.system)
        for k, f in figs.items():
            save_png(f, os.path.join(d, f"grafico_{k}.png"))
        self.status.showMessage(f"{len(figs)} gráficas guardadas en {d}", 6000)

    # ----------------------------------------------------------------- cálculo
    def calculate(self):
        if self.calc_thread is not None and self.calc_thread.isRunning():
            self.pending = True
            return
        self.status.showMessage("Calculando…")
        self._calc_seq += 1
        self.calc_thread = CalcThread(self.ctx.project.clone(), self.ctx.db, self.ctx.settings.copy(), self._calc_seq)
        self.calc_thread.done.connect(self._calc_done)
        self.calc_thread.failed.connect(self._calc_failed)
        self.calc_thread.start()

    def results_current(self) -> bool:
        """True si los resultados mostrados corresponden a las entradas actuales (proyecto, configuración, BD)."""
        return results_are_current(self.ctx.project, self.ctx.results, self.ctx.settings, self.ctx.db)

    def ensure_current_results(self) -> bool:
        """Garantiza resultados coherentes con las entradas actuales antes de exportar.

        Si las entradas cambiaron después del último cálculo (p. ej. con el recálculo automático desactivado, o
        con un cálculo en segundo plano aún en curso), recalcula de forma síncrona y actualiza la interfaz.
        Devuelve False si el cálculo falla.
        """
        if self.results_current():
            return True
        from PySide6.QtWidgets import QApplication
        self.status.showMessage("Actualizando resultados antes de exportar…")
        QApplication.setOverrideCursor(Qt.WaitCursor)
        t = time.time()
        try:
            self._calc_seq += 1
            seq = self._calc_seq
            res = run_project(self.ctx.project.clone(), self.ctx.db, self.ctx.settings.copy())
        except Exception as exc:  # noqa: BLE001
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Error de cálculo", f"No se pudieron actualizar los resultados:\n{exc}")
            return False
        QApplication.restoreOverrideCursor()
        self._calc_done(res, time.time() - t, seq)
        return self.results_current()

    def _calc_done(self, results, dt, seq: int | None = None):
        if seq is not None and seq < self._applied_seq:
            # resultado de un cálculo anterior que terminó después de uno más reciente: se descarta
            if self.pending:
                self.pending = False
                QTimer.singleShot(0, self.calculate)
            return
        if seq is not None:
            self._applied_seq = seq
        self.ctx.results = results
        for p in self.pages:
            p.set_results()
        d = results.dictamen
        if d:
            self.status_dec.setText(f"<b style='color:{DEC_COLORS[d.decision_code]}'>{d.decision}</b>")
        n_err = len([k for k in results.errors if not k.startswith("trace")])
        self.status.showMessage(f"Cálculo completado en {dt:.2f} s" + (f" · {n_err} módulo(s) con error" if n_err else ""), 8000)
        if self.pending:
            self.pending = False
            QTimer.singleShot(0, self.calculate)

    def _calc_failed(self, msg):
        self.status.showMessage("Error de cálculo")
        QMessageBox.critical(self, "Error de cálculo", msg[:2000])

    def closeEvent(self, ev):
        if self._confirm_discard():
            if self.calc_thread is not None:
                self.calc_thread.wait(5000)
            ev.accept()
        else:
            ev.ignore()
