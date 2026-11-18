"""Pérdidas de presión en equipos (filtros, ciclones, colectores, lavadores,
silenciadores, serpentines, intercambiadores, rejillas especiales).

Modelos disponibles:
* 'fixed'     ΔP constante (dato de fabricante a la condición de diseño).
* 'power_law' ΔP = ΔP_ref·(Q/Q_ref)^n  (n = 2 flujo turbulento; n ≈ 1 medios filtrantes
               en régimen laminar; el valor de n debe justificarse con datos del fabricante).
* 'table'     curva ΔP(Q) por puntos, interpolación monótona PCHIP; fuera del rango
               se extrapola con la ley cuadrática y se emite advertencia.
* 'filter'    filtro con ΔP inicial (limpio) y final (saturado/recomendado de
               mantenimiento) a Q_ref, ley de potencia con exponente n, evaluado en el
               estado seleccionado: 'limpio', 'sucio' o 'intermedio' (fracción).

Ningún valor de pérdida se asume por defecto: el usuario debe introducir los
datos del fabricante y su fuente.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import PchipInterpolator

EQUIPMENT_TYPES = ["Filtro", "Colector de polvo (mangas)", "Colector de cartuchos", "Ciclón", "Lavador de gases",
                   "Silenciador", "Serpentín", "Intercambiador", "Rejilla especial", "Otro"]


class EquipmentError(ValueError):
    pass


@dataclass
class Equipment:
    name: str = "Equipo"
    eq_type: str = "Filtro"
    model: str = "fixed"           # 'fixed' | 'power_law' | 'table' | 'filter'
    dp_fixed: float = 0.0          # Pa
    dp_ref: float = 0.0            # Pa a Q_ref
    q_ref: float = 1.0             # m³/s
    n_exp: float = 2.0
    table: list[list[float]] = field(default_factory=list)   # [[Q m³/s, ΔP Pa], ...]
    dp_clean: float = 0.0          # Pa a Q_ref (filtro limpio)
    dp_dirty: float = 0.0          # Pa a Q_ref (filtro en condición de mantenimiento)
    state: str = "sucio"           # 'limpio' | 'sucio' | 'intermedio'
    state_fraction: float = 1.0    # 0 = limpio, 1 = sucio (para 'intermedio')
    source: str = "Dato del fabricante (indicar)"

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "Equipment":
        e = cls()
        for k, v in d.items():
            if hasattr(e, k):
                setattr(e, k, v)
        return e


def equipment_dp(eq: Equipment, Q: float, state_override: str | None = None) -> tuple[float, list[str]]:
    """Pérdida del equipo [Pa] al caudal ``Q`` [m³/s]. Devuelve (ΔP, advertencias)."""
    warns: list[str] = []
    Qa = abs(Q)
    if eq.model == "fixed":
        dp = eq.dp_fixed
        warns.append(f"{eq.name}: pérdida fija independiente del caudal (válida solo en el punto de diseño).")
    elif eq.model == "power_law":
        if eq.q_ref <= 0:
            raise EquipmentError(f"{eq.name}: Q_ref debe ser positivo")
        dp = eq.dp_ref * (Qa / eq.q_ref) ** eq.n_exp
    elif eq.model == "table":
        pts = sorted((float(q), float(p)) for q, p in eq.table)
        if len(pts) < 2:
            raise EquipmentError(f"{eq.name}: la curva requiere al menos 2 puntos")
        qs = np.array([p[0] for p in pts])
        ps = np.array([p[1] for p in pts])
        if Qa < qs[0] or Qa > qs[-1]:
            q0, p0 = (pts[0] if Qa < qs[0] else pts[-1])
            dp = p0 * (Qa / q0) ** 2 if q0 > 0 else p0
            warns.append(f"{eq.name}: caudal fuera del rango de la curva; extrapolación cuadrática.")
        else:
            dp = float(PchipInterpolator(qs, ps)(Qa))
    elif eq.model == "filter":
        if eq.q_ref <= 0:
            raise EquipmentError(f"{eq.name}: Q_ref debe ser positivo")
        state = state_override or eq.state
        if state == "limpio":
            base = eq.dp_clean
        elif state == "intermedio":
            fr = min(max(eq.state_fraction, 0.0), 1.0)
            base = eq.dp_clean + fr * (eq.dp_dirty - eq.dp_clean)
        else:
            base = eq.dp_dirty
        dp = base * (Qa / eq.q_ref) ** eq.n_exp
        if eq.dp_dirty < eq.dp_clean:
            warns.append(f"{eq.name}: la pérdida final es menor que la inicial; revise los datos.")
    else:
        raise EquipmentError(f"Modelo de equipo desconocido: {eq.model}")
    if dp < 0:
        raise EquipmentError(f"{eq.name}: pérdida negativa")
    return (dp if Q >= 0 else -dp), warns
