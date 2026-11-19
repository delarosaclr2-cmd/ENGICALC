"""Relaciones de presión en sistemas de aire.

Convención de signos (presiones manométricas referidas a la atmósfera local):
* Presión de velocidad   VP = ρ·V²/2 (siempre ≥ 0)
* Presión total          TP = SP + VP  (en una misma sección)
* En el lado de succión de un sistema de extracción TP y SP son negativas.
* Las pérdidas reducen la presión TOTAL en el sentido del flujo; la presión
  estática puede subir o bajar por cambios de velocidad (conversión VP↔SP).

Presiones del ventilador (AMCA 210 / ASHRAE 51; ACGIH):
* Presión total del ventilador   FTP = TP_salida − TP_entrada
* Presión estática del ventilador FSP = FTP − VP_salida = SP_salida − TP_entrada
  (equivalente a la forma ACGIH: FSP = SP_sal − SP_ent − VP_ent)

Imperial con densidad no estándar: VP[in.wg] = ρ·V²/2 convertido; la forma
VP = (V/4005)² solo es válida para 0.075 lb/ft³ y no se usa internamente.
"""
from __future__ import annotations

from .constants import IN_WG_60F, FPM, LBM, FT


def velocity_pressure(rho: float, V: float) -> float:
    return 0.5 * rho * V * V


def total_pressure(sp: float, vp: float) -> float:
    return sp + vp


def static_from_total(tp: float, vp: float) -> float:
    return tp - vp


def velocity_from_vp(vp: float, rho: float) -> float:
    return (2.0 * vp / rho) ** 0.5


def fan_static_pressure(ftp: float, vp_outlet: float) -> float:
    """FSP = FTP − VP_salida (AMCA)."""
    return ftp - vp_outlet


def vp_ip_standard(V_fpm: float) -> float:
    """VP [in.wg] = (V/4005)²: SOLO para aire estándar 0.075 lb/ft³ (referencia y pruebas)."""
    return (V_fpm / 4005.0) ** 2


def vp_ip_general(V_fpm: float, rho_lb_ft3: float) -> float:
    """VP [in.wg] para cualquier densidad, calculado desde SI."""
    rho = rho_lb_ft3 * LBM / FT ** 3
    V = V_fpm * FPM
    return velocity_pressure(rho, V) / IN_WG_60F
