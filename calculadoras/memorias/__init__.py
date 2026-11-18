"""Memorias completas reescritas en Python; no ejecutan HTML ni JavaScript."""

from dataclasses import dataclass
from importlib import import_module


@dataclass(frozen=True)
class Memoria:
    id: str
    nombre: str
    modulo: str
    descripcion: str
    disciplina: str = "Memorias de cálculo RMR"
    estado_auditoria: str = "MIGRADA A PYTHON"
    estado_validacion: str = "Equivalencia numérica documentada"
    limitaciones: tuple = ("Se conservan las hipótesis y correlaciones de las memorias de revisión A.",
                           "Los datos de curvas y coeficientes deben corresponder al proyecto.")
    archivos_originales: tuple = ("Memoria HTML Rev_A (motor reescrito en Python)",)

    @property
    def motor(self):
        return import_module(f"{__name__}.{self.modulo}")


MEMORIAS = (
    Memoria("memoria_agitadores", "Agitadores · memoria completa", "agitadores",
            "Proceso, suspensión de sólidos y fibra, motor, flecha, deflexión y velocidad crítica."),
    Memoria("memoria_bombas", "Bombas centrífugas · memoria completa", "bombas",
            "Curvas del fabricante, sistema, operación, NPSH, BEP y leyes de afinidad."),
    Memoria("memoria_hvac", "Ductos HVAC · memoria completa", "ductos",
            "Red de tramos conectados, ventilador, balanceo, presiones y dimensionamiento."),
)
POR_ID = {m.id: m for m in MEMORIAS}


def buscar(texto):
    import unicodedata
    def normal(s):
        return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")
    palabras = normal(texto).split()
    return [m for m in MEMORIAS if all(p in normal(m.nombre + " " + m.descripcion + " " + m.id) for p in palabras)]
