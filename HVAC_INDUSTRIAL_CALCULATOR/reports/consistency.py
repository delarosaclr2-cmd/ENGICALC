"""Coherencia entre entradas y resultados de una memoria de cálculo.

Una memoria solo es válida si los datos de entrada que presenta son exactamente los
que produjeron los resultados. Cada ``ProjectResults`` guarda la huella SHA-256 de
sus entradas (proyecto, configuración y base de datos); antes de exportar se compara
con la huella de las entradas actuales y, si difieren, se rechaza la exportación.
"""
from __future__ import annotations


class StaleResultsError(RuntimeError):
    """Los resultados no corresponden a las entradas actuales del proyecto."""


def require_current_results(project, results, settings, db) -> None:
    from core.calculation import input_fingerprint
    if results is None:
        raise StaleResultsError("No hay resultados calculados: ejecute el cálculo antes de exportar.")
    fp = getattr(results, "input_fingerprint", "")
    if not fp:
        raise StaleResultsError("Los resultados no identifican las entradas con que se calcularon: recalcule antes "
                                "de exportar.")
    if fp != input_fingerprint(project, settings, db):
        raise StaleResultsError("Los resultados no corresponden a las entradas actuales (se modificaron datos, "
                                "configuración o base de datos después del último cálculo). Recalcule antes de "
                                "exportar la memoria.")
