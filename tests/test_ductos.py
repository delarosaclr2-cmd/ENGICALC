"""Validación de ductos contra referencias publicadas.

1. Ejemplo de ducto redondo de 24 plg (610 mm), L = 100 ft (30 m), densidad estándar 0.075 lb/ft³
   (1.204 kg/m³), calculado con la ASHRAE Duct Fitting Database (presentación técnica ASHRAE, ETEK Chipre):
   - 4000 fpm: 0.71 plg c.a. con ε = 0.0003 ft (0.09 mm) y 1.09 plg c.a. con 10 veces la rugosidad;
   - 1000 fpm: 0.05 y 0.07 plg c.a.; en SI (20 m/s y 5 m/s, 30 m): 171/262 Pa y 13/17.7 Pa.
2. ACGIH, Industrial Ventilation, 31.ª ed., ec. 5.1 (citada en Processing Magazine): un sistema de
   3000 fpm a nivel del mar y 70 °F requiere 3282 fpm a 5000 ft de altitud.
"""
import math

import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import ductos as DU
from calculadoras.nucleo.modelo import ErrorEntrada

PLG_CA = 249.08891  # Pa por pulgada de columna de agua (a 4 °C)
GALV = "Medianamente liso — acero galvanizado, costura longitudinal o espiral (0.09 mm)"
RUGOSO_X10 = "Medianamente rugoso — fibra de vidrio rígido, espiral corrugado (0.9 mm)"


def calc(**cambios):
    datos = dict(CASOS["ductos"])
    datos.update(cambios)
    return POR_ID["ductos"].calcular(datos)


def ducto_610(v, longitud, material):
    caudal = math.pi / 4 * 0.6096 ** 2 * v * 3600
    return calc(caudal=caudal, velocidad=v, longitud=longitud, densidad=1.204, temperatura=20, friccion=0,
                rugosidad=0, material_ducto=material, velocidad_minima=0, k_accesorios=0)


@pytest.mark.parametrize("fpm, material, plg_ca", [
    (4000, GALV, 0.71), (4000, RUGOSO_X10, 1.09), (1000, GALV, 0.05), (1000, RUGOSO_X10, 0.07)])
def test_ashrae_dfdb_ducto_24_plg_unidades_inglesas(fpm, material, plg_ca):
    r = ducto_610(fpm * 0.3048 / 60, 30.48, material)
    assert r["diametro_mm"] == pytest.approx(609.6)
    assert r["dp_total_pa"] / PLG_CA == pytest.approx(plg_ca, abs=0.006)   # publicado con 2 decimales


# Los valores en Pa de la lámina a «5 m/s» coinciden con 1000 fpm (5.08 m/s), no con 5.00 m/s exactos
@pytest.mark.parametrize("v, material, pa", [(20, GALV, 171), (20, RUGOSO_X10, 262), (5.08, GALV, 13),
                                             (5.08, RUGOSO_X10, 17.7)])
def test_ashrae_dfdb_ducto_610_mm_si(v, material, pa):
    r = ducto_610(v, 30, material)
    assert r["dp_total_pa"] == pytest.approx(pa, rel=0.03)


def test_rugosidad_capturada_tiene_prioridad():
    r = ducto_610(20, 30, GALV)
    capt = calc(**{**dict(caudal=math.pi / 4 * 0.6096 ** 2 * 20 * 3600, velocidad=20, longitud=30,
                          densidad=1.204, friccion=0, material_ducto=GALV, velocidad_minima=0), "rugosidad": 0.9})
    assert capt["rugosidad"] == 0.9 and capt.salida("rugosidad").nivel == "D"
    assert capt["dp_total_pa"] > r["dp_total_pa"]
    assert any("Rugosidad capturada" in n for n in capt.notas)


def test_velocidad_minima_acgih_y_correccion_por_densidad():
    polvo_seco = next(k for k in DU.CONTAMINANTES if k.startswith("Polvos secos"))
    r = calc(contaminante=polvo_seco, velocidad_minima=0, densidad=0, altitud=1524, temperatura=21.11, velocidad=20)
    # Publicado: 3282 fpm (ACGIH usa su propia fórmula de altitud; diferencia < 0.5 %)
    assert r["velocidad_minima"] / (0.3048 / 60) == pytest.approx(3282, rel=5e-3)
    assert r["cumple_velocidad"] is True
    lento = calc(contaminante=polvo_seco, velocidad_minima=0, densidad=1.2014, velocidad=12)
    assert lento["velocidad_minima"] == pytest.approx(3000 * 0.3048 / 60, rel=1e-4)
    assert lento["cumple_velocidad"] is False and any("NO CUMPLE" in a for a in lento.advertencias)
    # El dato capturado tiene prioridad sobre la tabla
    capt = calc(contaminante=polvo_seco, velocidad_minima=25, velocidad=20)
    assert capt["velocidad_minima"] == 25 and capt["cumple_velocidad"] is False


def test_vapores_y_sin_verificacion():
    vapores = next(k for k in DU.CONTAMINANTES if k.startswith("Vapores"))
    r = calc(contaminante=vapores, velocidad_minima=0, velocidad=5)
    assert "velocidad_minima" not in r
    humos = next(k for k in DU.CONTAMINANTES if k.startswith("Humos"))
    r = calc(contaminante=humos, velocidad_minima=0, densidad=1.2014, velocidad=12)
    assert r["velocidad_minima"] == pytest.approx(2000 * 0.3048 / 60, rel=1e-4)
    with pytest.raises(ErrorEntrada):
        calc(contaminante="Arena")
