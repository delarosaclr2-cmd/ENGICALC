"""Selección de ventiladores (curvas, leyes de semejanza, punto de operación) y potencia/motores."""
from __future__ import annotations

from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, QComboBox, QLineEdit, QCheckBox,
                               QMessageBox, QInputDialog, QWidget, QTabWidget, QFormLayout)

from core.fan_curves import FanCurve, load_curve_csv, load_curve_excel
from core.fan_laws import affinity
from core.units import fmt, UNITS
from graphics.plots import plot_fan_curve
from reports import tables as T
from ..editable_table import EditableTable, Col
from ..widgets import QField, combo, set_combo, group, note, ResultTable, PlotCanvas, UnitContext
from .base import BasePage, header, hrow

FAN_GUIDE = [
    ["Centrífugo de álabes inclinados hacia atrás / aerodinámicos", "Alta eficiencia; curva de potencia no sobrecargable; "
     "adecuado en el lado limpio (después del colector)", "No apto para aire con mucho polvo abrasivo o pegajoso"],
    ["Centrífugo de punta radial / álabes radiales", "Robusto ante abrasión y materiales pegajosos; apto para transporte "
     "de material", "Menor eficiencia; mayor ruido"],
    ["Centrífugo de álabes curvados hacia adelante", "Compacto, bajas presiones, HVAC general", "Curva de potencia "
     "sobrecargable; no recomendable para polvo"],
    ["Axial / tubo-axial", "Grandes caudales y bajas presiones; ventilación general", "Sensible a presiones altas y a "
     "partículas; zona de pérdida pronunciada"],
]


class FansPage(BasePage):
    modules = ["Selección de ventiladores"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Selección de ventiladores", "Curvas del fabricante (CSV, Excel o captura manual) "
                                  "interpoladas con PCHIP, corregidas por densidad y velocidad; intersección con la curva "
                                  "del sistema, BEP, zona inestable y rpm requeridas. Nunca se extrapola sin advertencia."))
        g, f = group("Curvas disponibles")
        self.fans = EditableTable([
            Col("id", "ID", width=80), Col("manufacturer", "Fabricante", width=170), Col("model", "Modelo", width=220),
            Col("fan_type", "Tipo", "combo", options=[("Centrífugo", "Centrífugo"), ("Axial", "Axial"), ("Otro", "Otro")]),
            Col("rpm", "rpm curva", "float"), Col("rho_ref", "ρ curva", "float", "density"),
            Col("pressure_basis", "Base de presión", "combo", options=[("total", "Total"), ("static", "Estática")]),
            Col("outlet_area_m2", "Área de descarga", "ofloat", "area"), Col("diameter_m", "Ø rodete", "ofloat", "small_length"),
            Col("max_rpm", "rpm máx.", "ofloat"), Col("q_min_rec", "Q mín. recomendado", "ofloat", "flow"),
            Col("q_max_rec", "Q máx. recomendado", "ofloat", "flow"), Col("certified", "Certificada", "bool"),
            Col("source", "Fuente", width=240),
        ], self.ctx.project.fans, factory=self._new_fan)
        self.fans.setMinimumHeight(170)
        self.fans.changed.connect(self._fans_changed)
        self.fans.current_changed.connect(self._select)
        b1 = QPushButton("Importar CSV…")
        b2 = QPushButton("Importar Excel…")
        b1.clicked.connect(lambda: self._import("csv"))
        b2.clicked.connect(lambda: self._import("xlsx"))
        self.fans.extra_bar.addWidget(b1)
        self.fans.extra_bar.addWidget(b2)
        f.addRow(self.fans)
        f.addRow(note("Puntos de la curva seleccionada (Q, presión en la base indicada, eficiencia en la misma base y/o "
                      "potencia absorbida). El CSV/Excel debe tener encabezados Q, P, eta, W."))
        self.points = EditableTable([Col("Q", "Q", "float", "flow"), Col("P", "Presión", "float", "pressure"),
                                     Col("eta", "η", "ofloat", unit="%", scale=100), Col("W", "Potencia", "ofloat", "power")],
                                    [], factory=lambda: {"Q": 0.0, "P": 0.0}, allow_move=True)
        self.points.setMinimumHeight(200)
        self.points.changed.connect(self.emit_changed)
        f.addRow(self.points)
        self.lay.addWidget(g)
        sg, sf = group("Selección y condiciones de operación")
        self.sel = QComboBox()
        self.sel.currentIndexChanged.connect(self._apply_sel)
        self.rpm = QField(None, unit_override="rpm", optional=True)
        self.dia = QField("small_length", optional=True)
        self.rpm.changed.connect(self._apply_sel)
        self.dia.changed.connect(self._apply_sel)
        sf.addRow("Ventilador seleccionado", self.sel)
        sf.addRow("Velocidad de operación (vacío = catálogo)", self.rpm)
        sf.addRow("Diámetro (familia semejante; vacío = catálogo)", self.dia)
        self.info = note("")
        sf.addRow(self.info)
        ag, af = group("Leyes de semejanza (calculadora)")
        self.a_Q, self.a_P, self.a_W = QField("flow"), QField("pressure"), QField("power", optional=True)
        self.a_N1, self.a_N2 = QField(None, unit_override="rpm"), QField(None, unit_override="rpm")
        self.a_D1, self.a_D2 = QField("small_length"), QField("small_length")
        self.a_r1, self.a_r2 = QField("density"), QField("density")
        for w, v in ((self.a_Q, 2.0), (self.a_P, 1000.0), (self.a_W, 3000.0), (self.a_N1, 1750.0), (self.a_N2, 1750.0),
                     (self.a_D1, 0.5), (self.a_D2, 0.5), (self.a_r1, 1.2), (self.a_r2, 1.2)):
            w.set_value(v)
            w.changed.connect(self._affinity)
        for lbl, w in (("Q₁", self.a_Q), ("P₁", self.a_P), ("W₁", self.a_W), ("N₁", self.a_N1), ("N₂", self.a_N2),
                       ("D₁", self.a_D1), ("D₂", self.a_D2), ("ρ₁", self.a_r1), ("ρ₂", self.a_r2)):
            af.addRow(lbl, w)
        self.a_res = note("")
        af.addRow(self.a_res)
        af.addRow(note("Válido para ventiladores geométricamente semejantes en puntos homólogos; no sustituye la curva "
                       "certificada del fabricante."))
        self.lay.addWidget(hrow(sg, ag))
        self.plot = PlotCanvas(520)
        self.lay.addWidget(self.plot)
        rg, rl = group("Comparación de ventiladores", QVBoxLayout())
        self.table = ResultTable()
        self.table.setMinimumHeight(150)
        rl.addWidget(self.table)
        self.guide = ResultTable(["Tipo", "Ventajas / aplicación", "Limitaciones"], FAN_GUIDE)
        self.guide.setMinimumHeight(150)
        rl.addWidget(note("Guía cualitativa (práctica general de ingeniería, no normativa):"))
        rl.addWidget(self.guide)
        self.lay.addWidget(rg)
        t2, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(t2)
        self.cur = None
        self._affinity()

    def _new_fan(self):
        ids = {f.id for f in self.ctx.project.fans}
        i = 1
        while f"FAN-{i}" in ids:
            i += 1
        return FanCurve(id=f"FAN-{i}", manufacturer="", model="", points=[{"Q": 0.5, "P": 1000.0}, {"Q": 1.0, "P": 900.0},
                                                                          {"Q": 1.5, "P": 700.0}],
                        source="Dato del fabricante (indicar)")

    def load(self):
        self._loading = True
        self.fans.set_items(self.ctx.project.fans)
        self._refresh_sel()
        fs = self.ctx.project.fan_selection
        self.rpm.set_value(fs.rpm)
        self.dia.set_value(fs.diameter_m)
        self._loading = False
        if self.ctx.project.fans:
            self.fans.table.setCurrentCell(0, 0)
            self._select(0)

    def _refresh_sel(self):
        self.sel.blockSignals(True)
        self.sel.clear()
        for fc in self.ctx.project.fans:
            self.sel.addItem(f"{fc.id} — {fc.model}", fc.id)
        set_combo(self.sel, self.ctx.project.fan_selection.selected_id)
        self.sel.blockSignals(False)

    def _fans_changed(self):
        self._refresh_sel()
        self._select(self.fans.current_index())
        self.emit_changed()

    def _select(self, idx):
        fs = self.ctx.project.fans
        if 0 <= idx < len(fs):
            self.cur = fs[idx]
            self.points.set_items(self.cur.points)

    def _apply_sel(self, *_):
        if self._loading:
            return
        s = self.ctx.project.fan_selection
        s.selected_id = self.sel.currentData()
        s.rpm = self.rpm.value()
        s.diameter_m = self.dia.value()
        self.emit_changed()

    def _import(self, kind):
        flt = "CSV (*.csv)" if kind == "csv" else "Excel (*.xlsx)"
        path, _ = QFileDialog.getOpenFileName(self, "Importar curva", "", flt)
        if not path:
            return
        sysu = UnitContext.system
        qu, ok = QInputDialog.getItem(self, "Unidad de caudal", "Caudal en:", list(UNITS["flow"].keys()),
                                      list(UNITS["flow"].keys()).index("cfm" if sysu == "IP" else "m³/s"), False)
        if not ok:
            return
        pu, ok = QInputDialog.getItem(self, "Unidad de presión", "Presión en:", list(UNITS["pressure"].keys()),
                                      list(UNITS["pressure"].keys()).index("in.wg" if sysu == "IP" else "Pa"), False)
        if not ok:
            return
        wu, ok = QInputDialog.getItem(self, "Unidad de potencia", "Potencia (columna W) en:", list(UNITS["power"].keys()),
                                      list(UNITS["power"].keys()).index("hp" if sysu == "IP" else "W"), False)
        if not ok:
            return
        try:
            pts = load_curve_csv(path, qu, pu, wu) if kind == "csv" else load_curve_excel(path, qu, pu, wu)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Error de importación", str(exc))
            return
        fc = self._new_fan()
        fc.points = pts
        fc.model = path.split("/")[-1].rsplit(".", 1)[0]
        fc.source = f"Importada de {path}"
        self.ctx.project.fans.append(fc)
        self.fans.rebuild()
        self._fans_changed()
        QMessageBox.information(self, "Curva importada", f"{len(pts)} puntos importados. Complete rpm, densidad de "
                                "referencia, base de presión y área de descarga en la tabla.")

    def _affinity(self, *_):
        try:
            r = affinity(self.a_Q.value(), self.a_P.value(), self.a_W.value(), self.a_N1.value(), self.a_N2.value(),
                         self.a_D1.value(), self.a_D2.value(), self.a_r1.value(), self.a_r2.value())
            s = UnitContext.system
            self.a_res.setText(f"<b>Q₂ = {fmt(r.Q2, 'flow', s)} · P₂ = {fmt(r.P2, 'pressure', s)}"
                               + (f" · W₂ = {fmt(r.W2, 'power', s)}" if r.W2 is not None else "") + "</b>")
        except Exception as exc:  # noqa: BLE001
            self.a_res.setText(f"<span style='color:#B42318'>{exc}</span>")

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        s = self.ctx.system
        self.table.set_data(*T.fans_table(r, s))
        fe = r.selected_fan
        if r.network_design is not None:
            self.plot.set_figure(plot_fan_curve(r, None, s))
        if fe is not None and fe.adjusted is not None:
            self.info.setText(f"Curva corregida a ρ = {fe.adjusted.rho:.4f} kg/m³ (factor {fe.adjusted.rr:.3f}) y "
                              f"{fe.adjusted.rpm:.0f} rpm. rpm requeridas para el punto de diseño: "
                              f"{fe.rpm_required:.0f}" if fe.rpm_required else "No se encontró una velocidad que pase por el punto de diseño.")
        self.fill_common(self.alerts, self.dec, self.trace, "Selección de ventiladores")


class PowerPage(BasePage):
    modules = ["Potencia y motores"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Potencia y selección del motor", "Potencia aerodinámica, absorbida por el ventilador, en "
                                  "el eje del motor y eléctrica de entrada; motor normalizado con margen aplicado una sola "
                                  "vez; consumo, costo y regulación por compuerta frente a variador."))
        g, f = group("Eficiencias y motor")
        self.eta = QField(None, unit_override="%", scale=100, minimum=0.01, maximum=1.0)
        self.basis = combo([("total", "Total (con FTP)"), ("static", "Estática (con FSP)")])
        self.drive = combo([("Directo", "Acople directo"), ("Bandas", "Transmisión por bandas"), ("Otro", "Otro")])
        self.eta_d = QField(None, unit_override="%", scale=100, minimum=0.01, maximum=1.0)
        self.eta_m = QField(None, unit_override="%", scale=100, minimum=0.01, maximum=1.0)
        self.vfd = QCheckBox("Variador de frecuencia")
        self.eta_v = QField(None, unit_override="%", scale=100, minimum=0.01, maximum=1.0)
        self.margin = QField(None, unit_override="%", scale=100, minimum=0.0, maximum=1.0)
        self.sf = QField(None, unit_override="-", minimum=1.0)
        self.std = combo([("IEC", "IEC 60072-1 (kW)"), ("NEMA", "NEMA MG 1 (hp)")])
        self.motor = QField(None, unit_override="kW", optional=True)
        for lbl, w in (("Eficiencia del ventilador (si no hay curva de potencia)", self.eta), ("Base de la eficiencia", self.basis),
                       ("Transmisión", self.drive), ("Eficiencia de transmisión", self.eta_d), ("Eficiencia del motor", self.eta_m),
                       ("", self.vfd), ("Eficiencia del variador", self.eta_v), ("Margen de selección (una vez)", self.margin),
                       ("Factor de servicio (informativo)", self.sf), ("Serie de motores", self.std),
                       ("Motor seleccionado (opcional)", self.motor)):
            f.addRow(lbl, w) if lbl else f.addRow(w)
        f.addRow(note("La eficiencia del ventilador debe estar en la misma base que la presión. Con curva de potencia del "
                      "fabricante el programa usa la curva."))
        eg, ef = group("Operación y energía")
        self.hours = QField(None, unit_override="h/año", minimum=0.0)
        self.tariff = QField(None, unit_override="$/kWh", minimum=0.0)
        self.cur = QLineEdit()
        ef.addRow("Horas de operación", self.hours)
        ef.addRow("Tarifa eléctrica", self.tariff)
        ef.addRow("Moneda", self.cur)
        self.profile = EditableTable([Col("0", "Fracción de caudal", "float", unit="%", scale=100),
                                      Col("1", "Fracción del tiempo", "float", unit="%", scale=100)], [],
                                     factory=lambda: [0.5, 0.1])
        self.profile.setMinimumHeight(150)
        ef.addRow(note("Perfil de carga para comparar compuerta vs. variador:"))
        ef.addRow(self.profile)
        self.lay.addWidget(hrow(g, eg))
        tabs = QTabWidget()
        self.t_pow = ResultTable()
        self.t_pl = ResultTable()
        tabs.addTab(self.t_pow, "Cadena de potencias y motor")
        tabs.addTab(self.t_pl, "Carga parcial: compuerta vs. variador")
        tabs.setMinimumHeight(420)
        self.lay.addWidget(tabs)
        t2, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(t2)
        for w in (self.eta, self.eta_d, self.eta_m, self.eta_v, self.margin, self.sf, self.motor, self.hours, self.tariff):
            w.changed.connect(self._apply)
        for c in (self.basis, self.drive, self.std):
            c.currentIndexChanged.connect(self._apply)
        self.vfd.toggled.connect(self._apply)
        self.cur.editingFinished.connect(self._apply)
        self.profile.changed.connect(self._apply)

    def load(self):
        self._loading = True
        p = self.ctx.project.power
        self.eta.set_value(p.eta_fan_user); set_combo(self.basis, p.eta_basis); set_combo(self.drive, p.drive_type)
        self.eta_d.set_value(p.eta_drive); self.eta_m.set_value(p.eta_motor); self.vfd.setChecked(p.use_vfd)
        self.eta_v.set_value(p.eta_vfd); self.margin.set_value(p.margin); self.sf.set_value(p.service_factor)
        set_combo(self.std, p.motor_standard); self.motor.set_value(p.motor_selected_kw)
        self.hours.set_value(p.hours_per_year); self.tariff.set_value(p.tariff); self.cur.setText(p.currency)
        self.profile.set_items(p.profile)
        self._loading = False

    def _apply(self, *_):
        if self._loading:
            return
        p = self.ctx.project.power
        p.eta_fan_user = self.eta.value() or p.eta_fan_user
        p.eta_basis = self.basis.currentData()
        p.drive_type = self.drive.currentData()
        if p.drive_type == "Directo" and (self.eta_d.value() or 1) < 1:
            pass
        p.eta_drive = self.eta_d.value() or p.eta_drive
        p.eta_motor = self.eta_m.value() or p.eta_motor
        p.use_vfd = self.vfd.isChecked()
        p.eta_vfd = self.eta_v.value() or p.eta_vfd
        p.margin = self.margin.value() if self.margin.value() is not None else p.margin
        p.service_factor = self.sf.value() or p.service_factor
        p.motor_standard = self.std.currentData()
        p.motor_selected_kw = self.motor.value()
        p.hours_per_year = self.hours.value() or 0.0
        p.tariff = self.tariff.value() or 0.0
        p.currency = self.cur.text() or "MXN"
        self.emit_changed()

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        self.t_pow.set_data(*T.power_table(r, self.ctx.project, self.ctx.system))
        self.t_pl.set_data(*T.part_load_table(r, self.ctx.system))
        self.fill_common(self.alerts, self.dec, self.trace, "Potencia y motores")
