"""Trazabilidad de cálculos.

Cada motor de cálculo registra pasos ``CalcStep`` con: ecuación, variables,
sustitución numérica, resultado, unidad, fuente técnica y el tipo de resultado
(calculado, estimación preliminar o dato externo que requiere validación).
Esto alimenta la memoria de cálculo PDF/Excel.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from .units import format_number

KIND_CALCULATED = "Calculado"
KIND_ESTIMATE = "Estimación preliminar"
KIND_EXTERNAL = "Dato externo (requiere validación)"
KIND_HYPOTHESIS = "Hipótesis"


@dataclass
class Variable:
    symbol: str
    value: Any
    unit: str
    description: str = ""

    def text(self) -> str:
        v = format_number(self.value, 5) if isinstance(self.value, (int, float)) else str(self.value)
        return f"{self.symbol} = {v} {self.unit}".strip()


@dataclass
class CalcStep:
    module: str
    title: str
    equation: str
    variables: list[Variable]
    substitution: str
    result: Any
    unit: str
    source: str
    kind: str = KIND_CALCULATED
    notes: str = ""

    def result_text(self) -> str:
        if isinstance(self.result, (int, float)):
            return f"{format_number(self.result, 5)} {self.unit}".strip()
        return f"{self.result} {self.unit}".strip()

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class Trace:
    steps: list[CalcStep] = field(default_factory=list)

    def add(self, module: str, title: str, equation: str, variables: list[tuple], substitution: str,
            result: Any, unit: str, source: str, kind: str = KIND_CALCULATED, notes: str = "") -> CalcStep:
        vars_ = [Variable(*v) if not isinstance(v, Variable) else v for v in variables]
        step = CalcStep(module, title, equation, vars_, substitution, result, unit, source, kind, notes)
        self.steps.append(step)
        return step

    def extend(self, other: "Trace | None") -> None:
        if other is not None:
            self.steps.extend(other.steps)

    def by_module(self, module: str) -> list[CalcStep]:
        return [s for s in self.steps if s.module == module]


def n(v: float, digits: int = 5) -> str:
    """Formato corto de un número para sustituciones numéricas."""
    return format_number(v, digits)
