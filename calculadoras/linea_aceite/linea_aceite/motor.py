"""Motor de cálculo de líneas de aceite.

Método (Menon 2005, cap. 6):
- Viscosidad cinemática a la temperatura de operación: ASTM D341 (ecs. 6.13–6.16) ajustada con dos
  puntos (T, ν) de la hoja técnica del aceite, o capturada directamente.
- Densidad a la temperatura de operación: capturada, o ρ(T) = ρ_ref·[1 − α·(T − T_ref)] con α del usuario.
- Reynolds: Re = v·D/ν (equivale a Menon ec. 6.38: R = 353 678·Q/(ν·D), Q m³/h, ν cSt, D mm).
- Darcy (Menon ec. 6.49: h = 50.94·f·L·v²/D, h en m DEL ACEITE); ΔP = ρ·g·h.
  Laminar (Re ≤ 2100): f = 64/Re y accesorios por longitud equivalente K = f·L/D.
- Espesor: ASME B31.3-2014 §304.1.2 (Tabla A-1 para A106 B) o S capturado.
"""
from __future__ import annotations

import hashlib
import json

from .nucleo import aceite as ac
from .nucleo import espesor as esp
from .nucleo import presion as pres
from .nucleo import seleccion as sel
from .nucleo import unidades as u
from .nucleo.hidraulica import factor_friccion
from .nucleo.liquido import G, tramo
from .nucleo.tubos import (RUGOSIDAD_ACERO_M, d_interior_m, espesor_nominal_in, nps_lista, od_in)

AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un "
         "ingeniero responsable ni constituyen una validación del proyecto.")
# ISO 3448: viscosidad cinemática a 40 °C de cada grado ISO VG, ±10 % del punto medio
ISO_VG = [2, 3, 5, 7, 10, 15, 22, 32, 46, 68, 100, 150, 220, 320, 460, 680, 1000, 1500]


class ErrorEntrada(ValueError):
    pass


def huella(c: dict) -> str:
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _num(x, nombre):
    try:
        return float(x)
    except (TypeError, ValueError):
        raise ErrorEntrada(f"Dato numérico inválido: {nombre}")


def grado_iso(nu40):
    for g in ISO_VG:
        if 0.9 * g <= nu40 <= 1.1 * g:
            return f"ISO VG {g}"
    return None


def viscosidad(c, t_c):
    vc = c["viscosidad"]
    if vc.get("modo", "dos_puntos") == "directa":
        nu = _num(vc["nu_cst"], "viscosidad")
        if nu <= 0:
            raise ErrorEntrada("La viscosidad debe ser positiva")
        return nu, None, f"capturada: {nu:g} cSt a la temperatura de operación"
    t1, n1 = _num(vc["t1_c"], "T1"), _num(vc["nu1_cst"], "ν1")
    t2, n2 = _num(vc["t2_c"], "T2"), _num(vc["nu2_cst"], "ν2")
    try:
        a, b = ac.ajustar_walther(t1 + 273.15, n1, t2 + 273.15, n2)
    except ValueError as exc:
        raise ErrorEntrada(str(exc))
    if b <= 0:
        raise ErrorEntrada("Los dos puntos dan una viscosidad que sube con la temperatura: revise los datos")
    nu = ac.viscosidad_cst(t_c + 273.15, a, b)
    return nu, (a, b), (f"ASTM D341 con {n1:g} cSt a {t1:g} °C y {n2:g} cSt a {t2:g} °C "
                        f"(A = {a:.4f}, B = {b:.4f})")


def calcular(c: dict) -> dict:
    tub = c["tuberia"]
    try:
        d = _num(tub["d_interior_mm"], "Di") / 1000 if tub.get("d_interior_mm") else d_interior_m(tub["nps"], tub["cedula"])
    except KeyError as exc:
        raise ErrorEntrada(str(exc).strip("'\""))
    q = u.caudal_liq_a_m3s(_num(c["caudal"]["valor"], "caudal"), c["caudal"]["unidad"])
    if q <= 0:
        raise ErrorEntrada("El caudal debe ser positivo")
    t_c = _num(c["temperatura_c"], "temperatura")
    nu, ab, ref_nu = viscosidad(c, t_c)
    den = c["densidad"]
    rho = _num(den["rho_kg_m3"], "densidad")
    ref_rho = den.get("fuente", "capturada")
    if den.get("t_ref_c") not in (None, "") and den.get("alfa_1_c") not in (None, ""):
        rho = rho * (1 - _num(den["alfa_1_c"], "α") * (t_c - _num(den["t_ref_c"], "T ref")))
        ref_rho += f"; corregida a {t_c:g} °C con α = {den['alfa_1_c']}"
    if not 500 < rho < 1200:
        raise ErrorEntrada("Densidad fuera del intervalo de aceites (500–1200 kg/m³)")
    mu = nu * 1e-6 * rho
    eps = _num(c.get("rugosidad_mm", RUGOSIDAD_ACERO_M * 1000), "rugosidad") / 1000
    L = _num(c.get("longitud_m", 0), "longitud")
    dz = _num(c.get("dz_m", 0) or 0, "desnivel")
    try:
        t = tramo(q, rho, mu, d, tub.get("nps"), L, eps, c.get("accesorios", []), dz)
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(str(exc).strip("'\""))
    res = {"q": q, "rho": rho, "nu": nu, "mu": mu, "ab": ab, "ref_nu": ref_nu, "ref_rho": ref_rho, "d": d, "L": L,
           "eps": eps, "dz": dz, "tramo": t, "t_c": t_c, "verificaciones": [], "advertencias": [], "espesor": None,
           "nu40": None, "iso": None}
    ver, adv = res["verificaciones"], res["advertencias"]
    if ab:
        res["nu40"] = ac.viscosidad_cst(313.15, *ab)
        res["iso"] = grado_iso(res["nu40"])
        if res["iso"] is None:
            adv.append(f"La viscosidad a 40 °C que dan los dos puntos ({res['nu40']:.1f} cSt) no corresponde a ningún "
                       "grado ISO VG (ISO 3448, ±10 %): confirme los datos con la hoja técnica del aceite.")
    if t["regimen"].startswith("crítico"):
        adv.append("Reynolds entre 2100 y 4000: zona crítica, el factor de fricción es incierto.")
    if t["laminar"] and c.get("accesorios"):
        adv.append("Flujo laminar: los accesorios se calculan como longitud equivalente con f = 64/Re.")
    cv = c.get("criterio_velocidad") or {}
    vmin, vmax = cv.get("v_min_m_s"), cv.get("v_max_m_s")
    if vmax not in (None, ""):
        ver.append(("Velocidad ≤ máxima recomendada", f"{t['v']:.3f} m/s", f"≤ {float(vmax):g} m/s",
                    "CUMPLE" if t["v"] <= float(vmax) else "NO CUMPLE", cv.get("fuente", "criterio del usuario")))
    if vmin not in (None, "") and t["v"] < float(vmin):
        ver.append(("Velocidad ≥ mínima recomendada", f"{t['v']:.3f} m/s", f"≥ {float(vmin):g} m/s", "INFORMATIVO",
                    "Por debajo del intervalo (en un drenaje por gravedad la velocidad baja es lo esperado)"))
    dpmax = c.get("dp_max_kpa")
    if dpmax not in (None, ""):
        ver.append(("Caída de presión ≤ admisible", f"{t['dp_total']/1000:.2f} kPa", f"≤ {float(dpmax):g} kPa",
                    "CUMPLE" if t["dp_total"] / 1000 <= float(dpmax) else "NO CUMPLE", c.get("fuente_dp_max", "criterio")))
    try:
        r_esp, datos_esp = esp.desde_caso(c.get("espesor"), tub)
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(f"Espesor: {exc}")
    if r_esp:
        res["espesor"], res["datos_espesor"] = r_esp, datos_esp
        ver.append(esp.verificacion(r_esp))
        adv.extend(r_esp["avisos"])
    # Presión máxima admisible y barridos de velocidad
    res["presion"] = presion_maxima(c, tub)
    if res["presion"]:
        ver.extend(pres.verificaciones(res["presion"]))
        adv.extend(res["presion"]["avisos"])
    res.update(barridos(c, res))
    return res


def presion_maxima(c, tub):
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
        f, reg = factor_friccion(re, eps, d)
        return {"v": v, "re": re, "f": f, "dp_pa": (f * L / d * rho * v ** 2 / 2) if L else None,
                "nota": None if not reg.startswith("crítico") else "zona crítica"}

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
