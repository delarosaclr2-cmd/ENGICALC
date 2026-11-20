"""Memoria de cálculo de la línea de vapor."""
from . import __version__
from .esquema import construir
from .motor import FT3_LB, calcular, gamma, huella
from .nucleo import espesor as esp
from .nucleo import presion as pres
from .nucleo import seleccion as sel
from .nucleo.unidades import PSI
from .ui.memoria_pdf import Memoria

ECUACIONES = [
    "Estado: IAPWS-IF97 (región 2 vapor; región 4 saturación);  μ: IAPWS 2008",
    "v = ṁ·ν / A   (Menon ec. 4.24, ν volumen específico);   Re = ṁ·Di/(A·μ)",
    "1/√f = −2·log₁₀[ε/(3.7·Di) + 2.51/(Re·√f)]   (Colebrook-White, Menon ec. 4.33)",
    "Por segmento: Δp = (f·Δx/Di + ΔK)·G²·ν/2,  G = ṁ/A,  h = constante  (Darcy, Menon ec. 4.29–4.31)",
    "Velocidad sónica de referencia: Us = √(γ·p·ν),  γ = 1.135 saturado / 1.3 sobrecalentado  (Menon ec. 4.25)",
    "Venteo: h₂ = h₁ (isentálpico);  Q = ṁ·ν₂;  ACFM = Q [ft³/min]",
    "Espesor: t = P·D/(2·(S·E·W + P·Y));  t_m = t + c ≤ t_nominal·(1 − tolerancia)   (Menon ec. 4.53)",
] + pres.ECUACIONES + sel.ECUACIONES
SUPUESTOS = [
    "Flujo permanente y adiabático (tubería aislada): la entalpía se conserva; se desprecia la energía cinética.",
    "Sin condensación por pérdidas de calor (si las hay, la calidad del vapor baja).",
    "Rugosidad de acero comercial; accesorios con K de Menon tabla 5.11.",
    "El límite superior del intervalo de velocidad se verifica; quedar por debajo del inferior solo indica tubería holgada.",
]
FUENTES = [
    "Menon, E. S. Piping Calculations Manual. McGraw-Hill, 2005, cap. 4 (ecs. 4.23–4.33, 4.53; tablas 4.4 y 4.10).",
    "IAPWS R7-97(2012) (IF97) e IAPWS R12-08 (viscosidad).",
    "ASME B36.10M; ASME B31.1 §104.1.2 (no proporcionado: S capturado); ASME B31.3-2014 §304.1.2.",
]


def evaluar(c: dict) -> Memoria:
    res = calcular(c)
    e1, e2 = res["e1"], res["e2"]
    tub = c["tuberia"]
    acc = "; ".join(f"{a.get('cantidad', 1)} × {a['tipo']}" for a in c.get("accesorios", [])) or "Ninguno capturado"
    datos = [("Flujo másico", f"{c['flujo']['valor']:g} {c['flujo']['unidad']}", f"{res['m']*3600:,.1f} kg/h"),
             ("Presión de entrada", f"{c['p_entrada']['valor']:g} {c['p_entrada']['unidad']}",
              f"{e1.p/PSI:.3f} psia; P atm {res['patm']/1000:.3f} kPa"),
             ("Estado de entrada", e1.fase, f"T = {e1.t-273.15:.2f} °C (IAPWS-IF97)"),
             ("Tubería", (f"NPS {tub['nps']} céd. {tub.get('cedula')}" if tub.get("nps") else "Di capturado")
              + f"; Di = {res['d']*1000:.2f} mm ({res['d']/0.0254:.3f} in)", "ASME B36.10M" if tub.get("nps") else ""),
             ("Longitud", f"{res['L']:g} m", "0 = solo velocidad y espesor"),
             ("Rugosidad", f"{res['eps']*1000:.4f} mm", ""), ("Accesorios", acc, "K de Menon tabla 5.11")]
    cv = c.get("criterio_velocidad") or {}
    if cv.get("v_max_m_s") not in (None, ""):
        datos.append(("Criterio de velocidad", f"{cv.get('v_min_m_s', '—')}–{cv['v_max_m_s']} m/s", cv.get("fuente", "")))
    if res.get("datos_espesor"):
        datos += res["datos_espesor"]
    resultados = [("Área interior A", f"{res['A']*1e3:.4f} ×10⁻³ m²", "A = π·Di²/4"),
                  ("Caudal real a la entrada", f"{res['q_entrada_m3s']*3600:,.1f} m³/h",
                   f"{res['q_entrada_m3s']/0.3048**3*60:,.0f} ACFM — Q = ṁ·ν"),
                  ("Volumen específico a la entrada", f"{e1.v:.5f} m³/kg", f"{e1.v/FT3_LB:.4f} ft³/lb"),
                  ("Densidad a la entrada", f"{e1.rho:.4f} kg/m³", ""),
                  ("Viscosidad", f"{e1.mu*1e6:.3f} µPa·s", "IAPWS 2008"),
                  ("Velocidad a la entrada", f"{res['v1']:.3f} m/s",
                   f"{res['v1']/0.3048:.2f} ft/s ({res['v1']/0.3048*60:,.0f} ft/min)"),
                  ("Número de Reynolds", f"{res['re1']:,.0f}", res["regimen"]),
                  ("Factor de fricción de Darcy", f"{res['f1']:.5f}", "Colebrook-White"),
                  ("ΣK accesorios", f"{res['k_total']:.3f}", "")]
    if res["L"] > 0 or res["k_total"] > 0:
        resultados += [("Presión de salida", f"{e2.p/PSI:.3f} psia", f"{e2.p/1e5:.4f} bar a"),
                       ("Temperatura de salida", f"{e2.t-273.15:.2f} °C", e2.fase),
                       ("Velocidad a la salida", f"{res['v2']:.3f} m/s", ""),
                       ("Caída de presión", f"{res['dp']/1000:.3f} kPa", f"{res['dp']/PSI:.4f} psi"),
                       ("ΔP por cada 100 m", f"{res['dp']/1000/max(res['L'], 1e-9)*100:.2f} kPa" if res["L"] else "—", "")]
    resultados.append(("Mach a la salida", f"{res['mach2']:.3f}", f"Us = {res['us2']:.0f} m/s (γ = {gamma(e2)})"))
    vt = res["venteo"]
    if vt:
        ed = vt["estado"]
        resultados += [("Venteo: estado a la descarga", f"{ed.fase}, {ed.t-273.15:.1f} °C", f"{vt['p']/PSI:.2f} psia"),
                       ("Venteo: volumen específico", f"{ed.v/FT3_LB:.3f} ft³/lb", f"{ed.v:.4f} m³/kg"),
                       ("Venteo: caudal real", f"{vt['acfm']:,.0f} ACFM", f"{vt['q_m3s']*3600:,.0f} m³/h")]
    if res["espesor"]:
        resultados += esp.filas_resultado(res["espesor"])
    if res.get("presion"):
        datos += pres.filas_datos(res["presion"], [d[0] for d in datos])
        resultados += pres.filas_resultado(res["presion"])
    cap = res.get("curva") or {}
    if cap.get("q_max_m3h"):
        resultados.append(("Capacidad máxima con el criterio de velocidad",
                           f"{cap['q_max_m3h']:,.1f} m³/h reales",
                           f"{cap['q_max_m3h']/e1.v/1000:,.3f} t/h de vapor a la entrada "
                           f"(v_máx = {cap['v_max']:g} m/s)"))
    if res.get("diametro_requerido_m"):
        resultados.append(("Diámetro interior requerido a la velocidad máxima",
                           f"{res['diametro_requerido_m']*1000:.2f} mm", "Di = √(4·Q/(π·v))"))
    tablas = [x for x in (res.get("tabla_diametros"), res.get("tabla_capacidad")) if x]
    if res.get("presion"):
        tablas.append(pres.tabla(res["presion"]))
    sust = [f"v₁ = {res['m']:.4f} kg/s × {e1.v:.5f} m³/kg / (π·{res['d']:.5f}²/4) = {res['v1']:.3f} m/s"]
    if res["L"] > 0:
        sust.append(f"Integración en 60 segmentos: p₁ = {e1.p/1000:.2f} kPa a → p₂ = {e2.p/1000:.2f} kPa a "
                    f"(ΔP = {res['dp']/1000:.3f} kPa); ΔP de un solo paso con ρ₁: "
                    f"{(res['f1']*res['L']/res['d'] + res['k_total'])*res['G']**2*e1.v/2/1000:.3f} kPa")
    if vt:
        sust.append(f"Q = {res['m']*3600/0.45359237:,.0f} lb/h × {vt['estado'].v/FT3_LB:.3f} ft³/lb / 60 = {vt['acfm']:,.0f} ACFM")
    if res["espesor"]:
        r = res["espesor"]
        sust.append(f"t = {r['p_pa']/PSI:.2f}·{r['od_m']/0.0254:.3f}/(2·({r['s_pa']/PSI:,.0f}·{r['e']:g}·{r['w']:g} + "
                    f"{r['p_pa']/PSI:.2f}·{r['y']:g})) = {r['t_presion_m']/0.0254:.4f} in;  t_m = {r['t_m_m']/0.0254:.4f} in "
                    f"≤ {r['t_disponible_m']/0.0254:.4f} in")
    if res.get("presion"):
        sust += pres.sustitucion(res["presion"])
    resumen = [("Velocidad", f"{max(res['v1'], res['v2']):.2f} m/s"), ("ν entrada", f"{e1.v/FT3_LB:.4f} ft³/lb")]
    if res["L"] > 0:
        resumen.append(("Caída de presión", f"{res['dp']/1000:.2f} kPa"))
    if vt:
        resumen.append(("Caudal de venteo", f"{vt['acfm']:,.0f} ACFM"))
    if res["espesor"]:
        resumen.append(("Espesor t_m / disponible", f"{res['espesor']['t_m_m']*1000:.2f} / "
                                                    f"{res['espesor']['t_disponible_m']*1000:.2f} mm"))
    if res.get("presion") and res["presion"]["p_max_pa"]:
        resumen.append(("Presión máxima admisible", f"{res['presion']['p_max_pa']/PSI:,.0f} psig"))
    return Memoria(
        titulo="Línea de vapor: velocidad, caída de presión y espesor", caso=c["nombre"], version=__version__,
        huella=huella(c), documento=c.get("documento", ""),
        objetivo="Verificar la velocidad, la caída de presión y el espesor de pared de una línea de vapor con "
                 "propiedades IAPWS-IF97, y el caudal real de venteo cuando descarga a un silenciador.",
        datos=datos, resultados=resultados, verificaciones=res["verificaciones"], advertencias=res["advertencias"],
        ecuaciones=ECUACIONES, sustitucion=sust, supuestos=SUPUESTOS,
        referencias=FUENTES + pres.REFERENCIAS, notas=c.get("notas", ""),
        escena=construir(c, res), resumen=resumen, tablas=tablas)
