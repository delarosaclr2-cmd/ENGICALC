"""Propiedades del aire húmedo (relaciones de ASHRAE Handbook — Fundamentals, cap. 1).

Unidades: temperatura en °C, presión en Pa, humedad absoluta W en kg agua/kg aire seco,
entalpía en kJ/kg de aire seco.

- Presión de saturación: Hyland y Wexler (1983), sobre agua líquida (0–200 °C) y
  sobre hielo (−100–0 °C), ecuaciones 5 y 6 de ASHRAE.
- W = 0.621945·pw/(p − pw)
- h = 1.006·t + W·(2501 + 1.86·t)
- v = 287.042·(t + 273.15)·(1 + 1.607858·W)/p
- Bulbo húmedo termodinámico: ecuación de balance de ASHRAE (resuelta por bisección).

No se aplica el factor de mejora f (≈ 1.004); el error que introduce es del orden
de 0.4 % en W, aceptable para cálculos de proceso.
"""
from __future__ import annotations

import math

from .constantes import CP_AIRE, CP_VAPOR, EPSILON_AGUA_AIRE, H_VAPORIZACION_0C, T_CERO_K

# Coeficientes de Hyland-Wexler (ASHRAE Fundamentals, cap. 1, ec. 5 y 6)
_C1, _C2, _C3, _C4, _C5, _C6, _C7 = (-5.6745359e3, 6.3925247, -9.6778430e-3, 6.2215701e-7,
                                     2.0747825e-9, -9.4840240e-13, 4.1635019)
_C8, _C9, _C10, _C11, _C12, _C13 = (-5.8002206e3, 1.3914993, -4.8640239e-2, 4.1764768e-5,
                                    -1.4452093e-8, 6.5459673)


def presion_saturacion(t_c: float) -> float:
    """Presión de saturación del vapor de agua [Pa] a t_c [°C], válida de −100 a 200 °C."""
    if not -100.0 <= t_c <= 200.0:
        raise ValueError("Temperatura fuera del intervalo de la correlación (−100 a 200 °C).")
    t = t_c + T_CERO_K
    if t_c < 0.0:
        ln_p = _C1 / t + _C2 + _C3 * t + _C4 * t ** 2 + _C5 * t ** 3 + _C6 * t ** 4 + _C7 * math.log(t)
    else:
        ln_p = _C8 / t + _C9 + _C10 * t + _C11 * t ** 2 + _C12 * t ** 3 + _C13 * math.log(t)
    return math.exp(ln_p)


def humedad_por_presion_vapor(pw: float, p: float) -> float:
    if not 0.0 <= pw < p:
        raise ValueError("La presión de vapor debe ser menor que la presión total.")
    return EPSILON_AGUA_AIRE * pw / (p - pw)


def presion_vapor_por_humedad(w: float, p: float) -> float:
    if w < 0:
        raise ValueError("La humedad absoluta no puede ser negativa.")
    return p * w / (EPSILON_AGUA_AIRE + w)


def humedad_saturacion(t_c: float, p: float) -> float:
    pws = presion_saturacion(t_c)
    if pws >= p:
        raise ValueError(f"A {t_c:.1f} °C el agua hierve a la presión dada; el aire no puede saturarse.")
    return humedad_por_presion_vapor(pws, p)


def humedad_por_hr(t_c: float, hr_pct: float, p: float) -> float:
    if not 0.0 <= hr_pct <= 100.0:
        raise ValueError("La humedad relativa debe estar entre 0 y 100 %.")
    return humedad_por_presion_vapor(hr_pct / 100.0 * presion_saturacion(t_c), p)


def hr_por_humedad(t_c: float, w: float, p: float) -> float:
    """Humedad relativa en % (puede salir > 100 si el estado es imposible: sobresaturado)."""
    return 100.0 * presion_vapor_por_humedad(w, p) / presion_saturacion(t_c)


def entalpia(t_c: float, w: float) -> float:
    return CP_AIRE * t_c + w * (H_VAPORIZACION_0C + CP_VAPOR * t_c)


def calor_humedo(w: float) -> float:
    """Calor específico del aire húmedo por kg de aire seco [kJ/(kg·K)]."""
    return CP_AIRE + CP_VAPOR * w


def volumen_especifico(t_c: float, w: float, p: float) -> float:
    """m³ de aire húmedo por kg de aire seco."""
    return 287.042 * (t_c + T_CERO_K) * (1.0 + 1.607858 * w) / p


def densidad_aire_humedo(t_c: float, w: float, p: float) -> float:
    return (1.0 + w) / volumen_especifico(t_c, w, p)


def _biseccion(f, a: float, b: float, tol: float = 1e-7, iter_max: int = 200) -> float:
    fa, fb = f(a), f(b)
    if fa == 0:
        return a
    if fb == 0:
        return b
    if fa * fb > 0:
        raise ValueError("No hay cambio de signo en el intervalo de búsqueda.")
    for _ in range(iter_max):
        m = 0.5 * (a + b)
        fm = f(m)
        if fm == 0 or (b - a) < tol:
            return m
        if fa * fm < 0:
            b, fb = m, fm
        else:
            a, fa = m, fm
    return 0.5 * (a + b)


def punto_rocio(w: float, p: float) -> float:
    """Temperatura de rocío [°C] para una humedad absoluta y presión total."""
    pw = presion_vapor_por_humedad(w, p)
    if pw <= 0:
        raise ValueError("Aire seco: no tiene punto de rocío.")
    return _biseccion(lambda t: presion_saturacion(t) - pw, -100.0, 200.0)


def bulbo_humedo(t_c: float, w: float, p: float) -> float:
    """Temperatura de bulbo húmedo termodinámico [°C] (ASHRAE, balance sobre agua líquida)."""
    if w < 0:
        raise ValueError("Humedad absoluta negativa.")

    def residuo(tw: float) -> float:
        ws = humedad_saturacion(tw, p)
        w_calc = ((2501.0 - 2.326 * tw) * ws - 1.006 * (t_c - tw)) / (2501.0 + 1.86 * t_c - 4.186 * tw)
        return w_calc - w

    limite_inf = max(-60.0, punto_rocio(w, p) - 1.0) if w > 0 else -60.0
    limite_sup = min(t_c, temperatura_ebullicion(p) - 0.05)
    return _biseccion(residuo, limite_inf, limite_sup)


def temperatura_ebullicion(p: float) -> float:
    """Temperatura [°C] a la que la presión de saturación del agua iguala p [Pa]."""
    return _biseccion(lambda t: presion_saturacion(t) - p, -100.0, 200.0)


def calor_latente(t_c: float) -> float:
    """Calor latente aproximado [kJ/kg] coherente con las entalpías de ASHRAE: 2501 − 2.326·t."""
    return H_VAPORIZACION_0C - 2.326 * t_c


def humedad_por_bulbo_humedo(t_c: float, t_bh: float, p: float) -> float:
    """Humedad absoluta a partir de bulbo seco y bulbo húmedo (ASHRAE, sobre agua líquida)."""
    if t_bh > t_c:
        raise ValueError("El bulbo húmedo no puede ser mayor que el bulbo seco.")
    ws = humedad_saturacion(t_bh, p)
    return ((2501.0 - 2.326 * t_bh) * ws - 1.006 * (t_c - t_bh)) / (2501.0 + 1.86 * t_c - 4.186 * t_bh)


def entalpia_saturacion(t_c: float, p: float) -> float:
    return entalpia(t_c, humedad_saturacion(t_c, p))
