"""Resistencia de diseño de vigas de acero: AISC 360-22 (LRFD) y NTC-DCEA de la Ciudad de México.

Unidades SI coherentes: N, m, Pa. Todas las funciones son puras (sin interfaz).

AISC 360-22 (Specification for Structural Steel Buildings, público en aisc.org):
- Capítulo F: F1 (Cb), F2 (I compactas: fluencia y pandeo lateral-torsional), F3 (I con patines no compactos o
  esbeltos y alma compacta), F8 (HSS redondo), F11 (barras rectangulares y redondas).
- Capítulo G: G2.1 (almas de perfiles I sin atiesadores), G5 (HSS redondo).
- φb = 0.90, φv = 0.90 (1.00 para almas de perfiles I laminados con h/tw ≤ 2.24·√(E/Fy)).
Validado contra «AISC Design Examples v16.0» F.1-1B, F.1-2B, F.1-3B, F.3B y G.1B (ver tests/test_acero.py).

NTC-DCEA (Normas Técnicas Complementarias para Diseño y Construcción de Estructuras de Acero, CDMX), texto
publicado con comentarios en la Gaceta Oficial (2020, edición 2017):
- 6.2.1 Cb por el método de los cuatro momentos (misma ecuación que AISC F1-1).
- 6.3.1 Fluencia: Mn = Zx·Fy;  6.3.2: Me = (Cb·π/L)·√(E·Iy·G·J + (π·E/L)²·Iy·Ca);
  si Me > (2/3)·Mp: MR = 1.15·FR·Mp·(1 − 0.28·Mp/Me) ≤ FR·Mp;  si Me ≤ (2/3)·Mp: MR = FR·Me.  FR = 0.9.
- 7.2: Vn = 0.6·Fy·Aa·Cv con Aa = h·ta; Cv y kv según 7.2.2 a 7.2.5.
La edición 2023 (Gaceta Oficial, 6/11/2023) no estuvo disponible para esta revisión: verifique que estas
expresiones sigan vigentes. Patines no compactos (6.4.3) no se implementan con NTC: se informa AISC F3.
"""
from __future__ import annotations

import math

KSI = 6.894757293168e6           # Pa
E_AISC = 29000 * KSI             # 199 948 MPa (AISC 360-22, notación)
G_AISC = 11200 * KSI             # 77 221 MPa
E_NTC = 200000e6                 # NTC-DCEA, notación
G_NTC = 77200e6
PHI_B = 0.90
PHI_V = 0.90
FR_NTC = 0.90


# --------------------------------------------------------------------------- propiedades
def propiedades_i(d: float, bf: float, tf: float, tw: float) -> dict:
    """Perfil I de doble simetría formado por placas (sin filetes). Unidades: m, m², m³, m⁴, m⁶."""
    if not (d > 2 * tf > 0 and bf > tw > 0):
        raise ValueError("Dimensiones de la I incongruentes (d > 2·tf, bf > tw).")
    h = d - 2 * tf                       # altura libre del alma (sin filetes)
    ho = d - tf                          # distancia entre centroides de patines
    area = 2 * bf * tf + h * tw
    ix = (bf * d ** 3 - (bf - tw) * h ** 3) / 12
    sx = ix / (d / 2)
    zx = bf * tf * ho + tw * h ** 2 / 4
    iy = 2 * tf * bf ** 3 / 12 + h * tw ** 3 / 12
    j = (2 * bf * tf ** 3 + ho * tw ** 3) / 3
    cw = iy * ho ** 2 / 4
    return completar_i({"d": d, "bf": bf, "tf": tf, "tw": tw, "h": h, "ho": ho, "A": area, "Ix": ix, "Sx": sx,
                        "Zx": zx, "Iy": iy, "J": j, "Cw": cw})


def completar_i(p: dict) -> dict:
    """Agrega ry y rts a un diccionario de propiedades de un perfil I."""
    p = dict(p)
    p["ry"] = math.sqrt(p["Iy"] / p["A"])
    p["rts"] = math.sqrt(math.sqrt(p["Iy"] * p["Cw"]) / p["Sx"])
    return p


# --------------------------------------------------------------------------- Cb
def cb_aisc(m_max: float, m_a: float, m_b: float, m_c: float) -> float:
    """AISC 360-22 ec. F1-1 (= NTC-DCEA ec. 6.2.1). Momentos en valor absoluto en el tramo no soportado."""
    if m_max <= 0:
        return 1.0
    return 12.5 * m_max / (2.5 * m_max + 3 * m_a + 4 * m_b + 3 * m_c)


# --------------------------------------------------------------------------- AISC 360-22: perfiles I
def clasificar_i(p: dict, fy: float, e: float = E_AISC) -> dict:
    """Esbeltez de patín (bf/2tf) y alma (h/tw) con los límites de la Tabla B4.1b (casos 10 y 15)."""
    lam_f = p["bf"] / (2 * p["tf"])
    lam_w = p["h"] / p["tw"]
    lpf, lrf = 0.38 * math.sqrt(e / fy), 1.0 * math.sqrt(e / fy)
    lpw, lrw = 3.76 * math.sqrt(e / fy), 5.70 * math.sqrt(e / fy)
    patin = "compacto" if lam_f <= lpf else ("no compacto" if lam_f <= lrf else "esbelto")
    alma = "compacta" if lam_w <= lpw else ("no compacta" if lam_w <= lrw else "esbelta")
    return {"lam_f": lam_f, "lpf": lpf, "lrf": lrf, "lam_w": lam_w, "lpw": lpw, "lrw": lrw,
            "patin": patin, "alma": alma}


def aisc_flexion_i(p: dict, fy: float, lb: float, cb: float, e: float = E_AISC) -> dict:
    """Mn [N·m] de un perfil I de doble simetría con alma compacta (AISC 360-22 F2 y F3).

    lb = 0 significa soporte lateral continuo del patín comprimido.
    """
    cl = clasificar_i(p, fy, e)
    if cl["alma"] != "compacta":
        raise ValueError("Alma no compacta o esbelta (h/tw > 3.76·√(E/Fy)): requiere AISC F4/F5, no implementado.")
    mp = fy * p["Zx"]
    lp = 1.76 * p["ry"] * math.sqrt(e / fy)
    jc_sho = p["J"] * 1.0 / (p["Sx"] * p["ho"])  # c = 1 para I de doble simetría
    lr = 1.95 * p["rts"] * e / (0.7 * fy) * math.sqrt(jc_sho + math.sqrt(jc_sho ** 2 + 6.76 * (0.7 * fy / e) ** 2))
    # F2: pandeo lateral-torsional
    fcr = None
    if lb <= lp:
        m_ltb, zona = mp, "fluencia (Lb ≤ Lp)"
    elif lb <= lr:
        m_ltb = min(cb * (mp - (mp - 0.7 * fy * p["Sx"]) * (lb - lp) / (lr - lp)), mp)
        zona = "pandeo lateral-torsional inelástico (Lp < Lb ≤ Lr)"
    else:
        relacion = lb / p["rts"]
        fcr = cb * math.pi ** 2 * e / relacion ** 2 * math.sqrt(1 + 0.078 * jc_sho * relacion ** 2)
        m_ltb, zona = min(fcr * p["Sx"], mp), "pandeo lateral-torsional elástico (Lb > Lr)"
    # F3: pandeo local del patín comprimido
    m_flb = mp
    if cl["patin"] == "no compacto":
        m_flb = mp - (mp - 0.7 * fy * p["Sx"]) * (cl["lam_f"] - cl["lpf"]) / (cl["lrf"] - cl["lpf"])
    elif cl["patin"] == "esbelto":
        kc = min(max(4 / math.sqrt(cl["lam_w"]), 0.35), 0.76)
        m_flb = 0.9 * e * kc * p["Sx"] / cl["lam_f"] ** 2
    mn = min(m_ltb, m_flb)
    controla = zona if m_ltb <= m_flb else f"pandeo local del patín ({cl['patin']})"
    return {"Mn": mn, "phiMn": PHI_B * mn, "Mp": mp, "Lp": lp, "Lr": lr, "Fcr": fcr, "controla": controla,
            "clasificacion": cl}


def aisc_cortante_i(p: dict, fy: float, laminado: bool, e: float = E_AISC) -> dict:
    """AISC 360-22 G2.1, almas sin atiesadores transversales (kv = 5.34). Aw = d·tw."""
    h_tw = p["h"] / p["tw"]
    aw = p["d"] * p["tw"]
    if laminado and h_tw <= 2.24 * math.sqrt(e / fy):
        cv1, phi = 1.0, 1.00
    else:
        kv = 5.34
        lim = 1.10 * math.sqrt(kv * e / fy)
        cv1, phi = (1.0 if h_tw <= lim else lim / h_tw), PHI_V
    vn = 0.6 * fy * aw * cv1
    return {"Vn": vn, "phiVn": phi * vn, "phi": phi, "Cv1": cv1, "Aw": aw, "h_tw": h_tw}


# --------------------------------------------------------------------------- AISC 360-22: otras secciones
def aisc_flexion_rect(fy: float, b: float, d: float, lb: float, cb: float, e: float = E_AISC) -> dict:
    """Barra rectangular maciza flexionada alrededor de su eje mayor (F11). b = ancho, d = peralte (d ≥ b)."""
    sx, zx = b * d ** 2 / 6, b * d ** 2 / 4
    my, mp = fy * sx, min(fy * zx, 1.6 * fy * sx)
    if lb <= 0 or lb * d / b ** 2 <= 0.08 * e / fy:
        mn, controla = mp, "fluencia"
    elif lb * d / b ** 2 <= 1.9 * e / fy:
        mn = min(cb * (1.52 - 0.274 * (lb * d / b ** 2) * fy / e) * my, mp)
        controla = "pandeo lateral-torsional inelástico"
    else:
        fcr = 1.9 * e * cb / (lb * d / b ** 2)
        mn, controla = min(fcr * sx, mp), "pandeo lateral-torsional elástico"
    return {"Mn": mn, "phiMn": PHI_B * mn, "Mp": mp, "controla": controla}


def aisc_flexion_redonda(fy: float, diametro: float) -> dict:
    """Barra redonda maciza (F11): Mn = Mp = Fy·Z ≤ 1.6·Fy·S; no hay pandeo lateral-torsional."""
    s, z = math.pi * diametro ** 3 / 32, diametro ** 3 / 6
    mn = min(fy * z, 1.6 * fy * s)
    return {"Mn": mn, "phiMn": PHI_B * mn, "Mp": mn, "controla": "fluencia"}


def aisc_flexion_tubo(fy: float, diametro: float, t: float, e: float = E_AISC) -> dict:
    """HSS redondo (F8). D/t ≤ 0.45·E/Fy."""
    dt = diametro / t
    if dt > 0.45 * e / fy:
        raise ValueError("D/t > 0.45·E/Fy: fuera del alcance de AISC 360-22 F8.")
    di = diametro - 2 * t
    s = math.pi * (diametro ** 4 - di ** 4) / (32 * diametro)
    z = (diametro ** 3 - di ** 3) / 6
    if dt <= 0.07 * e / fy:
        mn, controla = fy * z, "fluencia (sección compacta)"
    elif dt <= 0.31 * e / fy:
        mn, controla = (0.021 * e / dt + fy) * s, "pandeo local (sección no compacta)"
    else:
        mn, controla = 0.33 * e / dt * s, "pandeo local (pared esbelta)"
    return {"Mn": mn, "phiMn": PHI_B * mn, "Mp": fy * z, "controla": controla}


def aisc_cortante_tubo(fy: float, diametro: float, t: float, lv: float, e: float = E_AISC) -> dict:
    """HSS redondo (G5): Vn = Fcr·Ag/2; Lv = distancia de cortante máximo a cortante nulo."""
    dt = diametro / t
    ag = math.pi * (diametro ** 2 - (diametro - 2 * t) ** 2) / 4
    fcr1 = 1.60 * e / (math.sqrt(max(lv, 1e-9) / diametro) * dt ** 1.25)
    fcr2 = 0.78 * e / dt ** 1.5
    fcr = min(max(fcr1, fcr2), 0.6 * fy)
    vn = fcr * ag / 2
    return {"Vn": vn, "phiVn": PHI_V * vn, "phi": PHI_V}


# --------------------------------------------------------------------------- NTC-DCEA (CDMX)
def ntc_me(p: dict, l: float, cb: float, e: float = E_NTC, g: float = G_NTC) -> float:
    """Momento crítico elástico de pandeo lateral por flexotorsión (NTC-DCEA ec. 6.3.4), N·m."""
    return cb * math.pi / l * math.sqrt(e * p["Iy"] * g * p["J"] + (math.pi * e / l) ** 2 * p["Iy"] * p["Cw"])


def ntc_flexion_i(p: dict, fy: float, l: float, cb: float, e: float = E_NTC, g: float = G_NTC) -> dict:
    """MR [N·m] de un perfil I compacto de doble simetría (NTC-DCEA 6.3). l = 0: soporte lateral continuo."""
    cl = clasificar_i(p, fy, e)
    mp = fy * p["Zx"]
    if l <= 0:
        return {"MR": FR_NTC * mp, "Mn": mp, "Mp": mp, "Me": None, "controla": "fluencia (soporte continuo)",
                "clasificacion": cl}
    me = ntc_me(p, l, cb, e, g)
    if me > 2 / 3 * mp:
        mn = min(1.15 * mp * (1 - 0.28 * mp / me), mp)
        controla = "fluencia" if mn >= mp else "pandeo lateral por flexotorsión inelástico (Me > 2/3·Mp)"
    else:
        mn, controla = me, "pandeo lateral por flexotorsión elástico (Me ≤ 2/3·Mp)"
    return {"MR": FR_NTC * mn, "Mn": mn, "Mp": mp, "Me": me, "controla": controla, "clasificacion": cl}


def ntc_cortante_i(p: dict, fy: float, laminado: bool, e: float = E_NTC) -> dict:
    """NTC-DCEA 7.2: Vn = 0.6·Fy·Aa·Cv, Aa = h·ta; kv = 5.0 sin atiesadores."""
    h_ta = p["h"] / p["tw"]
    aa = p["h"] * p["tw"]
    if laminado and h_ta <= 2.24 * math.sqrt(e / fy):
        cv, fr = 1.0, 1.00
    else:
        kv = 5.0
        r1, r2 = 1.10 * math.sqrt(kv * e / fy), 1.37 * math.sqrt(kv * e / fy)
        if h_ta <= r1:
            cv = 1.0
        elif h_ta <= r2:
            cv = r1 / h_ta
        else:
            cv = 1.51 * kv * e / (h_ta ** 2 * fy)
        fr = FR_NTC
    vn = 0.6 * fy * aa * cv
    return {"Vn": vn, "VR": fr * vn, "FR": fr, "Cv": cv, "Aa": aa, "h_ta": h_ta}
