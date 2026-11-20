"""Propiedades del agua y del vapor: IAPWS-IF97 (regiones 1, 2 y 4) y viscosidad IAPWS 2008.

Fuentes:
- IAPWS R7-97(2012), "Revised Release on the IAPWS Industrial Formulation 1997 for the
  Thermodynamic Properties of Water and Steam": ecs. 7 (región 1), 15-17 (región 2),
  30-31 (región 4) y ec. 5 (frontera 2-3).
- IAPWS R12-08, "Release on the IAPWS Formulation 2008 for the Viscosity of Ordinary Water
  Substance", ecs. 10-12 (μ̄₂ = 1, uso industrial).

Unidades SI: p [Pa], T [K], v [m³/kg], h [J/kg], s [J/(kg·K)], μ [Pa·s].
Rango implementado: región 1 (líquido, 273.15 K ≤ T ≤ 623.15 K) y región 2 (vapor,
p ≤ p_sat(T) hasta 623.15 K y p ≤ p_B23(T) hasta 1073.15 K). La región 3 (cerca del punto
crítico) NO está implementada: se rechaza con un error.
La implementación se contrasta en las pruebas con IAPWS-95 (CoolProp) y con los valores de
verificación de la propia norma.
"""
from __future__ import annotations

import math

R = 461.526            # J/(kg·K)
T_CRIT = 647.096       # K
P_CRIT = 22.064e6      # Pa
RHO_CRIT = 322.0       # kg/m³

# ---------------- Región 4 (saturación) ----------------
_N4 = [0.0, 0.11670521452767e4, -0.72421316703206e6, -0.17073846940092e2, 0.12020824702470e5,
       -0.32325550322333e7, 0.14915108613530e2, -0.48232657361591e4, 0.40511340542057e6,
       -0.23855557567849, 0.65017534844798e3]


def p_sat(t_k: float) -> float:
    """Presión de saturación [Pa], 273.15 K ≤ T ≤ 647.096 K (IF97 ec. 30)."""
    if not 273.15 <= t_k <= T_CRIT:
        raise ValueError(f"T = {t_k:.2f} K fuera del intervalo de saturación (273.15–647.096 K)")
    n = _N4
    th = t_k + n[9] / (t_k - n[10])
    a = th * th + n[1] * th + n[2]
    b = n[3] * th * th + n[4] * th + n[5]
    c = n[6] * th * th + n[7] * th + n[8]
    return (2 * c / (-b + math.sqrt(b * b - 4 * a * c))) ** 4 * 1e6


def t_sat(p_pa: float) -> float:
    """Temperatura de saturación [K], 611.213 Pa ≤ p ≤ 22.064 MPa (IF97 ec. 31)."""
    if not 611.212 <= p_pa <= P_CRIT:
        raise ValueError(f"p = {p_pa/1e3:.3f} kPa fuera del intervalo de saturación")
    n = _N4
    be = (p_pa / 1e6) ** 0.25
    e = be * be + n[3] * be + n[6]
    f = n[1] * be * be + n[4] * be + n[7]
    g = n[2] * be * be + n[5] * be + n[8]
    d = 2 * g / (-f - math.sqrt(f * f - 4 * e * g))
    return (n[10] + d - math.sqrt((n[10] + d) ** 2 - 4 * (n[9] + n[10] * d))) / 2


def p_b23(t_k: float) -> float:
    """Frontera entre las regiones 2 y 3 [Pa] (IF97 ec. 5)."""
    return (0.34805185628969e3 - 0.11671859879975e1 * t_k + 0.10192970039326e-2 * t_k * t_k) * 1e6


# ---------------- Región 1 (líquido) ----------------
_R1 = [  # (I, J, n)
    (0, -2, 0.14632971213167), (0, -1, -0.84548187169114), (0, 0, -0.37563603672040e1),
    (0, 1, 0.33855169168385e1), (0, 2, -0.95791963387872), (0, 3, 0.15772038513228),
    (0, 4, -0.16616417199501e-1), (0, 5, 0.81214629983568e-3), (1, -9, 0.28319080123804e-3),
    (1, -7, -0.60706301565874e-3), (1, -1, -0.18990068218419e-1), (1, 0, -0.32529748770505e-1),
    (1, 1, -0.21841717175414e-1), (1, 3, -0.52838357969930e-4), (2, -3, -0.47184321073267e-3),
    (2, 0, -0.30001780793026e-3), (2, 1, 0.47661393906987e-4), (2, 3, -0.44141845330846e-5),
    (2, 17, -0.72694996297594e-15), (3, -4, -0.31679644845054e-4), (3, 0, -0.28270797985312e-5),
    (3, 6, -0.85205128120103e-9), (4, -5, -0.22425281908000e-5), (4, -2, -0.65171222895601e-6),
    (4, 10, -0.14341729937924e-12), (5, -8, -0.40516996860117e-6), (8, -11, -0.12734301741641e-8),
    (8, -6, -0.17424871230634e-9), (21, -29, -0.68762131295531e-18), (23, -31, 0.14478307828521e-19),
    (29, -38, 0.26335781662795e-22), (30, -39, -0.11947622640071e-22), (31, -40, 0.18228094581404e-23),
    (32, -41, -0.93537087292458e-25),
]


def _region1(p, t):
    pi, tau = p / 16.53e6, 1386.0 / t
    a, b = 7.1 - pi, tau - 1.222
    g = gp = gt = 0.0
    for i, j, n in _R1:
        g += n * a ** i * b ** j
        gp += -n * i * a ** (i - 1) * b ** j
        gt += n * j * a ** i * b ** (j - 1)
    v = pi * gp * R * t / p
    h = tau * gt * R * t
    s = (tau * gt - g) * R
    return v, h, s


# ---------------- Región 2 (vapor) ----------------
_R2_0 = [(0, -0.96927686500217e1), (1, 0.10086655968018e2), (-5, -0.56087911283020e-2),
         (-4, 0.71452738081455e-1), (-3, -0.40710498223928), (-2, 0.14240819171444e1),
         (-1, -0.43839511319450e1), (2, -0.28408632460772), (3, 0.21268463753307e-1)]
_R2_R = [
    (1, 0, -0.17731742473213e-2), (1, 1, -0.17834862292358e-1), (1, 2, -0.45996013696365e-1),
    (1, 3, -0.57581259083432e-1), (1, 6, -0.50325278727930e-1), (2, 1, -0.33032641670203e-4),
    (2, 2, -0.18948987516315e-3), (2, 4, -0.39392777243355e-2), (2, 7, -0.43797295650573e-1),
    (2, 36, -0.26674547914087e-4), (3, 0, 0.20481737692309e-7), (3, 1, 0.43870667284435e-6),
    (3, 3, -0.32277677238570e-4), (3, 6, -0.15033924542148e-2), (3, 35, -0.40668253562649e-1),
    (4, 1, -0.78847309559367e-9), (4, 2, 0.12790717852285e-7), (4, 3, 0.48225372718507e-6),
    (5, 7, 0.22922076337661e-5), (6, 3, -0.16714766451061e-10), (6, 16, -0.21171472321355e-2),
    (6, 35, -0.23895741934104e2), (7, 0, -0.59059564324270e-17), (7, 11, -0.12621808899101e-5),
    (7, 25, -0.38946842435739e-1), (8, 8, 0.11256211360459e-10), (8, 36, -0.82311340897998e1),
    (9, 13, 0.19809712802088e-7), (10, 4, 0.10406965210174e-18), (10, 10, -0.10234747095929e-12),
    (10, 14, -0.10018179379511e-8), (16, 29, -0.80882908646985e-10), (16, 50, 0.10693031879409),
    (18, 57, -0.33662250574171), (20, 20, 0.89185845355421e-24), (20, 35, 0.30629316876232e-12),
    (20, 48, -0.42002467698208e-5), (21, 21, -0.59056029685639e-25), (22, 53, 0.37826947613457e-5),
    (23, 39, -0.12768608934681e-14), (24, 26, 0.73087610595061e-28), (24, 40, 0.55414715350778e-16),
    (24, 58, -0.94369707241210e-6),
]


def _region2(p, t):
    pi, tau = p / 1e6, 540.0 / t
    g0 = math.log(pi)
    g0t = 0.0
    for j, n in _R2_0:
        g0 += n * tau ** j
        g0t += n * j * tau ** (j - 1)
    b = tau - 0.5
    gr = grp = grt = 0.0
    for i, j, n in _R2_R:
        gr += n * pi ** i * b ** j
        grp += n * i * pi ** (i - 1) * b ** j
        grt += n * pi ** i * j * b ** (j - 1)
    v = pi * (1 / pi + grp) * R * t / p
    h = tau * (g0t + grt) * R * t
    s = (tau * (g0t + grt) - (g0 + gr)) * R
    return v, h, s


# ---------------- Interfaz ----------------
class Estado:
    """Estado del agua: p [Pa], T [K], v, h, s, x (título; None si es una sola fase), fase."""

    def __init__(self, p, t, v, h, s, x, fase):
        self.p, self.t, self.v, self.h, self.s, self.x, self.fase = p, t, v, h, s, x, fase
        self.rho = 1.0 / v

    @property
    def mu(self) -> float:
        if self.x is not None and 0 < self.x < 1:
            # Mezcla: viscosidad del vapor saturado como aproximación (se advierte en el motor)
            return viscosidad(self.t, 1.0 / estado_sat(self.p, 1.0)._vg)
        return viscosidad(self.t, self.rho)

    def __repr__(self):
        return (f"Estado({self.fase}, p={self.p/1e3:.3f} kPa, T={self.t-273.15:.2f} °C, "
                f"ρ={self.rho:.4f} kg/m³, h={self.h/1e3:.2f} kJ/kg, x={self.x})")


def region(p, t):
    if not 273.15 <= t <= 1073.15:
        raise ValueError(f"T = {t-273.15:.1f} °C fuera del intervalo de IF97 implementado (0–800 °C)")
    if p <= 0 or p > 100e6:
        raise ValueError("Presión fuera del intervalo de IF97 (0–100 MPa)")
    if t <= 623.15:
        return 1 if p > p_sat(t) else 2
    if p <= p_b23(t):
        return 2
    raise ValueError("Estado en la región 3 de IF97 (cerca del punto crítico): no implementada")


def estado_pt(p, t) -> Estado:
    """Estado de una sola fase a partir de p y T."""
    r = region(p, t)
    v, h, s = (_region1 if r == 1 else _region2)(p, t)
    return Estado(p, t, v, h, s, None, "líquido" if r == 1 else "vapor")


def estado_sat(p, x) -> Estado:
    """Mezcla saturada de título x (0 = líquido saturado, 1 = vapor saturado seco)."""
    if not 0.0 <= x <= 1.0:
        raise ValueError("El título debe estar entre 0 y 1")
    t = t_sat(p)
    if t > 623.15:
        raise ValueError("Saturación por encima de 350 °C: requiere la región 3 (no implementada)")
    vf, hf, sf = _region1(p, t)
    vg, hg, sg = _region2(p, t)
    e = Estado(p, t, vf + x * (vg - vf), hf + x * (hg - hf), sf + x * (sg - sf), x,
               "vapor saturado" if x == 1 else ("líquido saturado" if x == 0 else "mezcla"))
    e._vf, e._vg, e._hf, e._hg = vf, vg, hf, hg
    return e


def estado_ph(p, h) -> Estado:
    """Estado a partir de p y h (para expansiones isentálpicas y flujo adiabático)."""
    ts = t_sat(p) if p < P_CRIT else None
    if ts is not None and ts <= 623.15:
        sat = estado_sat(p, 0.0)
        hf, hg = sat._hf, sat._hg
        if hf <= h <= hg:
            return estado_sat(p, (h - hf) / (hg - hf))
        lo, hi = (273.15, ts) if h < hf else (ts, 1073.15)
    else:
        lo, hi = 273.15, 1073.15
    fun = lambda t: estado_pt(p, t).h - h
    if fun(lo) * fun(hi) > 0:
        raise ValueError("No se encontró temperatura para esa entalpía dentro del intervalo IF97")
    for _ in range(100):                               # bisección (h es monótona en T a p fija)
        mid = 0.5 * (lo + hi)
        if fun(lo) * fun(mid) <= 0:
            hi = mid
        else:
            lo = mid
        if hi - lo < 1e-7:
            break
    return estado_pt(p, 0.5 * (lo + hi))


# ---------------- Viscosidad IAPWS 2008 ----------------
_H0 = [1.67752, 2.20462, 0.6366564, -0.241605]
_H1 = [
    [5.20094e-1, 2.22531e-1, -2.81378e-1, 1.61913e-1, -3.25372e-2, 0.0, 0.0],
    [8.50895e-2, 9.99115e-1, -9.06851e-1, 2.57399e-1, 0.0, 0.0, 0.0],
    [-1.08374, 1.88797, -7.72479e-1, 0.0, 0.0, 0.0, 0.0],
    [-2.89555e-1, 1.26613, -4.89837e-1, 0.0, 6.98452e-2, 0.0, -4.35673e-3],
    [0.0, 0.0, -2.57040e-1, 0.0, 0.0, 8.72102e-3, 0.0],
    [0.0, 1.20573e-1, 0.0, 0.0, 0.0, 0.0, -5.93264e-4],
]


def viscosidad(t_k: float, rho: float) -> float:
    """Viscosidad dinámica [Pa·s] (IAPWS 2008, sin el término crítico μ̄₂)."""
    tb, rb = t_k / T_CRIT, rho / RHO_CRIT
    mu0 = 100 * math.sqrt(tb) / sum(h / tb ** i for i, h in enumerate(_H0))
    suma = 0.0
    for i in range(6):
        for j in range(7):
            if _H1[i][j]:
                suma += _H1[i][j] * (1 / tb - 1) ** i * (rb - 1) ** j
    return mu0 * math.exp(rb * suma) * 1e-6
