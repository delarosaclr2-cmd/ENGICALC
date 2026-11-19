"""Pruebas de regresión de la revisión del PR (hallazgos P1/P2).

1. [P1] Eficiencias físicamente imposibles (η ≥ 100 %): la curva se rechaza y no se
   selecciona motor.
2. [P1] Velocidades de transporte verificadas también con los caudales REALES del
   ventilador (diseño que cumple el mínimo, operación que no lo cumple).
3. [P2] Intervalo de búsqueda del punto de operación construido con la curva ya
   ajustada a las rpm y al diámetro seleccionados.
4. [P2] La exportación nunca combina entradas actuales con resultados anteriores.

Segunda revisión:

5. [P2] Eficiencia estática nula en descarga libre: una curva estática que termina en
   FSP = 0 con caudal positivo es válida (η_s = Q·FSP/W = 0) y no debe rechazarse.

Cada caso reproduce el escenario descrito en la revisión y lo contrasta con un
cálculo independiente cuando aplica.
"""
from __future__ import annotations

import math
import os
import time

import pytest

from core.calculation import run_project, input_fingerprint, build_flow_context
from core.fan_curves import FanCurve, AdjustedFan, FanCurveError
from core.network_solver import NetworkModel, NetNode, NetSegment, solve_operating
from core.power import power_chain, PhysicalInconsistencyError, PowerError
from core.project import Project, NetworkSettings, FanSelection, PowerInputs
from core import constants as C
from validation.comparator import metrics_from_results

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# 1. Eficiencia > 100 %
# ---------------------------------------------------------------------------

def _halved_power_project(example_project):
    p = example_project.clone()
    p.alternatives = []
    fan = next(f for f in p.fans if f.id == "BI-560")
    for pt in fan.points:
        pt["W"] = pt["W"] / 2.0
    return p


def test_curve_with_halved_power_is_rejected(check, example_project):
    p = _halved_power_project(example_project)
    fan = next(f for f in p.fans if f.id == "BI-560")
    errs = fan.validate()
    assert errs and any("≥ 100 %" in e for e in errs), errs
    # cálculo independiente de la eficiencia del punto de mayor eficiencia original (η = 0.80 → 1.60)
    pt = fan.points[4]
    check("η_t del punto con potencia a la mitad", {"Q": pt["Q"], "P": pt["P"], "W": pt["W"]}, 1.60,
          pt["Q"] * pt["P"] / pt["W"], 1e-12, reference="η = Q·P/W (curva total, ρ_ref)")
    with pytest.raises(FanCurveError):
        AdjustedFan(fan)


def test_halved_power_blocks_motor_and_dictamen(example_project, db, settings):
    p = _halved_power_project(example_project)
    r = run_project(p, db, settings)
    assert r.power is None, "no debe seleccionarse motor con una curva incoherente"
    assert r.power_blocked
    crit = [a for a in r.alerts if a.level == "CRÍTICO"]
    assert any(a.parameter == "Curva del ventilador" and "≥ 100 %" in a.detected for a in crit)
    assert r.decisions["Potencia y motores"].code in ("insuf", "no")
    assert r.dictamen.decision_code == "no"
    m = metrics_from_results("A", p, r, 3, 3)
    assert not m.eligible and m.P_elec is None


def test_power_chain_rejects_curve_power_below_air_power(check):
    Q, FTP = 2.25, 2369.0
    W_curve = Q * FTP / 1.59            # potencia de curva que implica η = 159 %
    with pytest.raises(PhysicalInconsistencyError) as ei:
        power_chain(Q, FTP, W_fan_curve=W_curve, ratings_kw=[4.0, 5.5, 7.5, 11.0])
    check("η reportada en el bloqueo", {"Q": Q, "FTP": FTP, "W": W_curve}, 1.59, ei.value.eta, 1e-12,
          reference="η = Q·FTP/W")


def test_power_chain_rejects_static_efficiency_implying_total_over_100():
    # η_s = 0.80 con FSP = 500 Pa y FTP = 700 Pa → η_t = 0.80·700/500 = 1.12 (imposible)
    with pytest.raises(PhysicalInconsistencyError):
        power_chain(1.0, 700.0, FSP=500.0, eta_fan=0.80, eta_basis="static", ratings_kw=[1.1, 1.5])


def test_power_chain_rejects_unit_efficiency():
    with pytest.raises(PowerError):
        power_chain(1.0, 1000.0, eta_fan=1.0)


def test_runtime_efficiency_over_100_gives_critical_power_alert(example_project, db, settings, monkeypatch):
    """Si la curva pasa la validación por puntos pero la potencia en el punto de operación resulta menor que la
    potencia al aire (p. ej. por interpolación/extrapolación), la cadena de potencias se bloquea con alerta CRÍTICA."""
    import core.fan_curves as FC
    orig = FC.AdjustedFan.shaft_power

    def low_power(self, Q, rho=None):
        w = orig(self, Q, rho)
        return None if w is None else w / 2.0

    monkeypatch.setattr(FC.AdjustedFan, "shaft_power", low_power)
    p = example_project.clone()
    p.alternatives = []
    r = run_project(p, db, settings)
    assert r.power is None
    al = [a for a in r.alerts if a.parameter == "Coherencia caudal–presión–potencia"]
    assert al and al[0].level == "CRÍTICO" and al[0].value > 1.0
    assert r.dictamen.decision_code == "no"


def test_valid_curves_pass_and_coherence_warning(example_project):
    for f in example_project.fans:
        assert f.validate() == [], f.id
        assert f.coherence_warnings() == [], f.id
    f = example_project.fans[0]
    g = FanCurve.from_dict(dict(f.to_dict(), points=[dict(pt) for pt in f.points]))
    g.points[3]["eta"] = g.points[3]["eta"] * 0.85      # declarada 15 % menor que Q·P/W
    assert g.validate() == []
    assert len(g.coherence_warnings()) == 1


# ---------------------------------------------------------------------------
# 2. Velocidades de transporte en operación real
# ---------------------------------------------------------------------------

def _vmin_independent(db, class_id, rho):
    v = db.transport_class(class_id)["v_min_m_s"]
    df = rho / C.RHO_STD_AMCA
    return v / math.sqrt(df) if df < 1 else v


def test_design_meets_transport_but_real_operation_does_not(check, example_project, db, settings):
    p = example_project.clone()
    p.alternatives = []
    p.fan_selection.rpm = 2110.0
    r = run_project(p, db, settings)
    fe = r.selected_fan
    opn = fe.op_network
    assert opn is not None and opn.converged
    flagged = {a.item: a for a in r.alerts if a.parameter == "Velocidad de transporte"}
    for seg_id, hood in (("R1", "H1"), ("R4", "H4")):
        ev_d = r.network_design.state.seg_evals[seg_id]
        ev_o = opn.state.seg_evals[seg_id]
        seg = next(s for s in r.model.segments if s.id == seg_id)
        A = math.pi * seg.D ** 2 / 4.0
        # velocidad independiente en operación: V = ṁ_campana/(ρ·A)
        V_ind = opn.state.node_mdot[hood] / (ev_o.rho * A)
        check(f"V operación {seg_id}", {"ṁ": opn.state.node_mdot[hood], "ρ": ev_o.rho, "D": seg.D}, V_ind, abs(ev_o.V),
              1e-9, reference="Continuidad V = ṁ/(ρ·A)")
        vmin_d = _vmin_independent(db, "average_industrial", ev_d.rho)
        vmin_o = _vmin_independent(db, "average_industrial", ev_o.rho)
        assert abs(ev_d.V) >= vmin_d, f"{seg_id}: el diseño debe cumplir el mínimo"
        assert abs(ev_o.V) < vmin_o, f"{seg_id}: la operación real no cumple el mínimo"
        assert seg_id in flagged and flagged[seg_id].level == "ALTO"
        check(f"V alerta {seg_id}", {}, abs(ev_o.V), flagged[seg_id].value, 1e-12, reference="Valor de la alerta")
    m = metrics_from_results("2110 rpm", p, r, 3, 3)
    assert not m.eligible and not m.transport_ok and m.v_basis == "operación"
    assert r.dictamen.decision_code in ("mod", "no")


def test_catalog_speed_operation_meets_transport(example_project, db, settings):
    p = example_project.clone()
    p.alternatives = []
    r = run_project(p, db, settings)
    assert not [a for a in r.alerts if a.parameter == "Velocidad de transporte"]
    assert any(a.level == "CORRECTO" and a.parameter == "Velocidades en operación" for a in r.alerts)
    m = metrics_from_results("base", p, r, 3, 3)
    assert m.eligible and m.v_basis == "operación"


# ---------------------------------------------------------------------------
# 3. Intervalo de búsqueda con rpm y diámetro seleccionados
# ---------------------------------------------------------------------------

def _small_network_project(rpm=None, D=None) -> Project:
    p = Project()
    m = NetworkModel()
    for nd in [NetNode("H1", "hood", "Campana", q_design=0.15), NetNode("FAN", "fan", "Ventilador"),
               NetNode("OUT", "outlet", "Descarga", exit_K=1.0)]:
        m.nodes[nd.id] = nd
    m.segments = [NetSegment("S1", "H1", "FAN", "circular", 0.125, length=10.0),
                  NetSegment("D1", "FAN", "OUT", "circular", 0.125, length=3.0)]
    p.network = m
    p.network_settings = NetworkSettings("fumes", "none", "sucio")
    Q = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
    P = [1500, 1480, 1420, 1320, 1180, 1000]
    eta = [0.45, 0.60, 0.70, 0.74, 0.72, 0.65]
    pts = [{"Q": q, "P": pp, "eta": e, "W": q * pp / e} for q, pp, e in zip(Q, P, eta)]
    p.fans = [FanCurve(id="F1", model="prueba", rpm=2000, rho_ref=1.2, diameter_m=0.40, outlet_area_m2=0.02,
                       points=pts, max_rpm=2600, source="Curva sintética de prueba")]
    p.fan_selection = FanSelection("F1", rpm, D)
    p.power = PowerInputs()
    return p


@pytest.mark.parametrize("rpm,D", [(2000, None), (2400, None), (1600, None), (2000, 0.44), (2300, 0.42)])
def test_operating_point_found_after_speed_or_diameter_change(check, db, settings, rpm, D):
    p = _small_network_project(rpm, D)
    r = run_project(p, db, settings)
    fe = r.selected_fan
    assert fe.adjusted is not None and fe.adjusted.rpm == rpm
    assert fe.op is not None, f"sin punto de operación a {rpm} rpm, D = {D}"
    assert not any(a.parameter == "Punto de operación" and a.level == "CRÍTICO" for a in r.alerts)
    assert fe.adjusted.in_domain(fe.op.Q)
    # contraste independiente: solucionador de red en modo operación (incógnitas de caudal) con la curva ajustada
    nd = r.network_design
    ctx = build_flow_context(p, r.air, db, settings, "sucio")
    ctx.extra_K = dict(nd.damper_K)
    x0 = {h: nd.state.node_mdot[h] for h in nd.hood_q_final}
    adj = AdjustedFan(p.fans[0], rpm=rpm, rho=nd.state.rho_fan, diameter_m=D)
    opn = solve_operating(r.model, ctx, x0, fan_ftp=lambda Q, rho: adj.ftp(Q, rho))
    assert opn.converged
    check(f"Q operación {rpm} rpm D={D}", {"rpm": rpm, "D": D}, opn.state.Q_fan, fe.op.Q, 1e-6,
          reference="Solucionador de red en operación (independiente del muestreo de la curva del sistema)")
    qs = [x[0] for x in r.system_curve]
    assert min(qs) <= fe.adjusted.q_min + 1e-12 or min(qs) <= 0.05 * nd.state.Q_fan + 1e-12
    assert max(qs) >= fe.adjusted.q_max - 1e-12


def test_reviewer_case_2400_rpm(check, db, settings):
    """Caso de la revisión: de 2000 a 2400 rpm (≤ 2600 permitidas) el punto pasa de ≈0.29 a ≈0.35 m³/s, fuera del
    dominio de catálogo (≤ 0.300 m³/s) pero dentro del dominio ajustado (≤ 0.360 m³/s)."""
    r0 = run_project(_small_network_project(2000), db, settings)
    r1 = run_project(_small_network_project(2400), db, settings)
    q0, q1 = r0.selected_fan.op.Q, r1.selected_fan.op.Q
    assert q0 <= 0.300 < q1 <= r1.selected_fan.adjusted.q_max
    check("dominio ajustado q_max = 0.30·2400/2000", {"N": 2400}, 0.36, r1.selected_fan.adjusted.q_max, 1e-12,
          reference="Q ∝ N (ley de semejanza)")


# ---------------------------------------------------------------------------
# 4. Exportación con resultados desactualizados
# ---------------------------------------------------------------------------

def test_fingerprint_ignores_save_timestamp(example_project, db, settings):
    a = input_fingerprint(example_project, settings, db)
    time.sleep(1.05)                     # cambia la marca 'saved' de to_dict()
    assert input_fingerprint(example_project, settings, db) == a
    p = example_project.clone()
    p.air.t_c = 35.0
    assert input_fingerprint(p, settings, db) != a
    s2 = settings.copy()
    s2.data["criteria"]["flow_deficit_tolerance_pct"]["value"] = 7.0
    assert input_fingerprint(example_project, s2, db) != a


def test_reports_reject_stale_results(tmp_path, example_project, db, settings):
    from reports.consistency import StaleResultsError
    from reports.pdf_report import generate_pdf
    from reports.excel_export import export_excel
    p = example_project.clone()
    r = run_project(p, db, settings)
    p.air.t_c = 35.0                      # entrada modificada después del cálculo
    with pytest.raises(StaleResultsError):
        generate_pdf(p, r, db, settings, str(tmp_path / "x.pdf"))
    with pytest.raises(StaleResultsError):
        export_excel(p, r, db, settings, str(tmp_path / "x.xlsx"))
    assert not (tmp_path / "x.pdf").exists() and not (tmp_path / "x.xlsx").exists()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _wait(app, cond, timeout=60):
    t = time.time()
    while not cond() and time.time() - t < timeout:
        app.processEvents()
        time.sleep(0.02)
    return cond()


def test_gui_export_recalculates_when_autorecalc_disabled(qapp, check, example_project, db, settings, tmp_path,
                                                          monkeypatch):
    import openpyxl
    from PySide6.QtWidgets import QFileDialog
    from PySide6.QtGui import QDesktopServices
    from interface.main_window import MainWindow
    w = MainWindow(db, settings.copy(), example_project.clone(), None)
    assert _wait(qapp, lambda: w.ctx.results is not None and w.results_current())
    rho_25 = w.ctx.results.air.rho
    w.pages[11].auto.setChecked(False)               # recálculo automático desactivado
    air = w.pages[1]
    air.t.edit.setText("35")
    air.t._commit()
    for _ in range(60):                              # > 500 ms de rebote: no debe recalcular
        qapp.processEvents()
        time.sleep(0.02)
    assert w.ctx.project.air.t_c == 35.0
    assert w.ctx.results.air.t_c == 25.0 and not w.results_current()   # resultados desactualizados
    xlsx, pdf = str(tmp_path / "gui.xlsx"), str(tmp_path / "gui.pdf")
    monkeypatch.setattr(QDesktopServices, "openUrl", staticmethod(lambda *a, **k: True))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (xlsx, "")))
    w.pages[9].export_excel()
    assert os.path.exists(xlsx)
    # tras exportar, los resultados corresponden a 35 °C y a las entradas actuales
    assert w.ctx.results.air.t_c == 35.0 and w.results_current()
    ref = run_project(w.ctx.project.clone(), db, w.ctx.settings.copy())     # cálculo independiente a 35 °C
    ws = openpyxl.load_workbook(xlsx)["Aire"]
    vals = {row[0]: row[1] for row in ws.iter_rows(min_row=2, values_only=True) if row and row[0]}
    check("t exportada", {"t_c": 35.0}, 35.0, vals["Temperatura de bulbo seco"], 0, reference="Entrada actual")
    check("ρ exportada = ρ(35 °C)", {"t_c": 35.0}, ref.air.rho, vals["Densidad del aire húmedo"], 1e-3,
          reference="run_project a 35 °C (independiente de la GUI)")
    assert abs(vals["Densidad del aire húmedo"] - rho_25) / rho_25 > 0.02
    # PDF: misma garantía
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (pdf, "")))
    air.t.edit.setText("30")
    air.t._commit()
    assert not w.results_current()
    w.pages[9].export_pdf()
    assert os.path.exists(pdf) and w.ctx.results.air.t_c == 30.0 and w.results_current()
    w.dirty = False
    w.close()


def test_gui_discards_older_background_result(qapp, example_project, db, settings):
    from interface.main_window import MainWindow
    w = MainWindow(db, settings.copy(), example_project.clone(), None)
    assert _wait(qapp, lambda: w.ctx.results is not None)
    current = w.ctx.results
    stale = run_project(example_project.clone(), db, settings)
    w._calc_done(stale, 0.0, w._applied_seq - 1)     # resultado de un cálculo anterior que llega tarde
    assert w.ctx.results is current
    w.dirty = False
    w.close()


# ---------------------------------------------------------------------------
# 5. Eficiencia estática nula en el extremo de descarga libre
# ---------------------------------------------------------------------------

# Curva sintética en PRESIÓN ESTÁTICA de un ventilador pequeño: termina en descarga libre
# (FSP = 0) con caudal positivo, donde η_s = Q·FSP/W = 0 mientras η_t sigue siendo positiva
# gracias a la presión dinámica de salida. ρ_ref = 1.2 kg/m³, área de descarga 0.03 m².
_EST_Q = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30]
_EST_FSP = [250.0, 235.0, 205.0, 160.0, 95.0, 0.0]
_EST_W = [41.7, 45.2, 49.6, 53.3, 52.8, 48.0]
_EST_ETA_S = [0.30, 0.52, 0.62, 0.60, 0.45, 0.00]


def _static_curve(**overrides) -> FanCurve:
    """Curva estática de prueba. ``overrides`` modifica el último punto (descarga libre)."""
    pts = [{"Q": q, "P": p, "W": w, "eta": e}
           for q, p, w, e in zip(_EST_Q, _EST_FSP, _EST_W, _EST_ETA_S)]
    pts[-1].update(overrides)
    return FanCurve(id="EST", model="estática de prueba", rpm=2000, rho_ref=1.2, diameter_m=0.25,
                    outlet_area_m2=0.03, pressure_basis="static", points=pts, max_rpm=2600,
                    source="Curva sintética de prueba")


def test_static_curve_zero_efficiency_at_free_delivery_is_accepted(check):
    """FSP = 0 con Q > 0: η_s = 0 es correcta y la curva debe aceptarse."""
    curve = _static_curve()
    assert curve.validate() == [], curve.validate()
    # Cálculo independiente en el punto de descarga libre: la presión total es la dinámica
    # de salida, VP = ½·ρ·(Q/A)² = ½·1.2·(0.30/0.03)² = 60 Pa, de modo que η_t = Q·FTP/W > 0.
    Q, W = _EST_Q[-1], _EST_W[-1]
    vp = 0.5 * 1.2 * (Q / 0.03) ** 2
    check("VP de salida en descarga libre", {"Q": Q, "A": 0.03, "ρ": 1.2}, 60.0, vp, 1e-12,
          reference="VP = ½·ρ·v², v = Q/A")
    check("FTP en descarga libre", {"FSP": 0.0, "VP": vp}, vp, curve.total_pressure_at_point(curve.points[-1]),
          1e-12, reference="FTP = FSP + VP_salida (curva en base estática)")
    check("η_t en descarga libre", {"Q": Q, "FTP": vp, "W": W}, Q * vp / W, 0.375, 1e-3,
          reference="η_t = Q·FTP/W, calculada a mano")
    fan = AdjustedFan(curve)                      # no debe lanzar FanCurveError
    assert fan.eta_total(Q) > 0.0
    assert curve.coherence_warnings() == []       # η_s declarada coherente con Q·FSP/W


def test_zero_efficiency_with_positive_pressure_is_rejected():
    """η = 0 con caudal Y presión positivos exigiría potencia infinita: sigue siendo error."""
    errs = _static_curve(P=50.0, eta=0.0).validate()
    assert errs and "Eficiencia nula" in errs[0] and "0.3" in errs[0]
    with pytest.raises(FanCurveError):
        AdjustedFan(_static_curve(P=50.0, eta=0.0))


def test_zero_efficiency_at_shutoff_is_accepted():
    """A caudal nulo (cierre) η = 0 siempre es válida, cualquiera que sea la presión."""
    pts = [{"Q": 0.0, "P": 260.0, "W": 38.0, "eta": 0.0}]
    pts += [{"Q": q, "P": p, "W": w, "eta": e}
            for q, p, w, e in zip(_EST_Q, _EST_FSP, _EST_W, _EST_ETA_S)]
    curve = FanCurve(id="EST0", model="con cierre", rpm=2000, rho_ref=1.2, diameter_m=0.25,
                     outlet_area_m2=0.03, pressure_basis="static", points=pts)
    assert curve.validate() == []


def test_total_basis_curve_keeps_the_same_rule():
    """En base total la regla es idéntica: η = 0 solo con FTP = 0 o caudal nulo."""
    assert _static_curve(eta=0.0, P=0.0).validate() == []
    total = FanCurve(id="TOT", model="total", rpm=2000, rho_ref=1.2, diameter_m=0.25,
                     outlet_area_m2=0.03, pressure_basis="total",
                     points=[{"Q": q, "P": p, "W": w, "eta": e}
                             for q, p, w, e in zip(_EST_Q, _EST_FSP, _EST_W, _EST_ETA_S)])
    assert total.validate() == []                 # FTP = 0 en el extremo: η_t = 0 coherente
    total.points[-1]["P"] = 40.0                  # FTP > 0 con η = 0: incoherente
    assert any("Eficiencia nula" in e for e in total.validate())


@pytest.mark.parametrize("eta_bad", [-0.05, 1.0, 1.25])
def test_efficiencies_outside_range_still_rejected(eta_bad):
    """La protección contra eficiencias imposibles se conserva."""
    errs = _static_curve(eta=eta_bad).validate()
    assert errs and "físicamente imposible" in errs[0]


def test_static_zero_efficiency_curve_does_not_block_motor(check, db, settings):
    """Caso completo: la curva se acepta, hay punto de operación y SÍ se selecciona motor."""
    p = Project()
    m = NetworkModel()
    for nd in [NetNode("H1", "hood", "Campana", q_design=0.15), NetNode("FAN", "fan", "Ventilador"),
               NetNode("OUT", "outlet", "Descarga", exit_K=1.0)]:
        m.nodes[nd.id] = nd
    m.segments = [NetSegment("S1", "H1", "FAN", "circular", 0.15, length=6.0),
                  NetSegment("D1", "FAN", "OUT", "circular", 0.15, length=2.0)]
    p.network = m
    p.network_settings = NetworkSettings("fumes", "none", "sucio")
    p.fans = [_static_curve()]
    p.fan_selection = FanSelection("EST", None, None)
    p.power = PowerInputs()
    r = run_project(p, db, settings)
    fe = r.selected_fan
    assert not fe.error and fe.op is not None
    assert r.power is not None and r.power_blocked == "", r.power_blocked
    assert not [a for a in r.alerts if a.level == "CRÍTICO" and a.module == "Selección de ventiladores"]
    # contraste independiente de la cadena de potencias en el punto de operación
    pw = r.power
    check("η_t en el punto de operación", {"Q": pw.Q, "FTP": pw.FTP, "W_vent": pw.W_fan},
          pw.Q * pw.FTP / pw.W_fan, pw.eta_total, 1e-9, reference="η_t = Q·FTP/W (definición)")
    check("η_s en el punto de operación", {"Q": pw.Q, "FSP": pw.FSP, "W_vent": pw.W_fan},
          pw.Q * pw.FSP / pw.W_fan, pw.eta_static, 1e-9, reference="η_s = Q·FSP/W (definición)")
    assert 0.0 < pw.eta_total < 1.0 and pw.eta_static < pw.eta_total
