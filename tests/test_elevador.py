"""Validación de la potencia del elevador de cangilones contra la guía KWS (Bucket Elevator Engineering Guide,
«Horsepower Calculation»): P [HP] = G·(DH + Leq·d)/(33 000·60), G en lb/h, DH y d en ft, Leq 5–15.
Ejemplo KWS: 100 000 lb/h de arena, DH = 105 ft, d = 2 ft, Leq = 7 → P = 100 000·119/1 980 000 = 6.01 HP.
"""
import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.nucleo import constantes as K


def calc(**cambios):
    datos = dict(CASOS["elevador"])
    datos.update(cambios)
    return POR_ID["elevador"].calcular(datos)


def kws_hp(g_lbh, dh_ft, d_ft, leq):
    return g_lbh * (dh_ft + leq * d_ft) / (33000 * 60)


def test_ejemplo_kws_arena():
    assert kws_hp(100000, 105, 2, 7) == pytest.approx(6.01, abs=0.005)


def test_si_equivale_a_la_formula_kws():
    r = calc(altura=105 * 0.3048, leq=7, diametro_cola=2 * 304.8, eficiencia=1.0)
    g_lbh = r["capacidad_th"] * 1000 / K.KG_POR_LIBRA
    esperado = kws_hp(g_lbh, 105, 2, 7) * K.W_POR_HP / 1000
    assert r["potencia_elevacion"] == pytest.approx(esperado, rel=1e-9)
    assert r["altura_dragado"] == pytest.approx(7 * 0.6096)


def test_altura_capturada_tiene_prioridad():
    r = calc(altura_carga=6)
    assert r["altura_dragado"] == 6 and r.salida("altura_dragado").nivel == "D"
    assert any("capturada" in n for n in r.notas)
