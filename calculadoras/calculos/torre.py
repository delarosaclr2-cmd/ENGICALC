"""Torre de enfriamiento: carga térmica y balance de aire.

Originales: «Calculo de torre de enfriamiento rev0.py» (el que abría el menú) y «rev1.py».
Correcciones:
- rev0 dividía ṁ·cp·ΔT entre 1000 (carga 1 000 veces menor). rev1 lo corregía
  pero su gráfica conservaba el error.
- El flujo de aire de rev0 (1.2 × kW) y de rev1 (kW/187.5) no tenía base y
  diferían 4.5 veces entre sí. Ahora sale del balance de entalpía del aire
  (psicrometría ASHRAE) cuando se dan el bulbo húmedo y la temperatura de
  salida del aire.
- La aproximación (T salida agua − bulbo húmedo) se verifica: debe ser positiva.

v2.1.0: característica requerida de la torre (demanda) por la ecuación de Merkel,
KaV/L = ∫ cp·dT/(h_w − h_a), evaluada con el método de Chebyshev de 4 puntos
(Cooling Technology Institute; Perry's Chemical Engineers' Handbook, sec. 12) y
verificada con integración numérica de Simpson. Validada contra el ejemplo de
Perry's (105/85/78 °F, L/G = 0.97) y un ejemplo de diseño publicado
(110/84/69 °F, L/G = 1.30 → KaV/L = 1.49): ver tests/test_torre.py.
"""
from __future__ import annotations

from ..nucleo import constantes as K, psicrometria as ps
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             ErrorEntrada, Resultado, requerir)

CAMPOS = [
    Campo("flujo_agua", "Flujo de agua", "kg/s", minimo=0, min_incluido=False, grupo="Agua"),
    Campo("t_entrada", "Temperatura del agua caliente (entrada)", "°C", minimo=0, maximo=100, grupo="Agua"),
    Campo("t_salida", "Temperatura del agua fría (salida)", "°C", minimo=0, maximo=100, grupo="Agua"),
    Campo("cp", "Calor específico del agua", "kJ/(kg·K)", defecto=K.CP_AGUA, minimo=3.5, maximo=4.5, grupo="Agua"),
    Campo("t_bulbo_humedo", "Bulbo húmedo de diseño del aire de entrada", "°C", defecto=0, minimo=0, maximo=40,
          grupo="Aire", ayuda="0 = no calcular la aproximación ni el aire."),
    Campo("t_bulbo_seco", "Bulbo seco del aire de entrada", "°C", defecto=0, minimo=0, maximo=55, grupo="Aire",
          ayuda="Con bulbo seco y húmedo se usa el estado real del aire. 0 = aire saturado al bulbo húmedo."),
    Campo("t_aire_salida", "Temperatura del aire de salida", "°C", defecto=0, minimo=0, maximo=100,
          grupo="Aire", ayuda="Supuesto de diseño. 0 = no calcular el flujo de aire."),
    Campo("hr_aire_salida", "Humedad relativa del aire de salida", "%", defecto=100, minimo=50, maximo=100,
          grupo="Aire", ayuda="100 = saturado (supuesto usual)."),
    Campo("relacion_lg", "Relación L/G de diseño (capturada)", "", defecto=0, minimo=0, maximo=5, grupo="Aire",
          ayuda="0 = calcular L/G con la temperatura del aire de salida. Si > 0 tiene prioridad."),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000, grupo="Aire"),
]

CHEBYSHEV = (0.1, 0.4, 0.6, 0.9)


def merkel_chebyshev(t_caliente: float, t_fria: float, h_entrada: float, lg: float, cp: float,
                     p: float) -> tuple[float, list[tuple[float, float, float]]]:
    """KaV/L por Chebyshev de 4 puntos. Devuelve (KaV/L, [(T, h_w, h_a), ...]).

    h_a = h_entrada + (L/G)·cp·(T − T_fría) (línea de operación del aire, contraflujo).
    """
    rango = t_caliente - t_fria
    puntos, suma = [], 0.0
    for c in CHEBYSHEV:
        temp = t_fria + c * rango
        h_w = ps.entalpia_saturacion(temp, p)
        h_a = h_entrada + lg * cp * (temp - t_fria)
        if h_w - h_a <= 0:
            raise ErrorEntrada(f"La línea de operación del aire cruza la curva de saturación a {temp:.1f} °C: con "
                               f"L/G = {lg:.3f} la torre no puede lograr esa aproximación. Reduzca L/G o aumente "
                               "la aproximación.")
        puntos.append((temp, h_w, h_a))
        suma += 1.0 / (h_w - h_a)
    return cp * rango / 4.0 * suma, puntos


def merkel_simpson(t_caliente: float, t_fria: float, h_entrada: float, lg: float, cp: float, p: float,
                   n: int = 200) -> float:
    """KaV/L por integración de Simpson (verificación independiente de Chebyshev)."""
    rango = t_caliente - t_fria
    suma = 0.0
    for i in range(n + 1):
        temp = t_fria + rango * i / n
        dh = ps.entalpia_saturacion(temp, p) - (h_entrada + lg * cp * (temp - t_fria))
        peso = 1 if i in (0, n) else (4 if i % 2 else 2)
        suma += peso / dh
    return cp * rango / n / 3.0 * suma


def tipo_torre_rev1(flujo_kg_s: float) -> str:
    """Clasificación de rev1 por caudal (sin fuente)."""
    if flujo_kg_s < 10:
        return "Torre pequeña (paquete cerrado)"
    if flujo_kg_s < 100:
        return "Torre mediana (flujo cruzado)"
    return "Torre grande (flujo inducido o contraflujo)"


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rango = d["t_entrada"] - d["t_salida"]
    requerir(rango > 0, "La temperatura del agua caliente debe ser mayor que la del agua fría.")
    carga = d["flujo_agua"] * d["cp"] * rango  # kW

    r.agregar("rango", "Rango de enfriamiento", rango, "°C", 2, DATO)
    r.agregar("carga_kw", "Carga térmica", carga, "kW", 2)
    r.agregar("carga_btuh", "Carga térmica", carga * 1000 / K.W_POR_BTUH, "BTU/h", 0, DATO)
    r.agregar("carga_tr", "Carga térmica", carga * 1000 / K.W_POR_BTUH / 12000, "TR", 2, DATO,
              "1 TR = 12 000 BTU/h")
    r.ecuacion("Q = ṁ_agua·cp·(T_entrada − T_salida)")

    tbh = d["t_bulbo_humedo"]
    if tbh > 0:
        p = presion_por_altitud(d["altitud"])
        aproximacion = d["t_salida"] - tbh
        requerir(aproximacion > 0, "El agua no puede enfriarse por evaporación por debajo del bulbo húmedo: "
                                   "la temperatura de salida debe ser mayor que el bulbo húmedo.")
        r.agregar("aproximacion", "Aproximación (T salida − bulbo húmedo)", aproximacion, "°C", 2)
        tbs = d["t_bulbo_seco"]
        if tbs > 0:
            requerir(tbs >= tbh, "El bulbo seco no puede ser menor que el bulbo húmedo.")
            w_ent = ps.humedad_por_bulbo_humedo(tbs, tbh, p)
            h_entrada = ps.entalpia(tbs, w_ent)
            v_ent = ps.volumen_especifico(tbs, w_ent, p)
            r.agregar("h_aire_entrada", "Entalpía del aire de entrada (bulbo seco y húmedo)", h_entrada,
                      "kJ/kg a.s.", 2)
            r.agregar("w_entrada", "Humedad absoluta del aire de entrada", w_ent, "kg/kg a.s.", 5)
        else:
            w_ent = ps.humedad_saturacion(tbh, p)
            h_entrada = ps.entalpia_saturacion(tbh, p)
            v_ent = None
            r.agregar("h_aire_entrada", "Entalpía del aire de entrada (≈ saturado a bulbo húmedo)", h_entrada,
                      "kJ/kg a.s.", 2)
            r.nota("Sin bulbo seco, el aire de entrada se aproxima como saturado al bulbo húmedo (Merkel).")
        ts = d["t_aire_salida"]
        lg = None
        aire = None
        if d["relacion_lg"] > 0:
            lg = float(d["relacion_lg"])
            aire = d["flujo_agua"] / lg
            r.agregar("relacion_lg", "Relación L/G (agua/aire seco) capturada", lg, "", 3, DATO)
            r.agregar("flujo_aire", "Flujo de aire seco", aire, "kg/s", 3)
            r.agregar("h_aire_salida", "Entalpía del aire de salida (balance)", h_entrada + carga / aire,
                      "kJ/kg a.s.", 2)
            r.ecuacion("ṁ_aire = ṁ_agua/(L/G);   h_salida = h_entrada + Q/ṁ_aire")
            if ts > 0:
                r.nota("Se usó la relación L/G capturada; la temperatura del aire de salida no se empleó.")
        elif ts > 0:
            requerir(ts > tbh, "La temperatura del aire de salida debe ser mayor que el bulbo húmedo de entrada.")
            requerir(ts < d["t_entrada"], "El aire no puede salir más caliente que el agua caliente.")
            w_sal = ps.humedad_por_hr(ts, d["hr_aire_salida"], p)
            h_salida = ps.entalpia(ts, w_sal)
            requerir(h_salida > h_entrada, "La entalpía del aire de salida debe ser mayor que la de entrada.")
            # Balance de energía con el agua de reposición a la temperatura del agua fría (Çengel y Boles):
            # ṁ_a·[(h2 − h1) − (ω2 − ω1)·h_f(T_fría)] = ṁ_agua·cp·(T_caliente − T_fría)
            hf_fria = d["cp"] * d["t_salida"]
            aire = carga / ((h_salida - h_entrada) - (w_sal - w_ent) * hf_fria)
            lg = d["flujo_agua"] / aire
            evap = aire * (w_sal - w_ent)
            r.agregar("h_aire_salida", f"Entalpía del aire de salida ({d['hr_aire_salida']:g} % HR)", h_salida,
                      "kJ/kg a.s.", 2)
            r.agregar("w_salida", "Humedad absoluta del aire de salida", w_sal, "kg/kg a.s.", 5)
            r.agregar("flujo_aire", "Flujo de aire seco", aire, "kg/s", 3)
            r.agregar("relacion_lg", "Relación L/G (agua/aire seco)", lg, "", 3)
            if v_ent is not None:
                r.agregar("volumen_aire_entrada", "Caudal de aire a la entrada", aire * v_ent, "m³/s", 3)
            r.agregar("volumen_aire_salida", "Caudal de aire a la salida",
                      aire * ps.volumen_especifico(ts, w_sal, p), "m³/s", 3)
            r.agregar("evaporacion", "Agua evaporada (= agua de reposición sin purga ni arrastre)", evap * 3600,
                      "kg/h", 1)
            r.agregar("evaporacion_kgs", "Agua evaporada", evap, "kg/s", 4, DATO)
            r.agregar("evaporacion_pct", "Evaporación respecto al flujo de agua", evap / d["flujo_agua"] * 100, "%", 2)
            r.ecuacion("ṁ_aire = ṁ_agua·cp·ΔT / [(h₂ − h₁) − (ω₂ − ω₁)·h_f(T_fría)]")
            r.ecuacion("ṁ_evap = ṁ_aire·(ω₂ − ω₁);   V̇₁ = ṁ_aire·v₁")
        else:
            r.nota("Flujo de aire y KaV/L no calculados: capture L/G o la temperatura del aire de salida.")
        if lg is not None:
            kav, puntos = merkel_chebyshev(d["t_entrada"], d["t_salida"], h_entrada, lg, d["cp"], p)
            kav_s = merkel_simpson(d["t_entrada"], d["t_salida"], h_entrada, lg, d["cp"], p)
            r.agregar("kav_l", "Característica requerida KaV/L (Merkel, Chebyshev 4 puntos)", kav, "", 3, EMPIRICA)
            r.agregar("kav_l_simpson", "KaV/L por integración numérica (verificación)", kav_s, "", 3, VERIFICADA)
            r.agregar("dh_minimo", "Diferencia de entalpía mínima en los puntos de Chebyshev",
                      min(hw - ha for _, hw, ha in puntos), "kJ/kg a.s.", 2)
            r.ecuacion("KaV/L = ∫ cp·dT/(h_w − h_a) ≈ cp·R/4·Σ 1/(h_w − h_a) en T_fría + (0.1, 0.4, 0.6, 0.9)·R")
            r.ecuacion("h_a = h_entrada + (L/G)·cp·(T − T_fría)")
            if abs(kav - kav_s) / kav_s > 0.02:
                r.advertir("Chebyshev y la integración numérica difieren más de 2 %: use el valor integrado.")
            r.nota("KaV/L es la DEMANDA del proceso; la altura de relleno se obtiene con la característica del "
                   "relleno KaV/L = C·(L/G)^−n de ensayos del fabricante o del CTI.")
    else:
        r.advertir("Sin bulbo húmedo de diseño no se puede verificar la factibilidad ni calcular el aire.")
    r.agregar("tipo", "Tipo de torre sugerido", tipo_torre_rev1(d["flujo_agua"]), nivel=ORIGINAL,
              nota="Criterio de rev1 sin fuente.")
    return r


def graficar(d: dict, resultado: Resultado):
    from matplotlib.figure import Figure

    rangos = [x * 0.5 for x in range(1, 41)]
    cargas = [d["flujo_agua"] * d["cp"] * t for t in rangos]
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    ax.plot(rangos, cargas, label=f"Flujo = {d['flujo_agua']:g} kg/s")
    ax.axvline(d["t_entrada"] - d["t_salida"], color="red", linestyle="--", label="Rango de diseño")
    ax.axhline(resultado["carga_kw"], color="green", linestyle="--", label=f"Q = {resultado['carga_kw']:.1f} kW")
    ax.set_xlabel("Rango de enfriamiento (°C)")
    ax.set_ylabel("Carga térmica (kW)")
    ax.set_title("Carga térmica vs. rango")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    return fig


CALCULADORA = Calculadora(
    id="torre",
    nombre="Torre de enfriamiento",
    disciplina="Térmica y transferencia de calor",
    descripcion="Carga térmica, aproximación al bulbo húmedo, flujo de aire por balance de entalpía y evaporación.",
    campos=CAMPOS,
    funcion=calcular,
    graficar=graficar,
    archivos_originales=("Calculo de torre de enfriamiento rev0.py", "Calculo de torre de enfriamiento rev1.py"),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("Psicrometría: ASHRAE Handbook — Fundamentals, cap. 1.",
                 "Merkel (1925); método de Chebyshev de 4 puntos (CTI; Perry's Chemical Engineers' Handbook, sec. 12).",
                 "Balance de masa y energía con agua de reposición: Çengel y Boles, Termodinámica, "
                 "cap. 14 (torre de enfriamiento húmeda)."),
    limitaciones=("No dimensiona el relleno ni la torre: requiere curvas del fabricante o del CTI.",
                  "Aire de salida a la temperatura y humedad relativa capturadas (100 % = saturado)."),
    palabras_clave=("torre", "enfriamiento", "bulbo húmedo", "agua", "carga térmica"),
)
