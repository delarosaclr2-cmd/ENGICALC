"""Propiedades termofísicas del aire seco y húmedo.

Modelos utilizados (documentados en la memoria de cálculo):

* Presión atmosférica estándar con la altitud: ASHRAE Handbook—Fundamentals,
  cap. 1, ec. 3:  p = 101.325·(1 − 2.25577·10⁻⁵·Z)^5.2559  [kPa], válida en la
  troposfera (−500 m a 11 000 m). Equivale a la atmósfera estándar ISA.
* Presión de saturación del vapor: Hyland y Wexler (1983), ASHRAE Fundamentals
  cap. 1, ec. 5 (hielo, −100…0 °C) y ec. 6 (agua líquida, 0…200 °C).
* Relación de humedad: W = 0.621945·pw/(p − pw)  (ASHRAE ec. 20/22).
* Volumen específico: v = 0.287042·(t + 273.15)·(1 + 1.607858·W)/p  [m³/kg a.s.]
  (ASHRAE ec. 26, p en kPa).
* Densidad del aire húmedo: ρ = (1 + W)/v  (ASHRAE ec. 11).
* Entalpía: h = 1.006·t + W·(2501 + 1.86·t)  [kJ/kg a.s.] (ASHRAE ec. 32).
* Punto de rocío: inversión numérica exacta de Hyland-Wexler (pws(td) = pw).
* Bulbo húmedo termodinámico: solución numérica de ASHRAE ec. 35 (t* ≥ 0 °C) y ec. 37 (t* < 0 °C).
* Viscosidad dinámica: ley de Sutherland (White, Viscous Fluid Flow);
  μ0 = 1.716·10⁻⁵ Pa·s, T0 = 273.15 K, S = 110.4 K. Se desprecia el efecto de la
  humedad sobre la viscosidad (< 1 % en condiciones de ventilación habituales).

Hipótesis: comportamiento de gas ideal; se omite el factor de realce
(enhancement factor ≈ 1.004), lo que introduce errores < 0.5 % en W según
ASHRAE para presiones atmosféricas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from scipy.optimize import brentq

from . import constants as C
from .trace import Trace, n, KIND_HYPOTHESIS

SRC_ASHRAE = "ASHRAE Handbook—Fundamentals, cap. 1 (Psychrometrics)"
SRC_SUTH = "Ley de Sutherland — White, F. M., Viscous Fluid Flow"
MODULE = "Propiedades del aire"

# Modos de condición del aire
MODE_CUSTOM = "custom"
MODE_ASHRAE_STD = "ashrae_std"     # 20 °C, 101.325 kPa, aire seco
MODE_AMCA_STD = "amca_std"         # 20 °C, 101.325 kPa, HR 50 % (≈1.2 kg/m³)
MODE_STD_ATM = "std_atmosphere"    # T y p de la atmósfera estándar a la altitud

MODE_LABELS = {
    MODE_CUSTOM: "Condiciones personalizadas (T, altitud/presión, HR)",
    MODE_ASHRAE_STD: "Aire estándar ASHRAE (20 °C, 101.325 kPa, seco)",
    MODE_AMCA_STD: "Aire estándar AMCA (20 °C, 101.325 kPa, HR 50 %, ≈1.2 kg/m³)",
    MODE_STD_ATM: "Atmósfera estándar a la altitud indicada",
}


class AirPropertyError(ValueError):
    """Entradas físicamente imposibles para el cálculo de propiedades."""


# ---------------------------------------------------------------------------
# Funciones elementales (independientes y verificables)
# ---------------------------------------------------------------------------

def pressure_from_altitude(z_m: float) -> float:
    """Presión atmosférica estándar [Pa] a la altitud ``z_m`` [m] (ASHRAE ec. 3)."""
    base = 1.0 - C.ALT_COEF * z_m
    if base <= 0:
        raise AirPropertyError("Altitud fuera del dominio de la ecuación de atmósfera estándar")
    return C.P_STD_SEA_LEVEL * base ** C.ALT_EXPONENT


def temperature_from_altitude(z_m: float) -> float:
    """Temperatura estándar [°C] a la altitud ``z_m`` (ASHRAE ec. 4)."""
    return C.T_STD_SEA_LEVEL_C - C.LAPSE_RATE * z_m


def altitude_from_pressure(p_pa: float) -> float:
    """Altitud estándar equivalente [m] a la presión ``p_pa`` (inversa de ASHRAE ec. 3)."""
    return (1.0 - (p_pa / C.P_STD_SEA_LEVEL) ** (1.0 / C.ALT_EXPONENT)) / C.ALT_COEF


def saturation_pressure(t_c: float) -> float:
    """Presión de saturación del vapor de agua [Pa] (Hyland-Wexler, ASHRAE ec. 5 y 6).

    Sobre hielo para t < 0 °C y sobre agua líquida para t ≥ 0 °C.
    Dominio: −100 °C ≤ t ≤ 200 °C.
    """
    if t_c < -100.0 or t_c > 200.0:
        raise AirPropertyError(f"Temperatura {t_c} °C fuera del dominio de Hyland-Wexler (−100…200 °C)")
    T = t_c + C.T_ZERO_K
    if t_c < 0.0:
        c1, c2, c3, c4, c5, c6, c7 = (-5.6745359e3, 6.3925247, -9.6778430e-3, 6.2215701e-7,
                                      2.0747825e-9, -9.4840240e-13, 4.1635019)
        ln_p = c1 / T + c2 + c3 * T + c4 * T ** 2 + c5 * T ** 3 + c6 * T ** 4 + c7 * math.log(T)
    else:
        c8, c9, c10, c11, c12, c13 = (-5.8002206e3, 1.3914993, -4.8640239e-2, 4.1764768e-5,
                                      -1.4452093e-8, 6.5459673)
        ln_p = c8 / T + c9 + c10 * T + c11 * T ** 2 + c12 * T ** 3 + c13 * math.log(T)
    return math.exp(ln_p)


def humidity_ratio_from_pw(p_w: float, p: float) -> float:
    """Relación de humedad W [kg/kg a.s.] (ASHRAE ec. 20)."""
    if p_w >= p:
        raise AirPropertyError("La presión de vapor no puede igualar o superar la presión total")
    return C.MW_RATIO * p_w / (p - p_w)


def pw_from_humidity_ratio(W: float, p: float) -> float:
    return p * W / (C.MW_RATIO + W)


def dew_point(p_w: float) -> float:
    """Temperatura de rocío [°C]: inversión numérica de Hyland-Wexler."""
    if p_w <= 0:
        return float("nan")
    return brentq(lambda t: saturation_pressure(t) - p_w, -99.9, 199.9, xtol=1e-10)


def specific_volume(t_c: float, W: float, p: float) -> float:
    """Volumen específico [m³/kg aire seco] (ASHRAE ec. 26)."""
    return (C.R_DRY_AIR / 1000.0) * (t_c + C.T_ZERO_K) * (1.0 + C.VOLUME_FACTOR_VAPOR * W) / (p / 1000.0)


def moist_air_density(t_c: float, W: float, p: float) -> float:
    """Densidad del aire húmedo [kg/m³] (ASHRAE ec. 11)."""
    return (1.0 + W) / specific_volume(t_c, W, p)


def dry_air_density(t_c: float, p: float) -> float:
    """Densidad del aire completamente seco [kg/m³] a la misma T y p (gas ideal)."""
    return p / (C.R_DRY_AIR * (t_c + C.T_ZERO_K))


def enthalpy(t_c: float, W: float) -> float:
    """Entalpía del aire húmedo [kJ/kg a.s.] (ASHRAE ec. 32)."""
    return C.CP_DRY_AIR_KJ * t_c + W * (C.H_FG0_KJ + C.CP_VAPOR_KJ * t_c)


def cp_moist_per_kg_dry_air(W: float) -> float:
    """Calor específico del aire húmedo por kg de aire seco [kJ/(kg a.s.·K)]."""
    return C.CP_DRY_AIR_KJ + C.CP_VAPOR_KJ * W


def cp_moist_per_kg_mixture(W: float) -> float:
    """Calor específico por kg de mezcla [kJ/(kg·K)]."""
    return cp_moist_per_kg_dry_air(W) / (1.0 + W)


def viscosity_sutherland(t_c: float) -> float:
    """Viscosidad dinámica del aire [Pa·s] (ley de Sutherland)."""
    T = t_c + C.T_ZERO_K
    if T <= 0:
        raise AirPropertyError("Temperatura absoluta no positiva")
    return C.SUTHERLAND_MU0 * (T / C.SUTHERLAND_T0) ** 1.5 * (C.SUTHERLAND_T0 + C.SUTHERLAND_S) / (T + C.SUTHERLAND_S)


def wet_bulb(t_c: float, W: float, p: float) -> float:
    """Temperatura de bulbo húmedo termodinámico [°C].

    ASHRAE ec. 35 (t* ≥ 0 °C, sobre agua) y ec. 37 (t* < 0 °C, sobre hielo).
    """
    def resid(tw: float) -> float:
        pws = saturation_pressure(tw)
        Ws = C.MW_RATIO * pws / (p - pws)
        if tw >= 0.0:
            Wcalc = ((2501.0 - 2.326 * tw) * Ws - 1.006 * (t_c - tw)) / (2501.0 + 1.86 * t_c - 4.186 * tw)
        else:
            Wcalc = ((2830.0 - 0.24 * tw) * Ws - 1.006 * (t_c - tw)) / (2830.0 + 1.86 * t_c - 2.1 * tw)
        return Wcalc - W
    lo = max(-50.0, dew_point(pw_from_humidity_ratio(W, p)) - 5.0) if W > 0 else -50.0
    try:
        return brentq(resid, lo, t_c + 1e-9, xtol=1e-8)
    except ValueError:
        return float("nan")


# ---------------------------------------------------------------------------
# Estado completo del aire
# ---------------------------------------------------------------------------

@dataclass
class AirState:
    mode: str
    t_c: float
    rh: float                 # 0–1
    p_pa: float
    altitude_m: float | None
    p_std_altitude_pa: float | None
    T_k: float
    p_ws: float
    p_w: float
    W: float                  # kg/kg a.s.
    t_dew_c: float
    t_wb_c: float
    h_kj_kg: float            # kJ/kg a.s.
    v_m3_kg: float            # m³/kg a.s.
    rho: float                # densidad del aire húmedo (mezcla) kg/m³
    rho_dry: float            # densidad del aire seco a la misma T y p
    rho_dry_partial: float    # masa de aire seco por m³ de mezcla (1/v)
    mu: float                 # Pa·s
    nu: float                 # m²/s
    cp_da: float              # kJ/(kg a.s.·K)
    cp_mix: float             # kJ/(kg mezcla·K)
    pressure_source: str = ""
    trace: Trace = field(default_factory=Trace, repr=False)

    def with_temperature(self, t_c: float) -> "AirState":
        """Mismo aire (misma W y p) a otra temperatura: útil para tramos calientes."""
        return air_state_from_W(t_c, self.W, self.p_pa, mode=self.mode, altitude_m=self.altitude_m,
                                record_trace=False)


def air_state_from_W(t_c: float, W: float, p: float, mode: str = MODE_CUSTOM,
                     altitude_m: float | None = None, record_trace: bool = False) -> AirState:
    """Estado del aire a partir de T, W y p (sin trazabilidad detallada)."""
    p_w = pw_from_humidity_ratio(W, p)
    pws = saturation_pressure(t_c)
    rh = min(p_w / pws, 1.0) if pws > 0 else 0.0
    return _build_state(mode, t_c, rh, p, altitude_m, None, pws, p_w, W, record_trace)


def _build_state(mode, t_c, rh, p, altitude_m, p_alt, pws, p_w, W, record_trace, p_source="") -> AirState:
    T = t_c + C.T_ZERO_K
    v = specific_volume(t_c, W, p)
    rho = (1.0 + W) / v
    rho_dry = dry_air_density(t_c, p)
    mu = viscosity_sutherland(t_c)
    td = dew_point(p_w) if p_w > 0 else float("nan")
    twb = wet_bulb(t_c, W, p) if t_c <= 150 else float("nan")
    h = enthalpy(t_c, W)
    st = AirState(mode=mode, t_c=t_c, rh=rh, p_pa=p, altitude_m=altitude_m, p_std_altitude_pa=p_alt,
                  T_k=T, p_ws=pws, p_w=p_w, W=W, t_dew_c=td, t_wb_c=twb, h_kj_kg=h, v_m3_kg=v,
                  rho=rho, rho_dry=rho_dry, rho_dry_partial=1.0 / v, mu=mu, nu=mu / rho,
                  cp_da=cp_moist_per_kg_dry_air(W), cp_mix=cp_moist_per_kg_mixture(W),
                  pressure_source=p_source)
    return st


def compute_air_state(mode: str = MODE_CUSTOM, t_c: float = 20.0, altitude_m: float | None = 0.0,
                      p_pa: float | None = None, rh: float = 0.5) -> AirState:
    """Calcula el estado completo del aire con trazabilidad.

    Parámetros
    ----------
    mode : uno de ``MODE_*``.
    t_c : temperatura de bulbo seco [°C].
    altitude_m : altitud [m] (para estimar la presión si ``p_pa`` es None).
    p_pa : presión barométrica medida/de proyecto [Pa]. Si se da, prevalece sobre la altitud.
    rh : humedad relativa en fracción 0–1.
    """
    tr = Trace()
    p_alt = None
    if mode == MODE_ASHRAE_STD:
        t_c, p, rh, altitude_m = 20.0, C.P_STD_SEA_LEVEL, 0.0, 0.0
        p_source = "Condición estándar ASHRAE"
    elif mode == MODE_AMCA_STD:
        t_c, p, rh, altitude_m = 20.0, C.P_STD_SEA_LEVEL, 0.5, 0.0
        p_source = "Condición estándar AMCA"
    elif mode == MODE_STD_ATM:
        if altitude_m is None:
            raise AirPropertyError("Se requiere la altitud para la atmósfera estándar")
        p = pressure_from_altitude(altitude_m)
        t_c = temperature_from_altitude(altitude_m)
        p_alt = p
        p_source = "Atmósfera estándar a la altitud"
    else:
        if altitude_m is not None:
            p_alt = pressure_from_altitude(altitude_m)
        if p_pa is not None and p_pa > 0:
            p = p_pa
            p_source = "Presión barométrica indicada por el usuario"
        elif p_alt is not None:
            p = p_alt
            p_source = "Presión estimada con la atmósfera estándar (ASHRAE ec. 3)"
        else:
            raise AirPropertyError("Indique la presión barométrica o la altitud")

    # Validaciones de dominio (errores físicos → excepción)
    if t_c + C.T_ZERO_K <= 0:
        raise AirPropertyError("La temperatura absoluta debe ser positiva")
    if not (0.0 <= rh <= 1.0):
        raise AirPropertyError("La humedad relativa debe estar entre 0 y 100 %")
    if p <= 0:
        raise AirPropertyError("La presión atmosférica debe ser positiva")

    if p_alt is not None and altitude_m is not None:
        tr.add(MODULE, "Presión atmosférica estándar a la altitud",
               "p = 101.325·(1 − 2.25577·10⁻⁵·Z)^5.2559",
               [("Z", altitude_m, "m", "Altitud sobre el nivel del mar")],
               f"p = 101.325·(1 − 2.25577·10⁻⁵·{n(altitude_m)})^5.2559 = {n(p_alt / 1000)} kPa",
               p_alt, "Pa", SRC_ASHRAE + ", ec. 3")
    T = t_c + C.T_ZERO_K
    tr.add(MODULE, "Temperatura absoluta", "T = t + 273.15", [("t", t_c, "°C", "Temperatura de bulbo seco")],
           f"T = {n(t_c)} + 273.15", T, "K", "Definición de la escala Kelvin")
    pws = saturation_pressure(t_c)
    tr.add(MODULE, "Presión de saturación del vapor", "ln pws = C8/T + C9 + C10·T + C11·T² + C12·T³ + C13·ln T"
           if t_c >= 0 else "ln pws = C1/T + C2 + C3·T + C4·T² + C5·T³ + C6·T⁴ + C7·ln T",
           [("T", T, "K", "Temperatura absoluta")], f"pws({n(T)} K)", pws, "Pa",
           SRC_ASHRAE + ", ec. 5/6 (Hyland-Wexler)")
    p_w = rh * pws
    tr.add(MODULE, "Presión parcial del vapor", "pw = φ·pws", [("φ", rh, "-", "Humedad relativa"), ("pws", pws, "Pa", "")],
           f"pw = {n(rh)}·{n(pws)}", p_w, "Pa", SRC_ASHRAE + ", ec. 24 (sin factor de realce)",
           notes="Se omite el factor de realce (≈1.004); error < 0.5 % en W.")
    W = humidity_ratio_from_pw(p_w, p)
    tr.add(MODULE, "Relación de humedad (humedad absoluta)", "W = 0.621945·pw/(p − pw)",
           [("pw", p_w, "Pa", ""), ("p", p, "Pa", "Presión barométrica")],
           f"W = 0.621945·{n(p_w)}/({n(p)} − {n(p_w)})", W, "kg/kg a.s.", SRC_ASHRAE + ", ec. 20")
    st = _build_state(mode, t_c, rh, p, altitude_m, p_alt, pws, p_w, W, True, p_source)
    tr.add(MODULE, "Volumen específico", "v = 0.287042·(t + 273.15)·(1 + 1.607858·W)/p",
           [("t", t_c, "°C", ""), ("W", W, "kg/kg", ""), ("p", p / 1000, "kPa", "")],
           f"v = 0.287042·{n(T)}·(1 + 1.607858·{n(W)})/{n(p / 1000)}", st.v_m3_kg, "m³/kg a.s.", SRC_ASHRAE + ", ec. 26")
    tr.add(MODULE, "Densidad del aire húmedo", "ρ = (1 + W)/v", [("W", W, "kg/kg", ""), ("v", st.v_m3_kg, "m³/kg", "")],
           f"ρ = (1 + {n(W)})/{n(st.v_m3_kg)}", st.rho, "kg/m³", SRC_ASHRAE + ", ec. 11")
    tr.add(MODULE, "Densidad del aire seco (misma T y p)", "ρda = p/(Rda·T)",
           [("p", p, "Pa", ""), ("Rda", C.R_DRY_AIR, "J/(kg·K)", ""), ("T", T, "K", "")],
           f"ρda = {n(p)}/({C.R_DRY_AIR}·{n(T)})", st.rho_dry, "kg/m³", "Ecuación de gas ideal; " + SRC_ASHRAE)
    tr.add(MODULE, "Viscosidad dinámica", "μ = μ0·(T/T0)^1.5·(T0 + S)/(T + S)",
           [("μ0", C.SUTHERLAND_MU0, "Pa·s", ""), ("T0", C.SUTHERLAND_T0, "K", ""), ("S", C.SUTHERLAND_S, "K", ""),
            ("T", T, "K", "")],
           f"μ = 1.716·10⁻⁵·({n(T)}/273.15)^1.5·(383.55)/({n(T)} + 110.4)", st.mu, "Pa·s", SRC_SUTH,
           notes="Se desprecia el efecto de la humedad sobre la viscosidad.")
    tr.add(MODULE, "Viscosidad cinemática", "ν = μ/ρ", [("μ", st.mu, "Pa·s", ""), ("ρ", st.rho, "kg/m³", "")],
           f"ν = {n(st.mu)}/{n(st.rho)}", st.nu, "m²/s", "Definición")
    tr.add(MODULE, "Calor específico del aire húmedo", "cp = 1.006 + 1.86·W", [("W", W, "kg/kg", "")],
           f"cp = 1.006 + 1.86·{n(W)}", st.cp_da, "kJ/(kg a.s.·K)", SRC_ASHRAE + ", derivada de ec. 32")
    tr.add(MODULE, "Entalpía", "h = 1.006·t + W·(2501 + 1.86·t)", [("t", t_c, "°C", ""), ("W", W, "kg/kg", "")],
           f"h = 1.006·{n(t_c)} + {n(W)}·(2501 + 1.86·{n(t_c)})", st.h_kj_kg, "kJ/kg a.s.", SRC_ASHRAE + ", ec. 32")
    tr.add(MODULE, "Punto de rocío", "pws(td) = pw  (inversión numérica)", [("pw", p_w, "Pa", "")],
           f"td tal que pws(td) = {n(p_w)} Pa", st.t_dew_c, "°C", SRC_ASHRAE + ", inversión de ec. 5/6")
    tr.add(MODULE, "Bulbo húmedo termodinámico", "W = [(2501 − 2.326·t*)·Ws* − 1.006·(t − t*)]/(2501 + 1.86·t − 4.186·t*)",
           [("t", t_c, "°C", ""), ("W", W, "kg/kg", "")], "solución numérica de t*", st.t_wb_c, "°C",
           SRC_ASHRAE + ", ec. 35 (sobre agua) / ec. 37 (sobre hielo)")
    if mode in (MODE_ASHRAE_STD, MODE_AMCA_STD):
        tr.add(MODULE, "Condición de referencia", "—", [], MODE_LABELS[mode], "—", "", "Condición estándar declarada",
               kind=KIND_HYPOTHESIS)
    st.trace = tr
    return st


def density_correction_factor(rho: float, rho_ref: float = C.RHO_STD_AMCA) -> float:
    """Factor de corrección de densidad df = ρ/ρref."""
    return rho / rho_ref


def mixing_temperature(streams: list[tuple[float, float]]) -> float:
    """Temperatura de mezcla adiabática de corrientes (ṁ [kg/s], t [°C]) con cp constante."""
    m = sum(s[0] for s in streams)
    if m <= 0:
        return streams[0][1] if streams else 20.0
    return sum(s[0] * s[1] for s in streams) / m


def ppm_to_mg_m3(ppm: float, molar_mass_g_mol: float, t_c: float = 25.0, p_pa: float = C.P_STD_SEA_LEVEL) -> float:
    """Convierte ppm (v/v) a mg/m³ a T y p reales (gas ideal, R = 8.314462 J/(mol·K))."""
    molar_conc = p_pa / (8.314462618 * (t_c + C.T_ZERO_K))  # mol/m³
    return ppm * 1e-6 * molar_conc * molar_mass_g_mol * 1000.0


def mg_m3_to_ppm(mg_m3: float, molar_mass_g_mol: float, t_c: float = 25.0, p_pa: float = C.P_STD_SEA_LEVEL) -> float:
    molar_conc = p_pa / (8.314462618 * (t_c + C.T_ZERO_K))
    return mg_m3 / (1e-6 * molar_conc * molar_mass_g_mol * 1000.0)
