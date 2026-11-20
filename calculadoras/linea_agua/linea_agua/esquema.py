"""Esquema de la línea de agua (sin escala). Solo dibuja resultados del motor."""
from .nucleo import graficos as gr
from .nucleo.unidades import PSI
from .ui.dibujo import COLORES, Escena


def construir(c, res) -> Escena:
    t = res["tramo"]
    esc = Escena(c["nombre"], "Esquema sin escala. Alturas en metros del agua que circula; ΔP = ρ·g·h con la "
                              "densidad real. Barras verdes: intervalo de velocidad del criterio capturado.")
    x0, x1, yc, hp = 40.0, 230.0, 100.0, 8.0
    tub = c["tuberia"]
    etq = (f"NPS {tub['nps']} céd. {tub.get('cedula', '')} · " if tub.get("nps") else "") + f"Di {res['d']*1000:.1f} mm"
    info = (f"Q = {res['q']*3600:.3f} m³/h · v = {t['v']:.3f} m/s · Re = {t['re']:,.0f} ({t['regimen']}) · "
            f"f = {t['f']:.5f} · ρ = {res['rho']:.2f} kg/m³ · μ = {res['mu']*1000:.4f} cP")
    succion = c.get("servicio") == "succion"
    if succion:   # tanque de succión a la izquierda
        n = res["npsh"]
        esc.rect(4, yc - 2, 26, 30, COLORES["linea"], "#FFFFFF", 0.5, info="Tanque / deareador de succión")
        esc.rect(4, yc - 2, 26, 20, COLORES["agua"], COLORES["liquido"], 0.1)
        esc.texto(17, yc + 24, "TANQUE", 2.6, negrita=True)
        if n:
            esc.texto(17, yc + 13, f"p = {n['p_sup']/1000:.1f} kPa a", 2.3)
            esc.cota((33, yc), (33, yc + 18), f"z = {n['z']:g} m", sep=3)
        esc.linea([(30, yc), (x0, yc)], COLORES["tubo"], 1.2)
    else:
        esc.flecha((8, yc), (x0, yc), COLORES["acento"], 0.8, info=info)
    gr.tuberia(esc, x0, x1, yc, hp, COLORES["liquido"], etq, info, t["detalle_k"],
               f"L = {res['L']:g} m · ΣK = {t['k_total']:.2f}" + (f" · Δz = {res['dz']:+g} m" if res["dz"] else ""))
    if succion:   # bomba a la derecha
        esc.circulo(x1 + 9, yc, 7, COLORES["linea"], "#FFFFFF", 0.6, info="Bomba")
        esc.texto(x1 + 9, yc, "B", 3.0, negrita=True)
        esc.linea([(x1, yc), (x1 + 2, yc)], COLORES["tubo"], 1.2)
    else:
        esc.flecha((x1, yc), (x1 + 24, yc), COLORES["acento"], 0.8)
    esc.texto(x0, yc + 22, f"Q = {res['q']*3600:.3f} m³/h · T = {float(c['temperatura_c']):g} °C · "
                           f"ρ = {res['rho']:.2f} kg/m³ · ν = {res['mu']/res['rho']*1e6:.4f} cSt", 2.5, "w", info=info)
    esc.texto(x0, yc + 17, f"v = {t['v']:.3f} m/s ({t['v']/0.3048:.2f} ft/s) · Re = {t['re']:,.0f} · f = {t['f']:.4f}",
              2.5, "w", info=info)
    cv = c.get("criterio_velocidad") or {}
    gr.banda_velocidad(esc, x0, 62, 120, t["v"], _f(cv.get("v_min_m_s")), _f(cv.get("v_max_m_s")),
                       cv.get("fuente", ""))
    items = [("Tubería recta", t["dp_tuberia"] / 1000, COLORES["acento"]),
             ("Accesorios", t["dp_accesorios"] / 1000, COLORES["tubo"])]
    if res["dz"]:
        items.append(("Desnivel", t["dp_estatico"] / 1000, COLORES["aviso"]))
    items.append(("Total", t["dp_total"] / 1000, COLORES["linea"]))
    gr.barras(esc, x0 - 30, 38, 150, f"Caída de presión (total {t['dp_total']/PSI:.3f} psi; "
                                     f"h = {t['h_friccion']:.3f} m de agua)", items, "kPa")
    y_sig = 38 - len(items) * 6.5 - 10
    if res["npsh"]:
        n = res["npsh"]
        it = [("Presión en superficie", n["h_sup"], COLORES["acento"]), ("− presión de vapor", -n["h_vap"], COLORES["aviso"]),
              ("+ nivel z", n["z"], COLORES["tubo"]), ("− pérdidas succión", -t["h_friccion"], COLORES["mal"]),
              ("NPSH disponible", n["npsha"], COLORES["ok"])]
        if n.get("requerido") is not None:
            it.append(("NPSHr + margen", n["requerido"], COLORES["mal"] if n["npsha"] < n["requerido"] else COLORES["suave"]))
        gr.barras(esc, x0 - 30, y_sig, 150, "NPSH (m de agua)", it, "m", "{:.2f}")
        y_sig -= len(it) * 6.5 + 10
    if res["espesor"]:
        gr.espesor(esc, x0 - 30, y_sig, res["espesor"])
        y_sig -= 4 * 6.5 + 10
    if res.get("presion"):
        gr.presiones(esc, x0 - 30, y_sig, res["presion"])
        y_sig -= 8 * 6.5 + 14
    if res.get("curva"):
        gr.curva_velocidad(esc, x0 + 4, y_sig - 54, 120, 50, res["curva"])
    return esc


def _f(x):
    return None if x in (None, "") else float(x)
