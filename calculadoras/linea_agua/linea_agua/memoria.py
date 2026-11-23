"""Memoria de cálculo de la línea de agua."""
from . import __version__
from .esquema import construir
from .motor import ErrorEntrada, calcular, huella
from .nucleo import espesor as esp
from .nucleo import presion as pres
from .nucleo import seleccion as sel
from .nucleo.unidades import PSI
from .ui.memoria_pdf import Memoria

ECUACIONES = [
    "ρ, μ: IAPWS-IF97 región 1 (ρ = 1/v, v = π·γ_π·R·T/p) e IAPWS 2008 (μ = μ₀·μ₁)",
    "v = Q / A,  A = π·Di²/4;   Re = ρ·v·Di / μ",
    "Laminar (Re ≤ 2100): f = 64/Re;   turbulento: 1/√f = −2·log₁₀[ε/(3.7·Di) + 2.51/(Re·√f)]  (Colebrook-White)",
    "h_f = f·(L/Di)·v²/(2g);   h_acc = ΣK·v²/(2g)  (K de Menon tabla 5.11);   [m del agua que circula]",
    "ΔP = ρ·g·(h_f + h_acc + Δz)",
    "NPSHa = (p_sup − p_v)/(ρ·g) + z − h_f,succión",
    "Espesor: t = P·D/(2·(S·E·W + P·Y));  t_m = t + c ≤ t_nominal·(1 − tolerancia)",
] + pres.ECUACIONES + sel.ECUACIONES
SUPUESTOS = [
    "Flujo permanente, isotérmico e incompresible; tubería llena.",
    "Rugosidad de acero comercial salvo que se capture otra.",
    "Accesorios con K de turbulencia completa (Menon tabla 5.11); en laminar, K = f·(L/D).",
    "El intervalo de velocidad es un criterio de diseño: el límite superior se verifica; quedar por debajo del inferior "
    "solo indica tubería holgada.",
]
FUENTES = [
    "Menon, E. S. Piping Calculations Manual. McGraw-Hill, 2005, cap. 1 (ecs. 1.23–1.26) y tabla 4.4 (velocidades).",
    "IAPWS R7-97(2012) (IF97) e IAPWS R12-08 (viscosidad).",
    "ASME B36.10M (diámetros); ASME B31.3-2014 §304.1.2; ASME B31.1 §104.1.2 (no proporcionado: S capturado).",
]


def evaluar(c: dict) -> Memoria:
    res = calcular(c)
    t = res["tramo"]
    tub = c["tuberia"]
    acc = "; ".join(f"{a.get('cantidad', 1)} × {a['tipo']}" + (f" (K = {a['k']})" if a.get("k") is not None else "")
                    for a in c.get("accesorios", [])) or "Ninguno capturado"
    datos = [("Servicio", "Succión" if c.get("servicio") == "succion" else "Descarga / línea", ""),
             ("Caudal", f"{c['caudal']['valor']:g} {c['caudal']['unidad']}", f"{res['q']*3600:.3f} m³/h"),
             ("Temperatura", f"{float(c['temperatura_c']):g} °C", ""),
             ("Propiedades", f"ρ = {res['rho']:.3f} kg/m³ · μ = {res['mu']*1000:.4f} cP", res["ref_prop"]),
             ("Tubería", (f"NPS {tub['nps']} céd. {tub.get('cedula')}" if tub.get("nps") else "Di capturado")
              + f"; Di = {res['d']*1000:.2f} mm", "ASME B36.10M" if tub.get("nps") else ""),
             ("Longitud", f"{res['L']:g} m", ""), ("Rugosidad", f"{res['eps']*1000:.4f} mm", ""),
             ("Desnivel Δz (salida − entrada)", f"{res['dz']:+g} m", ""),
             ("Accesorios", acc, "K de Menon tabla 5.11 si no se capturó")]
    cv = c.get("criterio_velocidad") or {}
    if cv.get("v_max_m_s") not in (None, ""):
        datos.append(("Criterio de velocidad", f"{cv.get('v_min_m_s', '—')}–{cv['v_max_m_s']} m/s", cv.get("fuente", "")))
    if res.get("datos_espesor"):
        datos += res["datos_espesor"]
    resultados = [("Área interior A", f"{sel.area(res['d'])*1e3:.4f} ×10⁻³ m²", "A = π·Di²/4"),
                  ("Velocidad", f"{t['v']:.4f} m/s", f"{t['v']/0.3048:.3f} ft/s "
                   f"({t['v']*3600:,.1f} m/h)"),
                  ("Número de Reynolds", f"{t['re']:,.0f}", t["regimen"]),
                  ("Factor de fricción de Darcy", f"{t['f']:.5f}", "64/Re" if t["laminar"] else "Colebrook-White"),
                  ("ΣK accesorios", f"{t['k_total']:.3f}", ""),
                  ("Pérdida en tubería recta", f"{t['h_tuberia']:.4f} m", f"{t['dp_tuberia']/1000:.3f} kPa"),
                  ("Pérdida en accesorios", f"{t['h_accesorios']:.4f} m", f"{t['dp_accesorios']/1000:.3f} kPa"),
                  ("ΔP por fricción", f"{t['dp_friccion']/PSI:.4f} psi", f"{t['dp_friccion']/1000:.3f} kPa"),
                  ("ΔP total (con desnivel)", f"{t['dp_total']/PSI:.4f} psi", f"{t['dp_total']/1000:.3f} kPa")]
    if res["p_vapor"] is not None:
        resultados.append(("Presión de vapor a la temperatura", f"{res['p_vapor']/1000:.3f} kPa a", "IAPWS-IF97 región 4"))
    if res["npsh"]:
        resultados.append(("NPSH disponible", f"{res['npsh']['npsha']:.3f} m", ""))
    if res["espesor"]:
        resultados += esp.filas_resultado(res["espesor"])
    if res.get("presion"):
        datos += pres.filas_datos(res["presion"], [d[0] for d in datos])
        resultados += pres.filas_resultado(res["presion"])
    cap = res.get("curva") or {}
    if cap.get("q_max_m3h"):
        resultados.append(("Capacidad máxima con el criterio de velocidad",
                           f"{sel.redondeo_seguro(cap['q_max_m3h'], 2, 'abajo'):,.2f} m³/h",
                           f"Q = v_máx·A, v_máx = {cap['v_max']:g} m/s (redondeada hacia abajo)"))
    if res.get("diametro_requerido_m"):
        resultados.append(("Diámetro interior requerido a la velocidad máxima",
                           f"{sel.redondeo_seguro(res['diametro_requerido_m']*1000, 2, 'arriba'):.2f} mm",
                           "Di = √(4·Q/(π·v)), redondeado hacia arriba"))
    tablas = [x for x in (res.get("tabla_diametros"), res.get("tabla_capacidad")) if x]
    if res.get("presion"):
        tablas.append(pres.tabla(res["presion"]))
    D = res["d"] * 1000
    sust = [f"v = {res['q']:.6f} / (π·{res['d']:.5f}²/4) = {t['v']:.4f} m/s;  Re = {res['rho']:.2f}·{t['v']:.4f}·{res['d']:.5f}"
            f"/{res['mu']:.4e} = {t['re']:,.0f}",
            f"h_f = {t['f']:.5f}·({res['L']:g}/{res['d']:.5f})·{t['v']:.4f}²/(2·9.80665) = {t['h_tuberia']:.4f} m  "
            f"(equivale a Menon ec. 1.25: 50.94·f·L·v²/D[mm], D = {D:.1f} mm)",
            f"ΔP = {res['rho']:.2f}·9.80665·({t['h_tuberia']:.4f} + {t['h_accesorios']:.4f} + {res['dz']:g}) = "
            f"{t['dp_total']:.1f} Pa"]
    if res["npsh"]:
        n = res["npsh"]
        sust.append(f"NPSHa = ({n['p_sup']:.0f} − {res['p_vapor']:.0f})/({res['rho']:.2f}·9.80665) + {n['z']:g} − "
                    f"{t['h_friccion']:.4f} = {n['npsha']:.3f} m")
    if res["espesor"]:
        r = res["espesor"]
        sust.append(f"t = {r['p_pa']/PSI:.2f}·{r['od_m']/0.0254:.3f}/(2·({r['s_pa']/PSI:,.0f}·{r['e']:g}·{r['w']:g} + "
                    f"{r['p_pa']/PSI:.2f}·{r['y']:g})) = {r['t_presion_m']/0.0254:.4f} in;  t_m = {r['t_m_m']/0.0254:.4f} in")
    if res.get("presion"):
        sust += pres.sustitucion(res["presion"])
    resumen = [("Velocidad", f"{t['v']:.3f} m/s"), ("ΔP por fricción", f"{t['dp_friccion']/PSI:.3f} psi"),
               ("Reynolds", f"{t['re']:,.0f}")]
    if res["npsh"]:
        resumen.append(("NPSH disponible", f"{res['npsh']['npsha']:.2f} m"))
    if res["espesor"]:
        resumen.append(("Espesor t_m / disponible", f"{res['espesor']['t_m_m']*1000:.2f} / "
                                                    f"{res['espesor']['t_disponible_m']*1000:.2f} mm"))
    if res.get("presion") and res["presion"]["p_max_pa"]:
        # Fuera del dominio de la ec. (3a) el número existe pero no es una admisible comprobada:
        # en el tablero de resumen tiene que verse, o se lee como un resultado válido.
        _pm = res["presion"]
        resumen.append(("Presión máxima admisible",
                        f"{_pm['p_max_pa']/PSI:,.0f} psig"
                        + ("" if _pm.get("dominio_valido", True) else " (no evaluable)")))
    if cap.get("q_max_m3h"):
        resumen.append(("Capacidad máxima", f"{sel.redondeo_seguro(cap['q_max_m3h'], 1, 'abajo'):,.1f} m³/h"))
    return Memoria(
        titulo="Línea de agua: velocidad, pérdidas, NPSH y espesor", caso=c["nombre"], version=__version__,
        huella=huella(c), documento=c.get("documento", ""),
        objetivo="Verificar la velocidad, la caída de presión, el NPSH disponible (succiones) y el espesor de pared "
                 "de una línea de agua con propiedades IAPWS-IF97.",
        datos=datos, resultados=resultados, verificaciones=res["verificaciones"], advertencias=res["advertencias"],
        ecuaciones=ECUACIONES, sustitucion=sust, supuestos=SUPUESTOS,
        referencias=FUENTES + pres.REFERENCIAS, notas=c.get("notas", ""),
        escena=construir(c, res), resumen=resumen, tablas=tablas)
