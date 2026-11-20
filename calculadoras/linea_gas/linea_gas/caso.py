"""Caso en unidades de usuario (JSON) -> Entradas en SI; ejecución y reportes."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json

from . import __version__
from . import unidades as u
from .datos import GASES, REFERENCIAS, d_interior_m
from .motor import Accesorio, Entradas, calcular

AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un "
         "ingeniero responsable ni constituyen una validación del proyecto.")
_DIF = {"kPa": 1000.0, "psi": u.PSI, "bar": u.BAR}


def a_entradas(c: dict) -> Entradas:
    patm = u.presion_a_pa_abs(c.get("p_atm_psia", 14.696), "psia", 0.0)
    tub = c["tuberia"]
    d = tub["d_interior_mm"] / 1000 if tub.get("d_interior_mm") else d_interior_m(tub["nps"], tub["cedula"])
    crit = c.get("criterios", {})
    p_min = crit.get("p_min_salida")
    return Entradas(
        nombre=c["nombre"], gas=c.get("gas", "aire"),
        q_ref_m3s=u.caudal_a_m3s(c["caudal"]["valor"], c["caudal"]["unidad"]), ref=c["caudal"]["referencia"],
        p_entrada_pa=u.presion_a_pa_abs(c["p_entrada"]["valor"], c["p_entrada"]["unidad"], patm),
        t_k=u.temperatura_a_k(c["temperatura"]["valor"], c["temperatura"]["unidad"]),
        longitud_m=c["longitud_m"], d_interior_m=d, nps=tub.get("nps"),
        rugosidad_m=c.get("rugosidad_mm", 0.04572) / 1000,
        accesorios=[Accesorio(a["tipo"], a.get("cantidad", 1), a.get("k")) for a in c.get("accesorios", [])],
        z=c.get("z", 1.0), mu_pa_s=c.get("mu_pa_s"),
        v_max_m_s=crit.get("v_max_m_s"),
        dp_max_pa=None if crit.get("dp_max") is None else crit["dp_max"]["valor"] * _DIF[crit["dp_max"]["unidad"]],
        p_min_salida_pa=None if p_min is None else u.presion_a_pa_abs(p_min["valor"], p_min["unidad"], patm),
    )


def huella(c: dict) -> str:
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def ejecutar(c: dict):
    e = a_entradas(c)
    return e, calcular(e)


def tabla(c, e, r):
    psi = lambda pa: f"{pa / u.PSI:.3f} psi"
    filas = [
        ("Gas", GASES[e.gas]["nombre"], GASES[e.gas]["fuente"]),
        ("Caudal", f"{c['caudal']['valor']:g} {c['caudal']['unidad']}", REFERENCIAS[e.ref][2]),
        ("Flujo másico", f"{r.mdot_kg_s*3600:.3f} kg/h", ""),
        ("Presión de entrada", f"{e.p_entrada_pa/u.PSI:.3f} psia ({e.p_entrada_pa/1e5:.4f} bar a)", ""),
        ("Temperatura", f"{e.t_k-273.15:.2f} °C", ""),
        ("Diámetro interior", f"{e.d_interior_m*1000:.2f} mm ({e.d_interior_m/0.0254:.3f} in)",
         f"NPS {c['tuberia'].get('nps')} céd. {c['tuberia'].get('cedula')}" if c['tuberia'].get('nps') else "capturado"),
        ("Longitud", f"{e.longitud_m:g} m", ""),
        ("Caudal real a la entrada", f"{r.q_actual_m3h:.4f} m³/h", "Q_a = ṁ/ρ₁"),
        ("Densidad a la entrada", f"{r.rho_entrada:.4f} kg/m³", f"Z = {e.z:g}"),
        ("Velocidad entrada / salida", f"{r.v_entrada:.4f} / {r.v_salida:.4f} m/s", f"Mach salida {r.mach:.4f}"),
        ("Viscosidad dinámica", f"{r.mu:.4e} Pa·s", ""),
        ("Número de Reynolds", f"{r.re:,.0f}", ""),
        ("Factor de fricción Darcy (Colebrook)", f"{r.f:.5f}", f"Swamee-Jain: {r.f_swamee_jain:.5f}"),
        ("ΣK accesorios", f"{r.k_total:.3f}", "; ".join(f"{n}×{t} K={k:g}" for t, n, k, _ in r.detalle_k)),
        ("ΔP tubo recto", f"{r.dp_tubo_pa/1000:.4f} kPa", psi(r.dp_tubo_pa)),
        ("ΔP accesorios", f"{r.dp_accesorios_pa/1000:.4f} kPa", psi(r.dp_accesorios_pa)),
        ("ΔP TOTAL", f"{r.dp_total_pa/1000:.4f} kPa", psi(r.dp_total_pa)),
        ("Presión a la salida", f"{r.p_salida_pa/u.PSI:.3f} psia ({(r.p_salida_pa-101325)/1e5:.4f} bar man. ref. 1 atm)", ""),
    ]
    if r.dp_fritzsche_pa is not None:
        filas.append(("ΔP Fritzsche (comparación, Menon ec. 5.34)", f"{r.dp_fritzsche_pa/1000:.4f} kPa", psi(r.dp_fritzsche_pa)))
    return filas


def a_texto(c, e, r) -> str:
    l = [f"LÍNEA DE GAS — {c['nombre']}", f"v{__version__} | {_dt.datetime.now():%Y-%m-%d %H:%M} | huella {huella(c)}", ""]
    l += [f"  {a}: {b}" + (f"  [{n}]" if n else "") for a, b, n in tabla(c, e, r)]
    if r.verificaciones:
        l += ["", "VERIFICACIONES"] + [f"  [{s}] {a}: {b} (límite {lim})" for a, b, lim, s in r.verificaciones]
    if r.advertencias:
        l += ["", "ADVERTENCIAS"] + [f"  - {a}" for a in r.advertencias]
    l += ["", AVISO]
    return "\n".join(l)


def exportar_excel(casos: list, ruta: str) -> str:
    """Un renglón por caso: permite el resumen de varias líneas en una hoja."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    enc = ["Línea", "ṁ (kg/h)", "Q real (m³/h)", "Di (mm)", "L (m)", "v₁ (m/s)", "ρ₁ (kg/m³)", "Re", "f",
           "ΣK", "ΔP tubo (psi)", "ΔP acc. (psi)", "ΔP total (psi)", "P salida (psia)", "ΔP Fritzsche (psi)", "Huella"]
    ws.append(enc)
    for celda in ws[1]:
        celda.font, celda.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")
    for c in casos:
        e, r = ejecutar(c)
        ws.append([c["nombre"], r.mdot_kg_s * 3600, r.q_actual_m3h, e.d_interior_m * 1000, e.longitud_m, r.v_entrada,
                   r.rho_entrada, r.re, r.f, r.k_total, r.dp_tubo_pa / u.PSI, r.dp_accesorios_pa / u.PSI,
                   r.dp_total_pa / u.PSI, r.p_salida_pa / u.PSI,
                   None if r.dp_fritzsche_pa is None else r.dp_fritzsche_pa / u.PSI, huella(c)])
        hoja = wb.create_sheet(c["nombre"][:28].replace("/", "-").replace('"', "in"))
        hoja.append(["Parámetro", "Valor", "Nota"])
        for f in tabla(c, e, r):
            hoja.append(list(f))
        for v in r.verificaciones:
            hoja.append([f"Verificación: {v[0]}", f"{v[1]} (límite {v[2]})", v[3]])
        for a in r.advertencias:
            hoja.append(["Advertencia", a, ""])
        hoja.append(["", AVISO, ""])
        for col, w in zip("ABC", (42, 45, 60)):
            hoja.column_dimensions[col].width = w
    ws.column_dimensions["A"].width = 38
    wb.save(ruta)
    return ruta
