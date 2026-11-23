"""Pruebas de presión máxima admisible (Barlow y código) y de selección por velocidad.

Los valores de referencia salen de las memorias originales (PCGV-DM-005, DM-006, DM-012 y DM-017)
y de cálculos independientes hechos a mano con las ecuaciones citadas en los módulos.
"""
import math

import pytest

from linea_gas import presion as pres
from linea_gas import seleccion as sel

PSI = pres.PSI
IN = pres.PULG


# ---------------------------------------------------------------- Barlow contra las memorias
@pytest.mark.parametrize("memoria, p_psi, d_in, s_psi, f, t_esperado_in, tol", [
    # la tolerancia es media unidad del último decimal que imprime cada memoria
    ("PCGV-DM-017 línea de aceite 4\"", 101.526, 4.5, 35000, 0.5, 0.013, 5e-4),
    ("PCGV-DM-012 descarga deareador 4\"", 342.434, 4.0, 35000, 0.5, 0.03913, 5e-5),
    ("PCGV-DM-005 gas a calderas 4\"", 100.0, 4.0, 25000, 0.5, 0.016, 5e-4),
])
def test_barlow_reproduce_las_memorias(memoria, p_psi, d_in, s_psi, f, t_esperado_in, tol):
    t = pres.barlow_espesor(p_psi * PSI, d_in * IN, s_psi * PSI, f)
    assert t / IN == pytest.approx(t_esperado_in, abs=tol), memoria


def test_barlow_es_invertible():
    """P -> t -> P debe devolver la presión original."""
    p0 = 250.0 * PSI
    t = pres.barlow_espesor(p0, 4.5 * IN, 35000 * PSI, 0.5, 1.0, 0.967)
    assert pres.barlow_presion(t, 4.5 * IN, 35000 * PSI, 0.5, 1.0, 0.967) == pytest.approx(p0)


def test_presion_codigo_es_la_inversa_del_espesor():
    """P_máx del código debe coincidir con la presión que exige exactamente ese espesor (B31.3 3a)."""
    od, s, t = 4.5 * IN, 20000 * PSI, 0.1449 * IN
    p = pres.presion_codigo(t, od, s, e=1.0, w=1.0, y=0.4)
    t_vuelta = p * od / (2 * (s * 1.0 * 1.0 + p * 0.4))        # ec. (3a) despejando t
    assert t_vuelta == pytest.approx(t, rel=1e-12)


def test_presion_maxima_4in_ced40_a_mano():
    """4\" céd. 40 (OD 4.5, t 0.237), tolerancia 12.5 %, c = 0.0625 in, S = 20 ksi, SMYS = 35 ksi."""
    r = pres.evaluar(4.5 * IN, 0.237 * IN, s_adm_pa=20000 * PSI, s_cedencia_pa=35000 * PSI,
                     f=0.5, c_m=0.0625 * IN, p_diseno_pa=101.526 * PSI)
    assert r["t_disponible_m"] / IN == pytest.approx(0.2074, abs=1e-4)      # memoria DM-017
    assert r["t_resistente_m"] / IN == pytest.approx(0.1449, abs=1e-4)
    # 2·20000·0.144875/(4.5 − 0.8·0.144875) = 1321.8 psi
    assert r["codigo"]["fin_vida"] / PSI == pytest.approx(1321.8, abs=0.5)
    # 2·35000·0.144875·0.5/4.5 = 1126.8 psi
    assert r["barlow"]["fin_vida"] / PSI == pytest.approx(1126.8, abs=0.5)
    assert r["t_barlow_requerido_m"] / IN == pytest.approx(0.0755, abs=1e-4)  # memoria DM-017
    assert r["cumple"] is True


def test_el_orden_de_las_presiones_maximas_es_coherente():
    r = pres.evaluar(4.5 * IN, 0.237 * IN, s_adm_pa=20000 * PSI, s_cedencia_pa=35000 * PSI,
                     f=0.5, c_m=0.0625 * IN)
    assert r["codigo"]["nominal"] > r["codigo"]["nuevo"] > r["codigo"]["fin_vida"]
    assert r["barlow"]["nominal"] > r["barlow"]["nuevo"] > r["barlow"]["fin_vida"]


def test_sin_cedencia_no_hay_barlow():
    r = pres.evaluar(4.5 * IN, 0.237 * IN, s_adm_pa=20000 * PSI)
    assert r["barlow"] is None
    assert r["codigo"]["fin_vida"] > 0


def test_corrosion_que_consume_la_pared_es_error_explicito():
    with pytest.raises(ValueError):
        pres.barlow_presion(-1e-4, 4.5 * IN, 35000 * PSI)
    r = pres.evaluar(4.5 * IN, 0.237 * IN, s_adm_pa=20000 * PSI, c_m=0.3 * IN)
    assert r["codigo"]["fin_vida"] is None and r["avisos"]


# ---------------------------------------------------------------- factores de la NOM-007-SECRE-2010
def test_factor_diseno_por_clase_de_localizacion():
    assert pres.F_CLASE == {"1": 0.72, "2": 0.60, "3": 0.50, "4": 0.40}   # cuadro 2


def test_factor_de_temperatura_cuadro_4():
    assert pres.factor_temperatura(26.0) == 1.0                    # 299.15 K, como la memoria DM-005
    assert pres.factor_temperatura(400 - 273.15) == pytest.approx(1.000)
    assert pres.factor_temperatura(420 - 273.15) == pytest.approx(0.967)
    assert pres.factor_temperatura(500 - 273.15) == pytest.approx(0.867)
    assert pres.factor_temperatura(435 - 273.15) == pytest.approx(0.950)  # interpolación directa
    with pytest.raises(ValueError):
        pres.factor_temperatura(300.0)                              # 573 K, fuera del cuadro


def test_junta_longitudinal_sin_costura():
    assert pres.E_JUNTA["A106 sin costura"] == 1.00                 # cuadro 3


def test_aplica_nom_acepta_cadenas_de_la_interfaz():
    cfg = {"p_diseno": {"valor": 100, "unidad": "psig"}, "s": {"valor": 20000, "unidad": "psi"},
           "barlow": {"s_cedencia": {"valor": 35000, "unidad": "psi"}, "clase_localizacion": "3",
                      "aplica_nom": "false"}}
    r = pres.desde_caso(cfg, 4.5 * IN, 0.237 * IN, 20000 * PSI, 20.0)
    assert r["aplica_nom"] is False and r["avisos"]
    cfg["barlow"]["aplica_nom"] = "true"
    assert pres.desde_caso(cfg, 4.5 * IN, 0.237 * IN, 20000 * PSI, 20.0)["aplica_nom"] is True


def test_sobreespesor_por_vida_util():
    c, origen = pres.sobreespesor({"c_por_ano_in": 0.00625, "vida_util_anos": 10})
    assert c / IN == pytest.approx(0.0625)                          # memorias PCGV
    assert "años" in origen
    assert pres.sobreespesor({"c_mm": 3.0})[0] == pytest.approx(0.003)


def test_clase_de_localizacion_invalida_es_error():
    cfg = {"s": {"valor": 20000, "unidad": "psi"},
           "barlow": {"s_cedencia": {"valor": 35000, "unidad": "psi"}, "clase_localizacion": "9"}}
    with pytest.raises(ValueError):
        pres.desde_caso(cfg, 4.5 * IN, 0.237 * IN, 20000 * PSI, 20.0)


def test_esfuerzo_admisible_de_la_tabla_a1():
    s, fuente = pres.resolver_s({"s": {"tabla": "A106B_B313"}, "t_diseno_c": 90})
    assert s / PSI == pytest.approx(20000)                          # B31.3 Tabla A-1, ≤ 400 °F
    assert "A-1" in fuente
    assert not pres.hay_material({"s": {"valor": None}})
    assert pres.hay_material({"s": {"tabla": "A106B_B313"}})


# ---------------------------------------------------------------- velocidad, capacidad y diámetro
def test_velocidad_y_capacidad_son_consistentes():
    d = 0.10226                                   # 4" céd. 40
    q = 44.325 / 3600                             # m³/s (memoria DM-012)
    v = sel.velocidad(q, d)
    assert v == pytest.approx(1.4991, abs=1e-3)   # memoria corregida: 1.499 m/s
    assert sel.caudal_limite(d, v) == pytest.approx(q)
    assert sel.diametro_requerido(q, v) == pytest.approx(d)


def test_area_coincide_con_la_memoria():
    assert sel.area(0.10226) == pytest.approx(8.2131e-3, rel=1e-4)
    with pytest.raises(ValueError):
        sel.area(0.0)


def test_capacidad_maxima_es_proporcional_al_area():
    d, vmax = 0.10226, 1.52
    q_max = sel.caudal_limite(d, vmax)
    assert q_max * 3600 == pytest.approx(44.94, abs=0.02)
    assert q_max == pytest.approx(vmax * math.pi / 4 * d ** 2)


def test_estado_segun_el_intervalo():
    assert sel.estado_velocidad(1.0, 0.6, 1.5) == "CUMPLE"
    assert sel.estado_velocidad(2.0, 0.6, 1.5) == "NO CUMPLE"
    assert sel.estado_velocidad(0.3, 0.6, 1.5) == "INFORMATIVO"
    assert sel.estado_velocidad(0.3) == ""


def test_barrido_marca_el_diametro_actual_y_no_se_rompe():
    cand = [("2", "40", 0.0525), ("4", "40", 0.10226), ("6", "40", 0.15405)]
    filas = sel.barrido(cand, lambda d: {"v": sel.velocidad(44.325 / 3600, d)}, 0.61, 1.52, "4")
    assert filas[1][0].endswith(" *")                     # el diámetro en uso va marcado
    assert filas[0][-1] == "NO CUMPLE" and filas[1][-1] == "CUMPLE"
    malas = sel.barrido([("0", "40", 0.0)], lambda d: {"v": sel.velocidad(1.0, d)})
    assert "no evaluable" in malas[0][-1]                 # un diámetro inviable no tumba la tabla


def test_ventana_de_diametros_conserva_el_actual():
    cand = [(n, "40", d) for n, d in (("1/2", 0.0158), ("1", 0.02664), ("2", 0.0525),
                                      ("4", 0.10226), ("6", 0.15405), ("8", 0.20272))]
    v = sel.ventana(cand, 44.325 / 3600, 0.61, 1.52, "4")
    assert ("4", "40", 0.10226) in v and len(v) < len(cand)
    assert sel.ventana(cand, 1.0, None, None, None) == cand          # sin criterio, lista completa


def test_curva_pasa_por_el_punto_de_operacion():
    d, q = 0.10226, 44.325 / 3600
    cv = sel.curva(d, q, 0.61, 1.52)
    assert cv["v_actual"] == pytest.approx(sel.velocidad(q, d))
    assert cv["q_max_m3h"] == pytest.approx(sel.caudal_limite(d, 1.52) * 3600)
    assert all(v >= 0 for _, v in cv["puntos"])
