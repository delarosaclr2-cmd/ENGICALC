"""Caudales, campanas, geometría y dimensionamiento de ductos.

Los valores esperados se calculan a mano (aritmética explícita en la prueba) o con
ejemplos de referencia en unidades imperiales; no se reutilizan funciones del
programa para obtener el resultado esperado.
"""
import math

import pytest

from core import airflow as AF
from core import hood_design as HD
from core import duct_geometry as DG
from core import air_properties as AP
from core.friction import darcy_factor, darcy_weisbach, reynolds


def test_ach(check):
    r = AF.airflow_ach(20, 10, 5, 6)
    check("Q por ACH", {"L": 20, "A": 10, "H": 5, "ACH": 6}, 1000 * 6 / 3600, r.Q, 1e-12, reference="Q = V·ACH/3600")


def test_ach_volume_override(check):
    r = AF.airflow_ach(0, 0, 0, 10, volume=360)
    check("Q por ACH con volumen", {"V": 360, "ACH": 10}, 1.0, r.Q, 1e-12, reference="Q = V·ACH/3600")


def test_dilution(check):
    r = AF.airflow_dilution(10, 5, 0, 3)
    check("Q dilución", {"G": 10, "C": 5, "K": 3}, 6.0, r.Q, 1e-12, reference="Q = K·G/(C − Cb)")
    r2 = AF.airflow_dilution(10, 5, 1, 2, capture_eff=0.5)
    check("Q dilución con captura y fondo", {"G": 10, "C": 5, "Cb": 1, "K": 2, "ηc": 0.5}, 2 * 5 / 4, r2.Q, 1e-12,
          reference="Q = K·G(1−ηc)/(C − Cb)")


def test_dilution_infeasible():
    with pytest.raises(AF.AirflowError):
        AF.airflow_dilution(10, 1, 1, 1)
    with pytest.raises(AF.AirflowError):
        AF.airflow_dilution(10, 5, 0, 0.5)


def test_dilution_transient(check):
    V, Q, G, K, C0 = 500.0, 2.0, 10.0, 1.0, 50.0
    Css = G / Q
    t = 300.0
    exp = Css + (C0 - Css) * math.exp(-Q * t / V)
    check("C(t) mezcla perfecta", {"V": V, "Q": Q, "G": G, "C0": C0, "t": t}, exp,
          AF.concentration_vs_time(t, V, Q, G, K, C0), 1e-12, reference="Solución analítica EDO lineal")
    tt = AF.time_to_concentration(10.0, V, Q, G, K, C0)
    check("t para C = 10", {"C_obj": 10}, -V / Q * math.log((10 - Css) / (C0 - Css)), tt, 1e-12,
          reference="Solución analítica")


def test_thermal(check):
    air = AP.compute_air_state("custom", 25, 0, None, 0.0)
    r = AF.airflow_thermal(10000, 25, 30, air)
    m = 10000 / (1006.0 * 5)
    check("ṁ aire seco", {"q": 10000, "Δt": 5}, m, r.details["m_da"], 1e-9, reference="ṁ = q/(cp·Δt), cp = 1006 J/(kg·K)")
    check("Q entrada", {"v": air.v_m3_kg}, m * air.v_m3_kg, r.Q, 1e-9, reference="Q = ṁ·v")
    check("Q forma simplificada", {}, 10000 / (air.rho * 1006.0 * 5), r.details["Q_simple"], 1e-9,
          reference="Q = q/(ρ cp Δt)")


def test_occupancy(check):
    r = AF.airflow_occupancy(2.5, 20, 0.3, 100, 0.8)
    check("Voz 62.1", {"Rp": 2.5, "Pz": 20, "Ra": 0.3, "Az": 100, "Ez": 0.8}, (2.5 * 20 + 0.3 * 100) / 1000 / 0.8, r.Q, 1e-12,
          reference="Vbz = Rp·Pz + Ra·Az; Voz = Vbz/Ez")


# ------------------------------ campanas ---------------------------------------

@pytest.mark.parametrize("htype,expected", [
    ("exterior_plain", 0.5 * (10 * 0.3 ** 2 + 0.1)),
    ("exterior_flanged", 0.75 * 0.5 * (10 * 0.3 ** 2 + 0.1)),
    ("bench_plain", 0.5 * (5 * 0.3 ** 2 + 0.1)),
    ("bench_flanged", 0.75 * 0.5 * (5 * 0.3 ** 2 + 0.1)),
])
def test_hood_openings(check, htype, expected):
    r = HD.hood_airflow("H", htype, {"W": 0.5, "H": 0.2, "X": 0.3, "Vc": 0.5})
    check(f"Q {htype}", {"W": 0.5, "H": 0.2, "X": 0.3, "Vc": 0.5}, expected, r.Q, 1e-12, reference="DallaValle / ACGIH")


def test_hood_slots_booth_canopy(check):
    check("Q ranura", {"L": 1, "Vc": 0.5, "X": 0.3}, 3.7 * 1 * 0.5 * 0.3,
          HD.hood_airflow("H", "slot", {"L": 1, "Ws": 0.05, "X": 0.3, "Vc": 0.5}).Q, 1e-12, reference="Q = 3.7·L·V·X")
    check("Q ranura con brida", {}, 2.6 * 1 * 0.5 * 0.3,
          HD.hood_airflow("H", "slot_flanged", {"L": 1, "Ws": 0.05, "X": 0.3, "Vc": 0.5}).Q, 1e-12, reference="Q = 2.6·L·V·X")
    check("Q cabina", {}, 0.5 * 1.2 * 2.0, HD.hood_airflow("H", "booth", {"W": 1.2, "H": 2.0, "Vc": 0.5}).Q, 1e-12,
          reference="Q = V·W·H")
    check("Q dosel", {}, 1.4 * 4.0 * 0.8 * 0.5, HD.hood_airflow("H", "canopy", {"P": 4.0, "D": 0.8, "Vc": 0.5}).Q, 1e-12,
          reference="Q = 1.4·P·D·V")


def test_hood_imperial_example(check):
    # Ejemplo IP: abertura sin brida 1 ft², X = 1 ft, Vc = 100 fpm → Q = 100·(10 + 1) = 1100 cfm
    from core.units import to_si, from_si
    r = HD.hood_airflow("H", "exterior_plain", {"W": to_si(1, "length", "ft"), "H": to_si(1, "length", "ft"),
                                                "X": to_si(1, "length", "ft"), "Vc": to_si(100, "velocity", "fpm")})
    check("Q campana IP", {"A": "1 ft²", "X": "1 ft", "Vc": "100 fpm"}, 1100.0, from_si(r.Q, "flow", "cfm"), 1e-12,
          reference="Ecuación de DallaValle en unidades IP")


def test_hood_validity_flags():
    r = HD.hood_airflow("H", "exterior_plain", {"W": 0.1, "H": 0.1, "X": 0.5, "Vc": 0.5})
    assert any("fuera del rango" in v for v in r.validity)


def test_ce_fh(check):
    check("Fh(Ce=0.72)", {"Ce": 0.72}, (1 - 0.72 ** 2) / 0.72 ** 2, HD.ce_to_fh(0.72), 1e-12, reference="Fh = (1 − Ce²)/Ce²")
    check("Ce(Fh=0.49)", {"Fh": 0.49}, math.sqrt(1 / 1.49), HD.fh_to_ce(0.49), 1e-12, reference="Ce = √(1/(1+Fh))")


def test_hood_static_pressure(check):
    Q, A, rho = 0.5, math.pi * 0.2 ** 2 / 4, 1.2
    VP = 0.5 * rho * (Q / A) ** 2
    r = HD.hood_entry_loss(HD.HoodEntry("fh", 0.49), Q, A, rho)
    check("SPh = (1 + Fh)·VPd", {"Q": Q, "D": 0.2}, 1.49 * VP, r.SPh, 1e-12, reference="ACGIH")
    check("Ce efectivo", {}, math.sqrt(1 / 1.49), r.Ce_effective, 1e-12, reference="Ce = √(VP/SPh)")
    r2 = HD.hood_entry_loss(HD.HoodEntry("slot", Fh=0.25, Fs=1.78, slot_area=0.02), Q, A, rho)
    VPs = 0.5 * rho * (Q / 0.02) ** 2
    check("pérdida compuesta ranura", {}, 1.78 * VPs + 0.25 * VP, r2.he_total, 1e-12, reference="he = Fs·VPs + Fd·VPd")


# ------------------------------ ductos -----------------------------------------

def test_geometry(check):
    check("A circular D=0.3", {"D": 0.3}, math.pi * 0.09 / 4, DG.circle_area(0.3), 1e-15, reference="πD²/4")
    check("A rectangular 0.4×0.2", {"a": 0.4, "b": 0.2}, 0.08, DG.rect_area(0.4, 0.2), 1e-15, reference="a·b")
    check("Dh rectangular 0.4×0.2", {}, 4 * 0.08 / 1.2, DG.hydraulic_diameter_rect(0.4, 0.2), 1e-15, reference="4A/P")
    check("Dh circular = D", {}, 0.3, DG.DuctGeometry("circular", D=0.3).Dh, 1e-15, reference="4(πD²/4)/(πD)")
    check("De Huebscher cuadrado = 1.0932·a", {"a": 0.5}, 1.30 / 2 ** 0.25 * 0.5, DG.equivalent_diameter_rect(0.5, 0.5),
          1e-12, reference="De = 1.30(ab)^0.625/(a+b)^0.25")
    check("De Huebscher 0.4×0.2", {}, 1.30 * 0.08 ** 0.625 / 0.6 ** 0.25, DG.equivalent_diameter_rect(0.4, 0.2), 1e-12,
          reference="Huebscher (1948)")
    assert DG.equivalent_diameter_rect(0.4, 0.2) != pytest.approx(DG.hydraulic_diameter_rect(0.4, 0.2), rel=1e-3)


def test_rounding_rules(check):
    s = [100, 125, 150, 160, 180, 200]
    check("redondeo inferior", {"D": 0.17}, 0.16, DG.round_to_series(0.17, s, "down"), 1e-12, reference="Serie")
    check("redondeo superior", {"D": 0.17}, 0.18, DG.round_to_series(0.17, s, "up"), 1e-12, reference="Serie")
    check("redondeo cercano", {"D": 0.152}, 0.15, DG.round_to_series(0.152, s, "nearest"), 1e-12, reference="Serie")


def test_size_by_velocity(check):
    r = DG.size_by_velocity(1.0, 20.0, 1.2, 1.8e-5, 0.09e-3, rounding="none")
    check("D velocidad constante", {"Q": 1, "V": 20}, math.sqrt(4 * 1.0 / (math.pi * 20)), r.geometry.D, 1e-12,
          reference="D = √(4Q/(πV))")
    check("V resultante", {}, 20.0, r.V, 1e-12, reference="Continuidad")


def test_size_by_friction_reproduces_target(check):
    rho, mu, eps = 1.2, 1.8e-5, 0.09e-3
    r = DG.size_by_friction(2.0, 4.0, rho, mu, eps, rounding="none")
    D = r.geometry.D
    V = 2.0 / (math.pi * D ** 2 / 4)
    f = darcy_factor(reynolds(rho, V, D, mu), eps / D).f
    check("ΔP/L recalculada = objetivo", {"Q": 2, "ΔP/L": 4}, 4.0, darcy_weisbach(f, 1.0, D, rho, V), 1e-6,
          reference="Darcy-Weisbach + Colebrook recalculados")


def test_static_regain_balance(check):
    rho, mu, eps = 1.2, 1.8e-5, 0.09e-3
    secs = [DG.RegainSection(0.8, 6.0, 0.3)]
    r = DG.size_static_regain(10.0, secs, 0.75, rho, mu, eps)[0]
    VP1 = 0.5 * rho * 100
    lhs = 0.75 * (VP1 - r.VP)
    rhs = r.dp_per_m * 6.0 + 0.3 * r.VP
    check("recuperación estática R·ΔVP = pérdidas", {"V1": 10, "Q": 0.8}, lhs, rhs, 1e-5, reference="Balance del método")
