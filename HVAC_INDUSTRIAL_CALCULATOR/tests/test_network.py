"""Redes ramificadas: continuidad, balance de presiones y contraste independiente.

1. Caso analítico con resistencias puras (solo K, sin fricción): solución cerrada.
2. Segunda implementación independiente del modo de operación: incógnitas = presiones
   totales de nodo, cada tramo se invierte con bisección (formulación clásica de
   nudos), resuelto con fsolve. Debe coincidir con el solucionador del programa
   (formulación por trayectorias con incógnitas de caudal de campana).
3. Diseño balanceado: corrección exacta frente a la aproximación Q·√r.
"""
import copy
import math

import numpy as np
import pytest
from scipy.optimize import brentq, fsolve

from core.network_solver import (NetworkModel, NetNode, NetSegment, FlowContext, solve_design, solve_operating,
                                 forward, evaluate_segment, NetworkError)
from core.fittings import FittingInstance, FittingDef
from core.air_properties import moist_air_density


def _ctx(fittings=None):
    lib = {"k": FittingDef("k", "K del usuario", "Prueba", mode="user", K=None)}
    lib.update(fittings or {})
    return FlowContext(p_atm=101325.0, W=0.0, t_ambient=20.0, fittings_lib=lib, roughness_lib={"m": 0.09e-3})


def _k_only_network(K1, K2, D1, D2, K3=1.0, D3=0.3):
    m = NetworkModel()
    for nd in [NetNode("A", "hood"), NetNode("B", "hood"), NetNode("J", "junction"), NetNode("F", "fan"),
               NetNode("O", "outlet", exit_K=0.0)]:
        m.nodes[nd.id] = nd
    m.segments = [
        NetSegment("S1", "A", "J", "circular", D1, length=0.0, material_id="m", fittings=[FittingInstance("k", 1, K1)]),
        NetSegment("S2", "B", "J", "circular", D2, length=0.0, material_id="m", fittings=[FittingInstance("k", 1, K2)]),
        NetSegment("S3", "J", "F", "circular", D3, length=0.0, material_id="m", fittings=[FittingInstance("k", 1, K3)]),
        NetSegment("S4", "F", "O", "circular", D3, length=0.0, material_id="m"),
    ]
    return m


def test_k_only_split_analytic(check):
    K1, K2, D1, D2 = 2.0, 5.0, 0.2, 0.25
    m = _k_only_network(K1, K2, D1, D2)
    ctx = _ctx()
    rho = moist_air_density(20.0, 0.0, 101325.0)
    Qt = 1.2
    x0 = {"A": 0.5 * rho, "B": 0.5 * rho}
    r = solve_operating(m, ctx, x0, Q_total=Qt)
    A1, A2 = math.pi * D1 ** 2 / 4, math.pi * D2 ** 2 / 4
    ratio = (A1 / math.sqrt(K1)) / (A2 / math.sqrt(K2))   # Q1/Q2 con igual ΔP
    Q2 = Qt / (1 + ratio)
    Q1 = Qt - Q2
    check("Q1 reparto analítico", {"K1": K1, "K2": K2, "D1": D1, "D2": D2, "Qt": Qt}, Q1, r.hood_q_final["A"], 1e-6,
          reference="Igualdad de ΔP: Q ∝ A/√K")
    check("Q2 reparto analítico", {}, Q2, r.hood_q_final["B"], 1e-6, reference="Igualdad de ΔP")
    dp1 = K1 * 0.5 * rho * (Q1 / A1) ** 2
    A3 = math.pi * 0.3 ** 2 / 4
    ftp = dp1 + 1.0 * 0.5 * rho * (Qt / A3) ** 2
    check("FTP analítica", {}, ftp, r.state.FTP, 1e-6, reference="ΔP_ramal + K3·VP3")


def test_continuity_and_temperature_mixing(check):
    m = _k_only_network(2.0, 5.0, 0.2, 0.25)
    m.nodes["B"].temperature_c = 80.0
    ctx = _ctx()
    rhoA, rhoB = moist_air_density(20, 0, 101325), moist_air_density(80, 0, 101325)
    st = forward(m, ctx, {"A": 0.6, "B": 0.4}, {"A": 20.0, "B": 80.0})
    check("continuidad de masa", {"ṁA": 0.6, "ṁB": 0.4}, 1.0, st.mdot_fan, 1e-15, reference="Σṁ_entrada = ṁ_salida")
    check("temperatura de mezcla", {}, 0.6 * 20 + 0.4 * 80, st.t_fan, 1e-12, reference="Mezcla adiabática")
    check("ρ aguas abajo", {}, moist_air_density(44.0, 0, 101325), st.rho_fan, 1e-12, reference="Gas ideal a T_mezcla")


def _independent_node_solver(model, ctx, fan_ftp):
    """Formulación de nudos: incógnitas TP de uniones + TP entrada ventilador + ṁ ventilador."""
    junctions = [n for n in model.suction_order() if model.nodes[n].kind != "hood"]
    temps = {h.id: (h.temperature_c if h.temperature_c is not None else ctx.t_ambient) for h in model.nodes_of_kind("hood")}

    def seg_flow(seg, dp, t):
        if dp <= 0:
            return 0.0
        g = lambda mm: evaluate_segment(seg, mm, t, ctx).dp_total - dp  # noqa: E731
        hi = 0.1
        while g(hi) < 0:
            hi *= 2
        return brentq(g, 0.0, hi, xtol=1e-13)

    def node_temp_and_flows(tp):
        mflow, tnode = {}, dict(temps)
        for nid in junctions:
            streams = []
            for s in model.incoming(nid):
                up = 0.0 if model.nodes[s.from_node].kind == "hood" else tp[s.from_node]
                mm = seg_flow(s, up - tp[nid], tnode[s.from_node])
                mflow[s.id] = mm
                streams.append((mm, tnode[s.from_node]))
            tot = sum(a for a, _ in streams)
            tnode[nid] = sum(a * b for a, b in streams) / tot if tot > 0 else ctx.t_ambient
        return mflow, tnode

    def resid(x):
        tp = {nid: x[i] for i, nid in enumerate(junctions)}
        mfan = x[-1]
        mflow, tnode = node_temp_and_flows(tp)
        res = []
        for nid in junctions:
            inflow = sum(mflow[s.id] for s in model.incoming(nid))
            if nid == model.fan.id:
                res.append(inflow - mfan)
            else:
                out = model.outgoing(nid)[0]
                res.append(inflow - mflow[out.id])
        tf = tnode[model.fan.id]
        path = model.discharge_path()
        dpd = sum(evaluate_segment(s, mfan, tf, ctx, is_outlet=(i == len(path) - 1), exit_K=model.outlet.exit_K).dp_total
                  for i, s in enumerate(path))
        rho = ctx.rho(tf)
        res.append((fan_ftp(mfan / rho, rho) - (dpd - tp[model.fan.id])) / 100.0)
        return res

    x0 = [-200.0 * (i + 1) for i in range(len(junctions))] + [2.0]
    sol = fsolve(resid, x0, xtol=1e-12, full_output=True)
    tp = {nid: sol[0][i] for i, nid in enumerate(junctions)}
    mflow, _ = node_temp_and_flows(tp)
    return mflow, sol[0][-1]


def test_operating_vs_independent_node_solver(check, example_project, db):
    from core.calculation import prepare_model, build_flow_context
    from core.air_properties import compute_air_state
    from core.fan_curves import AdjustedFan
    p = example_project
    a = p.air
    air = compute_air_state(a.mode, a.t_c, a.altitude_m, a.p_pa, a.rh)
    model = prepare_model(p, db)
    from config.settings import load_settings
    ctx = build_flow_context(p, air, db, load_settings(), "sucio")
    fan = AdjustedFan(p.fans[0], rho=air.rho)
    ftp = lambda Q, rho: fan.ftp(Q, rho)  # noqa: E731
    x0 = {h.id: 0.6 * air.rho for h in model.nodes_of_kind("hood")}
    r = solve_operating(model, ctx, x0, fan_ftp=ftp)
    mflow, mfan = _independent_node_solver(model, ctx, ftp)
    check("ṁ ventilador (2 formulaciones)", {"red": "banco industrial"}, mfan, r.state.mdot_fan, 1e-6,
          reference="Formulación de nudos independiente (fsolve + bisección por tramo)")
    for h in model.nodes_of_kind("hood"):
        seg = model.outgoing(h.id)[0]
        check(f"ṁ campana {h.id}", {}, mflow[seg.id], r.state.node_mdot[h.id], 1e-5,
              reference="Formulación de nudos independiente")
    assert r.converged


def test_design_flow_increase_exact_vs_sqrt(check):
    m = _k_only_network(2.0, 6.0, 0.2, 0.2)
    ctx = _ctx()
    rho = ctx.rho(20.0)
    q = {"A": 0.5, "B": 0.5}
    res = solve_design(m, ctx, q, strategy="acgih", tol_ignore=0.0, tol_increase=5.0)
    rec = res.balance[0]
    # Con resistencias puras (sin fricción) la corrección exacta coincide con √r
    check("escala exacta = √r (sin fricción)", {"K1": 2, "K2": 6}, math.sqrt(rec.ratio), rec.scale, 1e-8,
          reference="ΔP ∝ Q² ⇒ Q_corr = Q·√r")
    st = res.state
    ends = dict(st.junction_ends["J"])
    check("presiones igualadas en la unión", {}, ends["S1"], ends["S2"], 1e-9, reference="Balance de presión total")


def test_design_dampers_then_operating_reproduces_design(check, example_project, db):
    from core.calculation import prepare_model, build_flow_context
    from core.air_properties import compute_air_state
    from config.settings import load_settings
    p = example_project
    a = p.air
    air = compute_air_state(a.mode, a.t_c, a.altitude_m, a.p_pa, a.rh)
    model = prepare_model(p, db)
    ctx = build_flow_context(p, air, db, load_settings(), "sucio")
    hq = {"H1": 0.67125, "H2": 0.39, "H3": 0.75, "H4": 0.38}
    # tol_ignore = 0: se balancea exactamente; con la tolerancia por defecto (5 %) los desbalances
    # pequeños se aceptan por criterio y la operación redistribuye ligeramente los caudales.
    d = solve_design(model, ctx, hq, strategy="dampers", tol_ignore=0.0)
    ctx2 = build_flow_context(p, air, db, load_settings(), "sucio")
    ctx2.extra_K = dict(d.damper_K)
    # ventilador ficticio que pasa exactamente por el punto de diseño
    Qd, Pd = d.state.Q_fan, d.state.FTP
    ftp = lambda Q, rho: Pd + 3000.0 * (Qd - Q)  # noqa: E731
    x0 = {h: d.state.node_mdot[h] for h in hq}
    r = solve_operating(model, ctx2, x0, fan_ftp=ftp)
    for h, qv in hq.items():
        check(f"Q {h} operación = diseño con compuertas", {"estrategia": "compuertas"}, qv, r.hood_q_final[h], 1e-5,
              reference="Consistencia diseño ↔ operación")


def test_topology_errors():
    m = _k_only_network(1, 1, 0.2, 0.2)
    m.nodes["O2"] = NetNode("O2", "outlet")
    assert m.validate()
    m2 = _k_only_network(1, 1, 0.2, 0.2)
    m2.segments.append(NetSegment("S5", "J", "A", "circular", 0.2))
    assert m2.validate()
    with pytest.raises(NetworkError):
        solve_design(m2, _ctx(), {"A": 0.5, "B": 0.5})
