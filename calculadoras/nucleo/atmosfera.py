"""Presión atmosférica según la altitud.

Ecuación de la atmósfera estándar en la forma de ASHRAE Fundamentals
(cap. 1, ec. 3):  p = 101.325 · (1 − 2.25577·10⁻⁵ · Z)^5.2559  [kPa, Z en m].

Las versiones originales usaban 101.3 kPa fijo; a 2 240 m (CDMX) la presión
estándar es ≈ 77 kPa, lo que cambia potencias de vacío, densidades y
psicrometría.
"""
from __future__ import annotations

from .constantes import P_ATM_NORMAL


def presion_por_altitud(altitud_m: float) -> float:
    """Presión atmosférica estándar en Pa para una altitud en metros (−500 a 11 000 m)."""
    if not -500.0 <= altitud_m <= 11000.0:
        raise ValueError("La altitud debe estar entre −500 y 11 000 m (troposfera).")
    return P_ATM_NORMAL * (1.0 - 2.25577e-5 * altitud_m) ** 5.2559
