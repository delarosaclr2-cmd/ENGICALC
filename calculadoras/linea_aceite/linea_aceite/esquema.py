"""Esquema de la línea de aceite (sin escala) y curva viscosidad-temperatura. Solo dibuja resultados del motor."""
import math

from .nucleo import aceite as ac
from .nucleo import graficos as gr
from .nucleo.unidades import PSI
from .ui.dibujo import COLORES, Escena


def construir(c, res) -> Escena:
    t = res["tramo"]
    esc = Escena(c["nombre"], "Esquema sin escala. Alturas en metros del ACEITE que circula; ΔP = ρ·g·h. "
                              "Curva ν–T según ASTM D341 (Menon ecs. 6.13–6.16).")
    x0, x1, yc, hp = 40.0, 230.0, 110.0, 8.0
    tub = c["tuberia"]
    etq = (f"NPS {tub['nps']} céd. {tub.get('cedula', '')} · " if tub.get("nps") else "") + f"Di {res['d']*1000:.1f} mm"
    info = (f"Q = {res['q']*60000:.1f} L/min · v = {t['v']:.3f} m/s · Re = {t['re']:,.0f} ({t['regimen']}) · "
            f"f = {t['f']:.5f} · ν = {res['nu']:.3f} cSt · ρ = {res['rho']:g} kg/m³")
    esc.flecha((8, yc), (x0, yc), COLORES["aviso"], 0.8, info=info)
    gr.tuberia(esc, x0, x1, yc, hp, COLORES["aceite"], etq, info, t["detalle_k"],
               f"L = {res['L']:g} m · ΣK = {t['k_total']:.2f}" + (f" · Δz = {res['dz']:+g} m" if res["dz"] else ""))
    esc.flecha((x1, yc), (x1 + 22, yc), COLORES["aviso"], 0.8)
    esc.texto(x0, yc + 22, f"Q = {res['q']*60000:.1f} L/min ({res['q']*3600:.2f} m³/h) · T = {res['t_c']:g} °C · "
                           f"ν = {res['nu']:.3f} cSt · ρ = {res['rho']:g} kg/m³", 2.5, "w", info=info)
    esc.texto(x0, yc + 17, f"v = {t['v']:.3f} m/s · Re = {t['re']:,.0f} ({t['regimen']}) · f = {t['f']:.4f}", 2.5, "w",
              COLORES["aviso"] if t["laminar"] else COLORES["texto"], info=info)
    cv = c.get("criterio_velocidad") or {}
    gr.banda_velocidad(esc, x0, 82, 120, t["v"], _f(cv.get("v_min_m_s")), _f(cv.get("v_max_m_s")),
                       cv.get("fuente", ""))
    items = [("Tubería recta", t["dp_tuberia"] / 1000, COLORES["acento"]),
             ("Accesorios", t["dp_accesorios"] / 1000, COLORES["tubo"])]
    if res["dz"]:
        items.append(("Desnivel", t["dp_estatico"] / 1000, COLORES["aviso"]))
    items.append(("Total", t["dp_total"] / 1000, COLORES["linea"]))
    gr.barras(esc, x0 - 30, 60, 150, f"Caída de presión (total {t['dp_total']/PSI:.3f} psi; "
                                     f"h = {t['h_friccion']:.3f} m de aceite)", items, "kPa")
    y = 60 - len(items) * 6.5 - 8
    if res["ab"]:   # curva ν-T
        a, b = res["ab"]
        ts = [20 + 2.5 * i for i in range(33)]
        nus = [ac.viscosidad_cst(tc + 273.15, a, b) for tc in ts]
        lmin, lmax = math.log10(min(nus)), math.log10(max(nus))
        T = esc.grafica(x0, y - 44, 120, 38, (20, 100), (lmin - 0.05, lmax + 0.05),
                        "Viscosidad contra temperatura (ASTM D341)", "Temperatura (°C)", "log₁₀ ν (cSt)",
                        fmt_y="{:.2f}")
        esc.linea([T(tc, math.log10(n)) for tc, n in zip(ts, nus)], COLORES["aviso"], 0.7)
        vc = c["viscosidad"]
        for tc, n, et in ((float(vc["t1_c"]), float(vc["nu1_cst"]), "dato"), (float(vc["t2_c"]), float(vc["nu2_cst"]), "dato"),
                          (res["t_c"], res["nu"], "operación"), (40.0, res["nu40"], "40 °C")):
            px, py = T(tc, math.log10(n))
            col = COLORES["mal"] if et == "operación" else COLORES["linea"]
            esc.circulo(px, py, 1.0, col, col, info=f"{et}: {n:.3f} cSt a {tc:g} °C")
            esc.texto(px + 1.5, py + 1.5, f"{n:.1f} cSt ({et})", 2.2, "sw", col)
        esc.texto(x0 + 125, y - 10, f"ν₄₀ = {res['nu40']:.1f} cSt → {res['iso'] or 'sin grado ISO VG'}", 2.5, "w",
                  COLORES["mal"] if res["iso"] is None else COLORES["texto"], negrita=True)
        y -= 62
    if res["espesor"]:
        gr.espesor(esc, x0 - 30, y, res["espesor"])
        y -= 4 * 6.5 + 10
    if res.get("presion"):
        gr.presiones(esc, x0 - 30, y, res["presion"])
        y -= 8 * 6.5 + 14
    if res.get("curva"):
        gr.curva_velocidad(esc, x0 + 4, y - 54, 120, 50, res["curva"])
    return esc


def _f(x):
    return None if x in (None, "") else float(x)
