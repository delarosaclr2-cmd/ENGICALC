"""Memoria de cálculo de la línea de aceite."""
from . import __version__
from .esquema import construir
from .motor import calcular, huella
from .nucleo import espesor as esp
from .nucleo import presion as pres
from .nucleo import seleccion as sel
from .nucleo.unidades import PSI
from .ui.memoria_pdf import Memoria

ECUACIONES = [
    "ν(T): log log Z = A − B·log T,  Z = ν + 0.7 + C − D  (ASTM D341, Menon ecs. 6.13–6.16; T en K)",
    "v = Q / A,  A = π·Di²/4;   Re = v·Di / ν  (= 353 678·Q/(ν·D), Q m³/h, ν cSt, D mm; Menon ec. 6.38)",
    "Laminar (Re ≤ 2100): f = 64/Re;   turbulento: 1/√f = −2·log₁₀[ε/(3.7·Di) + 2.51/(Re·√f)]  (Colebrook-White)",
    "h_f = f·(L/Di)·v²/(2g);   h_acc = ΣK·v²/(2g)  (K de Menon tabla 5.11);   [m del ACEITE: Menon ec. 6.49]",
    "ΔP = ρ·g·(h_f + h_acc + Δz)",
    "Espesor: t = P·D/(2·(S·E·W + P·Y));  t_m = t + c ≤ t_nominal·(1 − tolerancia)",
] + pres.ECUACIONES + sel.ECUACIONES
SUPUESTOS = [
    "Flujo permanente, isotérmico e incompresible; tubería llena (en drenajes por gravedad no se cumple).",
    "Rugosidad de acero comercial salvo que se capture otra.",
    "Accesorios con K de turbulencia completa (Menon tabla 5.11); en laminar, K = f·(L/D).",
    "El intervalo de velocidad es un criterio de diseño: el límite superior se verifica; quedar por debajo del inferior "
    "solo indica tubería holgada.",
]
FUENTES = [
    "Menon, E. S. Piping Calculations Manual. McGraw-Hill, 2005, cap. 6 (ecs. 6.13–6.16, 6.38, 6.49) y tabla 5.11.",
    "ISO 3448 (grados de viscosidad ISO VG a 40 °C, ±10 %).",
    "ASME B36.10M (diámetros); ASME B31.3-2014 §304.1.2 y Tabla A-1 (A106 Gr. B).",
]


def evaluar(c: dict) -> Memoria:
    res = calcular(c)
    t = res["tramo"]
    tub = c["tuberia"]
    acc = "; ".join(f"{a.get('cantidad', 1)} × {a['tipo']}" + (f" (K = {a['k']})" if a.get("k") is not None else "")
                    for a in c.get("accesorios", [])) or "Ninguno capturado"
    datos = [("Caudal", f"{c['caudal']['valor']:g} {c['caudal']['unidad']}", f"{res['q']*3600:.3f} m³/h"),
             ("Temperatura de operación", f"{res['t_c']:g} °C", c.get("p_operacion", "")),
             ("Viscosidad cinemática", f"{res['nu']:.3f} cSt", res["ref_nu"]),
             ("Densidad", f"{res['rho']:.1f} kg/m³", res["ref_rho"]),
             ("Tubería", (f"NPS {tub['nps']} céd. {tub.get('cedula')}" if tub.get("nps") else "Di capturado")
              + f"; Di = {res['d']*1000:.2f} mm", "ASME B36.10M" if tub.get("nps") else ""),
             ("Longitud", f"{res['L']:g} m", ""), ("Rugosidad", f"{res['eps']*1000:.4f} mm", ""),
             ("Desnivel Δz (salida − entrada)", f"{res['dz']:+g} m", ""),
             ("Accesorios", acc, "K de Menon tabla 5.11 (turbulento) o f·L/D (laminar)")]
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
                  ("Pérdida en tubería recta", f"{t['h_tuberia']:.4f} m de aceite", f"{t['dp_tuberia']/1000:.3f} kPa"),
                  ("Pérdida en accesorios", f"{t['h_accesorios']:.4f} m de aceite", f"{t['dp_accesorios']/1000:.3f} kPa"),
                  ("ΔP por fricción", f"{t['dp_friccion']/PSI:.4f} psi", f"{t['dp_friccion']/1e5:.4f} bar"),
                  ("ΔP total (con desnivel)", f"{t['dp_total']/PSI:.4f} psi", f"{t['dp_total']/1000:.3f} kPa")]
    if res["nu40"]:
        resultados.append(("Viscosidad a 40 °C (de los dos puntos)", f"{res['nu40']:.2f} cSt", res["iso"] or "sin grado ISO VG"))
    if res["espesor"]:
        resultados += esp.filas_resultado(res["espesor"])
    if res.get("presion"):
        datos += pres.filas_datos(res["presion"], [d[0] for d in datos])
        resultados += pres.filas_resultado(res["presion"])
    cap = res.get("curva") or {}
    if cap.get("q_max_m3h"):
        resultados.append(("Capacidad máxima con el criterio de velocidad",
                           f"{sel.redondeo_seguro(cap['q_max_m3h'], 2, 'abajo'):,.2f} m³/h",
                           f"{sel.redondeo_seguro(cap['q_max_m3h']*1000/60, 1, 'abajo'):,.1f} L/min "
                           f"(v_máx = {cap['v_max']:g} m/s; redondeada hacia abajo)"))
    if res.get("diametro_requerido_m"):
        resultados.append(("Diámetro interior requerido a la velocidad máxima",
                           f"{sel.redondeo_seguro(res['diametro_requerido_m']*1000, 2, 'arriba'):.2f} mm",
                           "Di = √(4·Q/(π·v)), redondeado hacia arriba"))
    tablas = [x for x in (res.get("tabla_diametros"), res.get("tabla_capacidad")) if x]
    if res.get("presion"):
        tablas.append(pres.tabla(res["presion"]))
    D = res["d"] * 1000
    sust = [f"Re = 353 678 × {res['q']*3600:.3f} / ({res['nu']:.3f} × {D:.2f}) = {t['re']:,.0f}",
            f"h_f = 50.94 × {t['f']:.5f} × {res['L']:g} × {t['v']:.4f}² / {D:.2f} = {t['h_tuberia']:.4f} m de aceite",
            f"ΔP = {res['rho']:.1f}·9.80665·({t['h_tuberia']:.4f} + {t['h_accesorios']:.4f} + {res['dz']:g}) = "
            f"{t['dp_total']:.1f} Pa = {t['dp_total']/PSI:.4f} psi"]
    if res["espesor"]:
        r = res["espesor"]
        sust.append(f"t = {r['p_pa']/PSI:.2f}·{r['od_m']/0.0254:.3f}/(2·({r['s_pa']/PSI:,.0f}·{r['e']:g}·{r['w']:g} + "
                    f"{r['p_pa']/PSI:.2f}·{r['y']:g})) = {r['t_presion_m']/0.0254:.4f} in;  t_m = {r['t_m_m']/0.0254:.4f} in")
    if res.get("presion"):
        sust += pres.sustitucion(res["presion"])
    resumen = [("Velocidad", f"{t['v']:.3f} m/s"), ("ΔP total", f"{t['dp_total']/PSI:.3f} psi"),
               ("Reynolds", f"{t['re']:,.0f} ({t['regimen'].split(' ')[0]})"), ("Viscosidad", f"{res['nu']:.2f} cSt")]
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
    return Memoria(
        titulo="Línea de aceite: velocidad, pérdidas y espesor", caso=c["nombre"], version=__version__,
        huella=huella(c), documento=c.get("documento", ""),
        objetivo="Verificar la velocidad, el régimen de flujo, la caída de presión y el espesor de pared de una línea "
                 "de aceite con viscosidad corregida por temperatura (ASTM D341).",
        datos=datos, resultados=resultados, verificaciones=res["verificaciones"], advertencias=res["advertencias"],
        ecuaciones=ECUACIONES, sustitucion=sust, supuestos=SUPUESTOS,
        referencias=FUENTES + pres.REFERENCIAS, notas=c.get("notas", ""),
        escena=construir(c, res), resumen=resumen, tablas=tablas)
