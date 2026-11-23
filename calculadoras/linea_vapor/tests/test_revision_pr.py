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


def test_barrido_recalcula_k_por_diametro_y_coincide_con_el_calculo_completo():
    """Revisión de comentarios: el barrido usaba el ΣK del NPS 12 (4.62) para el NPS 8. Al
    seleccionar NPS 8 el cálculo completo da ΣK 4.98 y 51.02 m/s, NO CUMPLE; el barrido mostraba
    50.900 m/s y CUMPLE."""
    from linea_vapor import motor

    c = _caso()
    c["flujo"] = {"valor": 53265.24, "unidad": "kg/h"}
    res = motor.calcular(c)
    assert res["k_total"] == pytest.approx(4.62, abs=0.005)
    fila8 = [f for f in motor.barridos(c, res)["tabla_diametros"][2] if f[0] == "8"][0]

    c8 = copy.deepcopy(c); c8["tuberia"]["nps"] = "8"
    completo = motor.calcular(c8)
    assert completo["k_total"] == pytest.approx(4.98, abs=0.005)
    assert float(fila8[3]) == pytest.approx(completo["v2"], abs=0.01)
    assert float(fila8[3]) == pytest.approx(51.02, abs=0.01)
    assert fila8[7] == "NO CUMPLE"


def test_k_capturado_se_conserva_en_todos_los_diametros():
    """Un K capturado explícitamente no depende del NPS: el barrido debe usar ese mismo valor."""
    from linea_vapor import motor

    c = _caso()
    c["flujo"] = {"valor": 53265.24, "unidad": "kg/h"}
    c["accesorios"] = [{"tipo": "codo90", "cantidad": 8, "k": 0.3}, {"tipo": "check_columpio", "cantidad": 1, "k": 2.0}]
    assert motor._k_total_para_nps(c, "12") == pytest.approx(4.4)
    assert motor._k_total_para_nps(c, "8") == pytest.approx(4.4)

    res = motor.calcular(c)
    c8 = copy.deepcopy(c); c8["tuberia"]["nps"] = "8"
    fila8 = [f for f in motor.barridos(c, res)["tabla_diametros"][2] if f[0] == "8"][0]
    assert float(fila8[3]) == pytest.approx(motor.calcular(c8)["v2"], abs=0.01)


def test_capacidad_mostrada_reintroducida_cumple():
    """La capacidad mostrada, reintroducida tal cual, debe cumplir el límite de salida."""
    from linea_vapor import motor

    res = motor.calcular(_caso())
    cap_txt = [f for f in res["tabla_capacidad"][2] if "máxima" in f[0]][0][2]
    c = copy.deepcopy(_caso()); c["flujo"]["valor"] = float(cap_txt.replace(",", ""))
    v = [x for x in motor.calcular(c)["verificaciones"] if "Velocidad máxima" in x[0]]
    assert v and v[0][3] == "CUMPLE", v


# ======================================== segunda ronda de comentarios del PR: valores límite
def test_redondeo_seguro_nunca_cruza_el_limite():
    """Comentario de revisión: 3,026.149… Nm³/h se mostraba 3,026.15 (redondeo al más cercano), que
    al reintroducirse daba 15.000010344 m/s y NO CUMPLE frente a 15 m/s."""
    assert sel.redondeo_seguro(3026.149, 2, "abajo") == 3026.14
    assert sel.redondeo_seguro(3026.141, 2, "arriba") == 3026.15
    assert sel.redondeo_seguro(56.5487, 2, "abajo") == 56.54
    assert sel.redondeo_seguro(14.1372, 2, "arriba") == 14.14
    with pytest.raises(ValueError):
        sel.redondeo_seguro(1.0, 2, "cercano")


def test_ajustar_al_criterio_corrige_con_el_modelo_del_dictamen():
    """Un caudal resuelto con un modelo barato que excede en el modelo del dictamen se corrige."""
    dictamen = lambda q: 10.0 * q ** 1.2              # la velocidad crece más que linealmente
    q_barato = (15.0 / 10.0) ** (1 / 1.2) * 1.0001      # excede un poco en el dictamen
    q = sel.ajustar_al_criterio(q_barato, 15.0, dictamen, "abajo")
    assert q is not None and dictamen(q) <= 15.0
    q = sel.ajustar_al_criterio(q_barato * 0.99, 15.0, dictamen, "arriba")
    assert q is not None and dictamen(q) >= 15.0
    assert sel.ajustar_al_criterio(1.0, 15.0, dictamen, "abajo") == 1.0     # ya cumple: no se toca


def test_minimo_se_juzga_con_la_velocidad_mas_baja_del_tramo():
    """Como en el dictamen: el máximo con la mayor velocidad (salida), el mínimo con la menor
    (entrada). Q_mín = v_mín·A con la velocidad de entrada."""
    assert sel.estado_velocidad(35.0, 30.5, 50.9) == "CUMPLE"
    assert sel.estado_velocidad(35.0, 30.5, 50.9, v_baja=29.0) == "INFORMATIVO"
    assert sel.estado_velocidad(52.0, 30.5, 50.9, v_baja=29.0) == "NO CUMPLE"
    A = sel.area(0.1)
    lim = sel.limites_de_caudal(0.1, 0.2, v_min=30.5, v_max=50.9, v_gobernante=lambda q: q / A * 1.3)
    assert lim["q_min"] == pytest.approx(30.5 * A)
    assert lim["q_max"] / A * 1.3 <= 50.9


def test_tabla_de_capacidad_comprueba_con_el_modelo_del_dictamen():
    """La capacidad mostrada se comprueba con el modelo que dictamina (vapor: 60 segmentos), no con
    el modelo barato con que se resolvió (8 segmentos)."""
    A = sel.area(0.1)
    barato = lambda q: q / A * 1.30
    dictamen = lambda q: q / A * 1.30 * (1 + 2e-5)      # difiere 2·10⁻⁵, del orden de 8 vs 60 seg.
    q_barato = sel.limites_de_caudal(0.1, 0.2, v_max=50.9, v_gobernante=barato)["q_max"]
    assert dictamen(q_barato) > 50.9                    # sin comprobar, el dictamen diría NO CUMPLE
    t, enc, filas, _ = sel.tabla_capacidad(0.1, 0.2, v_max=50.9, v_gobernante=barato,
                                           v_verificacion=dictamen, donde_v="a la salida")
    fila = [f for f in filas if "máxima" in f[0]][0]
    assert dictamen(float(fila[2].replace(",", "")) / 3600.0) <= 50.9


def test_redondeo_de_capacidad_hacia_el_lado_seguro():
    """Máximo: se redondea hacia abajo. Mínimo: hacia arriba. Ambos quedan del lado que cumple."""
    t, enc, filas, _ = sel.tabla_capacidad(0.1, 0.01, v_min=0.5, v_max=2.0)
    assert [f for f in filas if "máxima" in f[0]][0][2] == "56.54"      # 56.5487 m³/h → abajo
    assert [f for f in filas if "mínima" in f[0]][0][2] == "14.14"      # 14.1372 m³/h → arriba


def test_barrido_coincide_con_el_dictamen_en_cada_diametro():
    """Comentario de revisión: cada fila del barrido debe dar la misma velocidad y el mismo estado
    que el cálculo completo con ese diámetro. 120,000 kg/h prueba un tramo con ΔP/P₁ = 0.62, donde
    8 segmentos diferían 0.28 m/s y la fila se recalcula con los del dictamen."""
    from linea_vapor import motor

    for flujo in (53265.24, 120000.0):
        c = _caso()
        c["flujo"] = {"valor": flujo, "unidad": "kg/h"}
        for f in motor.calcular(c)["tabla_diametros"][2]:
            if f[3] == "—":
                continue
            cc = copy.deepcopy(c); cc["tuberia"]["nps"] = f[0].replace(" *", "")
            rr = motor.calcular(cc)
            ver = [x[3] for x in rr["verificaciones"] if "elocidad" in x[0]]
            est = "NO CUMPLE" if "NO CUMPLE" in ver else ("INFORMATIVO" if "INFORMATIVO" in ver else "CUMPLE")
            assert float(f[3]) == pytest.approx(max(rr["v1"], rr["v2"]), abs=6e-4), (flujo, f)
            assert f[7] == est, (flujo, f, ver)


def test_caudal_minimo_mostrado_deja_la_entrada_en_el_intervalo():
    """El dictamen juzga el mínimo con la velocidad de entrada: el caudal mínimo mostrado,
    reintroducido, no debe producir el aviso de velocidad mínima."""
    from linea_vapor import motor

    fila = [f for f in motor.calcular(_caso())["tabla_capacidad"][2] if "mínima" in f[0]][0]
    c = _caso(); c["flujo"]["valor"] = float(fila[2].replace(",", ""))
    rr = motor.calcular(c)
    assert rr["v1"] >= 30.5
    assert not [x for x in rr["verificaciones"] if "mínima" in x[0]]


def test_memoria_anuncia_una_capacidad_que_cumple():
    """La fila «Capacidad máxima» de la memoria (en t/h) también se redondea hacia abajo y, al
    reintroducirla, el dictamen da CUMPLE."""
    from linea_vapor import memoria, motor

    fila = [r for r in memoria.evaluar(_caso()).resultados if r[0].startswith("Capacidad máxima")][0]
    t_h = float(fila[2].split(" t/h")[0].replace(",", ""))
    c = _caso(); c["flujo"] = {"valor": t_h * 1000.0, "unidad": "kg/h"}
    v = [x for x in motor.calcular(c)["verificaciones"] if "Velocidad máxima" in x[0]]
    assert v and v[0][3] == "CUMPLE", (fila, v)
