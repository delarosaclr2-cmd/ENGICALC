"""Esquema de la línea de vapor (sin escala) y perfil de presión. Solo dibuja resultados del motor."""
from .motor import FT3_LB
from .nucleo import graficos as gr
from .nucleo.unidades import PSI
from .ui.dibujo import COLORES, Escena


def _desc(e):
    return (f"{e.fase}" + (f" (x = {e.x:g})" if e.x not in (None, 0, 1) else "") +
            f" · p = {e.p/PSI:.2f} psia ({e.p/1e5:.3f} bar a) · T = {e.t-273.15:.1f} °C · "
            f"ν = {e.v:.5f} m³/kg ({e.v/FT3_LB:.4f} ft³/lb) · h = {e.h/1000:.1f} kJ/kg")


def construir(c, res) -> Escena:
    e1, e2 = res["e1"], res["e2"]
    esc = Escena(c["nombre"], "Esquema sin escala. Flujo adiabático por segmentos con IAPWS-IF97; los accesorios "
                              "se reparten uniformemente en la longitud.")
    x0, x1, yc, hp = 40.0, 220.0, 110.0, 9.0
    tub = c["tuberia"]
    etq = (f"NPS {tub['nps']} céd. {tub.get('cedula', '')} · " if tub.get("nps") else "") + f"Di {res['d']*1000:.1f} mm"
    info = (f"ṁ = {res['m']*3600:,.0f} kg/h · v = {res['v1']:.2f}→{res['v2']:.2f} m/s · Re = {res['re1']:,.0f} · "
            f"f = {res['f1']:.5f}")
    esc.flecha((8, yc), (x0, yc), COLORES["mal"], 0.9, info=_desc(e1))
    gr.tuberia(esc, x0, x1, yc, hp, COLORES["vapor"], etq, info, res["detalle_k"],
               f"L = {res['L']:g} m · ΣK = {res['k_total']:.2f}")
    esc.texto(8, yc + 26, "ENTRADA", 2.8, "w", negrita=True)
    esc.texto(8, yc + 21.5, f"ṁ = {res['m']*3600:,.0f} kg/h ({res['m']*3600/0.45359237:,.0f} lb/h)", 2.5, "w")
    esc.texto(8, yc + 17.5, f"p₁ = {e1.p/PSI:.2f} psia · T₁ = {e1.t-273.15:.1f} °C · {e1.fase}", 2.5, "w", info=_desc(e1))
    esc.texto(8, yc + 13.5, f"v₁ = {res['v1']:.2f} m/s · ν₁ = {e1.v/FT3_LB:.4f} ft³/lb", 2.5, "w", info=_desc(e1))
    venteo = res["venteo"]
    if venteo:   # silenciador
        sx = x1 + 6
        esc.linea([(x1, yc), (sx + 4, yc)], COLORES["tubo"], 1.2)
        esc.rect(sx + 4, yc - 4, 10, 30, COLORES["linea"], "#EEEEEE", 0.6, info="Silenciador (venteo a la atmósfera)")
        esc.texto(sx + 9, yc + 11, "SIL", 2.6, negrita=True, rot=90)
        for k in range(3):
            esc.flecha((sx + 9, yc + 26), (sx + 4 + 5 * k, yc + 36), COLORES["suave"], 0.4)
        ed = venteo["estado"]
        esc.texto(x1 + 20, yc + 50, f"Descarga a {venteo['p']/PSI:.2f} psia (isentálpica)", 2.5, "e", negrita=True,
                  info=_desc(ed))
        esc.texto(x1 + 20, yc + 46, f"T₂ = {ed.t-273.15:.1f} °C · ν₂ = {ed.v/FT3_LB:.2f} ft³/lb", 2.4, "e", info=_desc(ed))
        esc.texto(x1 + 20, yc + 42, f"Q = {venteo['acfm']:,.0f} ACFM ({venteo['q_m3s']*3600:,.0f} m³/h)", 2.5, "e",
                  COLORES["acento"], negrita=True, info=_desc(ed))
    else:
        esc.flecha((x1, yc), (x1 + 22, yc), COLORES["mal"], 0.9, info=_desc(e2))
        esc.texto(x1 + 24, yc + 21.5, "SALIDA", 2.8, "e", negrita=True)
        esc.texto(x1 + 24, yc + 17.5, f"p₂ = {e2.p/PSI:.2f} psia · T₂ = {e2.t-273.15:.1f} °C", 2.5, "e", info=_desc(e2))
        esc.texto(x1 + 24, yc + 13.5, f"ΔP = {res['dp']/1000:.2f} kPa ({res['dp']/PSI:.3f} psi)", 2.5, "e",
                  negrita=True, info=_desc(e2))
    cv = c.get("criterio_velocidad") or {}
    gr.banda_velocidad(esc, x0, 72, 140, max(res["v1"], res["v2"]), _f(cv.get("v_min_m_s")), _f(cv.get("v_max_m_s")),
                       cv.get("fuente", ""))
    y = 52
    if len(res["perfil"]) > 2 and res["L"] > 0:
        ps = [p / PSI for _, p, _ in res["perfil"]]
        lo, hi = min(ps), max(ps)
        marg = max((hi - lo) * 0.15, 0.05)
        T = esc.grafica(x0, y - 40, x1 - x0, 34, (0, res["L"]), (lo - marg, hi + marg), "Perfil de presión",
                        "Distancia (m)", "Presión (psia)", fmt_y="{:.1f}")
        esc.linea([T(x, p / PSI) for x, p, _ in res["perfil"]], COLORES["mal"], 0.7,
                  info=f"p₁ = {hi:.2f} → p₂ = {lo:.2f} psia")
        y -= 62
    if res["espesor"]:
        gr.espesor(esc, x0 - 30, y, res["espesor"])
        y -= 4 * 6.5 + 10
    if res.get("presion"):
        gr.presiones(esc, x0 - 30, y, res["presion"])
        y -= 8 * 6.5 + 14
    if res.get("curva"):
        gr.curva_velocidad(esc, x0 + 4, y - 54, 120, 50, res["curva"], "m³/h reales")
    return esc


def _f(x):
    return None if x in (None, "") else float(x)
