"""Tablas de resultados en unidades de presentación.

Fuente única para la interfaz, la memoria PDF y la exportación Excel: cada
función devuelve (encabezados, filas) ya convertidos al sistema SI o IP.
"""
from __future__ import annotations

from core.units import to_display, display_unit, format_number
from core.hood_design import HOOD_TYPES


def _v(x, q, system, digits=4):
    if x is None:
        return "—"
    try:
        return format_number(to_display(x, q, system), digits)
    except Exception:  # noqa: BLE001
        return str(x)


def _h(name, q, system):
    u = display_unit(q, system)
    return f"{name} [{u}]" if u and u != "-" else name


def air_table(air, system):
    if air is None:
        return [], []
    hdr = ["Propiedad", "Valor", "Unidad", "Modelo / fuente"]
    rows = [
        ["Temperatura de bulbo seco", _v(air.t_c, "temperature", system), display_unit("temperature", system), "Dato"],
        ["Temperatura absoluta", format_number(air.T_k, 5), "K", "T = t + 273.15"],
        ["Humedad relativa", f"{air.rh * 100:.1f}", "%", "Dato"],
        ["Presión atmosférica", _v(air.p_pa, "pressure", system), display_unit("pressure", system), air.pressure_source],
        ["Altitud", _v(air.altitude_m, "length", system) if air.altitude_m is not None else "—", display_unit("length", system), "Dato"],
        ["Presión de saturación pws", format_number(air.p_ws, 5), "Pa", "Hyland-Wexler (ASHRAE)"],
        ["Presión parcial de vapor pw", format_number(air.p_w, 5), "Pa", "pw = φ·pws"],
        ["Humedad absoluta W", _v(air.W, "humidity_ratio", system), display_unit("humidity_ratio", system), "ASHRAE ec. 20"],
        ["Punto de rocío", _v(air.t_dew_c, "temperature", system), display_unit("temperature", system), "Inversión de Hyland-Wexler"],
        ["Bulbo húmedo", _v(air.t_wb_c, "temperature", system), display_unit("temperature", system), "ASHRAE ec. 35/37"],
        ["Densidad del aire húmedo", _v(air.rho, "density", system), display_unit("density", system), "ρ = (1+W)/v"],
        ["Densidad del aire seco (misma T, p)", _v(air.rho_dry, "density", system), display_unit("density", system), "Gas ideal"],
        ["Volumen específico", _v(air.v_m3_kg, "spec_volume", system), display_unit("spec_volume", system) + " a.s.", "ASHRAE ec. 26"],
        ["Entalpía", _v(air.h_kj_kg, "enthalpy", system), display_unit("enthalpy", system) + " a.s.", "ASHRAE ec. 32"],
        ["Calor específico (por kg a.s.)", _v(air.cp_da, "cp", system), display_unit("cp", system), "1.006 + 1.86·W"],
        ["Viscosidad dinámica", format_number(air.mu, 5), "Pa·s", "Sutherland"],
        ["Viscosidad cinemática", _v(air.nu, "kin_viscosity", system), display_unit("kin_viscosity", system), "ν = μ/ρ"],
    ]
    return hdr, rows


def airflow_table(results, system):
    hdr = ["Método", _h("Caudal", "flow", system), "Notas"]
    rows = []
    for k, r in results.airflow.items():
        rows.append([k, _v(r.Q, "flow", system), " ".join(r.notes[:1])])
    return hdr, rows


def hoods_table(project, results, system):
    hdr = ["Campana", "Nombre", "Tipo", "Ecuación", _h("Q requerido", "flow", system), _h("Vel. de cara", "velocity", system),
           "Fh entrada", _h("SPh", "pressure", system), "Ce efectivo", "Clase de contaminante"]
    rows = []
    node_of = {}
    if results.model is not None:
        node_of = {nd.hood_id: nd.id for nd in results.model.nodes_of_kind("hood") if nd.hood_id}
    for h in project.hoods:
        r = results.hoods.get(h.id)
        hl = results.hood_losses.get(node_of.get(h.id, ""))
        rows.append([h.id, h.name, HOOD_TYPES.get(h.type, {}).get("label", h.type), r.eq if r else "—",
                     _v(r.Q, "flow", system) if r else "—", _v(r.V_face, "velocity", system) if r and r.V_face else "—",
                     f"{h.entry.Fh:.2f}" + (f" + ranura {h.entry.Fs:.2f}" if h.entry.kind == "slot" else ""),
                     _v(hl.SPh, "pressure", system) if hl else "—", f"{hl.Ce_effective:.3f}" if hl else "—",
                     h.contaminant_class])
    return hdr, rows


def segments_geometry_table(results, db, system):
    model = results.model
    if model is None:
        return [], []
    hdr = ["Tramo", "De → A", "Sección", _h("D / a×b", "small_length", system), _h("L", "length", system), "Material",
           _h("ε", "roughness", system), _h("Área", "area", system), _h("Dh", "small_length", system)]
    rows = []
    for s in model.segments:
        g = s.geometry
        if s.shape == "circular":
            dim = _v(s.D, "small_length", system)
        else:
            dim = f"{_v(s.a, 'small_length', system)} × {_v(s.b, 'small_length', system)}"
        mat = db.material(s.material_id)
        eps = s.roughness_m if s.roughness_m is not None else (mat["roughness_mm"] / 1000 if mat else None)
        rows.append([s.id, f"{s.from_node} → {s.to_node}", s.shape, dim, _v(s.length, "length", system),
                     mat["name"] if mat else s.material_id, _v(eps, "roughness", system, 3), _v(g.area, "area", system),
                     _v(g.Dh, "small_length", system)])
    return hdr, rows


def segments_flow_table(results, system):
    nr = results.network_design
    if nr is None:
        return [], []
    hdr = ["Tramo", _h("Q", "flow", system), _h("T", "temperature", system), _h("ρ", "density", system),
           _h("V", "velocity", system), _h("VP", "pressure", system), "Re", "ε/Dh", "f Darcy", "Régimen",
           _h("ΔP fricción", "pressure", system), _h("ΔP locales", "pressure", system), _h("ΔP entrada", "pressure", system),
           _h("ΔP equipos", "pressure", system), _h("ΔP descarga", "pressure", system), _h("ΔP total", "pressure", system),
           _h("TP inicio", "pressure", system), _h("TP fin", "pressure", system), _h("SP inicio", "pressure", system),
           _h("SP fin", "pressure", system)]
    rows = []
    for sid, ev in nr.state.seg_evals.items():
        rows.append([sid, _v(abs(ev.Q), "flow", system), _v(ev.t_c, "temperature", system), _v(ev.rho, "density", system),
                     _v(abs(ev.V), "velocity", system), _v(ev.VP, "pressure", system), f"{ev.Re:,.0f}",
                     f"{ev.rel_rough:.2e}", f"{ev.f:.5f}", ev.regime, _v(ev.dp_friction, "pressure", system),
                     _v(ev.dp_fittings + ev.dp_damper, "pressure", system), _v(ev.dp_entry, "pressure", system),
                     _v(ev.dp_equipment, "pressure", system), _v(ev.dp_exit, "pressure", system),
                     _v(ev.dp_total, "pressure", system), _v(ev.TP_start, "pressure", system),
                     _v(ev.TP_end, "pressure", system), _v(ev.SP_start, "pressure", system), _v(ev.SP_end, "pressure", system)])
    return hdr, rows


def fittings_table(results, system):
    nr = results.network_design
    if nr is None:
        return [], []
    hdr = ["Tramo", "Accesorio", "Cant.", "K", _h("A ref", "area", system), _h("V ref", "velocity", system),
           _h("ΔP", "pressure", system), "Fuente", "Estado"]
    rows = []
    for sid, ev in nr.state.seg_evals.items():
        for fe in ev.fittings:
            rows.append([sid, fe.name, f"{fe.qty:g}", f"{fe.K:.4f}", _v(fe.area_ref, "area", system),
                         _v(fe.V_ref, "velocity", system), _v(fe.dp, "pressure", system), fe.source, fe.status])
        if ev.dp_entry:
            rows.append([sid, "Entrada de campana", "1", "Fh (ver campanas)", "—", _v(abs(ev.V), "velocity", system),
                         _v(ev.dp_entry, "pressure", system), "ACGIH (coeficientes de entrada)", "verificar"])
        if ev.dp_damper:
            rows.append([sid, "Compuerta de balance", "1", f"{ev.dp_damper / ev.VP:.3f}" if ev.VP else "—", "—",
                         _v(abs(ev.V), "velocity", system), _v(ev.dp_damper, "pressure", system), "Balance de diseño", "ajuste en campo"])
        if ev.dp_exit:
            rows.append([sid, "Descarga a la atmósfera", "1", f"{ev.dp_exit / ev.VP:.2f}" if ev.VP else "—", "—",
                         _v(abs(ev.V), "velocity", system), _v(ev.dp_exit, "pressure", system), "Energía cinética no recuperada",
                         "fórmula verificable"])
    return hdr, rows


def equipment_table(results, project, system):
    nr = results.network_design
    if nr is None:
        return [], []
    hdr = ["Tramo", "Equipo", "Tipo", "Modelo de pérdida", _h("Q", "flow", system), _h("ΔP diseño", "pressure", system),
           _h("ΔP filtro limpio", "pressure", system), "Fuente"]
    rows = []
    clean = results.network_clean
    for s in results.model.segments:
        ev = nr.state.seg_evals[s.id]
        for i, e in enumerate(s.equipment):
            dpc = None
            if clean is not None:
                dpc = clean.state.seg_evals[s.id].equipment[i][2]
            rows.append([s.id, e.name, e.eq_type, e.model, _v(abs(ev.Q), "flow", system), _v(ev.equipment[i][2], "pressure", system),
                         _v(dpc, "pressure", system), e.source])
    return hdr, rows


def balance_table(results, system):
    nr = results.network_design
    if nr is None:
        return [], []
    hdr = ["Unión", "Ramal gobernante", "Ramal", _h("TP gobernante", "pressure", system), _h("TP ramal", "pressure", system),
           "Relación r", "Acción", _h("Q antes", "flow", system), _h("Q después", "flow", system), "Escala exacta",
           "Aprox. √r", "K compuerta req."]
    rows = []
    for b in nr.balance:
        rows.append([b.junction, b.governing_segment, b.segment, _v(b.tp_gov, "pressure", system),
                     _v(b.tp_branch, "pressure", system), f"{b.ratio:.3f}", b.action, _v(b.Q_before, "flow", system),
                     _v(b.Q_after, "flow", system), f"{b.scale:.4f}", f"{b.scale_sqrt_approx:.4f}",
                     f"{b.damper_K_required:.3f}" if b.damper_K_required is not None else "—"])
    return hdr, rows


def hood_flows_table(results, system):
    hdr = ["Campana (nodo)", _h("Q requerido", "flow", system), _h("Q diseño balanceado", "flow", system),
           _h("Q en operación", "flow", system), "Cumplimiento"]
    rows = []
    nr = results.network_design
    fe = results.selected_fan
    for h, q in results.hood_q_required.items():
        qd = nr.hood_q_final.get(h) if nr else None
        qo = fe.op_network.hood_q_final.get(h) if fe and fe.op_network else None
        ok = "—" if qo is None else (f"{qo / q * 100:.0f} %")
        rows.append([h, _v(q, "flow", system), _v(qd, "flow", system), _v(qo, "flow", system), ok])
    return hdr, rows


def fans_table(results, system):
    hdr = ["Ventilador", "Tipo", "rpm", _h("ρ curva", "density", system), _h("Q operación", "flow", system),
           _h("FTP", "pressure", system), _h("FSP", "pressure", system), "η total", _h("Potencia eje", "power", system),
           _h("Q BEP", "flow", system), "Q/Q_BEP", "rpm para punto de diseño", "Estado"]
    rows = []
    for fid, fe in results.fans.items():
        if fe.adjusted is None:
            rows.append([fid, "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", "—", fe.error or "sin datos"])
            continue
        c = fe.adjusted.curve
        op = fe.op
        rows.append([f"{c.model or fid}", c.fan_type, f"{fe.adjusted.rpm:.0f}", _v(fe.adjusted.rho, "density", system),
                     _v(op.Q, "flow", system) if op else "sin intersección", _v(op.FTP, "pressure", system) if op else "—",
                     _v(op.FSP, "pressure", system) if op else "—",
                     f"{op.eta_total * 100:.1f} %" if op and op.eta_total else "—",
                     _v(op.W_shaft, "power", system) if op and op.W_shaft else "—",
                     _v(op.q_bep, "flow", system) if op and op.q_bep else "—",
                     f"{op.q_ratio_bep:.2f}" if op and op.q_ratio_bep else "—",
                     f"{fe.rpm_required:.0f}" if fe.rpm_required else "—",
                     ("seleccionado" if fid == results.selected_fan_id else "")
                     + (" · curva certificada" if c.certified else " · curva no certificada")])
    return hdr, rows


def power_table(results, project, system):
    p = results.power
    if p is None:
        why = getattr(results, "power_blocked", "")
        if why:
            return (["Concepto", "Valor", "Unidad", "Ecuación / criterio"],
                    [["Selección de motor", "BLOQUEADA", "—", why]])
        return [], []
    hdr = ["Concepto", "Valor", "Unidad", "Ecuación / criterio"]
    pu = display_unit("power", system)
    rows = [
        ["Caudal en el ventilador", _v(p.Q, "flow", system), display_unit("flow", system), "Punto de operación"],
        ["Presión total FTP", _v(p.FTP, "pressure", system), display_unit("pressure", system), "Punto de operación"],
        ["Presión estática FSP", _v(p.FSP, "pressure", system), display_unit("pressure", system), "FSP = FTP − VP_salida"],
        ["Potencia aerodinámica (total)", _v(p.P_air_total, "power", system), pu, "P = Q·FTP"],
        ["Potencia aerodinámica (estática)", _v(p.P_air_static, "power", system), pu, "P = Q·FSP (informativa)"],
        ["Potencia absorbida por el ventilador", _v(p.W_fan, "power", system), pu, p.W_fan_method],
        ["Eficiencia total del ventilador", f"{p.eta_total * 100:.1f}" if p.eta_total else "—", "%", "η_t = Q·FTP/W"],
        ["Eficiencia estática del ventilador", f"{p.eta_static * 100:.1f}" if p.eta_static else "—", "%", "η_s = Q·FSP/W"],
        ["Eficiencia de transmisión", f"{p.eta_drive * 100:.1f}", "%", project.power.drive_type],
        ["Potencia en el eje del motor", _v(p.W_motor_out, "power", system), pu, "W_motor = W_vent/η_tr"],
        ["Eficiencia del motor", f"{p.eta_motor * 100:.1f}", "%", "Dato de placa / IEC 60034-30-1"],
        ["Eficiencia del variador", f"{p.eta_vfd * 100:.1f}", "%", "1.0 si no hay variador"],
        ["Potencia eléctrica de entrada", _v(p.P_elec, "power", system), pu, "P_elec = W_motor/(η_m·η_vfd)"],
        ["Margen de selección (una vez)", f"{p.margin * 100:.0f}", "%", "Criterio del proyecto"],
        ["Potencia mínima del motor", _v(p.W_motor_required, "power", system), pu, "W_motor·(1 + margen)"],
        [f"Motor normalizado ({p.motor_standard})", _v(p.motor_nominal, "power", system), pu, "Serie normalizada"],
        ["Motor seleccionado por el usuario", _v(p.motor_selected, "power", system), pu, "—"],
        ["Carga del motor", f"{p.motor_load_fraction * 100:.0f}" if p.motor_load_fraction else "—", "%", "W_motor/P_nom"],
        ["Factor de servicio (informativo)", f"{p.service_factor:.2f}", "-", "No se usa como margen"],
        ["Horas de operación anual", f"{p.hours:,.0f}", "h/año", "Dato"],
        ["Energía anual", f"{p.energy_kwh:,.0f}", "kWh/año", "E = P_elec·t"],
        ["Costo energético anual", f"{p.cost:,.0f}", f"{project.power.currency}/año", f"tarifa {p.tariff} por kWh"],
    ]
    return hdr, rows


def part_load_table(results, system):
    if not results.part_load:
        return [], []
    rows_pl, summ = results.part_load
    pu = display_unit("power", system)
    hdr = ["Fracción de caudal", "Horas/año", _h("Q", "flow", system), f"P eléctrica compuerta [{pu}]",
           f"P eléctrica variador [{pu}]", "Velocidad relativa"]
    rows = [[f"{r.fraction * 100:.0f} %", f"{r.hours:,.0f}", _v(r.Q, "flow", system), _v(r.P_elec_damper, "power", system),
             _v(r.P_elec_vfd, "power", system), f"{r.speed_ratio:.3f}" if r.speed_ratio else "—"] for r in rows_pl]
    rows.append(["Energía anual", "", "", f"{summ['E_damper_kwh']:,.0f} kWh", f"{summ['E_vfd_kwh']:,.0f} kWh",
                 f"ahorro {summ['saving_kwh']:,.0f} kWh"])
    return hdr, rows


def alerts_table(results, system):
    hdr = ["Nivel", "Módulo", "Parámetro", "Elemento", "Qué se detectó", "Valor", "Criterio", "Consecuencia potencial",
           "Recomendación", "Fuente / base"]
    rows = []
    for a in results.alerts:
        rows.append([a.level, a.module, a.parameter, a.item, a.detected, a.value_str(system), a.criterion, a.consequence,
                     a.recommendation, f"{a.source} ({a.basis})" if a.source else a.basis])
    return hdr, rows


def comparison_table(metrics, project, system):
    hdr = ["Alternativa", "Elegible", _h("Q suministrado", "flow", system), "Déficit máx.", _h("V mín", "velocity", system),
           _h("V máx", "velocity", system), "Base de V", _h("FTP", "pressure", system), _h("FSP", "pressure", system),
           _h("Potencia eje", "power", system), _h("Potencia eléctrica", "power", system), "η vent.", "Energía kWh/año",
           f"Costo {project.power.currency}/año", "Complejidad (1–5)", "Mantenimiento (1–5)", "Riesgo técnico",
           "Puntuación", "Motivo de exclusión"]
    rows = []
    for m in metrics:
        rows.append([m.name, "Sí" if m.eligible else "No", _v(m.Q_fan, "flow", system), f"{m.deficit_max_pct:.1f} %",
                     _v(m.v_min, "velocity", system), _v(m.v_max, "velocity", system),
                     "Operación real" if getattr(m, "v_basis", "diseño") == "operación" else "Diseño",
                     _v(m.FTP, "pressure", system),
                     _v(m.FSP, "pressure", system), _v(m.W_shaft, "power", system), _v(m.P_elec, "power", system),
                     f"{m.eta * 100:.1f} %" if m.eta else "—", f"{m.energy_kwh:,.0f}" if m.energy_kwh else "—",
                     f"{m.cost:,.0f}" if m.cost else "—", str(m.complexity), str(m.maintenance),
                     f"{m.risk} ({m.n_alto} altas, {m.n_medio} medias)", f"{m.score:.0f}", "; ".join(m.exclusion)])
    return hdr, rows
