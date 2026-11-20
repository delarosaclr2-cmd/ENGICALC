"""Motor de cálculo de líneas de agua.

Método (Menon 2005, cap. 1; IAPWS-IF97):
- Propiedades del agua con IAPWS-IF97 región 1 (ρ) e IAPWS 2008 (μ) a la presión y temperatura de
  operación, o como líquido saturado a la temperatura (si no se conoce la presión).
- Velocidad v = Q/A con el diámetro interior real (ASME B36.10M).
- Pérdidas por Darcy-Weisbach, f de Colebrook-White (64/Re en laminar); accesorios con K de la tabla
  5.11 de Menon. Las alturas están en metros DEL AGUA que circula; ΔP = ρ·g·h con la ρ real.
- Succión: NPSH disponible = (p_superficie − p_v)/(ρ·g) + z − h_f (Hydraulic Institute / Menon cap. 1).
- Espesor por presión interna: ASME B31.1/B31.3 (ver nucleo/espesor.py).
"""
from __future__ import annotations

import hashlib
import json

from .nucleo import espesor as esp
from .nucleo import if97
from .nucleo import presion as pres
from .nucleo import seleccion as sel
from .nucleo import unidades as u
from .nucleo.hidraulica import factor_friccion
from .nucleo.liquido import G, tramo
from .nucleo.tubos import (RUGOSIDAD_ACERO_M, d_interior_m, espesor_nominal_in, nps_lista, od_in)

AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un "
         "ingeniero responsable ni constituyen una validación del proyecto.")


class ErrorEntrada(ValueError):
    pass


def huella(c: dict) -> str:
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _num(x, nombre):
    try:
        return float(x)
    except (TypeError, ValueError):
        raise ErrorEntrada(f"Dato numérico inválido: {nombre}")


def propiedades(c, patm):
    t_k = _num(c["temperatura_c"], "temperatura") + 273.15
    prop = c.get("propiedades", "IF97")
    if prop == "capturadas":
        rho, mu = _num(c["rho_kg_m3"], "densidad"), _num(c["mu_cp"], "viscosidad") / 1000
        return rho, mu, None, "capturadas por el usuario", if97.p_sat(t_k) if t_k <= 647 else None
    estado = c.get("estado", "presion")
    if estado == "saturado":
        e = if97.estado_sat(if97.p_sat(t_k), 0.0)
        ref = f"IAPWS-IF97: líquido saturado a {t_k-273.15:g} °C"
    else:
        p = u.presion_a_pa_abs(_num(c["presion"]["valor"], "presión"), c["presion"]["unidad"], patm)
        if p <= if97.p_sat(t_k):
            raise ErrorEntrada(f"A {t_k-273.15:g} °C el agua hierve por debajo de {if97.p_sat(t_k)/1000:.1f} kPa a: "
                               "la presión capturada no corresponde a líquido")
        e = if97.estado_pt(p, t_k)
        ref = f"IAPWS-IF97 región 1 a {p/1000:.1f} kPa a y {t_k-273.15:g} °C"
    return e.rho, e.mu, e, ref, if97.p_sat(t_k)


def calcular(c: dict) -> dict:
    patm = _num(c.get("p_atm_kpa", 101.325), "presión atmosférica") * 1000
    tub = c["tuberia"]
    try:
        d = _num(tub["d_interior_mm"], "Di") / 1000 if tub.get("d_interior_mm") else d_interior_m(tub["nps"], tub["cedula"])
    except KeyError as exc:
        raise ErrorEntrada(str(exc).strip("'\""))
    q = u.caudal_liq_a_m3s(_num(c["caudal"]["valor"], "caudal"), c["caudal"]["unidad"])
    if q <= 0:
        raise ErrorEntrada("El caudal debe ser positivo")
    try:
        rho, mu, est, ref_prop, pv = propiedades(c, patm)
    except ValueError as exc:
        raise ErrorEntrada(str(exc))
    eps = _num(c.get("rugosidad_mm", RUGOSIDAD_ACERO_M * 1000), "rugosidad") / 1000
    L = _num(c.get("longitud_m", 0), "longitud")
    dz = _num(c.get("dz_m", 0) or 0, "desnivel")
    try:
        t = tramo(q, rho, mu, d, tub.get("nps"), L, eps, c.get("accesorios", []), dz)
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(str(exc).strip("'\""))
    res = {"q": q, "rho": rho, "mu": mu, "estado": est, "ref_prop": ref_prop, "p_vapor": pv, "d": d, "L": L,
           "eps": eps, "dz": dz, "patm": patm, "tramo": t, "verificaciones": [], "advertencias": [],
           "npsh": None, "espesor": None}
    ver, adv = res["verificaciones"], res["advertencias"]
    if t["regimen"].startswith("crítico"):
        adv.append("Reynolds entre 2100 y 4000: zona crítica, el factor de fricción es incierto.")
    # Velocidad
    cv = c.get("criterio_velocidad") or {}
    vmin, vmax = cv.get("v_min_m_s"), cv.get("v_max_m_s")
    if vmax not in (None, ""):
        vmax = float(vmax)
        ver.append(("Velocidad ≤ máxima recomendada", f"{t['v']:.3f} m/s", f"≤ {vmax:g} m/s",
                    "CUMPLE" if t["v"] <= vmax else "NO CUMPLE", cv.get("fuente", "criterio del usuario")))
    if vmin not in (None, ""):
        vmin = float(vmin)
        if t["v"] < vmin:
            ver.append(("Velocidad ≥ mínima recomendada", f"{t['v']:.3f} m/s", f"≥ {vmin:g} m/s", "INFORMATIVO",
                        "Por debajo del intervalo: tubería holgada (no es un problema de seguridad)"))
    # NPSH
    n = c.get("npsh") or {}
    if c.get("servicio") == "succion":
        ps = n.get("p_superficie") or {}
        if ps.get("valor") not in (None, "") and n.get("nivel_m") not in (None, ""):
            psup = u.presion_a_pa_abs(_num(ps["valor"], "p superficie"), ps["unidad"], patm)
            if pv is None:
                raise ErrorEntrada("No se conoce la presión de vapor para el NPSH")
            z = _num(n["nivel_m"], "nivel")
            na = (psup - pv) / (rho * G) + z - t["h_friccion"]
            res["npsh"] = {"p_sup": psup, "z": z, "npsha": na, "h_vap": pv / (rho * G), "h_sup": psup / (rho * G)}
            nr = n.get("npshr_m")
            if nr not in (None, ""):
                req = float(nr) + float(n.get("margen_m") or 0)
                res["npsh"]["npshr"] = float(nr)
                res["npsh"]["requerido"] = req
                ver.append(("NPSH disponible ≥ NPSHr + margen", f"{na:.2f} m", f"≥ {req:.2f} m",
                            "CUMPLE" if na >= req else "NO CUMPLE", n.get("fuente", "NPSHr del fabricante")))
        elif t_sub(c) is not None and t_sub(c) < 25:
            adv.append("Succión con agua cerca de saturación sin datos de NPSH: capture el nivel del líquido sobre la "
                       "bomba y la presión en la superficie (en un deareador es la de saturación).")
    # Espesor
    try:
        r_esp, datos_esp = esp.desde_caso(c.get("espesor"), tub)
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(f"Espesor: {exc}")
    if r_esp:
        res["espesor"], res["datos_espesor"] = r_esp, datos_esp
        ver.append(esp.verificacion(r_esp))
        adv.extend(r_esp["avisos"])
    # Presión máxima admisible (código y Barlow) y barridos de velocidad
    res["presion"] = presion_maxima(c, tub, res)
    if res["presion"]:
        ver.extend(pres.verificaciones(res["presion"]))
        adv.extend(res["presion"]["avisos"])
    res.update(barridos(c, res))
    return res


def presion_maxima(c, tub, res):
    """Presión máxima admisible de la tubería. None si no hay datos de espesor o de material."""
    cfg = c.get("espesor") or {}
    geo = esp.geometria(cfg, tub, od_in, espesor_nominal_in)
    if not geo or not pres.hay_material(cfg):
        return None
    try:
        s_adm, _ = esp.resolver_s(cfg)
        return pres.desde_caso(cfg, geo[0], geo[1], s_adm, cfg.get("t_diseno_c"))
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(f"Presión máxima: {str(exc).strip(chr(39) + chr(34))}")


def barridos(c, res):
    """Velocidad por diámetro al caudal capturado, capacidad de la línea y curva v(Q)."""
    q, rho, mu, eps, L = res["q"], res["rho"], res["mu"], res["eps"], res["L"]
    cv = c.get("criterio_velocidad") or {}
    vmin, vmax = cv.get("v_min_m_s"), cv.get("v_max_m_s")
    tub = c["tuberia"]
    ced = str(tub.get("cedula") or "40")

    def calc(d):
        v = sel.velocidad(q, d)
        re = rho * v * d / mu
        f, _ = factor_friccion(re, eps, d)
        return {"v": v, "re": re, "f": f, "dp_pa": (f * L / d * rho * v ** 2 / 2) if L else None}

    cand = []
    for nps in nps_lista():
        try:
            cand.append((nps, ced, d_interior_m(nps, ced)))
        except KeyError:
            continue
    salida = {"curva": sel.curva(res["d"], q, vmin, vmax),
              "tabla_capacidad": sel.tabla_capacidad(res["d"], q, vmin, vmax,
                                                     conv=lambda x: u.m3s_a_liq(x, c["caudal"]["unidad"]),
                                                     unidad=c["caudal"]["unidad"]),
              "diametro_requerido_m": sel.diametro_requerido(q, float(vmax)) if vmax not in (None, "") else None}
    cand = sel.ventana(cand, q, vmin, vmax, tub.get("nps"))
    if cand:
        salida["tabla_diametros"] = sel.tabla_diametros(cand, calc, vmin, vmax, tub.get("nps"), L or None)
    return salida


def t_sub(c):
    """Subenfriamiento estimado (°C) respecto a 100 °C para avisar de succiones calientes."""
    try:
        return 100.0 - float(c["temperatura_c"])
    except (KeyError, TypeError, ValueError):
        return None


def perfil(res, n=30):
    """Presión relativa a la entrada a lo largo de la línea (fricción + accesorios repartidos + desnivel)."""
    t, L = res["tramo"], res["L"] or 1.0
    return [(L * i / n, -t["dp_total"] * i / n) for i in range(n + 1)]
