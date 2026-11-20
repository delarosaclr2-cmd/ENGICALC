"""Pruebas del motor: casos a mano, reproducción del original, integración numérica independiente."""
import math
import os

import pytest

from tanque_pulmon import unidades as u
from tanque_pulmon.caso import CasoUsuario
from tanque_pulmon.constantes import R_AIRE, REFERENCIAS, diametro_interior_m
from tanque_pulmon.criterios import clasificar_nom020
from tanque_pulmon.motor import Entradas, Tramo, calcular, masa_util, volumen_para_frecuencia
from tanque_pulmon.validacion import ErrorEntrada

CASOS = os.path.join(os.path.dirname(__file__), "..", "casos")
PSI = u.PSI


def entradas(**kw):
    base = dict(v_tanque_m3=20.0, p_superior_pa=128.9 * PSI, p_inferior_pa=115.0 * PSI,
                t_aire_k=313.15, q_consumo_m3s=105.6948 / 3600, ref_consumo="estandar_60F",
                p_atm_sitio_pa=14.7 * PSI)
    base.update(kw)
    return Entradas(**base)


# ------------------------------------------------------------------ unidades y tablas
def test_conversion_presion_manometrica_usa_atm_del_sitio():
    assert u.presion_a_pa_abs(100, "psig", 12.0 * PSI) == pytest.approx(112.0 * PSI)
    assert u.pa_abs_a(112.0 * PSI, "psig", 12.0 * PSI) == pytest.approx(100.0)
    assert u.presion_a_pa_abs(7.5, "bar g", 101_325) == pytest.approx(851_325)


def test_diametros_interiores_b36_10m():
    assert diametro_interior_m("4", "40") / 0.0254 == pytest.approx(4.026, abs=1e-9)
    assert diametro_interior_m("2", "40") / 0.0254 == pytest.approx(2.067, abs=1e-9)
    assert diametro_interior_m("4", "80") / 0.0254 == pytest.approx(3.826, abs=1e-9)
    with pytest.raises(KeyError):
        diametro_interior_m("5", "40")


def test_texto_tiempo():
    assert u.min_a_texto(10.73557) == "10 min 44 s"
    assert u.min_a_texto(75.5) == "1 h 15 min 30 s"


# ------------------------------------------------------------------ casos a mano
def test_reproduce_formula_original_cuando_T_aire_igual_a_T_ref():
    """Con T_r = T_ref y P_ref = 14.7 psia el motor debe dar 10.7356 min (memoria original)."""
    e = entradas(t_aire_k=REFERENCIAS["estandar_60F"].temperatura_k)
    r = calcular(e)
    # P_ref del motor = 14.696 psia vs 14.7 del original: diferencia esperada 0.03 %
    assert r.t_retencion_min == pytest.approx(10.73557 * 14.7 / (101_325 / PSI), rel=1e-6)


def test_valor_corregido_a_mano_40C():
    t = 20 * (128.9 - 115) * 288.7056 / ((105.6948 / 60) * (101.325 / 6.894757293168) * 313.15)
    assert calcular(entradas()).t_retencion_min == pytest.approx(t, rel=1e-9)
    assert t == pytest.approx(9.900, abs=1e-3)


def test_volumen_tuberia_y_sistema():
    tr = [Tramo("4", 447.6, diametro_interior_m("4", "40")), Tramo("2", 40.0, diametro_interior_m("2", "40"))]
    r = calcular(entradas(tramos=tr))
    assert r.v_tuberia_m3 == pytest.approx(3.76276, abs=1e-5)
    assert r.t_retencion_min == pytest.approx(11.7629, abs=1e-4)


def test_volumen_requerido_inverso_del_tiempo():
    e = entradas(t_retencion_req_min=10.0, p_inferior_pa=108.9745 * PSI)
    r = calcular(e)
    e2 = entradas(v_tanque_m3=r.v_sistema_req_m3, p_inferior_pa=108.9745 * PSI)
    assert calcular(e2).t_retencion_min == pytest.approx(10.0, rel=1e-12)
    assert r.v_sistema_req_m3 == pytest.approx(14.0925, abs=1e-4)


def test_margen_reduce_tiempo_proporcionalmente():
    t0 = calcular(entradas()).t_retencion_min
    t1 = calcular(entradas(margen_consumo=0.25)).t_retencion_min
    assert t1 == pytest.approx(t0 / 1.25)


def test_ciclo_independiente_del_volumen_y_formula_frecuencia_maxima():
    for v in (5.0, 20.0, 80.0):
        r = calcular(entradas(v_tanque_m3=v, q_consumo_m3s=200 / 3600, ref_consumo="normal",
                              q_compresor_m3s=300 / 3600, ref_compresor="normal"))
        assert r.fraccion_carga == pytest.approx(2 / 3)
    # f_max = ṁc/(4Δm) coincide con el máximo de 60/(t_c + t_d) barriendo el consumo
    e = entradas(q_compresor_m3s=300 / 3600, ref_compresor="normal", ref_consumo="normal")
    fmax = calcular(e).ciclos_por_hora_max
    mejores = max(calcular(entradas(q_compresor_m3s=300 / 3600, ref_compresor="normal", ref_consumo="normal",
                                    q_consumo_m3s=k / 1000 * 300 / 3600)).ciclos_por_hora for k in range(10, 1000, 5))
    assert mejores == pytest.approx(fmax, rel=1e-6)
    v = volumen_para_frecuencia(e, fmax)
    assert v == pytest.approx(20.0, rel=1e-9)


def test_fad_menor_que_consumo_no_da_tiempo_de_carga():
    r = calcular(entradas(q_compresor_m3s=50 / 3600, ref_compresor="estandar_60F"))
    assert r.t_carga_min is None
    assert any("no recupera presión" in a for a in r.advertencias)


def test_z_gas_real_despreciable_coolprop():
    CP = pytest.importorskip("CoolProp.CoolProp")
    z_s = CP.PropsSI("Z", "T", 313.15, "P", 128.9 * PSI, "Air")
    z_i = CP.PropsSI("Z", "T", 313.15, "P", 115.0 * PSI, "Air")
    t_ideal = calcular(entradas()).t_retencion_min
    t_real = calcular(entradas(z_superior=z_s, z_inferior=z_i)).t_retencion_min
    assert abs(t_real / t_ideal - 1) < 0.01      # < 1 %: el modelo de gas ideal es adecuado


# ------------------------------------------------------------------ integración numérica independiente
def test_integracion_isotermica_scipy():
    solve_ivp = pytest.importorskip("scipy.integrate").solve_ivp
    e = entradas()
    mdot = e.q_consumo_m3s * 101_325 / (R_AIRE * REFERENCIAS["estandar_60F"].temperatura_k)
    k = R_AIRE * e.t_aire_k / e.v_tanque_m3

    def ev(t, y):
        return y[0] - e.p_inferior_pa
    ev.terminal = True
    sol = solve_ivp(lambda t, y: [-k * mdot], (0, 1e5), [e.p_superior_pa], events=ev, rtol=1e-10, atol=1e-6)
    assert sol.t_events[0][0] / 60 == pytest.approx(calcular(e).t_retencion_min, rel=1e-8)


def test_integracion_adiabatica_balance_energia():
    """Descarga adiabática de un recipiente rígido integrando masa y energía (sin usar P/ρ^k):
    m·cv·dT/dt = −ṁ·R·T. Debe coincidir con la expresión politrópica del motor con n = k."""
    solve_ivp = pytest.importorskip("scipy.integrate").solve_ivp
    k_aire, cv = 1.4, R_AIRE / 0.4
    e = entradas(n_politropico=1.4)
    mdot = e.q_consumo_m3s * 101_325 / (R_AIRE * REFERENCIAS["estandar_60F"].temperatura_k)
    V = e.v_tanque_m3
    m0 = e.p_superior_pa * V / (R_AIRE * e.t_aire_k)

    def f(t, y):
        m, T = y
        return [-mdot, -mdot * R_AIRE * T / (m * cv)]

    def ev(t, y):
        return y[0] * R_AIRE * y[1] / V - e.p_inferior_pa
    ev.terminal = True
    sol = solve_ivp(f, (0, 1e5), [m0, e.t_aire_k], events=ev, rtol=1e-10, atol=1e-9)
    assert sol.t_events[0][0] / 60 == pytest.approx(calcular(e).t_retencion_min, rel=1e-6)
    assert k_aire == 1.4


def test_simulacion_ciclo_carga_vacio():
    """Simulación por pasos de un compresor carga/vacío con histéresis durante 4 h."""
    e = entradas(q_consumo_m3s=200 / 3600, ref_consumo="normal", q_compresor_m3s=300 / 3600, ref_compresor="normal")
    r = calcular(e)
    md = r.mdot_consumo_kg_s
    mc = r.mdot_compresor_kg_s
    m_s = e.p_superior_pa * e.v_tanque_m3 / (R_AIRE * e.t_aire_k)
    m_i = e.p_inferior_pa * e.v_tanque_m3 / (R_AIRE * e.t_aire_k)
    m, cargando, dt, t_carga, arranques = m_i, True, 0.05, 0.0, 0
    T = 4 * 3600
    for _ in range(int(T / dt)):
        m += ((mc if cargando else 0.0) - md) * dt
        t_carga += dt if cargando else 0.0
        if cargando and m >= m_s:
            cargando = False
        elif not cargando and m <= m_i:
            cargando, arranques = True, arranques + 1
    assert t_carga / T == pytest.approx(r.fraccion_carga, abs=0.01)
    assert arranques / 4 == pytest.approx(r.ciclos_por_hora, abs=0.3)


# ------------------------------------------------------------------ validación de entradas
@pytest.mark.parametrize("kw, msj", [
    (dict(v_tanque_m3=-1), "mayor que cero"),
    (dict(p_inferior_pa=130 * PSI), "superior debe ser mayor"),
    (dict(p_inferior_pa=10 * PSI, p_superior_pa=12 * PSI), "atmosférica"),
    (dict(n_politropico=1.6), "politrópico"),
    (dict(q_consumo_m3s=float("nan")), "no finito"),
    (dict(ref_consumo="inventada"), "referencia"),
    (dict(tramos=[Tramo("x", 10, 102.3)]), "mm"),
])
def test_entradas_invalidas(kw, msj):
    with pytest.raises(ErrorEntrada, match=msj):
        calcular(entradas(**kw))


# ------------------------------------------------------------------ clasificación NOM-020
@pytest.mark.parametrize("p, v, cat", [(400, 0.4, "I"), (400, 2, "II"), (700, 0.8, "II"),
                                       (700, 2, "III"), (790, 0.1, "III"), (490.33, 0.5, "I")])
def test_nom020(p, v, cat):
    assert clasificar_nom020(p, v) == cat


# ------------------------------------------------------------------ casos guardados
def test_casos_pcgv_cargan_y_coinciden_con_auditoria():
    """Valores esperados del recálculo independiente (audit/recalculo_dm014E.py para los casos A–D)."""
    esperado = {"caso1": 11.7629, "caso2": 8.4310, "caso4": 9.2248, "caso3": 5.8814,
                "casoA": 10.4281, "casoB": 11.5509, "casoC": 1.7380, "casoD": 10.4281}
    for nombre in os.listdir(CASOS):
        clave = nombre.split("_")[1]
        e = CasoUsuario.cargar(os.path.join(CASOS, nombre)).a_entradas()
        assert calcular(e).t_retencion_min == pytest.approx(esperado[clave], abs=2e-4), nombre
