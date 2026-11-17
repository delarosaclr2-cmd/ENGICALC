"""Genera los casos de los ejercicios de libros de texto y la tabla de resultados.

Fuente única de datos: ``tests/casos_libros.py``. Produce:

- ``docs/ejemplos/libros/<caso>.json``: casos que se abren en el programa (Archivo → Abrir caso guardado
  o «Abrir caso» en la calculadora) con los datos del ejercicio ya capturados.
- En la salida estándar, la tabla en Markdown (fuente, magnitud, publicado, calculadora, diferencia)
  que se copia en ``docs/VALIDACION_CON_LIBROS.md``.

Ejecutar después de modificar una calculadora o un caso:

    python herramientas/generar_casos_libros.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

from casos_libros import CASOS_LIBROS, valor  # noqa: E402
from calculadoras.calculos import POR_ID  # noqa: E402
from calculadoras.interfaz.reportes import guardar_caso  # noqa: E402

DESTINO = RAIZ / "docs" / "ejemplos" / "libros"


def _fmt(x: float) -> str:
    return f"{x:,.0f}".replace(",", " ") if abs(x) >= 1000 else f"{x:.4g}"


def main() -> int:
    DESTINO.mkdir(parents=True, exist_ok=True)
    filas, fallas = [], 0
    for nombre, caso in CASOS_LIBROS.items():
        calc = POR_ID[caso["calculadora"]]
        entradas = calc.valores_por_defecto()
        entradas.update(caso["entradas"])
        resultado = calc.calcular(entradas)
        proyecto = {"proyecto": "Validación con ejercicios de libros de texto", "documento": nombre}
        ruta = DESTINO / f"{nombre}.json"
        guardar_caso(ruta, calc, entradas, resultado, proyecto)
        datos = json.loads(ruta.read_text(encoding="utf-8"))  # trazabilidad: fuente y planteamiento
        datos["fuente"], datos["planteamiento"] = caso["fuente"], caso["planteamiento"]
        ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
        for etiqueta, salida, publicado, tolerancia in caso["comprobaciones"]:
            obtenido = valor(resultado, salida)
            dif = (obtenido - publicado) / publicado * 100
            ok = abs(dif) <= tolerancia * 100 + 1e-9
            fallas += not ok
            filas.append(f"| `{nombre}` | {etiqueta} | {_fmt(publicado)} | {_fmt(obtenido)} | {dif:+.2f} % | "
                         f"{'Coincide' if ok else 'NO COINCIDE'} |")
    print("| Caso | Magnitud | Publicado | Calculadora | Diferencia | Veredicto |")
    print("|---|---|---|---|---|---|")
    print("\n".join(filas))
    print(f"\n{len(CASOS_LIBROS)} casos escritos en {DESTINO.relative_to(RAIZ)}; comprobaciones fuera de "
          f"tolerancia: {fallas}")
    return 1 if fallas else 0


if __name__ == "__main__":
    raise SystemExit(main())
