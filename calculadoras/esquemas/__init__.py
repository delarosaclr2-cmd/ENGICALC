"""Esquemas ajustables de las calculadoras (material de apoyo visual).

Cada esquema se dibuja con los datos validados y el resultado de la calculadora, de modo que
se redibuja cuando cambian los datos. Donde la geometría lo permite, el dibujo es **a escala**
(silo, tolva, banda, helicoidal, aerodeslizador, secador, viga y las secciones de ductos y tubos);
los diagramas de proceso (torre, colector, soplador, vacío, neumático) son **esquemas sin escala**
con los valores del cálculo. Cada figura indica cuál es su caso.

Los esquemas no calculan nada nuevo: toman las dimensiones y valores del resultado, o llaman a
las mismas funciones del motor (p. ej. Janssen o la elástica de la viga), para que el dibujo no
pueda contradecir a la tabla de resultados.

La bomba centrífuga no tiene esquema (decisión del usuario).

Uso:
    from calculadoras import esquemas
    if esquemas.disponible("silo"):
        figura = esquemas.crear_figura("silo", datos, resultado)
"""
from __future__ import annotations

import importlib

# id de la calculadora → (módulo, función). Se importan al dibujar: así el programa abre aunque
# falte matplotlib y la ventana solo avisa en la pestaña del esquema.
ESQUEMAS: dict[str, tuple[str, str]] = {
    "silo": ("solidos", "silo"),
    "tolva": ("solidos", "tolva"),
    "banda": ("solidos", "banda"),
    "helicoidal": ("solidos", "helicoidal"),
    "elevador": ("solidos", "elevador"),
    "aerodeslizador": ("solidos", "aerodeslizador"),
    "neumatico": ("aire", "neumatico"),
    "ductos": ("aire", "ductos"),
    "colector": ("aire", "colector"),
    "soplador": ("aire", "soplador"),
    "vacio": ("aire", "vacio"),
    "torre": ("termica", "torre"),
    "secador": ("termica", "secador"),
    "viga": ("estructural", "viga"),
}

TAMANO = (10.0, 6.4)  # pulgadas de la figura; la ventana la ajusta al panel


def disponible(id_calculadora: str) -> bool:
    return id_calculadora in ESQUEMAS


def dibujar(figura, id_calculadora: str, datos: dict, resultado) -> None:
    """Borra la figura y dibuja en ella el esquema de la calculadora."""
    modulo, funcion = ESQUEMAS[id_calculadora]
    dibujo = getattr(importlib.import_module(f"{__name__}.{modulo}"), funcion)
    figura.clear()
    dibujo(figura, datos, resultado)


def crear_figura(id_calculadora: str, datos: dict, resultado, tamano: tuple = TAMANO):
    """Figura de matplotlib (sin pyplot) con el esquema; sirve sin pantalla (pruebas, PNG)."""
    from matplotlib.figure import Figure

    figura = Figure(figsize=tamano, dpi=100)
    dibujar(figura, id_calculadora, datos, resultado)
    return figura
