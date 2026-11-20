"""Velocidad en función del caudal y del diámetro: capacidad de la línea y selección de diámetro.

Relaciones básicas (las mismas que usan las memorias PCGV-DM-011/012/017):

    A = π·Di²/4                 área interior real (Di de ASME B36.10M, NO el diámetro nominal)
    v = Q / A                   Q es el caudal VOLUMÉTRICO A LA CONDICIÓN DE OPERACIÓN
    Q_máx = v_máx · A           caudal que agota el criterio de velocidad: capacidad de la línea
    Di_req = √(4·Q/(π·v))       diámetro interior necesario para una velocidad objetivo

Para gas y vapor, Q es el caudal real (no el referido a condiciones normales): Q = ṁ·ν = ṁ/ρ a la
presión y temperatura del punto que se evalúa. La velocidad cambia a lo largo de la línea conforme
cae la presión, por lo que el barrido de diámetros usa la condición de ENTRADA, que es la más
desfavorable en caudal másico constante solo si la densidad no cambia; para líneas con caída de
presión apreciable el valor que gobierna es el de salida, que da el cálculo completo del tramo.

El barrido de diámetros no sustituye al cálculo del tramo: sirve para elegir el diámetro y después
verificarlo con el método completo (compresible por segmentos, accesorios, desnivel y NPSH).
"""
from __future__ import annotations

import math

FT = 0.3048
PULG = 0.0254


def area(d_m: float) -> float:
    """A = π·Di²/4 en m²."""
    if d_m <= 0:
        raise ValueError("El diámetro interior debe ser positivo")
    return math.pi / 4.0 * d_m ** 2


def velocidad(q_m3s: float, d_m: float) -> float:
    """v = Q/A en m/s, con Q en m³/s a la condición de operación."""
    return q_m3s / area(d_m)


def caudal_limite(d_m: float, v_m_s: float) -> float:
    """Q = v·A en m³/s: caudal que produce la velocidad dada (capacidad de la línea)."""
    return v_m_s * area(d_m)


def diametro_requerido(q_m3s: float, v_m_s: float) -> float:
    """Di = √(4·Q/(π·v)) en m: diámetro interior para alcanzar la velocidad objetivo."""
    if v_m_s <= 0:
        raise ValueError("La velocidad objetivo debe ser positiva")
    return math.sqrt(4.0 * q_m3s / (math.pi * v_m_s))


def estado_velocidad(v: float, v_min=None, v_max=None) -> str:
    """CUMPLE / NO CUMPLE / INFORMATIVO según el intervalo recomendado."""
    if v_max not in (None, "") and v > float(v_max):
        return "NO CUMPLE"
    if v_min not in (None, "") and v < float(v_min):
        return "INFORMATIVO"
    if v_max in (None, "") and v_min in (None, ""):
        return ""
    return "CUMPLE"


def _fmt_dp(dp_pa):
    """kPa con los decimales que tengan sentido para el orden de magnitud."""
    k = dp_pa / 1000.0
    if abs(k) >= 1000:
        return f"{k:,.0f}"
    return f"{k:,.1f}" if abs(k) >= 10 else f"{k:.3f}"


def barrido(candidatos, calc, v_min=None, v_max=None, nps_actual=None) -> list:
    """Velocidad y caída de presión de cada diámetro candidato, al caudal capturado.

    candidatos  iterable de (nps, cedula, d_interior_m)
    calc        función d_m -> dict con al menos 'v'; opcionalmente 're', 'f', 'dp_pa', 'nota'
    Devuelve filas [NPS, cédula, Di mm, v m/s, v ft/s, Re, ΔP, estado].
    """
    filas = []
    for nps, cedula, d in candidatos:
        try:
            r = calc(d)
        except Exception as exc:                      # un diámetro inviable no debe romper la tabla
            filas.append([f"{nps}{' *' if nps == nps_actual else ''}", str(cedula),
                          f"{d*1000:.2f}", "—", "—", "—", "—", f"no evaluable: {exc}"])
            continue
        v = r["v"]
        dp = r.get("dp_pa")
        filas.append([f"{nps}{' *' if nps == nps_actual else ''}", str(cedula), f"{d*1000:.2f}",
                      f"{v:.3f}", f"{v/FT:.2f}",
                      "—" if r.get("re") is None else f"{r['re']:,.0f}",
                      "—" if dp is None else _fmt_dp(dp),
                      r.get("nota") or estado_velocidad(v, v_min, v_max)])
    return filas


def ventana(candidatos, q_m3s, v_min=None, v_max=None, nps_actual=None, antes=2, despues=3) -> list:
    """Recorta la lista de diámetros a los útiles: los que cumplen el criterio más unos vecinos.

    Sin criterio de velocidad devuelve la lista completa. Siempre conserva el diámetro actual.
    """
    if v_max in (None, "") or not candidatos:
        return list(candidatos)
    vmax = float(v_max)
    idx_ok = [i for i, (_, _, d) in enumerate(candidatos) if velocidad(q_m3s, d) <= vmax]
    if not idx_ok:
        return list(candidatos)
    i0, i1 = max(0, min(idx_ok) - antes), min(len(candidatos) - 1, min(idx_ok) + despues)
    if nps_actual is not None:
        for i, (nps, _, _) in enumerate(candidatos):
            if nps == nps_actual:
                i0, i1 = min(i0, i), max(i1, i)
    return candidatos[i0:i1 + 1]


def tabla_diametros(candidatos, calc, v_min=None, v_max=None, nps_actual=None, longitud_m=None) -> tuple:
    """Tabla (título, encabezados, filas, anchos) del barrido de diámetros para la memoria."""
    filas = barrido(candidatos, calc, v_min, v_max, nps_actual)
    lim = []
    if v_min not in (None, ""):
        lim.append(f"v ≥ {float(v_min):g}")
    if v_max not in (None, ""):
        lim.append(f"v ≤ {float(v_max):g} m/s")
    tit = "Velocidad por diámetro al caudal capturado"
    if lim:
        tit += f" (criterio: {', '.join(lim)})"
    if longitud_m:
        tit += f"; ΔP por fricción en {longitud_m:g} m de tubo recto"
    enc = ["NPS", "Céd.", "Di (mm)", "v (m/s)", "v (ft/s)", "Re", "ΔP (kPa)", "Estado"]
    return (tit, enc, filas, [1.9, 1.3, 2.0, 2.0, 2.0, 2.4, 2.2, 3.8])


def tabla_capacidad(d_m: float, q_m3s: float, v_min=None, v_max=None, conv=None, unidad="m³/h",
                    simbolo="Q") -> tuple:
    """Tabla (título, encabezados, filas, anchos) de capacidad de la línea: caudal contra velocidad.

    conv  función q_m3s -> valor en la unidad de presentación (por omisión m³/h).
    """
    doble = conv is not None and unidad.replace(" ", "") not in ("m³/h", "m3/h")
    conv = conv or (lambda q: q * 3600.0)
    filas = []
    def fila(etiqueta, v, nota):
        q = caudal_limite(d_m, v)
        cols = [etiqueta, f"{v:.3f}", f"{conv(q):,.2f}"] + ([f"{q*3600:,.3f}"] if doble else []) + [nota]
        filas.append(cols)
    if v_min not in (None, ""):
        fila("Velocidad mínima recomendada", float(v_min), "caudal por debajo del cual la línea queda holgada")
    v_act = velocidad(q_m3s, d_m)
    fila("Velocidad al caudal capturado", v_act, "condición evaluada")
    if v_max not in (None, ""):
        fila("Velocidad máxima recomendada", float(v_max), "CAPACIDAD MÁXIMA de la línea con este criterio")
    enc = ["Condición", "v (m/s)", f"{simbolo} ({unidad})"] + (["Q (m³/h real)"] if doble else []) + ["Nota"]
    anchos = [5.2, 2.0, 3.0] + ([3.0] if doble else []) + [4.4 if doble else 7.4]
    return (f"Capacidad de la línea: caudal correspondiente a cada velocidad (Di = {d_m*1000:.2f} mm)",
            enc, filas, anchos)


def curva(d_m: float, q_m3s: float, v_min=None, v_max=None, n: int = 24) -> dict:
    """Puntos (Q en m³/h real, v en m/s) para graficar la velocidad contra el caudal."""
    qmax = q_m3s * 2.0
    if v_max not in (None, ""):
        qmax = max(qmax, caudal_limite(d_m, float(v_max)) * 1.15)
    pts = [(q_m3s * 0 + qmax * i / n * 3600.0, velocidad(qmax * i / n, d_m)) for i in range(n + 1)]
    return {"puntos": pts, "q_actual_m3h": q_m3s * 3600.0, "v_actual": velocidad(q_m3s, d_m),
            "q_max_m3h": (caudal_limite(d_m, float(v_max)) * 3600.0) if v_max not in (None, "") else None,
            "q_min_m3h": (caudal_limite(d_m, float(v_min)) * 3600.0) if v_min not in (None, "") else None,
            "v_min": None if v_min in (None, "") else float(v_min),
            "v_max": None if v_max in (None, "") else float(v_max)}


ECUACIONES = [
    "A = π·Di²/4;   v = Q/A   (Q volumétrico a la condición de operación)",
    "Capacidad: Q_máx = v_máx·A;   diámetro requerido: Di = √(4·Q/(π·v))",
]
