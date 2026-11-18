"""Comparador de alternativas de diseño (mínimo tres).

Procedimiento (no se elige automáticamente la más barata ni la de menor presión):
1. Filtro de elegibilidad: se excluyen las alternativas con alertas CRÍTICAS, con
   déficit de caudal en alguna campana mayor que la tolerancia o con velocidades de
   transporte insuficientes (riesgo de sedimentación).
2. Puntuación multicriterio de las elegibles (0–100) con pesos configurables:
   energía, desempeño (margen de caudal y eficiencia), riesgo técnico (alertas ALTO/
   MEDIO), complejidad de instalación y facilidad de mantenimiento.
3. Conclusión razonada que explica por qué se recomienda la alternativa y qué se
   sacrifica frente a las demás.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .alerts import count_by_level, worst_level


@dataclass
class AltMetrics:
    name: str
    eligible: bool
    exclusion: list[str]
    Q_fan: float | None
    Q_required: float | None
    deficit_max_pct: float
    v_min: float | None
    v_max: float | None
    transport_ok: bool
    FTP: float | None
    FSP: float | None
    loss_total: float | None
    W_shaft: float | None
    P_elec: float | None
    eta: float | None
    energy_kwh: float | None
    cost: float | None
    complexity: int
    maintenance: int
    risk: str
    n_crit: int
    n_alto: int
    n_medio: int
    decision: str
    score: float = 0.0
    notes: str = ""


def metrics_from_results(name, project, results, complexity: int, maintenance: int, notes: str = "") -> AltMetrics:
    alerts = results.alerts
    cnt = count_by_level(alerts)
    nr = results.network_design
    op_net = results.selected_fan.op_network if results.selected_fan else None
    q_req = sum(results.hood_q_required.values()) if results.hood_q_required else None
    deficit = 0.0
    if op_net is not None:
        for h, qr in results.hood_q_required.items():
            q = op_net.hood_q_final.get(h, qr)
            deficit = max(deficit, (qr - q) / qr * 100)
    vs = [abs(ev.V) for ev in nr.state.seg_evals.values()] if nr else []
    transport_ok = not any(a.parameter == "Velocidad de transporte" for a in alerts)
    pw = results.power
    op = results.selected_fan.op if results.selected_fan else None
    excl = []
    if cnt["CRÍTICO"]:
        excl.append(f"{cnt['CRÍTICO']} alerta(s) CRÍTICA(s)")
    tol = results.settings.cval("flow_deficit_tolerance_pct", 5.0) if results.settings else 5.0
    if deficit > tol:
        excl.append(f"déficit de caudal {deficit:.1f} % > {tol:.0f} %")
    if not transport_ok:
        excl.append("velocidad de transporte insuficiente (riesgo de sedimentación)")
    if nr is None:
        excl.append("red no calculada")
    return AltMetrics(
        name=name, eligible=not excl, exclusion=excl,
        Q_fan=op.Q if op else (nr.state.Q_fan if nr else None), Q_required=q_req, deficit_max_pct=max(deficit, 0.0),
        v_min=min(vs) if vs else None, v_max=max(vs) if vs else None, transport_ok=transport_ok,
        FTP=op.FTP if op else (nr.state.FTP if nr else None), FSP=op.FSP if op else (nr.state.FSP if nr else None),
        loss_total=nr.state.FTP if nr else None, W_shaft=pw.W_fan if pw else None, P_elec=pw.P_elec if pw else None,
        eta=pw.eta_total if pw else None, energy_kwh=pw.energy_kwh if pw else None, cost=pw.cost if pw else None,
        complexity=complexity, maintenance=maintenance, risk=worst_level([a for a in alerts if a.level != "CORRECTO"]),
        n_crit=cnt["CRÍTICO"], n_alto=cnt["ALTO"], n_medio=cnt["MEDIO"],
        decision=results.dictamen.decision if results.dictamen else "", notes=notes)


def _norm_low_better(vals: list[float | None]) -> list[float]:
    xs = [v for v in vals if v is not None]
    if not xs:
        return [0.5] * len(vals)
    lo, hi = min(xs), max(xs)
    return [((1.0 if hi == lo else (hi - v) / (hi - lo)) if v is not None else 0.0) for v in vals]


def compare(metrics: list[AltMetrics], weights: dict) -> tuple[list[AltMetrics], list[str]]:
    elig = [m for m in metrics if m.eligible]
    if elig:
        e = _norm_low_better([m.cost if m.cost else m.P_elec for m in elig])
        perf_raw = [(1.0 - m.deficit_max_pct / 100.0) * (m.eta or 0.5) for m in elig]
        hi = max(perf_raw) or 1.0
        perf = [p / hi for p in perf_raw]
        risk = _norm_low_better([m.n_alto * 3 + m.n_medio for m in elig])
        inst = _norm_low_better([float(m.complexity) for m in elig])
        mant = _norm_low_better([float(m.maintenance) for m in elig])
        w = {"energy": 0.3, "performance": 0.25, "risk": 0.25, "installation": 0.1, "maintenance": 0.1}
        w.update(weights or {})
        tot = sum(w.values()) or 1.0
        for i, m in enumerate(elig):
            m.score = 100.0 * (w["energy"] * e[i] + w["performance"] * perf[i] + w["risk"] * risk[i]
                               + w["installation"] * inst[i] + w["maintenance"] * mant[i]) / tot
    for m in metrics:
        if not m.eligible:
            m.score = 0.0
    concl: list[str] = []
    if not elig:
        concl.append("Ninguna alternativa es elegible: todas presentan condiciones críticas, déficit de caudal o "
                     "velocidades de transporte insuficientes. Se requiere rediseño.")
        for m in metrics:
            concl.append(f"• {m.name}: excluida por {', '.join(m.exclusion)}.")
        return metrics, concl
    best = max(elig, key=lambda m: m.score)
    concl.append(f"Alternativa recomendada: {best.name} (puntuación {best.score:.0f}/100).")
    cheapest = min((m for m in metrics if m.P_elec), key=lambda m: m.P_elec, default=None)
    if cheapest and cheapest.name != best.name:
        if not cheapest.eligible:
            concl.append(f"La alternativa de menor consumo ({cheapest.name}) no es elegible: "
                         f"{', '.join(cheapest.exclusion)}. El ahorro energético no compensa el riesgo técnico.")
        else:
            concl.append(f"{cheapest.name} consume menos energía, pero obtiene menor puntuación global por riesgo, "
                         "desempeño o facilidad de instalación/mantenimiento.")
    for m in metrics:
        if m is best:
            continue
        if m.eligible:
            concl.append(f"• {m.name}: elegible, puntuación {m.score:.0f}/100.")
        else:
            concl.append(f"• {m.name}: no elegible ({', '.join(m.exclusion)}).")
    concl.append("La comparación usa los pesos configurados; cambie los pesos si el proyecto prioriza otro criterio "
                 "(p. ej. costo de inversión o espacio disponible).")
    return metrics, concl


def run_alternatives(project, db, settings) -> tuple[list[AltMetrics], list[str]]:
    """Calcula todas las alternativas guardadas en el proyecto y las compara."""
    from core.calculation import run_project
    from core.project import Project
    mets = []
    for alt in project.alternatives:
        pr = Project.from_dict(alt.project)
        pr.units = project.units
        rr = run_project(pr, db, settings)
        mets.append(metrics_from_results(alt.name, pr, rr, alt.complexity, alt.maintenance, alt.notes))
    if not mets:
        return [], []
    return compare(mets, settings.weights)
