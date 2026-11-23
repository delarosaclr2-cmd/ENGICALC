"""Línea de vapor: reproducción de PCGV-DM-011, ΔP contra un cálculo independiente y entradas inválidas."""
import json
import math
import os

import pytest

from linea_vapor.motor import FT3_LB, ErrorEntrada, calcular

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
caso = lambda n: json.load(open(os.path.join(CASOS, n + ".json"), encoding="utf-8"))


@pytest.mark.parametrize("n,v_memo", [("DM011_principal_cog_V_VI_a_M3_12in", 33.18), ("DM011_cogeneracion_V_VI_8in", 37.13),
                                      ("DM011_auxiliar_maquinas_1_2_6in", 22.05)])
def test_velocidades_de_la_memoria(n, v_memo):
    r = calcular(caso(n))
    assert r["e1"].v / FT3_LB == pytest.approx(1.6256, abs=5e-4)     # tablas de vapor de la memoria
    assert r["v1"] == pytest.approx(v_memo, abs=0.02)


def test_silenciador_di_corregido_y_acfm():
    r = calcular(caso("DM011_silenciador_10in"))
    assert r["v1"] == pytest.approx(37.55 * (9.27 / 10.02) ** 2, rel=2e-3)   # 32.1 m/s, no 37.5
    vt = r["venteo"]
    assert vt["estado"].v / FT3_LB == pytest.approx(31.4, abs=0.05)          # memoria: 31.4 ft³/lb
    assert vt["acfm"] == pytest.approx(66917, rel=2e-3)


def test_dp_contra_darcy_de_un_paso():
    c = dict(caso("DM011_principal_cog_V_VI_a_M3_12in"), longitud_m=20)
    r = calcular(c)
    G, e1 = r["G"], r["e1"]
    un_paso = r["f1"] * 20 / r["d"] * G * G * e1.v / 2
    assert r["dp"] == pytest.approx(un_paso, rel=5e-3)            # ΔP pequeña: densidad casi constante


def test_dp_coolprop_integracion_independiente():
    cp = pytest.importorskip("CoolProp.CoolProp")
    c = caso("ESCENARIO_principal_12in_150m")
    r = calcular(c)
    h = cp.PropsSI("H", "P", r["e1"].p, "Q", 1, "Water")
    p, G, d, n = r["e1"].p, r["G"], r["d"], 400
    K = r["k_total"]
    for _ in range(n):
        rho = cp.PropsSI("D", "P", p, "H", h, "Water")
        mu = cp.PropsSI("V", "P", p, "H", h, "Water")
        re = G * d / mu
        f = 0.02
        for _ in range(60):
            f = (-2 * math.log10(r["eps"] / d / 3.7 + 2.51 / (re * math.sqrt(f)))) ** -2
        p -= (f * 150 / n / d + K / n) * G * G / rho / 2
    assert r["e1"].p - r["e2"].p == pytest.approx(r["e1"].p - p, rel=5e-3)


def test_espesor_igual_a_la_memoria():
    r = calcular(caso("DM011_principal_cog_V_VI_a_M3_12in"))["espesor"]
    assert r["t_m_m"] / 0.0254 == pytest.approx(0.1763, abs=1e-4)


def test_sobrecalentado_bajo_saturacion_rechazado():
    c = dict(caso("DM011_principal_cog_V_VI_a_M3_12in"), estado="sobrecalentado", temperatura_c=200)
    with pytest.raises(ErrorEntrada, match="satura"):
        calcular(c)


def test_flujo_cero_rechazado():
    with pytest.raises(ErrorEntrada):
        calcular(dict(caso("DM011_cogeneracion_V_VI_8in"), flujo={"valor": 0, "unidad": "kg/h"}))
