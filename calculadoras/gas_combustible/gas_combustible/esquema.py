"""Esquema del gas combustible: composición, diagrama de consumidores y consumos diarios. No calcula."""
from .ui.dibujo import COLORES, Escena

PALETA = ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF"]


def construir(c, out) -> Escena:
    pr = out["prop"]
    esc = Escena(c["nombre"], "Barras de composición en % mol (escala lineal; los componentes menores se leen en la etiqueta). "
                              "Flujos en kg/h y en m³/h a la condición de referencia.")
    # Composición
    comp = sorted(c["composicion"].items(), key=lambda kv: -kv[1])
    x0, ytop, ancho = 22.0, 150.0, 62.0
    esc.texto(x0, ytop + 6, "Composición (% mol)", 3.0, "w", negrita=True)
    for i, (k, v) in enumerate(comp):
        y = ytop - i * 5.2
        w = ancho * v / 100.0
        esc.rect(x0, y - 1.8, max(w, 0.3), 3.6, COLORES["acento"], "#9CC3E6", 0.2, info=f"{k}: {v:g} % mol")
        esc.texto(x0 - 1.5, y, k, 2.4, "e")
        esc.texto(x0 + max(w, 0.3) + 1.5, y, f"{v:g}", 2.3, "w", COLORES["suave"])
    yb = ytop - len(comp) * 5.2 - 4
    esc.texto(x0, yb, f"M = {pr.m_kg_kmol:.4f} kg/kmol · SG = {pr.sg_ideal:.4f}", 2.5, "w")
    esc.texto(x0, yb - 4.5, f"ρ ({pr.ref}) = {pr.rho_ref:.5f} kg/m³ · Z = {pr.z_ref:.5f}", 2.5, "w")

    # Diagrama de consumidores
    bx = 112.0
    flujos = out["flujos"]
    by = ytop - 26 if flujos else ytop - 30
    info_g = f"M = {pr.m_kg_kmol:.4f}; ρ_ref = {pr.rho_ref:.5f} kg/m³" + (
        f"; LHV lab = {out['lhv_lab']:,.0f} kJ/kg" if out["lhv_lab"] else "")
    esc.rect(bx, by, 40, 24, COLORES["linea"], "#FFF4E0", 0.5, info=info_g)
    esc.texto(bx + 20, by + 17, "GAS NATURAL", 3.0, negrita=True, info=info_g)
    esc.texto(bx + 20, by + 11, f"ρ = {pr.rho_ref:.4f} kg/m³", 2.4, info=info_g)
    if out["lhv_lab"]:
        esc.texto(bx + 20, by + 6, f"LHV = {out['lhv_lab']:,.0f} kJ/kg", 2.4, info=info_g)
    if out["rho_linea"]:
        rho_l, p, tk, z = out["rho_linea"]
        esc.texto(bx + 20, by - 4, f"Línea: {p/6894.757:.1f} psia, {tk-273.15:.0f} °C, ρ = {rho_l:.2f} kg/m³", 2.3, "n",
                  COLORES["suave"])
    total = sum(k for _, k in flujos) or 1.0
    for i, (nombre, kgh) in enumerate(flujos):
        y = by + 20 - i * 22
        cx = bx + 72
        q = kgh / pr.rho_ref
        info = f"{nombre}: {kgh:,.2f} kg/h = {q:,.2f} m³/h ref = {q*24:,.0f} m³/d ({kgh/total*100:.1f} % del total)"
        esc.flecha((bx + 40, by + 12), (cx, y + 6), COLORES["acento"], 0.4 + 1.6 * kgh / total, info=info)
        esc.rect(cx, y, 52, 13, COLORES["linea"], "#E8F1FA", 0.4, info=info)
        esc.texto(cx + 26, y + 9.5, (nombre if len(nombre) <= 30 else nombre[:29].rstrip() + "…"), 2.3, negrita=True, info=info)
        esc.texto(cx + 26, y + 5, f"{kgh:,.1f} kg/h", 2.4, info=info)
        esc.texto(cx + 26, y + 1.6, f"{q:,.1f} m³/h ref", 2.2, color=COLORES["suave"], info=info)
        if out["turbina"] and i == 0 and c.get("turbina"):
            t = c["turbina"]
            esc.texto(cx + 26, y - 2.5, f"HR {t['heat_rate_kj_kwh']:g} kJ/kWh · {t['potencia_kw']:g} kW", 2.1, "n",
                      COLORES["suave"])
    if len(flujos) > 1:
        esc.texto(bx + 20, by - 10, f"Total {total:,.1f} kg/h = {total/pr.rho_ref:,.1f} m³/h ref", 2.6, "n", negrita=True)

    # Consumos diarios (barras apiladas)
    cons = out["consumo"]
    if cons:
        cs = c["consumos"]
        n = len(cs["fechas"])
        ymax = max(cons.total_por_dia) * 1.12
        fondo = min(yb - 4.5, by - 10 - max(0, len(flujos) - 2) * 22 if flujos else by - 6)
        gx, gw, gh = 26.0, 216.0, 62.0
        gy = fondo - 16 - gh
        T = esc.grafica(gx, gy, gw, gh, (0, n), (0, ymax), "Consumo diario por unidad (barras apiladas)",
                        "Día", f"Consumo ({cs.get('unidad', 'm³/d').split(' ')[0]})", nx=min(n, 14), ny=5,
                        fmt_x="{:.0f}", fmt_y="{:,.0f}")
        for i, fecha in enumerate(cs["fechas"]):
            base = 0.0
            for j, u in enumerate(cons.unidades):
                v = cs["series"][u][i]
                if v <= 0:
                    continue
                p0, p1 = T(i + 0.12, base), T(i + 0.88, base + v)
                esc.rect(p0[0], p0[1], p1[0] - p0[0], p1[1] - p0[1], "#FFFFFF", PALETA[j % len(PALETA)], 0.05,
                         info=f"{fecha} · {u}: {v:,.0f}")
                base += v
            if fecha == cons.dia_max:
                px, py = T(i + 0.5, base)
                esc.texto(px, py + 1.5, f"máx. {base:,.0f}", 2.3, "s", COLORES["mal"], negrita=True,
                          info=f"Día de máximo coincidente: {fecha}")
        pm = T(0, cons.promedio)
        esc.linea([pm, T(n, cons.promedio)], COLORES["linea"], 0.35, guion=(2, 1),
                  info=f"Promedio diario: {cons.promedio:,.0f}")
        esc.texto(T(n, cons.promedio)[0] + 1, pm[1], f"prom. {cons.promedio:,.0f}", 2.2, "w")
        for j, u in enumerate(cons.unidades):
            lx = gx + (j % 4) * 55
            ly = gy - 12 - (j // 4) * 4.5
            esc.rect(lx, ly - 1.4, 3, 2.8, "#FFFFFF", PALETA[j % len(PALETA)], 0.05)
            esc.texto(lx + 4, ly, u, 2.3, "w")
    return esc
