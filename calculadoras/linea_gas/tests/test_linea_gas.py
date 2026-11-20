import glob
import json
import math
import os

import pytest

from linea_gas import unidades as u
from linea_gas.caso import a_entradas, ejecutar, exportar_excel
from linea_gas.datos import R_U, d_interior_m, k_menon, mu_sutherland_aire
from linea_gas.motor import Accesorio, Entradas, ErrorEntrada, calcular, fritzsche_dp_psi

CASOS = os.path.join(os.path.dirname(__file__), "..", "casos")


def caso(**kw):
    base = dict(nombre="t", gas="aire", q_ref_m3s=200 / 3600, ref="normal", p_entrada_pa=130.7 * u.PSI,
                t_k=301.15, longitud_m=792.5, d_interior_m=d_interior_m("4", "40"), nps="4")
    base.update(kw)
    return Entradas(**base)


def test_menon_ejemplo_5_15():
    """150 CFM de aire libre a 100 psig y 80 °F, 100 ft de 1" céd. 40, e = 0.0018 in.
    Menon: Re = 2.2435e5, f = 0.0232, ΔP = 5.05 psi (Darcy incompresible con densidad de entrada)."""
    mu = 3.85e-7 * 47.880259   # lb·s/ft² -> Pa·s
    e = caso(q_ref_m3s=150 * u.FT3 / 60, ref="estandar_60F", p_entrada_pa=114.7 * u.PSI,
             t_k=u.temperatura_a_k(80, "°F"), longitud_m=100 * 0.3048, d_interior_m=d_interior_m("1", "40"),
             nps="1", mu_pa_s=mu)
    r = calcular(e)
    assert r.re == pytest.approx(2.2435e5, rel=0.01)
    assert r.f == pytest.approx(0.0232, abs=0.0005)
    # Isotérmico compresible: algo mayor que Darcy incompresible (ρ baja a lo largo)
    assert r.dp_total_pa / u.PSI == pytest.approx(5.05, rel=0.05)


def test_menon_ejemplo_5_17_fritzsche():
    """4000 SCFM, 20 000 ft, P media 125 psia, 60 °F, ΔP = 50 psi -> d = 6.39 in (Menon)."""
    assert fritzsche_dp_psi(4000, 20000, 6.39, 125, 520) == pytest.approx(50, rel=0.01)


def test_tabla_k_menon():
    assert k_menon("codo90", "2") == 0.57
    assert k_menon("globo", "4") == 5.80
    assert k_menon("check_columpio", "4") == pytest.approx(1.80)
    assert k_menon("codo45", "3") == 0.29      # columna 2½–3
    with pytest.raises(KeyError):
        k_menon("valvula_inventada", "2")


def test_sutherland_contra_coolprop():
    CP = pytest.importorskip("CoolProp.CoolProp")
    for t in (273.15, 301.15, 323.15):
        assert mu_sutherland_aire(t) == pytest.approx(CP.PropsSI("V", "T", t, "P", 101325, "Air"), rel=0.01)


def test_integracion_numerica_independiente():
    """dP/dx = −(f·G²·Z·R·T/(2·D·M·P)) / (1 − G²·Z·R·T/(M·P²)), integrada con scipy."""
    solve_ivp = pytest.importorskip("scipy.integrate").solve_ivp
    e = caso(longitud_m=300, d_interior_m=d_interior_m("1", "40"), nps="1", q_ref_m3s=150 / 3600,
             p_entrada_pa=7e5)
    r = calcular(e)
    G = r.mdot_kg_s / (math.pi * e.d_interior_m ** 2 / 4)
    a2 = R_U * e.t_k / 28.9647

    def dpdx(x, y):
        p = y[0]
        return [-(r.f * G ** 2 * a2 / (2 * e.d_interior_m * p)) / (1 - G ** 2 * a2 / p ** 2)]
    sol = solve_ivp(dpdx, (0, e.longitud_m), [e.p_entrada_pa], rtol=1e-11, atol=1e-6)
    assert sol.y[0][-1] == pytest.approx(r.p_salida_pa, rel=1e-6)
    assert r.dp_total_pa > 50_000     # caso con ΔP apreciable, no trivial


def test_accesorios_suman_como_k():
    e0 = caso()
    e1 = caso(accesorios=[Accesorio("codo90", 30)])
    r0, r1 = calcular(e0), calcular(e1)
    dyn = r1.rho_entrada * r1.v_entrada ** 2 / 2
    assert r1.dp_total_pa - r0.dp_total_pa == pytest.approx(30 * 0.51 * dyn, rel=0.01)


def test_gas_natural_densidad_contra_coolprop():
    CP = pytest.importorskip("CoolProp.CoolProp")
    comp = {"Methane": 95.335, "Ethane": 1.996, "n-Propane": 0.303, "IsoButane": 0.107, "n-Butane": 0.063,
            "Isopentane": 0.026, "n-Pentane": 0.025, "n-Hexane": 0.012, "n-Heptane": 0.003, "n-Octane": 0.001,
            "n-Nonane": 0.003, "Oxygen": 0.016, "Nitrogen": 0.087, "CarbonDioxide": 2.023}
    fl = "HEOS::" + "&".join(f"{k}[{v/100}]" for k, v in comp.items())
    T, P = 298.15, 594.7 * u.PSI
    z = CP.PropsSI("Z", "T", T, "P", P, fl)
    e = caso(gas="gas_natural_pcgv", p_entrada_pa=P, t_k=T, z=z, longitud_m=10)
    assert calcular(e).rho_entrada == pytest.approx(CP.PropsSI("D", "T", T, "P", P, fl), rel=0.002)


@pytest.mark.parametrize("kw, msj", [
    (dict(q_ref_m3s=-1), "positivo"), (dict(d_interior_m=52.5), "mm"), (dict(p_entrada_pa=20000), "manométrica"),
    (dict(gas="helio"), "Gas"), (dict(nps=None, accesorios=[Accesorio("codo90", 1)]), "NPS"),
    (dict(longitud_m=5000, d_interior_m=0.005, nps=None), "no puede conducir"),
])
def test_entradas_invalidas(kw, msj):
    with pytest.raises(ErrorEntrada, match=msj):
        calcular(caso(**kw))


def test_casos_rev_e_y_excel(tmp_path):
    esperado = {"L1": 0.104, "L2": 0.048, "L3": 0.011, "L4": 0.041, "L5": 0.023}   # psi
    casos = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(os.path.join(CASOS, "DM014E_*.json")))]
    for c in casos:
        _, r = ejecutar(c)
        assert r.dp_total_pa / u.PSI == pytest.approx(esperado[c["nombre"][:2]], abs=0.0015), c["nombre"]
    ruta = exportar_excel(casos, str(tmp_path / "r.xlsx"))
    from openpyxl import load_workbook
    assert len(load_workbook(ruta).sheetnames) == 6


def test_venteo_eliminador_neblina_dm017():
    """PCGV-DM-017: con 750 Nm³/h a 60 °C el caudal real es ≈914 m³/h y la contrapresión ≈5.9 mmH₂O
    (la memoria da 4.0 mmH₂O porque toma 750 m³/h reales)."""
    c = json.load(open(os.path.join(CASOS, "DM017_venteo_eliminador_neblina_8in.json"), encoding="utf-8"))
    _, r = ejecutar(c)
    assert r.q_actual_m3h == pytest.approx(750 * 333.15 / 273.15 * 101.325 / 101.425, rel=2e-3)
    assert r.dp_total_pa / 9.80665 == pytest.approx(5.85, abs=0.1)
    assert [v[3] for v in r.verificaciones] == ["CUMPLE"]
