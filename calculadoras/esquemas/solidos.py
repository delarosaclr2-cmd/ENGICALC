"""Esquemas de manejo de sólidos: silo, tolva, banda, helicoidal, elevador y aerodeslizador."""
from __future__ import annotations

import math
import re

from matplotlib.patches import Circle

from ..calculos import elevador as EL
from ..calculos import helicoidal as HE
from ..nucleo import solidos as SOL
from .base import (C, angulo, area_poligono, cota, cuadro, flecha, interrupcion, limites, num, poligono,
                   preparar, rectangulo, rotar)

# Relación paso/diámetro de cada opción de paso del helicoidal (el texto de la opción la indica).
PASO_RELATIVO = {"Estándar (paso = D)": 1.0, "Corto (paso = 2/3 D)": 2 / 3, "Medio (paso = 1/2 D)": 0.5,
                 "Largo (paso = 1.5 D)": 1.5}


# ------------------------------------------------------------------------------------------- silo
def perfil_janssen(d: dict, r, puntos: int = 40) -> list[tuple[float, float]]:
    """(profundidad z [m], p_h [kPa]) en el cilindro, con la misma función de Janssen del cálculo."""
    densidad = d["masa"] / r["volumen"]
    hc = r["altura_cilindro"]
    salida = []
    for i in range(puntos + 1):
        z = hc * i / puntos
        salida.append((z, SOL.janssen(z, densidad, d["diametro"], d["k"], d["mu"])["ph"] / 1000.0))
    return salida


def geometria_silo(d: dict, r) -> dict:
    D, d0 = d["diametro"], d["diametro_descarga"]
    ht, H = r["altura_tolva"], r["altura_total"]
    contorno = [(-d0 / 2, 0.0), (-D / 2, ht), (-D / 2, H), (D / 2, H), (D / 2, ht), (d0 / 2, 0.0)]
    return {"D": D, "d0": d0, "ht": ht, "hc": r["altura_cilindro"], "H": H, "contorno": contorno}


def silo(fig, d: dict, r) -> None:
    g = geometria_silo(d, r)
    D, d0, ht, hc, H = g["D"], g["d0"], g["ht"], g["hc"], g["H"]
    ax = fig.add_subplot(111)
    preparar(ax, "Silo metálico — elevación y presiones de llenado (Janssen)", True)

    poligono(ax, g["contorno"], C["material"], C["material_borde"], lw=0.6, alpha=0.75)
    xs, ys = zip(*g["contorno"])
    ax.plot(xs[:3], ys[:3], color=C["estructura"], lw=2.4)
    ax.plot(xs[3:], ys[3:], color=C["estructura"], lw=2.4)
    ax.plot([-D / 2, 0, D / 2], [H, H + 0.12 * D, H], color=C["estructura"], lw=1.6)  # techo (indicativo)
    ax.plot([-D / 2, D / 2], [ht, ht], color=C["estructura"], lw=0.8, ls="--")
    ax.text(0, ht + hc / 2, "Material\n(silo lleno)", ha="center", va="center", fontsize=8, color=C["texto"])

    # diagrama de presiones horizontales a la derecha de la pared
    x0 = D / 2 + 0.18 * D
    ph_max = r["ph_max"]
    escala = 0.55 * D / ph_max
    perfil = perfil_janssen(d, r)
    pts = [(x0, H)] + [(x0 + ph * escala, H - z) for z, ph in perfil] + [(x0, H - hc)]
    poligono(ax, pts, "#BBDEFB", C["aire"], lw=0.8, alpha=0.8)
    ax.plot([x0, x0], [H, ht], color=C["cota"], lw=0.8)
    ax.plot([x0 + ph_max * escala] * 2, [ht, H], color=C["frio"], lw=0.8, ls=":")
    ax.text(x0 + ph_max * escala, H + 0.04 * D, f"p_h,máx = {num(ph_max, 1)} kPa", ha="center", va="bottom",
            fontsize=7, color=C["frio"])
    ph_fondo = perfil[-1][1]
    ax.annotate(f"p_h = {num(ph_fondo, 1)} kPa\n(fondo del cilindro)", xy=(x0 + ph_fondo * escala, ht),
                xytext=(x0 + 0.62 * D, ht - 0.35 * ht), fontsize=7, color=C["frio"], ha="left",
                arrowprops=dict(arrowstyle="->", color=C["frio"], lw=0.7))
    ax.text(x0 + 0.02 * D, H - 0.03 * hc, "p_h(z)", fontsize=7, color=C["frio"], va="top")

    cota(ax, (-D / 2, H), (D / 2, H), f"D = {num(D, 2)} m", desplazamiento=0.32 * D)
    cota(ax, (-D / 2, ht), (-D / 2, H), f"h cilindro = {num(hc, 2)} m", desplazamiento=0.18 * D)
    cota(ax, (-D / 2, 0), (-D / 2, ht), f"h tolva = {num(ht, 2)} m", desplazamiento=0.18 * D)
    cota(ax, (-D / 2, 0), (-D / 2, H), f"H = {num(H, 2)} m", desplazamiento=0.42 * D)
    cota(ax, (d0 / 2, 0), (-d0 / 2, 0), f"d₀ = {num(d0, 3)} m", desplazamiento=0.12 * D)
    ax.plot([d0 / 2, d0 / 2], [0, 0.45 * ht], color=C["tenue"], lw=0.6, ls="--")
    angulo(ax, (d0 / 2, 0), 0.32 * ht, 90 - d["semiangulo"], 90, f"α = {num(d['semiangulo'], 0)}°",
           radio_texto=1.25, angulo_texto=45)
    flecha(ax, (0, -0.02 * D), (0, -0.30 * D), color=C["material_borde"])
    ax.text(-0.04 * D, -0.24 * D, f"Descarga ≈ {num(r['flujo_t_h'], 0)} t/h (Beverloo)", fontsize=7,
            color=C["material_borde"], va="center", ha="right")
    ax.annotate(f"t = {num(r['espesor_adoptado'], 1)} mm (adoptado)", xy=(-D / 2, ht + 0.25 * hc),
                xytext=(-D / 2 + 0.12 * D, ht + 0.25 * hc), fontsize=7, va="center", color=C["estructura"],
                arrowprops=dict(arrowstyle="->", color=C["estructura"], lw=0.7))

    cuadro(ax, [f"Masa: {num(d['masa'] / 1000, 1)} t", f"Volumen: {num(r['volumen'], 1)} m³",
                f"p_h diseño: {num(r['ph_diseno'], 1)} kPa", f"Compresión axial: {num(r['n_axial'], 1)} kN/m",
                "PREDIMENSIONAMIENTO", "no apto para diseño estructural"], titulo="Datos del cálculo",
          y=0.0, va="bottom")
    limites(ax, -D / 2 - 0.6 * D, x0 + 1.15 * D, -0.35 * D, H + 0.45 * D)


# ------------------------------------------------------------------------------------------ tolva
def tolva(fig, d: dict, r) -> None:
    a, d0, h = r["lado_superior"], r["diametro_descarga"], r["altura"]
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.3, wspace=0.15)
    preparar(ax1, "Tolva — vista frontal", True)
    contorno = [(-d0 / 2, 0), (-a / 2, h), (a / 2, h), (d0 / 2, 0)]
    poligono(ax1, contorno, C["material"], C["material_borde"], lw=0.6, alpha=0.75)
    ax1.plot(*zip(*contorno), color=C["estructura"], lw=2.2)
    ax1.plot([-a / 2, a / 2], [h, h], color=C["estructura"], lw=1.0)
    rectangulo(ax1, -d0 / 2, -0.08 * h, d0, 0.08 * h, C["relleno"], C["estructura"], lw=1.2)
    cota(ax1, (-a / 2, h), (a / 2, h), f"lado = {num(a, 3)} m", desplazamiento=0.12 * h)
    cota(ax1, (-a / 2, 0), (-a / 2, h), f"h = {num(h, 3)} m", desplazamiento=0.10 * a)
    cota(ax1, (d0 / 2, -0.08 * h), (-d0 / 2, -0.08 * h), f"d₀ = {num(d0, 3)} m", desplazamiento=0.12 * h)
    angulo(ax1, (d0 / 2, 0), 0.22 * h, 0, r["angulo_plano"], f"{num(r['angulo_plano'], 1)}°")
    flecha(ax1, (0, -0.1 * h), (0, -0.4 * h), color=C["material_borde"])
    ax1.text(0.05 * a, -0.32 * h, f"{num(r['flujo_t_h'], 0)} t/h", fontsize=7, color=C["material_borde"])
    limites(ax1, -a / 2 - 0.3 * a, a / 2 + 0.15 * a, -0.5 * h, h + 0.3 * h)

    preparar(ax2, "Vista en planta", True)
    rectangulo(ax2, -a / 2, -a / 2, a, a, "#F5F5F5", C["estructura"], lw=1.8)
    ax2.add_patch(Circle((0, 0), d0 / 2, fc=C["relleno"], ec=C["estructura"], lw=1.6))
    rho = d0 / 2
    for sx in (-1, 1):
        for sy in (-1, 1):  # aristas (valles): de cada esquina al círculo
            ax2.plot([sx * a / 2, sx * rho / math.sqrt(2)], [sy * a / 2, sy * rho / math.sqrt(2)],
                     color=C["carga"], lw=1.0)
    for px, py in ((0, a / 2), (0, -a / 2), (a / 2, 0), (-a / 2, 0)):  # líneas de las caras planas
        ax2.plot([px, px * rho / (a / 2)], [py, py * rho / (a / 2)], color=C["tenue"], lw=0.8, ls="--")
    cota(ax2, (-a / 2, a / 2), (a / 2, a / 2), f"{num(a, 3)} m", desplazamiento=0.1 * a)
    ok = r["angulo_arista"] > r["angulo_reposo"]
    cuadro(ax2, [f"Volumen: {num(r['volumen'], 2)} m³",
                 f"Ángulo de la cara: {num(r['angulo_plano'], 1)}°",
                 f"Ángulo de la arista (rojo): {num(r['angulo_arista'], 1)}°",
                 f"Ángulo de reposo: {num(r['angulo_reposo'], 0)}° → "
                 + ("arista más inclinada" if ok else "¡arista más tendida que el reposo!"),
                 f"Tiempo de vaciado: {num(r['tiempo_vaciado'], 2)} min"], x=0.5, y=-0.12, ha="center", va="top")
    limites(ax2, -a / 2 - 0.1 * a, a / 2 + 0.1 * a, -a / 2 - 0.1 * a, a / 2 + 0.25 * a)


# ------------------------------------------------------------------------------------------ banda
def seccion_banda(d: dict, r) -> dict:
    """Polígonos de la sección de material con la geometría de ISO 5048 que usa el cálculo."""
    b = r["ancho_util"] / 1000.0
    l3 = r["rodillo_central"] / 1000.0
    lam, beta = math.radians(d["angulo_artesa"]), math.radians(d["angulo_sobrecarga"])
    lado = (b - l3) / 2.0
    w = l3 + 2.0 * lado * math.cos(lam)
    y0 = lado * math.sin(lam)
    artesa = [(-l3 / 2, 0.0), (l3 / 2, 0.0), (w / 2, y0), (-w / 2, y0)]
    n = 80
    sobre = [(-w / 2 + w * i / n, y0 + math.tan(beta) / w * (w ** 2 / 4 - (-w / 2 + w * i / n) ** 2))
             for i in range(n + 1)]
    return {"b": b, "l3": l3, "w": w, "y0": y0, "artesa": artesa, "sobrecarga": sobre}


def banda(fig, d: dict, r) -> None:
    s = seccion_banda(d, r)
    B = d["ancho"] / 1000.0
    l3, w, y0 = s["l3"], s["w"], s["y0"]
    lam = math.radians(d["angulo_artesa"])
    droll = r["rodillo"] / 1000.0
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)

    fig.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.3, wspace=0.15)
    preparar(ax1, "Banda — sección (ISO 5048)", True)
    poligono(ax1, s["artesa"], C["material"], C["material_borde"], lw=0.6, alpha=0.9)
    poligono(ax1, s["sobrecarga"], "#E6CFA8", C["material_borde"], lw=0.6, alpha=0.9)
    alas = (B - l3) / 2.0
    u = (math.cos(lam), math.sin(lam))
    banda_x = [-l3 / 2 - alas * u[0], -l3 / 2, l3 / 2, l3 / 2 + alas * u[0]]
    banda_y = [alas * u[1], 0, 0, alas * u[1]]
    ax1.plot(banda_x, banda_y, color="#212121", lw=2.4)
    # rodillos (debajo de la banda)
    rectangulo(ax1, -l3 / 2, -droll, l3, droll, C["relleno"], C["estructura"], lw=1)
    largo_ala = min(l3, alas)
    for signo in (1, -1):
        p0 = (signo * (l3 / 2 + 0.02 * l3), 0.0)
        ux, uy = signo * u[0], u[1]
        nx, ny = signo * math.sin(lam), -math.cos(lam)
        esquinas = [p0, (p0[0] + ux * largo_ala, p0[1] + uy * largo_ala),
                    (p0[0] + ux * largo_ala + nx * droll, p0[1] + uy * largo_ala + ny * droll),
                    (p0[0] + nx * droll, p0[1] + ny * droll)]
        poligono(ax1, esquinas, C["relleno"], C["estructura"], lw=1)
    ax1.text(0, s["y0"] / 2, f"A₂ = {num(r['area_artesa'], 4)} m²", ha="center", va="center", fontsize=7)
    pico = y0 + math.tan(math.radians(d["angulo_sobrecarga"])) * w / 4
    ax1.text(0, y0 + 0.45 * (pico - y0), f"A₁ = {num(r['area_sobrecarga'], 4)} m²", ha="center", va="center",
             fontsize=7)
    cota(ax1, (-w / 2, y0), (w / 2, y0), f"ancho de material {num(w * 1000, 0)} mm", desplazamiento=pico - y0
         + 0.08 * B)
    cota(ax1, (l3 / 2, -droll), (-l3 / 2, -droll), f"l₃ = {num(l3 * 1000, 0)} mm", desplazamiento=0.06 * B)
    angulo(ax1, (l3 / 2, 0), 0.16 * B, 0, d["angulo_artesa"], f"λ = {num(d['angulo_artesa'], 0)}°")
    angulo(ax1, (-w / 2, y0), 0.16 * B, 0, d["angulo_sobrecarga"], "")
    medio = math.radians(d["angulo_sobrecarga"] / 2)
    ax1.annotate(f"β = {num(d['angulo_sobrecarga'], 0)}°",
                 xy=(-w / 2 + 0.16 * B * math.cos(medio), y0 + 0.16 * B * math.sin(medio)),
                 xytext=(-B / 2 - 0.02 * B, y0 + 0.22 * B), fontsize=7, ha="center",
                 arrowprops=dict(arrowstyle="->", color=C["cota"], lw=0.6))
    ax1.text(0, -droll - 0.2 * B, f"Banda B = {num(B * 1000, 0)} mm · ancho útil b = {num(s['b'] * 1000, 0)} mm"
             f"\nRodillos Ø{num(r['rodillo'], 0)} mm", ha="center", va="top", fontsize=7)
    limites(ax1, -B / 2 - 0.05 * B, B / 2 + 0.05 * B, -droll - 0.38 * B, pico + 0.3 * B)

    preparar(ax2, "Perfil longitudinal", True)
    L, delta = d["longitud"], d["inclinacion"]
    H = r["altura"]
    xc, yc = L * math.cos(math.radians(delta)), L * math.sin(math.radians(delta))
    rt = max(r["tambor"] / 2000.0, 0.004 * L)
    nx, ny = -math.sin(math.radians(delta)), math.cos(math.radians(delta))
    ax2.plot([nx * rt, xc + nx * rt], [ny * rt, yc + ny * rt], color="#212121", lw=1.8)
    ax2.plot([-nx * rt, xc - nx * rt], [-ny * rt, yc - ny * rt], color="#212121", lw=1.0)
    capa = 0.012 * L
    poligono(ax2, [(nx * rt, ny * rt), (xc + nx * rt, yc + ny * rt), (xc + nx * (rt + capa), yc + ny * (rt + capa)),
                   (nx * (rt + capa), ny * (rt + capa))], C["material"], C["material_borde"], lw=0.4)
    for x, y, txt in ((0, 0, "Cola"), (xc, yc, "Cabeza\n(motriz)")):
        ax2.add_patch(Circle((x, y), rt, fc=C["relleno"], ec=C["estructura"], lw=1.2, zorder=3))
        ax2.text(x, y + 0.06 * L, txt, ha="center", va="bottom", fontsize=7)
    flecha(ax2, (0.3 * xc + nx * 0.06 * L, 0.3 * yc + ny * 0.06 * L), (0.55 * xc + nx * 0.06 * L,
                                                                       0.55 * yc + ny * 0.06 * L),
           color=C["material_borde"])
    cota(ax2, (0, 0), (xc, yc), f"L = {num(L, 1)} m", desplazamiento=0.12 * L)
    if abs(H) > 1e-9:
        cota(ax2, (xc, 0), (xc, yc), f"H = {num(H, 2)} m", desplazamiento=-0.08 * L)
        ax2.plot([0, xc], [0, 0], color=C["tenue"], lw=0.6, ls="--")
        angulo(ax2, (0, 0), 0.18 * L, min(0, delta), max(0, delta), f"δ = {num(delta, 1)}°", radio_texto=1.25,
               angulo_texto=-6 if delta > 0 else 6)
    cuadro(ax2, [f"v = {num(r['velocidad'], 2)} m/s", f"Capacidad: {num(r['capacidad_th'], 0)} t/h "
                 f"({num(r['capacidad_m3h'], 0)} m³/h)", f"Fuerza tangencial: {num(r['fuerza_tangencial'], 1)} kN",
                 f"Potencia en el tambor: {num(r['potencia_tambor'], 1)} kW",
                 f"Potencia del motor: {num(r['potencia_motor'], 1)} kW"], x=0.5, y=-0.12, ha="center", va="top")
    limites(ax2, -0.05 * L, xc + 0.22 * L, min(0, yc) - 0.12 * L, max(0, yc) + 0.2 * L)


# ------------------------------------------------------------------------------------- helicoidal
def segmento_por_fraccion(radio: float, fraccion: float) -> float:
    """Altura del segmento circular cuya área es 'fraccion' del círculo (bisección geométrica)."""
    def area(hh):
        return radio ** 2 * math.acos((radio - hh) / radio) - (radio - hh) * math.sqrt(max(0.0, 2 * radio * hh - hh * hh))
    objetivo = fraccion * math.pi * radio ** 2
    lo, hi = 0.0, 2 * radio
    for _ in range(60):
        medio = (lo + hi) / 2
        if area(medio) < objetivo:
            lo = medio
        else:
            hi = medio
    return (lo + hi) / 2


def carga_helicoidal(r) -> float:
    m = re.match(r"\s*(\d+(?:\.\d+)?)", str(r["clase_carga"]))
    return float(m.group(1)) / 100.0 if m else 0.30


def helicoidal(fig, d: dict, r) -> None:
    D = r["diametro_mm"] / 1000.0
    L = d["longitud"]
    paso = PASO_RELATIVO.get(d["paso"], 1.0) * D
    ang = d["angulo"]
    fraccion = carga_helicoidal(r)
    ax1 = fig.add_subplot(2, 1, 1)
    ax2 = fig.add_subplot(2, 2, 3)
    ax3 = fig.add_subplot(2, 2, 4)

    preparar(ax1, "Transportador helicoidal — elevación (use el zoom para ver la hélice)", True)
    holgura = 0.06 * D

    def dib(puntos, **kw):
        ax1.plot(*zip(*rotar(puntos, ang)), **kw)

    canal = [(0, -D / 2 - holgura), (L, -D / 2 - holgura), (L, D / 2 + 0.25 * D), (0, D / 2 + 0.25 * D),
             (0, -D / 2 - holgura)]
    dib(canal, color=C["estructura"], lw=1.4)
    dib([(-0.03 * L, 0), (L + 0.03 * L, 0)], color=C["estructura"], lw=2.0)
    x = 0.0
    while x + paso / 2 <= L:
        dib([(x, D / 2), (x + paso / 2, -D / 2)], color=C["cota"], lw=0.7)
        x += paso
    entrada = rotar([(0.06 * L, D + 0.6 * D), (0.06 * L, D / 2 + 0.3 * D)], ang)
    flecha(ax1, entrada[0], entrada[1], "Carga", color=C["material_borde"], lado_texto="inicio")
    salida = rotar([(0.94 * L, -D / 2 - holgura), (0.94 * L, -D / 2 - 1.4 * D)], ang)
    flecha(ax1, salida[0], salida[1], "Descarga", color=C["material_borde"], lado_texto="fin")
    motor = rotar([(L + 0.03 * L, -0.4 * D), (L + 0.03 * L + 1.2 * D, -0.4 * D), (L + 0.03 * L + 1.2 * D, 0.4 * D),
                   (L + 0.03 * L, 0.4 * D)], ang)
    poligono(ax1, motor, C["relleno"], C["estructura"], lw=1)
    p1, p2 = rotar([(0, D / 2 + 0.25 * D), (L, D / 2 + 0.25 * D)], ang)
    cota(ax1, p1, p2, f"L = {num(L, 2)} m", desplazamiento=0.9 * D)
    if ang > 0:
        ax1.plot([0, L], [0, 0], color=C["tenue"], lw=0.6, ls="--")
        angulo(ax1, (0, 0), 0.15 * L, 0, ang, f"{num(ang, 0)}°")
    xs, ys = zip(*rotar([(-0.1 * L, -2 * D), (L * 1.12, -2 * D), (-0.1 * L, 2.5 * D), (L * 1.12, 2.5 * D)], ang))
    limites(ax1, min(xs), max(xs), min(ys), max(ys), margen=0.02)

    preparar(ax2, "Sección transversal", True)
    R = D / 2
    rc = R + holgura
    canal_u = ([(-rc, R + 0.25 * D)] + [(rc * math.cos(t), rc * math.sin(t))
                                       for t in [math.pi + i * math.pi / 40 for i in range(41)]]
               + [(rc, R + 0.25 * D)])
    ax2.plot(*zip(*canal_u), color=C["estructura"], lw=2)
    hseg = segmento_por_fraccion(R, fraccion)
    yliq = -R + hseg
    xs_seg = math.sqrt(max(0.0, R ** 2 - yliq ** 2))
    angs = [math.atan2(yliq, -xs_seg) + i * (math.atan2(yliq, xs_seg) - math.atan2(yliq, -xs_seg) + 2 * math.pi) / 60
            for i in range(61)]
    segmento = [(R * math.cos(t), R * math.sin(t)) for t in angs]
    segmento = [p for p in segmento if p[1] <= yliq + 1e-12]
    poligono(ax2, segmento + [(xs_seg, yliq), (-xs_seg, yliq)], C["material"], C["material_borde"], lw=0.6)
    ax2.add_patch(Circle((0, 0), R, fc="none", ec=C["cota"], lw=0.9, ls="--"))
    ax2.add_patch(Circle((0, 0), 0.17 * D, fc=C["relleno"], ec=C["estructura"], lw=1.2))
    cota(ax2, (-R, R + 0.25 * D), (R, R + 0.25 * D), f"D = {num(r['diametro'], 0)} plg ({num(D * 1000, 0)} mm)",
         desplazamiento=0.12 * D)
    ax2.text(0, -R - 0.2 * D, f"Carga de la sección: {r['clase_carga']}", ha="center",
             va="top", fontsize=7)
    limites(ax2, -R - 0.2 * D, R + 0.2 * D, -R - 0.45 * D, R + 0.6 * D)

    ax3.axis("off")
    cuadro(ax3, [f"Capacidad: {num(d['capacidad'], 2)} t/h ({num(r['cfh_m3h'], 2)} m³/h)",
                 f"Diámetro: {num(r['diametro'], 0)} plg · paso {num(paso * 1000, 0)} mm",
                 f"Velocidad: {num(r['rpm'], 1)} rpm (máx. {num(r['rpm_maxima'], 0)} rpm)",
                 f"Potencia total: {num(r['tshp'], 2)} HP ({num(r['tshp_kw'], 2)} kW)",
                 f"Motor comercial: {num(r['motor_hp'], 0) if isinstance(r['motor_hp'], (int, float)) else r['motor_hp']} HP",
                 "Verificación: " + ("cumple" if r["cumple"] else "NO cumple")],
          x=0.0, y=0.9, ha="left", titulo="Resultados")


# --------------------------------------------------------------------------------------- elevador
def elevador(fig, d: dict, r) -> None:
    H = d["altura"]
    Dh = r["diametro_tambor"] / 1000.0
    Dt = d["diametro_cola"] / 1000.0 if d["diametro_cola"] > 0 else Dh
    paso = r["paso"] / 1000.0
    dims = EL.CANGILONES_MM.get(d["cangilon_tabla"])
    proy = dims[0] / 1000.0 if dims else 0.25 * paso
    alto_c = min(dims[2] / 1000.0 if dims else 0.6 * paso, 0.8 * paso)
    ax = fig.add_subplot(1, 2, 1)
    ax_d = fig.add_subplot(1, 2, 2)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.3, wspace=0.15)
    preparar(ax, "Elevador — elevación", True)
    ax.text(0.0, -0.07, "Tramo intermedio interrumpido: la altura real es la de la cota H.", transform=ax.transAxes,
            fontsize=6.5, color=C["tenue"], va="top", style="italic")

    tramo = max(3.0 * Dh, 4.0 * paso)       # alto dibujado a escala en cabeza y en cola
    hueco = 0.5 * tramo                      # espacio de la interrupción
    yc_cola = Dt / 2 + 0.25
    yc_cabeza = yc_cola + tramo + hueco + tramo
    ancho = Dh / 2 + proy + 0.12
    # carcasa
    for signo in (-1, 1):
        ax.plot([signo * ancho, signo * ancho], [0, yc_cola + tramo], color=C["estructura"], lw=1.6)
        ax.plot([signo * ancho, signo * ancho], [yc_cola + tramo + hueco, yc_cabeza + Dh / 2 + 0.15],
                color=C["estructura"], lw=1.6)
    ax.plot([-ancho, ancho], [0, 0], color=C["estructura"], lw=1.6)
    ax.plot([-ancho, ancho], [yc_cabeza + Dh / 2 + 0.15] * 2, color=C["estructura"], lw=1.6)
    interrupcion(ax, -ancho - 0.1, ancho + 0.1, yc_cola + tramo + hueco / 2, 0.08)
    for yc, dd in ((yc_cola, Dt), (yc_cabeza, Dh)):
        ax.add_patch(Circle((0, yc), dd / 2, fc=C["relleno"], ec=C["estructura"], lw=1.4, zorder=3))
    # bandas y cangilones (solo en los tramos visibles)
    for signo in (-1, 1):
        for y1, y2 in ((yc_cola, yc_cola + tramo), (yc_cola + tramo + hueco, yc_cabeza)):
            ax.plot([signo * Dh / 2] * 2, [y1, y2], color="#212121", lw=1.4)
            y = y1 + paso / 2
            while y + alto_c < y2:
                x0 = signo * Dh / 2
                if signo > 0:   # ramal de subida: cangilón lleno, boca hacia arriba
                    pts = [(x0, y), (x0 + proy, y + 0.3 * alto_c), (x0 + proy, y + alto_c), (x0, y + alto_c)]
                else:           # ramal de bajada: vacío, boca hacia abajo
                    pts = [(x0, y + alto_c), (x0 - proy, y + 0.7 * alto_c), (x0 - proy, y), (x0, y)]
                poligono(ax, pts, C["material"] if signo > 0 else "#FFFFFF", C["estructura"], lw=0.8, zorder=4)
                y += paso
    cota(ax, (ancho, yc_cola), (ancho, yc_cabeza), f"H = {num(H, 1)} m (cota real)", desplazamiento=-0.35)
    flecha(ax, (ancho + 0.5, 0.35), (ancho, 0.35), "Alimentación", color=C["material_borde"], alinear="left",
           lado_texto="inicio")
    flecha(ax, (-ancho, yc_cabeza - 0.3), (-ancho - 0.5, yc_cabeza - 0.8), "Descarga", color=C["material_borde"],
           alinear="right", lado_texto="fin")
    flecha(ax, (Dh / 2 + proy + 0.05, yc_cola + 0.4 * tramo), (Dh / 2 + proy + 0.05, yc_cola + 0.8 * tramo),
           color=C["ok"], lw=1.2)
    limites(ax, -ancho - 1.2, ancho + 1.4, -0.3, yc_cabeza + Dh / 2 + 0.6, margen=0.03)

    preparar(ax_d, "Detalle: tambor de cabeza", True)
    R = Dh / 2
    ax_d.add_patch(Circle((0, 0), R, fc=C["relleno"], ec=C["estructura"], lw=1.6))
    ax_d.plot([R, R], [-3 * paso, 0], color="#212121", lw=1.6)
    ax_d.plot([-R, -R], [-3 * paso, 0], color="#212121", lw=1.6)
    n_arco = max(1, int(math.pi * R / paso))
    for i in range(n_arco + 1):  # cangilones alrededor del tambor, separados un paso
        t = i * paso / R  # la banda abraza la mitad superior del tambor (de la derecha a la izquierda)
        if t > math.pi:
            break
        base = (R * math.cos(t), R * math.sin(t))
        rad = (math.cos(t), math.sin(t))
        tan = (math.sin(t), -math.cos(t))
        pts = [base, (base[0] + rad[0] * proy, base[1] + rad[1] * proy),
               (base[0] + rad[0] * proy + tan[0] * alto_c, base[1] + rad[1] * proy + tan[1] * alto_c),
               (base[0] + tan[0] * alto_c, base[1] + tan[1] * alto_c)]
        poligono(ax_d, pts, C["material"], C["estructura"], lw=0.8, zorder=4)
    for signo in (1, -1):  # cangilones en los ramales rectos: subida cargada (derecha), bajada vacía
        y = -paso
        while y > -3 * paso + 0.02:
            x0 = signo * R
            if signo > 0:
                pts = [(x0, y - alto_c), (x0 + proy, y - 0.7 * alto_c), (x0 + proy, y), (x0, y)]
            else:
                pts = [(x0, y), (x0 - proy, y - 0.3 * alto_c), (x0 - proy, y - alto_c), (x0, y - alto_c)]
            poligono(ax_d, pts, C["material"] if signo > 0 else "#FFFFFF", C["estructura"], lw=0.8, zorder=4)
            y -= paso
    cota(ax_d, (-R, R + proy), (R, R + proy), f"Ø tambor = {num(Dh * 1000, 0)} mm", desplazamiento=0.12)
    cota(ax_d, (R + proy, -2 * paso), (R + proy, -paso), f"paso {num(paso * 1000, 0)} mm", desplazamiento=-0.12)
    cuadro(ax_d, [f"v = {num(r['velocidad'], 2)} m/s", f"Capacidad: {num(r['capacidad_th'], 1)} t/h",
                  f"Potencia del motor: {num(r['potencia_motor'], 2)} kW",
                  f"Relación centrífuga v²/(g·R): {num(r['relacion_centrifuga'], 2)}",
                  f"Cangilón: {d['cangilon_tabla'] if dims else 'volumen capturado'}"],
          x=0.5, y=-0.12, ha="center", va="top")
    limites(ax_d, -R - proy - 0.3, R + proy + 0.6, -3 * paso - 0.1, R + proy + 0.4)


# --------------------------------------------------------------------------------- aerodeslizador
def aerodeslizador(fig, d: dict, r) -> None:
    W = d["ancho"] / 1000.0
    hb = d["altura_lecho"] / 1000.0
    alto_canal = max(3 * hb, 0.6 * W)
    camara = 0.45 * W
    ax1 = fig.add_subplot(1, 2, 1)
    ax2 = fig.add_subplot(1, 2, 2)
    fig.subplots_adjust(left=0.04, right=0.98, top=0.9, bottom=0.3, wspace=0.15)
    preparar(ax1, "Aerodeslizador — sección", True)
    rectangulo(ax1, -W / 2, -camara, W, camara + alto_canal, "#FFFFFF", C["estructura"], lw=1.8)
    rectangulo(ax1, -W / 2, -camara, W, camara, "#E3F2FD", C["estructura"], lw=1.2)
    rectangulo(ax1, -W / 2, -0.012 * W, W, 0.024 * W, "#B0BEC5", C["estructura"], lw=0.8, hatch="////", zorder=3)
    rectangulo(ax1, -W / 2, 0.012 * W, W, hb, C["material"], C["material_borde"], lw=0.6)
    for xi in (-0.3, 0.0, 0.3):
        flecha(ax1, (xi * W, -0.8 * camara), (xi * W, -0.2 * camara), color=C["aire"], lw=1.2)
    ax1.text(0, -camara - 0.03 * W, f"Aire: {num(r['caudal_aire_h'], 0)} m³/h" if "caudal_aire_h" in r
             else "Aire de fluidización", ha="center", va="top", fontsize=7, color=C["aire"])
    ax1.text(0, 0.012 * W + hb / 2, "lecho fluidizado", ha="center", va="center", fontsize=7)
    ax1.text(W / 2 + 0.03 * W, 0, "tela porosa", fontsize=7, va="center", color=C["estructura"])
    cota(ax1, (-W / 2, alto_canal), (W / 2, alto_canal), f"ancho = {num(W * 1000, 0)} mm", desplazamiento=0.08 * W)
    cota(ax1, (-W / 2, 0.012 * W), (-W / 2, 0.012 * W + hb), f"lecho {num(hb * 1000, 0)} mm",
         desplazamiento=0.12 * W)
    ax1.text(0, -camara - 0.14 * W, "Alturas de la cámara de aire y del canal:\nproporciones indicativas (no se calculan)",
             ha="center", va="top", fontsize=6.5, color=C["tenue"], style="italic")
    limites(ax1, -W / 2 - 0.3 * W, W / 2 + 0.35 * W, -camara - 0.45 * W, alto_canal + 0.2 * W)

    L, th = d["longitud"], d["inclinacion"]
    preparar(ax2, "Perfil longitudinal", L > 0)
    if L <= 0:
        ax2.text(0.5, 0.5, "Capture la longitud para dibujar el perfil\ny calcular el aire de fluidización.",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=8)
    else:
        t = math.radians(th)
        x1, y1 = L * math.cos(t), -L * math.sin(t)
        grosor = alto_canal + camara
        nx, ny = math.sin(t), math.cos(t)
        poligono(ax2, [(0, 0), (x1, y1), (x1 + nx * grosor, y1 + ny * grosor), (nx * grosor, ny * grosor)],
                 "#FFFFFF", C["estructura"], lw=1.2)
        f = camara / grosor
        poligono(ax2, [(nx * f * grosor, ny * f * grosor), (x1 + nx * f * grosor, y1 + ny * f * grosor),
                       (x1 + nx * (f * grosor + hb), y1 + ny * (f * grosor + hb)),
                       (nx * (f * grosor + hb), ny * (f * grosor + hb))], C["material"], C["material_borde"], lw=0.5)
        off = 0.10 * L
        flecha(ax2, (0.30 * x1 + nx * off, 0.30 * y1 + ny * off), (0.65 * x1 + nx * off, 0.65 * y1 + ny * off),
               color=C["material_borde"])
        ax2.text(0.47 * x1 + nx * 1.6 * off, 0.47 * y1 + ny * 1.6 * off, f"material {num(r['velocidad'], 1)} m/s",
                 fontsize=7, color=C["material_borde"], ha="center", rotation=-th, rotation_mode="anchor")
        flecha(ax2, (-0.12 * L, -0.12 * L), (0, 0.5 * camara), "aire del ventilador", color=C["aire"],
               alinear="center", lado_texto="inicio")
        cota(ax2, (0, 0), (x1, y1), f"L = {num(L, 1)} m", desplazamiento=-0.08 * L)
        if th > 0:
            cota(ax2, (x1, 0), (x1, y1), f"Δz = {num(L * math.sin(t), 2)} m", desplazamiento=-0.07 * L)
            ax2.plot([0, x1], [0, 0], color=C["tenue"], lw=0.6, ls="--")
            angulo(ax2, (0, 0), 0.35 * L, -th, 0, f"{num(th, 1)}°", radio_texto=1.12, angulo_texto=4)
        limites(ax2, -0.22 * L, x1 + 0.2 * L, y1 - 0.2 * L, 0.18 * L)
    lineas = [f"Capacidad: {num(r['capacidad_th'], 1)} t/h", f"Umf (Ergun): {num(r['u_mf'], 2)} mm/s",
              f"ΔP del lecho: {num(r['dp_lecho_fluidizado_mm'], 1)} mm H₂O"]
    if "u_superficial" in r:
        lineas.insert(1, f"u aire: {num(r['u_superficial'], 1)} mm/s → " + ("fluidiza" if r["fluidiza"] else "NO fluidiza"))
    cuadro(ax2, lineas, x=0.5, y=-0.12, ha="center", va="top")
