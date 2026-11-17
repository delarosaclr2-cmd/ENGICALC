"""Esquemas térmicos: torre de enfriamiento y secador rotatorio."""
from __future__ import annotations

from matplotlib.patches import Circle

from ..calculos import secador as SEC
from .base import C, cota, cuadro, flecha, limites, num, poligono, preparar, rectangulo


# ------------------------------------------------------------------------------------------ torre
def torre(fig, d: dict, r) -> None:
    ax = fig.add_subplot(1, 3, (1, 2))
    ax_t = fig.add_subplot(1, 3, 3)
    preparar(ax, "Torre de enfriamiento a contracorriente", False)
    # carcasa, relleno, distribución, ventilador y pileta
    poligono(ax, [(1.0, 0.6), (5.0, 0.6), (4.6, 5.2), (1.4, 5.2)], "#FAFAFA", C["estructura"], lw=1.8)
    rectangulo(ax, 1.25, 2.0, 3.5, 1.8, "#E0E0E0", C["tenue"], lw=0.8, hatch="xx")
    ax.text(3.0, 2.9, "Relleno", ha="center", va="center", fontsize=8,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))
    ax.plot([1.4, 4.6], [4.3, 4.3], color=C["caliente"], lw=2.0)
    for x in (1.8, 2.4, 3.0, 3.6, 4.2):
        flecha(ax, (x, 4.25), (x, 3.95), color=C["caliente"], lw=0.9)
    rectangulo(ax, 0.9, 0.0, 4.2, 0.6, "#BBDEFB", C["agua"], lw=1.4)
    rectangulo(ax, 2.2, 5.2, 1.6, 0.8, "#FAFAFA", C["estructura"], lw=1.6)
    ax.plot([2.4, 3.6], [5.6, 5.6], color=C["estructura"], lw=3)
    # agua
    flecha(ax, (6.3, 4.3), (4.65, 4.3), f"Agua caliente {num(d['t_entrada'], 1)} °C\n{num(d['flujo_agua'], 2)} kg/s",
           color=C["caliente"], alinear="left", lado_texto="inicio")
    flecha(ax, (5.1, 0.3), (6.3, 0.3), f"Agua fría {num(d['t_salida'], 1)} °C", color=C["frio"], alinear="left",
           lado_texto="fin")
    # aire
    hay_aire = d["t_bulbo_humedo"] > 0
    if hay_aire:
        entrada = f"Aire de entrada\nbh {num(d['t_bulbo_humedo'], 1)} °C"
        if d["t_bulbo_seco"] > 0:
            entrada += f" · bs {num(d['t_bulbo_seco'], 1)} °C"
        if "w_entrada" in r:
            entrada += f"\nω₁ = {num(r['w_entrada'], 4)} kg/kg"
        flecha(ax, (-0.6, 1.3), (1.05, 1.3), entrada, color=C["aire"], alinear="center", lado_texto="inicio")
        salida = "Aire de salida"
        if d["t_aire_salida"] > 0 and "w_salida" in r:
            salida += f"\n{num(d['t_aire_salida'], 1)} °C · HR {num(d['hr_aire_salida'], 0)} %\nω₂ = {num(r['w_salida'], 4)} kg/kg"
        flecha(ax, (3.0, 6.05), (3.0, 6.8), salida, color=C["aire"], alinear="center", lado_texto="fin")
        for y in (2.2, 3.0, 3.6):
            flecha(ax, (4.85, y - 0.3), (4.85, y + 0.2), color=C["aire"], lw=0.8)
    if "evaporacion_kgs" in r:
        flecha(ax, (-0.6, 0.3), (0.95, 0.3), f"Reposición ≈ {num(r['evaporacion_kgs'], 3)} kg/s", color=C["agua"],
               alinear="center", lado_texto="inicio")
    lineas = [f"Carga térmica: {num(r['carga_kw'], 1)} kW ({num(r['carga_tr'], 1)} TR)"]
    if "flujo_aire" in r:
        lineas.append(f"Aire seco: {num(r['flujo_aire'], 3)} kg/s · L/G = {num(r['relacion_lg'], 3)}")
    if "volumen_aire_entrada" in r:
        lineas.append(f"Caudal de aire a la entrada: {num(r['volumen_aire_entrada'], 2)} m³/s")
    if "kav_l" in r:
        lineas.append(f"KaV/L requerido (Merkel): {num(r['kav_l'], 3)}")
    cuadro(ax, lineas, x=1.0, y=0.0, ha="right", va="bottom")
    limites(ax, -2.2, 8.4, -2.3, 7.4, margen=0.02)

    # escala de temperaturas (a escala en °C)
    preparar(ax_t, "Temperaturas", True, "°C")
    th, tc = d["t_entrada"], d["t_salida"]
    tb = d["t_bulbo_humedo"] if hay_aire else None
    tmin = (tb if tb else tc) - 3
    tmax = th + 3
    rectangulo(ax_t, 0.0, tmin, 0.5, tmax - tmin, "#FAFAFA", C["tenue"], lw=0.8)
    marcas = [(th, "agua caliente", C["caliente"]), (tc, "agua fría", C["frio"])]
    if tb:
        marcas.append((tb, "bulbo húmedo", C["aire"]))
    for t, texto, color in marcas:
        ax_t.plot([-0.1, 0.6], [t, t], color=color, lw=1.6)
        ax_t.text(0.7, t, f"{texto} {num(t, 1)} °C", va="center", fontsize=7, color=color)
    cota(ax_t, (-0.15, tc), (-0.15, th), f"rango {num(th - tc, 1)}", desplazamiento=0.35, fs=7)
    if tb:
        cota(ax_t, (-0.15, tb), (-0.15, tc), f"aprox. {num(tc - tb, 1)}", desplazamiento=0.35, fs=7)
    ax_t.set_aspect("auto")
    ax_t.set_xlim(-1.2, 3.2)
    ax_t.set_ylim(tmin - 1, tmax + 1)


# ---------------------------------------------------------------------------------------- secador
def secador(fig, d: dict, r) -> None:
    D, L = r["diametro"], r["longitud"]
    u = max(D, L / 8.0)  # unidad para ubicar textos y flechas (el tambor sí se dibuja con D y L reales)
    contra = d.get("flujo") == SEC.CONTRACORRIENTE
    ax = fig.add_subplot(1, 1, 1)
    preparar(ax, "Secador rotatorio directo — " + ("contracorriente" if contra else "flujo paralelo"), True)
    rectangulo(ax, 0, 0, L, D, "#FAFAFA", C["estructura"], lw=2.0)
    # material en el fondo del tambor (indicativo) y aletas
    poligono(ax, [(0, 0), (L, 0), (L, 0.18 * D), (0, 0.12 * D)], C["material"], C["material_borde"], lw=0.5)
    for i in range(1, 12):
        x = i * L / 12
        ax.plot([x, x], [D, D - 0.12 * D], color=C["tenue"], lw=0.8)
    for x in (0.2 * L, 0.8 * L):  # aros de rodadura y rodillos de apoyo (indicativos)
        rectangulo(ax, x - 0.015 * L, -0.08 * D, 0.03 * L, D + 0.16 * D, C["relleno"], C["estructura"], lw=1)
        ax.add_patch(Circle((x, -0.08 * D - 0.07 * u), 0.06 * u, fc=C["relleno"], ec=C["estructura"], lw=1))
    rectangulo(ax, 0.55 * L - 0.012 * L, -0.12 * D, 0.024 * L, D + 0.24 * D, "#CFD8DC", C["estructura"], lw=1)
    ax.text(0.55 * L, -0.12 * D - 0.05 * u, "corona", ha="center", va="top", fontsize=6.5, color=C["tenue"])
    # sólidos: entran por la izquierda (por arriba), salen por la derecha (por abajo)
    flecha(ax, (0.12 * L, D + 1.0 * u), (0.06 * L, D + 0.05 * u),
           f"Alimentación {num(d['alimentacion'], 0)} kg/h · {num(d['humedad_inicial'], 1)} % · "
           f"{num(d['t_solido_entrada'], 0)} °C", color=C["material_borde"], alinear="center", lado_texto="inicio")
    flecha(ax, (L - 0.02 * L, 0.05 * D), (L + 0.05 * L, -0.75 * u),
           f"Producto {num(r['producto'], 0)} kg/h · {num(d['humedad_final'], 1)} % · {num(d['t_solido_salida'], 0)} °C",
           color=C["material_borde"], alinear="center", lado_texto="fin")
    # aire caliente según la disposición
    if contra:
        x0_cal, x_ent, x_sal, s = L + 0.04 * L, L, 0.0, -1
    else:
        x0_cal, x_ent, x_sal, s = -0.14 * L, 0.0, L, 1
    yc = D / 2
    rectangulo(ax, x0_cal, yc - 0.15 * u, 0.1 * L, 0.3 * u, "#FFCDD2", C["caliente"], lw=1.2)
    ax.text(x0_cal + 0.05 * L, yc, "calentador", ha="center", va="center", fontsize=6.5, color=C["caliente"])
    ax.text(x0_cal + 0.05 * L, yc - 0.22 * u, f"Aire {num(d['t_aire_entrada'], 0)} °C\n{num(r['aire_seco'], 0)} kg a.s./h",
            ha="center", va="top", fontsize=7, color=C["caliente"])
    x_cal = x0_cal + (0.1 * L if not contra else 0.0)
    flecha(ax, (x_cal, yc), (x_ent + s * 0.18 * L, yc), color=C["caliente"], lw=1.8)
    flecha(ax, (x_sal - s * 0.15 * L, 0.7 * D), (x_sal, 0.7 * D), color=C["frio"], lw=1.4)
    flecha(ax, (x_sal, 0.8 * D), (x_sal + s * 0.1 * L, D + 0.55 * u),
           f"Gases {num(d['t_aire_salida'], 0)} °C · HR {num(r['hr_salida'], 1)} %", color=C["frio"],
           alinear="center", lado_texto="fin")
    cota(ax, (0, D), (L, D), f"L = {num(L, 2)} m (L/D = {num(r['relacion_ld'], 1)})", desplazamiento=0.3 * u)
    if contra:
        cota(ax, (0, 0), (0, D), f"D = {num(D, 3)} m", desplazamiento=0.04 * L)
    else:
        cota(ax, (L, 0), (L, D), f"D = {num(D, 3)} m", desplazamiento=-0.04 * L)
    ax.text(L / 2, -0.3 * u, "Pendiente del tambor: no calculada (dibujo horizontal)", ha="center", va="top",
            fontsize=6.5, color=C["tenue"], style="italic")
    cuadro(ax, [f"Agua evaporada: {num(r['agua_evaporada'], 1)} kg/h",
                f"Calor total que cede el aire: {num(r['q_total'], 1)} kW",
                f"Ua: {num(r['ua'], 1)} W/(m³·K) · ΔT_ml {num(r['dtml'], 1)} °C",
                f"Volumen del tambor: {num(r['volumen'], 2)} m³",
                "Diámetro, longitud y Ua: estimación preliminar"], x=0.5, y=0.0, ha="center", va="bottom")
    limites(ax, -0.25 * L, 1.3 * L, -2.0 * u, D + 1.25 * u, margen=0.02)
