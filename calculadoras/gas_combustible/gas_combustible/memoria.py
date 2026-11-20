"""Arma la memoria de cálculo del gas combustible a partir de los resultados del motor."""
from . import __version__
from .caso import ejecutar, huella
from .esquema import construir
from .motor import COMPONENTES, M_AIRE, R_U, REFERENCIAS
from .ui.memoria_pdf import Memoria

ECUACIONES = [
    "M = Σ xᵢ · Mᵢ   (xᵢ fracción molar normalizada; Mᵢ de GPA 2145-16)",
    "SG ideal = M / M_aire,  M_aire = 28.9625 kg/kmol",
    "ρ_ref = P_ref · M / (Z_ref · R_u · T_ref)   (R_u = 8314.462618 J/(kmol·K))",
    "ṁ_f = HR · P_el / (LHV · 3600)   (kg/s; HR en kJ/kWh, P_el en kW, LHV en kJ/kg)",
    "LHV_másico = LHV_volumétrico / ρ_ref   (misma condición de referencia)",
    "Q_ref = ṁ / ρ_ref ;  Q_real = ṁ / ρ(P, T, Z)",
    "Consumos: total diario = Σ de TODAS las unidades; máximo coincidente = máx(total diario); "
    "suma de máximos no coincidentes = Σ máx(unidad)",
]
SUPUESTOS = [
    "Composición del reporte de laboratorio normalizada a 100 % mol.",
    "Z a la condición de referencia con CoolProp (HEOS) salvo que se capture el del laboratorio.",
    "Tasa de calor, potencia y LHV del fabricante son datos de entrada (no verificados por la calculadora).",
]
FUENTES = [
    "GPA 2145-16: propiedades físicas de componentes del gas natural (masas molares).",
    "CoolProp (Bell et al., 2014): ecuación de estado HEOS para mezclas.",
    "Datos del caso: cromatografía del sitio y hojas de desempeño del fabricante de la turbina.",
]


def evaluar(c: dict) -> Memoria:
    c = dict(c)
    # Secciones opcionales que la ventana deja vacías: se eliminan para que el motor no las evalúe
    if c.get("linea") and (c["linea"].get("p") or {}).get("valor") in (None, ""):
        c.pop("linea")
    if c.get("turbina") and c["turbina"].get("heat_rate_kj_kwh") in (None, "") \
            and c["turbina"].get("potencia_kw") in (None, ""):
        c.pop("turbina")
    if isinstance(c.get("composicion"), list):          # la ventana edita la composición como lista
        c["composicion"] = {d["componente"]: float(d["pct_mol"]) for d in c["composicion"]}
    out = ejecutar(c)
    pr = out["prop"]
    datos = [(f"{k}", f"{v:g} % mol", f"M = {COMPONENTES[k][0]} kg/kmol") for k, v in c["composicion"].items()]
    datos.append(("Condición de referencia", pr.ref, f"{REFERENCIAS[pr.ref][0]/1000:.3f} kPa, {REFERENCIAS[pr.ref][1]-273.15:.2f} °C"))
    if c.get("lhv_laboratorio_mj_m3"):
        datos.append(("LHV del laboratorio", f"{c['lhv_laboratorio_mj_m3']} MJ/m³", "a la condición de referencia"))
    t = c.get("turbina")
    if t:
        datos += [("Turbina", t.get("nombre", ""), ""), ("Tasa de calor", f"{t['heat_rate_kj_kwh']:g} kJ/kWh", "fabricante"),
                  ("Potencia eléctrica", f"{t['potencia_kw']:g} kW", "fabricante"),
                  ("LHV del fabricante", f"{t['lhv_kj_kg']:g} kJ/kg" if t.get("lhv_kj_kg") else "(se usa el del laboratorio)", "")]
    for k in c.get("consumidores_kg_h", []):
        datos.append((f"Consumidor: {k['nombre']}", f"{k['kg_h']:g} kg/h", "dato"))
    if c.get("linea"):
        datos.append(("Condición de la línea", f"{c['linea']['p']['valor']:g} {c['linea']['p']['unidad']}, {c['linea']['t_c']:g} °C", ""))
    if c.get("consumos"):
        datos.append(("Tabla de consumos", f"{len(c['consumos']['fechas'])} días × {len(c['consumos']['series'])} unidades",
                      c["consumos"].get("unidad", "")))
    p, tr = REFERENCIAS[pr.ref]
    sust = [f"M = Σ xᵢ·Mᵢ = {pr.m_kg_kmol:.4f} kg/kmol;  SG = {pr.m_kg_kmol:.4f} / {M_AIRE} = {pr.sg_ideal:.4f}",
            f"ρ_ref = {p:.0f} × {pr.m_kg_kmol:.4f} / ({pr.z_ref:.5f} × {R_U} × {tr:.4f}) = {pr.rho_ref:.5f} kg/m³"]
    if out["lhv_lab"]:
        sust.append(f"LHV = {c['lhv_laboratorio_mj_m3']} × 1000 / {pr.rho_ref:.5f} = {out['lhv_lab']:,.1f} kJ/kg")
    if out["turbina"]:
        sust.append(f"ṁ_f = {t['heat_rate_kj_kwh']:g} × {t['potencia_kw']:g} / ({out['turbina']['lhv']:g} × 3600) = "
                    f"{out['turbina']['m_kg_s']:.6f} kg/s = {out['turbina']['m_kg_s']*3600:,.2f} kg/h")
    resumen = [("Masa molar", f"{pr.m_kg_kmol:.4f} kg/kmol"), ("Densidad de referencia", f"{pr.rho_ref:.5f} kg/m³")]
    if out["lhv_lab"]:
        resumen.append(("LHV (laboratorio)", f"{out['lhv_lab']:,.0f} kJ/kg"))
    if out["flujos"]:
        tot = sum(k for _, k in out["flujos"])
        resumen += [("Flujo total", f"{tot:,.1f} kg/h"), ("Flujo total (ref)", f"{tot/pr.rho_ref:,.1f} m³/h")]
    if out["consumo"]:
        e = out["consumo"]
        resumen += [("Máximo coincidente", f"{e.total_max:,.0f} ({e.dia_max})"), ("Promedio diario", f"{e.promedio:,.0f}")]
    return Memoria(
        titulo="Gas combustible: propiedades, flujo de turbina y consumos", caso=c["nombre"], version=__version__,
        huella=huella(c), documento=c.get("documento", ""),
        objetivo="Obtener las propiedades del gas a partir de su composición, el flujo de combustible de la turbina "
                 "y los consumos de diseño.",
        datos=datos, resultados=[(a, b, n) for a, b, n in out["filas"] if not a.startswith("Suma de la")],
        advertencias=out["advertencias"], ecuaciones=ECUACIONES, sustitucion=sust, supuestos=SUPUESTOS,
        referencias=FUENTES, notas=c.get("notas", ""), escena=construir(c, out), resumen=resumen[:6])
