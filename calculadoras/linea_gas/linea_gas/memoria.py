"""Arma la memoria de cálculo (y el esquema) de una línea a partir de los resultados del motor."""
from dataclasses import replace

from . import __version__
from . import presion as pres
from . import seleccion as sel
from . import unidades as u
from .caso import ejecutar, huella, p_atm_sitio_pa
from .datos import (GASES, REFERENCIAS, RUGOSIDAD_ACERO_M, d_interior_m, espesor_nominal_in, nps_lista, od_in)
from .esquema import construir
from .motor import calcular
from .ui.memoria_pdf import Memoria

ECUACIONES = [
    "ṁ = Q_ref · P_ref · M / (R_u · T_ref)   (caudal a condición de referencia → flujo másico; Menon ec. 5.9–5.12)",
    "ρ = P · M / (Z · R_u · T);   v = ṁ / (ρ · A);   Re = ρ · v · D / μ",
    "1/√f = −2 · log₁₀[ ε/(3.7·D) + 2.51/(Re·√f) ]   (Colebrook-White; Swamee-Jain como verificación)",
    "P₁² − P₂² = (G² · Z · R_u · T / M) · [ f·L/D + ΣK + 2·ln(P₁/P₂) ]   (flujo isotérmico compresible, G = ṁ/A)",
    "ΔP_accesorios ≈ ΣK · ρ · v² / 2   (K = f_T · L/D, Menon tabla 5.11; altura en columna del gas que circula)",
    "Comparación (solo aire): ΔP = 9.8265×10⁻⁴ · T · L / (P · d⁵) · (P_s · Q_s / T_s)^1.857   (Fritzsche, Menon ec. 5.34; Q_s en SCFM)",
] + pres.ECUACIONES + sel.ECUACIONES
SUPUESTOS = [
    "Flujo isotérmico y permanente; Z y μ constantes en el tramo.",
    "Gas ideal corregido por Z; velocidad baja (Mach < 0.3); ΔP < 40 % de P₁.",
    "Tubería de acero comercial con la rugosidad indicada; accesorios con K de la tabla 5.11 de Menon.",
]
FUENTES = [
    "Menon, E. S. Piping Calculations Manual. McGraw-Hill, 2005, cap. 5 (ec. 5.9–5.12, 5.17, 5.34; tablas 5.10 y 5.11).",
    "ASME B36.10M: diámetros interiores de tubo de acero (céd. 40 y 80).",
    "GPA 2145-16 / ISO 6976: masas molares; ley de Sutherland para la viscosidad del aire.",
]


def evaluar(c: dict) -> Memoria:
    e, r = ejecutar(c)
    psi = lambda pa: pa / u.PSI
    g = GASES[e.gas]
    t = c["tuberia"]
    acc = "; ".join(f"{a.cantidad} × {a.tipo}" + (f" (K = {a.k})" if a.k is not None else "") for a in e.accesorios) or "Ninguno"
    datos = [
        ("Gas", g["nombre"], g["fuente"]),
        ("Caudal", f"{c['caudal']['valor']:g} {c['caudal']['unidad']}", REFERENCIAS[e.ref][2]),
        ("Presión de entrada", f"{psi(e.p_entrada_pa):.3f} psia ({e.p_entrada_pa/1000:.2f} kPa a)",
         f"capturada: {c['p_entrada']['valor']:g} {c['p_entrada']['unidad']}; P atm {c.get('p_atm_psia', 14.696)} psia"),
        ("Temperatura", f"{e.t_k-273.15:.2f} °C", ""),
        ("Tubería", (f"NPS {t['nps']} céd. {t.get('cedula')}" if t.get("nps") else "Di capturado")
         + f"; Di = {e.d_interior_m*1000:.2f} mm", "ASME B36.10M" if t.get("nps") else ""),
        ("Longitud", f"{e.longitud_m:g} m", ""),
        ("Rugosidad", f"{e.rugosidad_m*1000:.4f} mm", ""),
        ("Factor Z", f"{e.z:g}", ""),
        ("Accesorios", acc, "K de Menon tabla 5.11 si no se capturó"),
    ]
    A = 3.141592653589793 * e.d_interior_m ** 2 / 4
    resultados = [
        ("Flujo másico", f"{r.mdot_kg_s*3600:.3f}", "kg/h"),
        ("Caudal real a la entrada", f"{r.q_actual_m3h:.4f}", "m³/h"),
        ("Densidad a la entrada", f"{r.rho_entrada:.4f}", "kg/m³"),
        ("Velocidad entrada / salida", f"{r.v_entrada:.4f} / {r.v_salida:.4f}", f"m/s (Mach {r.mach:.4f})"),
        ("Viscosidad dinámica", f"{r.mu:.4e}", "Pa·s"),
        ("Número de Reynolds", f"{r.re:,.0f}", ""),
        ("Factor de fricción (Colebrook)", f"{r.f:.5f}", f"Swamee-Jain {r.f_swamee_jain:.5f}"),
        ("ΣK accesorios", f"{r.k_total:.3f}", ""),
        ("ΔP tubo recto", f"{psi(r.dp_tubo_pa):.4f}", f"psi ({r.dp_tubo_pa/1000:.4f} kPa)"),
        ("ΔP accesorios", f"{psi(r.dp_accesorios_pa):.4f}", f"psi ({r.dp_accesorios_pa/1000:.4f} kPa)"),
        ("ΔP total", f"{psi(r.dp_total_pa):.4f}", f"psi ({r.dp_total_pa/1000:.4f} kPa)"),
        ("Presión a la salida", f"{psi(r.p_salida_pa):.3f}", f"psia ({r.p_salida_pa/1000:.2f} kPa a)"),
    ]
    if r.dp_fritzsche_pa is not None:
        resultados.append(("ΔP Fritzsche (comparación)", f"{psi(r.dp_fritzsche_pa):.4f}", "psi (Menon ec. 5.34)"))
    p_ref, t_ref, _ = REFERENCIAS[e.ref]
    sust = [
        f"ṁ = {e.q_ref_m3s*3600:g} m³/h ÷ 3600 × {p_ref:.0f} Pa × {g['M']} / (8314.46 × {t_ref:.2f} K) = {r.mdot_kg_s:.6f} kg/s",
        f"ρ₁ = {e.p_entrada_pa:.0f} Pa × {g['M']} / ({e.z:g} × 8314.46 × {e.t_k:.2f} K) = {r.rho_entrada:.4f} kg/m³",
        f"A = π × {e.d_interior_m:.5f}² / 4 = {A:.6f} m²;  v₁ = {r.mdot_kg_s:.6f} / ({r.rho_entrada:.4f} × {A:.6f}) = {r.v_entrada:.4f} m/s",
        f"Re = {r.rho_entrada:.4f} × {r.v_entrada:.4f} × {e.d_interior_m:.5f} / {r.mu:.4e} = {r.re:,.0f};  f = {r.f:.5f}",
        f"f·L/D = {r.f:.5f} × {e.longitud_m:g} / {e.d_interior_m:.5f} = {r.f*e.longitud_m/e.d_interior_m:.2f};  ΣK = {r.k_total:.3f}",
        f"Ecuación isotérmica resuelta por iteración: P₂ = {r.p_salida_pa:.0f} Pa = {psi(r.p_salida_pa):.3f} psia;  "
        f"ΔP = {r.dp_total_pa:.1f} Pa = {psi(r.dp_total_pa):.4f} psi",
    ]
    ver = [(a, b, lim, s, "Criterio del proyecto") for a, b, lim, s in r.verificaciones]
    adv = list(r.advertencias)
    # --- presión máxima admisible y barridos de velocidad
    pm = presion_maxima(c, e)
    tablas = []
    if pm:
        datos += pres.filas_datos(pm, [d[0] for d in datos])
        resultados += pres.filas_resultado(pm)
        ver += pres.verificaciones(pm)
        adv += pm["avisos"]
        sust += pres.sustitucion(pm)
        tablas.append(pres.tabla(pm))
    bar = barridos(c, e, r)
    tablas = [x for x in (bar.get("tabla_diametros"), bar.get("tabla_capacidad")) if x] + tablas
    cv = bar.get("curva") or {}
    resultados.insert(2, ("Área interior A", f"{sel.area(e.d_interior_m)*1e3:.4f}", "×10⁻³ m² (A = π·Di²/4)"))
    if cv.get("q_max_m3h"):
        resultados.append(("Capacidad máxima con el criterio de velocidad",
                           f"{sel.redondeo_seguro(cv['q_max_m3h'], 2, 'abajo'):,.2f}",
                           f"m³/h reales a la entrada (v_máx = {cv['v_max']:g} m/s a la salida; "
                           "redondeada hacia abajo)"))
    if bar.get("diametro_requerido_m"):
        resultados.append(("Diámetro interior requerido a la velocidad máxima",
                           f"{sel.redondeo_seguro(bar['diametro_requerido_m']*1000, 2, 'arriba'):.2f}",
                           "mm (Di = √(4·Q/(π·v)) con la densidad de ENTRADA: preselección; la velocidad "
                           "de salida es mayor, verifique el diámetro en la tabla de diámetros)"))
    return Memoria(
        titulo="Caída de presión en línea de gas o aire comprimido", caso=c["nombre"], version=__version__,
        huella=huella(c), documento=c.get("documento", ""),
        objetivo="Calcular el caudal real, la velocidad, la caída de presión y la presión de llegada de la línea "
                 "para el caudal y las condiciones indicadas.",
        datos=datos, resultados=resultados, verificaciones=ver, advertencias=adv,
        ecuaciones=ECUACIONES, sustitucion=sust, supuestos=SUPUESTOS, referencias=FUENTES + pres.REFERENCIAS,
        notas=c.get("notas", ""), escena=construir(c, e, r, pm, cv), tablas=tablas,
        resumen=[("ΔP total", f"{psi(r.dp_total_pa):.4f} psi ({r.dp_total_pa/1000:.3f} kPa)"),
                 ("Presión a la salida", f"{psi(r.p_salida_pa):.3f} psia"),
                 ("Velocidad", f"{r.v_entrada:.3f} m/s"),
                 ("Reynolds / f", f"{r.re:,.0f} / {r.f:.4f}"),
                 ("Caudal real", f"{r.q_actual_m3h:.3f} m³/h"),
                 ("Flujo másico", f"{r.mdot_kg_s*3600:.2f} kg/h")])


def presion_maxima(c, e):
    """Presión máxima admisible de la tubería. None si el caso no trae datos de espesor/material."""
    cfg = c.get("espesor") or {}
    t = c["tuberia"]
    if not pres.hay_material(cfg):
        return None
    if t.get("nps"):
        od = od_in(t["nps"]) * pres.PULG
        tn = (cfg["t_nominal_mm"] / 1000) if cfg.get("t_nominal_mm") else espesor_nominal_in(t["nps"], t["cedula"]) * pres.PULG
    elif cfg.get("od_mm") and cfg.get("t_nominal_mm"):
        od, tn = cfg["od_mm"] / 1000, cfg["t_nominal_mm"] / 1000
    else:
        return None
    s_adm, _ = pres.resolver_s(cfg)
    # La presión de operación se compara en MANOMÉTRICA, igual que la presión máxima admisible.
    # Se resta la atmósfera del SITIO, la misma con la que se convirtió la presión de entrada.
    return pres.desde_caso(cfg, od, tn, s_adm, cfg.get("t_diseno_c", e.t_k - 273.15),
                           p_operacion_pa=e.p_entrada_pa - p_atm_sitio_pa(c))


def barridos(c, e, r):
    """Velocidad por diámetro al caudal REAL de entrada, capacidad de la línea y curva v(Q).

    Para un gas el caudal real depende de la presión: Q = ṁ/ρ₁ a la entrada. Al cambiar de diámetro
    se mantiene el flujo másico y la presión de entrada, no el caudal real de salida.
    """
    q = r.mdot_kg_s / r.rho_entrada
    vmax = (c.get("criterios") or {}).get("v_max_m_s")
    vmin = (c.get("criterios") or {}).get("v_min_m_s")
    ced = str(c["tuberia"].get("cedula") or "40")

    cand = []
    for nps in nps_lista():
        try:
            cand.append((nps, ced, d_interior_m(nps, ced)))
        except KeyError:
            continue
    d_a_nps = {d: nps for nps, _c, d in cand}

    def calc(d):
        """Resultado del tramo completo con ese diámetro, al mismo caudal y presión de entrada.

        Informa la velocidad A LA SALIDA y la ΔP del modelo compresible, no una estimación con la
        densidad de entrada: así el estado de cada diámetro coincide con el que dictaminaría el
        motor si se capturara ese diámetro. Los accesorios se recalculan con el NPS de ese diámetro
        (K capturados se conservan) porque calcular() los toma de la tabla con e.nps. El mínimo se
        juzga con la velocidad de entrada, la menor del tramo.
        """
        r2 = calcular(replace(e, d_interior_m=d, nps=d_a_nps.get(d, e.nps)))
        return {"v": r2.v_salida, "v_baja": r2.v_entrada, "re": r2.re, "f": r2.f,
                "dp_pa": r2.dp_total_pa if e.longitud_m else None}

    def v_salida(q_entrada):
        """Velocidad A LA SALIDA para ese caudal de entrada, con la misma P₁, T y diámetro.

        Es la que verifica el motor (la densidad cae con la presión, así que es la mayor del
        tramo). Se obtiene volviendo a correr el mismo modelo isotérmico escalando el caudal de
        referencia: ṁ es proporcional a Q_ref, y el caudal real de entrada a ṁ con P₁ y T fijas.
        """
        return calcular(replace(e, q_ref_m3s=e.q_ref_m3s * q_entrada / q)).v_salida

    # v_salida corre el mismo modelo que el dictamen, así que no hace falta otra verificación; la
    # velocidad al caudal capturado ya la dio el dictamen (r.v_salida).
    lim = sel.limites_de_caudal(e.d_interior_m, q, vmin, vmax, v_salida, v_actual=r.v_salida)
    salida = {"curva": sel.curva(e.d_interior_m, q, vmin, vmax, v_gobernante=v_salida, limites=lim),
              "tabla_capacidad": sel.tabla_capacidad(e.d_interior_m, q, vmin, vmax,
                                                     conv=lambda x: x / q * float(c["caudal"]["valor"]),
                                                     unidad=f"{c['caudal']['unidad']} {e.ref}",
                                                     v_gobernante=v_salida, donde_v="a la salida",
                                                     limites=lim),
              "diametro_requerido_m": sel.diametro_requerido(q, float(vmax)) if vmax not in (None, "") else None}
    cand = sel.ventana(cand, q, vmin, vmax, c["tuberia"].get("nps"))
    if cand:
        salida["tabla_diametros"] = sel.tabla_diametros(cand, calc, vmin, vmax, c["tuberia"].get("nps"),
                                                        e.longitud_m or None, donde_v="a la salida",
                                                        nota_dp="total del tramo ({} m y accesorios)")
    return salida
