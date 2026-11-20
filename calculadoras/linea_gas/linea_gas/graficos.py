"""Piezas de dibujo comunes a las calculadoras de líneas (solo dibujan resultados ya calculados)."""
from __future__ import annotations

from .ui.dibujo import COLORES

VALVULAS = {"compuerta": "C", "globo": "G", "angulo": "A", "bola": "B", "check_columpio": "R",
            "check_columpio_t511": "R", "check_levantamiento": "RL"}


def tuberia(esc, x0, x1, yc, hp, relleno, etiqueta, info, detalle_k, cota):
    esc.rect(x0, yc - hp / 2, x1 - x0, hp, COLORES["linea"], relleno, 0.5, info=info)
    esc.texto(x0 + 0.15 * (x1 - x0), yc, etiqueta, 2.6, info=info)
    for i, (tipo, n, k, kt) in enumerate(detalle_k):
        xa = x0 + (x1 - x0) * (0.32 + 0.66 * (i + 0.5) / max(len(detalle_k), 1))
        inf = f"{n:g} × {tipo.replace('_', ' ')}: K = {k:.3f} c/u, ΣK = {kt:.3f}"
        if tipo in VALVULAS:
            h = hp * 0.95
            esc.poli([(xa - 3.5, yc - h / 2), (xa + 3.5, yc + h / 2), (xa + 3.5, yc - h / 2), (xa - 3.5, yc + h / 2)],
                     COLORES["linea"], "#FFFFFF", 0.4, info=inf)
            esc.texto(xa, yc + hp / 2 + 2.5, VALVULAS[tipo], 2.4, "s", negrita=True, info=inf)
        elif tipo.startswith("codo"):
            esc.linea([(xa - 3, yc + hp / 2), (xa - 3, yc + hp / 2 + 5), (xa + 2, yc + hp / 2 + 7)], COLORES["tubo"],
                      1.0, info=inf)
            esc.texto(xa, yc + hp / 2 + 8.5, "45°" if "45" in tipo else "90°", 2.3, "s", info=inf)
        else:
            esc.linea([(xa, yc + hp / 2), (xa, yc + hp / 2 + 7)], COLORES["tubo"], 1.4, info=inf)
            esc.texto(xa, yc + hp / 2 + 8.5, "T", 2.3, "s", info=inf)
        esc.texto(xa, yc - hp / 2 - 2.0, f"{n:g}×", 2.4, "n", info=inf)
    esc.cota((x0, yc - hp / 2 - 6), (x1, yc - hp / 2 - 6), cota, sep=-3.5)


def banda_velocidad(esc, x, y, w, v, v_min, v_max, fuente, unidad="m/s"):
    """Barra horizontal con el intervalo recomendado (verde) y la velocidad calculada (rombo)."""
    tope = max(v, v_max or 0, v_min or 0) * 1.2 or 1.0
    X = lambda q: x + w * q / tope
    esc.texto(x + w / 2, y + 7, f"Velocidad ({unidad})", 2.8, "s", negrita=True)
    esc.rect(x, y - 2.5, w, 5, COLORES["rejilla"], "#F4F4F4", 0.1)
    if v_max:
        lo = v_min or 0.0
        esc.rect(X(lo), y - 2.5, X(v_max) - X(lo), 5, COLORES["ok"], COLORES["banda"], 0.2,
                 info=f"Intervalo {lo:g}–{v_max:g} {unidad} · {fuente}")
    col = COLORES["mal"] if (v_max and v > v_max) else (COLORES["aviso"] if (v_min and v < v_min) else COLORES["ok"])
    esc.poli([(X(v), y + 3.2), (X(v) + 2, y), (X(v), y - 3.2), (X(v) - 2, y)], col, col, 0.2,
             info=f"v = {v:.3f} {unidad}")
    esc.texto(X(v), y - 4.5, f"{v:.2f}", 2.4, "n", col, negrita=True)
    for i in range(6):
        q = tope * i / 5
        esc.texto(X(q), y + 3.4, f"{q:.1f}", 2.0, "s", COLORES["suave"])


def barras(esc, x, y, w, titulo, items, unidad, fmt="{:.3f}"):
    """Barras horizontales de una descomposición (p. ej. ΔP por concepto)."""
    tope = max((abs(v) for _, v, _ in items), default=1.0) or 1.0
    esc.texto(x, y + 5, titulo, 2.8, "w", negrita=True)
    for i, (et, v, col) in enumerate(items):
        yy = y - i * 6.5
        esc.texto(x + 30, yy, et, 2.3, "e")
        largo = (w - 50) * abs(v) / tope
        esc.rect(x + 32, yy - 2, max(largo, 0.3), 4, col, col, 0.1, info=f"{et}: {fmt.format(v)} {unidad}")
        esc.texto(x + 33 + largo, yy, f"{fmt.format(v)} {unidad}", 2.3, "w")


def espesor(esc, x, y, r):
    """Comparación t_m requerido contra espesor nominal menos tolerancia (barras, en mm)."""
    mm = 1000.0
    items = [("t por presión", r["t_presion_m"] * mm, COLORES["acento"]),
             ("t_m = t + c", r["t_m_m"] * mm, COLORES["mal"] if not r["cumple"] else COLORES["tubo"]),
             ("nominal − tolerancia", r["t_disponible_m"] * mm, COLORES["ok"] if r["cumple"] else COLORES["aviso"]),
             ("nominal", r["t_nominal_m"] * mm, COLORES["acero"])]
    barras(esc, x, y, 110, f"Espesor de pared — {'CUMPLE' if r['cumple'] else 'NO CUMPLE'} "
                           f"(margen {r['margen']:.2f}×)", items, "mm", "{:.2f}")


def presiones(esc, x, y, r, psi=6894.757293168):
    """Presión máxima admisible por cada espesor y criterio, contra la presión de diseño (psig)."""
    c, b = r["codigo"], r.get("barlow")
    items = []
    for clave, et in (("nominal", "nominal"), ("nuevo", "tubo nuevo"), ("fin_vida", "fin de vida")):
        if c.get(clave):
            items.append((f"P máx. código, {et}", c[clave] / psi,
                          COLORES["ok"] if clave == "fin_vida" else COLORES["acero"]))
    if b:
        for clave, et in (("nominal", "nominal"), ("fin_vida", "fin de vida")):
            if b.get(clave):
                items.append((f"P máx. Barlow, {et}", b[clave] / psi, COLORES["acento"]))
    pd = r.get("p_diseno_pa")
    if pd:
        items.append(("P de diseño", pd / psi,
                      COLORES["mal"] if r.get("cumple") is False else COLORES["tubo"]))
    if r.get("p_operacion_pa"):
        items.append(("P de operación", r["p_operacion_pa"] / psi, COLORES["liquido"]))
    est = "" if r.get("cumple") is None else (" — CUMPLE" if r["cumple"] else " — NO CUMPLE")
    margen = f" (margen {r['margen_diseno']:.2f}×)" if r.get("margen_diseno") else ""
    barras(esc, x, y, 118, f"Presión máxima admisible{est}{margen}", items, "psig", "{:,.1f}")


def curva_velocidad(esc, x, y, w, h, cv, unidad="m³/h"):
    """Velocidad contra caudal para el diámetro elegido, con el intervalo recomendado y el punto
    de operación. cv es el diccionario que devuelve seleccion.curva()."""
    pts = cv["puntos"]
    if not pts:
        return
    qmax = max(q for q, _ in pts) or 1.0
    vmax_g = max(max(v for _, v in pts), cv["v_actual"], cv.get("v_max") or 0) * 1.1 or 1.0
    T = esc.grafica(x, y, w, h, (0, qmax), (0, vmax_g), "Velocidad contra caudal",
                    f"Caudal ({unidad})", "v (m/s)", fmt_x="{:,.0f}", fmt_y="{:.1f}")
    lo, hi = cv.get("v_min") or 0.0, cv.get("v_max")
    if hi:
        p0, p1 = T(0, lo), T(qmax, min(hi, vmax_g))
        esc.rect(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], COLORES["ok"], COLORES["banda"], 0.15,
                 info=f"Intervalo recomendado {lo:g}–{hi:g} m/s")
    esc.linea([T(q, v) for q, v in pts], COLORES["acento"], 0.5)
    qa, va = cv["q_actual_m3h"], cv["v_actual"]
    px, py = T(qa, va)
    col = COLORES["mal"] if (hi and va > hi) else (COLORES["aviso"] if (lo and va < lo) else COLORES["ok"])
    esc.circulo(px, py, 1.8, col, col, 0.2, info=f"Operación: {qa:,.2f} m³/h, {va:.3f} m/s")
    esc.texto(px, py + 3, f"{va:.2f} m/s", 2.4, "s", col, negrita=True)
    if cv.get("q_max_m3h"):
        p = T(cv["q_max_m3h"], min(hi, vmax_g))
        esc.linea([(p[0], y), (p[0], p[1])], COLORES["mal"], 0.25, guion=(1.2, 1.2))
        esc.texto(p[0] - 1.2, y + h * 0.06, f"capacidad {cv['q_max_m3h']:,.0f} {unidad}", 2.2, "w",
                  COLORES["mal"], rot=90, info="Caudal que agota el criterio de velocidad")
