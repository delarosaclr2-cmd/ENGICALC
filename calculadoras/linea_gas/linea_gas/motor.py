"""Caída de presión de un gas (aire comprimido, gas natural) en una línea de acero.

Método principal (Menon 2005, cap. 5; flujo isotérmico compresible, Darcy):

    ṁ = Q_ref·P_ref·M / (R_u·T_ref)                          caudal a condición de referencia -> masa
    ρ = P·M / (Z·R_u·T);   v = ṁ/(ρ·A);   Re = ρ·v·D/μ
    1/√f = −2·log10(ε/(3.7·D) + 2.51/(Re·√f))               Colebrook-White (Swamee-Jain como inicio)
    P1² − P2² = (G²·Z·R_u·T/M)·[f·L/D + ΣK + 2·ln(P1/P2)]    G = ṁ/A

Los accesorios entran como ΣK (Menon tabla 5.11, K = f_T·L/D) dentro de la misma ecuación; la
contribución de accesorios se informa además como ΔP = ΣK·ρ·v²/2, en Pa (densidad DEL GAS).

Comparación (solo aire): fórmula de Fritzsche, Menon ec. 5.34 (USCS, Qs en SCFM).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from .datos import GASES, R_U, REFERENCIAS, RUGOSIDAD_ACERO_M, k_menon, mu_sutherland_aire


class ErrorEntrada(ValueError):
    pass


@dataclass
class Accesorio:
    tipo: str
    cantidad: int = 1
    k: Optional[float] = None      # si es None se toma de Menon tabla 5.11 con el NPS de la línea


@dataclass
class Entradas:
    nombre: str
    gas: str                       # clave de GASES
    q_ref_m3s: float
    ref: str                       # clave de REFERENCIAS
    p_entrada_pa: float            # absoluta
    t_k: float
    longitud_m: float
    d_interior_m: float
    nps: Optional[str] = None
    rugosidad_m: float = RUGOSIDAD_ACERO_M
    accesorios: List[Accesorio] = field(default_factory=list)
    z: float = 1.0
    mu_pa_s: Optional[float] = None
    v_max_m_s: Optional[float] = None        # criterio del proyecto (opcional)
    dp_max_pa: Optional[float] = None        # criterio del proyecto (opcional)
    p_min_salida_pa: Optional[float] = None  # criterio del proyecto (opcional)


@dataclass
class Resultados:
    mdot_kg_s: float
    q_actual_m3h: float
    rho_entrada: float
    v_entrada: float
    mu: float
    re: float
    f: float
    f_swamee_jain: float
    k_total: float
    detalle_k: list
    dp_total_pa: float
    dp_tubo_pa: float
    dp_accesorios_pa: float
    p_salida_pa: float
    v_salida: float
    mach: float
    dp_fritzsche_pa: Optional[float] = None
    verificaciones: list = field(default_factory=list)
    advertencias: list = field(default_factory=list)


def swamee_jain(re, eps, d):
    return 0.25 / math.log10(eps / (3.7 * d) + 5.74 / re ** 0.9) ** 2


def colebrook(re, eps, d):
    if re < 2000:
        return 64.0 / re
    f = swamee_jain(re, eps, d)
    for _ in range(100):
        nuevo = (-2.0 * math.log10(eps / (3.7 * d) + 2.51 / (re * math.sqrt(f)))) ** -2
        if abs(nuevo - f) < 1e-14:
            break
        f = nuevo
    return f


def fritzsche_dp_psi(qs_scfm, l_ft, d_in, p_media_psia, t_rankine, ps_psia=14.7, ts_rankine=520.0):
    """Menon (2005) ec. 5.34: ΔP [psi] = 9.8265e-4·T·L/(P·d^5) · (Ps·Qs/Ts)^1.857."""
    return 9.8265e-4 * t_rankine * l_ft / (p_media_psia * d_in ** 5) * (ps_psia * qs_scfm / ts_rankine) ** 1.857


def _validar(e: Entradas):
    for nombre, v in (("caudal", e.q_ref_m3s), ("presión de entrada", e.p_entrada_pa),
                      ("temperatura", e.t_k), ("longitud", e.longitud_m), ("diámetro interior", e.d_interior_m),
                      ("Z", e.z), ("rugosidad", e.rugosidad_m + 1e-30)):
        if v is None or not math.isfinite(v) or v <= 0:
            raise ErrorEntrada(f"{nombre}: debe ser un número positivo")
    if e.gas not in GASES:
        raise ErrorEntrada(f"Gas desconocido: {e.gas}")
    if e.ref not in REFERENCIAS:
        raise ErrorEntrada(f"Condición de referencia desconocida: {e.ref}")
    if e.d_interior_m > 2.0:
        raise ErrorEntrada("Diámetro interior > 2 m: ¿se capturó en mm?")
    if e.p_entrada_pa < 50_000:
        raise ErrorEntrada("Presión de entrada < 50 kPa absolutos: ¿se capturó manométrica como absoluta?")
    for a in e.accesorios:
        if a.cantidad < 0:
            raise ErrorEntrada("Cantidad de accesorios negativa")
        if a.k is None and not e.nps:
            raise ErrorEntrada(f"Accesorio {a.tipo}: indique NPS de la línea o K")


def calcular(e: Entradas) -> Resultados:
    _validar(e)
    g = GASES[e.gas]
    M = g["M"]
    p_ref, t_ref, _ = REFERENCIAS[e.ref]
    adv = []

    mdot = e.q_ref_m3s * p_ref * M / (R_U * t_ref)
    A = math.pi * e.d_interior_m ** 2 / 4.0
    rho1 = e.p_entrada_pa * M / (e.z * R_U * e.t_k)
    v1 = mdot / (rho1 * A)
    mu = e.mu_pa_s if e.mu_pa_s is not None else (mu_sutherland_aire(e.t_k) if g["mu"] is None else g["mu"])
    re = rho1 * v1 * e.d_interior_m / mu
    f = colebrook(re, e.rugosidad_m, e.d_interior_m)
    fsj = swamee_jain(re, e.rugosidad_m, e.d_interior_m) if re >= 2000 else f
    if 2000 <= re < 4000:
        adv.append("Régimen de transición (2000 ≤ Re < 4000): factor de fricción incierto")

    detalle, k_tot = [], 0.0
    for a in e.accesorios:
        k = a.k if a.k is not None else k_menon(a.tipo, e.nps)
        detalle.append((a.tipo, a.cantidad, k, a.cantidad * k))
        k_tot += a.cantidad * k

    G = mdot / A
    c = G ** 2 * e.z * R_U * e.t_k / M
    resist = f * e.longitud_m / e.d_interior_m + k_tot
    p1 = e.p_entrada_pa
    p2 = p1
    for _ in range(200):
        arg = p1 ** 2 - c * (resist + 2.0 * math.log(p1 / p2))
        if arg <= 0:
            raise ErrorEntrada("La línea no puede conducir ese flujo con esa presión de entrada "
                               "(presión de salida nula: flujo crítico o diámetro insuficiente)")
        nuevo = math.sqrt(arg)
        if abs(nuevo - p2) < 1e-9:
            p2 = nuevo
            break
        p2 = nuevo
    dp_total = p1 - p2
    # Reparto informativo (ponderado por resistencias)
    dp_acc = dp_total * k_tot / resist if resist > 0 else 0.0
    rho2 = p2 * M / (e.z * R_U * e.t_k)
    v2 = mdot / (rho2 * A)
    a_son = math.sqrt(g["k"] * e.z * R_U * e.t_k / M)
    mach = v2 / a_son
    if mach > 0.3:
        adv.append(f"Mach a la salida = {mach:.2f} > 0.3: revisar con flujo compresible no isotérmico")
    if dp_total / p1 > 0.4:
        adv.append("ΔP > 40 % de la presión de entrada: el modelo isotérmico pierde exactitud")

    dp_fr = None
    if e.gas == "aire":
        qs_scfm = mdot / (101_325.0 * M / (R_U * 288.7056)) * 35.3146667 * 60.0
        l_eq = e.longitud_m + k_tot / f * e.d_interior_m
        dp_fr = fritzsche_dp_psi(qs_scfm, l_eq / 0.3048, e.d_interior_m / 0.0254,
                                 (p1 + p2) / 2 / 6894.757293168, e.t_k * 1.8) * 6894.757293168

    r = Resultados(mdot_kg_s=mdot, q_actual_m3h=mdot / rho1 * 3600, rho_entrada=rho1, v_entrada=v1, mu=mu,
                   re=re, f=f, f_swamee_jain=fsj, k_total=k_tot, detalle_k=detalle, dp_total_pa=dp_total,
                   dp_tubo_pa=dp_total - dp_acc, dp_accesorios_pa=dp_acc, p_salida_pa=p2, v_salida=v2,
                   mach=mach, dp_fritzsche_pa=dp_fr, advertencias=adv)

    # Verificaciones contra criterios del proyecto (si se capturaron)
    if e.v_max_m_s is not None:
        r.verificaciones.append(("Velocidad máxima", f"{v2:.2f} m/s", f"≤ {e.v_max_m_s:g} m/s",
                                 "CUMPLE" if v2 <= e.v_max_m_s else "NO CUMPLE"))
    if e.dp_max_pa is not None:
        r.verificaciones.append(("Caída de presión", f"{dp_total/1000:.3f} kPa", f"≤ {e.dp_max_pa/1000:g} kPa",
                                 "CUMPLE" if dp_total <= e.dp_max_pa else "NO CUMPLE"))
    if e.p_min_salida_pa is not None:
        r.verificaciones.append(("Presión a la salida", f"{p2/1000:.2f} kPa a", f"≥ {e.p_min_salida_pa/1000:g} kPa a",
                                 "CUMPLE" if p2 >= e.p_min_salida_pa else "NO CUMPLE"))
    return r


def perfil_presion(e: Entradas, r: Resultados, n: int = 40):
    """Presión a lo largo de la línea, repartiendo ΣK uniformemente en la longitud (para el esquema).
    Usa la misma ecuación isotérmica de calcular(); el último punto coincide con r.p_salida_pa."""
    M = GASES[e.gas]["M"]
    A = math.pi * e.d_interior_m ** 2 / 4.0
    G = r.mdot_kg_s / A
    c = G ** 2 * e.z * R_U * e.t_k / M
    p1 = e.p_entrada_pa
    puntos = [(0.0, p1)]
    for i in range(1, n + 1):
        x = e.longitud_m * i / n
        resist = r.f * x / e.d_interior_m + r.k_total * x / e.longitud_m
        p2 = p1
        for _ in range(200):
            nuevo = math.sqrt(max(p1 ** 2 - c * (resist + 2.0 * math.log(p1 / p2)), 1.0))
            if abs(nuevo - p2) < 1e-9:
                break
            p2 = nuevo
        puntos.append((x, p2))
    return puntos
