"""Orquestador del cálculo completo de un proyecto.

Secuencia (PDF de arquitectura, sección 8, corregida):
1. Validar entradas → 2. Propiedades del aire → 3. Caudales generales →
4. Campanas (caudal requerido y pérdidas de entrada) → 5. Red: diseño balanceado,
camino crítico y presión requerida (filtro en estado de diseño y limpio) →
6. Curva del sistema → 7. Ventiladores: corrección por densidad/velocidad, punto de
operación, distribución real de caudales → 8. Potencia, motor y energía →
9. Herramienta de dimensionamiento → 10. Alertas, decisiones, dictamen y
recomendaciones constructivas.

Cada módulo se protege: un error en uno no detiene los demás; se registra como
alerta y el módulo queda con "información insuficiente".
"""
from __future__ import annotations

import copy
import datetime as _dt
import traceback
from dataclasses import dataclass, field

import numpy as np

from . import air_properties as AP
from .airflow import airflow_ach, airflow_dilution, airflow_thermal, airflow_occupancy, AirflowResult
from .duct_geometry import size_by_velocity, size_by_friction, size_static_regain, RegainSection
from .fan_curves import AdjustedFan, find_intersections, analyze_operating_point, speed_for_design_point, OperatingPoint
from .hood_design import hood_airflow, hood_entry_loss, HoodResult, HoodLossResult
from .network_solver import (NetworkModel, FlowContext, solve_design, solve_operating, system_curve, NetworkResult)
from .power import power_chain, part_load_comparison, PowerResult
from .project import Project, APP_VERSION
from .trace import Trace

from validation.alerts import Alert, sort_alerts, BASIS_PHYSICS
from validation import engineering_checks as EC
from validation.input_validation import validate_project_inputs
from validation.decision_engine import module_decision, build_dictamen, Decision, Dictamen
from validation.construction_recs import build_recommendations


@dataclass
class FanEval:
    fan_id: str
    adjusted: AdjustedFan | None
    op: OperatingPoint | None
    op_network: NetworkResult | None
    rpm_required: float | None
    error: str = ""
    op_clean: OperatingPoint | None = None


@dataclass
class ProjectResults:
    timestamp: str
    app_version: str
    air: AP.AirState | None = None
    airflow: dict[str, AirflowResult] = field(default_factory=dict)
    hoods: dict[str, HoodResult] = field(default_factory=dict)
    hood_losses: dict[str, HoodLossResult] = field(default_factory=dict)
    hood_q_required: dict[str, float] = field(default_factory=dict)
    model: NetworkModel | None = None
    network_design: NetworkResult | None = None
    network_clean: NetworkResult | None = None
    system_curve: list[tuple[float, float, float, bool]] = field(default_factory=list)
    system_curve_clean: list[tuple[float, float, float, bool]] = field(default_factory=list)
    fans: dict[str, FanEval] = field(default_factory=dict)
    selected_fan_id: str | None = None
    power: PowerResult | None = None
    part_load: tuple | None = None
    duct_tool: list = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    decisions: dict[str, Decision] = field(default_factory=dict)
    dictamen: Dictamen | None = None
    construction: list = field(default_factory=list)
    trace: Trace = field(default_factory=Trace)
    errors: dict[str, str] = field(default_factory=dict)
    settings: object = None

    @property
    def selected_fan(self) -> FanEval | None:
        return self.fans.get(self.selected_fan_id) if self.selected_fan_id else None


def _err(res: ProjectResults, module: str, exc: Exception) -> None:
    res.errors[module] = f"{exc}"
    res.alerts.append(Alert("CRÍTICO", module, "Error de cálculo", str(exc), basis=BASIS_PHYSICS,
                            recommendation="Revise los datos de entrada del módulo.",
                            source="Validación de dominio del motor de cálculo"))


def build_flow_context(project: Project, air: AP.AirState, db, settings, filter_state: str | None) -> FlowContext:
    return FlowContext(p_atm=air.p_pa, W=air.W, t_ambient=air.t_c, fittings_lib=db.fittings_lib(),
                       roughness_lib=db.roughness_lib(), friction_method=settings.solver("friction_method", "colebrook"),
                       filter_state=filter_state)


def prepare_model(project: Project, db) -> NetworkModel:
    """Copia de trabajo de la red con la entrada de cada campana inyectada en su primer tramo."""
    model = NetworkModel.from_dict(copy.deepcopy(project.network.to_dict()))
    entries = {e["id"]: e for e in db.hood_entries}
    for nd in model.nodes_of_kind("hood"):
        h = project.hood(nd.hood_id) if nd.hood_id else None
        seg = model.outgoing(nd.id)[0] if model.outgoing(nd.id) else None
        if seg is None or h is None:
            continue
        if seg.hood_entry is None:
            he = copy.deepcopy(h.entry)
            ent = entries.get(h.entry_id)
            if ent and ent.get("Fh") is not None and he.kind == "fh":
                he.Fh = float(ent["Fh"])
                he.source = ent.get("source", he.source)
            seg.hood_entry = he
    return model


def run_project(project: Project, db, settings, compute_fans: bool = True) -> ProjectResults:
    res = ProjectResults(_dt.datetime.now().isoformat(timespec="seconds"), APP_VERSION, settings=settings)
    res.alerts += validate_project_inputs(project)
    system = project.units

    # 2. Aire --------------------------------------------------------------
    try:
        a = project.air
        res.air = AP.compute_air_state(a.mode, a.t_c, a.altitude_m, a.p_pa, a.rh)
        res.trace.extend(res.air.trace)
        res.alerts += EC.check_air(a, res.air, settings)
    except Exception as exc:  # noqa: BLE001
        _err(res, "Propiedades del aire", exc)
    air = res.air

    # 3. Caudales generales -------------------------------------------------
    af = project.airflow
    try:
        if af.ach.get("enabled"):
            r = airflow_ach(af.ach.get("L", 0), af.ach.get("W", 0), af.ach.get("H", 0), af.ach.get("ACH", 0), af.ach.get("V"))
            res.airflow["ACH"] = r
        if af.dilution.get("enabled"):
            d = af.dilution
            V = (af.ach.get("L", 0) * af.ach.get("W", 0) * af.ach.get("H", 0)) or af.ach.get("V")
            r = airflow_dilution(d.get("G_mg_s", 0), d.get("C_target", 1), d.get("C_bg", 0), d.get("K", 1),
                                 d.get("capture_eff", 0), V, d.get("C0"))
            res.airflow["Dilución"] = r
        if af.thermal.get("enabled") and air is not None:
            t = af.thermal
            q = float(sum(t.get("sources_W", []) or [0]))
            air_in = AP.air_state_from_W(t.get("t_in", air.t_c), air.W, air.p_pa)
            res.airflow["Térmico"] = airflow_thermal(q, t.get("t_in", air.t_c), t.get("t_out", air.t_c + 5), air_in)
        if af.occupancy.get("enabled"):
            o = af.occupancy
            res.airflow["Ocupación"] = airflow_occupancy(o.get("Rp", 0), o.get("Pz", 0), o.get("Ra", 0), o.get("Az", 0),
                                                         o.get("Ez", 1))
        for r in res.airflow.values():
            res.trace.extend(r.trace)
    except Exception as exc:  # noqa: BLE001
        _err(res, "Caudales", exc)
    try:
        al, insuf_flow = EC.check_airflow(af, res.airflow, project.hoods, settings)
        res.alerts += al
    except Exception as exc:  # noqa: BLE001
        insuf_flow = True
        _err(res, "Caudales", exc)

    # 4. Campanas -----------------------------------------------------------
    limits = {"x_over_d_max": settings.cval("hood_x_over_d_max", 1.5),
              "slot_aspect_max": settings.cval("hood_slot_aspect_max", 0.2)}
    for h in project.hoods:
        try:
            hr = hood_airflow(h.id, h.type, h.params, limits)
            res.hoods[h.id] = hr
            res.trace.extend(hr.trace)
        except Exception as exc:  # noqa: BLE001
            _err(res, "Campanas", Exception(f"{h.id}: {exc}"))
    try:
        res.alerts += EC.check_hoods(project.hoods, res.hoods, db, settings)
    except Exception as exc:  # noqa: BLE001
        _err(res, "Campanas", exc)

    # 5. Red ------------------------------------------------------------------
    net_ok = False
    hood_class: dict[str, str] = {}
    if project.network.nodes and air is not None:
        try:
            model = prepare_model(project, db)
            res.model = model
            errs = model.validate()
            if errs:
                raise ValueError("Topología inválida: " + "; ".join(errs))
            hood_q = {}
            for nd in model.nodes_of_kind("hood"):
                h = project.hood(nd.hood_id) if nd.hood_id else None
                if h is not None:
                    hood_class[nd.id] = h.contaminant_class
                if nd.q_design:
                    hood_q[nd.id] = nd.q_design
                elif h is not None and h.id in res.hoods:
                    hood_q[nd.id] = res.hoods[h.id].Q
                else:
                    raise ValueError(f"La campana {nd.id} no tiene caudal (vincule una campana o indique Q)")
            res.hood_q_required = dict(hood_q)
            ns = project.network_settings
            ctx = build_flow_context(project, air, db, settings, ns.filter_state_design)
            series = db.diameter_series_mm(system)
            res.network_design = solve_design(
                model, ctx, hood_q, strategy=ns.strategy,
                tol_ignore=settings.cval("imbalance_ignore_pct", 5.0) / 100.0,
                tol_increase=settings.cval("imbalance_flow_increase_max_pct", 20.0) / 100.0,
                force_increase=settings.solver("force_flow_increase", False), diameter_series_mm=series)
            res.trace.extend(res.network_design.trace)
            # hood loss summary (SPh) a caudal final de diseño
            for nd in model.nodes_of_kind("hood"):
                seg = model.outgoing(nd.id)[0]
                if seg.hood_entry is not None:
                    ev = res.network_design.state.seg_evals[seg.id]
                    hl = hood_entry_loss(seg.hood_entry, ev.Q, ev.A, ev.rho, nd.id)
                    res.hood_losses[nd.id] = hl
                    res.trace.extend(hl.trace)
            ctx_clean = build_flow_context(project, air, db, settings, "limpio")
            ctx_clean.extra_K = dict(res.network_design.damper_K)
            res.network_clean = solve_design(model, ctx_clean, res.network_design.hood_q_final, strategy="none")
            net_ok = True
        except Exception as exc:  # noqa: BLE001
            _err(res, "Redes ramificadas", exc)
            res.errors["trace_net"] = traceback.format_exc()
        if net_ok:
            try:
                res.alerts += EC.check_network(project, res.model, res.network_design, db, settings, hood_class)
            except Exception as exc:  # noqa: BLE001
                _err(res, "Redes ramificadas", exc)

    # 6–7. Curva del sistema y ventiladores ---------------------------------
    if net_ok and compute_fans:
        try:
            nd_res = res.network_design
            model = res.model
            ctx = build_flow_context(project, air, db, settings, project.network_settings.filter_state_design)
            ctx.extra_K = dict(nd_res.damper_K)
            x0 = {h: nd_res.state.node_mdot[h] for h in nd_res.hood_q_final}
            Qd = nd_res.state.Q_fan
            q_lo, q_hi = 0.3 * Qd, 1.7 * Qd
            for f in project.fans:
                try:
                    af_ = AdjustedFan(f, rho=nd_res.state.rho_fan)
                    q_lo = min(q_lo, af_.q_min)
                    q_hi = max(q_hi, af_.q_max)
                except Exception:  # noqa: BLE001
                    pass
            npts = int(settings.solver("system_curve_points", 25))
            qs = list(np.linspace(max(q_lo, 0.05 * Qd), q_hi, npts))
            res.system_curve = system_curve(model, ctx, x0, qs)
            ctx_c = build_flow_context(project, air, db, settings, "limpio")
            ctx_c.extra_K = dict(nd_res.damper_K)
            res.system_curve_clean = system_curve(model, ctx_c, x0, qs)
            sel = project.fan_selection
            res.selected_fan_id = sel.selected_id or (project.fans[0].id if project.fans else None)
            for f in project.fans:
                fe = FanEval(f.id, None, None, None, None)
                res.fans[f.id] = fe
                try:
                    rpm = sel.rpm if (f.id == res.selected_fan_id and sel.rpm) else None
                    D = sel.diameter_m if (f.id == res.selected_fan_id and sel.diameter_m) else None
                    adj = AdjustedFan(f, rpm=rpm, rho=nd_res.state.rho_fan, diameter_m=D)
                    fe.adjusted = adj
                    sq = [p[0] for p in res.system_curve if p[3]]
                    sp = [p[1] for p in res.system_curve if p[3]]
                    inter = find_intersections(adj, sq, sp)
                    fe.rpm_required = speed_for_design_point(adj, Qd, nd_res.state.FTP)
                    if inter:
                        q_op = max(inter)
                        fan_ftp = (lambda Q, rho, _a=adj: _a.ftp(Q, rho))
                        opn = solve_operating(model, ctx, x0, fan_ftp=fan_ftp)
                        fe.op_network = opn
                        q_use = opn.state.Q_fan if opn.converged else q_op
                        fe.op = analyze_operating_point(
                            adj, q_use, inter, rho=opn.state.rho_fan, vp_out_fallback=opn.state.VP_fan_out,
                            stall_margin=settings.cval("fan_stall_margin_pct", 10) / 100.0,
                            eta_ratio_min=settings.cval("fan_eta_ratio_min", 0.9))
                        sqc = [p[0] for p in res.system_curve_clean if p[3]]
                        spc = [p[1] for p in res.system_curve_clean if p[3]]
                        ic = find_intersections(adj, sqc, spc)
                        if ic:
                            fe.op_clean = analyze_operating_point(adj, max(ic), ic)
                except Exception as exc:  # noqa: BLE001
                    fe.error = str(exc)
            res.alerts += EC.check_fan(res.fans, res.selected_fan_id, res.network_design,
                                       res.selected_fan.op_network if res.selected_fan else None, settings,
                                       res.hood_q_required)
        except Exception as exc:  # noqa: BLE001
            _err(res, "Selección de ventiladores", exc)
            res.errors["trace_fan"] = traceback.format_exc()

    # 8. Potencia ---------------------------------------------------------------
    if net_ok:
        try:
            pw = project.power
            fe = res.selected_fan
            ratings = db.motor_ratings_kw(pw.motor_standard)
            sel_W = pw.motor_selected_kw * 1000.0 if pw.motor_selected_kw else None
            eta_vfd = pw.eta_vfd if pw.use_vfd else 1.0
            if fe is not None and fe.op is not None:
                op = fe.op
                res.power = power_chain(op.Q, op.FTP, op.FSP, op.W_shaft, pw.eta_fan_user, pw.eta_basis, pw.eta_drive,
                                        pw.eta_motor, eta_vfd, pw.margin, pw.service_factor, ratings, pw.motor_standard,
                                        sel_W, pw.hours_per_year, pw.tariff)
            else:
                st = res.network_design.state
                res.power = power_chain(st.Q_fan, st.FTP, st.FSP, None, pw.eta_fan_user, pw.eta_basis, pw.eta_drive,
                                        pw.eta_motor, eta_vfd, pw.margin, pw.service_factor, ratings, pw.motor_standard,
                                        sel_W, pw.hours_per_year, pw.tariff)
            res.trace.extend(res.power.trace)
            overload = None
            if fe is not None and fe.adjusted is not None:
                cands = []
                if fe.op_clean and fe.op_clean.W_shaft:
                    cands.append(fe.op_clean.W_shaft / pw.eta_drive)
                if cands:
                    overload = max(cands)
                if fe.op is not None and pw.profile:
                    sq = [p[0] for p in res.system_curve if p[3]]
                    sp = [p[1] for p in res.system_curve if p[3]]
                    from scipy.interpolate import PchipInterpolator
                    sint = PchipInterpolator(sq, sp)
                    res.part_load = part_load_comparison(fe.adjusted, lambda q: float(sint(q)), fe.op.Q,
                                                         [(float(a), float(b) * pw.hours_per_year) for a, b in pw.profile],
                                                         pw.eta_drive, pw.eta_motor, pw.eta_vfd)
            hot_ratio = None
            temps = [nd.temperature_c for nd in res.model.nodes_of_kind("hood") if nd.temperature_c is not None]
            if temps and max(temps) > air.t_c + 20:
                hot_ratio = air.rho / res.network_design.state.rho_fan
            res.alerts += EC.check_power(pw, res.power, settings, overload, hot_ratio)
        except Exception as exc:  # noqa: BLE001
            _err(res, "Potencia y motores", exc)

    # 9. Herramienta de dimensionamiento ----------------------------------------
    if air is not None:
        try:
            dt = project.duct_tool
            eps = db.roughness_lib().get(dt.material_id, 0.09e-3)
            series = db.diameter_series_mm(system)
            if dt.method == "friction":
                res.duct_tool = [size_by_friction(dt.Q, dt.dp_per_m, air.rho, air.mu, eps, dt.shape, dt.aspect, series,
                                                  dt.rounding)]
            elif dt.method == "regain":
                secs = [RegainSection(float(q), float(L), float(k)) for q, L, k in dt.regain_sections]
                res.duct_tool = size_static_regain(dt.V_target, secs, dt.regain_R, air.rho, air.mu, eps, series,
                                                   dt.rounding)
            else:
                res.duct_tool = [size_by_velocity(dt.Q, dt.V_target, air.rho, air.mu, eps, dt.shape, dt.aspect, None,
                                                  series, dt.rounding)]
        except Exception as exc:  # noqa: BLE001
            _err(res, "Diseño de ductos", exc)

    # 10. Decisiones y dictamen -------------------------------------------------
    res.alerts = sort_alerts(res.alerts)
    try:
        _build_decisions(project, res, insuf_flow)
        res.dictamen = build_dictamen(project, res, res.decisions, res.alerts, db, system=system)
        res.construction = build_recommendations(project, res)
    except Exception as exc:  # noqa: BLE001
        res.errors["dictamen"] = f"{exc}"
        res.errors["trace_dict"] = traceback.format_exc()
    return res


def _build_decisions(project: Project, res: ProjectResults, insuf_flow: bool) -> None:
    from .units import fmt
    sysu = project.units
    D = res.decisions
    if res.air is not None:
        a = res.air
        D["Propiedades del aire"] = module_decision(
            "Propiedades del aire", res.alerts,
            [f"ρ = {fmt(a.rho, 'density', sysu)} (aire húmedo), μ = {a.mu:.4e} Pa·s, W = {a.W * 1000:.2f} g/kg, "
             f"t_rocío = {a.t_dew_c:.1f} °C"],
            ["Psicrometría ASHRAE Fundamentals cap. 1 (Hyland-Wexler, gas ideal); viscosidad por Sutherland."],
            system=sysu)
    else:
        D["Propiedades del aire"] = module_decision("Propiedades del aire", res.alerts, ["Sin resultado"], [], True,
                                                    ["Corregir las condiciones del aire."], sysu)
    if res.airflow or project.airflow.purpose == "contaminant_control":
        summ = [f"{k}: Q = {fmt(v.Q, 'flow', sysu)}" for k, v in res.airflow.items()]
        D["Caudales"] = module_decision("Caudales", res.alerts, summ or ["Sin métodos habilitados"],
                                        ["Métodos: ACH, dilución con factor K (ACGIH), balance sensible, ASHRAE 62.1."],
                                        insuf_flow and not res.hoods, system=sysu)
    if project.hoods:
        summ = [f"{hid}: Q = {fmt(r.Q, 'flow', sysu)} ({r.eq})" for hid, r in res.hoods.items()]
        D["Campanas"] = module_decision("Campanas", res.alerts, summ,
                                        ["Ecuaciones de DallaValle según geometría (ACGIH); pérdidas de entrada he = Fh·VPd."],
                                        system=sysu)
    nr = res.network_design
    if project.network.nodes:
        if nr is not None:
            st = nr.state
            vs = [abs(e.V) for e in st.seg_evals.values()]
            D["Diseño de ductos"] = module_decision(
                "Diseño de ductos", res.alerts,
                [f"Velocidades de ducto entre {min(vs):.1f} y {max(vs):.1f} m/s en {len(vs)} tramos."],
                ["Continuidad V = Q/A; velocidades mínimas de transporte ACGIH corregidas por densidad."], system=sysu)
            tb = nr.total_by_type()
            D["Pérdidas de presión"] = module_decision(
                "Pérdidas de presión", res.alerts,
                [f"Camino crítico: fricción {fmt(tb['Fricción'], 'pressure', sysu)}, locales "
                 f"{fmt(tb['Locales'], 'pressure', sysu)}, equipos {fmt(tb['Equipos'], 'pressure', sysu)}; "
                 f"FTP = {fmt(st.FTP, 'pressure', sysu)}."],
                ["Darcy-Weisbach con Colebrook-White; ΔP = K·ρV²/2 con sección de referencia; TP = SP + VP."], system=sysu)
            D["Redes ramificadas"] = module_decision(
                "Redes ramificadas", res.alerts,
                [f"Q ventilador {fmt(st.Q_fan, 'flow', sysu)}; campana gobernante {nr.governing_hood}; "
                 f"{len(nr.balance)} comparaciones de balance en uniones."],
                ["Balance de presión total en nodos, continuidad de masa, mezcla adiabática; equilibrado por diseño."],
                system=sysu)
        else:
            D["Redes ramificadas"] = module_decision("Redes ramificadas", res.alerts, ["La red no pudo calcularse."], [],
                                                     True, ["Completar/corregir la red."], sysu)
    if nr is not None:
        fe = res.selected_fan
        if fe is None or fe.adjusted is None:
            D["Selección de ventiladores"] = module_decision(
                "Selección de ventiladores", res.alerts,
                [f"Punto de diseño requerido: Q = {fmt(nr.state.Q_fan, 'flow', sysu)}, FTP = "
                 f"{fmt(nr.state.FTP, 'pressure', sysu)}."], [], True,
                ["Cargar curva(s) del fabricante con potencia o eficiencia."], sysu)
        else:
            summ = [f"Curva corregida a ρ = {fe.adjusted.rho:.3f} kg/m³, {fe.adjusted.rpm:.0f} rpm."]
            if fe.op is not None:
                summ.append(f"Operación: Q = {fmt(fe.op.Q, 'flow', sysu)}, FTP = {fmt(fe.op.FTP, 'pressure', sysu)}"
                            + (f", η_t = {fe.op.eta_total * 100:.1f} %" if fe.op.eta_total else "")
                            + (f", Q/Q_BEP = {fe.op.q_ratio_bep:.2f}" if fe.op.q_ratio_bep else ""))
            if fe.rpm_required:
                summ.append(f"Velocidad para pasar por el punto de diseño: {fe.rpm_required:.0f} rpm.")
            D["Selección de ventiladores"] = module_decision(
                "Selección de ventiladores", res.alerts, summ,
                ["Intersección curva del ventilador (PCHIP, leyes de semejanza) con la curva del sistema obtenida del "
                 "solucionador de red."], system=sysu)
    if res.power is not None:
        p = res.power
        D["Potencia y motores"] = module_decision(
            "Potencia y motores", res.alerts,
            [f"P_aire = {fmt(p.P_air_total, 'power', sysu)}, W_vent = {fmt(p.W_fan, 'power', sysu)}, W_motor = "
             f"{fmt(p.W_motor_out, 'power', sysu)}, P_elec = {fmt(p.P_elec, 'power', sysu)}; motor "
             f"{fmt(p.motor_nominal, 'power', sysu) if p.motor_nominal else '—'}."],
            [f"Cadena de potencias con eficiencias de ventilador ({p.W_fan_method}), transmisión y motor; margen único."],
            system=sysu)
