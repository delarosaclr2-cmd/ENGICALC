"""Propiedades de aceites derivados del petróleo (Menon 2005, cap. 6).

Viscosidad contra temperatura: ASTM D341, Menon ecs. 6.13-6.16:
    log log Z = A − B·log T,  Z = ν + 0.7 + C − D,
    C = exp(−1.14883 − 2.65868·ν),  D = exp(−0.0038138 − 12.5645·ν),  T en K, ν en cSt.
Se ajustan A y B con dos puntos (T, ν) de la hoja técnica del aceite.
"""
from __future__ import annotations

import math


def _z(nu):
    return nu + 0.7 + math.exp(-1.14883 - 2.65868 * nu) - math.exp(-0.0038138 - 12.5645 * nu)


def ajustar_walther(t1_k, nu1, t2_k, nu2):
    if nu1 <= 0 or nu2 <= 0 or t1_k == t2_k:
        raise ValueError("Se requieren dos puntos de viscosidad positivos a temperaturas distintas")
    y1, y2 = math.log10(math.log10(_z(nu1))), math.log10(math.log10(_z(nu2)))
    b = (y1 - y2) / (math.log10(t2_k) - math.log10(t1_k))
    a = y1 + b * math.log10(t1_k)
    return a, b


def viscosidad_cst(t_k, a, b):
    z = 10 ** (10 ** (a - b * math.log10(t_k)))
    nu = z - 0.7
    for _ in range(50):                    # corrige C y D (solo importan por debajo de ~2 cSt)
        nuevo = z - 0.7 - math.exp(-1.14883 - 2.65868 * nu) + math.exp(-0.0038138 - 12.5645 * nu)
        if abs(nuevo - nu) < 1e-12:
            break
        nu = nuevo
    return nu
