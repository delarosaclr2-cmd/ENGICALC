"""Espesor de pared por presión interna.

- ASME B31.3-2014 §304.1.2, ec. (3a): t = P·D / (2·(S·E·W + P·Y)); t_m = t + c (ec. 2).
  Válida para t < D/6 y P/(S·E) ≤ 0.385. El espesor nominal menos la tolerancia de fabricación
  debe ser ≥ t_m (§304.1.1).
- ASME B31.1 §104.1.2: la memoria original usa la misma forma, t_m = P·D/(2·(S·E + P·y)) + A
  (Menon 2005, ec. 4.53). El código B31.1 no se proporcionó: S, E, y y A se capturan y deben
  verificarse en la edición contractual.

Tabla A-1 de B31.3-2014, A106 Gr. B (sin costura, E = 1.00, tabla A-1B): S [ksi] por temperatura [°F].
"""
from __future__ import annotations

from .presion import (PSI, S_A106B_B313_KSI, _nota_dominio, fuera_de_dominio,  # noqa: F401
                      resolver_s, s_a106b_b313)                                # (API compartida)


def espesor_requerido(p_pa, od_m, s_pa, e=1.0, w=1.0, y=0.4, c_m=0.0):
    """(t presión, t_m) en m. P manométrica de diseño."""
    if p_pa < 0:
        raise ValueError("La presión de diseño (manométrica) no puede ser negativa")
    t = p_pa * od_m / (2.0 * (s_pa * e * w + p_pa * y))
    return t, t + c_m


def verificar(p_pa, od_m, t_nom_m, s_pa, e=1.0, w=1.0, y=0.4, c_m=0.0, tolerancia=0.125):
    """Espesor requerido y su comparación con el disponible.

    `cumple` es None cuando la ec. (3a) queda fuera de su dominio (B31.3 §304.1.2(b)): el espesor
    requerido se calculó con una fórmula que el código no autoriza ahí, así que la comparación no
    es una comprobación. Los motivos quedan en `fuera_dominio`.
    """
    if c_m < 0:
        raise ValueError("El sobreespesor c no puede ser negativo")
    if not 0.0 <= tolerancia < 1.0:
        raise ValueError("La tolerancia de fabricación debe estar entre 0 % y 100 %")
    t, tm = espesor_requerido(p_pa, od_m, s_pa, e, w, y, c_m)
    t_min = t_nom_m * (1.0 - tolerancia)
    motivos = fuera_de_dominio(t, od_m, p_pa, s_pa, e)
    avisos = [f"Espesor por presión: {_nota_dominio(motivos)}."] if motivos else []
    return {"t_presion_m": t, "t_m_m": tm, "t_nominal_m": t_nom_m, "t_disponible_m": t_min,
            "cumple": None if motivos else tm <= t_min, "fuera_dominio": motivos,
            "margen": None if motivos else (t_min / tm if tm > 0 else float("inf")),
            "avisos": avisos}


_S_UNID = {"psi": PSI, "ksi": 1000 * PSI, "MPa": 1e6, "kgf/cm²": 98066.5}
_P_UNID = {"psig": PSI, "kPa g": 1000.0, "bar g": 1e5, "kgf/cm² g": 98066.5, "MPa g": 1e6}
PULG = 0.0254


def geometria(cfg: dict, tub: dict, od_in, espesor_nominal_in):
    """(OD, espesor nominal) en m, de la tabla de tubos o capturados. None si no se puede resolver."""
    cfg = cfg or {}
    if tub.get("nps"):
        od = od_in(tub["nps"]) * PULG
        tn = (cfg.get("t_nominal_mm") / 1000) if cfg.get("t_nominal_mm") else \
            espesor_nominal_in(tub["nps"], tub["cedula"]) * PULG
        return od, tn
    if cfg.get("od_mm") and cfg.get("t_nominal_mm"):
        return cfg["od_mm"] / 1000, cfg["t_nominal_mm"] / 1000
    return None


def desde_caso(cfg: dict, tub: dict):
    """Evalúa el espesor con la configuración del caso. Devuelve (resultado, filas de datos) o (None, [])."""
    if not cfg or cfg.get("p_diseno", {}).get("valor") in (None, ""):
        return None, []
    from .tubos import espesor_nominal_in, od_in
    p = float(cfg["p_diseno"]["valor"]) * _P_UNID[cfg["p_diseno"]["unidad"]]
    codigo = cfg.get("codigo", "B31.3")
    s, fuente_s = resolver_s(cfg)
    if tub.get("nps"):
        od = od_in(tub["nps"]) * PULG
        tn = (cfg.get("t_nominal_mm") / 1000) if cfg.get("t_nominal_mm") else espesor_nominal_in(tub["nps"], tub["cedula"]) * PULG
    else:
        od, tn = cfg["od_mm"] / 1000, cfg["t_nominal_mm"] / 1000
    from .presion import sobreespesor
    c, origen_c = sobreespesor(cfg)
    r = verificar(p, od, tn, s, cfg.get("e", 1.0), cfg.get("w", 1.0), cfg.get("y", 0.4), c,
                  cfg.get("tolerancia_pct", 12.5) / 100)
    r.update(codigo=codigo, p_pa=p, s_pa=s, od_m=od, c_m=c, fuente_s=fuente_s,
             e=cfg.get("e", 1.0), w=cfg.get("w", 1.0), y=cfg.get("y", 0.4), tol=cfg.get("tolerancia_pct", 12.5))
    datos = [("Espesor: código", codigo, "B31.1 no proporcionado: S, E, y, A del usuario" if codigo == "B31.1" else
              "ASME B31.3-2014 §304.1.2"),
             ("Presión de diseño", f"{p/PSI:.2f} psig ({p/1e5:.3f} bar g)", ""),
             ("Esfuerzo admisible S", f"{s/PSI:,.0f} psi ({s/1e6:.1f} MPa)", fuente_s),
             ("E · W · Y", f"{r['e']:g} · {r['w']:g} · {r['y']:g}", ""),
             ("Sobreespesor c (corrosión + mecánico)", f"{c*1000:.3f} mm ({c/PULG:.4f} in)", origen_c),
             ("Tolerancia de fabricación", f"{r['tol']:g} %", "ASTM A106 / A530")]
    return r, datos


def filas_resultado(r):
    mm = lambda m: f"{m*1000:.3f} mm ({m/PULG:.4f} in)"
    return [("Espesor por presión t", mm(r["t_presion_m"]), "t = P·D/(2(S·E·W + P·Y))"),
            ("Espesor mínimo requerido t_m", mm(r["t_m_m"]), "t_m = t + c"),
            ("Espesor nominal", mm(r["t_nominal_m"]), "ASME B36.10M"),
            ("Nominal menos tolerancia", mm(r["t_disponible_m"]), f"−{r['tol']:g} %")]


def verificacion(r):
    motivos = r.get("fuera_dominio") or []
    return ("Espesor de pared (t_m ≤ nominal − tolerancia)",
            f"{r['t_m_m']*1000:.3f} mm", f"≤ {r['t_disponible_m']*1000:.3f} mm",
            "NO EVALUABLE" if motivos else ("CUMPLE" if r["cumple"] else "NO CUMPLE"),
            f"{r['codigo']} — {_nota_dominio(motivos)}" if motivos else r["codigo"])
