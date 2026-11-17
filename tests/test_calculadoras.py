"""Pruebas por calculadora: caso ordinario contra cálculo independiente, caso límite,
caso extremo y entradas inválidas (sección 5 de las instrucciones del proyecto)."""
import math

import pytest

from casos import CASOS
from calculadoras.calculos import CALCULADORAS, POR_ID, buscar
from calculadoras.nucleo import constantes as K, psicrometria as ps
from calculadoras.nucleo.atmosfera import presion_por_altitud
from calculadoras.nucleo.modelo import ErrorEntrada


def calc(cid, **cambios):
    datos = dict(CASOS[cid])
    datos.update(cambios)
    return POR_ID[cid].calcular(datos)


# ---------------------------------------------------------------------------
# Registro
# ---------------------------------------------------------------------------
def test_registro_completo():
    assert len(CALCULADORAS) == 15
    assert set(CASOS) == set(POR_ID)
    assert [c.id for c in buscar("bulbo humedo")] == ["torre"]
    assert "banda" in [c.id for c in buscar("TRANSPORTADOR")]


@pytest.mark.parametrize("cid", sorted(CASOS))
def test_caso_ordinario_sin_errores_y_finito(cid):
    r = calc(cid)
    assert r.salidas
    for s in r.salidas:
        if isinstance(s.valor, float):
            assert math.isfinite(s.valor), s.etiqueta


@pytest.mark.parametrize("cid", sorted(CASOS))
def test_texto_no_numerico_rechazado(cid):
    c = POR_ID[cid]
    campo = next(x for x in c.campos if x.tipo in ("real", "entero"))
    with pytest.raises(ErrorEntrada):
        calc(cid, **{campo.clave: "abc"})


# ---------------------------------------------------------------------------
# Ductos
# ---------------------------------------------------------------------------
def test_ductos_contra_calculo_a_mano():
    r = calc("ductos")
    q = 10000 / 3600
    d = math.sqrt(4 * q / (math.pi * 20))
    dp = 0.02 * 50 / d * 1.2 * 20 ** 2 / 2
    assert r["diametro_m"] == pytest.approx(d)
    assert r["dp_total_pa"] == pytest.approx(dp)
    assert r["potencia_kw"] == pytest.approx(dp * q / 0.7 / 1000)
    # El original (mm H₂O con 9.795 y /102) daba prácticamente lo mismo: método conservado
    original = q * (dp / 9.795) / (0.7 * 102)
    assert r["potencia_kw"] == pytest.approx(original, rel=3e-3)


def test_ductos_limite_velocidad_minima_y_laminar():
    r = calc("ductos", velocidad=15, velocidad_minima=18)
    assert any("sedimentar" in a for a in r.advertencias)
    lam = calc("ductos", caudal=0.05, velocidad=0.1, friccion=0)
    assert lam["reynolds"] < 2300
    assert lam["friccion"] == pytest.approx(64 / lam["reynolds"])


def test_ductos_colebrook_y_entradas_invalidas():
    r = calc("ductos", friccion=0, rugosidad=0.15, densidad=0, altitud=2240)
    assert r["densidad"] == pytest.approx(presion_por_altitud(2240) / (287.042 * 293.15), rel=1e-6)
    assert 0.01 < r["friccion"] < 0.03
    for malo in (dict(eficiencia=0), dict(caudal=-5), dict(velocidad=0), dict(eficiencia=1.5)):
        with pytest.raises(ErrorEntrada):
            calc("ductos", **malo)


# ---------------------------------------------------------------------------
# Colector
# ---------------------------------------------------------------------------
def test_colector_potencia_y_almacenamiento():
    r = calc("colector")
    q = 10000 / 3600
    assert r["potencia_kw"] == pytest.approx(200 * 9.80665 * q / 0.8 / 1000)
    original = (200 * 9.80665) * q / (0.8 * 102)
    assert original / r["potencia_kw"] == pytest.approx(1000 / 102)  # error original de 9.8×
    assert r["area_filtracion"] == pytest.approx(10000 / 60 / 1.2)
    assert r["volumen_tolva"] == pytest.approx(10000 * 10e-3 * 0.99 * 12 / 1100)


def test_colector_invalidos():
    with pytest.raises(ErrorEntrada):
        calc("colector", relacion_aire_tela=0)
    with pytest.raises(ErrorEntrada):
        calc("colector", densidad_polvo=0)
    r = calc("colector", carga_polvo=0, tipo_polvo="Fino — 1.0 m/min (criterio original)", relacion_aire_tela=0)
    assert "volumen_tolva" not in r and r.salida("area_filtracion").nivel == "O"


# ---------------------------------------------------------------------------
# Soplador
# ---------------------------------------------------------------------------
def test_soplador_adiabatico_e_incompresible():
    r = calc("soplador")
    q, p1 = 1000 / 3600, 101325.0
    adi = 1.4 / 0.4 * p1 * q * ((1 + 5000 / p1) ** (0.4 / 1.4) - 1) / 0.8
    assert r["potencia_adiabatica_kw"] == pytest.approx(adi / 1000)
    assert r["potencia_incompresible_kw"] == pytest.approx(5000 * q / 0.8 / 1000)
    original = 5000 * q / (0.8 * 102)
    assert original == pytest.approx(17.02, rel=1e-3)        # valor del original: 9.8× mayor


def test_soplador_extremo_advierte_compresibilidad():
    r = calc("soplador", presion=80000)
    assert r["potencia_incompresible_kw"] > r["potencia_adiabatica_kw"]
    assert any("adiabático" in a for a in r.advertencias)
    assert r["tipo"] == "Soplador tipo Roots o de lóbulos"


# ---------------------------------------------------------------------------
# Bomba de vacío
# ---------------------------------------------------------------------------
def test_vacio_contra_formula_de_compresion():
    r = calc("vacio")
    q = 100 * 0.000471947
    ps_, pd = 10000.0, 101325.0
    teor = 1.4 / 0.4 * ps_ * q * ((pd / ps_) ** (0.4 / 1.4) - 1)
    assert r["potencia_teorica_kw"] == pytest.approx(teor / 1000, rel=1e-5)
    assert r["potencia_eje_kw"] == pytest.approx(teor / 0.85 / 1000, rel=1e-5)
    assert r["potencia_isotermica_kw"] == pytest.approx(ps_ * q * math.log(pd / ps_) / 1000, rel=1e-5)
    original_rev1 = 1.4 / 0.4 * 101.3 * q * (1 - (10 / 101.3) ** (0.4 / 1.4))
    assert original_rev1 / r["potencia_teorica_kw"] == pytest.approx(5.23, rel=0.01)


def test_vacio_limites():
    alto = calc("vacio", altitud=2240)
    assert alto["presion_descarga_kpa"] == pytest.approx(77.16, rel=2e-3)
    assert alto["potencia_teorica_kw"] < calc("vacio")["potencia_teorica_kw"]
    with pytest.raises(ErrorEntrada):
        calc("vacio", presion_succion=120)          # mayor que la atmosférica: antes daba potencia negativa
    with pytest.raises(ErrorEntrada):
        calc("vacio", presion_succion=-5)           # antes daba un número complejo
    m3h = calc("vacio", caudal=169.9, unidad_caudal="m³/h")
    assert m3h["potencia_teorica_kw"] == pytest.approx(calc("vacio")["potencia_teorica_kw"], rel=1e-3)


# ---------------------------------------------------------------------------
# Neumático
# ---------------------------------------------------------------------------
def test_neumatico_balances():
    r = calc("neumatico")
    assert r["capacidad_t_h"] == pytest.approx(4 * r["masa_aire_kg_h"] / 1000)
    assert r["dp_solidos_pa"] == pytest.approx(4 * 0.5 * r["dp_aire_pa"])
    q = 1500 / 3600
    assert r["potencia_kw"] == pytest.approx(r["dp_total_pa"] * q / 0.75 / 1000)


def test_neumatico_sin_ks_y_fase_densa_advierten():
    r = calc("neumatico", ks=0, fase="Fase densa")
    assert r["dp_solidos_pa"] == 0
    assert any("SUBESTIMADAS" in a for a in r.advertencias)
    assert any("fase diluida" in a for a in r.advertencias)


# ---------------------------------------------------------------------------
# Torre
# ---------------------------------------------------------------------------
def test_torre_carga_y_correccion_rev0():
    r = calc("torre")
    assert r["carga_kw"] == pytest.approx(10 * 4.186 * 6)
    rev0 = 10 * 4.18 * 6 / 1000
    assert r["carga_kw"] / rev0 == pytest.approx(1000 * 4.186 / 4.18)


def test_torre_entalpias_contra_tabla_ashrae():
    p = 101325
    assert ps.entalpia_saturacion(25, p) == pytest.approx(76.43, abs=0.4)
    assert ps.entalpia_saturacion(30, p) == pytest.approx(100.0, abs=0.5)


def test_torre_balance_de_aire_y_limites():
    r = calc("torre")
    w1, w2 = r["w_entrada"], r["w_salida"]
    balance = r["flujo_aire"] * ((r["h_aire_salida"] - r["h_aire_entrada"]) - (w2 - w1) * 4.186 * 29)
    assert balance == pytest.approx(r["carga_kw"])
    assert r["evaporacion_kgs"] == pytest.approx(r["flujo_aire"] * (w2 - w1))
    with pytest.raises(ErrorEntrada):
        calc("torre", t_salida=23)                  # debajo del bulbo húmedo: imposible
    with pytest.raises(ErrorEntrada):
        calc("torre", t_entrada=29, t_salida=29)
    with pytest.raises(ErrorEntrada):
        calc("torre", t_aire_salida=36)             # aire más caliente que el agua
    solo_carga = calc("torre", t_bulbo_humedo=0)
    assert "flujo_aire" not in solo_carga


# ---------------------------------------------------------------------------
# Banda
# ---------------------------------------------------------------------------
def _area_poligono(puntos):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(puntos, puntos[1:] + puntos[:1]))) / 2


def test_banda_geometria_contra_poligono_e_integral():
    from calculadoras.calculos.banda import area_seccion
    b, l3, lam, beta = 0.85, 0.85 / 3, 35, 20
    sob, art = area_seccion(b, l3, lam, beta)
    lado = (b - l3) / 2
    lr = math.radians(lam)
    pts = [(-l3 / 2, 0), (l3 / 2, 0), (l3 / 2 + lado * math.cos(lr), lado * math.sin(lr)),
           (-l3 / 2 - lado * math.cos(lr), lado * math.sin(lr))]
    assert art == pytest.approx(_area_poligono(pts))
    w = l3 + 2 * lado * math.cos(lr)
    h = w * math.tan(math.radians(beta)) / 4
    n = 20000
    integral = sum(h * (1 - (2 * ((i + 0.5) * w / n - w / 2) / w) ** 2) * w / n for i in range(n))
    assert sob == pytest.approx(integral, rel=1e-6)
    plana = area_seccion(b, b, 0, beta)
    assert plana[1] == 0 and plana[0] == pytest.approx(b ** 2 * math.tan(math.radians(beta)) / 6)


def test_banda_capacidad_y_potencia():
    r = calc("banda")
    k = 0.97                                   # IS 11592, tabla 9, 8°
    assert r["factor_pendiente"] == pytest.approx(k)
    assert r["capacidad_th"] == pytest.approx(r["area"] * k * 1.5 * 3600 * 1.6)
    d = math.radians(8)
    qg = 1600 * r["area"] * k
    fu = 1.5 * 0.02 * 100 * K.G * (30 + (2 * 15 + qg) * math.cos(d)) + qg * K.G * 100 * math.sin(d)
    assert r["fuerza_tangencial"] == pytest.approx(fu / 1000)
    assert r["potencia_motor"] == pytest.approx(fu * 1.5 / 0.9 / 1000)
    assert r["potencia_elevacion"] == pytest.approx(qg * K.G * 100 * math.sin(d) * 1.5 / 1000)


def test_banda_limites():
    with pytest.raises(ErrorEntrada):
        calc("banda", ancho_util=1200)
    with pytest.raises(ErrorEntrada):
        calc("banda", inclinacion=-20, masa_rodillos=0, masa_banda=0, coef_c=1)   # descendente regenerativa
    tabla = calc("banda", velocidad=0, material="Carbón")
    assert tabla["velocidad"] == 2.0 and tabla.salida("velocidad").nivel == "O"


# ---------------------------------------------------------------------------
# Elevador
# ---------------------------------------------------------------------------
def test_elevador_capacidad_sin_truncar_y_eficiencia_separada():
    r = calc("elevador")
    vol = 0.08 * 0.3 * 0.2
    cap = 1000 / 350 * 2.5 * vol * 0.8 * 3600
    assert r["cangilones_m"] == pytest.approx(1000 / 350)
    assert r["capacidad_m3h"] == pytest.approx(cap)
    h_drag = 10 * 0.450                        # KWS: Leq·d_cola (tambor de 450 mm para banda de 400 mm)
    assert r["potencia_elevacion"] == pytest.approx(cap * 1.2 / 3.6 * K.G * (25 + h_drag) / 1000)
    otro = calc("elevador", eficiencia=0.6)
    assert otro["capacidad_th"] == pytest.approx(r["capacidad_th"])          # η ya no cambia la capacidad
    assert otro["potencia_motor"] == pytest.approx(r["potencia_motor"] * 0.85 / 0.6)


def test_elevador_descarga_centrifuga_y_capturas():
    r = calc("elevador", descarga="Descarga centrífuga, materiales livianos", velocidad=0, diametro_tambor=0)
    assert r["relacion_centrifuga"] == pytest.approx(1.2 ** 2 / (K.G * 0.225))
    assert any("centrífuga" in a for a in r.advertencias)
    with pytest.raises(ErrorEntrada):
        calc("elevador", paso_tabla="Capturar paso", paso=0)
    cat = calc("elevador", cangilon_tabla="Capturar volumen de catálogo", volumen_cangilon=3.5)
    assert cat["volumen_cangilon"] == pytest.approx(3.5)


# ---------------------------------------------------------------------------
# Helicoidal
# ---------------------------------------------------------------------------
def _helicoidal_original(**cambios):
    """Método heredado v2.0.x (módulo no registrado en el menú, conservado para trazabilidad)."""
    from calculadoras.calculos.helicoidal_original import CALCULADORA as ORIGINAL
    datos = dict(capacidad=10, factor_capacidad=1.25, material="Arena", densidad=0, carga="30 %",
                 diametro="12 plg", factor_f=0, longitud=6, factor_material=0.4, factor_sobrecarga=1.25,
                 eficiencia=85, angulo=0)
    datos.update(cambios)
    return ORIGINAL.calcular(datos)


def test_helicoidal_original_conservado_para_trazabilidad():
    r = _helicoidal_original()
    # Algoritmo original transcrito (2.204 lb/kg, densidad 99.88 lb/ft³, F por rangos, factores fijos)
    cap = 10 * 1.25 * 1000 * 2.204
    cv = cap / 99.88
    f = 5.45                       # 30 %, 180 < cv ≤ 545
    n = cv / f
    hp = (6 / 0.3048) * (98 * n + cap * 0.4) / 1e6 * 1.25 / 0.85
    assert r["rpm"] == pytest.approx(n, rel=2e-3)
    assert r["potencia_hp"] == pytest.approx(hp, rel=2e-3)
    r = _helicoidal_original(factor_f=12.9)
    assert r["rpm"] == pytest.approx(r["capacidad_pie3h"] / 12.9)
    with pytest.raises(ErrorEntrada):
        _helicoidal_original(capacidad=400)
    assert "helicoidal_original" not in POR_ID


# ---------------------------------------------------------------------------
# Aerodeslizador
# ---------------------------------------------------------------------------
def test_aerodeslizador_ergun_y_fluidizacion():
    from calculadoras.calculos.aerodeslizador import ergun_por_metro
    r = calc("aerodeslizador")
    eps, dp, mu, rg, rb, h = 0.5, 30e-6, 1.8e-5, 1.2, 1100, 0.06
    umf = r["u_mf"] / 1000
    assert ergun_por_metro(umf, eps, dp, mu, rg) * h == pytest.approx(rb * K.G * h, rel=1e-9)
    u = 1.5 / 60
    erg = (150 * mu * (1 - eps) ** 2 * u / (eps ** 3 * dp ** 2) + 1.75 * rg * (1 - eps) * u ** 2 / (eps ** 3 * dp)) * h
    assert r["dp_ergun"] == pytest.approx(erg)
    assert r["fluidiza"] is True and r["dp_lecho"] == pytest.approx(rb * K.G * h)
    assert r["capacidad_th"] == pytest.approx(3 * 0.4 * 0.06 * 1100 * 3.6)


def test_aerodeslizador_no_fluidiza_y_sin_aire():
    r = calc("aerodeslizador", aire_especifico=0.05)
    assert r["fluidiza"] is False and any("no fluidiza" in a for a in r.advertencias)
    assert "caudal_aire" not in calc("aerodeslizador", longitud=0)
    with pytest.raises(ErrorEntrada):
        calc("aerodeslizador", porosidad=1)


# ---------------------------------------------------------------------------
# Tolva
# ---------------------------------------------------------------------------
def test_tolva_geometria_y_beverloo():
    r = calc("tolva")
    v = 3000 / 1200
    h = 3 * v / (4 + 0.1 + math.sqrt(0.4))
    d0 = math.sqrt(0.4 / math.pi)
    assert r["altura"] == pytest.approx(h)
    assert r["flujo_kg_s"] == pytest.approx(0.58 * 1200 * math.sqrt(K.G) * (d0 - 1.4 * 0.05e-3) ** 2.5)
    assert r["angulo_arista"] < r["angulo_plano"]
    original_h = v / ((4 + 0.1) / 2)
    assert original_h / r["altura"] == pytest.approx(0.77, abs=0.01)


def test_tolva_limites():
    with pytest.raises(ErrorEntrada):
        calc("tolva", area_inferior=4)
    with pytest.raises(ErrorEntrada):
        calc("tolva", area_inferior=1e-6, particula=5)     # orificio menor que k·d: arqueo
    with pytest.raises(ErrorEntrada):
        calc("tolva", material="Otro (capturar densidad)", densidad=0)


# ---------------------------------------------------------------------------
# Silo
# ---------------------------------------------------------------------------
def test_silo_geometria_presiones_y_espesor():
    from calculadoras.nucleo.solidos import janssen
    r = calc("silo")
    v = 100000 / 1300
    ht = (4 - 0.3) / 2 / math.tan(math.radians(30))
    vt = math.pi * ht / 12 * (16 + 1.2 + 0.09)
    hc = (v - vt) / (math.pi * 4)
    assert r["altura_cilindro"] == pytest.approx(hc)
    j = janssen(hc, 1300, 4, 0.5, 0.4)
    assert r["ph"] == pytest.approx(j["ph"] / 1000)
    t = j["ph"] * 1.2 * 2 / (150e6 * 0.85) * 1000 + 1.5
    assert r["espesor_requerido"] == pytest.approx(t)
    assert r["espesor_adoptado"] == pytest.approx(max(t, 4))
    assert r["ph"] < 1300 * K.G * hc / 1000          # Janssen < hidrostática (el original usaba ρ·g·h)


def test_silo_limites():
    r = calc("silo", masa=5000)
    assert r["altura_cilindro"] == 0 and any("cabe en la tolva" in a for a in r.advertencias)
    with pytest.raises(ErrorEntrada):
        calc("silo", diametro_descarga=5)
    alto = calc("silo", masa=2_000_000)
    assert alto["ph"] < alto["ph_max"]


# ---------------------------------------------------------------------------
# Viga
# ---------------------------------------------------------------------------
E, I_RECT = 210e9, 0.1 * 0.2 ** 3 / 12
P = 1000 * K.G


def test_viga_formulas_clasicas():
    vol = calc("viga")
    assert vol["deflexion_max"] == pytest.approx(P * 2 ** 3 / (3 * E * I_RECT) * 1000, rel=1e-9)
    assert vol["momento_max"] == pytest.approx(P * 2 / 1000)
    simple = calc("viga", tipo="Simplemente apoyada (apoyos en x = 0 y x = L)", posicion=1)
    assert simple["deflexion_max"] == pytest.approx(P * 8 / (48 * E * I_RECT) * 1000, rel=1e-6)
    assert simple["momento_max"] == pytest.approx(P * 2 / 4 / 1000, rel=1e-6)
    w = 500 * K.G
    uni = calc("viga", tipo="Simplemente apoyada (apoyos en x = 0 y x = L)", carga_puntual=0, carga_distribuida=500)
    assert uni["deflexion_max"] == pytest.approx(5 * w * 16 / (384 * E * I_RECT) * 1000, rel=1e-6)
    vu = calc("viga", carga_puntual=0, carga_distribuida=500)
    assert vu["deflexion_max"] == pytest.approx(w * 16 / (8 * E * I_RECT) * 1000, rel=1e-9)


def _deflexion_numerica_voladizo(L, a, EI, n=20000):
    """Doble integración independiente de M/EI con y(0) = y'(0) = 0 (empotramiento en x = 0)."""
    dx = L / n
    theta = y = 0.0
    for i in range(n):
        x = (i + 0.5) * dx
        m = P * (a - x) if x < a else 0.0
        theta += m / EI * dx
        y += theta * dx
    return y


def test_viga_carga_intermedia_contra_integracion():
    r = calc("viga", posicion=0.5)
    assert r["momento_max"] == pytest.approx(P * 0.5 / 1000)       # el original daba P·(L − a): 3 veces más
    assert r["deflexion_max"] / 1000 == pytest.approx(_deflexion_numerica_voladizo(2, 0.5, E * I_RECT), rel=1e-3)
    assert r["deflexion_max"] / 1000 == pytest.approx(P * 0.25 * (6 - 0.5) / (6 * E * I_RECT), rel=1e-9)


def test_viga_secciones():
    circ = calc("viga", seccion="Circular maciza", d=100)
    i_c = math.pi * 0.1 ** 4 / 64
    assert circ["esfuerzo_flexion"] == pytest.approx(P * 2 * 0.05 / i_c / 1e6)     # c = d/2 (antes 0.1 fijo)
    i_beam = calc("viga", seccion="I simétrica", b=100, h=200, tf=10, tw=6)
    assert i_beam["inercia"] == pytest.approx((0.1 * 0.2 ** 3 - 0.094 * 0.18 ** 3) / 12 * 1e8)
    with pytest.raises(ErrorEntrada):
        calc("viga", seccion="Tubo circular", d=100, t=60)
    with pytest.raises(ErrorEntrada):
        calc("viga", posicion=3)
    with pytest.raises(ErrorEntrada):
        calc("viga", carga_puntual=0, carga_distribuida=0)


# ---------------------------------------------------------------------------
# Bomba centrífuga
# ---------------------------------------------------------------------------
def test_bomba_reproduce_prueba_pdf_con_supuestos_originales():
    r = calc("bomba", elevacion=0, friccion=0.02, cribas=1, limpiadores_hd=14, eficiencia=0,
             k_codo=0.5, k_valvula=1.0, k_tee=1.8)  # K originales capturados
    assert r["altura_total"] == pytest.approx(562.85, abs=0.05)
    assert r["potencia_hidraulica"] == pytest.approx(175.39, rel=1e-3)
    assert any("solo se reporta la potencia hidráulica" in a for a in r.advertencias)


def test_bomba_altura_potencia_y_npsh():
    r = calc("bomba")
    v = 1234 * K.PIE3S_POR_GPM / (math.pi * (8 / 12) ** 2 / 4)
    assert r["velocidad"] == pytest.approx(v)
    tdh = 20 + 14 * K.PIES_POR_PSI_AGUA + r["h_friccion"] + r["h_accesorios"] + 30
    assert r["altura_total"] == pytest.approx(tdh)
    assert r["potencia_freno"] == pytest.approx(1234 * tdh / 3960 / 0.75)
    patm = presion_por_altitud(2240) / K.PA_POR_PSI
    pv = ps.presion_saturacion(20) / K.PA_POR_PSI
    assert r["npsha"] == pytest.approx((patm - pv) * K.PIES_POR_PSI_AGUA + 5 - 2)


def test_bomba_limites():
    with pytest.raises(ErrorEntrada):
        calc("bomba", elevacion=-500, presion_descarga=0, cribas=0)
    laminar = calc("bomba", caudal=1, viscosidad=500)
    assert laminar["friccion"] == pytest.approx(64 / laminar["reynolds"])
    densa = calc("bomba", ge=1.5)
    assert densa["h_presion"] == pytest.approx(14 * K.PIES_POR_PSI_AGUA / 1.5)


# ---------------------------------------------------------------------------
# Secador
# ---------------------------------------------------------------------------
def test_secador_balances_de_masa_y_energia():
    r = calc("secador")
    assert r["producto"] + r["agua_evaporada"] == pytest.approx(3763.6)
    assert r["agua_final"] / r["producto"] == pytest.approx(0.03)
    p = presion_por_altitud(1860)
    w_in = ps.humedad_por_hr(20, 50, p)
    cp_h = 1.006 + 1.86 * w_in
    assert r["aire_seco"] * cp_h * (400 - 110) / 3600 == pytest.approx(r["q_total"])
    assert r["w_salida"] == pytest.approx(w_in + r["agua_evaporada"] / r["aire_seco"])
    assert r["q_total"] == pytest.approx(r["q_util"] * 1.2)
    assert math.pi * r["diametro"] ** 2 / 4 * r["longitud"] == pytest.approx(r["volumen"])


def test_secador_ua_perry_contra_forma_si_publicada():
    from calculadoras.calculos.secador import ua_perry
    g, d = 4456.0, 1.13
    g_si = g / 3600
    # Pacheco y Stella (Braz. J. Chem. Eng.): Ua = 244.7·G^0.67/D en W/(m³·°C), G en kg/(m²·s)
    assert ua_perry(g, d) == pytest.approx(244.7 * g_si ** 0.67 / d, rel=0.04)


def test_secador_base_seca_equivalente():
    humeda = calc("secador")
    xi_s = 0.12 / 0.88 * 100
    xf_s = 0.03 / 0.97 * 100
    seca = calc("secador", base="Base seca (kg agua / kg sólido seco × 100)", humedad_inicial=xi_s,
                humedad_final=xf_s)
    assert seca["agua_evaporada"] == pytest.approx(humeda["agua_evaporada"], rel=1e-9)


def test_secador_limites():
    with pytest.raises(ErrorEntrada):
        calc("secador", humedad_final=15)
    # Aire de salida por debajo del bulbo húmedo de entrada (≈ 24.2 °C): quedaría sobresaturado
    with pytest.raises(ErrorEntrada, match="sobresaturado"):
        calc("secador", t_aire_entrada=60, t_aire_salida=24, t_solido_salida=22, perdidas=0)
    with pytest.raises(ErrorEntrada):
        calc("secador", t_aire_salida=70)          # aire más frío que el sólido en la salida (flujo paralelo)
    ua = calc("secador", metodo_ua="Capturar Ua", ua=150)
    assert ua["ua"] == 150


def test_beverloo_advierte_polvos_finos():
    """Beverloo solo es aplicable a sólidos gruesos: debe advertir con partículas finas o sin dato."""
    for cid in ("tolva", "silo"):
        fino = POR_ID[cid].calcular(dict(CASOS[cid], particula=0.05))
        assert any("NO es aplicable a polvos finos" in a for a in fino.advertencias), cid
        sin_dato = POR_ID[cid].calcular(dict(CASOS[cid], particula=0))
        assert any("no capturado" in a for a in sin_dato.advertencias), cid
        grueso = POR_ID[cid].calcular(dict(CASOS[cid], particula=2))
        assert not any("Beverloo" in a for a in grueso.advertencias), cid


def test_bomba_curva_del_sistema():
    """Hallazgo de la prueba en vivo: la curva sumaba las pérdidas por equipo como constantes.
    A caudal cero la curva debe valer la altura estática; al caudal de diseño, la TDH."""
    from calculadoras.calculos.bomba import altura_estatica, curva_sistema

    d = POR_ID["bomba"].validar(CASOS["bomba"])
    qs, hs = curva_sistema(d)
    h_presion, h_equipos = altura_estatica(d)
    assert h_equipos > 0
    assert qs[0] == 0 and hs[0] == pytest.approx(d["elevacion"] + h_presion)
    i = qs.index(min(qs, key=lambda q: abs(q - d["caudal"])))
    assert qs[i] == pytest.approx(d["caudal"])
    assert hs[i] == pytest.approx(POR_ID["bomba"].calcular(CASOS["bomba"])["altura_total"], rel=1e-9)
    assert all(b > a for a, b in zip(hs, hs[1:]))  # creciente con el caudal


def test_viga_modulo_capturado_tiene_prioridad():
    """Hallazgo de la prueba en vivo: con «Acero» elegido, un E = 200 GPa capturado se ignoraba (se usaba 210)."""
    base = dict(tipo=CASOS["viga"]["tipo"], longitud=2, carga_puntual=1000, posicion=2, carga_distribuida=0,
                material="Acero", seccion="Rectangular maciza", b=100, h=200,
                norma="Ninguna (solo análisis elástico)")
    capturado = POR_ID["viga"].calcular(dict(base, modulo=200))
    inercia = 0.1 * 0.2 ** 3 / 12
    assert capturado["modulo_e"] == pytest.approx(200)
    assert capturado["deflexion_max"] == pytest.approx(1000 * 9.80665 * 2 ** 3 / (3 * 200e9 * inercia) * 1000, rel=1e-9)
    assert any("E capturado" in n for n in capturado.notas)
    lista = POR_ID["viga"].calcular(dict(base, modulo=0))
    assert lista["modulo_e"] == pytest.approx(210)
    from calculadoras.calculos.viga import PERSONALIZADO

    with pytest.raises(ErrorEntrada, match="módulo de elasticidad"):
        POR_ID["viga"].calcular(dict(base, material=PERSONALIZADO, modulo=0))


@pytest.mark.parametrize("cid, cambios, clave, esperado", [
    ("colector", {"tipo_polvo": "Fino — 1.0 m/min (criterio original)", "relacion_aire_tela": 1.5},
     "relacion_aire_tela", 1.5),
    ("elevador", {"paso": 400}, "cangilones_m", 2.5),
])
def test_dato_capturado_tiene_prioridad_sobre_la_lista(cid, cambios, clave, esperado):
    """Regla común (hallazgo de la prueba en vivo en la viga): un valor capturado > 0 nunca se ignora en silencio."""
    calc = POR_ID[cid]
    opciones = {c.clave: c.opciones for c in calc.campos if c.tipo == "opcion"}
    datos = dict(CASOS[cid], **cambios)
    for k, v in cambios.items():
        if k in opciones:
            assert v in opciones[k], f"opción inexistente: {v}"
    r = calc.calcular(datos)
    assert r[clave] == pytest.approx(esperado)
    assert any("capturad" in n for n in r.notas)


def test_secador_ua_capturado_tiene_prioridad():
    r = POR_ID["secador"].calcular(dict(CASOS["secador"], ua=150))
    assert r["ua"] == pytest.approx(150) and any("Ua capturado" in n for n in r.notas)
