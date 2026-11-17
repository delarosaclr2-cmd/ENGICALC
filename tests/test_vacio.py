"""Validación de la potencia de la bomba de vacío por rutas independientes.

- Adiabática: P = ṁ·cp·T₁·[(pd/ps)^((k−1)/k) − 1] con ṁ = ps·Qs/(R·T₁).
- Isotérmica: integral numérica de V·dp = ∫ ps·Qs/p dp (trapecios en escala logarítmica).
"""
import math

import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.nucleo import constantes as K


def calc(**cambios):
    datos = dict(CASOS["vacio"])
    datos.update(cambios)
    return POR_ID["vacio"].calcular(datos)


@pytest.mark.parametrize("ps_kpa, t", [(10, 20), (50, 35), (1, 0)])
def test_potencias_por_rutas_independientes(ps_kpa, t):
    r = calc(presion_succion=ps_kpa, temperatura=t, altitud=0, presion_descarga=0)
    q = 100 * K.M3S_POR_CFM
    ps, pd, k = ps_kpa * 1000, 101325.0, 1.4
    masa = ps * q / (K.R_AIRE_SECO * (t + 273.15))
    cp = k * K.R_AIRE_SECO / (k - 1)
    adi = masa * cp * (t + 273.15) * ((pd / ps) ** ((k - 1) / k) - 1)
    assert r["potencia_teorica_kw"] == pytest.approx(adi / 1000, rel=1e-9)
    n = 20000
    xs = [math.log(ps) + (math.log(pd) - math.log(ps)) * i / n for i in range(n + 1)]
    integral = sum((ps * q) * (xs[i + 1] - xs[i]) for i in range(n))   # V·dp = ps·Q·d(ln p)
    assert r["potencia_isotermica_kw"] == pytest.approx(integral / 1000, rel=1e-9)
    assert r["potencia_isotermica_kw"] < r["potencia_teorica_kw"]
