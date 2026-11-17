"""Validación de la banda transportadora.

1. MEKA, Crushing, Screening and Mining Equipment Handbook (tabla de capacidad volumétrica, reproducida en el
   blog técnico de MEKA): banda de 1 000 mm, rodillos laterales a 35°, talud dinámico 20°, horizontal, 2 m/s →
   V = 795 m³/h. Con la geometría ISO 5048 (b = 0.9·B − 0.05, rodillo central ISO 1537 de 380 mm) el resultado
   difiere < 3 % (MEKA usa el borde libre CEMA 0.055·B + 23 mm).
2. IS 11592:2000 (alineada con ISO 5048): b = 0.9·B − 0.05 (B ≤ 2 000 mm) y B − 0.25; tabla 9 de k;
   f básico 0.020; C = (L + L₀)/L con L₀ = 70–100 m (ISO 5048).
"""
import math

import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import banda as BA
from calculadoras.nucleo import constantes as K


def calc(**cambios):
    datos = dict(CASOS["banda"])
    datos.update(cambios)
    return POR_ID["banda"].calcular(datos)


def test_meka_capacidad_volumetrica_1000_mm():
    r = calc(ancho=1000, velocidad=2, angulo_artesa=35, angulo_sobrecarga=20, inclinacion=0, rodillo_central=0,
             ancho_util=0, llenado=1)
    assert r["ancho_util"] == pytest.approx(850)
    assert r["rodillo_central"] == pytest.approx(380)
    assert r["capacidad_m3h"] == pytest.approx(795, rel=0.03)
    # Ejemplo MEKA: caliza 1.5 t/m³ → 795 × 1.5 = 1 192.5 t/h en horizontal
    caliza = calc(ancho=1000, velocidad=2, angulo_artesa=35, angulo_sobrecarga=20, inclinacion=0, densidad=1500)
    assert caliza["capacidad_th"] == pytest.approx(795 * 1.5, rel=0.03)


def test_ancho_util_y_rodillo_iso():
    assert BA.ancho_util_iso(1.0) == pytest.approx(0.85)
    assert BA.ancho_util_iso(2.4) == pytest.approx(2.15)
    r = calc(ancho=1100)                     # no normalizado
    assert r["rodillo_central"] == pytest.approx((0.9 * 1.1 - 0.05) / 3 * 1000)
    assert any("no normalizado" in a for a in r.advertencias)


@pytest.mark.parametrize("ang, k", [(0, 1.0), (8, 0.97), (10, 0.95), (15, 0.90), (18, 0.85), (25, 0.68), (30, 0.56)])
def test_factor_pendiente_is_11592(ang, k):
    assert BA.factor_pendiente(ang) == pytest.approx(k)
    assert BA.factor_pendiente(-ang) == pytest.approx(k)


def test_coeficiente_c_y_f_iso_5048():
    assert BA.coeficiente_c_iso(200, 100) == pytest.approx(1.5)
    assert BA.coeficiente_c_iso(10000, 70) == pytest.approx(1.02)       # tope inferior C ≥ 1.02
    r = calc(coef_c=0, l0=100, longitud=200, f=BA.F_BASICO_ISO)
    assert r["coef_c"] == pytest.approx(1.5) and r.salida("coef_c").nivel == "E"
    corto = calc(coef_c=0, longitud=40)
    assert any("L < 80 m" in a for a in corto.advertencias)
    assert POR_ID["banda"].campo("f").defecto == 0.020


def test_potencia_con_c_iso_contra_calculo_a_mano():
    r = calc(coef_c=0, l0=100, longitud=300, inclinacion=0, f=0.02)
    qg = 1600 * r["area"]
    c = 400 / 300
    fu = c * 0.02 * 300 * K.G * (30 + 2 * 15 + qg)
    assert r["fuerza_tangencial"] == pytest.approx(fu / 1000)
    assert r["potencia_motor"] == pytest.approx(fu * 1.5 / 0.9 / 1000)
