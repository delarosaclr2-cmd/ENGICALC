"""Mecánica de sólidos a granel compartida (tolva y silo).

- Descarga por orificio: correlación de Beverloo et al. (1961)
  W = C·ρb·√g·(D0 − k·d)^2.5, con C ≈ 0.58 y k ≈ 1.4 (estimación general; 1.5
  para esferas). Válida para sólidos gruesos no cohesivos; para polvos finos
  la descarga real es menor (efecto del aire intersticial).
- Presiones en silo: teoría de Janssen para la parte cilíndrica.
"""
from __future__ import annotations

import math

from .constantes import G

BEVERLOO_C = 0.58
BEVERLOO_K = 1.4


def descarga_beverloo(densidad_aparente: float, diametro_orificio: float, diametro_particula: float,
                      c: float = BEVERLOO_C, k: float = BEVERLOO_K) -> float:
    """Flujo másico [kg/s] por un orificio circular (Beverloo)."""
    if densidad_aparente <= 0 or diametro_orificio <= 0:
        raise ValueError("Densidad y diámetro de orificio deben ser positivos.")
    if diametro_particula < 0:
        raise ValueError("El tamaño de partícula no puede ser negativo.")
    efectivo = diametro_orificio - k * diametro_particula
    if efectivo <= 0:
        raise ValueError("El orificio es demasiado pequeño para el tamaño de partícula (D0 ≤ k·d): habrá arqueo.")
    return c * densidad_aparente * math.sqrt(G) * efectivo ** 2.5


PARTICULA_MINIMA_BEVERLOO_MM = 0.4


def advertencia_beverloo(diametro_particula_mm: float) -> str | None:
    """Advertencia de aplicabilidad de Beverloo según el tamaño de partícula.

    La correlación se obtuvo con sólidos gruesos no cohesivos. Con partículas finas
    (del orden de 0.4–0.5 mm o menores) el aire intersticial frena la descarga y
    Beverloo sobreestima el flujo (Nedderman, *Statics and Kinematics of Granular
    Materials*, 1992; Nedderman y Verghese, IFPRI FRR-02-06).
    """
    if diametro_particula_mm <= 0:
        return ("Tamaño de partícula no capturado: Beverloo se evaluó con d = 0. Si el material es un polvo fino, "
                "el flujo real es MENOR que el calculado.")
    if diametro_particula_mm < PARTICULA_MINIMA_BEVERLOO_MM:
        return (f"Partícula de {diametro_particula_mm:g} mm: Beverloo NO es aplicable a polvos finos "
                f"(< ~{PARTICULA_MINIMA_BEVERLOO_MM:g} mm). El aire intersticial reduce la descarga; el flujo real "
                "puede ser varias veces menor. Use el dato del dosificador o de la válvula, o pruebas.")
    return None


def janssen(profundidad: float, densidad_aparente: float, diametro: float, k: float, mu_pared: float) -> dict:
    """Presiones de Janssen a una profundidad z bajo la superficie del material.

    Devuelve presión horizontal ph, vertical pv, fricción en pared pw [Pa] y la
    fuerza axial de compresión en la pared por unidad de perímetro n [N/m]
    (peso del material soportado por fricción).
    """
    if min(densidad_aparente, diametro, k, mu_pared) <= 0:
        raise ValueError("Densidad, diámetro, K y μ deben ser positivos.")
    if profundidad < 0:
        raise ValueError("La profundidad no puede ser negativa.")
    radio_hidraulico = diametro / 4.0
    gamma = densidad_aparente * G
    z0 = radio_hidraulico / (k * mu_pared)
    factor = 1.0 - math.exp(-profundidad / z0)
    ph = gamma * radio_hidraulico / mu_pared * factor
    pv = ph / k
    pw = mu_pared * ph
    n_axial = radio_hidraulico * (gamma * profundidad - pv)
    return {"ph": ph, "pv": pv, "pw": pw, "n_axial": n_axial, "z0": z0,
            "ph_max": gamma * radio_hidraulico / mu_pared}


def volumen_tronco_cono(diametro_mayor: float, diametro_menor: float, altura: float) -> float:
    return math.pi * altura / 12.0 * (diametro_mayor ** 2 + diametro_mayor * diametro_menor + diametro_menor ** 2)


def volumen_tronco_secciones_semejantes(area_mayor: float, area_menor: float, altura: float) -> float:
    """V = h/3·(A1 + A2 + √(A1·A2)), exacta para secciones semejantes (tronco de pirámide o cono)."""
    return altura / 3.0 * (area_mayor + area_menor + math.sqrt(area_mayor * area_menor))
