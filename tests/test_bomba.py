"""Validación de la bomba centrífuga contra referencias publicadas.

- Crane TP-410 (ed. 2009): tabla «Pipe friction data for Schedule 40 clean commercial steel pipe with flow in
  zone of complete turbulence» (f_T por diámetro nominal), reproducida públicamente; Pumps & Systems,
  «Understand how valves & fittings affect head loss» (R. Hardee): f_T = 0.016 (4 plg) y 0.015 (6 plg),
  válvula de globo L/D = 340.
- J. Elsey, «NPSHa Basics», Pumps & Systems (2022), ejemplos 1 a 3:
  1) succión ahogada abierta, agua a 68 °F, +10 ft estática, 3.2 ft fricción → NPSHa = 40 ft;
  2) succión negativa −10 ft → 20 ft;  3) agua a 212 °F (GE 0.958) → 6.8 ft.
"""
import math

import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import bomba as B
from calculadoras.nucleo import constantes as K
from calculadoras.nucleo.modelo import ErrorEntrada

# Diámetro interior cédula 40 [plg] y f_T publicado por Crane (ed. 2009)
CRANE_FT = [(0.622, 0.026), (0.824, 0.024), (1.049, 0.022), (2.067, 0.019), (3.068, 0.017), (4.026, 0.016),
            (6.065, 0.015), (7.981, 0.014), (11.938, 0.013), (22.626, 0.011)]


def calc(**cambios):
    datos = dict(CASOS["bomba"])
    datos.update(cambios)
    return POR_ID["bomba"].calcular(datos)


@pytest.mark.parametrize("d_int, ft_crane", CRANE_FT)
def test_ft_contra_tabla_crane(d_int, ft_crane):
    # La tabla publica f_T redondeado a 3 decimales (ε = 0.0018 plg, acero comercial)
    assert B.friccion_turbulencia_completa(0.0018, d_int) == pytest.approx(ft_crane, abs=7e-4)


def test_k_valvula_de_globo_pumps_and_systems():
    ft4 = B.friccion_turbulencia_completa(0.0018, 4.026)
    assert ft4 == pytest.approx(0.016, abs=5e-4)
    assert B.VALVULAS["Globo, abierta (L/D 340)"] * ft4 == pytest.approx(340 * 0.016, rel=0.03)   # 5.44


def test_k_crane_en_la_altura_total():
    accesorios = dict(codos=3, codos_rl=2, codos_45=1, tees=1, tees_paso=2, valvulas=2,
                      tipo_valvula="Bola, paso completo (L/D 3)", retenciones=1, entradas=1, salidas=1,
                      reducciones=0, k_codo=0, k_valvula=0, k_tee=0, cribas=0)
    r = calc(**accesorios)
    ft = B.friccion_turbulencia_completa(0.0018, 8)
    k_total = ft * (3 * 30 + 2 * 20 + 16 + 60 + 2 * 20 + 2 * 3 + 100) + 0.5 + 1.0
    v = 1234 * K.PIE3S_POR_GPM / (math.pi * (8 / 12) ** 2 / 4)
    assert r["friccion_ft"] == pytest.approx(ft)
    assert r["k_total"] == pytest.approx(k_total)
    assert r["h_accesorios"] == pytest.approx(k_total * v ** 2 / (2 * K.G_PIES))
    assert r.salida("h_accesorios").nivel == "E"
    # K capturado sustituye al valor Crane y se informa
    capt = calc(**dict(accesorios, k_codo=0.75))
    assert capt["k_total"] == pytest.approx(k_total + 3 * (0.75 - 30 * ft))
    assert capt.salida("h_accesorios").nivel == "D"
    assert any("K capturado" in n for n in capt.notas)
    # Reducciones con el K original: nivel O y advertencia
    red = calc(**dict(accesorios, reducciones=1))
    assert red.salida("h_accesorios").nivel == "O"
    assert any("reducciones" in a for a in red.advertencias)


@pytest.mark.parametrize("cambios, esperado", [
    (dict(temperatura=20, ge=1.0, elevacion_succion=10), 40.0),     # ejemplo 1
    (dict(temperatura=20, ge=1.0, elevacion_succion=-10), 20.0),    # ejemplo 2
    (dict(temperatura=100, ge=0.958, elevacion_succion=10), 6.8),   # ejemplo 3
])
def test_npsha_ejemplos_pumps_and_systems(cambios, esperado):
    r = calc(altitud=0, presion_succion=0, presion_vapor=0, perdidas_succion=3.2, **cambios)
    # Diferencias < 0.1 ft: el artículo redondea 14.7 psia × 2.31 y la presión de vapor
    assert r["npsha"] == pytest.approx(esperado, abs=0.1)


def test_npsha_con_presion_de_vapor_capturada():
    r = calc(altitud=0, presion_succion=0, presion_vapor=14.696, ge=0.958, elevacion_succion=10, perdidas_succion=3.2)
    assert r["npsha"] == pytest.approx(6.8, abs=1e-3)


def test_entradas_invalidas():
    with pytest.raises(ErrorEntrada):
        calc(tipo_valvula="Cuchilla")
    with pytest.raises(ErrorEntrada):
        calc(retenciones=-1)
    assert any("mariposa" in a for a in calc(valvulas=1, tipo_valvula="Mariposa ≤ 8 plg (L/D 45)",
                                             diametro=10).advertencias)
