"""Diseño de ductos (herramienta de dimensionamiento) y pérdidas de presión de la red."""
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QTabWidget

from core.units import fmt
from graphics.plots import plot_duct_geometry, plot_losses_by_component, plot_pressure_distribution
from reports import tables as T
from ..editable_table import EditableTable, Col
from ..widgets import QField, combo, set_combo, group, note, ResultTable, PlotCanvas
from .base import BasePage, header, hrow


class DuctsPage(BasePage):
    modules = ["Diseño de ductos"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Dimensionamiento de ductos", "Velocidad constante, fricción constante y recuperación "
                                  "estática. Diámetro hidráulico Dh = 4A/Pm para Reynolds y fricción; diámetro equivalente "
                                  "de Huebscher (igual fricción) para equivalencia circular–rectangular."))
        g, f = group("Datos")
        self.method = combo([("velocity", "1. Velocidad constante"), ("friction", "2. Fricción constante"),
                             ("regain", "3. Recuperación estática (inyección)")])
        self.Q = QField("flow", minimum=1e-9)
        self.V = QField("velocity", minimum=1e-6)
        self.dp = QField("friction_rate", minimum=1e-9)
        self.shape = combo([("circular", "Circular"), ("rectangular", "Rectangular")])
        self.aspect = QField(None, unit_override="a/b", minimum=1.0)
        self.material = combo([])
        self.rounding = combo([("down", "Inferior (mayor velocidad — transporte de partículas)"),
                               ("up", "Superior (menor velocidad y pérdida)"), ("nearest", "Más cercano"),
                               ("none", "Sin redondeo (teórico)")])
        self.R = QField(None, unit_override="-", minimum=0.01, maximum=1.0)
        for lbl, w in (("Método", self.method), ("Caudal", self.Q), ("Velocidad de diseño / inicial", self.V),
                       ("Pérdida unitaria objetivo", self.dp), ("Sección", self.shape), ("Relación de aspecto", self.aspect),
                       ("Material", self.material), ("Redondeo comercial", self.rounding),
                       ("Coef. de recuperación R (recup. estática)", self.R)):
            f.addRow(lbl, w)
        self.sections = EditableTable([Col("0", "Q tramo", "float", "flow"), Col("1", "Longitud", "float", "length"),
                                       Col("2", "ΣK accesorios", "float")], [], factory=lambda: [0.5, 5.0, 0.3])
        self.sections.setMinimumHeight(150)
        f.addRow(note("Tramos sucesivos para recuperación estática (después de cada derivación):"))
        f.addRow(self.sections)
        f.addRow(note("La recuperación estática aplica a sistemas de inyección; en extracción con partículas debe "
                      "mantenerse la velocidad de transporte."))
        rg, rf = group("Resultados", QVBoxLayout())
        self.res = ResultTable()
        self.res.setMinimumHeight(260)
        rf.addWidget(self.res)
        self.plot = PlotCanvas(300)
        rf.addWidget(self.plot)
        self.lay.addWidget(hrow(g, rg))
        tabs, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(tabs)
        for w in (self.Q, self.V, self.dp, self.aspect, self.R):
            w.changed.connect(self._apply)
        for c in (self.method, self.shape, self.material, self.rounding):
            c.currentIndexChanged.connect(self._apply)
        self.sections.changed.connect(self._apply)

    def load(self):
        self._loading = True
        d = self.ctx.project.duct_tool
        self.material.clear()
        for m in self.ctx.db.materials:
            self.material.addItem(f"{m['name']} (ε = {m['roughness_mm']} mm)", m["id"])
        set_combo(self.method, d.method)
        self.Q.set_value(d.Q); self.V.set_value(d.V_target); self.dp.set_value(d.dp_per_m)
        set_combo(self.shape, d.shape); self.aspect.set_value(d.aspect); set_combo(self.material, d.material_id)
        set_combo(self.rounding, d.rounding); self.R.set_value(d.regain_R)
        self.sections.set_items(d.regain_sections)
        self._loading = False

    def _apply(self, *_):
        if self._loading:
            return
        d = self.ctx.project.duct_tool
        d.method = self.method.currentData()
        d.Q = self.Q.value() or d.Q
        d.V_target = self.V.value() or d.V_target
        d.dp_per_m = self.dp.value() or d.dp_per_m
        d.shape = self.shape.currentData()
        d.aspect = self.aspect.value() or 2.0
        d.material_id = self.material.currentData()
        d.rounding = self.rounding.currentData()
        d.regain_R = self.R.value() or 0.75
        self.emit_changed()

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        s = self.ctx.system
        rows = []
        for i, x in enumerate(r.duct_tool):
            g = x.geometry
            rows.append([i + 1, x.method, g.describe(), fmt(x.D_theoretical, "small_length", s) if x.D_theoretical else "—",
                         fmt(g.area, "area", s), fmt(x.Dh, "small_length", s), fmt(x.De, "small_length", s),
                         fmt(x.V, "velocity", s), fmt(x.VP, "pressure", s), f"{x.Re:,.0f}", f"{x.rel_rough:.2e}",
                         f"{x.f:.5f}", x.regime, fmt(x.dp_per_m, "friction_rate", s), " ".join(x.warnings)])
        self.res.set_data(["#", "Método", "Adoptado", "D teórico", "Área", "Dh", "De (igual fricción)", "V", "VP", "Re",
                           "ε/Dh", "f Darcy", "Régimen", "ΔP/L", "Observaciones"], rows)
        if r.duct_tool:
            g = r.duct_tool[0].geometry
            if g.shape == "circular":
                import math
                b = math.sqrt(g.area / 2.0)
                fig = plot_duct_geometry(g.D, 2 * b, b, s, "adoptado y rectangular 2:1 de igual área")
            else:
                fig = plot_duct_geometry(g.De, g.a, g.b, s, "adoptado y circular de igual fricción")
            self.plot.set_figure(fig)
        self.fill_common(self.alerts, self.dec, None, "Diseño de ductos")
        self.trace.set_steps([st for x in r.duct_tool for st in x.trace.steps])


class LossesPage(BasePage):
    modules = ["Pérdidas de presión"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Pérdidas de presión y presión del sistema", "Fricción (Darcy-Weisbach), pérdidas locales "
                                  "K·ρV²/2 con su sección de referencia, equipos (fijos, ley de potencia, curva o filtro "
                                  "limpio/saturado) y descarga. Presión total TP = SP + VP; camino crítico."))
        g, f = group("Condición de diseño de los filtros")
        self.state = combo([("sucio", "Saturado / condición de mantenimiento (recomendado para diseño)"),
                            ("limpio", "Limpio"), ("intermedio", "Intermedio (fracción del equipo)")])
        self.state.currentIndexChanged.connect(self._apply)
        f.addRow("Estado del filtro para el diseño", self.state)
        f.addRow(note("El programa evalúa además la condición de filtro limpio para la curva del sistema y la posible "
                      "sobrecarga del motor."))
        self.lay.addWidget(g)
        tabs = QTabWidget()
        self.t_seg = ResultTable()
        self.t_fit = ResultTable()
        self.t_eq = ResultTable()
        tabs.addTab(self.t_seg, "Pérdidas por tramo")
        tabs.addTab(self.t_fit, "Accesorios y entradas")
        tabs.addTab(self.t_eq, "Equipos")
        tabs.setMinimumHeight(300)
        self.lay.addWidget(tabs)
        self.summary = note("")
        self.lay.addWidget(self.summary)
        self.p_loss = PlotCanvas(380)
        self.p_pres = PlotCanvas(380)
        self.lay.addWidget(hrow(self.p_loss, self.p_pres))
        t2, self.alerts, self.dec, self.trace = self.results_tabs(with_trace=False)
        self.lay.addWidget(t2)

    def load(self):
        self._loading = True
        set_combo(self.state, self.ctx.project.network_settings.filter_state_design)
        self._loading = False

    def _apply(self, *_):
        if self._loading:
            return
        self.ctx.project.network_settings.filter_state_design = self.state.currentData()
        self.emit_changed()

    def render(self):
        r = self.ctx.results
        if r is None or r.network_design is None:
            return
        s = self.ctx.system
        self.t_seg.set_data(*T.segments_flow_table(r, s))
        self.t_fit.set_data(*T.fittings_table(r, s))
        self.t_eq.set_data(*T.equipment_table(r, self.ctx.project, s))
        nr = r.network_design
        tb = nr.total_by_type()
        self.summary.setText(f"<b>Camino crítico:</b> {' → '.join(nr.critical_path)} · fricción {fmt(tb['Fricción'], 'pressure', s)}"
                             f" · locales {fmt(tb['Locales'], 'pressure', s)} · equipos {fmt(tb['Equipos'], 'pressure', s)}"
                             f" · <b>FTP requerida {fmt(nr.state.FTP, 'pressure', s)}</b> · FSP {fmt(nr.state.FSP, 'pressure', s)}")
        self.p_loss.set_figure(plot_losses_by_component(r, s))
        self.p_pres.set_figure(plot_pressure_distribution(r, s))
        self.fill_common(self.alerts, self.dec, None, "Pérdidas de presión")
