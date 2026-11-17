"""Fórmulas de mecánica de fluidos compartidas.

Todas en SI: m, s, kg, Pa, W. Estas funciones sustituyen las copias que había
en seis archivos originales (diámetro por caudal), cuatro (potencia de
ventilador) y tres (Darcy).
"""
from __future__ import annotations

import math

from .constantes import R_AIRE_SECO, T_CERO_K


def area_circular(diametro: float) -> float:
    return math.pi * diametro ** 2 / 4.0


def diametro_por_caudal(caudal_m3s: float, velocidad: float) -> float:
    """Diámetro interior [m] para conducir ``caudal_m3s`` a ``velocidad`` (continuidad Q = A·v)."""
    if caudal_m3s <= 0 or velocidad <= 0:
        raise ValueError("Caudal y velocidad deben ser positivos.")
    return math.sqrt(4.0 * caudal_m3s / (math.pi * velocidad))


def velocidad_media(caudal_m3s: float, diametro: float) -> float:
    return caudal_m3s / area_circular(diametro)


def reynolds(densidad: float, velocidad: float, diametro: float, viscosidad_dinamica: float) -> float:
    return densidad * velocidad * diametro / viscosidad_dinamica


def viscosidad_aire_sutherland(t_c: float) -> float:
    """Viscosidad dinámica del aire [Pa·s] por la ley de Sutherland (μ0 = 1.716e-5 Pa·s a 273.15 K, S = 110.4 K)."""
    t = t_c + T_CERO_K
    return 1.716e-5 * (t / 273.15) ** 1.5 * (273.15 + 110.4) / (t + 110.4)


def densidad_aire_seco(presion_pa: float, t_c: float) -> float:
    return presion_pa / (R_AIRE_SECO * (t_c + T_CERO_K))


def friccion_swamee_jain(re: float, rugosidad_relativa: float) -> float:
    """Aproximación explícita de Swamee-Jain (régimen turbulento). Se usa como valor inicial."""
    return 0.25 / math.log10(rugosidad_relativa / 3.7 + 5.74 / re ** 0.9) ** 2


def factor_friccion_darcy(re: float, rugosidad_relativa: float) -> tuple[float, str]:
    """Factor de fricción de Darcy y régimen.

    - Laminar (Re < 2 300): f = 64/Re.
    - Turbulento (Re ≥ 4 000): ecuación de Colebrook-White, resuelta por iteración.
    - Transición (2 300 ≤ Re < 4 000): se usa Colebrook (conservador) y se informa.
    """
    if re <= 0:
        raise ValueError("Reynolds debe ser positivo.")
    if rugosidad_relativa < 0:
        raise ValueError("La rugosidad relativa no puede ser negativa.")
    if re < 2300:
        return 64.0 / re, "laminar"
    f = friccion_swamee_jain(max(re, 4000.0), rugosidad_relativa)
    for _ in range(100):
        nuevo = (-2.0 * math.log10(rugosidad_relativa / 3.7 + 2.51 / (re * math.sqrt(f)))) ** -2
        if abs(nuevo - f) < 1e-12:
            f = nuevo
            break
        f = nuevo
    return f, ("transición" if re < 4000 else "turbulento")


def perdida_darcy(f: float, longitud: float, diametro: float, densidad: float, velocidad: float) -> float:
    """Pérdida de presión por fricción [Pa]: ΔP = f·(L/D)·ρ·v²/2 (f de Darcy)."""
    return f * (longitud / diametro) * densidad * velocidad ** 2 / 2.0


def perdida_menor(k_total: float, densidad: float, velocidad: float) -> float:
    """Pérdida por accesorios [Pa]: ΔP = ΣK·ρ·v²/2."""
    return k_total * densidad * velocidad ** 2 / 2.0


def potencia_incompresible(delta_p: float, caudal_m3s: float, eficiencia: float) -> float:
    """Potencia al eje [W] de un ventilador o bomba: P = ΔP·Q/η (fluido incompresible)."""
    if not 0 < eficiencia <= 1:
        raise ValueError("La eficiencia debe estar entre 0 y 1.")
    return delta_p * caudal_m3s / eficiencia


def potencia_adiabatica(p1: float, caudal1_m3s: float, p2: float, k: float = 1.4,
                        eficiencia: float = 1.0) -> float:
    """Potencia al eje [W] para comprimir gas ideal de p1 a p2 (isentrópica / η).

    P = k/(k−1)·p1·Q1·[(p2/p1)^((k−1)/k) − 1]/η, con Q1 caudal a condiciones de succión.
    """
    if p1 <= 0 or p2 <= 0:
        raise ValueError("Las presiones absolutas deben ser positivas.")
    if not 0 < eficiencia <= 1:
        raise ValueError("La eficiencia debe estar entre 0 y 1.")
    return k / (k - 1.0) * p1 * caudal1_m3s * ((p2 / p1) ** ((k - 1.0) / k) - 1.0) / eficiencia


def potencia_isotermica(p1: float, caudal1_m3s: float, p2: float) -> float:
    """Potencia isotérmica ideal [W]: P = p1·Q1·ln(p2/p1)."""
    if p1 <= 0 or p2 <= 0:
        raise ValueError("Las presiones absolutas deben ser positivas.")
    return p1 * caudal1_m3s * math.log(p2 / p1)


def media_logaritmica(dt1: float, dt2: float) -> float:
    """Diferencia media logarítmica de temperatura."""
    if dt1 <= 0 or dt2 <= 0:
        raise ValueError("Las diferencias de temperatura deben ser positivas.")
    if abs(dt1 - dt2) < 1e-9:
        return dt1
    return (dt1 - dt2) / math.log(dt1 / dt2)
