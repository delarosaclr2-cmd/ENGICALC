"""Prueba de integración: banco de pruebas industrial (nave con 4 campanas).

Comprobaciones:
* Ejecución completa sin errores de módulo.
* Recalculo independiente del camino crítico a partir de las ecuaciones básicas
  (sin usar el solucionador de red).
* El punto de operación pertenece a la curva del ventilador y a la del sistema.
* Coherencia de la cadena de potencias.
* Dictamen y comparador de alternativas con conclusiones esperadas por diseño del caso.

Hipótesis y valores de referencia documentados en examples/build_example.py y en
docs/VALIDACION.md.
"""
import math

import pytest

from core.calculation import run_project
from core.project import Project
from core.friction import f_colebrook
from validation.comparator import metrics_from_results, compare


@pytest.fixture(scope="module")
def results(example_project, db, settings):
    return run_project(example_project, db, settings)


def test_runs_without_errors(results):
    assert not [k for k in results.errors if not k.startswith("trace")], results.errors


def test_air_density_cdmx(check, results):
    from CoolProp.HumidAirProp import HAPropsSI
    a = results.air
    rho = 1.0 / HAPropsSI("Vha", "T", 298.15, "P", a.p_pa, "R", 0.5)
    check("ρ a 2240 m, 25 °C, 50 %", {"Z": 2240, "t": 25, "HR": 0.5}, rho, a.rho, 1e-3, reference="CoolProp")


def test_critical_path_independent(check, results, example_project, db):
    """Recalcula cada tramo del camino crítico con fórmulas elementales."""
    nr = results.network_design
    model = results.model
    rough = db.roughness_lib()
    st = nr.state
    total = 0.0
    for sid in nr.critical_path:
        seg = model.seg(sid)
        ev = st.seg_evals[sid]
        rho, mu = ev.rho, ev.mu
        A = math.pi * seg.D ** 2 / 4
        V = abs(ev.mdot) / rho / A
        VP = 0.5 * rho * V * V
        Re = rho * V * seg.D / mu
        f = f_colebrook(Re, rough[seg.material_id] / seg.D)
        dp = f * seg.length / seg.D * VP
        for fi in seg.fittings:
            if fi.fitting_id.startswith("elbow"):
                ang = 90 if "90" in fi.fitting_id else 45
                rd = float(fi.fitting_id.split("RD")[1])
                A1 = 1.0 if ang == 90 else 0.9 * math.sin(math.radians(ang))
                kloc = A1 * 0.21 / math.sqrt(rd)
                if Re < 3e5:
                    kloc *= max(11.5 / Re ** 0.19, 1.0)
                k = kloc + 0.0175 * f * rd * ang
            elif fi.fitting_id == "branch_entry_30":
                k = 0.18
            elif fi.fitting_id == "branch_entry_45":
                k = 0.28
            else:
                raise AssertionError(fi.fitting_id)
            dp += fi.qty * k * VP
        if seg.hood_entry is not None:
            dp += seg.hood_entry.Fh * VP
            if seg.hood_entry.kind == "slot":
                dp += seg.hood_entry.Fs * 0.5 * rho * (abs(ev.mdot) / rho / seg.hood_entry.slot_area) ** 2
        for e in seg.equipment:
            dp += e.dp_dirty * (abs(ev.mdot) / rho / e.q_ref) ** e.n_exp
        if model.nodes[seg.to_node].kind == "outlet":
            dp += model.outlet.exit_K * VP
        check(f"ΔP tramo {sid}", {"D": seg.D, "L": seg.length}, dp, ev.dp_total, 1e-9,
              reference="Recalculo con ecuaciones elementales")
        total += dp
    check("FTP = Σ pérdidas del camino crítico", {"camino": nr.critical_path}, total, st.FTP, 1e-9,
          reference="Balance de presión total en el camino crítico")


def test_branch_balance_after_design(results, settings):
    for b in results.network_design.balance:
        assert b.action in ("aceptado",) or b.action.startswith("aumento")
    st = results.network_design.state
    for nid, lst in st.junction_ends.items():
        tps = [tp for _, tp in lst]
        assert max(tps) - min(tps) <= abs(min(tps)) * settings.cval("imbalance_ignore_pct", 5) / 100 + 1e-6


def test_operating_point_on_both_curves(check, results):
    fe = results.selected_fan
    op = fe.op
    check("FTP ventilador = FTP sistema en operación", {"Q_op": op.Q}, fe.op_network.state.FTP, op.FTP, 1e-4,
          reference="Intersección de curvas")
    check("continuidad en operación", {}, sum(fe.op_network.state.node_mdot[h] for h in fe.op_network.hood_q_final),
          fe.op_network.state.mdot_fan, 1e-12, reference="Σṁ campanas = ṁ ventilador")
    for h, qreq in results.hood_q_required.items():
        assert fe.op_network.hood_q_final[h] >= qreq * 0.95


def test_power_chain(check, results, example_project):
    pw = results.power
    pinp = example_project.power
    check("P_elec = W_vent/(η_tr·η_m)", {"η_tr": pinp.eta_drive, "η_m": pinp.eta_motor},
          pw.W_fan / (pinp.eta_drive * pinp.eta_motor), pw.P_elec, 1e-12, reference="Cadena de potencias")
    check("P_aire = Q·FTP", {}, pw.Q * pw.FTP, pw.P_air_total, 1e-12, reference="Definición")
    assert pw.motor_nominal >= pw.W_motor_out * (1 + pinp.margin) - 1e-6


def test_dictamen_and_alternatives(results, example_project, db, settings):
    assert results.dictamen is not None
    assert results.dictamen.decision_code in ("ok", "obs")
    assert len(results.dictamen.limitations) >= 5
    mets = []
    for alt in example_project.alternatives:
        pr = Project.from_dict(alt.project)
        rr = run_project(pr, db, settings)
        mets.append(metrics_from_results(alt.name, pr, rr, alt.complexity, alt.maintenance))
    mets, concl = compare(mets, settings.weights)
    by = {m.name[0]: m for m in mets}
    assert by["A"].eligible
    assert not by["B"].eligible and not by["B"].transport_ok      # velocidad de transporte insuficiente
    assert not by["D"].eligible and by["D"].deficit_max_pct > 5   # ventilador subdimensionado
    assert "A —" in concl[0]


def test_fixed_speed_lower_resistance_increases_power(example_project, db, settings):
    """Comportamiento físico: a rpm fijas, menor resistencia → más caudal y (en esta zona de la curva) más potencia."""
    import copy
    base = run_project(example_project, db, settings)
    p = Project.from_dict(copy.deepcopy(example_project.to_dict()))
    for s in p.network.segments:
        if s.id in ("M1", "M2", "M3"):
            s.D = {"M1": 0.280, "M2": 0.355, "M3": 0.400}[s.id]
    r = run_project(p, db, settings)
    assert r.selected_fan.op.Q > base.selected_fan.op.Q
    assert r.power.W_fan > base.power.W_fan
