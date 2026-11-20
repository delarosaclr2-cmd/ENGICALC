"""Pruebas de regresión de la revisión del PR (change request).

Cada prueba reproduce uno de los escenarios reportados, con los mismos números, para que el
defecto no vuelva a pasar inadvertido:

P1-1  Se aceptaba una corrosión anual negativa, que engrosaba la pared y elevaba la presión
      admisible (DM-012: de ~991 a ~1,890 psig, y el dictamen pasaba de NO CUMPLE a CUMPLE).
P1-2  Con t ≥ D/6 se avisaba del dominio pero se dictaminaba CUMPLE con la ec. (3a) igual.
P2-5  El cuadro 4 de la NOM-007 (que llega a 500 K) se leía aunque no se pidiera Barlow, e
      interrumpía el cálculo ASME a 300 °C, que sí está dentro de la tabla A-1 implementada.
P2-4  La capacidad máxima se obtenía con la densidad de entrada, pero el dictamen usa la
      velocidad de salida, mayor al caer la presión.
"""
import pytest

try:                                    # agua, vapor y aceite tienen los módulos en nucleo/
    from linea_vapor.nucleo import presion as pres
except ImportError:                     # gas y tanque pulmón, en la raíz del paquete
    from linea_vapor import presion as pres

try:
    from linea_vapor.nucleo import espesor as esp
except ImportError:
    esp = None

try:
    from linea_vapor.nucleo import seleccion as sel
except ImportError:
    try:
        from linea_vapor import seleccion as sel
    except ImportError:
        sel = None

PSI = pres.PSI
IN = pres.PULG


# ================================================================ P1-1: valores negativos
@pytest.mark.parametrize("cfg, trozo", [
    ({"c_por_ano_in": -0.00625, "vida_util_anos": 10}, "corrosión no puede ser negativa"),
    ({"c_por_ano_in": 0.00625, "vida_util_anos": -10}, "vida útil no puede ser negativa"),
    ({"c_mm": -1.5}, "no puede ser negativo"),
])
def test_rechaza_sobreespesor_negativo(cfg, trozo):
    with pytest.raises(ValueError, match=trozo):
        pres.sobreespesor(cfg)


def test_sobreespesor_positivo_sigue_funcionando():
    """El caso normal de las memorias: 0.00625 in/año × 10 años = 0.0625 in."""
    c, origen = pres.sobreespesor({"c_por_ano_in": 0.00625, "vida_util_anos": 10})
    assert c / IN == pytest.approx(0.0625)
    assert "10 años" in origen
    assert pres.sobreespesor({})[0] == 0.0                      # sin capturar, c = 0


def test_corrosion_negativa_no_puede_elevar_la_presion_admisible():
    """Escenario DM-012 del revisor: con c = −0.00625 in/año la admisible pasaba de 991 a 1,890 psig."""
    comun = dict(od_m=4.5 * IN, t_nominal_m=0.237 * IN, s_adm_pa=15000 * PSI,
                 tolerancia=0.125, p_diseno_pa=1500 * PSI)
    normal = pres.evaluar(c_m=0.0625 * IN, **comun)
    assert normal["p_max_pa"] / PSI == pytest.approx(991, abs=1)
    assert normal["cumple"] is False
    with pytest.raises(ValueError, match="no puede ser negativo"):
        pres.evaluar(c_m=-0.0625 * IN, **comun)


def test_evaluar_rechaza_tolerancia_imposible():
    for tol in (-0.1, 1.0, 1.5):
        with pytest.raises(ValueError, match="entre 0 % y 100 %"):
            pres.evaluar(0.1143, 0.00602, s_adm_pa=15000 * PSI, tolerancia=tol)


# ================================================================ P1-2: dominio de la ec. (3a)
def test_dentro_del_dominio_si_dictamina():
    """Justo por debajo de D/6 la ec. (3a) sí aplica: el resultado es un dictamen, no un aviso."""
    od = 0.1143
    r = pres.evaluar(od, od / 6 * 0.99, s_adm_pa=20000 * PSI, c_m=0.0, tolerancia=0.0,
                     p_diseno_pa=1000 * PSI)
    assert r["fuera_dominio"]["fin_vida"] == []
    assert r["dominio_valido"] is True
    assert r["cumple"] is True
    assert "margen_diseno" in r
    assert [v[3] for v in pres.verificaciones(r)] == ["CUMPLE"]


def test_en_el_limite_d6_no_es_evaluable():
    """t = D/6 exacto ya está fuera: B31.3 §304.1.2(b) pide t < D/6."""
    od = 0.1143
    r = pres.evaluar(od, od / 6, s_adm_pa=20000 * PSI, c_m=0.0, tolerancia=0.0,
                     p_diseno_pa=1000 * PSI)
    assert r["fuera_dominio"]["fin_vida"]
    assert r["cumple"] is None
    assert all(v[3] == "NO EVALUABLE" for v in pres.verificaciones(r))


def test_fuera_del_dominio_no_informa_cumple():
    """Escenario del revisor: D = 114.3 mm, t = 30 mm, tol 12.5 %, S = 20,000 psi, P = 10,000 psig.

    Antes daba CUMPLE con una presión admisible de ~11,254 psig calculada con una fórmula que el
    código no autoriza para esa pared. Ahora la presión se conserva como referencia, marcada, y
    las verificaciones salen NO EVALUABLE.
    """
    r = pres.evaluar(0.1143, 0.030, s_adm_pa=20000 * PSI, c_m=0.0, tolerancia=0.125,
                     p_diseno_pa=10000 * PSI, p_operacion_pa=9000 * PSI)
    assert r["p_max_pa"] / PSI == pytest.approx(11254, abs=2)    # el número no cambia
    assert r["t_resistente_m"] > 0.1143 / 6
    assert r["cumple"] is None
    assert r["dominio_valido"] is False
    motivos = " ".join(r["fuera_dominio"]["fin_vida"])
    assert "t ≥ D/6" in motivos and "P/(S·E)" in motivos
    assert "margen_diseno" not in r and "margen_operacion" not in r
    estados = [v[3] for v in pres.verificaciones(r)]
    assert estados == ["NO EVALUABLE", "NO EVALUABLE"]
    assert any("304.1.2(b)" in a for a in r["avisos"])
    assert "fuera de dominio" in pres.tabla(r)[2][-1][3]         # marcado en la tabla


def test_fuera_de_dominio_detecta_cada_criterio_por_separado():
    od = 0.1143
    assert pres.fuera_de_dominio(od / 6 * 0.5, od) == []
    assert any("t ≥ D/6" in m for m in pres.fuera_de_dominio(od / 6, od))
    # P/(S·E) > 0.385 con pared delgada: se detecta por el segundo criterio
    solo_p = pres.fuera_de_dominio(0.001, od, p_pa=0.5 * 20000 * PSI, s_pa=20000 * PSI)
    assert len(solo_p) == 1 and "P/(S·E)" in solo_p[0]


@pytest.mark.skipif("esp is None")
def test_espesor_fuera_de_dominio_no_informa_cumple():
    """La verificación de ESPESOR tenía el mismo defecto: avisaba pero dictaminaba CUMPLE."""
    r = esp.verificar(10000 * PSI, 0.1143, 0.030, 20000 * PSI, tolerancia=0.125)
    assert r["cumple"] is None and r["fuera_dominio"] and r["margen"] is None
    r["codigo"] = "B31.3"
    assert esp.verificacion(r)[3] == "NO EVALUABLE"
    # dentro del dominio sigue dictaminando
    ok = esp.verificar(300 * PSI, 0.1143, 0.00602, 20000 * PSI, tolerancia=0.125)
    assert ok["cumple"] is True and ok["fuera_dominio"] == []
    ok["codigo"] = "B31.3"
    assert esp.verificacion(ok)[3] == "CUMPLE"


@pytest.mark.skipif("esp is None")
def test_espesor_rechaza_sobreespesor_negativo():
    with pytest.raises(ValueError, match="no puede ser negativo"):
        esp.verificar(300 * PSI, 0.1143, 0.00602, 20000 * PSI, c_m=-0.001)


# ================================================================ P2-5: Barlow y la temperatura
def _cfg_sin_barlow(t_c):
    return {"s": {"tabla": "A106B_B313"}, "t_diseno_c": t_c, "tolerancia_pct": 12.5,
            "c_por_ano_in": 0.00625, "vida_util_anos": 10,
            "p_diseno": {"valor": 150, "unidad": "psig"}}


def test_sin_barlow_no_se_aplica_el_cuadro_4_de_la_nom():
    """A 300 °C (573 K) el cuadro 4 de Barlow no aplica, pero la tabla A-1 de B31.3 sí.

    Antes se evaluaba el factor T aunque no se pidiera Barlow y el cálculo ASME se interrumpía.
    """
    cfg = _cfg_sin_barlow(300)
    s_adm, _ = pres.resolver_s(cfg)
    # 300 °C = 572 °F; B31.3 Tabla A-1 interpola entre 19.0 ksi (500 °F) y 17.9 ksi (600 °F)
    assert s_adm / PSI == pytest.approx(18208, abs=1)
    r = pres.desde_caso(cfg, 12.75 * IN, 0.375 * IN, s_adm, t_diseno_c=300)
    assert r is not None and r["barlow"] is None
    assert r["p_max_pa"] > 0
    assert "tf" not in r                       # no se leyó el cuadro 4: Barlow no se evaluó


def test_con_barlow_sigue_rechazando_fuera_del_cuadro_4():
    """Si sí se pide Barlow, el límite de 500 K del cuadro 4 debe seguir deteniendo el cálculo."""
    cfg = _cfg_sin_barlow(300)
    cfg["barlow"] = {"s_cedencia": {"valor": 35000, "unidad": "psi"}, "clase_localizacion": "3"}
    s_adm, _ = pres.resolver_s(cfg)
    with pytest.raises(ValueError, match="500 K"):
        pres.desde_caso(cfg, 12.75 * IN, 0.375 * IN, s_adm, t_diseno_c=300)


def test_barlow_dentro_del_cuadro_4_sigue_calculando():
    cfg = _cfg_sin_barlow(150)
    cfg["barlow"] = {"s_cedencia": {"valor": 35000, "unidad": "psi"}, "clase_localizacion": "3",
                     "junta": "A106 sin costura"}
    s_adm, _ = pres.resolver_s(cfg)
    r = pres.desde_caso(cfg, 12.75 * IN, 0.375 * IN, s_adm, t_diseno_c=150)
    assert r["barlow"]["fin_vida"] > 0
    assert r["tf"] == pytest.approx(pres.factor_temperatura(150))
    assert r["f"] == 0.5


# ================================================================ P2-4: capacidad y caída de presión
@pytest.mark.skipif("sel is None")
def test_caudal_limite_real_resuelve_la_velocidad_objetivo():
    """Con una v(Q) creciente conocida, el caudal devuelto debe alcanzar el objetivo por debajo."""
    v = lambda q: 3.0 * q ** 1.2                      # monótona, como v_salida(Q)
    q = sel.caudal_limite_real(v, 15.0, q_inicial=1.0)
    assert v(q) == pytest.approx(15.0, rel=1e-4)
    assert v(q) <= 15.0                                # se aproxima por debajo: el valor cumple


@pytest.mark.skipif("sel is None")
def test_caudal_limite_real_acota_aunque_el_modelo_falle():
    """Un caudal que el modelo no puede resolver acota por arriba, no rompe la tabla."""
    def v(q):
        if q > 2.0:
            raise ValueError("flujo crítico")
        return 10.0 * q
    q = sel.caudal_limite_real(v, 15.0, q_inicial=1.0)
    assert q == pytest.approx(1.5, rel=1e-4)
    assert sel.caudal_limite_real(lambda q: 1.0, 15.0, q_inicial=1.0) is None   # inalcanzable


@pytest.mark.skipif("sel is None")
def test_capacidad_de_liquido_no_cambia():
    """Sin v_gobernante (líquido: densidad constante) la tabla sigue siendo Q = v·A."""
    d, q = 0.10226, 44.325 / 3600
    _t, _e, filas, _a = sel.tabla_capacidad(d, q, 0.61, 1.52)
    assert filas[-1][1] == "1.520"
    # la tabla imprime 2 decimales: media unidad del último decimal es la tolerancia que aplica
    assert float(filas[-1][2].replace(",", "")) == pytest.approx(sel.caudal_limite(d, 1.52) * 3600,
                                                                 abs=0.005)


@pytest.mark.skipif("sel is None")
def test_capacidad_de_gas_descuenta_la_caida_de_presion():
    """Con v_gobernante la capacidad es menor que v_máx·A con la densidad de entrada."""
    d, q = 0.10226, 0.05
    a = sel.area(d)
    v_sal = lambda qq: qq / a * (1.0 + 0.35 * qq / q)       # crece más rápido que la de entrada
    _t, _e, filas, _a = sel.tabla_capacidad(d, q, None, 15.0, v_gobernante=v_sal,
                                            donde_v="a la salida")
    cap = float(filas[-1][2].replace(",", "")) / 3600.0
    assert v_sal(cap) == pytest.approx(15.0, rel=1e-4)
    assert cap < sel.caudal_limite(d, 15.0)                 # menor que la estimación de entrada
    assert "a la salida" in filas[-1][-1]


# ================================================================ específicas de línea de vapor
import copy
import json
import os

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
ESCENARIO = os.path.join(CASOS, "ESCENARIO_principal_12in_150m.json")


def _caso(ruta=ESCENARIO):
    return json.load(open(ruta, encoding="utf-8"))


def test_capacidad_maxima_respeta_la_velocidad_de_salida():
    """P2-4. Anunciaba 130,411 kg/h, caudal con el que la salida llega a 55.04 m/s (límite 50.9)."""
    from linea_vapor import motor

    res = motor.calcular(_caso())
    filas = res["tabla_capacidad"][2]
    cap = float([f for f in filas if "máxima" in f[0]][0][2].replace(",", ""))
    assert cap == pytest.approx(121887.7, rel=1e-3)      # antes: 130,411.16

    c2 = copy.deepcopy(_caso()); c2["flujo"]["valor"] = cap
    assert motor.calcular(c2)["v2"] == pytest.approx(50.9, abs=0.02)
    c3 = copy.deepcopy(_caso()); c3["flujo"]["valor"] = 130411.16
    assert motor.calcular(c3)["v2"] == pytest.approx(55.04, abs=0.02)   # el reporte del revisor


def test_la_capacidad_coincide_con_el_dictamen_del_motor():
    """Al caudal de capacidad el motor debe dictaminar CUMPLE, y por encima NO CUMPLE."""
    from linea_vapor import motor

    res = motor.calcular(_caso())
    cap = float([f for f in res["tabla_capacidad"][2] if "máxima" in f[0]][0][2].replace(",", ""))
    for factor, esperado in ((0.999, "CUMPLE"), (1.02, "NO CUMPLE")):
        c = copy.deepcopy(_caso()); c["flujo"]["valor"] = cap * factor
        v = [x for x in motor.calcular(c)["verificaciones"] if "Velocidad máxima" in x[0]]
        assert v and v[0][3] == esperado, (factor, v)


def test_sin_caida_de_presion_la_capacidad_es_la_de_siempre():
    """Con L = 0 y sin accesorios la velocidad no cambia en el tramo: Q_máx = v_máx·A."""
    from linea_vapor import motor
    from linea_vapor.nucleo import seleccion as sel

    res = motor.calcular(json.load(open(os.path.join(
        CASOS, "DM011_principal_cog_V_VI_a_M3_12in.json"), encoding="utf-8")))
    assert res["L"] == 0 and res["k_total"] == 0
    assert res["v1"] == pytest.approx(res["v2"])
    cap_m3s = sel.caudal_limite(res["d"], 50.9)
    filas = res["tabla_capacidad"][2]
    anunciada = float([f for f in filas if "máxima" in f[0]][0][2].replace(",", ""))
    assert anunciada == pytest.approx(cap_m3s / res["e1"].v * 3600, rel=1e-3)


def test_segmentacion_converge():
    """Justifica N_SEG_BARRIDO: el estado de salida ya está convergido con pocos segmentos.

    Las marchas auxiliares (capacidad, curva, barrido) se repiten decenas de veces, así que usan
    N_SEG_BARRIDO en vez de los 60 del dictamen. Esta prueba comprueba que esa economía no cambia
    el resultado. Si se baja N_SEG_BARRIDO, aquí se verá.
    """
    from linea_vapor import motor
    from linea_vapor.nucleo.hidraulica import area

    res = motor.calcular(_caso())
    e1, d, eps, L, k = res["e1"], res["d"], res["eps"], res["L"], res["k_total"]
    a = area(d)
    for m in (res["m"], 121887.73 / 3600):               # al flujo capturado y al de capacidad
        v = {}
        for n in (motor.N_SEG_BARRIDO, 60, 120):
            e2, _p = motor.marcha(e1, d, eps, L, k, m, n)
            v[n] = m * e2.v / a
        assert v[motor.N_SEG_BARRIDO] == pytest.approx(v[60], rel=1e-5), v
        assert v[60] == pytest.approx(v[120], rel=1e-5), v


def test_marcha_es_la_misma_que_usa_calcular():
    """marcha() se extrajo de calcular(): deben dar el mismo estado de salida."""
    from linea_vapor import motor
    from linea_vapor.nucleo.hidraulica import area

    res = motor.calcular(_caso())
    e2, perfil = motor.marcha(res["e1"], res["d"], res["eps"], res["L"], res["k_total"], res["m"], 60)
    assert res["m"] * e2.v / area(res["d"]) == pytest.approx(res["v2"], rel=1e-12)
    assert perfil == res["perfil"]
