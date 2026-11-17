"""Pruebas del núcleo contra valores de referencia y métodos independientes."""
import math

import pytest

from calculadoras.nucleo import atmosfera, constantes as k, fluidos, psicrometria as ps, solidos
from calculadoras.nucleo.modelo import Campo, ErrorEntrada


# --- Constantes ---------------------------------------------------------------
def test_conversiones_conocidas():
    assert k.M3S_POR_CFM == pytest.approx(0.000471947, rel=1e-6)
    assert k.PIE3S_POR_GPM == pytest.approx(0.002228, rel=1e-3)
    assert k.KGM3_POR_LBPIE3 == pytest.approx(16.0185, rel=1e-5)
    assert k.PIES_POR_PSI_AGUA == pytest.approx(2.31, rel=2e-3)
    assert k.W_POR_HP == pytest.approx(745.7, rel=1e-4)
    assert k.G_PIES == pytest.approx(32.174, rel=1e-4)


# --- Atmósfera ----------------------------------------------------------------
def test_presion_altitud_contra_isa():
    # ISA independiente: p = p0·(1 − L·h/T0)^(g·M/(R·L)), L = 0.0065 K/m, T0 = 288.15 K
    expo = 9.80665 * 0.0289644 / (8.31447 * 0.0065)
    for h in (0, 1000, 2240, 3000):
        isa = 101325 * (1 - 0.0065 * h / 288.15) ** expo
        assert atmosfera.presion_por_altitud(h) == pytest.approx(isa, rel=2e-4)
    assert atmosfera.presion_por_altitud(2240) == pytest.approx(77160, rel=2e-3)
    with pytest.raises(ValueError):
        atmosfera.presion_por_altitud(20000)


# --- Psicrometría -------------------------------------------------------------
@pytest.mark.parametrize("t, p_ref", [(0.01, 611.66), (20, 2339.3), (25, 3169.9), (50, 12352), (100, 101418)])
def test_presion_saturacion_tablas_vapor(t, p_ref):
    assert ps.presion_saturacion(t) == pytest.approx(p_ref, rel=2e-3)


def test_estado_25C_50HR_contra_ashrae():
    p = 101325
    w = ps.humedad_por_hr(25, 50, p)
    assert w == pytest.approx(0.00992, rel=6e-3)          # ASHRAE con factor f = 1.0043
    assert ps.entalpia(25, w) == pytest.approx(50.4, abs=0.3)
    assert ps.punto_rocio(w, p) == pytest.approx(13.87, abs=0.15)
    assert ps.bulbo_humedo(25, w, p) == pytest.approx(17.88, abs=0.15)
    assert ps.volumen_especifico(25, w, p) == pytest.approx(0.8581, rel=2e-3)


def _stull(t, rh):
    """Correlación independiente de Stull (2011) para bulbo húmedo a nivel del mar."""
    return (t * math.atan(0.151977 * (rh + 8.313659) ** 0.5) + math.atan(t + rh) - math.atan(rh - 1.676331)
            + 0.00391838 * rh ** 1.5 * math.atan(0.023101 * rh) - 4.686035)


@pytest.mark.parametrize("t, rh", [(20, 50), (30, 30), (35, 80), (15, 90)])
def test_bulbo_humedo_contra_stull(t, rh):
    w = ps.humedad_por_hr(t, rh, 101325)
    # Stull reporta su propio error entre −1 °C y +0.65 °C respecto al cálculo psicrométrico
    assert ps.bulbo_humedo(t, w, 101325) == pytest.approx(_stull(t, rh), abs=1.0)


def test_ida_y_vuelta_bulbo_humedo():
    p = 80000
    w = ps.humedad_por_bulbo_humedo(30, 20, p)
    assert ps.bulbo_humedo(30, w, p) == pytest.approx(20, abs=1e-4)


def test_psicrometria_valida_entradas():
    with pytest.raises(ValueError):
        ps.humedad_por_hr(25, 120, 101325)
    with pytest.raises(ValueError):
        ps.humedad_por_bulbo_humedo(20, 25, 101325)


# --- Fluidos ------------------------------------------------------------------
def test_diametro_por_caudal():
    q = 3600 / 3600.0
    d = fluidos.diametro_por_caudal(q, 20)
    assert math.pi * d ** 2 / 4 * 20 == pytest.approx(q)
    with pytest.raises(ValueError):
        fluidos.diametro_por_caudal(1, 0)


def _colebrook_independiente(re, er):
    """Resolución independiente por bisección sobre x = 1/√f."""
    g = lambda x: x + 2 * math.log10(er / 3.7 + 2.51 * x / re)
    a, b = 1.0, 20.0
    for _ in range(200):
        m = (a + b) / 2
        if g(a) * g(m) <= 0:
            b = m
        else:
            a = m
    return 1 / ((a + b) / 2) ** 2


@pytest.mark.parametrize("re, er", [(1e4, 0), (1e5, 1e-4), (1e6, 1e-3), (5e7, 5e-2)])
def test_colebrook(re, er):
    f, regimen = fluidos.factor_friccion_darcy(re, er)
    assert regimen == "turbulento"
    assert f == pytest.approx(_colebrook_independiente(re, er), rel=1e-6)
    # Haaland (aproximación explícita) dentro de ±2 %
    haaland = (-1.8 * math.log10((er / 3.7) ** 1.11 + 6.9 / re)) ** -2
    assert f == pytest.approx(haaland, rel=0.02)


def test_laminar():
    f, regimen = fluidos.factor_friccion_darcy(1000, 0.001)
    assert regimen == "laminar" and f == pytest.approx(0.064)


def test_potencias():
    assert fluidos.potencia_incompresible(5000, 1000 / 3600, 0.8) == pytest.approx(1736.1, rel=1e-4)
    # Adiabática tiende a incompresible cuando Δp → 0
    p1, dp, q = 101325, 100, 1.0
    assert fluidos.potencia_adiabatica(p1, q, p1 + dp) == pytest.approx(dp * q, rel=1e-3)
    # Isotérmica ≤ adiabática
    assert fluidos.potencia_isotermica(10000, 1, 101325) < fluidos.potencia_adiabatica(10000, 1, 101325)


def test_media_logaritmica():
    assert fluidos.media_logaritmica(100, 50) == pytest.approx(50 / math.log(2))
    assert fluidos.media_logaritmica(40, 40) == 40


def test_sutherland():
    assert fluidos.viscosidad_aire_sutherland(20) == pytest.approx(1.81e-5, rel=0.01)


# --- Sólidos ------------------------------------------------------------------
def test_beverloo_a_mano():
    w = solidos.descarga_beverloo(1500, 0.2, 0.002)
    assert w == pytest.approx(0.58 * 1500 * math.sqrt(9.80665) * (0.2 - 1.4 * 0.002) ** 2.5)
    with pytest.raises(ValueError):
        solidos.descarga_beverloo(1500, 0.002, 0.002)


def test_janssen_contra_integracion_numerica():
    rho, d, kk, mu = 1400.0, 4.0, 0.45, 0.4
    gamma, a_u = rho * 9.80665, d / 4
    # dpv/dz = γ − (K·μ/R)·pv  integrado por RK4
    pv, pasos = 0.0, 12000
    dz = 12.0 / pasos
    f = lambda p: gamma - kk * mu / a_u * p
    for _ in range(pasos):
        k1 = f(pv); k2 = f(pv + dz * k1 / 2); k3 = f(pv + dz * k2 / 2); k4 = f(pv + dz * k3)
        pv += dz * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    j = solidos.janssen(12.0, rho, d, kk, mu)
    assert j["pv"] == pytest.approx(pv, rel=1e-6)
    assert j["ph"] == pytest.approx(kk * pv, rel=1e-6)
    # Equilibrio global: peso = pv·A + n·U
    peso = gamma * 12.0 * math.pi * d ** 2 / 4
    assert j["pv"] * math.pi * d ** 2 / 4 + j["n_axial"] * math.pi * d == pytest.approx(peso, rel=1e-9)


def test_volumenes_troncos():
    assert solidos.volumen_tronco_cono(2, 0, 3) == pytest.approx(math.pi * 1 * 3 / 3)
    assert solidos.volumen_tronco_secciones_semejantes(4, 4, 2) == pytest.approx(8)


# --- Validación de campos -------------------------------------------------------
def test_campo_validacion():
    c = Campo("q", "Caudal", "m³/h", minimo=0, min_incluido=False)
    assert c.convertir("12,5") == 12.5
    for malo in ("", "abc", "0", "-3", "nan", "inf"):
        with pytest.raises(ErrorEntrada):
            c.convertir(malo)
    e = Campo("n", "Número", tipo="entero", defecto=0, minimo=0)
    assert e.convertir("014") == 14
    assert e.convertir("") == 0
    with pytest.raises(ErrorEntrada):
        e.convertir("2.5")
    o = Campo("m", "Material", tipo="opcion", opciones=("A", "B"), defecto="A")
    assert o.convertir("B") == "B"
    with pytest.raises(ErrorEntrada):
        o.convertir("Z")
