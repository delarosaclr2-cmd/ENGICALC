"""Conversión de unidades y propiedades del aire.

Referencias independientes:
* Factores exactos de definición (NIST SP 811).
* CoolProp 7 (HAPropsSI, ASHRAE RP-1485) para aire húmedo y agua — implementación
  completamente independiente de las ecuaciones del programa.
* Atmósfera estándar deducida desde primeros principios (hidrostática + gas ideal +
  gradiente térmico lineal) — segunda implementación de la ecuación de altitud.
"""
import math

import pytest

from core import units as U
from core import air_properties as AP

CP = pytest.importorskip("CoolProp.CoolProp")
from CoolProp.HumidAirProp import HAPropsSI  # noqa: E402


# --------------------------- unidades ---------------------------------------

def test_flow_cfm(check):
    check("1 cfm → m³/s", {"Q": "1 cfm"}, 0.3048 ** 3 / 60, U.to_si(1, "flow", "cfm"), 1e-15, reference="Definición ft = 0.3048 m")
    check("3600 m³/h → m³/s", {"Q": "3600 m³/h"}, 1.0, U.to_si(3600, "flow", "m³/h"), 1e-15, reference="Definición")


def test_velocity_pressure_temperature(check):
    check("1 fpm → m/s", {"V": "1 fpm"}, 0.00508, U.to_si(1, "velocity", "fpm"), 1e-15, reference="Definición")
    check("1 in.wg (60 °F) → Pa", {"P": "1 in.wg"}, 248.84, U.to_si(1, "pressure", "in.wg"), 1e-12, reference="ASHRAE/NIST SP 811")
    check("68 °F → °C", {"t": "68 °F"}, 20.0, U.to_si(68, "temperature", "°F"), 1e-12, reference="Definición")
    check("293.15 K → °C", {"t": "293.15 K"}, 20.0, U.to_si(293.15, "temperature", "K"), 1e-12, reference="Definición")
    check("ΔT 9 °F → K", {"dT": "9 °F"}, 5.0, U.to_si(9, "temperature_diff", "°F"), 1e-12, reference="Definición")
    check("1 hp → W", {"P": "1 hp"}, 745.69987, U.to_si(1, "power", "hp"), 1e-12, reference="NIST SP 811")
    check("0.075 lb/ft³ → kg/m³", {"rho": "0.075 lb/ft³"}, 1.2013848, U.to_si(0.075, "density", "lb/ft³"), 1e-7,
          reference="lb = 0.45359237 kg (exacto)")


@pytest.mark.parametrize("q,u", [("flow", "cfm"), ("pressure", "mmH2O"), ("temperature", "°F"), ("velocity", "fpm"),
                                 ("friction_rate", "in.wg/100ft"), ("enthalpy", "Btu/lb")])
def test_roundtrip(check, q, u):
    v = 123.456
    check(f"ida y vuelta {u}", {"v": v}, v, U.from_si(U.to_si(v, q, u), q, u), 1e-12, reference="Identidad")


def test_unknown_unit():
    with pytest.raises(U.UnitError):
        U.to_si(1, "flow", "gpm")


# --------------------------- aire ------------------------------------------------

def _iapws_sublimation(T):
    """Presión de sublimación del hielo Ih — IAPWS (Wagner, Riethmann, Feistel, Harvey, 2011)."""
    Tt, pt = 273.16, 611.657
    th = T / Tt
    a = (-0.212144006e2, 0.273203819e2, -0.610598130e1)
    b = (0.333333333e-2, 0.120666667e1, 0.170333333e1)
    return pt * math.exp(sum(ai * th ** bi for ai, bi in zip(a, b)) / th)


@pytest.mark.parametrize("t", [-40.0, -20.0, -5.0, 0.5, 20.0, 50.0, 100.0, 150.0])
def test_saturation_pressure_independent(check, t):
    # Nota: HAPropsSI('P_w', R=1) incluye el factor de realce f (≈1.004) y no es pws pura;
    # por eso bajo 0 °C la referencia es la ecuación IAPWS de sublimación.
    if t < 0:
        exp, ref = _iapws_sublimation(t + 273.15), "IAPWS 2011 (sublimación del hielo Ih)"
    else:
        exp, ref = CP.PropsSI("P", "T", t + 273.15, "Q", 0, "Water"), "CoolProp IAPWS-95 (saturación líquido-vapor)"
    check(f"pws({t} °C)", {"t_C": t}, exp, AP.saturation_pressure(t), 1.5e-3, reference=ref)


@pytest.mark.parametrize("z", [0.0, 500.0, 1000.0, 2240.0, 3000.0])
def test_altitude_first_principles(check, z):
    # Segunda implementación: dp/dz = −ρg, ρ = p/(R·T), T = T0 − L·z ⇒ p = p0·(1 − L·z/T0)^(g·M/(R·L))
    g, M, R, L, T0 = 9.80665, 0.0289644, 8.3144598, 0.0065, 288.15
    exp = 101325.0 * (1 - L * z / T0) ** (g * M / (R * L))
    check(f"p(Z={z})", {"Z_m": z}, exp, AP.pressure_from_altitude(z), 2e-5,
          reference="Hidrostática + gas ideal (US Std. Atmosphere 1976)")


def test_altitude_ashrae_table(check):
    # ASHRAE Fundamentals cap. 1, tabla 1: 2000 m → 79.495 kPa
    check("p(2000 m) tabla ASHRAE", {"Z_m": 2000}, 79495.0, AP.pressure_from_altitude(2000), 5e-5,
          reference="ASHRAE Fundamentals cap. 1, tabla 1")


@pytest.mark.parametrize("t,z,rh", [(20, 0, 0.5), (25, 2240, 0.5), (35, 0, 0.9), (5, 1500, 0.3), (60, 500, 0.2)])
def test_moist_air_vs_coolprop(check, t, z, rh):
    st = AP.compute_air_state("custom", t, z, None, rh)
    T, p = t + 273.15, st.p_pa
    inp = {"t_C": t, "Z_m": z, "HR": rh}
    W = HAPropsSI("W", "T", T, "P", p, "R", rh)
    check("W humedad absoluta", inp, W, st.W, 6e-3, reference="CoolProp HAPropsSI (con factor de realce)")
    rho = 1.0 / HAPropsSI("Vha", "T", T, "P", p, "R", rh)
    check("densidad aire húmedo", inp, rho, st.rho, 1e-3, reference="CoolProp HAPropsSI")
    check("entalpía", inp, HAPropsSI("H", "T", T, "P", p, "R", rh) / 1000.0, st.h_kj_kg, 6e-3,
          reference="CoolProp HAPropsSI")
    check("punto de rocío [K]", inp, HAPropsSI("Tdp", "T", T, "P", p, "R", rh), st.t_dew_c + 273.15, 5e-4,
          reference="CoolProp HAPropsSI")
    check("bulbo húmedo [K]", inp, HAPropsSI("Twb", "T", T, "P", p, "R", rh), st.t_wb_c + 273.15, 5e-4,
          reference="CoolProp HAPropsSI")


@pytest.mark.parametrize("t,tol", [(0.0, 5e-3), (20.0, 5e-3), (100.0, 8e-3), (200.0, 1.5e-2), (400.0, 2.5e-2)])
def test_viscosity_vs_coolprop(check, t, tol):
    # Tolerancia = precisión documentada del modelo de Sutherland en cada rango (ver air_properties.py)
    check(f"μ({t} °C)", {"t_C": t}, CP.PropsSI("V", "T", t + 273.15, "P", 101325, "Air"), AP.viscosity_sutherland(t),
          tol, reference="CoolProp (Lemmon y Jacobsen 2004)")


@pytest.mark.parametrize("t", [200.0, 400.0])
def test_viscosity_error_impact_on_friction(check, t):
    """El error de Sutherland a alta temperatura tiene efecto despreciable en el factor de fricción."""
    from core.friction import f_colebrook
    mu_ref = CP.PropsSI("V", "T", t + 273.15, "P", 101325, "Air")
    rho, V, D, er = 0.6, 20.0, 0.3, 3e-4
    f_ref = f_colebrook(rho * V * D / mu_ref, er)
    f_mod = f_colebrook(rho * V * D / AP.viscosity_sutherland(t), er)
    check(f"f con μ Sutherland a {t} °C", {"V": V, "D": D}, f_ref, f_mod, 5e-3, reference="f con μ de CoolProp")


def test_standard_air(check):
    st = AP.compute_air_state("ashrae_std")
    check("ρ aire estándar ASHRAE seco 20 °C", {"modo": "ashrae_std"}, 1.2041, st.rho, 2e-4,
          reference="ASHRAE: aire seco 20 °C, 101.325 kPa = 1.204 kg/m³")
    st2 = AP.compute_air_state("amca_std")
    check("ρ aire estándar AMCA", {"modo": "amca_std"}, 1.2, st2.rho, 2e-3, reference="AMCA 210 (≈1.2 kg/m³)")


def test_dry_vs_moist_density_differ():
    st = AP.compute_air_state("custom", 30, 0, None, 0.9)
    assert st.rho < st.rho_dry, "El aire húmedo es menos denso que el seco a igual T y p"


def test_air_domain_errors():
    with pytest.raises(AP.AirPropertyError):
        AP.compute_air_state("custom", 20, 0, None, 1.5)
    with pytest.raises(AP.AirPropertyError):
        AP.compute_air_state("custom", -300, 0, None, 0.5)
    with pytest.raises(AP.AirPropertyError):
        AP.saturation_pressure(250)


def test_ppm_conversion(check):
    # 1 ppm de CO (28.01 g/mol) a 25 °C y 1 atm = 1.145 mg/m³ (24.45 L/mol)
    check("ppm→mg/m³ CO", {"ppm": 1, "MW": 28.01}, 28.01 / 24.465, AP.ppm_to_mg_m3(1, 28.01), 1e-3,
          reference="Gas ideal, volumen molar 24.465 L/mol a 25 °C")
