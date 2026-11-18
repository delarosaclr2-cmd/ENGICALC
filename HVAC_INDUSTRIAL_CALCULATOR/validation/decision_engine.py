"""Motor de decisión técnica y dictamen de ingeniería.

Para cada módulo se emite: A. Diagnóstico, B. Decisión, C. Justificación y
D. Acción recomendada. La decisión se deriva de las alertas (con sus criterios y
fuentes) y de la suficiencia de información; nunca se fuerza una conclusión
positiva si los resultados no la justifican.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .alerts import Alert, LEVEL_RANK, sort_alerts, count_by_level

DEC_OK = "Diseño técnicamente aceptable bajo las hipótesis indicadas"
DEC_OBS = "Diseño aceptable con observaciones"
DEC_MOD = "Diseño que requiere modificaciones"
DEC_NO = "Diseño no recomendable en las condiciones evaluadas"
DEC_INSUF = "Información insuficiente para emitir una conclusión"

DEC_CODES = {"ok": DEC_OK, "obs": DEC_OBS, "mod": DEC_MOD, "no": DEC_NO, "insuf": DEC_INSUF}
DEC_COLORS = {"ok": "#2B7A4B", "obs": "#2F6FB0", "mod": "#D9480F", "no": "#B42318", "insuf": "#5B6577"}


@dataclass
class Decision:
    module: str
    code: str
    diagnosis: list[str] = field(default_factory=list)
    satisfactory: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    justification: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)
    viable: str = ""

    @property
    def decision(self) -> str:
        return DEC_CODES[self.code]

    @property
    def color(self) -> str:
        return DEC_COLORS[self.code]


def module_decision(module: str, alerts: list[Alert], summary: list[str], basis: list[str],
                    insufficient: bool = False, missing: list[str] | None = None, system: str = "SI") -> Decision:
    al = sort_alerts([a for a in alerts if a.module == module])
    cnt = count_by_level(al)
    if cnt["CRÍTICO"]:
        code = "no"
    elif insufficient:
        code = "insuf"
    elif cnt["ALTO"]:
        code = "mod"
    elif cnt["MEDIO"] or cnt["BAJO"]:
        code = "obs"
    else:
        code = "ok"
    d = Decision(module, code)
    d.diagnosis = list(summary)
    d.satisfactory = [f"{a.parameter}: {a.detected}" + (f" ({a.value_str(system)})" if a.value is not None else "")
                      for a in al if a.level == "CORRECTO"]
    d.problems = [f"[{a.level}] {a.parameter}" + (f" — {a.item}" if a.item else "") + f": {a.detected}"
                  + (f" (valor: {a.value_str(system)}; criterio: {a.criterion})" if a.criterion else "")
                  for a in al if a.level in ("CRÍTICO", "ALTO", "MEDIO", "BAJO")]
    d.justification = list(basis)
    crit_src = sorted({f"{a.parameter}: {a.source}" for a in al if a.source and a.level in ("CRÍTICO", "ALTO", "MEDIO")})
    d.justification += [f"Criterio — {s}" for s in crit_src]
    acts, seen = [], set()
    for a in al:
        if a.level in ("CRÍTICO", "ALTO", "MEDIO", "BAJO") and a.recommendation and a.recommendation not in seen:
            seen.add(a.recommendation)
            acts.append(f"[{a.level}] {a.recommendation}")
    if missing:
        acts += [f"[DATOS] {m}" for m in missing]
    if not acts:
        acts.append("Sin acciones correctivas; conservar las hipótesis documentadas y validar en campo.")
    d.actions = acts
    d.viable = {"ok": "Sí, bajo las hipótesis indicadas.", "obs": "Sí, con las observaciones señaladas.",
                "mod": "No en su forma actual; requiere las modificaciones indicadas.",
                "no": "No: existen condiciones físicamente inválidas o inseguras.",
                "insuf": "No se puede determinar con la información disponible."}[code]
    return d


def global_decision(decisions: dict[str, Decision], essential: tuple[str, ...]) -> str:
    codes = {m: d.code for m, d in decisions.items()}
    if any(c == "no" for c in codes.values()):
        return "no"
    if any(c == "mod" for c in codes.values()):
        return "mod"
    if any(codes.get(m) == "insuf" for m in essential) or not any(m in codes for m in essential):
        return "insuf"
    if any(c in ("obs", "insuf") for c in codes.values()):
        return "obs"
    return "ok"


@dataclass
class Dictamen:
    description: list[str]
    objective: list[str]
    inputs: list[str]
    results: list[str]
    evaluation: list[str]
    problems: list[str]
    decision_code: str
    modifications: list[str]
    alternatives: list[str]
    pending: list[str]
    references: list[str]
    limitations: list[str]

    @property
    def decision(self) -> str:
        return DEC_CODES[self.decision_code]


LIMITATIONS = [
    "El dictamen se basa en modelos de ingeniería (mezcla perfecta, ecuaciones empíricas de captura, coeficientes de "
    "pérdida de literatura y curvas de fabricante) y en los datos ingresados; no sustituye la revisión de un ingeniero "
    "responsable ni de especialistas competentes.",
    "No constituye certificación de cumplimiento normativo: solo se evaluaron los criterios listados con su fuente.",
    "Los coeficientes marcados 'verificar' y los criterios marcados 'hipótesis del proyecto' deben confirmarse con la "
    "edición vigente de la referencia o con la especificación del proyecto.",
    "La red se resuelve como árbol convergente de extracción con un ventilador; no se modelan fugas, efecto del sistema "
    "del ventilador (AMCA 201) cuantitativo, compresibilidad ni transferencia de calor en los ductos.",
    "El diseño estructural de soportes, el diseño eléctrico, la protección contra explosiones de polvo combustible y la "
    "evaluación ambiental de emisiones requieren especialistas.",
    "Los resultados deben validarse con mediciones de campo (caudales, presiones estáticas de campana, rpm y potencia) "
    "durante la puesta en marcha.",
]


def build_dictamen(project, results, decisions: dict[str, Decision], alerts: list[Alert], db,
                   comparison_text: list[str] | None = None, system: str = "SI") -> Dictamen:
    from core.units import fmt
    p = project
    nr = results.network_design
    desc = [f"Proyecto: {p.info.name}" + (f" — Cliente: {p.info.client}" if p.info.client else ""),
            f"Tipo de ventilación: {p.info.ventilation_type}. Ubicación: {p.info.location or 'no indicada'}."]
    if p.info.description:
        desc.append(p.info.description)
    if nr is not None:
        model = results.model
        desc.append(f"Red de extracción con {len(model.nodes_of_kind('hood'))} campanas, {len(model.segments)} tramos, "
                    "un ventilador y una descarga a la atmósfera.")
    obj = [p.info.objective or "Capturar los contaminantes en su origen con la velocidad de captura requerida, "
           "transportarlos sin sedimentación hasta el equipo de control y descargarlos de forma segura, con el menor "
           "consumo energético compatible con la seguridad."]
    a = results.air
    inputs = []
    if a is not None:
        inputs.append(f"Aire: t = {a.t_c:.1f} °C, HR = {a.rh * 100:.0f} %, p = {fmt(a.p_pa, 'pressure', system)}"
                      + (f", altitud {a.altitude_m:.0f} m" if a.altitude_m is not None else "")
                      + f" → ρ = {fmt(a.rho, 'density', system)}, μ = {a.mu:.3e} Pa·s.")
    for h in p.hoods:
        hr = results.hoods.get(h.id)
        if hr:
            inputs.append(f"Campana {h.id} ({h.name}): {hr.eq}; Q requerido = {fmt(hr.Q, 'flow', system)}.")
    inputs.append(f"Estrategia de balance: {p.network_settings.strategy}; filtro evaluado en estado "
                  f"'{p.network_settings.filter_state_design}'. Factor de fricción: Colebrook-White.")
    inputs.append(f"Motor: margen de selección {p.power.margin * 100:.0f} % (aplicado una vez); transmisión "
                  f"{p.power.drive_type} η = {p.power.eta_drive:.3f}; η_motor = {p.power.eta_motor:.3f}.")
    res = []
    if nr is not None:
        st = nr.state
        res += [f"Caudal en el ventilador (diseño balanceado): {fmt(st.Q_fan, 'flow', system)} a {st.t_fan:.1f} °C.",
                f"Presión total requerida FTP = {fmt(st.FTP, 'pressure', system)}; presión estática FSP = "
                f"{fmt(st.FSP, 'pressure', system)}.",
                f"Camino crítico: {' → '.join(nr.critical_path)} (campana gobernante {nr.governing_hood})."]
        tb = nr.total_by_type()
        res.append(f"Pérdidas del camino crítico: fricción {fmt(tb['Fricción'], 'pressure', system)}, locales "
                   f"{fmt(tb['Locales'], 'pressure', system)}, equipos {fmt(tb['Equipos'], 'pressure', system)}.")
    fe = results.selected_fan
    if fe is not None and fe.op is not None:
        op = fe.op
        res.append(f"Punto de operación ({fe.adjusted.curve.model or fe.adjusted.curve.id}, {fe.adjusted.rpm:.0f} rpm): "
                   f"Q = {fmt(op.Q, 'flow', system)}, FTP = {fmt(op.FTP, 'pressure', system)}"
                   + (f", η_t = {op.eta_total * 100:.1f} %" if op.eta_total else "") + ".")
    pw = results.power
    if pw is not None:
        res.append(f"Potencia: aire {fmt(pw.P_air_total, 'power', system)}, ventilador {fmt(pw.W_fan, 'power', system)}, "
                   f"eje motor {fmt(pw.W_motor_out, 'power', system)}, eléctrica {fmt(pw.P_elec, 'power', system)}; "
                   f"motor normalizado {fmt(pw.motor_nominal, 'power', system) if pw.motor_nominal else '—'}.")
        if pw.hours:
            res.append(f"Energía anual {pw.energy_kwh:,.0f} kWh; costo {pw.cost:,.0f} {p.power.currency}/año.")
    evaluation = [f"{m}: {d.decision}" for m, d in decisions.items()]
    problems = [f"[{x.level}] {x.module} — {x.parameter}" + (f" ({x.item})" if x.item else "") + f": {x.detected}"
                for x in sort_alerts(alerts) if x.level in ("CRÍTICO", "ALTO", "MEDIO")]
    code = global_decision(decisions, ("Redes ramificadas", "Selección de ventiladores", "Potencia y motores"))
    mods, seen = [], set()
    for x in sort_alerts(alerts):
        if x.level in ("CRÍTICO", "ALTO", "MEDIO") and x.recommendation and x.recommendation not in seen:
            seen.add(x.recommendation)
            mods.append(f"[{x.level}] {x.recommendation}" + (f" ({x.item})" if x.item else ""))
    alts = list(comparison_text or [])
    if pw is not None and not p.power.use_vfd:
        alts.append("Evaluar variador de frecuencia: permite ajustar el caudal en la puesta en marcha y compensar el "
                    "ensuciamiento del filtro sin estrangular (ver análisis de carga parcial).")
    if any(x.parameter == "Ramal desbalanceado" for x in alerts):
        alts.append("Rediseñar los ramales desbalanceados (diámetros) frente a compuertas de balance: comparar presión "
                    "del ventilador y consumo.")
    alts.append("Comparar al menos tres configuraciones (diámetros/velocidad de diseño y ventiladores) con el "
                "comparador de alternativas.")
    pending = [f"{x.parameter}: {x.detected}" + (f" ({x.item})" if x.item else "") for x in alerts
               if x.basis == "datos faltantes" or (x.level == "INFO" and "verificar" in (x.parameter + x.detected).lower())]
    pending = list(dict.fromkeys(pending))
    pending += ["Curva certificada del ventilador a la densidad de operación y datos de ruido.",
                "Pérdidas de presión del colector/filtro (limpio y en condición de mantenimiento) del fabricante.",
                "Confirmación de coeficientes K de accesorios marcados 'verificar' con la edición vigente de la fuente.",
                "Levantamiento de interferencias, rutas y soportería (ingeniería de detalle)."]
    refs = [r["title"] for r in db.references if r["id"] in
            ("ACGIH", "ASHRAE_F", "ASHRAE_SE", "ASHRAE_APP", "AMCA210", "AMCA99", "AMCA201", "AMCA203", "SMACNA_DD",
             "SMACNA_DCS", "Idelchik", "Crane", "White", "Colebrook", "HylandWexler", "IEC60072", "NOM010")]
    return Dictamen(desc, obj, inputs, res, evaluation, problems, code, mods, alts, pending, refs, list(LIMITATIONS))
