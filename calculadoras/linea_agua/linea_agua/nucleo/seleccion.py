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


def caudal_limite_real(v_de_q, v_objetivo, q_inicial: float, max_iter: int = 60):
    """Caudal de ENTRADA cuya velocidad GOBERNANTE del tramo iguala v_objetivo.

    Para un gas o un vapor la densidad cae con la presión, así que la velocidad crece a lo largo
    de la línea y la que gobierna la verificación es la de salida. Entonces Q_máx = v_máx·A
    calculado a la entrada sobreestima la capacidad: al conducir ese caudal la salida ya excede el
    límite. Aquí se resuelve el caudal de entrada que hace que la velocidad gobernante alcance el
    límite, usando el mismo modelo de caída de presión del tramo.

    v_de_q      función q (m³/s a la entrada) -> velocidad gobernante (m/s), o None / excepción si
                la línea no puede conducir ese caudal con esa presión de entrada. Debe crecer con q.
    q_inicial   caudal de referencia para acotar la búsqueda (el capturado).
    Devuelve el caudal en m³/s a la entrada, o None si no se pudo acotar (línea ya saturada o
    criterio inalcanzable). Se aproxima POR DEBAJO: el valor devuelto cumple el límite.
    """
    if v_objetivo in (None, "") or not q_inicial or q_inicial <= 0:
        return None
    v_objetivo = float(v_objetivo)
    if v_objetivo <= 0:
        return None

    def v(q):
        """Velocidad gobernante, o None si la línea no conduce ese caudal (flujo crítico, ΔP > P1)."""
        try:
            x = v_de_q(q)
        except Exception:                      # un caudal inviable acota por arriba, no es un error
            return None
        return x if (x is not None and math.isfinite(x) and x > 0) else None

    lo = q_inicial                             # cota inferior: velocidad por debajo del objetivo
    v_lo = None
    for _ in range(max_iter):
        v_lo = v(lo)
        if v_lo is not None and v_lo < v_objetivo:
            break
        lo *= 0.5
    else:
        return None
    hi, v_hi = lo * 2.0, None                  # cota superior: la alcanza o la línea ya no conduce
    for _ in range(max_iter):
        v_hi = v(hi)
        if v_hi is None or v_hi >= v_objetivo:
            break
        lo, v_lo, hi = hi, v_hi, hi * 2.0
    else:
        return None

    # Illinois (secante acotada): v(q) es suave y casi lineal, así converge en ~6 evaluaciones en
    # vez de ~40. El intervalo se conserva en todo momento, así que no puede divergir. Cada
    # evaluación vuelve a correr el modelo del tramo, que para vapor cuesta décimas de segundo.
    g_lo, g_hi = v_lo - v_objetivo, (None if v_hi is None else v_hi - v_objetivo)
    for _ in range(max_iter):
        if hi - lo <= 1e-6 * hi:
            break
        if g_hi is None or g_hi <= 0 or g_lo >= 0:
            m = 0.5 * (lo + hi)                        # sin secante útil: parte en dos
        else:
            m = lo + (hi - lo) * (-g_lo) / (g_hi - g_lo)
            borde = 0.01 * (hi - lo)                   # no pegarse a un extremo
            m = min(max(m, lo + borde), hi - borde)
        v_m = v(m)
        if v_m is None or v_m >= v_objetivo:
            hi, g_hi = m, (None if v_m is None else v_m - v_objetivo)
            if g_lo is not None:
                g_lo *= 0.5                            # Illinois: acelera el extremo estancado
        else:
            lo, g_lo = m, v_m - v_objetivo
            if g_hi is not None:
                g_hi *= 0.5
    return lo


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


def tabla_diametros(candidatos, calc, v_min=None, v_max=None, nps_actual=None, longitud_m=None,
                    donde_v="", nota_dp="por fricción en {} m de tubo recto") -> tuple:
    """Tabla (título, encabezados, filas, anchos) del barrido de diámetros para la memoria.

    donde_v   dónde se evalúa la velocidad que reporta `calc`, p. ej. "a la salida" para gas y
              vapor, donde la que gobierna no es la de entrada.
    """
    filas = barrido(candidatos, calc, v_min, v_max, nps_actual)
    lim = []
    if v_min not in (None, ""):
        lim.append(f"v ≥ {float(v_min):g}")
    if v_max not in (None, ""):
        lim.append(f"v ≤ {float(v_max):g} m/s")
    tit = "Velocidad por diámetro al caudal capturado"
    if donde_v:
        tit += f" (velocidad {donde_v}: la que gobierna)"
    if lim:
        tit += f" (criterio: {', '.join(lim)})"
    if longitud_m:
        tit += "; ΔP " + nota_dp.format(f"{longitud_m:g}")
    v_enc = f"v {donde_v} (m/s)" if donde_v else "v (m/s)"
    enc = ["NPS", "Céd.", "Di (mm)", v_enc, "v (ft/s)", "Re", "ΔP (kPa)", "Estado"]
    return (tit, enc, filas, [1.9, 1.3, 2.0, 2.0, 2.0, 2.4, 2.2, 3.8])


def tabla_capacidad(d_m: float, q_m3s: float, v_min=None, v_max=None, conv=None, unidad="m³/h",
                    simbolo="Q", v_gobernante=None, donde_v="") -> tuple:
    """Tabla (título, encabezados, filas, anchos) de capacidad de la línea: caudal contra velocidad.

    conv          función q_m3s -> valor en la unidad de presentación (por omisión m³/h).
    v_gobernante  función q (m³/s a la entrada) -> velocidad que gobierna la verificación del tramo.
                  Para un LÍQUIDO se omite: la velocidad no cambia a lo largo de la línea, así que
                  v = Q/A basta. Para GAS y VAPOR debe darse, porque la velocidad crece al caer la
                  presión y v_máx·A con la densidad de entrada sobreestima la capacidad.
    donde_v       dónde se evalúa la velocidad gobernante, p. ej. "a la salida" (para el título).
    """
    doble = conv is not None and unidad.replace(" ", "") not in ("m³/h", "m3/h")
    conv = conv or (lambda q: q * 3600.0)
    comp = v_gobernante is not None
    filas = []

    def q_de_v(v_obj):
        """Caudal de entrada que lleva la velocidad gobernante al objetivo."""
        if comp:
            return caudal_limite_real(v_gobernante, v_obj, q_m3s)
        return caudal_limite(d_m, v_obj)

    def fila(etiqueta, v, q, nota):
        if q is None or v is None:
            cols = [etiqueta, "—" if v is None else f"{v:.3f}", "no alcanzable"] + \
                   (["—"] if doble else []) + [nota]
        else:
            cols = [etiqueta, f"{v:.3f}", f"{conv(q):,.2f}"] + \
                   ([f"{q*3600:,.3f}"] if doble else []) + [nota]
        filas.append(cols)

    if v_min not in (None, ""):
        fila("Velocidad mínima recomendada", float(v_min), q_de_v(float(v_min)),
             "caudal por debajo del cual la línea queda holgada")
    try:
        v_act = v_gobernante(q_m3s) if comp else velocidad(q_m3s, d_m)
    except Exception:
        v_act = None
    fila("Velocidad al caudal capturado", v_act, q_m3s, "condición evaluada")
    if v_max not in (None, ""):
        nota = "CAPACIDAD MÁXIMA de la línea con este criterio"
        if comp:
            nota += f", resuelta con la caída de presión (velocidad {donde_v or 'gobernante'})"
        fila("Velocidad máxima recomendada", float(v_max), q_de_v(float(v_max)), nota)
    etiqueta_v = f"v {donde_v} (m/s)" if (comp and donde_v) else "v (m/s)"
    enc = ["Condición", etiqueta_v, f"{simbolo} ({unidad})"] + (["Q (m³/h real)"] if doble else []) + ["Nota"]
    anchos = [5.2, 2.0, 3.0] + ([3.0] if doble else []) + [4.4 if doble else 7.4]
    tit = f"Capacidad de la línea: caudal correspondiente a cada velocidad (Di = {d_m*1000:.2f} mm)"
    if comp:
        tit += f"; velocidad gobernante del tramo{(' ' + donde_v) if donde_v else ''}, " \
               "con la presión de entrada fija"
    return (tit, enc, filas, anchos)


def curva(d_m: float, q_m3s: float, v_min=None, v_max=None, n: int = 24, v_gobernante=None) -> dict:
    """Puntos (Q en m³/h real a la entrada, v en m/s) para graficar la velocidad contra el caudal.

    Con `v_gobernante` la curva es la de la velocidad que gobierna la verificación (la mayor del
    tramo), para que el punto de capacidad coincida con el de la tabla y con el dictamen.
    """
    comp = v_gobernante is not None

    def vel(q):
        if not comp:
            return velocidad(q, d_m)
        try:
            v = v_gobernante(q)
        except Exception:
            return None
        return v if (v is not None and math.isfinite(v)) else None

    q_de_v = (lambda v: caudal_limite_real(v_gobernante, v, q_m3s)) if comp \
        else (lambda v: caudal_limite(d_m, v))
    q_lim = q_de_v(float(v_max)) if v_max not in (None, "") else None
    q_bajo = q_de_v(float(v_min)) if v_min not in (None, "") else None
    qmax = max(q_m3s * 2.0, (q_lim or 0.0) * 1.15)
    pts = [(qmax * i / n * 3600.0, vel(qmax * i / n)) for i in range(1, n + 1)]
    pts = [(q, v) for q, v in pts if v is not None]
    return {"puntos": pts, "q_actual_m3h": q_m3s * 3600.0, "v_actual": vel(q_m3s),
            "q_max_m3h": (q_lim * 3600.0) if q_lim else None,
            "q_min_m3h": (q_bajo * 3600.0) if q_bajo else None,
            "v_min": None if v_min in (None, "") else float(v_min),
            "v_max": None if v_max in (None, "") else float(v_max)}


ECUACIONES = [
    "A = π·Di²/4;   v = Q/A   (Q volumétrico a la condición de operación)",
    "Capacidad (líquido, densidad constante): Q_máx = v_máx·A",
    "Capacidad (gas y vapor): se resuelve el caudal de entrada tal que la velocidad gobernante del "
    "tramo (la de salida, con la caída de presión) iguale v_máx; v_máx·A con la densidad de entrada "
    "sobreestima la capacidad",
    "Diámetro requerido (preselección, con la condición de entrada): Di = √(4·Q/(π·v))",
]
