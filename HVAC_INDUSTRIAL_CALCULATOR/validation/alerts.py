"""Alertas de ingeniería.

Niveles (módulo de criterio de ingeniería):
  CRÍTICO      riesgo de diseño, requisito esencial incumplido o resultado físicamente inválido
  ALTO         problema importante que requiere corrección antes de aprobar
  MEDIO        oportunidad de mejora o condición que requiere revisión
  BAJO         recomendación de optimización
  INFO         observación, hipótesis o dato a documentar
  CORRECTO     verificación satisfactoria

Equivalencia con la clasificación de la especificación general y del PDF:
  CRÍTICO → CRÍTICA;  ALTO, MEDIO → ADVERTENCIA;  BAJO, INFO → INFORMATIVA;  CORRECTO → CORRECTO

Regla: una alerta CRÍTICA solo puede emitirse con base 'física' (resultado
imposible o condición insegura evidente) o 'referencia' (criterio citado de
fabricante/norma). Los criterios 'hipótesis' del proyecto no generan alertas
críticas.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

LEVELS = ["CRÍTICO", "ALTO", "MEDIO", "BAJO", "INFO", "CORRECTO"]
LEVEL_RANK = {lv: i for i, lv in enumerate(LEVELS)}
LEGACY = {"CRÍTICO": "CRÍTICA", "ALTO": "ADVERTENCIA", "MEDIO": "ADVERTENCIA", "BAJO": "INFORMATIVA",
          "INFO": "INFORMATIVA", "CORRECTO": "CORRECTO"}
LEVEL_COLORS = {"CRÍTICO": "#B42318", "ALTO": "#D9480F", "MEDIO": "#B7791F", "BAJO": "#2F6FB0",
                "INFO": "#5B6577", "CORRECTO": "#2B7A4B"}

BASIS_PHYSICS = "física"
BASIS_REFERENCE = "referencia"
BASIS_HYPOTHESIS = "hipótesis"
BASIS_DATA = "datos faltantes"


@dataclass
class Alert:
    level: str
    module: str
    parameter: str
    detected: str                 # qué se detectó
    value: float | None = None    # valor SI
    quantity: str | None = None   # magnitud para formatear en SI/IP
    value_text: str = ""          # alternativa textual
    criterion: str = ""           # criterio de comparación
    consequence: str = ""         # por qué puede ser un problema
    recommendation: str = ""      # acción correctiva
    source: str = ""              # fuente técnica o justificación
    basis: str = BASIS_REFERENCE
    item: str = ""                # elemento afectado (tramo, campana, ventilador…)

    def __post_init__(self):
        if self.level not in LEVELS:
            raise ValueError(f"Nivel de alerta inválido: {self.level}")
        if self.level == "CRÍTICO" and self.basis == BASIS_HYPOTHESIS:
            # Una hipótesis no puede respaldar una alerta crítica: se degrada a ALTO.
            self.level = "ALTO"

    @property
    def legacy_level(self) -> str:
        return LEGACY[self.level]

    def value_str(self, system: str = "SI") -> str:
        if self.value is None:
            return self.value_text or "—"
        from core.units import fmt
        if self.quantity:
            return fmt(self.value, self.quantity, system)
        from core.units import format_number
        return format_number(self.value, 4) + (f" {self.value_text}" if self.value_text else "")

    def to_dict(self) -> dict:
        return asdict(self)


def sort_alerts(alerts: list[Alert]) -> list[Alert]:
    return sorted(alerts, key=lambda a: (LEVEL_RANK[a.level], a.module, a.item))


def count_by_level(alerts: list[Alert]) -> dict[str, int]:
    out = {lv: 0 for lv in LEVELS}
    for a in alerts:
        out[a.level] += 1
    return out


def worst_level(alerts: list[Alert]) -> str:
    if not alerts:
        return "CORRECTO"
    return min((a.level for a in alerts), key=lambda lv: LEVEL_RANK[lv])
