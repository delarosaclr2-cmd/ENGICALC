"""Validación del soplador.

1. Ruta independiente por entalpía: P = ṁ·cp·T₁·[(p₂/p₁)^((k−1)/k) − 1]/η con ṁ = p₁·Q₁/(R·T₁)
   debe coincidir con la forma p₁·Q₁·k/(k−1)·[...] usada en el módulo.
2. Atlas Copco, «Screw versus Roots technology in low pressure blowers» (blog técnico): 2000 m³/h, 0.7 bar(g),
   35 °C; soplador de lóbulos: 60 kW de consumo y 125 °C a la salida. Con η = Q·Δp/60 kW el balance de energía
   da la temperatura de salida dentro de 5 °C (la carcasa real pierde calor).
"""
import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import soplador as S
from calculadoras.nucleo import constantes as K


def calc(**cambios):
    datos = dict(CASOS["soplador"])
    datos.update(cambios)
    return POR_ID["soplador"].calcular(datos)


@pytest.mark.parametrize("dp, t", [(5000, 20), (30000, 40), (80000, 0)])
def test_ruta_por_entalpia(dp, t):
    r = calc(presion=dp, temperatura=t)
    p1, q, k = 101325.0, 1000 / 3600, 1.4
    t1 = t + 273.15
    masa = p1 * q / (K.R_AIRE_SECO * t1)
    cp = k * K.R_AIRE_SECO / (k - 1)
    ideal = masa * cp * t1 * (((p1 + dp) / p1) ** ((k - 1) / k) - 1)
    assert r["potencia_adiabatica_kw"] == pytest.approx(ideal / 0.8 / 1000, rel=1e-9)
    assert r["t_descarga"] == pytest.approx(t + ideal / 0.8 / (masa * cp), rel=1e-9)
    assert r["potencia_eje_kw"] == r["potencia_adiabatica_kw"]


def test_lobulos_atlas_copco():
    q, dp = 2000.0, 70000.0
    eta = q / 3600 * dp / 60000.0                       # Q·Δp / consumo publicado
    r = calc(tipo_maquina=S.LOBULOS, caudal=q, presion=dp, temperatura=35, eficiencia=eta)
    assert r["potencia_eje_kw"] == pytest.approx(60.0, rel=1e-9)
    assert r["t_descarga"] == pytest.approx(125, abs=5)
    assert r["potencia_eje_kw"] > r["potencia_adiabatica_kw"]
    assert any("isocórica" in n for n in r.notas)
    assert not any("use la potencia adiabática" in a for a in r.advertencias)
