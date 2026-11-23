"""Fricción en tubería: Darcy-Weisbach con Colebrook-White (Menon 2005, ecs. 1.25, 4.32-4.33)."""
from __future__ import annotations

import math

RE_LAMINAR = 2100.0      # Menon: laminar R ≤ 2100
RE_TURBULENTO = 4000.0   # Menon: Colebrook para R > 4000


def factor_friccion(re: float, eps_m: float, d_m: float):
    """(f de Darcy, régimen). Laminar: 64/Re. Turbulento y crítico: Colebrook-White resuelta por
    iteración desde Swamee-Jain. En la zona crítica (2100–4000) el valor es incierto: se informa."""
    if re <= 0:
        raise ValueError("Número de Reynolds no positivo")
    if re <= RE_LAMINAR:
        return 64.0 / re, "laminar"
    er = eps_m / d_m
    f = 0.25 / math.log10(er / 3.7 + 5.74 / re ** 0.9) ** 2
    for _ in range(60):
        nuevo = (-2.0 * math.log10(er / 3.7 + 2.51 / (re * math.sqrt(f)))) ** -2
        if abs(nuevo - f) < 1e-12:
            f = nuevo
            break
        f = nuevo
    return f, ("crítico (2100–4000): f incierto" if re < RE_TURBULENTO else "turbulento")


def area(d_m: float) -> float:
    return math.pi / 4.0 * d_m * d_m
