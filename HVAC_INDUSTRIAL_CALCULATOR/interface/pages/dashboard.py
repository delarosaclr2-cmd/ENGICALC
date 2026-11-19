"""Dashboard: indicadores clave, estado del dictamen y esquema del sistema."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QWidget, QLabel, QTextBrowser, QFrame, QVBoxLayout

from core.units import fmt
from graphics.plots import plot_system_schematic
from validation.decision_engine import DEC_COLORS
from ..widgets import KpiCard, PlotCanvas, level_badges
from .base import BasePage, header


class DashboardPage(BasePage):
    title = "Dashboard"

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Dashboard del proyecto", "Resumen del último cálculo: indicadores, estado del dictamen "
                                  "y esquema del sistema. Los valores se actualizan automáticamente al modificar datos."))
        grid = QGridLayout()
        grid.setSpacing(10)
        self.k_q = KpiCard("Caudal en el ventilador")
        self.k_p = KpiCard("Presión total del ventilador (FTP)")
        self.k_pw = KpiCard("Potencia eléctrica")
        self.k_m = KpiCard("Motor normalizado")
        self.k_v = KpiCard("Velocidades en ductos")
        self.k_rho = KpiCard("Densidad del aire")
        self.k_e = KpiCard("Energía y costo anual")
        self.k_d = KpiCard("Decisión técnica global")
        for i, k in enumerate([self.k_q, self.k_p, self.k_pw, self.k_m, self.k_v, self.k_rho, self.k_e, self.k_d]):
            grid.addWidget(k, i // 4, i % 4)
        gw = QWidget()
        gw.setLayout(grid)
        self.lay.addWidget(gw)
        self.badges = QLabel()
        self.lay.addWidget(self.badges)
        self.plot = PlotCanvas(430)
        card = QFrame()
        card.setObjectName("card")
        cl = QVBoxLayout(card)
        cl.addWidget(self.plot)
        self.lay.addWidget(card)
        self.summary = QTextBrowser()
        self.summary.setMinimumHeight(230)
        self.lay.addWidget(self.summary)

    def render(self):
        r = self.ctx.results
        s = self.ctx.system
        if r is None:
            return
        nr = r.network_design
        fe = r.selected_fan
        if fe and fe.op:
            self.k_q.set(fmt(fe.op.Q, "flow", s), f"Operación real · diseño requerido {fmt(nr.state.Q_fan, 'flow', s)}")
            self.k_p.set(fmt(fe.op.FTP, "pressure", s), f"FSP {fmt(fe.op.FSP, 'pressure', s)} · requerido "
                         f"{fmt(nr.state.FTP, 'pressure', s)}")
        elif nr:
            self.k_q.set(fmt(nr.state.Q_fan, "flow", s), "Punto de diseño (sin curva de ventilador)")
            self.k_p.set(fmt(nr.state.FTP, "pressure", s), f"FSP {fmt(nr.state.FSP, 'pressure', s)}")
        pw = r.power
        if pw:
            self.k_pw.set(fmt(pw.P_elec, "power", s), f"Eje ventilador {fmt(pw.W_fan, 'power', s)}"
                          + (f" · η_t {pw.eta_total * 100:.1f} %" if pw.eta_total else ""))
            self.k_m.set(fmt(pw.motor_nominal, "power", s) if pw.motor_nominal else "—",
                         f"Carga {pw.motor_load_fraction * 100:.0f} % · {pw.motor_standard}" if pw.motor_load_fraction else "")
            self.k_e.set(f"{pw.energy_kwh:,.0f} kWh", f"{pw.cost:,.0f} {self.ctx.project.power.currency}/año")
        if nr:
            vs = [abs(e.V) for e in nr.state.seg_evals.values()]
            self.k_v.set(f"{fmt(min(vs), 'velocity', s, 3, False)}–{fmt(max(vs), 'velocity', s, 3)}",
                         f"{len(vs)} tramos · camino crítico desde {nr.governing_hood}")
        if r.air:
            self.k_rho.set(fmt(r.air.rho, "density", s), f"{r.air.t_c:.1f} °C · {fmt(r.air.p_pa, 'pressure', s)} · "
                           f"{r.air.rho / 1.2 * 100:.1f} % del estándar")
        if r.dictamen:
            self.k_d.set(r.dictamen.decision, "", DEC_COLORS[r.dictamen.decision_code])
            self.k_d.v.setWordWrap(True)
            self.k_d.v.setStyleSheet(f"color:{DEC_COLORS[r.dictamen.decision_code]}; font-size:11.5pt;")
        self.badges.setText("<b>Alertas:</b> " + level_badges(r.alerts))
        try:
            self.plot.set_figure(plot_system_schematic(self.ctx.project, r, s))
        except Exception as exc:  # noqa: BLE001
            self.plot.setToolTip(str(exc))
        html = "<h3>Evaluación por módulo</h3><table cellpadding='4'>"
        for m, d in r.decisions.items():
            html += f"<tr><td><b>{m}</b></td><td style='color:{d.color}'>{d.decision}</td></tr>"
        html += "</table>"
        if r.errors:
            html += "<h3 style='color:#B42318'>Errores de cálculo</h3><ul>" + "".join(
                f"<li>{k}: {v}</li>" for k, v in r.errors.items() if not k.startswith("trace")) + "</ul>"
        if r.dictamen and r.dictamen.modifications:
            html += "<h3>Modificaciones recomendadas</h3><ul>" + "".join(f"<li>{x}</li>" for x in r.dictamen.modifications[:8]) + "</ul>"
        self.summary.setHtml(html)
