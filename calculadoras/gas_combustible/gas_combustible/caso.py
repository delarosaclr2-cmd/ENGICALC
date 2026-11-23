"""Caso JSON -> resultados, texto y Excel."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json

from . import __version__
from . import unidades as u
from .motor import (estadistica, flujo_turbina_kg_s, lhv_masico, propiedades, rho_real, z_coolprop)

AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un "
         "ingeniero responsable ni constituyen una validación del proyecto.")


def huella(c):
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def ejecutar(c: dict) -> dict:
    pr = propiedades(c["composicion"], c.get("referencia", "estandar_60F"), c.get("z_ref"),
                     c.get("usar_coolprop", True))
    out = {"prop": pr, "filas": [], "consumo": None, "advertencias": list(pr.advertencias),
           "flujos": [], "lhv_lab": None, "rho_linea": None, "turbina": None}
    f = out["filas"]
    f += [("Suma de la composición", f"{pr.suma_pct:.3f} % mol", ""),
          ("Masa molar", f"{pr.m_kg_kmol:.4f} kg/kmol", "Σ x·M (GPA 2145-16)"),
          ("Gravedad específica ideal", f"{pr.sg_ideal:.4f}", "M/28.9625"),
          (f"Z a condición de referencia ({pr.ref})", f"{pr.z_ref:.5f}", pr.fuente_z),
          (f"Densidad a condición de referencia ({pr.ref})", f"{pr.rho_ref:.5f} kg/m³", "")]
    lhv = None
    if c.get("lhv_laboratorio_mj_m3"):
        lhv = lhv_masico(c["lhv_laboratorio_mj_m3"], pr.rho_ref)
        out["lhv_lab"] = lhv
        f.append(("LHV másico desde el laboratorio", f"{lhv:,.1f} kJ/kg",
                  f"{c['lhv_laboratorio_mj_m3']} MJ/m³ ÷ ρ_ref (misma referencia)"))
    flujos = []
    t = c.get("turbina")
    if t:
        lhv_t = t.get("lhv_kj_kg") or lhv
        m = flujo_turbina_kg_s(t["heat_rate_kj_kwh"], t["potencia_kw"], lhv_t)
        flujos.append((t.get("nombre", "Turbina"), m * 3600))
        out["turbina"] = {"m_kg_s": m, "lhv": lhv_t}
        f.append(("ṁ turbina = HR·P/(LHV·3600)", f"{m:.6f} kg/s = {m*3600:,.2f} kg/h",
                  f"HR {t['heat_rate_kj_kwh']} kJ/kWh, P {t['potencia_kw']} kW, LHV {lhv_t} kJ/kg"))
        if lhv and t.get("lhv_kj_kg"):
            dif = (t["lhv_kj_kg"] / lhv - 1) * 100
            f.append(("Diferencia LHV fabricante vs laboratorio", f"{dif:+.2f} %", "verificación de consistencia"))
            if abs(dif) > 2:
                out["advertencias"].append(f"El LHV del fabricante difiere {dif:+.1f} % del de la cromatografía")
    for k in c.get("consumidores_kg_h", []):
        flujos.append((k["nombre"], k["kg_h"]))
    lin = c.get("linea")
    rho_l = None
    if lin:
        patm = u.presion_a_pa_abs(c.get("p_atm_psia", 14.696), "psia", 0)
        p = u.presion_a_pa_abs(lin["p"]["valor"], lin["p"]["unidad"], patm)
        tk = lin["t_c"] + 273.15
        z = lin.get("z") or z_coolprop(c["composicion"], tk, p) or 1.0
        rho_l = rho_real(pr.m_kg_kmol, p, tk, z)
        out["rho_linea"] = (rho_l, p, tk, z)
        f.append(("Densidad en la línea", f"{rho_l:.4f} kg/m³", f"{p/u.PSI:.2f} psia, {lin['t_c']} °C, Z = {z:.4f}"))
    out["flujos"] = flujos
    tot = 0.0
    for nombre, kgh in flujos:
        tot += kgh
        q = kgh / pr.rho_ref
        f.append((f"Flujo {nombre}", f"{kgh:,.2f} kg/h = {q:,.2f} m³/h ref = {q*24:,.0f} m³/d ref",
                  "" if rho_l is None else f"real en línea: {kgh/rho_l:,.2f} m³/h"))
    if len(flujos) > 1:
        f.append(("Flujo total", f"{tot:,.2f} kg/h = {tot/pr.rho_ref:,.2f} m³/h ref", ""))
    cs = c.get("consumos")
    if cs:
        e = estadistica(cs["fechas"], cs["series"])
        out["consumo"] = e
        un = cs.get("unidad", "m³/d")
        f += [("Día de máximo consumo coincidente", f"{e.dia_max}: {e.total_max:,.0f} {un}", f"{e.total_max/24:,.1f} por hora"),
              ("Promedio diario (todas las unidades)", f"{e.promedio:,.0f} {un}", f"{e.promedio/24:,.1f} por hora"),
              ("Suma de máximos no coincidentes", f"{e.suma_max_no_coincidentes:,.0f} {un}",
               f"{e.suma_max_no_coincidentes/24:,.1f} por hora (conservador)")]
        f += [(f"Máximo {k}", f"{v:,.0f} {un}", f"día {e.dia_max_por_unidad[k]}") for k, v in e.max_por_unidad.items()]
    return out


def a_texto(c, out) -> str:
    l = [f"GAS COMBUSTIBLE — {c['nombre']}", f"v{__version__} | {_dt.datetime.now():%Y-%m-%d %H:%M} | huella {huella(c)}", ""]
    l += [f"  {a}: {b}" + (f"  [{n}]" if n else "") for a, b, n in out["filas"]]
    if out["advertencias"]:
        l += ["", "ADVERTENCIAS"] + [f"  - {a}" for a in out["advertencias"]]
    return "\n".join(l + ["", AVISO])


def exportar_excel(c, ruta):
    from openpyxl import Workbook
    from openpyxl.styles import Font
    out = ejecutar(c)
    wb = Workbook()
    ws = wb.active
    ws.title = "Resultados"
    ws.append([f"Gas combustible — {c['nombre']}", f"v{__version__}", f"huella {huella(c)}"])
    ws["A1"].font = Font(bold=True)
    ws.append(["Parámetro", "Valor", "Nota"])
    for fila in out["filas"]:
        ws.append(list(fila))
    for a in out["advertencias"]:
        ws.append(["Advertencia", a, ""])
    ws.append(["", AVISO, ""])
    for col, w in zip("ABC", (46, 52, 60)):
        ws.column_dimensions[col].width = w
    h = wb.create_sheet("Composición")
    h.append(["Componente", "% mol"])
    for k, v in c["composicion"].items():
        h.append([k, v])
    if out["consumo"]:
        e, cs = out["consumo"], c["consumos"]
        h = wb.create_sheet("Consumos")
        h.append(["Fecha"] + e.unidades + ["Total (todas)"])
        for i, fch in enumerate(cs["fechas"]):
            h.append([fch] + [cs["series"][k][i] for k in e.unidades] + [e.total_por_dia[i]])
    wb.save(ruta)
    return ruta
