"""Leyes de semejanza de ventiladores (AMCA 99 / ASHRAE HVAC Systems and Equipment).

Para ventiladores geométricamente semejantes operando en puntos de
funcionamiento homólogos (mismo punto relativo de la curva):

    Q₂ = Q₁·(N₂/N₁)·(D₂/D₁)³
    P₂ = P₁·(N₂/N₁)²·(D₂/D₁)²·(ρ₂/ρ₁)
    W₂ = W₁·(N₂/N₁)³·(D₂/D₁)⁵·(ρ₂/ρ₁)
    η₂ = η₁

Limitaciones: el cambio de diámetro solo es válido dentro de una familia
geométricamente semejante; no incluye efectos de Reynolds, compresibilidad
(relación de presiones > 1.03 aprox.) ni correcciones de rendimiento por tamaño.
La curva escalada no sustituye a la curva certificada del fabricante.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .trace import Trace, n

MODULE = "Selección de ventiladores"
SRC_LAWS = "Leyes de ventiladores — AMCA Publication 99 / ASHRAE Handbook—HVAC Systems and Equipment"


@dataclass
class AffinityResult:
    Q2: float
    P2: float
    W2: float | None
    ratios: dict
    trace: Trace


def affinity(Q1: float, P1: float, W1: float | None, N1: float, N2: float, D1: float = 1.0, D2: float = 1.0,
             rho1: float = 1.2, rho2: float = 1.2) -> AffinityResult:
    if min(N1, N2, D1, D2, rho1, rho2) <= 0:
        raise ValueError("Velocidades, diámetros y densidades deben ser positivos")
    rn, rd, rr = N2 / N1, D2 / D1, rho2 / rho1
    Q2 = Q1 * rn * rd ** 3
    P2 = P1 * rn ** 2 * rd ** 2 * rr
    W2 = W1 * rn ** 3 * rd ** 5 * rr if W1 is not None else None
    tr = Trace()
    tr.add(MODULE, "Ley de semejanza: caudal", "Q₂ = Q₁·(N₂/N₁)·(D₂/D₁)³",
           [("Q₁", Q1, "m³/s", ""), ("N₂/N₁", rn, "-", ""), ("D₂/D₁", rd, "-", "")],
           f"Q₂ = {n(Q1)}·{n(rn)}·{n(rd)}³", Q2, "m³/s", SRC_LAWS)
    tr.add(MODULE, "Ley de semejanza: presión", "P₂ = P₁·(N₂/N₁)²·(D₂/D₁)²·(ρ₂/ρ₁)",
           [("P₁", P1, "Pa", ""), ("ρ₂/ρ₁", rr, "-", "")], f"P₂ = {n(P1)}·{n(rn)}²·{n(rd)}²·{n(rr)}", P2, "Pa", SRC_LAWS)
    if W2 is not None:
        tr.add(MODULE, "Ley de semejanza: potencia", "W₂ = W₁·(N₂/N₁)³·(D₂/D₁)⁵·(ρ₂/ρ₁)",
               [("W₁", W1, "W", "")], f"W₂ = {n(W1)}·{n(rn)}³·{n(rd)}⁵·{n(rr)}", W2, "W", SRC_LAWS)
    return AffinityResult(Q2, P2, W2, {"N": rn, "D": rd, "rho": rr}, tr)


def tip_speed(D_m: float, rpm: float) -> float:
    """Velocidad periférica del rodete U = π·D·N/60 [m/s]."""
    return math.pi * D_m * rpm / 60.0
