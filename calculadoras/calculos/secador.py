"""Secador rotatorio directo (flujo paralelo o contracorriente): balances y dimensionamiento preliminar.

Originales: «calculo del secador.py», «rev 1», «rev 2» (método para fluorita) y
«DS rev 3» a «DS rev 7» (método del documento .docx). No estaba en el menú.

Se reconstruye el método de rev0–rev2, que era el más cercano a una referencia
reconocible (Perry's), y se corrigen los errores demostrados:
- DS: el volumen V = Q/(100·ΔT) se reducía a 10.05·G (92 872 m³ en la prueba);
  el diámetro usaba 9 en lugar de 4 (+50 %); L = τ·(1/v)/sen α era
  dimensionalmente inconsistente; la potencia tampoco tenía unidades de potencia;
  Cp se pedía y no se usaba; no se validaba la humedad del aire (aceptó Y = 5).
- rev0–rev2: bulbo húmedo con la fórmula de Stull truncada; «G + e^0.67» en
  lugar de G^0.67; potencia con diámetro fijo 9.97; calor solo latente.
Ahora: balance de masa (base húmeda o seca), balance de energía completo,
psicrometría ASHRAE con la altitud, verificación de saturación del aire de
salida, diámetro por velocidad del gas, longitud por coeficiente volumétrico Ua
(correlación de Perry's o dato) y consumo de combustible del calentador.
La potencia y las aletas de rev0 se conservan identificadas como criterio original.

v2.1.1: se agrega la disposición a contracorriente (Perry's trata ambas). Los
balances de masa y energía no dependen de la disposición; solo cambian las
diferencias de temperatura extremas de ΔT_ml. Validado contra Geankoplis,
Ejemplo 9.10-2 «Heat Balance on a Dryer» (secador continuo a contracorriente).
"""
from __future__ import annotations

import math

from ..nucleo import constantes as K, fluidos, psicrometria as ps
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             ErrorEntrada, Resultado, requerir)

HUMEDA = "Base húmeda (% del peso total)"
SECA = "Base seca (kg agua / kg sólido seco × 100)"
PERRY = "Correlación de Perry's: Ua = 0.5·G^0.67/D (unidades inglesas)"
CAPTURAR_UA = "Capturar Ua"
PARALELO = "Flujo paralelo (aire y sólido en el mismo sentido)"
CONTRACORRIENTE = "Contracorriente (aire en sentido opuesto al sólido)"

CAMPOS = [
    Campo("alimentacion", "Alimentación húmeda", "kg/h", minimo=0, min_incluido=False, grupo="Producto"),
    Campo("base", "Base de la humedad", tipo="opcion", opciones=(HUMEDA, SECA), defecto=HUMEDA, grupo="Producto",
          ayuda="Rev0–rev2 usaban base húmeda; la serie DS no lo definía."),
    Campo("humedad_inicial", "Humedad inicial", "%", minimo=0, grupo="Producto"),
    Campo("humedad_final", "Humedad final", "%", minimo=0, grupo="Producto"),
    Campo("cp_solido", "Calor específico del sólido seco", "kJ/(kg·K)", minimo=0, min_incluido=False, maximo=5,
          grupo="Producto"),
    Campo("t_solido_entrada", "Temperatura del sólido a la entrada", "°C", minimo=-20, maximo=300, grupo="Producto"),
    Campo("t_solido_salida", "Temperatura del sólido a la salida", "°C", minimo=-20, maximo=300, grupo="Producto"),
    Campo("t_aire_entrada", "Temperatura del aire a la entrada del secador", "°C", minimo=0, maximo=900,
          grupo="Aire"),
    Campo("t_aire_salida", "Temperatura del aire a la salida", "°C", minimo=0, maximo=900, grupo="Aire"),
    Campo("flujo", "Disposición de los flujos", tipo="opcion", opciones=(PARALELO, CONTRACORRIENTE),
          defecto=PARALELO, grupo="Aire",
          ayuda="Solo cambia ΔT_ml (longitud). Los balances de masa y energía son los mismos en ambos casos."),
    Campo("t_ambiente", "Temperatura del aire ambiente", "°C", minimo=-20, maximo=50, grupo="Aire"),
    Campo("hr_ambiente", "Humedad relativa ambiente", "%", minimo=0, maximo=100, grupo="Aire"),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000, grupo="Aire"),
    Campo("latente", "Calor latente de vaporización", "kJ/kg", defecto=0, minimo=0, grupo="Aire",
          ayuda="0 = 2501 − 2.326·t evaluado al bulbo húmedo del aire de entrada."),
    Campo("perdidas", "Pérdidas de calor por la envolvente", "% del calor útil", defecto=20, minimo=0, maximo=100,
          grupo="Aire", ayuda="20 % era el criterio del original (Q_total = 1.2·Q)."),
    Campo("velocidad_aire", "Velocidad permisible del gas en el tambor", "m/s", minimo=0, min_incluido=False,
          maximo=10, grupo="Dimensiones", ayuda="Perry's: típica 3 m/s en flujo paralelo, 2 m/s a contracorriente."),
    Campo("fraccion_libre", "Fracción de la sección libre para el gas", "", defecto=1.0, minimo=0, maximo=1,
          min_incluido=False, grupo="Dimensiones",
          ayuda="1 = toda la sección. (El «9» de la serie DS equivalía a 0.444 sin documentar.)"),
    Campo("metodo_ua", "Coeficiente volumétrico Ua", tipo="opcion", opciones=(PERRY, CAPTURAR_UA), defecto=PERRY,
          grupo="Dimensiones"),
    Campo("ua", "Ua capturado", "W/(m³·K)", defecto=0, minimo=0, grupo="Dimensiones"),
    Campo("pci", "Poder calorífico inferior del combustible", "kJ/kg", defecto=0, minimo=0, grupo="Combustible",
          ayuda="0 = no calcular el combustible."),
    Campo("eficiencia_quemador", "Eficiencia del calentador", "%", defecto=0, minimo=0, maximo=100,
          grupo="Combustible"),
    Campo("masa_galon", "Masa de combustible por galón", "kg/gal", defecto=0, minimo=0, grupo="Combustible",
          ayuda="Para reportar gal/h y L/h. 0 = solo kg/h."),
]


def ua_perry(g_kg_h_m2: float, diametro_m: float) -> float:
    """Ua [W/(m³·K)] por Ua = 0.5·G^0.67/D con G [lb/(h·ft²)], D [ft], Ua [Btu/(h·ft³·°F)] (Perry's)."""
    g_lb = g_kg_h_m2 / K.KG_POR_LIBRA * K.M_POR_PIE ** 2
    ua_ingles = 0.5 * g_lb ** 0.67 / (diametro_m / K.M_POR_PIE)
    return ua_ingles * K.W_POR_BTUH / K.M3_POR_PIE3 * 1.8


def calcular(d: dict) -> Resultado:
    r = Resultado()
    F = d["alimentacion"]
    xi, xf = d["humedad_inicial"] / 100.0, d["humedad_final"] / 100.0
    requerir(xf < xi, "La humedad final debe ser menor que la inicial.")
    if d["base"] == HUMEDA:
        requerir(xi < 1, "En base húmeda la humedad debe ser menor que 100 %.")
        ms = F * (1 - xi)
        agua_i = F * xi
        agua_f = ms * xf / (1 - xf)
    else:
        ms = F / (1 + xi)
        agua_i = ms * xi
        agua_f = ms * xf
    w_ev = agua_i - agua_f

    ts1, ts2 = d["t_solido_entrada"], d["t_solido_salida"]
    tg1, tg2 = d["t_aire_entrada"], d["t_aire_salida"]
    requerir(tg1 > tg2, "El aire debe enfriarse: temperatura de entrada mayor que la de salida.")
    requerir(ts2 >= ts1, "El sólido no puede salir más frío que como entra en un secador.")
    p = presion_por_altitud(d["altitud"])
    try:
        w_in = ps.humedad_por_hr(d["t_ambiente"], d["hr_ambiente"], p)
        t_ev = ps.bulbo_humedo(tg1, w_in, p)
    except ValueError as e:
        raise ErrorEntrada(f"Psicrometría del aire de entrada: {e}") from e
    lam = d["latente"] if d["latente"] > 0 else ps.calor_latente(t_ev)

    q_solido = ms * d["cp_solido"] * (ts2 - ts1) / 3600
    q_residual = agua_f * K.CP_AGUA * (ts2 - ts1) / 3600
    q_evap = w_ev * (K.CP_AGUA * (t_ev - ts1) + lam + K.CP_VAPOR * (tg2 - t_ev)) / 3600
    q_util = q_solido + q_residual + q_evap
    q_perd = q_util * d["perdidas"] / 100
    q_total = q_util + q_perd

    cp_h = ps.calor_humedo(w_in)
    g_aire = q_total * 3600 / (cp_h * (tg1 - tg2))  # kg aire seco/h
    w_out = w_in + w_ev / g_aire
    hr_out = ps.hr_por_humedad(tg2, w_out, p)  # pw/psat(T); válida también por encima de la ebullición
    requerir(hr_out < 100, f"El aire de salida quedaría sobresaturado (HR = {hr_out:.0f} %): aumente la "
                           "temperatura de salida del aire o el flujo de aire.")
    rocio = ps.punto_rocio(w_out, p)

    q_in = g_aire / 3600 * ps.volumen_especifico(tg1, w_in, p)
    q_out = g_aire / 3600 * ps.volumen_especifico(tg2, w_out, p)
    q_diseno = max(q_in, q_out)
    diam = fluidos.diametro_por_caudal(q_diseno, d["velocidad_aire"] * d["fraccion_libre"])
    area = math.pi * diam ** 2 / 4
    g_masico = g_aire / area

    if d["metodo_ua"] == PERRY and d["ua"] <= 0:
        ua, nivel_ua = ua_perry(g_masico, diam), EMPIRICA
    else:  # el dato capturado tiene prioridad sobre la correlación
        requerir(d["ua"] > 0, "Capture el coeficiente volumétrico Ua.")
        ua, nivel_ua = d["ua"], DATO
        if d["metodo_ua"] == PERRY:
            r.nota(f"Se usó el Ua capturado ({d['ua']:g} W/(m³·K)) en lugar de la correlación de Perry's "
                   f"({ua_perry(g_masico, diam):.1f} W/(m³·K)).")
    if d["flujo"] == CONTRACORRIENTE:
        dt1, dt2 = tg1 - ts2, tg2 - ts1
        requerir(dt1 > 0 and dt2 > 0, "A contracorriente el aire de entrada debe estar más caliente que el sólido "
                                      "de salida y el aire de salida más caliente que el sólido de entrada.")
        disposicion = "contracorriente"
    else:
        dt1, dt2 = tg1 - ts1, tg2 - ts2
        requerir(dt1 > 0 and dt2 > 0, "En flujo paralelo el aire debe estar más caliente que el sólido en ambos "
                                      "extremos (aire de salida más caliente que el sólido de salida).")
        disposicion = "flujo paralelo"
    dtml = fluidos.media_logaritmica(dt1, dt2)
    volumen = q_util * 1000 / (ua * dtml)
    largo = volumen / area

    r.agregar("solido_seco", "Sólido seco", ms, "kg/h", 2)
    r.agregar("agua_inicial", "Agua en la alimentación", agua_i, "kg/h", 2)
    r.agregar("agua_final", "Agua en el producto", agua_f, "kg/h", 2)
    r.agregar("producto", "Producto a la salida", ms + agua_f, "kg/h", 2)
    r.agregar("agua_evaporada", "Agua evaporada", w_ev, "kg/h", 2)
    r.agregar("w_entrada", "Humedad absoluta del aire de entrada", w_in, "kg/kg a.s.", 5)
    r.agregar("t_evaporacion", "Bulbo húmedo del aire de entrada (T de evaporación)", t_ev, "°C", 2)
    r.agregar("latente", "Calor latente usado", lam, "kJ/kg", 1, DATO)
    r.agregar("q_solido", "Calor para calentar el sólido", q_solido, "kW", 2)
    r.agregar("q_residual", "Calor para calentar el agua residual", q_residual, "kW", 2)
    r.agregar("q_evaporacion", "Calor para evaporar y sobrecalentar el vapor", q_evap, "kW", 2)
    r.agregar("q_util", "Calor útil", q_util, "kW", 2)
    r.agregar("q_perdidas", "Pérdidas de calor", q_perd, "kW", 2, ORIGINAL if d["perdidas"] == 20 else DATO)
    r.agregar("q_total", "Calor total que cede el aire", q_total, "kW", 2)
    r.agregar("aire_seco", "Flujo de aire seco", g_aire, "kg/h", 1)
    r.agregar("w_salida", "Humedad absoluta del aire de salida", w_out, "kg/kg a.s.", 5)
    r.agregar("hr_salida", "Humedad relativa del aire de salida", hr_out, "%", 1)
    r.agregar("rocio_salida", "Punto de rocío del aire de salida", rocio, "°C", 1)
    r.agregar("caudal_gas", "Caudal de gas de diseño (mayor entre entrada y salida)", q_diseno, "m³/s", 3)
    r.agregar("diametro", "Diámetro interior del tambor", diam, "m", 3)
    r.agregar("flujo_masico_gas", "Flujo másico de gas por área", g_masico, "kg/(h·m²)", 0)
    r.agregar("ua", "Coeficiente volumétrico Ua", ua, "W/(m³·K)", 1, nivel_ua)
    r.agregar("dtml", f"Diferencia media logarítmica ({disposicion})", dtml, "°C", 2)
    r.agregar("volumen", "Volumen del tambor", volumen, "m³", 2, nivel_ua)
    r.agregar("longitud", "Longitud del tambor", largo, "m", 2, nivel_ua)
    r.agregar("relacion_ld", "Relación L/D", largo / diam, "", 2, nivel_ua)

    q_calentador = g_aire / 3600 * cp_h * (tg1 - d["t_ambiente"])
    r.agregar("q_calentador", "Calor del calentador (aire ambiente → entrada)", q_calentador, "kW", 2)
    r.agregar("eficiencia_termica", "Eficiencia térmica (calor útil / calentador)", q_util / q_calentador * 100, "%", 1)
    if d["pci"] > 0:
        requerir(d["eficiencia_quemador"] > 0, "Capture la eficiencia del calentador para el combustible.")
        comb = q_calentador / (d["pci"] * d["eficiencia_quemador"] / 100) * 3600
        r.agregar("combustible_kg_h", "Consumo de combustible", comb, "kg/h", 2)
        if d["masa_galon"] > 0:
            gal = comb / d["masa_galon"]
            r.agregar("combustible_gal_h", "Consumo de combustible", gal, "gal/h", 2, DATO)
            r.agregar("combustible_l_h", "Consumo de combustible", gal * K.L_POR_GALON_US, "L/h", 2, DATO)

    largo_pie, diam_pie = largo / K.M_POR_PIE, diam / K.M_POR_PIE
    r.agregar("potencia_original", "Potencia estimada (fórmula rev0, con D real en ft)",
              ((largo_pie - 1) * 0.85 + 1) * 0.99 * diam_pie ** 2.5 * 0.00218, "HP", 2, ORIGINAL)
    r.agregar("aletas_original", "Número de aletas (criterio rev0: 2.63·D)", 2.63 * diam, "", 1, ORIGINAL)
    r.agregar("altura_aletas_original", "Altura de aletas (criterio rev0: 4.6·D)", 4.6 * diam, "cm", 1, ORIGINAL)

    if not 5 <= largo / diam <= 10:
        r.advertir(f"L/D = {largo / diam:.1f}: Perry's indica que la longitud suele estar entre 5 y 10 diámetros. "
                   "Revise la velocidad del gas o Ua.")
    if nivel_ua == EMPIRICA:
        r.advertir("Ua por la correlación de Perry's (McCormick): estimación preliminar; depende de aletas, rpm y "
                   "carga del tambor. Confírmelo con el fabricante o con pruebas.")
    r.advertir("Potencia de accionamiento y aletas: fórmulas originales sin fuente; NO validadas. "
               "El tiempo de residencia y la pendiente no se calculan (correlación de Friedman-Marshall pendiente "
               "de verificar contra Perry's).")
    r.nota("El calentador se supone sin aporte de humedad (gases de combustión no considerados en W).")
    r.ecuacion("Base húmeda: ms = F·(1 − xi);  agua_f = ms·xf/(1 − xf);  W = F·xi − agua_f")
    r.ecuacion("Q_útil = ms·cps·ΔTs + agua_f·cpw·ΔTs + W·[cpw·(t_ev − Ts1) + λ + cpv·(Tg2 − t_ev)]")
    r.ecuacion("G = Q_total/((1.006 + 1.86·W_in)·(Tg1 − Tg2));   W_out = W_in + W/G")
    r.ecuacion("D = √(4·Q_gas/(π·v·φ_libre));   V = Q_útil/(Ua·ΔT_ml);   L = V/A")
    r.ecuacion("ΔT_ml: paralelo (Tg1 − Ts1, Tg2 − Ts2);  contracorriente (Tg1 − Ts2, Tg2 − Ts1)")
    r.ecuacion("Ua = 0.5·G^0.67/D [Btu/(h·ft³·°F), G en lb/(h·ft²), D en ft] (Perry's)")
    r.ecuacion("Q_calentador = G·cp_h·(Tg1 − T_amb);   ṁ_comb = Q_calentador/(PCI·η)")
    return r


CALCULADORA = Calculadora(
    id="secador",
    nombre="Secador rotatorio directo",
    disciplina="Térmica y transferencia de calor",
    descripcion="Balances de masa y energía, psicrometría del aire, diámetro, longitud por Ua y combustible.",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("calculo del secador.py", "calculo del secador rev 1.py", "calculo del secador rev 2.py",
                         "calculo del secador DS rev 3.py", "calculo del secador DS rev 4.py",
                         "calculo del secador DS rev 5.py", "calculo del secador DS rev 6.py",
                         "calculo del secador DS rev 7.py"),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("Perry's Chemical Engineers' Handbook, secadores rotatorios: Ua = 0.5·G^0.67/D (estimación), "
                 "L/D entre 5 y 10, velocidad típica del gas.",
                 "Pacheco y Stella, Braz. J. Chem. Eng.: Ua = 244.7·G^0.67/D en SI (contraste de la conversión).",
                 "Psicrometría: ASHRAE Handbook — Fundamentals, cap. 1.",
                 "Geankoplis, Transport Processes and Unit Operations, 3.ª ed., Ej. 9.10-2 «Heat Balance on a "
                 "Dryer» (validación de los balances: G = 1 171 kg a.s./h, H = 0.0247)."),
    limitaciones=("Validada para balances de masa y energía, flujo de aire seco y humedad de salida.",
                  "Diámetro, longitud y Ua: estimación preliminar (Ua empírico); sin tiempo de residencia; "
                  "potencia y aletas sin validar."),
    imagenes=("imagen secador 2.png",),
    palabras_clave=("secador", "rotatorio", "secado", "fluorita", "psicrometría", "combustible"),
)
