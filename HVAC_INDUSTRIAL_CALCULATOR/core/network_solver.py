"""Solucionador de redes de ductos ramificadas de EXTRACCIÓN (árbol convergente).

Modelo físico
-------------
* Todas las campanas toman aire de la atmósfera en reposo (presión total 0).
* La red converge en uniones hasta un único ventilador y descarga a la atmósfera
  por un único punto (chimenea). Topología de árbol: cada nodo distinto de la
  descarga tiene exactamente un tramo de salida.
* Balance en nodos por **presión total**: la presión total de un nodo es la
  presión total al inicio del tramo aguas abajo. Las pérdidas de unión (entrada
  de ramal, paso recto) se asignan como accesorios a los tramos que llegan a la
  unión, cada uno con su sección de referencia (convención ACGIH de pérdida de
  entrada de ramal o convención ASHRAE de coeficientes Cb/Cs). Con esta
  formulación la "corrección por presión de velocidad resultante" de ACGIH queda
  incluida automáticamente: SP = TP − VP en cada sección.
* Continuidad en **flujo másico**; la temperatura aguas abajo de una unión se
  obtiene por mezcla adiabática (cp constante). La densidad de cada tramo se
  evalúa con la presión barométrica y la humedad del ambiente (se desprecia el
  efecto de la presión manométrica del ducto sobre la densidad, < 1 % para
  presiones menores a 1 kPa).
* Pérdida de cada tramo = fricción (Darcy-Weisbach) + accesorios (K·ρV_ref²/2)
  + entrada de campana + compuerta de balance + equipos + descarga (K·VP en la
  salida a la atmósfera).

Modos de cálculo
----------------
1. Diseño balanceado (``solve_design``): con los caudales requeridos de cada
   campana se recorre la red desde las campanas hacia el ventilador. En cada
   unión se identifica el ramal gobernante (mayor pérdida). Para los demás se
   calcula la relación r = |TP_gob|/|TP_ramal| y se aplica la estrategia
   configurada: aceptar, aumentar el caudal del ramal (solución exacta del
   factor de escala, comparada con la aproximación Q·√r), proponer compuerta o
   rediseño. Los umbrales son criterios configurables.
2. Operación (``solve_operating``): con la geometría, las compuertas y la curva
   del ventilador (corregida por densidad y velocidad) se resuelve la
   distribución real de caudales. Incógnitas: flujos másicos de las campanas;
   ecuaciones: igualdad de presión total de todos los ramales que llegan a cada
   unión (n_campanas − 1 ecuaciones) y ecuación del ventilador (o caudal total
   impuesto para trazar la curva del sistema). Sistema cuadrado resuelto con
   Powell híbrido (scipy.optimize.root) con arranque desde el diseño.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
from scipy.optimize import brentq, root

from .air_properties import moist_air_density, viscosity_sutherland, mixing_temperature
from .duct_geometry import DuctGeometry, round_to_series
from .equipment import Equipment, equipment_dp
from .fittings import FittingDef, FittingInstance, evaluate_fitting, FittingEval
from .friction import reynolds, darcy_factor
from .hood_design import HoodEntry
from .trace import Trace, n

MODULE = "Redes ramificadas"


class NetworkError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class NetNode:
    id: str
    kind: str                       # 'hood' | 'junction' | 'fan' | 'outlet'
    label: str = ""
    hood_id: str | None = None      # vínculo a la definición de campana
    q_design: float | None = None   # m³/s a la temperatura de la campana (si no hay campana vinculada)
    temperature_c: float | None = None
    exit_K: float = 1.0             # solo descarga: K de salida referido a la sección de salida
    stack_height_above_roof_m: float | None = None
    fan_outlet_area_m2: float | None = None  # solo ventilador: área de descarga del ventilador
    x: float | None = None
    y: float | None = None

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "NetNode":
        node = cls(d["id"], d.get("kind", "junction"))
        for k, v in d.items():
            if hasattr(node, k):
                setattr(node, k, v)
        return node


@dataclass
class NetSegment:
    id: str
    from_node: str
    to_node: str
    shape: str = "circular"
    D: float | None = 0.3
    a: float | None = None
    b: float | None = None
    length: float = 1.0
    material_id: str = "galv_ashrae"
    roughness_m: float | None = None
    fittings: list[FittingInstance] = field(default_factory=list)
    equipment: list[Equipment] = field(default_factory=list)
    hood_entry: HoodEntry | None = None
    damper_K: float = 0.0
    contaminant_class: str | None = None
    label: str = ""

    @property
    def geometry(self) -> DuctGeometry:
        return DuctGeometry(self.shape, D=self.D, a=self.a, b=self.b)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "from_node": self.from_node, "to_node": self.to_node, "shape": self.shape,
            "D": self.D, "a": self.a, "b": self.b, "length": self.length, "material_id": self.material_id,
            "roughness_m": self.roughness_m, "fittings": [f.to_dict() for f in self.fittings],
            "equipment": [e.to_dict() for e in self.equipment],
            "hood_entry": dict(self.hood_entry.__dict__) if self.hood_entry else None,
            "damper_K": self.damper_K, "contaminant_class": self.contaminant_class, "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "NetSegment":
        he = d.get("hood_entry")
        return cls(
            d["id"], d["from_node"], d["to_node"], d.get("shape", "circular"), d.get("D"), d.get("a"), d.get("b"),
            d.get("length", 1.0), d.get("material_id", "galv_ashrae"), d.get("roughness_m"),
            [FittingInstance.from_dict(f) for f in d.get("fittings", []) or []],
            [Equipment.from_dict(e) for e in d.get("equipment", []) or []],
            HoodEntry(**he) if he else None, d.get("damper_K", 0.0) or 0.0, d.get("contaminant_class"),
            d.get("label", ""),
        )


@dataclass
class NetworkModel:
    nodes: dict[str, NetNode] = field(default_factory=dict)
    segments: list[NetSegment] = field(default_factory=list)

    # --- utilidades topológicas ---
    def seg(self, sid: str) -> NetSegment:
        for s in self.segments:
            if s.id == sid:
                return s
        raise NetworkError(f"Tramo {sid} no existe")

    def incoming(self, nid: str) -> list[NetSegment]:
        return [s for s in self.segments if s.to_node == nid]

    def outgoing(self, nid: str) -> list[NetSegment]:
        return [s for s in self.segments if s.from_node == nid]

    def nodes_of_kind(self, kind: str) -> list[NetNode]:
        return [nd for nd in self.nodes.values() if nd.kind == kind]

    @property
    def fan(self) -> NetNode:
        return self.nodes_of_kind("fan")[0]

    @property
    def outlet(self) -> NetNode:
        return self.nodes_of_kind("outlet")[0]

    def validate(self) -> list[str]:
        """Comprueba la topología; devuelve lista de errores (vacía si es válida)."""
        errs: list[str] = []
        if len(self.nodes_of_kind("fan")) != 1:
            errs.append("La red debe tener exactamente un nodo de ventilador.")
        if len(self.nodes_of_kind("outlet")) != 1:
            errs.append("La red debe tener exactamente una descarga a la atmósfera.")
        if not self.nodes_of_kind("hood"):
            errs.append("La red debe tener al menos una campana (entrada de aire).")
        ids = set(self.nodes)
        seg_ids = set()
        for s in self.segments:
            if s.id in seg_ids:
                errs.append(f"Identificador de tramo duplicado: {s.id}")
            seg_ids.add(s.id)
            if s.from_node not in ids or s.to_node not in ids:
                errs.append(f"El tramo {s.id} conecta nodos inexistentes ({s.from_node} → {s.to_node}).")
            if s.from_node == s.to_node:
                errs.append(f"El tramo {s.id} conecta un nodo consigo mismo.")
            try:
                s.geometry.validate()
            except Exception as e:  # noqa: BLE001
                errs.append(f"Tramo {s.id}: {e}")
            if s.length < 0:
                errs.append(f"Tramo {s.id}: longitud negativa.")
        if errs:
            return errs
        for nd in self.nodes.values():
            out = self.outgoing(nd.id)
            inc = self.incoming(nd.id)
            if nd.kind == "outlet":
                if out:
                    errs.append(f"La descarga {nd.id} no puede tener tramos de salida.")
                if len(inc) != 1:
                    errs.append(f"La descarga {nd.id} debe recibir exactamente un tramo.")
            else:
                if len(out) != 1:
                    errs.append(f"El nodo {nd.id} debe tener exactamente un tramo de salida (red en árbol convergente).")
            if nd.kind == "hood" and inc:
                errs.append(f"La campana {nd.id} no puede recibir tramos.")
            if nd.kind in ("junction", "fan") and not inc:
                errs.append(f"El nodo {nd.id} no recibe ningún tramo.")
        if errs:
            return errs
        # Cada campana debe llegar al ventilador y luego a la descarga
        fan_id, out_id = self.fan.id, self.outlet.id
        for h in self.nodes_of_kind("hood"):
            cur, seen, hit_fan = h.id, set(), False
            while cur != out_id:
                if cur in seen:
                    errs.append(f"Ciclo detectado desde {h.id}.")
                    break
                seen.add(cur)
                if cur == fan_id:
                    hit_fan = True
                cur = self.outgoing(cur)[0].to_node
            if not hit_fan:
                errs.append(f"La campana {h.id} no pasa por el ventilador antes de la descarga.")
        # El lado de descarga no debe tener uniones de varios ramales
        cur = fan_id
        while cur != out_id:
            nxt = self.outgoing(cur)[0].to_node
            if nxt != out_id and len(self.incoming(nxt)) > 1:
                errs.append("Uniones aguas abajo del ventilador no soportadas en esta versión.")
                break
            cur = nxt
        return errs

    def suction_order(self) -> list[str]:
        """Nodos del lado de succión en orden topológico (campanas → ventilador)."""
        order: list[str] = []
        visited: set[str] = set()

        def visit(nid: str):
            if nid in visited:
                return
            for s in self.incoming(nid):
                visit(s.from_node)
            visited.add(nid)
            order.append(nid)

        visit(self.fan.id)
        return order

    def discharge_path(self) -> list[NetSegment]:
        path, cur = [], self.fan.id
        while cur != self.outlet.id:
            s = self.outgoing(cur)[0]
            path.append(s)
            cur = s.to_node
        return path

    def upstream_hoods(self, nid: str) -> list[str]:
        nd = self.nodes[nid]
        if nd.kind == "hood":
            return [nid]
        out: list[str] = []
        for s in self.incoming(nid):
            out += self.upstream_hoods(s.from_node)
        return out

    def depth(self, nid: str) -> int:
        """Número de tramos entre el nodo y el ventilador."""
        d, cur = 0, nid
        while cur != self.fan.id and self.nodes[cur].kind != "outlet":
            cur = self.outgoing(cur)[0].to_node
            d += 1
        return d

    def to_dict(self) -> dict:
        return {"nodes": [nd.to_dict() for nd in self.nodes.values()], "segments": [s.to_dict() for s in self.segments]}

    @classmethod
    def from_dict(cls, d: dict) -> "NetworkModel":
        m = cls()
        for nd in d.get("nodes", []):
            node = NetNode.from_dict(nd)
            m.nodes[node.id] = node
        m.segments = [NetSegment.from_dict(s) for s in d.get("segments", [])]
        return m


# ---------------------------------------------------------------------------
# Contexto físico y evaluación de tramos
# ---------------------------------------------------------------------------

@dataclass
class FlowContext:
    p_atm: float                       # Pa
    W: float                           # kg/kg a.s.
    t_ambient: float                   # °C
    fittings_lib: dict[str, FittingDef]
    roughness_lib: dict[str, float]    # material_id → ε [m]
    friction_method: str = "colebrook"
    filter_state: str | None = None    # None → estado definido en cada equipo
    extra_K: dict[str, float] = field(default_factory=dict)  # K de compuerta adicional por tramo

    def rho(self, t_c: float) -> float:
        return moist_air_density(t_c, self.W, self.p_atm)

    def mu(self, t_c: float) -> float:
        return viscosity_sutherland(t_c)


@dataclass
class SegmentEval:
    seg_id: str
    mdot: float
    t_c: float
    rho: float
    mu: float
    Q: float
    A: float
    Dh: float
    V: float
    VP: float
    Re: float
    rel_rough: float
    f: float
    regime: str
    dp_friction: float
    dp_fittings: float
    dp_entry: float
    dp_damper: float
    dp_equipment: float
    dp_exit: float
    dp_total: float
    fittings: list[FittingEval] = field(default_factory=list)
    equipment: list[tuple[str, str, float]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    TP_start: float = 0.0
    TP_end: float = 0.0

    @property
    def SP_start(self) -> float:
        return self.TP_start - self.VP

    @property
    def SP_end(self) -> float:
        return self.TP_end - self.VP


def evaluate_segment(seg: NetSegment, mdot: float, t_c: float, ctx: FlowContext, is_outlet: bool = False,
                     exit_K: float = 1.0) -> SegmentEval:
    """Pérdida de presión total de un tramo para un flujo másico dado (con signo)."""
    sign = 1.0 if mdot >= 0 else -1.0
    m = abs(mdot)
    rho = ctx.rho(t_c)
    mu = ctx.mu(t_c)
    geom = seg.geometry
    A = geom.area
    Dh = geom.Dh
    Q = m / rho
    V = Q / A
    VP = 0.5 * rho * V * V
    eps = seg.roughness_m if seg.roughness_m is not None else ctx.roughness_lib.get(seg.material_id, 0.09e-3)
    warns: list[str] = []
    if V > 0:
        Re = reynolds(rho, V, Dh, mu)
        fr = darcy_factor(Re, eps / Dh, ctx.friction_method)
        f, regime = fr.f, fr.regime
        warns += fr.warnings
        dp_f = f * seg.length / Dh * VP
    else:
        Re, f, regime, dp_f = 0.0, 0.0, "sin flujo", 0.0
    fevals: list[FittingEval] = []
    dp_fit = 0.0
    for inst in seg.fittings:
        fd = ctx.fittings_lib.get(inst.fitting_id)
        fe = evaluate_fitting(inst, fd, Q, A, rho, Re if Re > 0 else None, f if f > 0 else None)
        fevals.append(fe)
        dp_fit += fe.dp
        warns += fe.warnings
    dp_entry = 0.0
    if seg.hood_entry is not None and Q > 0:
        he = seg.hood_entry
        dp_entry = he.Fh * VP
        if he.kind == "slot" and he.slot_area:
            VPs = 0.5 * rho * (Q / he.slot_area) ** 2
            dp_entry += he.Fs * VPs + (VPs if he.plenum_loss else 0.0)
    K_damper = (seg.damper_K or 0.0) + ctx.extra_K.get(seg.id, 0.0)
    dp_damper = K_damper * VP
    dp_eq = 0.0
    eq_list: list[tuple[str, str, float]] = []
    for eq in seg.equipment:
        dpe, w = equipment_dp(eq, Q, ctx.filter_state if eq.model == "filter" else None)
        dp_eq += dpe
        eq_list.append((eq.name, eq.eq_type, dpe))
        warns += w
    dp_exit = exit_K * VP if is_outlet else 0.0
    total = dp_f + dp_fit + dp_entry + dp_damper + dp_eq + dp_exit
    return SegmentEval(seg.id, mdot, t_c, rho, mu, Q * sign, A, Dh, V * sign, VP, Re, eps / Dh, f, regime,
                       dp_f * sign, dp_fit * sign, dp_entry * sign, dp_damper * sign, dp_eq * sign, dp_exit * sign,
                       total * sign, fevals, eq_list, list(dict.fromkeys(warns)))


# ---------------------------------------------------------------------------
# Evaluación hacia adelante de toda la red con flujos de campana conocidos
# ---------------------------------------------------------------------------

@dataclass
class ForwardState:
    seg_evals: dict[str, SegmentEval]
    node_tp: dict[str, float]
    node_t: dict[str, float]
    node_mdot: dict[str, float]
    junction_ends: dict[str, list[tuple[str, float]]]   # nodo → [(tramo, TP_fin)]
    tp_fan_in: float
    tp_fan_out: float
    mdot_fan: float
    t_fan: float
    rho_fan: float
    Q_fan: float
    VP_fan_in: float
    VP_fan_out: float
    FTP: float
    FSP: float


def forward(model: NetworkModel, ctx: FlowContext, hood_mdot: dict[str, float],
            hood_temp: dict[str, float], node_rule: str = "min") -> ForwardState:
    """Recorre la red desde las campanas con flujos másicos fijos y calcula presiones.

    node_rule = 'min'   → la presión total del nodo es la del ramal gobernante (diseño).
    node_rule = 'first' → la del primer ramal (función suave para el solucionador de operación;
                          en la solución convergida todos los ramales coinciden).
    """
    seg_evals: dict[str, SegmentEval] = {}
    node_tp: dict[str, float] = {}
    node_t: dict[str, float] = {}
    node_m: dict[str, float] = {}
    ends: dict[str, list[tuple[str, float]]] = {}
    for nid in model.suction_order():
        nd = model.nodes[nid]
        if nd.kind == "hood":
            node_tp[nid] = 0.0
            node_t[nid] = hood_temp[nid]
            node_m[nid] = hood_mdot[nid]
            continue
        streams, lst = [], []
        for s in model.incoming(nid):
            u = s.from_node
            ev = evaluate_segment(s, node_m[u], node_t[u], ctx)
            ev.TP_start = node_tp[u]
            ev.TP_end = node_tp[u] - ev.dp_total
            seg_evals[s.id] = ev
            lst.append((s.id, ev.TP_end))
            streams.append((node_m[u], node_t[u]))
        ends[nid] = lst
        node_tp[nid] = min(tp for _, tp in lst) if node_rule == "min" else lst[0][1]
        node_m[nid] = sum(m for m, _ in streams)
        node_t[nid] = mixing_temperature(streams)
    fan_id = model.fan.id
    m_fan = node_m[fan_id]
    t_fan = node_t[fan_id]
    # Lado de descarga: desde la salida (TP = 0 tras la pérdida de descarga) hacia el ventilador
    path = model.discharge_path()
    dp_dis = 0.0
    evs = []
    for i, s in enumerate(path):
        is_out = (i == len(path) - 1)
        ev = evaluate_segment(s, m_fan, t_fan, ctx, is_outlet=is_out, exit_K=model.outlet.exit_K)
        evs.append(ev)
        dp_dis += ev.dp_total
    tp = dp_dis
    for ev in evs:
        ev.TP_start = tp
        # En el tramo de descarga TP_fin es la presión total justo DENTRO de la boca de salida
        # (SP = 0 si K_salida = 1); la pérdida de descarga ocurre fuera del ducto.
        ev.TP_end = tp - (ev.dp_total - ev.dp_exit)
        tp = tp - ev.dp_total
        seg_evals[ev.seg_id] = ev
    tp_out = dp_dis
    tp_in = node_tp[fan_id]
    rho_fan = ctx.rho(t_fan)
    Q_fan = m_fan / rho_fan
    inc = model.incoming(fan_id)
    VP_in = seg_evals[inc[0].id].VP if len(inc) == 1 else 0.0
    fan_area = model.fan.fan_outlet_area_m2
    if fan_area and fan_area > 0:
        VP_out = 0.5 * rho_fan * (Q_fan / fan_area) ** 2
    else:
        VP_out = evs[0].VP if evs else 0.0
    FTP = tp_out - tp_in
    FSP = FTP - VP_out
    return ForwardState(seg_evals, node_tp, node_t, node_m, ends, tp_in, tp_out, m_fan, t_fan, rho_fan, Q_fan,
                        VP_in, VP_out, FTP, FSP)


# ---------------------------------------------------------------------------
# Modo de diseño balanceado
# ---------------------------------------------------------------------------

@dataclass
class BalanceRecord:
    junction: str
    governing_segment: str
    segment: str
    tp_gov: float
    tp_branch: float
    ratio: float
    action: str
    scale: float = 1.0
    scale_sqrt_approx: float = 1.0
    Q_before: float = 0.0
    Q_after: float = 0.0
    damper_K_required: float | None = None
    suggested_D: float | None = None
    suggested_D_velocity: float | None = None
    note: str = ""


@dataclass
class NetworkResult:
    mode: str
    state: ForwardState
    hood_q_required: dict[str, float]      # m³/s requeridos (a T de campana)
    hood_q_final: dict[str, float]         # m³/s resultantes (corregidos o de operación)
    balance: list[BalanceRecord]
    critical_path: list[str]                # tramos desde la campana gobernante hasta la descarga
    governing_hood: str
    trace: Trace
    warnings: list[str] = field(default_factory=list)
    damper_K: dict[str, float] = field(default_factory=dict)
    converged: bool = True
    residual_pa: float = 0.0
    iterations: int = 0

    # --- resúmenes ---
    def breakdown_critical(self) -> dict[str, float]:
        """Pérdidas por componente a lo largo del camino crítico (Pa)."""
        out = {"Fricción": 0.0, "Entrada de campana": 0.0, "Compuertas": 0.0, "Equipos": 0.0, "Descarga": 0.0}
        cats: dict[str, float] = {}
        for sid in self.critical_path:
            ev = self.state.seg_evals[sid]
            out["Fricción"] += ev.dp_friction
            out["Entrada de campana"] += ev.dp_entry
            out["Compuertas"] += ev.dp_damper
            out["Equipos"] += ev.dp_equipment
            out["Descarga"] += ev.dp_exit
            for fe in ev.fittings:
                cats[fe.category] = cats.get(fe.category, 0.0) + fe.dp
        out.update(cats)
        return {k: v for k, v in out.items() if abs(v) > 1e-9}

    def total_by_type(self) -> dict[str, float]:
        """Fricción, locales y equipos del camino crítico."""
        fr = loc = eq = 0.0
        for sid in self.critical_path:
            ev = self.state.seg_evals[sid]
            fr += ev.dp_friction
            loc += ev.dp_fittings + ev.dp_entry + ev.dp_damper + ev.dp_exit
            eq += ev.dp_equipment
        return {"Fricción": fr, "Locales": loc, "Equipos": eq, "Total": fr + loc + eq}


def _hood_temps(model: NetworkModel, ctx: FlowContext) -> dict[str, float]:
    return {h.id: (h.temperature_c if h.temperature_c is not None else ctx.t_ambient)
            for h in model.nodes_of_kind("hood")}


def _critical_path(model: NetworkModel, st: ForwardState) -> tuple[list[str], str]:
    """Camino crítico: desde el ventilador se remonta siempre por el ramal de menor TP_fin."""
    path: list[str] = []
    cur = model.fan.id
    while model.nodes[cur].kind != "hood":
        lst = st.junction_ends[cur]
        sid = min(lst, key=lambda t: t[1])[0]
        path.insert(0, sid)
        cur = model.seg(sid).from_node
    path += [s.id for s in model.discharge_path()]
    return path, cur


def solve_design(model: NetworkModel, ctx: FlowContext, hood_q: dict[str, float], strategy: str = "acgih",
                 tol_ignore: float = 0.05, tol_increase: float = 0.20, force_increase: bool = False,
                 diameter_series_mm: list[float] | None = None, v_min_transport: Callable[[NetSegment], float] | None = None
                 ) -> NetworkResult:
    """Diseño balanceado con los caudales requeridos por campana (m³/s a T de campana).

    strategy: 'acgih' (aceptar / aumentar caudal / rediseñar según umbrales),
              'dampers' (compuertas en los ramales no gobernantes), 'none' (solo informe).
    """
    errs = model.validate()
    if errs:
        raise NetworkError("; ".join(errs))
    temps = _hood_temps(model, ctx)
    for h in model.nodes_of_kind("hood"):
        if hood_q.get(h.id) is None or hood_q[h.id] <= 0:
            raise NetworkError(f"La campana {h.id} no tiene caudal de diseño")
    mdot = {hid: hood_q[hid] * ctx.rho(temps[hid]) for hid in hood_q}
    mdot_req = dict(mdot)
    tr = Trace()
    balance: list[BalanceRecord] = []
    dampers: dict[str, float] = {}
    work_ctx = FlowContext(ctx.p_atm, ctx.W, ctx.t_ambient, ctx.fittings_lib, ctx.roughness_lib, ctx.friction_method,
                           ctx.filter_state, dict(ctx.extra_K))

    for nid in model.suction_order():
        nd = model.nodes[nid]
        inc = model.incoming(nid)
        if nd.kind == "hood" or len(inc) < 2:
            continue
        st = forward(model, work_ctx, mdot, temps)
        lst = st.junction_ends[nid]
        gov_sid, tp_gov = min(lst, key=lambda t: t[1])
        for sid, tp_b in lst:
            if sid == gov_sid:
                continue
            s = model.seg(sid)
            r = tp_gov / tp_b if tp_b < 0 else float("inf")
            hoods_up = model.upstream_hoods(s.from_node)
            m_before = sum(mdot[h] for h in hoods_up)
            Q_before = st.seg_evals[sid].Q
            rec = BalanceRecord(nid, gov_sid, sid, tp_gov, tp_b, r, "aceptado", Q_before=Q_before, Q_after=Q_before)
            excess = r - 1.0
            if strategy == "none" or excess <= tol_ignore:
                rec.action = "aceptado" if excess <= tol_ignore else "desbalance informado"
            elif strategy == "dampers":
                VP = st.seg_evals[sid].VP
                K_req = (abs(tp_gov) - abs(tp_b)) / VP
                dampers[sid] = dampers.get(sid, 0.0) + K_req
                work_ctx.extra_K[sid] = work_ctx.extra_K.get(sid, 0.0) + K_req
                rec.action = "compuerta de balance"
                rec.damper_K_required = K_req
            elif excess <= tol_increase or force_increase:
                base = {h: mdot[h] for h in hoods_up}

                def resid(scale: float) -> float:
                    trial = dict(mdot)
                    for h in hoods_up:
                        trial[h] = base[h] * scale
                    stt = forward(model, work_ctx, trial, temps)
                    return dict(stt.junction_ends[nid])[sid] - tp_gov

                try:
                    scale = brentq(resid, 1.0, 3.0, xtol=1e-10)
                except ValueError:
                    scale = math.sqrt(r)
                    rec.note = "No se encontró solución exacta; se usa Q·√r."
                for h in hoods_up:
                    mdot[h] = base[h] * scale
                rec.scale = scale
                rec.scale_sqrt_approx = math.sqrt(r)
                rec.action = "aumento de caudal del ramal" + (" (forzado sobre el límite)" if excess > tol_increase else "")
                st2 = forward(model, work_ctx, mdot, temps)
                rec.Q_after = st2.seg_evals[sid].Q
                tr.add(MODULE, f"Balance en {nid}: corrección del ramal {sid}", "Q_corr: TP_fin(Q_corr) = TP_gob  ≈ Q·√(TP_gob/TP_ramal)",
                       [("TP_gob", tp_gov, "Pa", f"Ramal gobernante {gov_sid}"), ("TP_ramal", tp_b, "Pa", ""),
                        ("Q", Q_before, "m³/s", "Caudal de diseño del ramal")],
                       f"r = {n(r)}; Q_corr = {n(Q_before)}·{n(scale)} (aprox. √r = {n(math.sqrt(r))})",
                       rec.Q_after, "m³/s", "Método de equilibrado por diseño (ACGIH); solución numérica exacta")
            else:
                rec.action = "rediseñar ramal o instalar compuerta"
                VP = st.seg_evals[sid].VP
                rec.damper_K_required = (abs(tp_gov) - abs(tp_b)) / VP
                # Diámetro sugerido para el tramo final del ramal (mismo caudal de diseño)
                if s.shape == "circular" and diameter_series_mm:
                    rec.suggested_D, rec.suggested_D_velocity = _suggest_diameter(
                        model, work_ctx, mdot, temps, nid, sid, tp_gov, diameter_series_mm)
            balance.append(rec)

    st = forward(model, work_ctx, mdot, temps)
    path, gov_hood = _critical_path(model, st)
    hood_q_final = {h: mdot[h] / ctx.rho(temps[h]) for h in mdot}
    res = NetworkResult("diseño", st, dict(hood_q), hood_q_final, balance, path, gov_hood, tr, damper_K=dampers)
    _add_segment_traces(res, model)
    tr.add(MODULE, "Presión total requerida del ventilador", "FTP = TP_salida − TP_entrada",
           [("TP_salida", st.tp_fan_out, "Pa", "Pérdidas de descarga incl. salida"),
            ("TP_entrada", st.tp_fan_in, "Pa", "Presión total en la succión (camino crítico)")],
           f"FTP = {n(st.tp_fan_out)} − ({n(st.tp_fan_in)})", st.FTP, "Pa", "AMCA 210 / ASHRAE 51 (definición)")
    tr.add(MODULE, "Presión estática del ventilador", "FSP = FTP − VP_salida",
           [("FTP", st.FTP, "Pa", ""), ("VP_salida", st.VP_fan_out, "Pa", "")],
           f"FSP = {n(st.FTP)} − {n(st.VP_fan_out)}", st.FSP, "Pa", "AMCA 210 / ASHRAE 51 (definición)")
    tr.add(MODULE, "Caudal en la entrada del ventilador", "Q = ṁ/ρ_entrada",
           [("ṁ", st.mdot_fan, "kg/s", "Suma de flujos másicos"), ("ρ", st.rho_fan, "kg/m³", "")],
           f"Q = {n(st.mdot_fan)}/{n(st.rho_fan)}", st.Q_fan, "m³/s", "Continuidad (masa)")
    return res


def _suggest_diameter(model, ctx, mdot, temps, nid, sid, tp_gov, series_mm):
    s = model.seg(sid)
    D0 = s.D
    best = None
    for D_mm in sorted(series_mm, reverse=True):
        D = D_mm / 1000.0
        if D >= D0:
            continue
        s.D = D
        stt = forward(model, ctx, mdot, temps)
        tp = dict(stt.junction_ends[nid])[sid]
        V = stt.seg_evals[sid].V
        if tp <= tp_gov:
            best = (D, V)
            break
        best = (D, V)
    s.D = D0
    return best if best else (None, None)


def _add_segment_traces(res: NetworkResult, model: NetworkModel) -> None:
    tr = res.trace
    for sid, ev in res.state.seg_evals.items():
        s = model.seg(sid)
        tr.add(MODULE, f"Tramo {sid}: velocidad", "V = Q/A", [("Q", ev.Q, "m³/s", ""), ("A", ev.A, "m²", s.geometry.describe())],
               f"V = {n(ev.Q)}/{n(ev.A)}", ev.V, "m/s", "Continuidad")
        tr.add(MODULE, f"Tramo {sid}: Reynolds", "Re = ρ·V·Dh/μ",
               [("ρ", ev.rho, "kg/m³", ""), ("V", ev.V, "m/s", ""), ("Dh", ev.Dh, "m", ""), ("μ", ev.mu, "Pa·s", "")],
               f"Re = {n(ev.rho)}·{n(ev.V)}·{n(ev.Dh)}/{n(ev.mu)}", ev.Re, "-", "Definición")
        tr.add(MODULE, f"Tramo {sid}: fricción", "ΔPf = f·(L/Dh)·ρV²/2",
               [("f", ev.f, "-", f"Darcy, régimen {ev.regime}"), ("L", s.length, "m", ""), ("Dh", ev.Dh, "m", ""),
                ("VP", ev.VP, "Pa", "")],
               f"ΔPf = {n(ev.f)}·({n(s.length)}/{n(ev.Dh)})·{n(ev.VP)}", ev.dp_friction, "Pa", "Darcy-Weisbach")
        for fe in ev.fittings:
            tr.add(MODULE, f"Tramo {sid}: {fe.name}", "ΔP = n·K·ρ·V_ref²/2",
                   [("n", fe.qty, "-", ""), ("K", fe.K, "-", fe.status), ("V_ref", fe.V_ref, "m/s", f"A_ref = {fe.area_ref:.4f} m²")],
                   f"ΔP = {n(fe.qty)}·{n(fe.K)}·{n(ev.rho)}·{n(fe.V_ref)}²/2", fe.dp, "Pa", fe.source)
        if ev.dp_entry:
            tr.add(MODULE, f"Tramo {sid}: entrada de campana", "he = Fh·VPd (+ Fs·VPs)", [("VPd", ev.VP, "Pa", "")],
                   "ver módulo de campanas", ev.dp_entry, "Pa", "ACGIH (coeficientes de entrada)")
        for name, typ, dp in ev.equipment:
            tr.add(MODULE, f"Tramo {sid}: {name}", "ΔP_equipo(Q)", [("Q", ev.Q, "m³/s", typ)], "curva/dato del equipo",
                   dp, "Pa", "Dato del fabricante (indicado por el usuario)", kind="Dato externo (requiere validación)")
        if ev.dp_exit:
            tr.add(MODULE, f"Tramo {sid}: descarga a la atmósfera", "ΔP = K_salida·VP", [("VP", ev.VP, "Pa", "")],
                   f"ΔP = K·{n(ev.VP)}", ev.dp_exit, "Pa", "Energía cinética perdida en la descarga")
        if ev.dp_damper:
            tr.add(MODULE, f"Tramo {sid}: compuerta de balance", "ΔP = K_c·VP", [("VP", ev.VP, "Pa", "")],
                   f"ΔP = K·{n(ev.VP)}", ev.dp_damper, "Pa", "K requerido por el balance (ajuste en campo)")


# ---------------------------------------------------------------------------
# Modo de operación (curva del ventilador o caudal total impuesto)
# ---------------------------------------------------------------------------

FanCallable = Callable[[float, float], float]   # (Q_actual m³/s, ρ_entrada) → FTP [Pa]


def solve_operating(model: NetworkModel, ctx: FlowContext, x0_mdot: dict[str, float],
                    fan_ftp: FanCallable | None = None, Q_total: float | None = None,
                    tol: float = 1e-6, max_iter: int = 400) -> NetworkResult:
    """Distribución real de caudales.

    Si se da ``fan_ftp`` se resuelve el punto de operación con el ventilador; si se da
    ``Q_total`` (m³/s en la entrada del ventilador) se impone el caudal total (curva del sistema).
    """
    if (fan_ftp is None) == (Q_total is None):
        raise NetworkError("Indique la curva del ventilador o el caudal total, no ambos")
    temps = _hood_temps(model, ctx)
    hoods = [h.id for h in model.nodes_of_kind("hood")]
    scale = np.array([max(abs(x0_mdot[h]), 1e-6) for h in hoods])
    p_scale = 100.0
    junctions = [nid for nid in model.suction_order()
                 if model.nodes[nid].kind != "hood" and len(model.incoming(nid)) >= 2]

    def unpack(x):
        return {h: x[i] * scale[i] for i, h in enumerate(hoods)}

    def residual(x):
        m = unpack(x)
        st = forward(model, ctx, m, temps, node_rule="first")
        res = []
        for nid in junctions:
            lst = st.junction_ends[nid]
            ref = lst[0][1]
            for _, tp in lst[1:]:
                res.append((tp - ref) / p_scale)
        if fan_ftp is not None:
            res.append((fan_ftp(st.Q_fan, st.rho_fan) - st.FTP) / p_scale)
        else:
            res.append((st.Q_fan - Q_total) / max(Q_total, 1e-9) * 10.0)
        return np.array(res)

    x0 = np.ones(len(hoods))
    if Q_total is not None:
        st0 = forward(model, ctx, x0_mdot, temps)
        if st0.Q_fan > 0:
            x0 = x0 * Q_total / st0.Q_fan
    sol = root(residual, x0, method="hybr", tol=tol, options={"maxfev": max_iter * (len(hoods) + 1)})
    if not sol.success or np.max(np.abs(sol.fun)) > 1e-4:
        sol2 = root(residual, sol.x if np.all(np.isfinite(sol.x)) else x0, method="lm", tol=tol,
                    options={"maxiter": max_iter * 10})
        if np.max(np.abs(sol2.fun)) < np.max(np.abs(sol.fun)):
            sol = sol2
    m = unpack(sol.x)
    st = forward(model, ctx, m, temps)
    resid_pa = float(np.max(np.abs(sol.fun)) * p_scale) if len(sol.fun) else 0.0
    converged = resid_pa < 0.05 and all(v >= 0 for v in m.values())
    path, gov = _critical_path(model, st)
    q_final = {h: m[h] / ctx.rho(temps[h]) for h in hoods}
    warns = []
    if any(v < 0 for v in m.values()):
        warns.append("Flujo invertido en alguna campana: la red no puede operar como se definió.")
    if not converged:
        warns.append(f"El solucionador no alcanzó la tolerancia (residuo {resid_pa:.3g} Pa).")
    res = NetworkResult("operación", st, {}, q_final, [], path, gov, Trace(), warns,
                        converged=converged, residual_pa=resid_pa, iterations=int(getattr(sol, "nfev", 0)))
    return res


def system_curve(model: NetworkModel, ctx: FlowContext, x0_mdot: dict[str, float], Q_values: list[float]
                 ) -> list[tuple[float, float, float, bool]]:
    """Curva del sistema: lista de (Q_ventilador, FTP requerido, FSP requerido, convergió)."""
    out = []
    guess = dict(x0_mdot)
    for Q in Q_values:
        r = solve_operating(model, ctx, guess, Q_total=Q)
        out.append((r.state.Q_fan, r.state.FTP, r.state.FSP, r.converged))
        if r.converged:
            guess = {h: r.state.node_mdot[h] for h in guess}
    return out
