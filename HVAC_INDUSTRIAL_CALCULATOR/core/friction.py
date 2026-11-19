"""Número de Reynolds, factor de fricción de Darcy y pérdidas Darcy-Weisbach.

IMPORTANTE: el factor de Darcy (f_D) NO es el factor de Fanning (f_F):
    f_D = 4·f_F
Todas las funciones de este módulo devuelven el factor de **Darcy**.

Correlaciones implementadas:
* Laminar (Re < 2300):            f = 64/Re
* Colebrook-White (turbulento):   1/√f = −2·log10(ε/(3.7·D) + 2.51/(Re·√f))  (implícita, iterativa)
* Swamee-Jain (explícita):        f = 0.25/[log10(ε/(3.7·D) + 5.74/Re^0.9)]²
      validez declarada: 10⁻⁶ ≤ ε/D ≤ 10⁻², 5000 ≤ Re ≤ 10⁸ (error ≈ ±1 % frente a Colebrook)
* Churchill (1977), válida en todos los regímenes (uso de contraste):
      f = 8·[(8/Re)¹² + (A + B)^(−1.5)]^(1/12)
      A = [2.457·ln(1/((7/Re)^0.9 + 0.27·ε/D))]¹⁶,  B = (37530/Re)¹⁶
* Altshul-Tsal (ASHRAE Fundamentals, cap. Duct Design), contraste:
      f' = 0.11·(ε/D + 68/Re)^0.25;  f = f' si f' ≥ 0.018, si no f = 0.85·f' + 0.0028

Régimen transicional (2300 ≤ Re ≤ 4000): el flujo es inestable y ninguna
correlación es fiable. El programa adopta, como hipótesis conservadora,
f = max(64/Re, f_Colebrook) y emite una advertencia.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from . import constants as C

SRC_DW = "Ecuación de Darcy-Weisbach (ASHRAE Fundamentals, cap. Duct Design)"
SRC_COLEBROOK = "Colebrook, C. F. (1939), J. Inst. Civil Eng. 11"
SRC_SJ = "Swamee, P. K. y Jain, A. K. (1976), J. Hydraulics Div. ASCE 102"
SRC_CHURCHILL = "Churchill, S. W. (1977), Chemical Engineering 84(24)"
SRC_ALTSHUL = "Altshul-Tsal, ASHRAE Handbook—Fundamentals, cap. Duct Design"

REGIME_LAMINAR = "laminar"
REGIME_TRANSITIONAL = "transicional"
REGIME_TURBULENT = "turbulento"


class FrictionError(ValueError):
    pass


def reynolds(rho: float, V: float, Dh: float, mu: float) -> float:
    """Re = ρ·V·Dh/μ."""
    if mu <= 0:
        raise FrictionError("La viscosidad debe ser positiva")
    if Dh <= 0:
        raise FrictionError("El diámetro hidráulico debe ser positivo")
    return rho * abs(V) * Dh / mu


def f_laminar(Re: float) -> float:
    if Re <= 0:
        raise FrictionError("Re debe ser positivo")
    return 64.0 / Re


def f_swamee_jain(Re: float, rel_rough: float) -> float:
    if Re <= 0:
        raise FrictionError("Re debe ser positivo")
    return 0.25 / math.log10(rel_rough / 3.7 + 5.74 / Re ** 0.9) ** 2


def f_colebrook(Re: float, rel_rough: float, tol: float = 1e-12, max_iter: int = 100) -> float:
    """Colebrook-White por iteración de punto fijo sobre x = 1/√f (arranque Swamee-Jain).

    La iteración converge de forma monótona y rápida para Re > 2000.
    """
    if Re <= 0:
        raise FrictionError("Re debe ser positivo")
    x = 1.0 / math.sqrt(f_swamee_jain(Re, rel_rough))
    for _ in range(max_iter):
        x_new = -2.0 * math.log10(rel_rough / 3.7 + 2.51 * x / Re)
        if abs(x_new - x) < tol * abs(x_new):
            x = x_new
            break
        x = x_new
    else:
        raise FrictionError("Colebrook no convergió")
    return 1.0 / x ** 2


def f_churchill(Re: float, rel_rough: float) -> float:
    A = (2.457 * math.log(1.0 / ((7.0 / Re) ** 0.9 + 0.27 * rel_rough))) ** 16
    B = (37530.0 / Re) ** 16
    return 8.0 * ((8.0 / Re) ** 12 + (A + B) ** -1.5) ** (1.0 / 12.0)


def f_altshul_tsal(Re: float, rel_rough: float) -> float:
    fp = 0.11 * (rel_rough + 68.0 / Re) ** 0.25
    return fp if fp >= 0.018 else 0.85 * fp + 0.0028


def fanning_from_darcy(f_darcy: float) -> float:
    """f_Fanning = f_Darcy/4."""
    return f_darcy / 4.0


def darcy_from_fanning(f_fanning: float) -> float:
    return 4.0 * f_fanning


@dataclass
class FrictionResult:
    f: float
    Re: float
    rel_rough: float
    regime: str
    method: str
    warnings: list[str] = field(default_factory=list)
    f_swamee_jain: float | None = None


METHODS = ("colebrook", "swamee_jain", "churchill", "altshul_tsal")


def darcy_factor(Re: float, rel_rough: float, method: str = "colebrook") -> FrictionResult:
    """Factor de fricción de Darcy con identificación de régimen."""
    if rel_rough < 0:
        raise FrictionError("La rugosidad relativa no puede ser negativa")
    warnings: list[str] = []
    if Re < C.RE_LAMINAR_MAX:
        f = f_laminar(Re)
        return FrictionResult(f, Re, rel_rough, REGIME_LAMINAR, "laminar 64/Re", warnings)
    if Re <= C.RE_TURBULENT_MIN:
        f_turb = f_colebrook(Re, rel_rough)
        f = max(f_laminar(Re), f_turb)
        warnings.append(f"Re = {Re:.0f} en régimen transicional (2300–4000): factor de fricción incierto; "
                        "se adopta el mayor entre laminar y Colebrook (hipótesis conservadora).")
        return FrictionResult(f, Re, rel_rough, REGIME_TRANSITIONAL, "transicional (conservador)", warnings)
    if method == "swamee_jain":
        f = f_swamee_jain(Re, rel_rough)
        if not (1e-6 <= rel_rough <= 1e-2) or not (5000 <= Re <= 1e8):
            warnings.append("Swamee-Jain fuera de su rango declarado de validez (1e-6 ≤ ε/D ≤ 1e-2; 5000 ≤ Re ≤ 1e8).")
        name = "Swamee-Jain"
    elif method == "churchill":
        f = f_churchill(Re, rel_rough)
        name = "Churchill"
    elif method == "altshul_tsal":
        f = f_altshul_tsal(Re, rel_rough)
        name = "Altshul-Tsal"
    else:
        f = f_colebrook(Re, rel_rough)
        name = "Colebrook-White"
    if rel_rough > 0.05:
        warnings.append("Rugosidad relativa > 0.05: fuera del rango del diagrama de Moody.")
    return FrictionResult(f, Re, rel_rough, REGIME_TURBULENT, name, warnings, f_swamee_jain(Re, rel_rough))


def darcy_weisbach(f: float, L: float, Dh: float, rho: float, V: float) -> float:
    """ΔP = f·(L/Dh)·ρV²/2  [Pa]."""
    if Dh <= 0:
        raise FrictionError("Dh debe ser positivo")
    return f * (L / Dh) * 0.5 * rho * V * V
