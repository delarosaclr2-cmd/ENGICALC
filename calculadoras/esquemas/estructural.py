"""Esquema estructural: viga en voladizo o simplemente apoyada, con su sección transversal."""
from __future__ import annotations

from matplotlib.patches import Circle

from ..calculos import viga as V
from ..nucleo import constantes as K
from .base import C, cota, cuadro, flecha, limites, num, poligono, preparar, rectangulo


def peralte_dibujo(d: dict) -> float:
    """Peralte de la sección en m (para dibujar la viga con su altura real)."""
    s = d["seccion"]
    if s in (V.RECT, V.IVIGA):
        return d["h"] / 1000.0
    if s in (V.CIRC, V.TUBO):
        return d["d"] / 1000.0
    return 2 * d["c"] / 1000.0


def elastica(d: dict, puntos: int = 200) -> list[tuple[float, float]]:
    """(x [m], y [m] hacia abajo) con la misma función de respuesta que usa el cálculo."""
    L, a = d["longitud"], d["posicion"]
    P, w = d["carga_puntual"] * K.G, d["carga_distribuida"] * K.G
    EI = V.modulo_elasticidad(d)[0] * V.propiedades_seccion(d)["I"]
    return [(L * i / puntos, V.respuesta(d["tipo"], L, P, a, w, EI, L * i / puntos)[2]) for i in range(puntos + 1)]


def _seccion(ax, d: dict) -> None:
    s = d["seccion"]
    preparar(ax, "Sección transversal", True, "mm")
    if s == V.RECT:
        b, h = d["b"], d["h"]
        rectangulo(ax, -b / 2, -h / 2, b, h, "#CFD8DC", C["estructura"], lw=1.6)
        cota(ax, (-b / 2, h / 2), (b / 2, h / 2), f"b = {num(b, 0)}", desplazamiento=0.12 * h)
        cota(ax, (b / 2, -h / 2), (b / 2, h / 2), f"h = {num(h, 0)}", desplazamiento=-0.15 * max(b, h))
        ext = max(b, h)
    elif s in (V.CIRC, V.TUBO):
        dd = d["d"]
        ax.add_patch(Circle((0, 0), dd / 2, fc="#CFD8DC", ec=C["estructura"], lw=1.6))
        if s == V.TUBO:
            ax.add_patch(Circle((0, 0), dd / 2 - d["t"], fc="white", ec=C["estructura"], lw=1.2))
            ax.text(0, -dd / 2 + d["t"] / 2, f"t = {num(d['t'], 1)}", ha="center", va="bottom", fontsize=7)
        cota(ax, (-dd / 2, dd / 2), (dd / 2, dd / 2), f"d = {num(dd, 0)}", desplazamiento=0.12 * dd)
        ext = dd
    elif s == V.IVIGA:
        b, h, tf, tw = d["b"], d["h"], d["tf"], d["tw"]
        pts = [(-b / 2, h / 2), (b / 2, h / 2), (b / 2, h / 2 - tf), (tw / 2, h / 2 - tf), (tw / 2, -h / 2 + tf),
               (b / 2, -h / 2 + tf), (b / 2, -h / 2), (-b / 2, -h / 2), (-b / 2, -h / 2 + tf), (-tw / 2, -h / 2 + tf),
               (-tw / 2, h / 2 - tf), (-b / 2, h / 2 - tf)]
        poligono(ax, pts, "#CFD8DC", C["estructura"], lw=1.6)
        cota(ax, (-b / 2, h / 2), (b / 2, h / 2), f"b = {num(b, 0)}", desplazamiento=0.1 * h)
        cota(ax, (b / 2, -h / 2), (b / 2, h / 2), f"h = {num(h, 0)}", desplazamiento=-0.18 * max(b, h))
        ax.text(-tw / 2 - 0.03 * b, -0.15 * h, f"tw = {num(tw, 1)}", fontsize=7, va="center", ha="right")
        ax.text(-b / 2, h / 2 - tf / 2, f"tf = {num(tf, 1)} ", fontsize=7, va="center", ha="right")
        ext = max(b, h)
    else:
        c = d["c"]
        rectangulo(ax, -c, -c, 2 * c, 2 * c, "#ECEFF1", C["estructura"], lw=1.2)
        ax.text(0, 0, f"Sección personalizada\nI = {num(d['inercia'], 0)} cm⁴\nA = {num(d['area'], 1)} cm²",
                ha="center", va="center", fontsize=7)
        cota(ax, (c, -c), (c, c), f"2c = {num(2 * c, 0)}", desplazamiento=-0.3 * c)
        ax.text(0, -1.25 * c, "(forma no conocida: se dibuja un recuadro de peralte 2c)", ha="center", va="top",
                fontsize=6.5, color=C["tenue"])
        ext = 2 * c
    ax.plot([-0.75 * ext, 0.75 * ext], [0, 0], color=C["carga"], lw=0.8, ls="-.")
    ax.text(0.76 * ext, 0, "eje neutro", fontsize=6.5, color=C["carga"], va="center")
    limites(ax, -0.85 * ext, 1.2 * ext, -0.95 * ext, 0.85 * ext)


def viga(fig, d: dict, r) -> None:
    L, a = d["longitud"], d["posicion"]
    voladizo = d["tipo"] == V.VOLADIZO
    h = peralte_dibujo(d)
    ax = fig.add_subplot(1, 3, (1, 2))
    ax_s = fig.add_subplot(1, 3, 3)
    preparar(ax, "Viga " + ("en voladizo" if voladizo else "simplemente apoyada") + " — elevación", True)
    rectangulo(ax, 0, -h / 2, L, h, "#CFD8DC", C["estructura"], lw=1.4, zorder=2)
    # apoyos
    if voladizo:
        rectangulo(ax, -0.06 * L, -max(h, 0.15 * L), 0.06 * L, 2 * max(h, 0.15 * L), "#ECEFF1", C["estructura"],
                   lw=1.2, hatch="////")
    else:
        for x in (0.0, L):
            poligono(ax, [(x, -h / 2), (x - 0.035 * L, -h / 2 - 0.06 * L), (x + 0.035 * L, -h / 2 - 0.06 * L)],
                     "#ECEFF1", C["estructura"], lw=1.2)
        for dx in (-0.018, 0.018):
            ax.add_patch(Circle((L + dx * L, -h / 2 - 0.068 * L), 0.008 * L, fc="white", ec=C["estructura"], lw=1))
    # cargas
    alto_flecha = 0.16 * L
    if d["carga_distribuida"] > 0:
        y0 = h / 2 + 0.02 * L
        ax.plot([0, L], [y0 + 0.08 * L] * 2, color=C["carga"], lw=1.0)
        for i in range(13):
            x = L * i / 12
            flecha(ax, (x, y0 + 0.08 * L), (x, y0), color=C["carga"], lw=0.9)
        w = d["carga_distribuida"]
        ax.text(L / 2, y0 + 0.1 * L, f"w = {num(w, 1)} kg/m ({num(w * K.G / 1000, 2)} kN/m)", ha="center",
                va="bottom", fontsize=7.5, color=C["carga"])
    if d["carga_puntual"] > 0:
        y_base = h / 2 + (0.2 * L if d["carga_distribuida"] > 0 else 0.0)
        flecha(ax, (a, y_base + alto_flecha), (a, y_base + 0.005 * L), color=C["carga"], lw=2.0)
        P = d["carga_puntual"]
        ax.text(a, y_base + alto_flecha + 0.01 * L, f"P = {num(P, 1)} kg ({num(P * K.G / 1000, 2)} kN)",
                ha="center", va="bottom", fontsize=7.5, color=C["carga"])
        if 0 < a < L:
            cota(ax, (0, -h / 2), (a, -h / 2), f"a = {num(a, 3)} m", desplazamiento=-0.17 * L)
    # reacciones
    if voladizo:
        ax.text(0.01 * L, -h / 2 - 0.08 * L, f"R = {num(r['reaccion'], 2)} kN\nM = {num(r['momento_empotramiento'], 2)} kN·m",
                fontsize=7, va="top", color=C["ok"])
    else:
        for x, clave in ((0.0, "reaccion_izq"), (L, "reaccion_der")):
            flecha(ax, (x, -h / 2 - 0.2 * L), (x, -h / 2 - 0.08 * L), color=C["ok"], lw=1.4)
            ax.text(x, -h / 2 - 0.21 * L, f"{num(r[clave], 2)} kN", ha="center", va="top", fontsize=7, color=C["ok"])
    # deformada amplificada
    curva = elastica(d)
    ymax = max(abs(y) for _, y in curva) or 1.0
    factor = 0.12 * L / ymax
    ax.plot([x for x, _ in curva], [-y * factor for _, y in curva], color=C["caliente"], lw=1.4, ls="--", zorder=4)
    ax.text(0.5 * L, -h / 2 - (0.3 * L if not voladizo else 0.2 * L), f"Deformada amplificada ×{num(factor, 0)} · δmáx = {num(r['deflexion_max'], 3)} mm"
            f" (límite {num(r['deflexion_limite'], 2)} mm)" if "deflexion_limite" in r else
            f"Deformada amplificada ×{num(factor, 0)} · δmáx = {num(r['deflexion_max'], 3)} mm",
            ha="center", va="top", fontsize=7, color=C["caliente"])
    cota(ax, (0, h / 2), (L, h / 2), f"L = {num(L, 3)} m", desplazamiento=0.42 * L if d["carga_puntual"] > 0
         and d["carga_distribuida"] > 0 else 0.3 * L)
    lineas = [f"V máx = {num(r['cortante_max'], 2)} kN", f"M máx = {num(r['momento_max'], 2)} kN·m",
              f"σ flexión = {num(r['esfuerzo_flexion'], 1)} MPa", f"τ máx = {num(r['esfuerzo_cortante'], 2)} MPa",
              f"E = {num(r['modulo_e'], 0)} GPa · I = {num(r['inercia'], 1)} cm⁴"]
    cuadro(ax, lineas, x=1.0, y=0.0, ha="right", va="bottom")
    limites(ax, -0.12 * L, 1.1 * L, -0.55 * L, 0.6 * L, margen=0.02)
    _seccion(ax_s, d)
