"""Páginas de propiedades del aire y caudales de ventilación general."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QTabWidget, QWidget, QFormLayout, QLineEdit, QVBoxLayout

from core.air_properties import MODE_LABELS
from core.units import to_display, from_display, display_unit
from reports import tables as T
from ..widgets import QField, combo, set_combo, group, note, ResultTable, UnitContext, parse_float
from .base import BasePage, header, hrow


class AirPage(BasePage):
    modules = ["Propiedades del aire"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Propiedades del aire", "Aire seco y húmedo por psicrometría ASHRAE (Hyland-Wexler), "
                                  "viscosidad de Sutherland. No se usa 1.2 kg/m³ por defecto: la densidad se calcula "
                                  "con temperatura, altitud/presión y humedad."))
        g, f = group("Condiciones de cálculo")
        self.mode = combo(list(MODE_LABELS.items()))
        self.t = QField("temperature")
        self.alt = QField("length", optional=True)
        self.use_p = QCheckBox("Usar presión barométrica medida / de proyecto")
        self.p = QField("pressure", optional=True, minimum=1.0)
        self.rh = QField(None, unit_override="%", scale=100.0, minimum=0.0, maximum=1.0)
        self.rho_m = QField("density", optional=True)
        self.tmin = QField("temperature", optional=True)
        f.addRow("Condición", self.mode)
        f.addRow("Temperatura de bulbo seco", self.t)
        f.addRow("Altitud", self.alt)
        f.addRow(self.use_p)
        f.addRow("Presión barométrica", self.p)
        f.addRow("Humedad relativa", self.rh)
        f.addRow("Densidad declarada (verificación, opcional)", self.rho_m)
        f.addRow("Temp. superficial mínima de ductos (condensación, opcional)", self.tmin)
        f.addRow(note("Si se indica la presión y la altitud, el programa verifica su consistencia con la atmósfera estándar."))
        rg, rf = group("Resultados", QVBoxLayout())
        self.table = ResultTable()
        self.table.setMinimumHeight(420)
        rf.addWidget(self.table)
        self.lay.addWidget(hrow(g, rg))
        tabs, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(tabs)
        for w in (self.t, self.alt, self.p, self.rh, self.rho_m, self.tmin):
            w.changed.connect(self._apply)
        self.mode.currentIndexChanged.connect(self._apply)
        self.use_p.toggled.connect(self._apply)

    def load(self):
        self._loading = True
        a = self.ctx.project.air
        set_combo(self.mode, a.mode)
        self.t.set_value(a.t_c)
        self.alt.set_value(a.altitude_m)
        self.use_p.setChecked(a.p_pa is not None)
        self.p.set_value(a.p_pa)
        self.rh.set_value(a.rh)
        self.rho_m.set_value(a.rho_measured)
        self.tmin.set_value(a.t_min_surface_c)
        self.p.setEnabled(a.p_pa is not None)
        self._loading = False

    def _apply(self, *_):
        if self._loading:
            return
        a = self.ctx.project.air
        a.mode = self.mode.currentData()
        a.t_c = self.t.value() if self.t.value() is not None else 20.0
        a.altitude_m = self.alt.value()
        a.p_pa = self.p.value() if self.use_p.isChecked() else None
        self.p.setEnabled(self.use_p.isChecked())
        a.rh = self.rh.value() if self.rh.value() is not None else 0.5
        a.rho_measured = self.rho_m.value()
        a.t_min_surface_c = self.tmin.value()
        custom = a.mode == "custom"
        for w in (self.t, self.rh, self.use_p):
            w.setEnabled(custom)
        self.emit_changed()

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        self.table.set_data(*T.air_table(r.air, self.ctx.system))
        self.fill_common(self.alerts, self.dec, self.trace, "Propiedades del aire")


class AirflowPage(BasePage):
    modules = ["Caudales"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Cálculo de caudales", "Renovaciones por hora, balance de contaminantes (dilución con "
                                  "factor de mezcla), balance térmico sensible y ventilación por ocupación (ASHRAE 62.1). "
                                  "La captura localizada se calcula en 'Campanas de extracción'."))
        g, f = group("Objetivo del sistema")
        self.purpose = combo([("general", "Ventilación general"), ("contaminant_control", "Control de contaminantes"),
                              ("thermal", "Evacuación de calor"), ("comfort", "Calidad de aire por ocupación")])
        self.src = QCheckBox("La fuente del contaminante es identificable / localizada")
        f.addRow("Propósito", self.purpose)
        f.addRow(self.src)
        self.lay.addWidget(g)
        tabs = QTabWidget()
        # ACH
        w1 = QWidget(); f1 = QFormLayout(w1)
        self.ach_on = QCheckBox("Habilitar método ACH")
        self.L, self.W, self.H = QField("length"), QField("length"), QField("length")
        self.V = QField("volume", optional=True)
        self.ach = QField(None, unit_override="1/h", minimum=0.0)
        for lbl, w in (("", self.ach_on), ("Largo", self.L), ("Ancho", self.W), ("Altura", self.H),
                       ("Volumen (opcional, reemplaza L·A·H)", self.V), ("Renovaciones por hora", self.ach)):
            f1.addRow(lbl, w) if lbl else f1.addRow(w)
        f1.addRow(note("ACH es un dato de diseño; no justifica por sí solo el control de contaminantes."))
        tabs.addTab(w1, "A. Renovaciones por hora")
        # Dilución
        w2 = QWidget(); f2 = QFormLayout(w2)
        self.dil_on = QCheckBox("Habilitar balance de contaminantes")
        self.G = QField("gen_rate", minimum=0.0)
        self.Ct = QField("concentration", minimum=0.0)
        self.Cb = QField("concentration", minimum=0.0)
        self.K = QField(None, unit_override="-", minimum=1.0)
        self.eff = QField(None, unit_override="%", scale=100, minimum=0.0, maximum=0.999)
        self.C0 = QField("concentration", optional=True)
        self.tox = QCheckBox("Toxicidad / VLE documentados (NOM-010-STPS o TLV)")
        for lbl, w in (("", self.dil_on), ("Tasa de generación G", self.G), ("Concentración objetivo", self.Ct),
                       ("Concentración de fondo", self.Cb), ("Factor de mezcla K (≥1)", self.K),
                       ("Eficiencia de captura/remoción", self.eff), ("Concentración inicial (purga, opcional)", self.C0),
                       ("", self.tox)):
            f2.addRow(lbl, w) if lbl else f2.addRow(w)
        f2.addRow(note("Modelo de mezcla perfecta corregido con K (ACGIH). No representa gradientes cerca de la fuente."))
        tabs.addTab(w2, "C. Balance de contaminantes")
        # Térmico
        w3 = QWidget(); f3 = QFormLayout(w3)
        self.th_on = QCheckBox("Habilitar balance térmico")
        self.sources = QLineEdit()
        self.tin, self.tout = QField("temperature"), QField("temperature")
        f3.addRow(self.th_on)
        self.src_lbl = f"Fuentes de calor sensible (separadas por ';')"
        f3.addRow(self.src_lbl, self.sources)
        f3.addRow("Temperatura de entrada", self.tin)
        f3.addRow("Temperatura de salida admisible", self.tout)
        self.src_unit = note("")
        f3.addRow(self.src_unit)
        tabs.addTab(w3, "D. Balance térmico")
        # Ocupación
        w4 = QWidget(); f4 = QFormLayout(w4)
        self.oc_on = QCheckBox("Habilitar ventilación por ocupación")
        self.Rp = QField(None, unit_override="L/(s·persona)")
        self.Pz = QField(None, unit_override="personas")
        self.Ra = QField(None, unit_override="L/(s·m²)")
        self.Az = QField(None, unit_override="m²")
        self.Ez = QField(None, unit_override="-")
        for lbl, w in (("", self.oc_on), ("Rp (tabla ASHRAE 62.1)", self.Rp), ("Pz", self.Pz),
                       ("Ra (tabla ASHRAE 62.1)", self.Ra), ("Az", self.Az), ("Ez", self.Ez)):
            f4.addRow(lbl, w) if lbl else f4.addRow(w)
        f4.addRow(note("Rp, Ra y Ez son valores tabulados de ASHRAE 62.1 (edición vigente); el programa no los inventa."))
        tabs.addTab(w4, "E. Ocupación (ASHRAE 62.1)")
        self.lay.addWidget(tabs)
        rg, rf = group("Resultados", QVBoxLayout())
        self.table = ResultTable()
        self.table.setMinimumHeight(140)
        rf.addWidget(self.table)
        self.lay.addWidget(rg)
        t2, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(t2)
        for w in (self.L, self.W, self.H, self.V, self.ach, self.G, self.Ct, self.Cb, self.K, self.eff, self.C0, self.tin,
                  self.tout, self.Rp, self.Pz, self.Ra, self.Az, self.Ez):
            w.changed.connect(self._apply)
        for cb in (self.ach_on, self.dil_on, self.th_on, self.oc_on, self.tox, self.src):
            cb.toggled.connect(self._apply)
        self.purpose.currentIndexChanged.connect(self._apply)
        self.sources.editingFinished.connect(self._apply)
        UnitContext.listeners.append(self._refresh_sources)

    def _refresh_sources(self):
        af = self.ctx.project.airflow
        u = display_unit("heat", UnitContext.system)
        self.src_unit.setText(f"Unidades de las fuentes: {u}")
        self.sources.setText("; ".join(f"{to_display(x, 'heat', UnitContext.system):.4g}"
                                       for x in af.thermal.get("sources_W", [])))

    def load(self):
        self._loading = True
        af = self.ctx.project.airflow
        set_combo(self.purpose, af.purpose)
        self.src.setChecked(af.source_identifiable)
        a, d, t, o = af.ach, af.dilution, af.thermal, af.occupancy
        self.ach_on.setChecked(a.get("enabled", False))
        self.L.set_value(a.get("L")); self.W.set_value(a.get("W")); self.H.set_value(a.get("H"))
        self.V.set_value(a.get("V")); self.ach.set_value(a.get("ACH"))
        self.dil_on.setChecked(d.get("enabled", False))
        self.G.set_value(d.get("G_mg_s")); self.Ct.set_value(d.get("C_target")); self.Cb.set_value(d.get("C_bg"))
        self.K.set_value(d.get("K")); self.eff.set_value(d.get("capture_eff")); self.C0.set_value(d.get("C0"))
        self.tox.setChecked(d.get("toxicity_known", False))
        self.th_on.setChecked(t.get("enabled", False))
        self.tin.set_value(t.get("t_in")); self.tout.set_value(t.get("t_out"))
        self._refresh_sources()
        self.oc_on.setChecked(o.get("enabled", False))
        self.Rp.set_value(o.get("Rp")); self.Pz.set_value(o.get("Pz")); self.Ra.set_value(o.get("Ra"))
        self.Az.set_value(o.get("Az")); self.Ez.set_value(o.get("Ez"))
        self._loading = False

    def _apply(self, *_):
        if self._loading:
            return
        af = self.ctx.project.airflow
        af.purpose = self.purpose.currentData()
        af.source_identifiable = self.src.isChecked()
        af.ach.update({"enabled": self.ach_on.isChecked(), "L": self.L.value() or 0, "W": self.W.value() or 0,
                       "H": self.H.value() or 0, "V": self.V.value(), "ACH": self.ach.value() or 0})
        af.dilution.update({"enabled": self.dil_on.isChecked(), "G_mg_s": self.G.value() or 0, "C_target": self.Ct.value() or 0,
                            "C_bg": self.Cb.value() or 0, "K": self.K.value() or 1, "capture_eff": self.eff.value() or 0,
                            "C0": self.C0.value(), "toxicity_known": self.tox.isChecked()})
        try:
            src = [from_display(parse_float(x), "heat", UnitContext.system) for x in self.sources.text().split(";") if x.strip()]
        except ValueError:
            src = af.thermal.get("sources_W", [])
        af.thermal.update({"enabled": self.th_on.isChecked(), "sources_W": src, "t_in": self.tin.value(),
                           "t_out": self.tout.value()})
        af.occupancy.update({"enabled": self.oc_on.isChecked(), "Rp": self.Rp.value() or 0, "Pz": self.Pz.value() or 0,
                             "Ra": self.Ra.value() or 0, "Az": self.Az.value() or 0, "Ez": self.Ez.value() or 1})
        self.emit_changed()

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        hdr, rows = T.airflow_table(r, self.ctx.system)
        self.table.set_data(hdr, rows)
        self.fill_common(self.alerts, self.dec, self.trace, "Caudales")
