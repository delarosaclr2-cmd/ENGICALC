"""Validación de la revisión de vigas de acero contra ejemplos publicados.

Fuente: AISC «Design Examples v16.0» (First Semester Design Examples, aisc.org), con AISC 360-22.
Los ejemplos están en unidades de EE. UU.; aquí se convierten a SI y se comparan los resultados publicados.
"""
import math

import pytest

from calculadoras.calculos import POR_ID
from calculadoras.nucleo import acero

IN, FT, KIP, KSI = 0.0254, 0.3048, 4448.2216152605, 6.894757293168e6
KIPFT = KIP * FT
G = 9.80665

W18X50 = dict(d=18.0, bf=7.50, tf=0.570, tw=0.355, A=14.7, Ix=800, Zx=101, Sx=88.9, Iy=40.1, J=1.24, Cw=3040)
W21X48 = dict(d=20.6, bf=8.14, tf=0.430, tw=0.350, Ix=959, Zx=107, Sx=93.0)
W24X62 = dict(d=23.7, bf=7.04, tf=0.590, tw=0.430)
FY50 = 50 * KSI


def props_si(s):
    p = acero.propiedades_i(s["d"] * IN, s["bf"] * IN, s["tf"] * IN, s["tw"] * IN)
    for k, f in (("A", IN ** 2), ("Ix", IN ** 4), ("Zx", IN ** 3), ("Sx", IN ** 3), ("Iy", IN ** 4), ("J", IN ** 4), ("Cw", IN ** 6)):
        if k in s:
            p[k] = s[k] * f
    return acero.completar_i(p)


def entradas_viga(s, span_ft, w_servicio_kft, factor, soporte, tramos=2):
    """Viga simplemente apoyada con carga uniforme; propiedades del manual capturadas en cm."""
    cm = 1e-2
    return dict(
        tipo="Simplemente apoyada (apoyos en x = 0 y x = L)", longitud=span_ft * FT, carga_puntual=0, posicion=0,
        carga_distribuida=w_servicio_kft * KIP / FT / G, material="Acero", modulo=29000 * KSI / 1e9,
        seccion="I simétrica", b=s["bf"] * IN * 1e3, h=s["d"] * IN * 1e3, tf=s["tf"] * IN * 1e3,
        tw=s["tw"] * IN * 1e3, fabricacion="Laminado (rolado)",
        area_manual=s.get("A", 0) * (IN / cm) ** 2, ix_manual=s.get("Ix", 0) * (IN / cm) ** 4, zx_manual=s.get("Zx", 0) * (IN / cm) ** 3,
        sx_manual=s.get("Sx", 0) * (IN / cm) ** 3, iy_manual=s.get("Iy", 0) * (IN / cm) ** 4,
        j_manual=s.get("J", 0) * (IN / cm) ** 4, cw_manual=s.get("Cw", 0) * (IN / cm) ** 6,
        norma="AISC 360-22 (LRFD)", fy=50 * KSI / 1e6, factor_carga=factor, soporte=soporte, tramos=tramos)


# F.1: W18x50, L = 35 ft, D = 0.45 k/ft, L = 0.75 k/ft -> wu = 1.74 k/ft, Mu = 266 kip-ft
SERV, FACT = 1.20, 1.74 / 1.20


def test_f11b_continuamente_arriostrada():
    r = POR_ID["viga"].calcular(entradas_viga(W18X50, 35, SERV, FACT, "Continuo (losa o cubierta conectada)"))
    assert r["aisc_mp"] * 1e3 / KIPFT == pytest.approx(421, abs=1)       # Mp = 421 kip-ft
    assert r["aisc_phimn"] * 1e3 / KIPFT == pytest.approx(379, abs=1)    # φMn = 379 kip-ft
    assert r["aisc_mu"] * 1e3 / KIPFT == pytest.approx(266, abs=1)       # Mu = 266 kip-ft


def test_f12b_arriostrada_en_tercios():
    r = POR_ID["viga"].calcular(entradas_viga(W18X50, 35, SERV, FACT,
                                              "En puntos equidistantes (capturar número de tramos)", 3))
    assert r["aisc_lp"] / FT == pytest.approx(5.83, abs=0.02)            # Lp = 5.83 ft
    assert r["aisc_lr"] / IN == pytest.approx(203, abs=1)                # Lr = 203 in (16.9 ft)
    assert r["aisc_cb"] == pytest.approx(1.01, abs=0.005)                # Cb tramo central
    # El ejemplo redondea Cb = 1.01 (exacto 1.0135), Lb = 11.7 ft y Lr = 16.9 ft: diferencia < 1 %
    assert r["aisc_mn"] * 1e3 / KIPFT == pytest.approx(338, rel=0.01)    # Mn = 338 kip-ft
    assert r["aisc_phimn"] * 1e3 / KIPFT == pytest.approx(304, rel=0.01)
    # con los mismos valores redondeados del ejemplo se reproduce el resultado publicado
    out = acero.aisc_flexion_i(props_si(W18X50), FY50, 11.7 * FT, 1.01)
    assert out["Mn"] / KIPFT == pytest.approx(338, abs=1)


def test_f13b_arriostrada_al_centro_pandeo_elastico():
    r = POR_ID["viga"].calcular(entradas_viga(W18X50, 35, SERV, FACT,
                                              "En puntos equidistantes (capturar número de tramos)", 2))
    assert r["aisc_cb"] == pytest.approx(1.30, abs=0.005)
    assert "elástico" in r["aisc_controla"]
    assert r["aisc_mn"] * 1e3 / KIPFT == pytest.approx(320, rel=0.005)   # Mn = 320 kip-ft (Fcr = 43.2 ksi)
    assert r["aisc_phimn"] * 1e3 / KIPFT == pytest.approx(288, rel=0.005)
    p = props_si(W18X50)
    out = acero.aisc_flexion_i(p, FY50, 17.5 * FT, 1.30)
    assert out["Fcr"] / KSI == pytest.approx(43.2, abs=0.1)


def test_f3b_patin_no_compacto():
    # W21x48, L = 40 ft, continuamente arriostrada; Mu = 396 kip-ft; Mn = 442 kip-ft
    p = props_si(W21X48)
    out = acero.aisc_flexion_i(p, FY50, 0.0, 1.0)
    assert out["clasificacion"]["lam_f"] == pytest.approx(9.47, abs=0.01)
    assert out["clasificacion"]["lpf"] == pytest.approx(9.15, abs=0.01)
    assert out["clasificacion"]["lrf"] == pytest.approx(24.1, abs=0.05)
    assert out["Mp"] / KIPFT == pytest.approx(446, abs=1)
    assert out["Mn"] / KIPFT == pytest.approx(442, abs=1)
    assert out["phiMn"] / KIPFT == pytest.approx(398, abs=1)


def test_g1b_cortante_alma():
    p = props_si(W24X62)
    v = acero.aisc_cortante_i(p, FY50, laminado=True)
    assert v["Aw"] / IN ** 2 == pytest.approx(10.2, abs=0.05)
    assert v["Cv1"] == 1.0 and v["phi"] == 1.0
    assert v["phiVn"] / KIP == pytest.approx(306, abs=1)                 # φVn = 306 kips


def test_ntc_coincide_con_la_teoria_clasica():
    """Me de la NTC (ec. 6.3.4) es el momento crítico clásico; con Cw = Iy·ho²/4 y G = E/2.6 debe coincidir
    con Fcr·Sx de AISC F2-4 (que se deduce de la misma expresión)."""
    p = acero.propiedades_i(0.4572, 0.1905, 0.014478, 0.009017)
    for lb in (4.0, 6.0, 9.0):
        me = acero.ntc_me(p, lb, 1.0, e=acero.E_AISC, g=acero.E_AISC / 2.6)
        rel = lb / p["rts"]
        fcr = math.pi ** 2 * acero.E_AISC / rel ** 2 * math.sqrt(1 + 0.078 * p["J"] / (p["Sx"] * p["ho"]) * rel ** 2)
        assert me == pytest.approx(fcr * p["Sx"], rel=1e-3)


def test_ntc_limites_y_continuidad():
    p = props_si(W18X50)
    fy = 345e6
    cont = acero.ntc_flexion_i(p, fy, 0.0, 1.0)
    assert cont["MR"] == pytest.approx(0.9 * fy * p["Zx"])
    # continuidad en Me = 2/3·Mp: 1.15·Mp·(1 − 0.28·1.5) = 0.667·Mp
    assert 1.15 * (1 - 0.28 * 1.5) == pytest.approx(2 / 3, abs=0.001)
    largo = acero.ntc_flexion_i(p, fy, 15.0, 1.0)
    assert largo["Mn"] == pytest.approx(largo["Me"]) and "elástico" in largo["controla"]
    medio = acero.ntc_flexion_i(p, fy, 3.0, 1.0)
    assert medio["Me"] > 2 / 3 * medio["Mp"] and medio["Mn"] < medio["Mp"]


def test_viga_aisc_y_ntc_en_unidades_mexicanas():
    """Caso ordinario: IR 457 × 74.5 (W18x50) de 6 m, A992, ambas normas, soporte solo en apoyos."""
    s = W18X50
    datos = entradas_viga(s, 6 / FT, 0, 1.4, "Solo en apoyos (sin soportes intermedios)")
    datos.update(longitud=6.0, carga_distribuida=2000, norma="AISC 360-22 y NTC-DCEA", fy=345)
    r = POR_ID["viga"].calcular(datos)
    for clave in ("aisc_phimn", "aisc_rel_m", "aisc_phivn", "ntc_mr", "ntc_rel_m", "ntc_vr"):
        assert clave in r and r[clave] > 0
    assert r["aisc_cb"] == pytest.approx(1.136, abs=0.002)               # carga uniforme, sin soportes: Cb = 1.14
    # las dos normas dan resistencias del mismo orden (difieren en E, G y en la forma de la curva inelástica)
    assert r["ntc_mr"] == pytest.approx(r["aisc_phimn"], rel=0.15)


def test_viga_norma_requiere_datos():
    from calculadoras.nucleo.modelo import ErrorEntrada

    datos = entradas_viga(W18X50, 35, SERV, FACT, "Continuo (losa o cubierta conectada)")
    with pytest.raises(ErrorEntrada, match="Fy"):
        POR_ID["viga"].calcular(dict(datos, fy=0))
    with pytest.raises(ErrorEntrada, match="factor de carga"):
        POR_ID["viga"].calcular(dict(datos, factor_carga=0))
    with pytest.raises(ErrorEntrada, match="acero"):
        POR_ID["viga"].calcular(dict(datos, material="Madera", modulo=0))


def test_voladizo_usa_cb_1():
    datos = entradas_viga(W18X50, 10, 1.0, 1.4, "Solo en apoyos (sin soportes intermedios)")
    datos.update(tipo="Voladizo (empotrada en x = 0)")
    r = POR_ID["viga"].calcular(datos)
    assert r["aisc_cb"] == 1.0
