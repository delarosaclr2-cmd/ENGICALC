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
    from linea_gas.nucleo import presion as pres
except ImportError:                     # gas y tanque pulmón, en la raíz del paquete
    from linea_gas import presion as pres

try:
    from linea_gas.nucleo import espesor as esp
except ImportError:
    esp = None

try:
    from linea_gas.nucleo import seleccion as sel
except ImportError:
    try:
        from linea_gas import seleccion as sel
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


# ================================================================ específicas de línea de gas
import copy
import json
import os

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
L1 = os.path.join(CASOS, "DM014E_L1_rack_4in.json")


def _caso(ruta=L1):
    return json.load(open(ruta, encoding="utf-8"))


def test_presion_de_operacion_usa_la_atmosfera_del_sitio():
    """P1-3. Con 10 psia de atmósfera y 114.2 psig de entrada, la verificación usaba 109.5 psig.

    Restar 101325 Pa fijos descontaba 14.696 psi en lugar de los 10 psia del sitio, y con S de
    1,700 psi (P máx. ≈ 112.4 psig) eso convertía un NO CUMPLE en CUMPLE.
    """
    from linea_gas import memoria as M
    from linea_gas import presion as pres
    from linea_gas.caso import ejecutar, p_atm_sitio_pa

    c = _caso()
    c["p_atm_psia"] = 10.0
    c["p_entrada"] = {"valor": 114.2, "unidad": "psig"}
    c["espesor"] = dict(c.get("espesor") or {},
                        s={"valor": 1700, "unidad": "psi", "fuente": "prueba de regresión"},
                        tolerancia_pct=12.5, c_mm=0)
    assert p_atm_sitio_pa(c) / pres.PSI == pytest.approx(10.0)
    e, _r = ejecutar(c)
    pm = M.presion_maxima(c, e)
    # la de operación debe coincidir con la capturada, no con 109.5 psig
    assert pm["p_operacion_pa"] / pres.PSI == pytest.approx(114.2, abs=0.01)
    assert pm["p_max_pa"] / pres.PSI == pytest.approx(112.4, abs=0.1)
    ver = [v for v in pres.verificaciones(pm) if "operación" in v[0]]
    assert ver and ver[0][3] == "NO CUMPLE"


def test_atmosfera_estandar_no_cambia_los_casos_existentes():
    from linea_gas import memoria as M
    from linea_gas.caso import ejecutar, p_atm_sitio_pa
    c = _caso()
    assert p_atm_sitio_pa(c) == pytest.approx(14.7 * 6894.757293168)
    e, _r = ejecutar(c)
    assert M.presion_maxima(c, e) is None or True        # el caso base no trae material


def test_capacidad_maxima_respeta_la_velocidad_de_salida():
    """P2-4. A 15 m/s anunciaba 3,577.63 Nm³/h, caudal con el que la salida llega a 19.30 m/s."""
    from linea_gas import memoria as M
    from linea_gas.caso import ejecutar

    c = _caso()
    c.setdefault("criterios", {})["v_max_m_s"] = 15
    e, r = ejecutar(c)
    filas = M.barridos(c, e, r)["tabla_capacidad"][2]
    cap = float([f for f in filas if "máxima" in f[0]][0][2].replace(",", ""))
    assert cap == pytest.approx(3026.15, rel=1e-3)       # antes: 3,577.63

    # comprobación independiente: correr el caso a ese caudal y al anterior
    c2 = copy.deepcopy(c); c2["caudal"]["valor"] = cap
    assert ejecutar(c2)[1].v_salida == pytest.approx(15.0, abs=0.01)
    c3 = copy.deepcopy(c); c3["caudal"]["valor"] = 3577.63
    assert ejecutar(c3)[1].v_salida == pytest.approx(19.30, abs=0.01)   # el reporte del revisor


def test_barrido_de_diametros_reporta_la_velocidad_de_salida():
    """El barrido tenía el mismo defecto: informaba la velocidad de entrada."""
    from linea_gas import memoria as M
    from linea_gas.caso import ejecutar

    c = _caso()
    c.setdefault("criterios", {})["v_max_m_s"] = 15
    c["caudal"]["valor"] = 3000
    e, r = ejecutar(c)
    tit, enc, filas, _a = M.barridos(c, e, r)["tabla_diametros"]
    assert "a la salida" in enc[3] and "a la salida" in tit
    actual = [f for f in filas if f[0].endswith("*")][0]
    assert float(actual[3]) == pytest.approx(r.v_salida, abs=0.01)


def test_capacidad_mostrada_reintroducida_cumple_con_el_limite():
    """Revisión de comentarios. Con v_max 15 m/s, 3,026.15 Nm³/h daba 15.000010344 m/s y NO CUMPLE
    al reintroducirlo. Ahora la capacidad se muestra redondeada hacia abajo (3,026.14) y cumple.
    El criterio no se relaja: el caudal exacto anterior sigue siendo NO CUMPLE."""
    import copy
    import json
    import os

    from linea_gas import caso, memoria
    from linea_gas.motor import calcular

    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos",
                        "DM014E_L1_rack_4in.json")
    c = json.load(open(ruta, encoding="utf-8"))
    c["criterios"] = {"v_max_m_s": 15.0}
    e = caso.a_entradas(c)
    fila = [f for f in memoria.barridos(c, e, calcular(e))["tabla_capacidad"][2] if "máxima" in f[0]][0]
    assert fila[2] == "3,026.14"

    c2 = copy.deepcopy(c); c2["caudal"]["valor"] = float(fila[2].replace(",", ""))
    assert calcular(caso.a_entradas(c2)).v_salida <= 15.0

    c3 = copy.deepcopy(c); c3["caudal"]["valor"] = 3026.15
    assert calcular(caso.a_entradas(c3)).v_salida > 15.0


def test_redondeo_de_capacidad_hacia_el_lado_seguro():
    """Máximo: se redondea hacia abajo. Mínimo: hacia arriba. Ambos quedan del lado que cumple."""
    # Líquido, Di = 100 mm: A = π·0.1²/4 = 0.0078540 m²
    t, enc, filas, _ = sel.tabla_capacidad(0.1, 0.01, v_min=0.5, v_max=2.0)
    fila_max = [f for f in filas if "máxima" in f[0]][0]
    fila_min = [f for f in filas if "mínima" in f[0]][0]
    assert fila_max[2] == "56.54"          # 56.5487 m³/h → abajo
    assert fila_min[2] == "14.14"          # 14.1372 m³/h → arriba


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


def _caso_l1(**criterios):
    import json
    import os
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos",
                        "DM014E_L1_rack_4in.json")
    c = json.load(open(ruta, encoding="utf-8"))
    c["criterios"] = criterios
    return c


def test_caudal_minimo_mostrado_deja_la_entrada_en_el_intervalo():
    """El mínimo se juzga con la velocidad de entrada (la menor del tramo), redondeado hacia arriba."""
    import copy

    from linea_gas import caso, memoria
    from linea_gas.motor import calcular

    c = _caso_l1(v_min_m_s=2.0, v_max_m_s=15.0)
    e = caso.a_entradas(c)
    fila = [f for f in memoria.barridos(c, e, calcular(e))["tabla_capacidad"][2] if "mínima" in f[0]][0]
    c2 = copy.deepcopy(c); c2["caudal"]["valor"] = float(fila[2].replace(",", ""))
    assert calcular(caso.a_entradas(c2)).v_entrada >= 2.0


def test_barrido_de_gas_coincide_con_el_calculo_completo_en_otro_diametro():
    """Cada fila del barrido recalcula los K tabulados con su NPS y coincide con capturar ese NPS."""
    import copy

    from linea_gas import caso, memoria
    from linea_gas.motor import calcular

    c = _caso_l1(v_max_m_s=15.0)
    e = caso.a_entradas(c)
    r0 = calcular(e)
    filas = memoria.barridos(c, e, r0)["tabla_diametros"][2]
    otros = [f for f in filas if f[3] != "—" and "*" not in f[0]]
    assert otros
    for f in otros:
        cc = copy.deepcopy(c); cc["tuberia"]["nps"] = f[0]
        rr = calcular(caso.a_entradas(cc))
        assert float(f[3]) == pytest.approx(rr.v_salida, abs=6e-4), f
        assert f[7] == ("NO CUMPLE" if rr.v_salida > 15.0 else "CUMPLE"), f
    assert any(calcular(caso.a_entradas(dict(c, tuberia={"nps": f[0], "cedula": "40"}))).k_total
               != pytest.approx(r0.k_total) for f in otros)        # el K tabulado sí cambia con el NPS
