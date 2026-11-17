"""Validación del transportador helicoidal (método CEMA en la forma publicada por KWS).

Casos de referencia publicados por KWS Manufacturing, Screw Conveyor Engineering Guide:

1. «Screw Conveyor Example» — harina de maíz, 25 600 lb/h, 32–40 lb/ft³ (se usa 32), carga 30A,
   16 ft, horizontal, cojinete de madera (HBF 1.7), MF 0.5, e = 0.88.
   Publicado: tornillo de 12 plg (1 161 ft³/h a 90 rpm; 12.9 ft³/h a 1 rpm), 62 rpm, MHP = 0.21 HP,
   MHP corregido (gráfica) = 0.5 HP, motor de 1 HP.
2. «Screw Conveyor Capacity» — cal viva, 10 ton/h (20 000 lb/h), 60 lb/ft³ → 333 ft³/h, carga 30A,
   paso corto (CF1 = 1.50), hélice cortada y doblada (CF2 = 3.75).
   Publicado: SC = 1 873 ft³/h, tornillo de 16 plg (31.2 ft³/h a 1 rpm; 2 496 ft³/h a 80 rpm), 60 rpm.
   «Screw Conveyor Horsepower» (mismo ejemplo): SF = 1.50 para hélice cortada y doblada con 30 %.
"""
import math

import pytest

from casos import CASOS
from calculadoras.calculos import POR_ID
from calculadoras.calculos import helicoidal as H
from calculadoras.nucleo import constantes as K
from calculadoras.nucleo.modelo import VALIDADA_CONDICIONES, ErrorEntrada

LB = K.KG_POR_LIBRA


def calc(**cambios):
    datos = dict(CASOS["helicoidal"])
    datos.update(cambios)
    return POR_ID["helicoidal"].calcular(datos)


def ejemplo_maiz(**cambios):
    datos = dict(material="Harina de maíz (corn meal)", capacidad=25600 * LB / 1000, longitud=16 * K.M_POR_PIE,
                 cojinete="Bronce o madera", eficiencia=88, mhp_corregido=0.5)
    datos.update(cambios)
    return calc(**datos)


def test_ejemplo_kws_harina_de_maiz():
    r = ejemplo_maiz()
    assert r["densidad_lbft3"] == pytest.approx(32)
    assert r["clase_carga"] == "30 % (30A)"
    assert r["cfh"] == pytest.approx(800, rel=1e-9)                     # 25 600 / 32
    assert r["diametro"] == 12                                          # selección automática = publicada
    assert (r["capacidad_maxima"], r["rpm_maxima"], r["capacidad_1rpm"]) == (1161, 90, 12.9)
    assert r["rpm"] == pytest.approx(62, abs=0.05)                      # publicado: 62 rpm
    assert r["mhp"] == pytest.approx(0.21, abs=0.006)                   # publicado: 0.21 HP
    # Cálculo independiente de FHP y TSHP (las ecuaciones están en la guía KWS)
    fhp = 16 * (800 / 12.9) * 55 * 1.7 / 1e6
    assert r["fhp"] == pytest.approx(fhp, rel=1e-9)
    assert r["tshp"] == pytest.approx((fhp + 0.5) / 0.88, rel=1e-9)     # ≈ 0.674 HP
    assert r["tshp"] == pytest.approx(0.674, abs=0.001)
    # KWS eligió 1 HP; la regla «siguiente tamaño NEMA» da 0.75 HP (ambos ≥ TSHP)
    assert r["motor_hp"] == 0.75 and r["motor_hp"] >= r["tshp"]
    assert r["par_motor"] == pytest.approx(63025 * 0.75 / r["rpm"])
    assert r["cumple"] is True
    assert r.salida("tshp").nivel == "E"


def test_ejemplo_kws_par_del_motor_publicado():
    """Con el motor publicado (1 HP) a 60 rpm el par es 1 050 lbf·plg, menor que las capacidades publicadas
    para flecha de 2 plg (9 500), tornillos de acople (19 000) y tubo de 2-1/2 plg (8 900 en aplastamiento)."""
    par = H.PAR_HP_RPM * 1 / 60
    assert par == pytest.approx(1050.4, abs=0.1)
    assert par < min(9500, 19000, 14200, 8900)


def test_ejemplo_kws_cal_viva_capacidad_especial():
    r = calc(material=H.OTRO, densidad=60 * K.KGM3_POR_LBPIE3, factor_material=2.0, carga="30 % (clase 30A)",
             capacidad=20000 * LB / 1000, paso="Corto (paso = 2/3 D)", helice=H.CORTADA_DOBLADA, longitud=15 * 0.3048)
    assert r["cfh"] == pytest.approx(333.33, rel=1e-4)
    assert (r["cf1"], r["cf2"], r["cf3"]) == (1.50, 3.75, 1.00)
    assert r["sc"] == pytest.approx(1873, rel=2e-3)                     # publicado con CFH redondeado a 333
    assert r["diametro"] == 16
    assert r["capacidad_1rpm"] == 31.2 and r["capacidad_maxima"] == 2496
    assert r["rpm"] == pytest.approx(60, abs=0.2)                       # publicado: 60 rpm
    assert r["sf"] == 1.50
    assert r["mhp"] == pytest.approx(20000 * 15 * 2.0 * 1.50 / 1e6, rel=1e-6)


def test_fo_cema_aproximado():
    assert H.fo_cema_aproximado(10) == 1.0
    assert H.fo_cema_aproximado(5.2) == 1.0
    assert H.fo_cema_aproximado(0.1) == 3.0
    assert H.fo_cema_aproximado(0.2) == pytest.approx(3.0)
    assert H.fo_cema_aproximado(math.sqrt(0.2 * 5.2)) == pytest.approx(2.0)   # punto medio logarítmico
    valores = [H.fo_cema_aproximado(x) for x in (0.3, 0.5, 1, 2, 4)]
    assert valores == sorted(valores, reverse=True)


def test_cema_con_fo_aproximado_y_capturado():
    r = ejemplo_maiz(mhp_corregido=0)
    base = r["fhp"] + r["mhp"]
    assert r["fo"] == pytest.approx(H.fo_cema_aproximado(base))
    assert r["tshp"] == pytest.approx(base * r["fo"] / 0.88)
    assert any("aproximación" in a for a in r.advertencias)
    assert r.salida("fo").nivel == "E"
    r = ejemplo_maiz(mhp_corregido=0, factor_sobrecarga=2.0)
    assert r["tshp"] == pytest.approx(base * 2.0 / 0.88)
    assert r.salida("fo").nivel == "D"
    with pytest.raises(ErrorEntrada):
        ejemplo_maiz(mhp_corregido=0, factor_sobrecarga=0.8)
    with pytest.raises(ErrorEntrada):          # MHP corregido menor que el calculado
        ejemplo_maiz(mhp_corregido=0.1)


def test_potencia_grande_sin_sobrecarga():
    r = calc(capacidad=200, longitud=30)
    assert r["fhp"] + r["mhp"] > 5.2
    assert r["fo"] == 1.0
    assert not any("aproximación" in a for a in r.advertencias)


def test_seleccion_y_limites_de_diametro():
    # Diámetro manual insuficiente: avisa y sugiere el mínimo
    r = ejemplo_maiz(diametro="9 plg")
    assert r["cumple"] is False
    assert any("NO CUMPLE" in a and "12 plg" in a for a in r.advertencias)
    # Capacidad excesiva para la tabla
    with pytest.raises(ErrorEntrada):
        calc(capacidad=5000)
    # Hélices no recomendadas («X» de KWS)
    with pytest.raises(ErrorEntrada):
        calc(material="Alúmina (alumina)", helice=H.CORTADA_DOBLADA, diametro="12 plg")   # 15 %
    with pytest.raises(ErrorEntrada):
        calc(helice=H.LISTON, diametro="4 plg")
    r = calc(helice=H.LISTON, capacidad=0.2)                           # automático salta el de 4 plg
    assert r["diametro"] >= 6
    assert r["cf2"] == H.CF2_LISTON[r["diametro"]][1]


def test_datos_de_catalogo_y_material():
    r = ejemplo_maiz(diametro="12 plg", capacidad_rpm=13.5, rpm_maxima=100)
    assert r["rpm"] == pytest.approx(800 / 13.5)
    assert r.salida("capacidad_1rpm").nivel == "D"
    with pytest.raises(ErrorEntrada):          # catálogo sin diámetro elegido
        ejemplo_maiz(capacidad_rpm=13.5)
    with pytest.raises(ErrorEntrada):          # «Otro» sin datos
        calc(material=H.OTRO)
    r = calc(material="Azúcar granulada seca (sugar, granulated dry)")
    assert r["mf"] == 1.2                       # intervalo 1.0–1.2: se usa el mayor
    r = calc(densidad=3000)
    assert any("fuera del intervalo" in a for a in r.advertencias)
    r = calc(carga="45 %")
    assert any("difiere" in a for a in r.advertencias)


def test_paletas_y_paso():
    base = calc()
    r = calc(paletas=2, paso="Medio (paso = 1/2 D)")
    assert r["sc"] == pytest.approx(base["cfh"] * 2.00 * 1.16)
    assert r["pf"] == 1.58
    assert r["mhp"] == pytest.approx(base["mhp"] * 1.58)


def test_inclinacion():
    r = calc(angulo=8)
    assert any("10°" in a for a in r.advertencias)
    assert r["potencia_elevacion"] == pytest.approx(10 * 1000 / 3600 * K.G * 6 * math.sin(math.radians(8)) / 1000)
    with pytest.raises(ErrorEntrada):
        calc(angulo=20)
    r = calc(angulo=20, eficiencia_inclinacion=0.7, factor_inclinacion=1.4)
    horizontal = calc()
    assert r["sc"] == pytest.approx(horizontal["sc"] / 0.7)
    assert r["fi"] == 1.4
    with pytest.raises(ErrorEntrada):
        calc(angulo=60)
    with pytest.raises(ErrorEntrada):
        calc(angulo=20, eficiencia_inclinacion=0.7, factor_inclinacion=0.9)


def test_estado_documentado():
    c = POR_ID["helicoidal"]
    assert c.estado_validacion == VALIDADA_CONDICIONES
    assert any("KWS" in ref for ref in c.referencias)
