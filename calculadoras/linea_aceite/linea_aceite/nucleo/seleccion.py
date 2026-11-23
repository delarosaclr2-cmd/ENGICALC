"""Velocidad en función del caudal y del diámetro: capacidad de la línea y selección de diámetro.

Relaciones básicas (las mismas que usan las memorias PCGV-DM-011/012/017):

    A = π·Di²/4                 área interior real (Di de ASME B36.10M, NO el diámetro nominal)
    v = Q / A                   Q es el caudal VOLUMÉTRICO A LA CONDICIÓN DE OPERACIÓN
    Q_máx = v_máx · A           caudal que agota el criterio de velocidad: capacidad de la línea
    Di_req = √(4·Q/(π·v))       diámetro interior necesario para una velocidad objetivo

Para gas y vapor, Q es el caudal real (no el referido a condiciones normales): Q = ṁ·ν = ṁ/ρ a la
presión y temperatura del punto que se evalúa. La velocidad crece a lo largo de la línea conforme
cae la presión: el MÁXIMO se juzga con la mayor del tramo (la de salida) y el MÍNIMO con la menor
(la de entrada), igual que en el dictamen del tramo.

Valores mostrados: un caudal límite se redondea hacia el lado que conserva el criterio (capacidad
máxima hacia abajo, caudal mínimo hacia arriba) y se comprueba al reintroducirlo, para que el número
que se anuncia nunca contradiga el dictamen. El criterio físico no se relaja.

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


def redondeo_seguro(x: float, decimales: int, lado: str) -> float:
    """Redondea al número de decimales que se muestra, hacia el lado que conserva el criterio.

    lado "abajo" (piso) para una capacidad máxima; "arriba" (techo) para un caudal mínimo o un
    diámetro requerido. El redondeo al más cercano puede pasar el límite: 3,026.149… Nm³/h se
    mostraba como 3,026.15, que al reintroducirse daba 15.00001 m/s y NO CUMPLE frente a 15 m/s.
    """
    if lado not in ("abajo", "arriba"):
        raise ValueError("lado debe ser 'abajo' o 'arriba'")
    f = 10 ** decimales
    return (math.floor(x * f) if lado == "abajo" else math.ceil(x * f)) / f


def ajustar_al_criterio(q, v_objetivo, v_de_q, lado: str = "abajo", max_iter: int = 20):
    """Comprueba un caudal con el modelo del DICTAMEN y lo corrige hasta que quede del lado que
    cumple: "abajo" → v(q) ≤ v_objetivo (capacidad máxima); "arriba" → v(q) ≥ v_objetivo.

    Hace falta cuando el caudal se resolvió con un modelo más barato (en vapor, la marcha con menos
    segmentos): la diferencia es de cienmilésimas, pero basta para que el valor anunciado dictamine
    NO CUMPLE. La corrección q·(v_obj/v)^1.5 queda siempre del lado seguro, porque la velocidad
    crece al menos linealmente con el caudal. Devuelve el caudal corregido, o None si no se logró.
    """
    if q is None or v_objetivo in (None, ""):
        return None
    v_objetivo = float(v_objetivo)
    for _ in range(max_iter):
        try:
            v = v_de_q(q)
        except Exception:                      # caudal inviable (flujo crítico, ΔP > P1)
            v = None
        if v is None or not math.isfinite(v) or v <= 0:
            if lado != "abajo":
                return None
            q *= 0.99                          # inviable por exceso de caudal: bajar
            continue
        if (v <= v_objetivo) if lado == "abajo" else (v >= v_objetivo):
            return q
        q *= (v_objetivo / v) ** 1.5
    return None


def limites_de_caudal(d_m: float, q_m3s: float, v_min=None, v_max=None, v_gobernante=None,
                      v_verificacion=None, v_actual=None) -> dict:
    """Caudales de ENTRADA (m³/s) en los límites del criterio de velocidad, del lado que cumple.

    Máximo  la velocidad que gobierna (la MAYOR del tramo) no debe exceder v_max. En un líquido
            v = Q/A y Q_máx = v_máx·A exacto. En gas y vapor se resuelve con `v_gobernante` y, si
            se da `v_verificacion` (el modelo con el que dictamina el tramo), se comprueba y corrige
            con él, para que la capacidad anunciada dictamine CUMPLE.
    Mínimo  la velocidad más BAJA del tramo (la de entrada, v = Q/A) no debe quedar debajo de
            v_min; es la que evalúa el dictamen. Q_mín = v_mín·A exacto en todos los fluidos.
    v_actual  velocidad gobernante al caudal capturado, si ya la calculó el dictamen (evita repetir
              la marcha del tramo); si se omite se calcula con el modelo del dictamen.

    Devuelve {"q_min", "q_max", "v_actual"}; un límite inalcanzable queda en None. Se calcula una
    sola vez y se comparte entre la tabla de capacidad y la curva, para que coincidan.
    """
    lim = {"q_min": None, "q_max": None, "v_actual": v_actual}
    if v_min not in (None, ""):
        lim["q_min"] = caudal_limite(d_m, float(v_min))
    if v_max not in (None, ""):
        vmax = float(v_max)
        if v_gobernante is None:
            lim["q_max"] = caudal_limite(d_m, vmax)
        else:
            q = caudal_limite_real(v_gobernante, vmax, q_m3s)
            if v_verificacion is not None:
                q = ajustar_al_criterio(q, vmax, v_verificacion, "abajo")
            lim["q_max"] = q
    if lim["v_actual"] is None:
        v_dict = v_verificacion or v_gobernante
        try:
            lim["v_actual"] = v_dict(q_m3s) if v_dict is not None else velocidad(q_m3s, d_m)
        except Exception:
            lim["v_actual"] = None
    return lim


def estado_velocidad(v: float, v_min=None, v_max=None, v_baja=None) -> str:
    """CUMPLE / NO CUMPLE / INFORMATIVO según el intervalo recomendado.

    v       velocidad con la que se juzga el máximo: la MAYOR del tramo (en gas y vapor, la salida).
    v_baja  velocidad con la que se juzga el mínimo: la MENOR del tramo (en gas y vapor, la
            entrada). Si se omite se usa v, como en un líquido, donde ambas son iguales.
    """
    v_low = v if v_baja is None else v_baja
    if v_max not in (None, "") and v > float(v_max):
        return "NO CUMPLE"
    if v_min not in (None, "") and v_low < float(v_min):
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
    calc        función d_m -> dict con al menos 'v' (la mayor del tramo); opcionalmente 'v_baja'
                (la menor, con la que se juzga el mínimo), 're', 'f', 'dp_pa', 'nota'
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
                      r.get("nota") or estado_velocidad(v, v_min, v_max, r.get("v_baja"))])
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
                    simbolo="Q", v_gobernante=None, donde_v="", v_verificacion=None,
                    limites=None) -> tuple:
    """Tabla (título, encabezados, filas, anchos) de capacidad de la línea: caudal contra velocidad.

    conv            función q_m3s -> valor en la unidad de presentación (por omisión m³/h). Debe
                    ser proporcional al caudal (conversión de unidades sin desplazamiento).
    v_gobernante    función q (m³/s a la entrada) -> velocidad que gobierna el máximo del tramo.
                    Para un LÍQUIDO se omite: la velocidad no cambia a lo largo de la línea, así
                    que v = Q/A basta. Para GAS y VAPOR debe darse, porque la velocidad crece al
                    caer la presión y v_máx·A con la densidad de entrada sobreestima la capacidad.
    v_verificacion  el modelo con el que DICTAMINA el tramo, si v_gobernante es una versión más
                    barata (vapor: menos segmentos). La capacidad se comprueba con él.
    limites         resultado de limites_de_caudal(), para no resolverlo dos veces.
    donde_v         dónde se evalúa la velocidad gobernante, p. ej. "a la salida" (para el título).

    Los caudales límite se muestran redondeados hacia el lado que cumple y se comprueban al
    reintroducirlos: la capacidad máxima mostrada dictamina CUMPLE y el caudal mínimo mostrado
    queda en el intervalo.
    """
    doble = conv is not None and unidad.replace(" ", "") not in ("m³/h", "m3/h")
    conv = conv or (lambda q: q * 3600.0)
    comp = v_gobernante is not None
    v_dict = v_verificacion or v_gobernante
    if limites is None:
        limites = limites_de_caudal(d_m, q_m3s, v_min, v_max, v_gobernante, v_verificacion)
    filas = []

    def cumple(q, lado, v_obj):
        """¿El caudal q, reintroducido, queda del lado que cumple? Con el modelo del dictamen."""
        if lado == "arriba":                       # mínimo: velocidad de entrada, v = Q/A
            return velocidad(q, d_m) >= v_obj
        try:
            v = v_dict(q) if comp else velocidad(q, d_m)
        except Exception:
            return False
        return v is not None and math.isfinite(v) and v <= v_obj

    def mostrado(q, lado, v_obj):
        """(valor en la unidad de presentación, caudal que representa), redondeado hacia el lado
        que cumple y comprobado; (None, None) si no se pudo garantizar."""
        val = conv(q)
        if not val or val <= 0:
            return None, None
        x = redondeo_seguro(val, 2, lado)
        paso = -0.01 if lado == "abajo" else 0.01
        for _ in range(50):
            if x <= 0:
                break
            q_x = q * x / val
            if cumple(q_x, lado, v_obj):
                return x, q_x
            x = round(x + paso, 2)
        return None, None

    def fila(etiqueta, v, q, nota, lado=None):
        v_txt = "—" if v is None else f"{v:.3f}"
        if q is None or v is None:
            filas.append([etiqueta, v_txt, "no alcanzable"] + (["—"] if doble else []) + [nota])
            return
        if lado is None:                           # dato capturado: se muestra tal cual
            val, real = conv(q), q * 3600.0
        else:
            val, _q = mostrado(q, lado, v)
            if val is None:
                filas.append([etiqueta, v_txt, "no verificable"] + (["—"] if doble else []) +
                             [nota + "; el valor redondeado no pudo comprobarse"])
                return
            # Columna en m³/h reales: del caudal límite comprobado, con su propio redondeo seguro
            # (no del valor ya redondeado en la otra unidad, que lo redondearía dos veces).
            real = redondeo_seguro(q * 3600.0, 3, lado)
        filas.append([etiqueta, v_txt, f"{val:,.2f}"] + ([f"{real:,.3f}"] if doble else []) + [nota])

    if v_min not in (None, ""):
        fila("Velocidad mínima recomendada", float(v_min), limites["q_min"],
             "caudal por debajo del cual la línea queda holgada"
             + (" (velocidad de entrada, la menor del tramo)" if comp else ""), lado="arriba")
    fila("Velocidad al caudal capturado", limites.get("v_actual"), q_m3s, "condición evaluada")
    if v_max not in (None, ""):
        nota = "CAPACIDAD MÁXIMA de la línea con este criterio"
        if comp:
            nota += f", resuelta con la caída de presión (velocidad {donde_v or 'gobernante'})"
        fila("Velocidad máxima recomendada", float(v_max), limites["q_max"], nota, lado="abajo")
    etiqueta_v = f"v {donde_v} (m/s)" if (comp and donde_v) else "v (m/s)"
    enc = ["Condición", etiqueta_v, f"{simbolo} ({unidad})"] + (["Q (m³/h real)"] if doble else []) + ["Nota"]
    anchos = [5.2, 2.0, 3.0] + ([3.0] if doble else []) + [4.4 if doble else 7.4]
    tit = f"Capacidad de la línea: caudal correspondiente a cada velocidad (Di = {d_m*1000:.2f} mm)"
    if comp:
        tit += f"; velocidad gobernante del tramo{(' ' + donde_v) if donde_v else ''}, " \
               "con la presión de entrada fija"
    tit += "; caudales límite redondeados hacia el lado que cumple"
    return (tit, enc, filas, anchos)


def curva(d_m: float, q_m3s: float, v_min=None, v_max=None, n: int = 24, v_gobernante=None,
          v_verificacion=None, limites=None) -> dict:
    """Puntos (Q en m³/h real a la entrada, v en m/s) para graficar la velocidad contra el caudal.

    Con `v_gobernante` la curva es la de la velocidad que gobierna la verificación (la mayor del
    tramo). Los caudales límite salen de limites_de_caudal(), los mismos de la tabla de capacidad.
    q_max_m3h / q_min_m3h son los valores SIN redondear: quien los muestre debe usar
    redondeo_seguro() (máximo hacia abajo, mínimo hacia arriba).
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

    if limites is None:
        limites = limites_de_caudal(d_m, q_m3s, v_min, v_max, v_gobernante, v_verificacion)
    q_lim, q_bajo = limites["q_max"], limites["q_min"]
    qmax = max(q_m3s * 2.0, (q_lim or 0.0) * 1.15)
    pts = [(qmax * i / n * 3600.0, vel(qmax * i / n)) for i in range(1, n + 1)]
    pts = [(q, v) for q, v in pts if v is not None]
    v_act = limites.get("v_actual")
    return {"puntos": pts, "q_actual_m3h": q_m3s * 3600.0,
            "v_actual": v_act if v_act is not None else vel(q_m3s),
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
    "Caudal mínimo: con la velocidad de ENTRADA, la menor del tramo: Q_mín = v_mín·A",
    "Diámetro requerido (preselección, con la condición de entrada): Di = √(4·Q/(π·v))",
    "Valores límite mostrados: capacidad máxima redondeada hacia abajo, caudal mínimo y diámetro "
    "requerido hacia arriba; la capacidad se comprueba con el modelo del dictamen al reintroducirla",
]
