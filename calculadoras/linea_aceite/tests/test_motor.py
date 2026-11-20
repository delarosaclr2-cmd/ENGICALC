"""Línea de aceite: reproducción de PCGV-DM-017 con cálculo independiente, ASTM D341 y entradas inválidas."""
import json
import math
import os

import pytest

from linea_aceite.motor import ErrorEntrada, calcular, grado_iso
from linea_aceite.nucleo import aceite as ac

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
caso = lambda n: json.load(open(os.path.join(CASOS, n + ".json"), encoding="utf-8"))


def test_astm_d341_ejemplo_menon_6_6():
    a, b = ac.ajustar_walther(60 + 459.67, 750, 180 + 459.67, 25)    # °R
    assert a == pytest.approx(9.78, abs=0.01) and b == pytest.approx(3.43, abs=0.01)
    assert ac.viscosidad_cst(180 + 459.67, a, b) == pytest.approx(25, rel=1e-9)


def test_reynolds_formula_de_menon():
    r = calcular(caso("DM017_turbina_a_enfriador_4in"))
    D = r["d"] * 1000
    assert r["tramo"]["re"] == pytest.approx(353678 * r["q"] * 3600 / (r["nu"] * D), rel=1e-4)
    assert r["tramo"]["re"] == pytest.approx(16913, rel=3e-3)        # memoria (con D = 102.3 mm)


def test_retorno_laminar_f_64_re():
    r = calcular(caso("DM017_retorno_a_reservorio_1_5in"))
    t = r["tramo"]
    assert t["laminar"] and t["f"] == pytest.approx(64 / t["re"], rel=1e-12)
    assert t["f"] > 0.29                                              # la memoria usa 0.029 (error ×10)
    # Hagen-Poiseuille independiente: ΔP = 128·μ·L·Q/(π·D⁴)
    hp = 128 * r["mu"] * r["L"] * r["q"] / (math.pi * r["d"] ** 4)
    assert t["dp_tuberia"] == pytest.approx(hp, rel=1e-9)


def test_altura_en_columna_de_aceite():
    r = calcular(caso("DM017_turbina_a_enfriador_4in"))
    t = r["tramo"]
    assert t["dp_tuberia"] == pytest.approx(827 * 9.80665 * t["h_tuberia"], rel=1e-12)


def test_dos_puntos_no_son_un_grado_iso():
    r = calcular(caso("DM017_turbina_a_enfriador_4in"))
    assert r["nu40"] == pytest.approx(38.05, abs=0.05) and r["iso"] is None
    assert grado_iso(46) == "ISO VG 46" and grado_iso(32) == "ISO VG 32"


def test_espesor_b313_tabla():
    r = calcular(caso("DM017_turbina_a_enfriador_4in"))["espesor"]
    assert r["s_pa"] / 6894.757293168 == pytest.approx(20000, rel=1e-9)
    t = 101.526 * 4.5 / (2 * (20000 + 0.4 * 101.526))
    assert r["t_presion_m"] / 0.0254 == pytest.approx(t, rel=1e-3)


@pytest.mark.parametrize("cambio", [{"caudal": {"valor": -1, "unidad": "L/min"}},
                                    {"densidad": {"rho_kg_m3": 50}},
                                    {"viscosidad": {"modo": "dos_puntos", "t1_c": 40, "nu1_cst": 10, "t2_c": 80, "nu2_cst": 30}}])
def test_entradas_invalidas(cambio):
    with pytest.raises(ErrorEntrada):
        calcular(dict(caso("DM017_turbina_a_enfriador_4in"), **cambio))
