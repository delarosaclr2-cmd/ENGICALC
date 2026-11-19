"""Pérdidas locales en accesorios: ΔP = K·ρ·V_ref²/2.

Cada coeficiente K está asociado a una **sección de referencia** (y por tanto a una
velocidad de referencia). El programa calcula V_ref = Q/A_ref, donde A_ref es el
área propia del tramo salvo que el accesorio indique otra (por ejemplo, el área
de ranura, el lado pequeño de una reducción, etc.).

Coeficientes calculados por fórmula (fuentes verificables):
* Expansión brusca (Borda-Carnot):       K₁ = (1 − A₁/A₂)²            ref. sección aguas arriba (pequeña)
* Contracción brusca (Crane TP-410):     K₂ = 0.5·(1 − A₂/A₁)          ref. sección pequeña
* Difusor cónico (Crane TP-410):         θ ≤ 45°: K₁ = 2.6·sen(θ/2)·(1 − β²)²; θ > 45°: K₁ = (1 − β²)²
* Reducción cónica (Crane TP-410):       θ ≤ 45°: K₂ = 0.8·sen(θ/2)·(1 − β²); θ > 45°: K₂ = 0.5·(1 − β²)·√sen(θ/2)
  (β² = A_pequeña/A_grande)
* Codo liso (Idelchik, Diagrama 6-1):    ζ = A1·B1·C1·k_Re + ζ_fricción
      A1 = 0.9·sen δ (δ ≤ 70°), 1.0 (δ = 90°), 0.7 + 0.35·δ/90 (δ ≥ 100°)
      B1 = 0.21/(R/D)^2.5 (0.5 ≤ R/D ≤ 1), 0.21/√(R/D) (R/D > 1)
      C1 = 1 (sección circular o cuadrada)
      ζ_fricción = 0.0175·f·(R/D)·δ  (fricción a lo largo del eje del codo)
* Descarga libre a la atmósfera: K = 1 (pérdida de toda la energía cinética).

Los coeficientes fijos de la biblioteca (por ejemplo, entradas de ramal ACGIH)
se toman de ``database/fittings.json`` con su fuente y estado de verificación.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

SRC_BORDA = "Expansión brusca: Borda-Carnot (balance de cantidad de movimiento)"
SRC_CRANE = "Crane Co., Technical Paper No. 410 (fórmulas de reducciones y expansiones)"
SRC_IDELCHIK = "Idelchik, I. E., Handbook of Hydraulic Resistance, Diagrama 6-1 (codos lisos)"
SRC_EXIT = "Pérdida en descarga libre: energía cinética no recuperada (K = 1 referido a la salida)"


class FittingError(ValueError):
    pass


def k_sudden_expansion(A_small: float, A_large: float) -> float:
    if A_large <= A_small:
        raise FittingError("En una expansión el área aguas abajo debe ser mayor")
    return (1.0 - A_small / A_large) ** 2


def k_sudden_contraction(A_small: float, A_large: float) -> float:
    if A_large <= A_small:
        raise FittingError("En una contracción el área aguas arriba debe ser mayor")
    return 0.5 * (1.0 - A_small / A_large)


def k_gradual_expansion(theta_deg: float, A_small: float, A_large: float) -> float:
    beta2 = A_small / A_large
    if beta2 >= 1:
        raise FittingError("Relación de áreas inválida para expansión")
    th = math.radians(theta_deg)
    if theta_deg <= 45:
        return 2.6 * math.sin(th / 2) * (1 - beta2) ** 2
    return (1 - beta2) ** 2


def k_gradual_contraction(theta_deg: float, A_small: float, A_large: float) -> float:
    beta2 = A_small / A_large
    if beta2 >= 1:
        raise FittingError("Relación de áreas inválida para contracción")
    th = math.radians(theta_deg)
    if theta_deg <= 45:
        return 0.8 * math.sin(th / 2) * (1 - beta2)
    return 0.5 * (1 - beta2) * math.sqrt(math.sin(th / 2))


def k_bend_idelchik(angle_deg: float, r_over_d: float, Re: float | None = None, f_darcy: float | None = None,
                    include_friction: bool = True) -> tuple[float, list[str]]:
    """Coeficiente de codo liso (Idelchik, Diagrama 6-1). Devuelve (K, advertencias)."""
    warns: list[str] = []
    if not (0.5 <= r_over_d <= 3.0):
        warns.append(f"R/D = {r_over_d} fuera del rango de la correlación de Idelchik (0.5–3.0).")
    rd = min(max(r_over_d, 0.5), 3.0)
    d = angle_deg
    if d <= 70:
        A1 = 0.9 * math.sin(math.radians(d))
    elif d >= 100:
        A1 = 0.7 + 0.35 * d / 90.0
    else:  # interpolación lineal 70–90–100
        a70 = 0.9 * math.sin(math.radians(70))
        a100 = 0.7 + 0.35 * 100 / 90.0
        A1 = a70 + (1.0 - a70) * (d - 70) / 20.0 if d <= 90 else 1.0 + (a100 - 1.0) * (d - 90) / 10.0
    B1 = 0.21 / rd ** 2.5 if rd <= 1.0 else 0.21 / math.sqrt(rd)
    k_loc = A1 * B1
    if Re is not None and Re < 3e5 and 0.7 <= rd < 3.0:
        k_re = 11.5 / Re ** 0.19 if Re >= 4e4 else 11.5 / 4e4 ** 0.19
        k_loc *= max(k_re, 1.0)
        if Re < 4e4:
            warns.append("Re < 4·10⁴: corrección por Reynolds del codo extrapolada.")
    k_fr = 0.0175 * (f_darcy or 0.0) * rd * d if include_friction and f_darcy else 0.0
    return k_loc + k_fr, warns


def fitting_loss(K: float, rho: float, V_ref: float) -> float:
    """ΔP = K·ρ·V_ref²/2 [Pa]."""
    return K * 0.5 * rho * V_ref * V_ref


@dataclass
class FittingDef:
    """Entrada de la biblioteca de accesorios."""
    id: str
    name: str
    category: str
    mode: str = "fixed"            # 'fixed' | 'formula' | 'user'
    K: float | None = None
    formula: str | None = None     # 'bend', 'sudden_expansion', 'sudden_contraction', 'diffuser', 'reducer', 'exit'
    params: dict = field(default_factory=dict)
    reference: str = "propia"      # descripción de la sección de referencia
    source: str = ""
    status: str = "verificar"      # 'fórmula verificable' | 'verificar' | 'dato del usuario'
    notes: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "FittingDef":
        known = {k: d[k] for k in cls.__dataclass_fields__ if k in d}
        return cls(**known)


@dataclass
class FittingInstance:
    """Accesorio colocado en un tramo."""
    fitting_id: str
    qty: float = 1.0
    K_override: float | None = None
    params: dict = field(default_factory=dict)     # p. ej. angle, R_D, A_other_m2, theta
    area_ref_m2: float | None = None               # None → área del tramo
    note: str = ""

    def to_dict(self) -> dict:
        return {"fitting_id": self.fitting_id, "qty": self.qty, "K_override": self.K_override,
                "params": dict(self.params), "area_ref_m2": self.area_ref_m2, "note": self.note}

    @classmethod
    def from_dict(cls, d: dict) -> "FittingInstance":
        return cls(d.get("fitting_id", ""), d.get("qty", 1.0), d.get("K_override"), dict(d.get("params", {}) or {}),
                   d.get("area_ref_m2"), d.get("note", ""))


@dataclass
class FittingEval:
    name: str
    category: str
    K: float
    qty: float
    area_ref: float
    V_ref: float
    dp: float
    source: str
    status: str
    warnings: list[str] = field(default_factory=list)


def evaluate_fitting(inst: FittingInstance, fdef: FittingDef | None, Q: float, seg_area: float, rho: float,
                     Re: float | None, f_darcy: float | None) -> FittingEval:
    """Calcula K y ΔP de un accesorio instalado."""
    warns: list[str] = []
    name = fdef.name if fdef else inst.fitting_id
    cat = fdef.category if fdef else "Usuario"
    source = fdef.source if fdef else "Dato del usuario"
    status = fdef.status if fdef else "dato del usuario"
    area_ref = inst.area_ref_m2 if inst.area_ref_m2 else seg_area
    params = dict(fdef.params) if fdef else {}
    params.update(inst.params or {})
    if inst.K_override is not None:
        K = float(inst.K_override)
        source = (source + " — K indicado por el usuario") if fdef else "K indicado por el usuario"
        status = "dato del usuario"
    elif fdef is None:
        raise FittingError(f"Accesorio '{inst.fitting_id}' no existe en la biblioteca y no tiene K")
    elif fdef.mode == "formula":
        fm = fdef.formula
        if fm == "bend":
            K, w = k_bend_idelchik(float(params.get("angle", 90)), float(params.get("R_D", 1.5)), Re, f_darcy)
            warns += w
        elif fm == "exit":
            K = 1.0
        elif fm in ("sudden_expansion", "diffuser"):
            A_other = float(params.get("A_other_m2", 0) or 0)
            if A_other <= 0:
                raise FittingError(f"{name}: indique el área de la sección mayor (A_other_m2)")
            A_s, A_l = min(seg_area, A_other), max(seg_area, A_other)
            K = k_sudden_expansion(A_s, A_l) if fm == "sudden_expansion" else \
                k_gradual_expansion(float(params.get("theta", 30)), A_s, A_l)
            area_ref = A_s
        elif fm in ("sudden_contraction", "reducer"):
            A_other = float(params.get("A_other_m2", 0) or 0)
            if A_other <= 0:
                raise FittingError(f"{name}: indique el área de la sección mayor (A_other_m2)")
            A_s, A_l = min(seg_area, A_other), max(seg_area, A_other)
            K = k_sudden_contraction(A_s, A_l) if fm == "sudden_contraction" else \
                k_gradual_contraction(float(params.get("theta", 30)), A_s, A_l)
            area_ref = A_s
        else:
            raise FittingError(f"Fórmula desconocida: {fm}")
    elif fdef.mode == "user" or fdef.K is None:
        raise FittingError(f"El accesorio '{name}' requiere que el usuario indique K y su fuente")
    else:
        K = float(fdef.K)
    if K < 0:
        warns.append(f"{name}: K negativo (posible en uniones con aporte de energía del flujo principal); revisar.")
    V_ref = Q / area_ref
    dp = inst.qty * fitting_loss(K, rho, V_ref)
    return FittingEval(name, cat, K, inst.qty, area_ref, V_ref, dp, source, status, warns)
