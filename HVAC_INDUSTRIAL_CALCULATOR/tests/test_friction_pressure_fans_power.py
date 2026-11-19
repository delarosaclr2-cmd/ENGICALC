"""Fricción, presión, accesorios, leyes de ventiladores, curvas y potencia.

Referencias independientes: soluciones de Colebrook por bisección (algoritmo
distinto del punto fijo del programa), fórmula explícita de Haaland, ley de
Prandtl–Kármán para tubo liso, curvas analíticas con intersección cerrada.
"""
import math

import numpy as np
import pytest
from scipy.optimize import brentq

from core import friction as FR
from core import pressure as PR
from core import fittings as FT
from core import fan_laws as FL
from core import power as PW
from core.fan_curves import FanCurve, AdjustedFan, find_intersections, speed_for_design_point
from core.constants import BHP_IP_CONSTANT


def test_reynolds(check):
    check("Re", {"ρ": 1.2, "V": 10, "D": 0.3, "μ": 1.8e-5}, 200000.0, FR.reynolds(1.2, 10, 0.3, 1.8e-5), 1e-12,
          reference="Re = ρVD/μ")


def test_laminar(check):
    check("f laminar Re=1000", {"Re": 1000}, 0.064, FR.darcy_factor(1000, 1e-4).f, 1e-12, reference="64/Re")


@pytest.mark.parametrize("Re,er", [(5e3, 0.0), (1e4, 1e-4), (1e5, 1e-4), (1e6, 1e-3), (1e7, 1e-5), (3e5, 5e-3)])
def test_colebrook_vs_bisection(check, Re, er):
    def g(f):
        return 1 / math.sqrt(f) + 2 * math.log10(er / 3.7 + 2.51 / (Re * math.sqrt(f)))
    exp = brentq(g, 1e-4, 1.0, xtol=1e-15)
    check(f"Colebrook Re={Re:g} εr={er:g}", {"Re": Re, "εr": er}, exp, FR.f_colebrook(Re, er), 1e-10,
          reference="Colebrook resuelto por bisección (Brent)")


@pytest.mark.parametrize("Re,er", [(1e4, 1e-4), (1e5, 1e-3), (1e6, 1e-4), (1e7, 1e-3)])
def test_explicit_correlations(check, Re, er):
    fc = FR.f_colebrook(Re, er)
    haaland = (-1.8 * math.log10((er / 3.7) ** 1.11 + 6.9 / Re)) ** -2
    check("Haaland vs Colebrook", {"Re": Re, "εr": er}, haaland, fc, 2e-2, reference="Haaland (1983), ±2 %")
    check("Swamee-Jain vs Colebrook", {"Re": Re, "εr": er}, fc, FR.f_swamee_jain(Re, er), 1.5e-2,
          reference="Swamee-Jain declara ≈±1 %")
    check("Churchill vs Colebrook", {"Re": Re, "εr": er}, fc, FR.f_churchill(Re, er), 3e-2, reference="Churchill (1977)")


def test_smooth_pipe_prandtl(check):
    f = brentq(lambda f: 1 / math.sqrt(f) - (2 * math.log10(1e5 * math.sqrt(f)) - 0.8), 0.005, 0.1)
    check("tubo liso Re=1e5 (Prandtl–Kármán)", {"Re": 1e5}, f, FR.f_colebrook(1e5, 0.0), 1e-2,
          reference="1/√f = 2 log(Re√f) − 0.8")


def test_transitional_flag():
    r = FR.darcy_factor(3000, 1e-4)
    assert r.regime == "transicional" and r.warnings
    assert r.f >= 64 / 3000


def test_fanning_darcy(check):
    check("Fanning = Darcy/4", {"f_D": 0.02}, 0.005, FR.fanning_from_darcy(0.02), 1e-15, reference="Definición")


def test_darcy_weisbach(check):
    check("ΔP Darcy-Weisbach", {"f": 0.02, "L": 10, "D": 0.3, "ρ": 1.2, "V": 10}, 0.02 * 10 / 0.3 * 0.5 * 1.2 * 100,
          FR.darcy_weisbach(0.02, 10, 0.3, 1.2, 10), 1e-12, reference="ΔP = f(L/D)ρV²/2")


def test_pressures(check):
    check("VP", {"ρ": 1.2, "V": 10}, 60.0, PR.velocity_pressure(1.2, 10), 1e-15, reference="ρV²/2")
    check("TP = SP + VP", {"SP": -200, "VP": 60}, -140.0, PR.total_pressure(-200, 60), 1e-15, reference="Definición")
    check("FSP = FTP − VPsal", {"FTP": 1500, "VP": 90}, 1410.0, PR.fan_static_pressure(1500, 90), 1e-15,
          reference="AMCA 210")
    check("VP 4005 fpm estándar", {"V": 4005}, 1.0, PR.vp_ip_standard(4005), 1e-12, reference="(V/4005)²")
    check("VP 4005 fpm desde SI (0.075 lb/ft³)", {"V": 4005, "ρ": 0.075}, 1.0, PR.vp_ip_general(4005, 0.075), 1.5e-3,
          reference="Forma (V/4005)² — diferencia por la definición de in.wg")


def test_fittings(check):
    check("ΔP local", {"K": 0.5, "ρ": 1.2, "V": 10}, 30.0, FT.fitting_loss(0.5, 1.2, 10), 1e-15, reference="KρV²/2")
    check("Borda-Carnot A1/A2=0.5", {}, 0.25, FT.k_sudden_expansion(0.1, 0.2), 1e-15, reference="(1 − A1/A2)²")
    check("contracción brusca β²=0.5", {}, 0.25, FT.k_sudden_contraction(0.1, 0.2), 1e-15, reference="Crane 0.5(1−β²)")
    check("difusor 20°", {}, 2.6 * math.sin(math.radians(10)) * 0.25, FT.k_gradual_expansion(20, 0.1, 0.2), 1e-15,
          reference="Crane fórmula 3")
    k, _ = FT.k_bend_idelchik(90, 1.5, Re=None, f_darcy=None, include_friction=False)
    check("codo 90° R/D=1.5 (local)", {"δ": 90, "R/D": 1.5}, 0.21 / math.sqrt(1.5), k, 1e-12,
          reference="Idelchik A1·B1·C1")
    k45, _ = FT.k_bend_idelchik(45, 2.0, include_friction=False)
    check("codo 45° R/D=2", {}, 0.9 * math.sin(math.radians(45)) * 0.21 / math.sqrt(2), k45, 1e-12,
          reference="Idelchik A1 = 0.9 sen δ")


def test_fan_laws(check):
    r = FL.affinity(2.0, 1000.0, 3000.0, 1000, 1200)
    check("Q ∝ N", {"N2/N1": 1.2}, 2.4, r.Q2, 1e-12, reference="AMCA 99")
    check("P ∝ N²", {}, 1440.0, r.P2, 1e-12, reference="AMCA 99")
    check("W ∝ N³", {}, 3000 * 1.728, r.W2, 1e-12, reference="AMCA 99")
    r2 = FL.affinity(2.0, 1000.0, 3000.0, 1000, 1000, 0.5, 0.6, 1.2, 0.9)
    check("Q ∝ D³", {"D2/D1": 1.2}, 2.0 * 1.2 ** 3, r2.Q2, 1e-12, reference="AMCA 99")
    check("P ∝ D²ρ", {}, 1000 * 1.44 * 0.75, r2.P2, 1e-12, reference="AMCA 99")
    check("W ∝ D⁵ρ", {}, 3000 * 1.2 ** 5 * 0.75, r2.W2, 1e-12, reference="AMCA 99")
    check("velocidad periférica", {"D": 0.5, "N": 1800}, math.pi * 0.5 * 30, FL.tip_speed(0.5, 1800), 1e-12,
          reference="U = πDN/60")


def _analytic_fan(rho_ref=1.2, rpm=1000):
    Q = np.linspace(0.5, 6.0, 23)
    pts = [{"Q": float(q), "P": float(2000 - 50 * q * q), "eta": float(0.8 - 0.02 * (q - 4) ** 2)} for q in Q]
    return FanCurve(id="T", rpm=rpm, rho_ref=rho_ref, points=pts, pressure_basis="total")


def test_operating_point_analytic(check):
    fan = AdjustedFan(_analytic_fan())
    qs = np.linspace(0.5, 6, 40)
    inter = find_intersections(fan, list(qs), list(30 * qs ** 2))
    check("Q operación analítica", {"ventilador": "2000 − 50Q²", "sistema": "30Q²"}, 5.0, inter[0], 2e-3,
          reference="Solución cerrada Q = √(2000/80)")
    check("P operación", {}, 750.0, fan.ftp(inter[0]), 5e-3, reference="30·Q²")


def test_density_correction(check):
    fan = AdjustedFan(_analytic_fan(), rho=0.9)
    check("P corregida por densidad", {"ρ": 0.9}, (2000 - 50 * 4) * 0.75, fan.ftp(2.0), 1e-3,
          reference="P ∝ ρ a Q constante")


def test_bep(check):
    fan = AdjustedFan(_analytic_fan())
    q_bep, eta = fan.bep()
    # η_total = Q·P/W con W = Q·P/η ⇒ η_total = η del catálogo; máximo en Q = 4
    check("Q_BEP", {}, 4.0, q_bep, 1e-2, reference="Máximo de η(Q) = 0.8 − 0.02(Q−4)²")
    check("η_max", {}, 0.8, eta, 1e-3, reference="Parábola de eficiencia")


def test_speed_for_design_point(check):
    fan = AdjustedFan(_analytic_fan())
    Qd, Pd = 4.0, 2000.0
    k = math.sqrt((Pd + 50 * Qd ** 2) / 2000.0)
    check("N requerida", {"Qd": Qd, "Pd": Pd}, 1000 * k, speed_for_design_point(fan, Qd, Pd), 2e-3,
          reference="P_k(Q) = 2000k² − 50Q² pasa por (Qd, Pd)")


def test_power_si(check):
    r = PW.power_chain(5.0, 1500.0, eta_fan=0.75, eta_drive=0.95, eta_motor=0.92, margin=0.1,
                       ratings_kw=[7.5, 11, 15, 18.5], hours=4000, tariff=2.0)
    check("P_aire", {"Q": 5, "FTP": 1500}, 7500.0, r.P_air_total, 1e-15, reference="Q·FTP")
    check("W ventilador", {"η": 0.75}, 10000.0, r.W_fan, 1e-12, reference="Q·FTP/η")
    check("W motor", {"η_tr": 0.95}, 10000 / 0.95, r.W_motor_out, 1e-12, reference="W/η_tr")
    check("P eléctrica", {"η_m": 0.92}, 10000 / 0.95 / 0.92, r.P_elec, 1e-12, reference="W_motor/η_m")
    check("motor normalizado", {"margen": 0.1}, 15000.0, r.motor_nominal, 1e-12, reference="Serie IEC ≥ 11.58 kW")
    check("energía anual", {"h": 4000}, 10000 / 0.95 / 0.92 / 1000 * 4000, r.energy_kwh, 1e-12, reference="E = P·t")


def test_power_ip_bhp(check):
    from core.units import to_si
    Q, P, eta = to_si(10000, "flow", "cfm"), to_si(4.0, "pressure", "in.wg"), 0.7
    r = PW.power_chain(Q, P, eta_fan=eta)
    bhp = r.W_fan / 745.69987
    check("BHP IP (6356)", {"Q": "10000 cfm", "P": "4 in.wg", "η": 0.7}, 10000 * 4 / (BHP_IP_CONSTANT * 0.7), bhp, 1.5e-3,
          reference="BHP = cfm·in.wg/(6356·η); 0.1 % por la definición de in.wg")


def test_power_static_basis(check):
    r = PW.power_chain(2.0, 1200.0, FSP=1100.0, eta_fan=0.70, eta_basis="static")
    check("W con base estática", {"FSP": 1100, "η_s": 0.7}, 2.0 * 1100 / 0.7, r.W_fan, 1e-12, reference="Q·FSP/η_s")
    check("η total resultante", {}, 2.0 * 1200 / (2.0 * 1100 / 0.7), r.eta_total, 1e-12, reference="Q·FTP/W")


def test_power_invalid():
    with pytest.raises(PW.PowerError):
        PW.power_chain(1, 1000, eta_fan=1.2)
    with pytest.raises(PW.PowerError):
        PW.power_chain(1, 1000, eta_fan=0.7, eta_motor=0)
