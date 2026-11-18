"""Campanas de extracción localizada.

Ecuaciones de caudal por geometría (DallaValle / Silverman, reproducidas en
ACGIH Industrial Ventilation Manual). Los coeficientes numéricos (10, 0.75, 5,
3.7, 2.6, 1.4) son adimensionales: las ecuaciones son dimensionalmente
homogéneas y valen en SI o IP.

  exterior_plain    Q = Vc·(10X² + A)            abertura libre, W/L ≥ 0.2, X ≤ 1.5·D
  exterior_flanged  Q = 0.75·Vc·(10X² + A)       abertura con brida
  bench_plain       Q = Vc·(5X² + A)             abertura apoyada sobre mesa/plano
  bench_flanged     Q = 0.75·Vc·(5X² + A)        sobre mesa y con brida
  slot              Q = 3.7·L·Vc·X               ranura sin brida, W/L ≤ 0.2
  slot_flanged      Q = 2.6·L·Vc·X               ranura con brida
  booth             Q = Vf·W·H                   cabina (velocidad de cara)
  enclosure         Q = Vf·A_aberturas           campana envolvente
  canopy            Q = 1.4·P·D·Vc               campana de dosel para procesos fríos
  receiving         Q = Q_fuente·(1 + margen)    campana de recepción (flujo inducido por el proceso)

Pérdida de entrada (ACGIH):  he = Fh·VPd,  Fh = (1 − Ce²)/Ce²
Presión estática de campana: SPh = he + VPd (aceleración del aire desde el reposo)
Campanas compuestas (ranura + pleno): pérdida total = Fs·VPs + Fd·VPd (+ VPs si se
considera perdida la energía cinética de la ranura en el pleno; hipótesis del usuario).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .trace import Trace, n, KIND_EXTERNAL, KIND_HYPOTHESIS

MODULE = "Campanas"
SRC_ACGIH = "ACGIH, Industrial Ventilation: A Manual of Recommended Practice for Design (ecuaciones de DallaValle)"
SRC_ACGIH_ENTRY = "ACGIH, Industrial Ventilation Manual — coeficiente de entrada Ce y factor de pérdida Fh"

HOOD_TYPES = {
    "exterior_plain": {"label": "Campana exterior (abertura libre, sin brida)", "eq": "Q = Vc·(10X² + A)",
                       "params": ["W", "H", "X", "Vc"]},
    "exterior_flanged": {"label": "Campana exterior con brida", "eq": "Q = 0.75·Vc·(10X² + A)",
                         "params": ["W", "H", "X", "Vc"]},
    "bench_plain": {"label": "Campana sobre mesa (sin brida)", "eq": "Q = Vc·(5X² + A)",
                    "params": ["W", "H", "X", "Vc"]},
    "bench_flanged": {"label": "Campana sobre mesa con brida", "eq": "Q = 0.75·Vc·(5X² + A)",
                      "params": ["W", "H", "X", "Vc"]},
    "slot": {"label": "Campana ranurada (sin brida)", "eq": "Q = 3.7·L·Vc·X", "params": ["L", "Ws", "X", "Vc"]},
    "slot_flanged": {"label": "Campana ranurada con brida", "eq": "Q = 2.6·L·Vc·X", "params": ["L", "Ws", "X", "Vc"]},
    "booth": {"label": "Cabina de extracción", "eq": "Q = Vf·W·H", "params": ["W", "H", "Vc"]},
    "enclosure": {"label": "Campana envolvente", "eq": "Q = Vf·A_ab", "params": ["A_open", "Vc"]},
    "canopy": {"label": "Campana de dosel (proceso frío)", "eq": "Q = 1.4·P·D·Vc", "params": ["P", "D", "Vc"]},
    "receiving": {"label": "Campana de recepción", "eq": "Q = Q_fuente·(1 + margen)", "params": ["Q_source", "margin"]},
}

# Validez geométrica (ACGIH / DallaValle). Valores en la base de datos editable;
# estos son los de respaldo si la base no está disponible.
DEFAULT_LIMITS = {"x_over_d_max": 1.5, "slot_aspect_max": 0.2}


class HoodError(ValueError):
    pass


@dataclass
class HoodEntry:
    """Definición de la pérdida de entrada de la campana."""
    kind: str = "fh"            # 'fh' (simple) o 'slot' (compuesta ranura + pleno)
    Fh: float = 0.49            # factor de pérdida del ducto/campana referido a VPd
    Fs: float = 1.78            # factor de pérdida de la ranura referido a VPs
    slot_area: float | None = None   # m² área de ranuras
    plenum_loss: bool = False   # considerar perdida la energía cinética de la ranura (VPs)
    source: str = SRC_ACGIH_ENTRY


@dataclass
class HoodResult:
    hood_id: str
    type: str
    Q: float
    area_face: float | None
    V_face: float | None
    eq: str
    validity: list[str] = field(default_factory=list)
    trace: Trace = field(default_factory=Trace)


def ce_to_fh(ce: float) -> float:
    """Fh = (1 − Ce²)/Ce²."""
    if not (0 < ce <= 1):
        raise HoodError("Ce debe estar en (0, 1]")
    return (1.0 - ce ** 2) / ce ** 2


def fh_to_ce(fh: float) -> float:
    """Ce = √(1/(1 + Fh))."""
    return math.sqrt(1.0 / (1.0 + fh))


def hood_airflow(hood_id: str, htype: str, p: dict, limits: dict | None = None) -> HoodResult:
    """Caudal requerido por la campana según su geometría.

    ``p`` contiene (en SI): W, H (m) dimensiones de la cara; X (m) distancia de captura;
    Vc (m/s) velocidad de captura o de cara; L (m) longitud de ranura; Ws (m) ancho de
    ranura; A_open (m²); P (m) perímetro; D (m) altura sobre el proceso; Q_source (m³/s);
    margin (fracción).
    """
    lim = dict(DEFAULT_LIMITS)
    if limits:
        lim.update(limits)
    if htype not in HOOD_TYPES:
        raise HoodError(f"Tipo de campana desconocido: {htype}")
    tr = Trace()
    val: list[str] = []
    eq = HOOD_TYPES[htype]["eq"]
    Vc = float(p.get("Vc", 0) or 0)
    X = float(p.get("X", 0) or 0)
    W = float(p.get("W", 0) or 0)
    H = float(p.get("H", 0) or 0)
    area = None
    if htype in ("exterior_plain", "exterior_flanged", "bench_plain", "bench_flanged"):
        if W <= 0 or H <= 0 or Vc <= 0 or X < 0:
            raise HoodError("Indique dimensiones W, H, distancia X y velocidad de captura Vc positivas")
        area = W * H
        k = 0.75 if "flanged" in htype else 1.0
        c = 5.0 if "bench" in htype else 10.0
        Q = k * Vc * (c * X ** 2 + area)
        tr.add(MODULE, f"Caudal de campana ({HOOD_TYPES[htype]['label']})", eq,
               [("Vc", Vc, "m/s", "Velocidad de captura en el punto X"), ("X", X, "m", "Distancia de captura"),
                ("A", area, "m²", "Área de la cara W·H")],
               f"Q = {k}·{n(Vc)}·({c:g}·{n(X)}² + {n(area)})", Q, "m³/s", SRC_ACGIH)
        aspect = min(W, H) / max(W, H)
        d_eq = math.sqrt(4 * area / math.pi)
        if aspect < lim["slot_aspect_max"]:
            val.append(f"Relación de aspecto W/L = {aspect:.2f} < {lim['slot_aspect_max']}: la abertura se comporta "
                       "como ranura; use la ecuación de campana ranurada.")
        if X > lim["x_over_d_max"] * d_eq:
            val.append(f"X = {X:.3f} m > {lim['x_over_d_max']}·D_eq = {lim['x_over_d_max'] * d_eq:.3f} m: fuera del rango "
                       "de validez de la ecuación de DallaValle; acerque la campana a la fuente.")
        if "flanged" in htype:
            val.append("Verifique el ancho mínimo de brida en el manual ACGIH (la reducción del 25 % solo aplica con "
                       "brida suficiente).")
    elif htype in ("slot", "slot_flanged"):
        L = float(p.get("L", 0) or 0)
        Ws = float(p.get("Ws", 0) or 0)
        if L <= 0 or Vc <= 0 or X <= 0:
            raise HoodError("Indique longitud de ranura L, distancia X y velocidad Vc positivas")
        k = 2.6 if htype == "slot_flanged" else 3.7
        Q = k * L * Vc * X
        area = L * Ws if Ws > 0 else None
        tr.add(MODULE, f"Caudal de campana ({HOOD_TYPES[htype]['label']})", eq,
               [("L", L, "m", "Longitud de ranura"), ("Vc", Vc, "m/s", ""), ("X", X, "m", "")],
               f"Q = {k}·{n(L)}·{n(Vc)}·{n(X)}", Q, "m³/s", SRC_ACGIH)
        if Ws > 0 and Ws / L > lim["slot_aspect_max"]:
            val.append(f"Relación ancho/longitud = {Ws / L:.2f} > {lim['slot_aspect_max']}: no es una ranura; use la "
                       "ecuación de abertura rectangular.")
    elif htype == "booth":
        if W <= 0 or H <= 0 or Vc <= 0:
            raise HoodError("Indique ancho, alto y velocidad de cara positivos")
        area = W * H
        Q = Vc * area
        tr.add(MODULE, "Caudal de cabina", eq, [("Vf", Vc, "m/s", "Velocidad de cara"), ("W", W, "m", ""), ("H", H, "m", "")],
               f"Q = {n(Vc)}·{n(W)}·{n(H)}", Q, "m³/s", SRC_ACGIH)
    elif htype == "enclosure":
        A_open = float(p.get("A_open", 0) or 0)
        if A_open <= 0 or Vc <= 0:
            raise HoodError("Indique el área de aberturas y la velocidad a través de ellas")
        area = A_open
        Q = Vc * A_open
        tr.add(MODULE, "Caudal de campana envolvente", eq,
               [("Vf", Vc, "m/s", "Velocidad en aberturas"), ("A_ab", A_open, "m²", "Área total de aberturas")],
               f"Q = {n(Vc)}·{n(A_open)}", Q, "m³/s", SRC_ACGIH)
    elif htype == "canopy":
        P = float(p.get("P", 0) or 0)
        D = float(p.get("D", 0) or 0)
        if P <= 0 or D <= 0 or Vc <= 0:
            raise HoodError("Indique perímetro P, altura D y velocidad Vc positivos")
        Q = 1.4 * P * D * Vc
        tr.add(MODULE, "Caudal de campana de dosel", eq,
               [("P", P, "m", "Perímetro del proceso"), ("D", D, "m", "Altura sobre el proceso"), ("Vc", Vc, "m/s", "")],
               f"Q = 1.4·{n(P)}·{n(D)}·{n(Vc)}", Q, "m³/s", SRC_ACGIH,
               notes="Aplicable a procesos fríos; para fuentes calientes se requiere el análisis de pluma térmica "
                     "del manual ACGIH.")
        val.append("La campana de dosel no protege la zona respiratoria del operador si éste se inclina sobre el "
                   "proceso; evalúe campana lateral o envolvente.")
    else:  # receiving
        Qs = float(p.get("Q_source", 0) or 0)
        margin = float(p.get("margin", 0) or 0)
        if Qs <= 0:
            raise HoodError("Indique el caudal inducido por la fuente (dato de proceso)")
        Q = Qs * (1.0 + margin)
        tr.add(MODULE, "Caudal de campana de recepción", eq,
               [("Q_fuente", Qs, "m³/s", "Flujo inducido por el proceso (dato externo)"),
                ("margen", margin, "-", "Margen de diseño")],
               f"Q = {n(Qs)}·(1 + {n(margin)})", Q, "m³/s", "Balance de caudales; ACGIH (campanas de recepción)",
               kind=KIND_EXTERNAL)
        val.append("El caudal inducido por la fuente debe justificarse (pluma térmica, chorro del proceso); "
                   "requiere validación.")
    v_face = Q / area if area else None
    if v_face is not None:
        tr.add(MODULE, "Velocidad media en la cara", "Vf = Q/A", [("Q", Q, "m³/s", ""), ("A", area, "m²", "")],
               f"Vf = {n(Q)}/{n(area)}", v_face, "m/s", "Continuidad")
    return HoodResult(hood_id, htype, Q, area, v_face, eq, val, tr)


@dataclass
class HoodLossResult:
    he_total: float       # pérdida de presión total de entrada [Pa]
    SPh: float            # presión estática de campana (magnitud) [Pa]
    VPd: float
    Ce_effective: float
    trace: Trace


def hood_entry_loss(entry: HoodEntry, Q: float, duct_area: float, rho: float, hood_id: str = "") -> HoodLossResult:
    """Pérdida de entrada y presión estática de campana."""
    tr = Trace()
    Vd = Q / duct_area
    VPd = 0.5 * rho * Vd ** 2
    he = entry.Fh * VPd
    parts = [f"{n(entry.Fh)}·{n(VPd)}"]
    if entry.kind == "slot":
        if not entry.slot_area or entry.slot_area <= 0:
            raise HoodError("Para campanas ranuradas indique el área total de ranuras")
        Vs = Q / entry.slot_area
        VPs = 0.5 * rho * Vs ** 2
        he_s = entry.Fs * VPs
        he += he_s
        parts.insert(0, f"{n(entry.Fs)}·{n(VPs)}")
        if entry.plenum_loss:
            he += VPs
            parts.append(f"{n(VPs)} (energía cinética de ranura perdida en el pleno)")
        tr.add(MODULE, f"Pérdida de entrada compuesta {hood_id}", "he = Fs·VPs + Fd·VPd" + (" + VPs" if entry.plenum_loss else ""),
               [("Fs", entry.Fs, "-", "Factor de ranura"), ("VPs", VPs, "Pa", "Presión de velocidad en ranura"),
                ("Fd", entry.Fh, "-", "Factor de entrada al ducto"), ("VPd", VPd, "Pa", "Presión de velocidad del ducto")],
               "he = " + " + ".join(parts), he, "Pa", entry.source,
               kind=KIND_HYPOTHESIS if entry.plenum_loss else "Calculado")
    else:
        tr.add(MODULE, f"Pérdida de entrada {hood_id}", "he = Fh·VPd",
               [("Fh", entry.Fh, "-", "Factor de pérdida de entrada"), ("VPd", VPd, "Pa", "ρ·V²/2 en el ducto")],
               "he = " + parts[0], he, "Pa", entry.source)
    SPh = he + VPd
    tr.add(MODULE, f"Presión estática de campana {hood_id}", "|SPh| = he + VPd",
           [("he", he, "Pa", ""), ("VPd", VPd, "Pa", "Aceleración desde el reposo")], f"|SPh| = {n(he)} + {n(VPd)}",
           SPh, "Pa", SRC_ACGIH_ENTRY)
    ce = math.sqrt(VPd / SPh) if SPh > 0 else float("nan")
    return HoodLossResult(he, SPh, VPd, ce, tr)
