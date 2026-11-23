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
    from linea_agua.nucleo import presion as pres
except ImportError:                     # gas y tanque pulmón, en la raíz del paquete
    from linea_agua import presion as pres

try:
    from linea_agua.nucleo import espesor as esp
except ImportError:
    esp = None

try:
    from linea_agua.nucleo import seleccion as sel
except ImportError:
    try:
        from linea_agua import seleccion as sel
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


# ================================================================ integración (línea de agua)
import copy
import json
import os

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
DM012 = os.path.join(CASOS, "DM012_deareador_a_HRSG_descarga_4in.json")


def _caso():
    return json.load(open(DM012, encoding="utf-8"))


def test_la_memoria_no_declara_cumple_fuera_de_dominio():
    """De punta a punta: verificaciones, resumen, tabla y advertencias deben ser coherentes."""
    from linea_agua.memoria import evaluar

    c = _caso()
    c["espesor"] = dict(c["espesor"], t_nominal_mm=30.0, c_por_ano_in=0.0, vida_util_anos=0,
                        p_diseno={"valor": 10000, "unidad": "psig"},
                        s={"valor": 20000, "unidad": "psi", "fuente": "prueba de regresión"})
    m = evaluar(c)
    estados = {v[0]: v[3] for v in m.verificaciones}
    assert estados["Presión de diseño ≤ presión máxima admisible"] == "NO EVALUABLE"
    assert estados["Espesor de pared (t_m ≤ nominal − tolerancia)"] == "NO EVALUABLE"
    assert not any(e == "CUMPLE" for k, e in estados.items() if "resión" in k or "spesor" in k)
    resumen = dict(m.resumen)
    assert "no evaluable" in resumen["Presión máxima admisible"]
    assert any("304.1.2(b)" in a for a in m.advertencias)
    tit = [t[0] for t in m.tablas if "Presión máxima admisible" in t[0]][0]
    assert "fuera del dominio" in tit


def test_el_caso_normal_sigue_dictaminando():
    """El caso real de la memoria no cambia: sigue dando NO CUMPLE contra 991 psig."""
    from linea_agua.memoria import evaluar

    m = evaluar(_caso())
    ver = [v for v in m.verificaciones if v[0] == "Presión de diseño ≤ presión máxima admisible"]
    assert ver and ver[0][3] in ("CUMPLE", "NO CUMPLE")
    assert "991" in ver[0][2]
    assert "no evaluable" not in dict(m.resumen)["Presión máxima admisible"]


def test_corrosion_negativa_detiene_el_calculo_completo():
    """El rechazo debe llegar al usuario como error de entrada, no como un resultado inflado."""
    from linea_agua.motor import ErrorEntrada, calcular

    c = _caso()
    c["espesor"] = dict(c["espesor"], c_por_ano_in=-0.00625)
    with pytest.raises(ErrorEntrada, match="corrosión no puede ser negativa"):
        calcular(c)


def test_redondeo_de_capacidad_hacia_el_lado_seguro():
    """Máximo: se redondea hacia abajo. Mínimo: hacia arriba. Ambos quedan del lado que cumple."""
    # Di = 100 mm: A = π·0.1²/4 = 0.0078540 m²
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


def test_memoria_anuncia_una_capacidad_que_cumple():
    """La fila «Capacidad máxima» de la memoria se redondea hacia abajo: reintroducida, cumple."""
    import glob
    import json
    import os

    from linea_agua import memoria, motor

    casos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
    revisados = 0
    for ruta in sorted(glob.glob(os.path.join(casos, "*.json"))):
        c = json.load(open(ruta, encoding="utf-8"))
        vmax = (c.get("criterio_velocidad") or {}).get("v_max_m_s")
        filas = [r for r in memoria.evaluar(c).resultados if r[0].startswith("Capacidad máxima")]
        if vmax in (None, "") or not filas:
            continue
        c["caudal"] = {"valor": float(filas[0][1].split(" ")[0].replace(",", "")), "unidad": "m³/h"}
        r = motor.calcular(c)
        v = r["v"] if "v" in r else r["tramo"]["v"]
        assert v <= float(vmax), (ruta, filas[0], v)
        revisados += 1
    assert revisados
