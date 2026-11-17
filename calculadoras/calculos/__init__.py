"""Registro de calculadoras.

Para agregar una calculadora nueva:
1. Cree ``calculadoras/calculos/mi_calculo.py`` con ``CAMPOS``, una función
   ``calcular(datos) -> Resultado`` y un objeto ``CALCULADORA``.
2. Agregue el módulo a la lista ``_MODULOS``. El menú, el buscador, los reportes
   y la prueba de humo la incluyen automáticamente.
"""
from __future__ import annotations

from importlib import import_module

_MODULOS = (
    "banda", "elevador", "helicoidal", "aerodeslizador", "neumatico", "tolva", "silo",
    "ductos", "colector", "soplador",
    "bomba", "vacio",
    "torre", "secador",
    "viga",
)

DISCIPLINAS = (
    "Manejo de sólidos a granel",
    "Ventilación y control de polvo",
    "Máquinas de fluido y bombeo",
    "Térmica y transferencia de calor",
    "Estructural",
)

CALCULADORAS = [import_module(f"{__name__}.{m}").CALCULADORA for m in _MODULOS]
POR_ID = {c.id: c for c in CALCULADORAS}


def por_disciplina() -> dict:
    grupos = {d: [] for d in DISCIPLINAS}
    for c in CALCULADORAS:
        grupos.setdefault(c.disciplina, []).append(c)
    return grupos


def buscar(texto: str) -> list:
    """Búsqueda simple por nombre, disciplina, descripción y palabras clave (sin acentos)."""
    import unicodedata

    def normal(s: str) -> str:
        return "".join(ch for ch in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(ch) != "Mn")

    t = normal(texto.strip())
    if not t:
        return list(CALCULADORAS)
    salida = []
    for c in CALCULADORAS:
        pajar = normal(" ".join((c.nombre, c.disciplina, c.descripcion) + tuple(c.palabras_clave)))
        if all(p in pajar for p in t.split()):
            salida.append(c)
    return salida
