"""Validación de la característica requerida de la torre (Merkel).

1. Perry's Chemical Engineers' Handbook (ejemplo de KaV/L por Chebyshev, reproducido públicamente):
   agua 105 → 85 °F, bulbo húmedo 78 °F, L/G = 0.97; diferencias h_w − h_a publicadas en los tres primeros
   puntos de Chebyshev: 8.41, 10.91 y 13.33 Btu/lb (87, 93 y 97 °F).
2. Ejemplo de diseño publicado (curso de torres de enfriamiento, ejemplo 2): 110 → 84 °F, bulbo húmedo 69 °F,
   L/G = 1.30 → característica de la torre 1.49.
"""
import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import torre as T
from calculadoras.nucleo import psicrometria as ps
from calculadoras.nucleo.modelo import ErrorEntrada

BTU_LB = 2.326  # kJ/kg por Btu/lb


def f_a_c(f):
    return (f - 32) / 1.8


def calc(**cambios):
    datos = dict(CASOS["torre"])
    datos.update(cambios)
    return POR_ID["torre"].calcular(datos)


def test_perry_diferencias_de_entalpia():
    p = 101325.0
    h_in = ps.entalpia_saturacion(f_a_c(78), p)
    _, puntos = T.merkel_chebyshev(f_a_c(105), f_a_c(85), h_in, 0.97, 4.186, p)
    publicadas = (8.41, 10.91, 13.33)
    for (_, hw, ha), dh in zip(puntos, publicadas):
        assert (hw - ha) / BTU_LB == pytest.approx(dh, rel=0.01)


def test_ejemplo_de_diseno_kav_l():
    r = calc(t_entrada=f_a_c(110), t_salida=f_a_c(84), t_bulbo_humedo=f_a_c(69), relacion_lg=1.30, altitud=0,
             t_bulbo_seco=0, cp=4.186)
    assert r["kav_l"] == pytest.approx(1.49, rel=0.025)
    assert r["kav_l"] == pytest.approx(r["kav_l_simpson"], rel=0.01)
    assert r.salida("relacion_lg").nivel == "D"


def test_lg_desde_temperatura_de_salida_y_limites():
    r = calc()
    assert r["kav_l"] > 0 and r["relacion_lg"] == pytest.approx(10 / r["flujo_aire"])
    with pytest.raises(ErrorEntrada):          # L/G excesivo: la línea del aire cruza la saturación
        calc(relacion_lg=4.5)
