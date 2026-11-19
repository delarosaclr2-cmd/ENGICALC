"""Base de datos técnica editable y configuración de criterios."""
from __future__ import annotations

from PySide6.QtWidgets import (QTabWidget, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QMessageBox, QLineEdit,
                               QCheckBox, QFormLayout)

from config.settings import restore_default_settings
from core import units as U
from database.db import restore_defaults
from ..editable_table import EditableTable, Col
from ..widgets import group, note, combo, set_combo, QField, UnitContext
from .base import BasePage, header

LEVEL_OPTS = [(x, x) for x in ("CRÍTICO", "ALTO", "MEDIO", "BAJO", "INFO")]


class DatabasePage(BasePage):
    def __init__(self, ctx, main=None):
        super().__init__(ctx)
        self.main = main
        self.lay.addWidget(header("Base de datos técnica", "Bibliotecas editables con fuente y estado de verificación de "
                                  "cada valor. Los cambios se guardan en la carpeta de datos del usuario; 'Restaurar' "
                                  "recupera los valores de fábrica."))
        self.tabs = QTabWidget()
        self.lay.addWidget(self.tabs)
        bar = QHBoxLayout()
        bs = QPushButton("Guardar cambios de la base de datos")
        bs.setObjectName("primary")
        br = QPushButton("Restaurar valores de fábrica")
        br.setObjectName("danger")
        bs.clicked.connect(self.save)
        br.clicked.connect(self.restore)
        bar.addWidget(bs)
        bar.addWidget(br)
        bar.addStretch(1)
        w = QWidget()
        w.setLayout(bar)
        self.lay.addWidget(w)
        self.tables = {}

    def load(self):
        self.tabs.clear()
        db = self.ctx.db
        specs = {
            "materials.json": ("Materiales y rugosidad", "materials", [Col("id", "ID"), Col("name", "Material", width=300),
                               Col("roughness_mm", "ε [mm]", "float"), Col("t_max_c", "T máx. [°C]", "ofloat"),
                               Col("source", "Fuente", width=380), Col("status", "Estado", width=160)],
                               lambda: {"id": "nuevo", "name": "Nuevo material", "roughness_mm": 0.05, "t_max_c": None,
                                        "source": "Indicar fuente", "status": "dato del usuario"}),
            "fittings.json": ("Accesorios (K)", "fittings", [Col("id", "ID", width=150), Col("name", "Accesorio", width=300),
                              Col("category", "Categoría"), Col("mode", "Modo", "combo", options=[("fixed", "K fijo"),
                              ("formula", "Fórmula"), ("user", "K del usuario")]), Col("K", "K", "ofloat"),
                              Col("reference", "Sección de referencia", width=200), Col("source", "Fuente", width=380),
                              Col("status", "Estado", width=160)],
                              lambda: {"id": "nuevo_acc", "name": "Nuevo accesorio", "category": "Usuario", "mode": "fixed",
                                       "K": 0.5, "reference": "propia (tramo)", "source": "Indicar fuente", "status": "dato del usuario"}),
            "hood_entries.json": ("Entradas de campana", "entries", [Col("id", "ID"), Col("name", "Entrada", width=280),
                                  Col("Ce", "Ce", "ofloat"), Col("Fh", "Fh", "ofloat"), Col("source", "Fuente", width=360),
                                  Col("status", "Estado", width=160)],
                                  lambda: {"id": "nueva", "name": "Nueva entrada", "Ce": None, "Fh": 0.5, "source": "Indicar",
                                           "status": "dato del usuario"}),
            "transport_velocities.json": ("Velocidades de transporte", "classes", [Col("id", "ID", width=150),
                                          Col("name", "Clase", width=230), Col("examples", "Ejemplos", width=330),
                                          Col("v_min_m_s", "V mín [m/s]", "ofloat"), Col("v_range_m_s.0", "Rango inf. [m/s]", "ofloat"),
                                          Col("v_range_m_s.1", "Rango sup. [m/s]", "ofloat"), Col("status", "Estado", width=160)],
                                          lambda: {"id": "nueva_clase", "name": "Nueva clase", "examples": "", "v_min_m_s": 15.0,
                                                   "v_range_m_s": [15.0, 20.0], "status": "dato del usuario"}),
            "capture_velocities.json": ("Velocidades de captura", "ranges", [Col("condition", "Condición", width=330),
                                        Col("examples", "Ejemplos", width=380), Col("v_min_m_s", "V mín [m/s]", "float"),
                                        Col("v_max_m_s", "V máx [m/s]", "float")], None),
            "references.json": ("Referencias", "references", [Col("id", "ID"), Col("title", "Referencia", width=420),
                                Col("type", "Tipo", width=150), Col("use", "Uso", width=320), Col("access", "Acceso", width=160)],
                                lambda: {"id": "nueva", "title": "", "type": "", "use": "", "access": ""}),
        }
        self.tables = {}
        for fname, (title, key, cols, factory) in specs.items():
            items = db.data[fname][key]
            t = EditableTable(cols, items, factory=factory)
            w = QWidget()
            lay = QVBoxLayout(w)
            meta = db.data[fname].get("_meta", {})
            if meta:
                lay.addWidget(note(" ".join(str(v) for v in meta.values())))
            lay.addWidget(t)
            self.tabs.addTab(w, title)
            self.tables[fname] = t
        # listas simples
        w = QWidget()
        f = QFormLayout(w)
        self.iec = QLineEdit(", ".join(f"{x:g}" for x in db.data["motors.json"]["IEC_kW"]))
        self.nema = QLineEdit(", ".join(f"{x:g}" for x in db.data["motors.json"]["NEMA_hp"]))
        self.dm = QLineEdit(", ".join(f"{x:g}" for x in db.data["commercial_diameters.json"]["metric_mm"]))
        self.di = QLineEdit(", ".join(f"{x:g}" for x in db.data["commercial_diameters.json"]["imperial_in"]))
        f.addRow("Motores IEC [kW]", self.iec)
        f.addRow("Motores NEMA [hp]", self.nema)
        f.addRow("Diámetros comerciales [mm]", self.dm)
        f.addRow("Diámetros comerciales [in]", self.di)
        f.addRow(note("Series normalizadas editables; confirme con su proveedor de ductos y motores."))
        self.tabs.addTab(w, "Motores y diámetros")

    def _parse_list(self, txt):
        return [float(x) for x in txt.replace(";", ",").split(",") if x.strip()]

    def save(self):
        db = self.ctx.db
        try:
            db.data["motors.json"]["IEC_kW"] = self._parse_list(self.iec.text())
            db.data["motors.json"]["NEMA_hp"] = self._parse_list(self.nema.text())
            db.data["commercial_diameters.json"]["metric_mm"] = self._parse_list(self.dm.text())
            db.data["commercial_diameters.json"]["imperial_in"] = self._parse_list(self.di.text())
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", str(exc))
            return
        for name in db.data:
            db.save(name)
        QMessageBox.information(self, "Base de datos", "Cambios guardados.")
        self.emit_changed()

    def restore(self):
        if QMessageBox.question(self, "Restaurar", "¿Restaurar todos los valores de fábrica de la base de datos?") != QMessageBox.Yes:
            return
        new = restore_defaults()
        self.ctx.db.data = new.data
        self.load()
        self.emit_changed()


class SettingsPage(BasePage):
    def __init__(self, ctx, main=None):
        super().__init__(ctx)
        self.main = main
        self.lay.addWidget(header("Configuración", "Sistema de unidades, solucionador, criterios de evaluación (con su base "
                                  "y fuente) y pesos del comparador. Las alertas CRÍTICAS solo se emiten con base física o "
                                  "referencia; los criterios 'hipótesis' son del proyecto y configurables."))
        g, f = group("General")
        self.units = combo([("SI", "Sistema Internacional (SI)"), ("IP", "Sistema Imperial (IP)")])
        self.flow_si = combo([("m³/h", "m³/h"), ("m³/s", "m³/s"), ("L/s", "L/s")])
        self.auto = QCheckBox("Recalcular automáticamente al modificar datos")
        self.auto.setChecked(True)
        self.autosave = QField(None, unit_override="min", minimum=0.0)
        f.addRow("Sistema de unidades", self.units)
        f.addRow("Unidad de caudal en SI", self.flow_si)
        f.addRow(self.auto)
        f.addRow("Autoguardado cada", self.autosave)
        self.lay.addWidget(g)
        sg, sf = group("Solucionador")
        self.fric = combo([("colebrook", "Colebrook-White"), ("swamee_jain", "Swamee-Jain"), ("churchill", "Churchill"),
                           ("altshul_tsal", "Altshul-Tsal")])
        self.force = QCheckBox("Forzar aumento de caudal aunque se supere el límite de desbalance")
        self.npts = QField(None, unit_override="puntos", minimum=8, maximum=80)
        self.traces = QCheckBox("Incluir el anexo de trazabilidad completo en la memoria PDF")
        sf.addRow("Factor de fricción", self.fric)
        sf.addRow(self.force)
        sf.addRow("Puntos de la curva del sistema", self.npts)
        sf.addRow(self.traces)
        self.lay.addWidget(sg)
        cg, cl = group("Criterios de evaluación", QVBoxLayout())
        self.crit_items = []
        self.crit = EditableTable([Col("key", "Criterio", readonly=True, width=230), Col("value", "Valor", "float"),
                                   Col("unit", "Unidad", readonly=True), Col("basis", "Base", "combo",
                                   options=[("física", "física"), ("referencia", "referencia"), ("hipótesis", "hipótesis")]),
                                   Col("level", "Nivel de alerta", "combo", options=LEVEL_OPTS),
                                   Col("source", "Fuente / justificación", width=520)], self.crit_items,
                                  allow_add=False, allow_remove=False)
        self.crit.setMinimumHeight(420)
        cl.addWidget(self.crit)
        self.lay.addWidget(cg)
        wg, wl = group("Pesos del comparador de alternativas", QVBoxLayout())
        self.w_items = []
        self.weights = EditableTable([Col("key", "Criterio", readonly=True), Col("value", "Peso", "float")], self.w_items,
                                     allow_add=False, allow_remove=False)
        self.weights.setMinimumHeight(190)
        wl.addWidget(self.weights)
        self.lay.addWidget(wg)
        bar = QHBoxLayout()
        bs = QPushButton("Guardar configuración")
        bs.setObjectName("primary")
        br = QPushButton("Restaurar configuración de fábrica")
        br.setObjectName("danger")
        bs.clicked.connect(self.save)
        br.clicked.connect(self.restore)
        bar.addWidget(bs)
        bar.addWidget(br)
        bar.addStretch(1)
        w = QWidget()
        w.setLayout(bar)
        self.lay.addWidget(w)
        self.units.currentIndexChanged.connect(self._units)
        self.flow_si.currentIndexChanged.connect(self._units)
        for c in (self.fric,):
            c.currentIndexChanged.connect(self._solver)
        self.force.toggled.connect(self._solver)
        self.npts.changed.connect(self._solver)
        self.traces.toggled.connect(self._solver)
        self.crit.changed.connect(self._crit)
        self.weights.changed.connect(self._weights)

    def load(self):
        self._loading = True
        s = self.ctx.settings
        set_combo(self.units, self.ctx.project.units)
        set_combo(self.flow_si, s.app("flow_unit_SI", "m³/h"))
        self.autosave.set_value(s.app("autosave_minutes", 3))
        set_combo(self.fric, s.solver("friction_method", "colebrook"))
        self.force.setChecked(bool(s.solver("force_flow_increase", False)))
        self.npts.set_value(s.solver("system_curve_points", 25))
        self.traces.setChecked(s.data.get("report", {}).get("include_traces", True))
        self.crit_items[:] = [dict(key=k, **v) for k, v in s.data["criteria"].items()]
        self.crit.set_items(self.crit_items)
        self.w_items[:] = [{"key": k, "value": v} for k, v in s.weights.items()]
        self.weights.set_items(self.w_items)
        self._loading = False

    def _units(self, *_):
        if self._loading:
            return
        U.DISPLAY_UNITS["SI"]["flow"] = self.flow_si.currentData()
        self.ctx.settings.data["app"]["flow_unit_SI"] = self.flow_si.currentData()
        if self.main:
            self.main.set_units(self.units.currentData())

    def _solver(self, *_):
        if self._loading:
            return
        s = self.ctx.settings.data
        s["solver"]["friction_method"] = self.fric.currentData()
        s["solver"]["force_flow_increase"] = self.force.isChecked()
        s["solver"]["system_curve_points"] = int(self.npts.value() or 25)
        s.setdefault("report", {})["include_traces"] = self.traces.isChecked()
        s["app"]["autosave_minutes"] = self.autosave.value() or 0
        self.emit_changed()

    def _crit(self):
        for it in self.crit_items:
            c = self.ctx.settings.data["criteria"][it["key"]]
            for k in ("value", "basis", "level", "source"):
                c[k] = it[k]
        self.emit_changed()

    def _weights(self):
        for it in self.w_items:
            self.ctx.settings.data["comparator_weights"][it["key"]] = it["value"]
        self.emit_changed()

    def save(self):
        p = self.ctx.settings.save()
        QMessageBox.information(self, "Configuración", f"Configuración guardada en:\n{p}")

    def restore(self):
        if QMessageBox.question(self, "Restaurar", "¿Restaurar la configuración de fábrica?") != QMessageBox.Yes:
            return
        new = restore_default_settings()
        self.ctx.settings.data = new.data
        self.load()
        self.emit_changed()

    def auto_recalc(self) -> bool:
        return self.auto.isChecked()
