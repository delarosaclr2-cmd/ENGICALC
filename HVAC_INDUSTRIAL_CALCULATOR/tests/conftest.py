"""Configuración de pruebas y registro de resultados.

Cada comprobación numérica se registra con: datos de entrada, resultado esperado
(de una referencia independiente), resultado obtenido, error absoluto, error
relativo, tolerancia, referencia y estado. Al terminar la sesión se escriben:
  tests/results/registro_pruebas.csv
  tests/results/registro_pruebas.md
Los resultados esperados NUNCA se ajustan para hacer pasar una prueba.
"""
from __future__ import annotations

import csv
import datetime
import json
import math
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

RESULTS_DIR = os.path.join(ROOT, "tests", "results")
RECORDS: list[dict] = []


@pytest.fixture
def check(request):
    def _check(name: str, inputs: dict, expected: float, obtained: float, rel_tol: float = 1e-9,
               abs_tol: float = 0.0, reference: str = ""):
        expected = float(expected)
        obtained = float(obtained)
        abs_err = abs(obtained - expected)
        rel_err = abs_err / abs(expected) if expected != 0 else (0.0 if abs_err == 0 else math.inf)
        ok = abs_err <= max(abs_tol, rel_tol * abs(expected))
        RECORDS.append({
            "prueba": request.node.nodeid.split("::", 1)[-1], "comprobación": name,
            "entradas": json.dumps(inputs, ensure_ascii=False, default=str),
            "esperado": expected, "obtenido": obtained, "error_abs": abs_err, "error_rel": rel_err,
            "tolerancia": f"rel {rel_tol:g}" + (f" / abs {abs_tol:g}" if abs_tol else ""),
            "referencia": reference, "estado": "APROBADA" if ok else "FALLIDA",
        })
        assert ok, (f"{name}: esperado {expected:.10g}, obtenido {obtained:.10g}, "
                    f"error rel {rel_err:.3g} > {rel_tol:g}")
    return _check


@pytest.fixture(scope="session")
def db():
    from database.db import load_db
    return load_db()


@pytest.fixture(scope="session")
def settings():
    from config.settings import load_settings
    return load_settings()


@pytest.fixture(scope="session")
def example_project():
    from examples.build_example import build, alternatives
    p = build()
    p.alternatives = alternatives(p)
    return p


def pytest_sessionfinish(session, exitstatus):
    if not RECORDS:
        return
    os.makedirs(RESULTS_DIR, exist_ok=True)
    keys = list(RECORDS[0].keys())
    with open(os.path.join(RESULTS_DIR, "registro_pruebas.csv"), "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(RECORDS)
    n_ok = sum(r["estado"] == "APROBADA" for r in RECORDS)
    lines = [
        "# Registro de pruebas de validación matemática",
        "",
        f"Fecha: {datetime.datetime.now().isoformat(timespec='seconds')}  ",
        f"Comprobaciones numéricas: {len(RECORDS)} — aprobadas: {n_ok} — fallidas: {len(RECORDS) - n_ok}",
        "",
        "| Prueba | Comprobación | Esperado | Obtenido | Error abs. | Error rel. | Tolerancia | Referencia | Estado |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in RECORDS:
        lines.append(f"| {r['prueba']} | {r['comprobación']} | {r['esperado']:.8g} | {r['obtenido']:.8g} | "
                     f"{r['error_abs']:.3g} | {r['error_rel']:.3g} | {r['tolerancia']} | {r['referencia']} | {r['estado']} |")
    with open(os.path.join(RESULTS_DIR, "registro_pruebas.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
