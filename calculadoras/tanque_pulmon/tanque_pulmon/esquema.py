"""Esquema del tanque pulmón (sin escala) y gráfica presión–tiempo. No calcula: usa los resultados del motor."""
from . import unidades as u
from .criterios import clasificar_nom020
from .ui.dibujo import COLORES, Escena


def _cuerpo(esc, x, y, w, h, info):
    """Recipiente vertical con cabezas semielípticas 2:1."""
    import math
    hc = w / 4
    arco = lambda yc, signo: [(x + w / 2 + w / 2 * math.cos(math.pi * k / 16), yc + signo * hc * math.sin(math.pi * k / 16))
                              for k in range(17)]
    sup = arco(y + h, 1)
    inf = arco(y, -1)
    esc.poli([(x, y), (x + w, y)] + sup, COLORES["linea"], COLORES["aire"], 0.6, info=info)
    esc.poli(inf, COLORES["linea"], COLORES["aire"], 0.6, info=info)


def construir(inf) -> Escena:
    e, r, caso = inf.entradas, inf.resultados, inf.caso
    psia = lambda pa: pa / u.PSI
    esc = Escena(caso.nombre, "Recipiente sin escala. La gráfica usa los tiempos calculados (balance de masa isotérmico).")
    x, y, w, h = 28.0, 30.0, 34.0, 62.0
    info_t = (f"V tanque = {e.v_tanque_m3:.3f} m³ · V sistema = {r.v_sistema_m3:.3f} m³ · T aire = {e.t_aire_k-273.15:.1f} °C · "
              f"masa útil = {r.masa_util_kg:.2f} kg")
    _cuerpo(esc, x, y, w, h, info_t)
    esc.texto(x + w / 2, y + h * 0.62, "TANQUE", 3.2, negrita=True, info=info_t)
    esc.texto(x + w / 2, y + h * 0.50, f"V = {e.v_tanque_m3:g} m³", 2.8, info=info_t)
    esc.texto(x + w / 2, y + h * 0.40, f"T = {e.t_aire_k-273.15:.1f} °C", 2.6, info=info_t)
    # patas
    for xp in (x + 4, x + w - 4):
        esc.linea([(xp, y - 3), (xp, y - 14)], COLORES["acero"], 1.2)
    esc.linea([(x - 4, y - 14), (x + w + 4, y - 14)], COLORES["suave"], 0.4)
    # manómetro
    esc.linea([(x + w, y + h * 0.78), (x + w + 7, y + h * 0.78)], COLORES["linea"], 0.5)
    esc.circulo(x + w + 11, y + h * 0.78, 4, COLORES["linea"], "#FFFFFF", 0.5,
                info=f"Banda: {psia(e.p_superior_pa):.2f} → {psia(e.p_inferior_pa):.2f} psia")
    esc.texto(x + w + 11, y + h * 0.78, "PI", 2.4, negrita=True)
    esc.texto(x + w + 16, y + h * 0.78 + 2, f"Ps {psia(e.p_superior_pa):.2f} psia", 2.4, "w")
    esc.texto(x + w + 16, y + h * 0.78 - 2.5, f"Pi {psia(e.p_inferior_pa):.2f} psia", 2.4, "w")
    # válvula de seguridad
    yt = y + h + w / 4
    p_cal = None
    cat = clasificar_nom020((e.p_superior_pa - e.p_atm_sitio_pa) / 1000.0, e.v_tanque_m3)
    esc.linea([(x + w / 2, yt), (x + w / 2, yt + 6)], COLORES["linea"], 0.6)
    esc.poli([(x + w / 2 - 3, yt + 6), (x + w / 2 + 3, yt + 6), (x + w / 2, yt + 10)], COLORES["mal"], "#FFFFFF", 0.5,
             info=f"Válvula de seguridad: calibración > presión de operación y ≤ PTMP (NOM-020-STPS-2011, num. 14.2). "
                  f"Recipiente categoría {cat} (num. 7.1.1)")
    esc.texto(x + w / 2 + 5, yt + 8, f"PSV · NOM-020 cat. {cat}", 2.4, "w", COLORES["mal"])
    # entrada (suministro)
    ye = y + h * 0.22
    fad = "no capturado" if e.q_compresor_m3s is None else f"{caso.q_compresor.valor:g} {caso.q_compresor.unidad} ({e.ref_compresor})"
    esc.flecha((2, ye), (x, ye), COLORES["acento"], 0.8, info=f"Suministro / FAD: {fad}")
    esc.texto(2, ye + 3, "Suministro", 2.6, "sw", negrita=True)
    esc.texto(2, ye - 2.5, f"FAD: {fad}", 2.3, "nw")
    # salida (consumo)
    ys = y + h * 0.22
    q = f"{caso.q_consumo.valor:g} {caso.q_consumo.unidad} ({e.ref_consumo})"
    esc.flecha((x + w, ys), (x + w + 36, ys), COLORES["acento"], 0.8,
               info=f"Consumo = {q} · ṁ = {r.mdot_consumo_kg_s*3600:.2f} kg/h (incluye margen {e.margen_consumo*100:g} %)")
    esc.texto(x + w + 36, ys + 3, "Consumo", 2.6, "se", negrita=True)
    esc.texto(x + w + 36, ys - 2.5, q, 2.3, "ne")
    if e.incluir_tuberia and r.v_tuberia_m3 > 0:
        esc.linea([(x + w + 36, ys), (x + w + 52, ys), (x + w + 52, ys - 18)], COLORES["tubo"], 1.0, guion=(2, 1),
                  info=f"Tubería conectada: {r.v_tuberia_m3:.4f} m³ (se suma al volumen del tanque)")
        esc.texto(x + w + 52, ys - 20, f"Tubería {r.v_tuberia_m3:.3f} m³", 2.3, "n", COLORES["tubo"])

    # Gráfica presión–tiempo
    ps, pi_ = psia(e.p_superior_pa), psia(e.p_inferior_pa)
    gx, gy, gw, gh = 148.0, 26.0, 108.0, 62.0
    if r.t_carga_min:
        tc, td = r.t_carga_min, r.t_descarga_min
        horizonte = max(60.0, 2.2 * (tc + td))
        pts, t, sube = [(0.0, ps)], 0.0, False
        while t < horizonte:
            dt = tc if sube else td
            t = min(t + dt, horizonte)
            frac = (t - pts[-1][0]) / dt
            p_ini = pts[-1][1]
            p_fin = p_ini + (ps - pi_) * frac * (1 if sube else -1)
            pts.append((t, p_fin))
            sube = not sube
        titulo = f"Ciclo carga / vacío: carga {tc:.2f} min, vacío {td:.2f} min, {r.ciclos_por_hora:.2f} ciclos/h"
        xmax = horizonte
    else:
        tr = r.t_retencion_min
        xmax = max(tr * 1.3, (e.t_retencion_req_min or 0) * 1.15, 1.0)
        pts = [(0.0, ps), (tr, pi_)]
        titulo = f"Descarga sin aporte del compresor: t = {tr:.2f} min"
    marg = (ps - pi_) * 0.25
    T = esc.grafica(gx, gy, gw, gh, (0, xmax), (pi_ - marg, ps + marg), titulo, "Tiempo (min)", "Presión (psia)",
                    fmt_x="{:.1f}", fmt_y="{:.1f}")
    esc.linea([T(*p) for p in pts], COLORES["acento"], 0.7,
              info=f"Retención = {r.t_retencion_min:.2f} min ({u.min_a_texto(r.t_retencion_min)})")
    for val, et in ((ps, "Ps"), (pi_, "Pi")):
        esc.linea([T(0, val), T(xmax, val)], COLORES["suave"], 0.3, guion=(2, 1))
        esc.texto(T(xmax, val)[0] + 1.5, T(xmax, val)[1], f"{et} {val:.2f}", 2.3, "w", COLORES["suave"])
    if not r.t_carga_min:
        px, py = T(r.t_retencion_min, pi_)
        esc.circulo(px, py, 1.1, COLORES["acento"], COLORES["acento"], info=f"t retención = {r.t_retencion_min:.3f} min")
        esc.texto(px, py - 3, f"t = {r.t_retencion_min:.2f} min", 2.5, "n", negrita=True)
    if e.t_retencion_req_min:
        cumple = r.t_retencion_min >= e.t_retencion_req_min
        col = COLORES["ok"] if cumple else COLORES["mal"]
        esc.linea([T(e.t_retencion_req_min, pi_ - marg), T(e.t_retencion_req_min, ps + marg)], col, 0.5, guion=(1.5, 1),
                  info=f"Criterio: retención ≥ {e.t_retencion_req_min:g} min → {'CUMPLE' if cumple else 'NO CUMPLE'}")
        esc.texto(T(e.t_retencion_req_min, ps + marg)[0] + 1, T(0, ps + marg)[1] - 2.5,
                  f"requerido {e.t_retencion_req_min:g} min", 2.3, "nw", col)
    return esc
