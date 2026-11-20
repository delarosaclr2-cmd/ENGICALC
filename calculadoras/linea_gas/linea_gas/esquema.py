"""Esquema de la línea (sin escala) y perfil de presión a lo largo de ella. No calcula: usa los resultados."""
from . import graficos as gr
from . import unidades as u
from .motor import perfil_presion
from .ui.dibujo import COLORES, Escena

_VALVULAS = {"compuerta": "C", "globo": "G", "angulo": "A", "bola": "B", "check_columpio": "R",
             "check_columpio_t511": "R", "check_levantamiento": "RL"}


def construir(c, e, r, presion=None, curva=None) -> Escena:
    psi = lambda pa: pa / u.PSI
    esc = Escena(c["nombre"], "Esquema sin escala (el diámetro está exagerado). El perfil de presión reparte la "
                              "resistencia de los accesorios uniformemente en la longitud.")
    x0, x1, yc, hp = 30.0, 230.0, 100.0, 8.0
    info_tubo = (f"Di = {e.d_interior_m*1000:.2f} mm · L = {e.longitud_m:g} m · v = {r.v_entrada:.3f}→{r.v_salida:.3f} m/s · "
                 f"Re = {r.re:,.0f} · f = {r.f:.5f}")
    esc.rect(x0, yc - hp / 2, x1 - x0, hp, COLORES["linea"], COLORES["aire"], 0.5, info=info_tubo)
    t = c["tuberia"]
    etiqueta = (f"NPS {t['nps']} céd. {t.get('cedula', '')} · " if t.get("nps") else "") + f"Di {e.d_interior_m*1000:.1f} mm"
    esc.texto(x0 + 0.15 * (x1 - x0), yc, etiqueta, 2.6, info=info_tubo)
    # Entrada y salida
    esc.flecha((4, yc), (x0, yc), COLORES["acento"], 0.8, info=f"ṁ = {r.mdot_kg_s*3600:.2f} kg/h")
    esc.texto(4, yc + 16, "ENTRADA", 2.8, "w", negrita=True)
    esc.texto(4, yc + 11.5, f"P₁ = {psi(e.p_entrada_pa):.2f} psia ({e.p_entrada_pa/1000:.1f} kPa a)", 2.5, "w")
    esc.texto(4, yc + 7.5, f"Q = {c['caudal']['valor']:g} {c['caudal']['unidad']} ({c['caudal']['referencia']}) · "
              f"T = {e.t_k-273.15:.1f} °C", 2.5, "w")
    esc.flecha((x1, yc), (x1 + 26, yc), COLORES["acento"], 0.8)
    esc.texto(x1 + 26, yc + 16, "SALIDA", 2.8, "e", negrita=True)
    esc.texto(x1 + 26, yc + 11.5, f"P₂ = {psi(r.p_salida_pa):.3f} psia", 2.5, "e")
    esc.texto(x1 + 26, yc + 7.5, f"ΔP = {psi(r.dp_total_pa):.4f} psi ({r.dp_total_pa/1000:.3f} kPa)", 2.5, "e",
              COLORES["mal"] if any(v[3] == "NO CUMPLE" for v in r.verificaciones) else COLORES["texto"], negrita=True)
    # Accesorios repartidos
    grupos = r.detalle_k
    for i, (tipo, n, k, kt) in enumerate(grupos):
        xa = x0 + (x1 - x0) * (0.32 + 0.66 * (i + 0.5) / max(len(grupos), 1))
        info = f"{n} × {tipo.replace('_', ' ')}: K = {k:g} c/u, ΣK = {kt:.3f} (Menon tabla 5.11)"
        if tipo in _VALVULAS:
            h = hp * 0.95
            esc.poli([(xa - 3.5, yc - h / 2), (xa + 3.5, yc + h / 2), (xa + 3.5, yc - h / 2), (xa - 3.5, yc + h / 2)],
                     COLORES["linea"], "#FFFFFF", 0.4, info=info)
            esc.texto(xa, yc + hp / 2 + 2.5, _VALVULAS[tipo], 2.4, "s", negrita=True, info=info)
        elif tipo.startswith("codo"):
            ang = "45°" if "45" in tipo else "90°"
            esc.linea([(xa - 3, yc + hp / 2), (xa - 3, yc + hp / 2 + 5), (xa + 2, yc + hp / 2 + 7)], COLORES["tubo"], 1.0,
                      info=info)
            esc.texto(xa, yc + hp / 2 + 8.5, ang, 2.3, "s", info=info)
        else:
            esc.linea([(xa, yc + hp / 2), (xa, yc + hp / 2 + 7)], COLORES["tubo"], 1.4, info=info)
            esc.texto(xa, yc + hp / 2 + 8.5, "T", 2.3, "s", info=info)
        esc.texto(xa, yc - hp / 2 - 2.0, f"{n}×", 2.4, "n", info=info)
    esc.cota((x0, yc - hp / 2 - 6), (x1, yc - hp / 2 - 6), f"L = {e.longitud_m:g} m · ΣK = {r.k_total:.2f}", sep=-3.5)
    esc.texto(x0, yc - 24, "Válvulas: C compuerta · G globo · A ángulo · B bola · R retención (check) · RL retención de levantamiento",
              2.2, "w", COLORES["suave"])

    # Perfil de presión
    perfil = perfil_presion(e, r, 40)
    ps = [psi(p) for _, p in perfil]
    pmin, pmax = min(ps), max(ps)
    if e.p_min_salida_pa is not None:
        pmin = min(pmin, psi(e.p_min_salida_pa))
    marg = max((pmax - pmin) * 0.15, 0.01)
    T = esc.grafica(x0, 18, x1 - x0, 42, (0, e.longitud_m), (pmin - marg, pmax + marg),
                    "Perfil de presión a lo largo de la línea", "Distancia desde la entrada (m)", "Presión (psia)",
                    fmt_y="{:.2f}" if pmax - pmin < 5 else "{:.1f}")
    esc.linea([T(x, psi(p)) for x, p in perfil], COLORES["acento"], 0.7,
              info=f"P₁ = {pmax:.3f} psia → P₂ = {psi(r.p_salida_pa):.3f} psia")
    for (x, p), et in ((perfil[0], "P₁"), (perfil[-1], "P₂")):
        px, py = T(x, psi(p))
        esc.circulo(px, py, 1.0, COLORES["acento"], COLORES["acento"], info=f"{et} = {psi(p):.3f} psia")
        esc.texto(px + (2 if x == 0 else -2), py + 2, f"{et} = {psi(p):.3f}", 2.4, "sw" if x == 0 else "se")
    if e.p_min_salida_pa is not None:
        y = psi(e.p_min_salida_pa)
        esc.linea([T(0, y), T(e.longitud_m, y)], COLORES["mal"], 0.4, guion=(2, 1.2),
                  info=f"Presión mínima de salida (criterio): {y:.2f} psia")
    yy = 2
    if presion:
        gr.presiones(esc, x0 - 30, yy - 10, presion)
        yy -= 8 * 6.5 + 20
    if curva and curva.get("puntos"):
        gr.curva_velocidad(esc, x0 + 4, yy - 58, 120, 50, curva, "m³/h reales")
    return esc
