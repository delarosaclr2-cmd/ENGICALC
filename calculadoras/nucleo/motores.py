"""Tamaños comerciales de motores eléctricos.

- NEMA MG 1: potencias nominales normalizadas en HP para motores de inducción.
- IEC 60072-1: serie de potencias nominales en kW.

La selección devuelve el menor tamaño normalizado que es mayor o igual a la
potencia requerida en la flecha. No sustituye la selección del fabricante
(factor de servicio, ciclo de trabajo, arranque con carga, altitud y temperatura).
"""
from __future__ import annotations

NEMA_HP = (0.25, 0.33, 0.5, 0.75, 1, 1.5, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 100, 125, 150,
           200, 250, 300, 350, 400, 450, 500)
IEC_KW = (0.18, 0.25, 0.37, 0.55, 0.75, 1.1, 1.5, 2.2, 3, 4, 5.5, 7.5, 11, 15, 18.5, 22, 30, 37, 45, 55, 75, 90,
          110, 132, 160, 200, 250, 315, 355, 400)


def siguiente(serie: tuple, requerido: float) -> float | None:
    """Menor valor de ``serie`` ≥ ``requerido`` (con tolerancia de redondeo); None si excede la serie."""
    for valor in serie:
        if valor >= requerido * (1 - 1e-9):
            return valor
    return None


def motor_nema_hp(hp: float) -> float | None:
    return siguiente(NEMA_HP, hp)


def motor_iec_kw(kw: float) -> float | None:
    return siguiente(IEC_KW, kw)
