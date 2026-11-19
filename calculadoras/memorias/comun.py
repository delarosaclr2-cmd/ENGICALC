"""Utilidades numéricas independientes de la interfaz. Todas las magnitudes en SI."""
from __future__ import annotations

import copy
import json
import math
from functools import lru_cache
from pathlib import Path

from ..nucleo.modelo import ErrorEntrada

G = 9.80665


@lru_cache
def catalogo(nombre):
    return json.loads((Path(__file__).parent / "datos" / f"{nombre}.json").read_text(encoding="utf-8"))


def copia(x):
    return copy.deepcopy(x)


def exigir(condicion, mensaje):
    if not condicion:
        raise ErrorEntrada(mensaje)


def numero(x, nombre="Dato", minimo=None, maximo=None, positivo=False):
    try:
        v = float(str(x).replace(",", "."))
    except (ValueError, TypeError):
        raise ErrorEntrada(f"{nombre}: escribe un número.") from None
    exigir(math.isfinite(v), f"{nombre}: debe ser finito.")
    exigir(not positivo or v > 0, f"{nombre}: debe ser mayor que cero.")
    exigir(minimo is None or v >= minimo, f"{nombre}: valor menor que {minimo}.")
    exigir(maximo is None or v <= maximo, f"{nombre}: valor mayor que {maximo}.")
    return v


def validar_campos(nombre, entradas):
    datos = copia(entradas)
    for f in catalogo(nombre)["fields"]:
        key = f["id"]
        exigir(key in datos, f"Falta el dato {f['label']}.")
        if f["type"] == "number":
            datos[key] = numero(datos[key], f["label"], f.get("min"), f.get("max"))
        elif f["type"] == "checkbox":
            exigir(isinstance(datos[key], bool), f"{f['label']}: valor lógico no válido.")
        elif key == "nmot":
            numero(datos[key], "Velocidad del motor", positivo=True)
        elif f["options"]:
            exigir(str(datos[key]) in [o[0] for o in f["options"]], f"{f['label']}: opción no válida.")
    return datos


def raiz(funcion, lo, hi, pasos=600):
    x0, f0 = lo, funcion(lo)
    if f0 == 0:
        return lo
    for i in range(1, pasos + 1):
        x1 = lo + (hi - lo) * i / pasos
        f1 = funcion(x1)
        if math.isfinite(f0) and math.isfinite(f1) and f0 * f1 <= 0:
            a, b, fa = x0, x1, f0
            for _ in range(90):
                m = (a + b) / 2
                if fa * funcion(m) <= 0:
                    b = m
                else:
                    a, fa = m, funcion(m)
            return (a + b) / 2
        x0, f0 = x1, f1
    return None


def siguiente(serie, valor):
    return next((x for x in serie if x >= valor), None)


def fila(clave, etiqueta, valor, unidad="", nivel="V"):
    return {"clave": clave, "etiqueta": etiqueta, "valor": valor, "unidad": unidad, "nivel": nivel}


def pchip(xs, ys):
    """Interpolación Hermite monótona, sin extrapolación; equivalente al HTML."""
    from bisect import bisect_right
    n = len(xs)
    exigir(n >= 2 and all(xs[i+1] > xs[i] for i in range(n-1)), "Caudales de curva repetidos o insuficientes.")
    h = [xs[i+1]-xs[i] for i in range(n-1)]
    d = [(ys[i+1]-ys[i])/h[i] for i in range(n-1)]
    def extremo(h0,h1,d0,d1):
        m = ((2*h0+h1)*d0-h0*d1)/(h0+h1)
        if m*d0 <= 0: return 0
        return 3*d0 if d0*d1 <= 0 and abs(m)>3*abs(d0) else m
    m = [0.0]*n
    if n == 2:
        m = [d[0], d[0]]
    else:
        for i in range(1,n-1):
            if d[i-1]*d[i] > 0:
                w1,w2=2*h[i]+h[i-1],h[i]+2*h[i-1]
                m[i]=(w1+w2)/(w1/d[i-1]+w2/d[i])
        m[0]=extremo(h[0],h[1],d[0],d[1]);m[-1]=extremo(h[-1],h[-2],d[-1],d[-2])
    def evaluar(x):
        tol=1e-9*(xs[-1]-xs[0])
        if not xs[0]-tol <= x <= xs[-1]+tol: return math.nan
        if x<=xs[0]: return ys[0]
        if x>=xs[-1]: return ys[-1]
        i=bisect_right(xs,x)-1;t=(x-xs[i])/h[i]
        return (2*t**3-3*t*t+1)*ys[i]+(t**3-2*t*t+t)*h[i]*m[i]+(-2*t**3+3*t*t)*ys[i+1]+(t**3-t*t)*h[i]*m[i+1]
    return evaluar
