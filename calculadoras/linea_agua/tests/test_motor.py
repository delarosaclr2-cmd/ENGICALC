"""Línea de agua: reproducción de PCGV-DM-012 con cálculo independiente y entradas inválidas."""
import glob
import json
import math
import os

import pytest

from linea_agua.motor import ErrorEntrada, calcular

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
caso = lambda n: json.load(open(os.path.join(CASOS, n + ".json"), encoding="utf-8"))


def _colebrook(re, er):
    f = 0.02
    for _ in range(200):
        f = (-2 * math.log10(er / 3.7 + 2.51 / (re * math.sqrt(f)))) ** -2
    return f


@pytest.mark.parametrize("n,q,di,L,h_memo", [
    ("DM012_TQ_condensado_a_deareador_descarga_6in", 88.655, 6.065, 71.44, 0.659),
    ("DM012_deareador_a_HRSG_descarga_4in", 44.325, 4.026, 78.87, 1.604),
    ("DM012_deareador_a_HRSG_succion_6in", 44.325, 6.065, 12.661, 0.0324)])
def test_darcy_independiente(n, q, di, L, h_memo):
    r = calcular(caso(n))
    t = r["tramo"]
    D = di * 0.0254
    v = q / 3600 / (math.pi / 4 * D * D)
    re = v * D * r["rho"] / r["mu"]
    f = _colebrook(re, 0.045e-3 / D)
    h = f * L / D * v * v / (2 * 9.80665)
    assert t["v"] == pytest.approx(v, rel=1e-12)
    assert t["f"] == pytest.approx(f, rel=1e-9)
    assert t["h_tuberia"] == pytest.approx(h, rel=1e-9)
    assert t["h_tuberia"] == pytest.approx(h_memo, rel=0.06)       # la memoria con f del diagrama de Moody


def test_propiedades_agua_90C():
    r = calcular(caso("DM012_deareador_a_HRSG_descarga_4in"))
    assert r["rho"] == pytest.approx(965.3, abs=0.05)                # IAPWS: 965.30 kg/m³
    assert r["mu"] / r["rho"] * 1e6 == pytest.approx(0.3255, abs=2e-4)   # cSt (la memoria escribe 3.22e-3 "cP")


def test_espesor_4in_b311():
    r = calcular(caso("DM012_deareador_a_HRSG_descarga_4in"))["espesor"]
    t = 342.434 * 4.5 / (2 * (15000 + 0.4 * 342.434))
    assert r["t_presion_m"] / 0.0254 == pytest.approx(t, rel=1e-9)
    assert r["t_m_m"] / 0.0254 == pytest.approx(t + 0.0625, rel=1e-9)
    assert r["t_disponible_m"] / 0.0254 == pytest.approx(0.237 * 0.875, rel=1e-9) and r["cumple"]


def test_npsh_escenario():
    c = caso("ESCENARIO_succion_deareador_con_NPSH")
    r = calcular(c)
    n = r["npsh"]
    esperado = (120800 - r["p_vapor"]) / (r["rho"] * 9.80665) + 6.0 - r["tramo"]["h_friccion"]
    assert n["npsha"] == pytest.approx(esperado, rel=1e-12)
    assert r["p_vapor"] == pytest.approx(120.9e3, rel=2e-3)           # p_sat(105 °C)


def test_succion_sin_npsh_avisa():
    r = calcular(caso("DM012_deareador_a_HRSG_succion_6in"))
    assert any("NPSH" in a for a in r["advertencias"])


@pytest.mark.parametrize("cambio,msg", [({"caudal": {"valor": 0, "unidad": "m³/h"}}, "positivo"),
                                        ({"estado": "presion", "presion": {"valor": 0.1, "unidad": "bar a"}}, "hierve"),
                                        ({"tuberia": {"nps": "5", "cedula": "40"}}, "fuera de tabla")])
def test_entradas_invalidas(cambio, msg):
    c = dict(caso("DM012_deareador_a_HRSG_descarga_4in"), **cambio)
    with pytest.raises(ErrorEntrada, match=msg):
        calcular(c)


def test_todos_los_casos_corren():
    for f in glob.glob(os.path.join(CASOS, "*.json")):
        calcular(json.load(open(f, encoding="utf-8")))
