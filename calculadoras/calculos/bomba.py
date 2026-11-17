"""Bomba centrífuga: altura total del sistema, potencia y NPSH disponible (unidades inglesas).

Originales: «Calculo de bomba cemtrifuga.py» (rev0) a «rev6.py». No estaba en el menú.
Correcciones:
- La potencia gpm·H/3960 es hidráulica (agua, sin eficiencia) y se presentaba
  como «potencia requerida». Ahora se separan potencia hidráulica y al freno
  (con eficiencia y gravedad específica).
- Se agrega la diferencia de elevación estática (no existía) y se separan la
  presión requerida en la descarga y la presión en la succión (el original
  sumaba una «presión disponible» ambigua).
- Factor de fricción por Colebrook (o f fijo si se captura; el original usaba 0.02).
- NPSH disponible (las imágenes de NPSH se mostraban pero no se calculaba).
- La gráfica de rev3–rev6 omitía accesorios y equipos; la curva del sistema
  incluye todos los términos (como rev2).
- v2.1.0: los K de accesorios se calculan por el método Crane TP-410:
  K = (L/D)·f_T, con f_T = 0.25/[log10(ε/(3.7·D))]² (fricción en zona de
  turbulencia completa) y L/D de la tabla Crane para codos, tees y válvulas;
  entrada K = 0.5 y salida K = 1.0. Los K originales (0.5, 1.0, 1.8) siguen
  disponibles como dato capturado. Las reducciones conservan el K original
  (0.8, sin fuente) porque Crane requiere la geometría (β, θ).
- Las pérdidas por equipo (30/35/35/25 ft) se conservan como valores
  originales editables, sin fuente.
"""
from __future__ import annotations

from ..nucleo import constantes as K, fluidos, psicrometria
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
import math

from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             Resultado, requerir)

# Crane TP-410: longitud equivalente L/D en turbulencia completa (K = (L/D)·f_T)
LD_CODO_90, LD_CODO_RL, LD_CODO_45 = 30, 20, 16
LD_TEE_DERIVACION, LD_TEE_PASO = 60, 20
LD_RETENCION_COLUMPIO = 100
VALVULAS = {"Compuerta, abierta (L/D 8)": 8, "Bola, paso completo (L/D 3)": 3,
            "Mariposa ≤ 8 plg (L/D 45)": 45, "Globo, abierta (L/D 340)": 340, "Ángulo, abierta (L/D 150)": 150,
            "De pie con criba, disco con bisagra (L/D 75)": 75}
K_ENTRADA, K_SALIDA = 0.5, 1.0          # entrada a ras con arista viva; descarga a depósito


def friccion_turbulencia_completa(rugosidad: float, diametro: float) -> float:
    """f_T de Crane TP-410: 0.25/[log10(ε/(3.7·D))]² (mismas unidades para ε y D)."""
    return 0.25 / math.log10(rugosidad / (3.7 * diametro)) ** 2


CAMPOS = [
    Campo("caudal", "Caudal", "gpm", minimo=0, min_incluido=False, grupo="Sistema"),
    Campo("diametro", "Diámetro interior real de la tubería", "in", minimo=0, min_incluido=False, grupo="Sistema",
          ayuda="Diámetro interior según cédula, no el nominal."),
    Campo("longitud", "Longitud de tubería", "ft", minimo=0, grupo="Sistema"),
    Campo("elevacion", "Diferencia de elevación estática (descarga − succión)", "ft", defecto=0, grupo="Sistema",
          ayuda="Positiva si el punto de descarga está más alto que la superficie del líquido en la succión."),
    Campo("presion_descarga", "Presión manométrica requerida en la descarga", "psig", defecto=0, grupo="Sistema",
          ayuda="Antes «presión disponible»: el original la sumaba a la altura."),
    Campo("presion_succion", "Presión manométrica en la superficie de succión", "psig", defecto=0, grupo="Sistema"),
    Campo("ge", "Gravedad específica del líquido", "", defecto=1.0, minimo=0, min_incluido=False, maximo=3,
          grupo="Líquido"),
    Campo("viscosidad", "Viscosidad cinemática", "cSt", defecto=1.0, minimo=0, min_incluido=False, grupo="Líquido",
          ayuda="Agua a 20 °C ≈ 1.0 cSt."),
    Campo("temperatura", "Temperatura del líquido", "°C", defecto=20, minimo=0, maximo=150, grupo="Líquido",
          ayuda="Para la presión de vapor del agua en el NPSH."),
    Campo("presion_vapor", "Presión de vapor del líquido", "psia", defecto=0, minimo=0, grupo="Líquido",
          ayuda="0 = presión de vapor del agua a la temperatura dada."),
    Campo("rugosidad", "Rugosidad absoluta", "in", defecto=0.0018, minimo=0, grupo="Fricción",
          ayuda="0.0018 in (0.045 mm): acero comercial, diagrama de Moody."),
    Campo("friccion", "Factor de fricción de Darcy fijo", "", defecto=0, minimo=0, maximo=0.2, grupo="Fricción",
          ayuda="0 = Colebrook. El original usaba 0.02 fijo."),
    Campo("codos", "Codos de 90° estándar (L/D 30)", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("codos_rl", "Codos de 90° de radio largo (L/D 20)", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("codos_45", "Codos de 45° (L/D 16)", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("tees", "Tees con flujo por la derivación (L/D 60)", tipo="entero", defecto=0, minimo=0,
          grupo="Accesorios"),
    Campo("tees_paso", "Tees con flujo directo (L/D 20)", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("valvulas", "Válvulas de bloqueo", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("tipo_valvula", "Tipo de válvula de bloqueo", tipo="opcion", opciones=tuple(VALVULAS),
          defecto="Compuerta, abierta (L/D 8)", grupo="Accesorios"),
    Campo("retenciones", "Válvulas de retención de columpio (L/D 100)", tipo="entero", defecto=0, minimo=0,
          grupo="Accesorios"),
    Campo("entradas", "Entradas desde depósito (K 0.5)", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("salidas", "Descargas a depósito (K 1.0)", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("reducciones", "Número de reducciones", tipo="entero", defecto=0, minimo=0, grupo="Accesorios"),
    Campo("k_codo", "K por codo de 90° estándar (capturado)", "", defecto=0, minimo=0, grupo="Accesorios",
          ayuda="0 = Crane (30·f_T). El original usaba 0.5 sin fuente."),
    Campo("k_valvula", "K por válvula de bloqueo (capturado)", "", defecto=0, minimo=0, grupo="Accesorios",
          ayuda="0 = Crane según el tipo. El original usaba 1.0 sin fuente; con Cv: K = 891·d⁴/Cv² (d en plg)."),
    Campo("k_tee", "K por tee de derivación (capturado)", "", defecto=0, minimo=0, grupo="Accesorios",
          ayuda="0 = Crane (60·f_T). El original usaba 1.8 sin fuente."),
    Campo("k_reduccion", "K por reducción", "", defecto=0.8, minimo=0, grupo="Accesorios",
          ayuda="Valor original 0.8, sin fuente. Capture el K de Crane para la relación de diámetros y el ángulo."),
    Campo("cribas", "Número de cribas", tipo="entero", defecto=0, minimo=0, grupo="Equipos"),
    Campo("limpiadores", "Número de limpiadores", tipo="entero", defecto=0, minimo=0, grupo="Equipos"),
    Campo("limpiadores_hd", "Número de limpiadores de alta densidad", tipo="entero", defecto=0, minimo=0,
          grupo="Equipos"),
    Campo("limpiadores_rev", "Número de limpiadores reversos", tipo="entero", defecto=0, minimo=0, grupo="Equipos"),
    Campo("h_criba", "Pérdida por criba", "ft", defecto=30, minimo=0, grupo="Equipos", ayuda="Valor original."),
    Campo("h_limpiador", "Pérdida por limpiador", "ft", defecto=35, minimo=0, grupo="Equipos", ayuda="Valor original."),
    Campo("h_limpiador_hd", "Pérdida por limpiador de alta densidad", "ft", defecto=35, minimo=0, grupo="Equipos",
          ayuda="Valor original."),
    Campo("h_limpiador_rev", "Pérdida por limpiador reverso", "ft", defecto=25, minimo=0, grupo="Equipos",
          ayuda="Valor original."),
    Campo("eficiencia", "Eficiencia de la bomba", "%", defecto=0, minimo=0, maximo=100, grupo="Bomba",
          ayuda="De la curva del fabricante. 0 = solo potencia hidráulica."),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000, grupo="NPSH"),
    Campo("elevacion_succion", "Elevación del líquido sobre el eje de la bomba", "ft", defecto=0, grupo="NPSH",
          ayuda="Positiva con succión ahogada (tanque arriba); negativa con succión negativa."),
    Campo("perdidas_succion", "Pérdidas en la línea de succión", "ft", defecto=0, minimo=0, grupo="NPSH"),
]


def _perdidas(d: dict, gpm: float) -> dict:
    diam_ft = d["diametro"] / 12.0
    area = 3.141592653589793 * diam_ft ** 2 / 4
    v = gpm * K.PIE3S_POR_GPM / area
    nu = d["viscosidad"] * 1e-6 / K.M_POR_PIE ** 2  # ft²/s
    re = v * diam_ft / nu
    if d["friccion"] > 0:
        f, regimen = d["friccion"], "capturado"
    else:
        f, regimen = fluidos.factor_friccion_darcy(re, d["rugosidad"] / d["diametro"])
    carga_v = v ** 2 / (2 * K.G_PIES)
    hf = f * d["longitud"] / diam_ft * carga_v
    k = coeficientes_k(d)
    hk = k["total"] * carga_v
    return {"v": v, "re": re, "f": f, "regimen": regimen, "hf": hf, "hk": hk, "k": k}


def coeficientes_k(d: dict) -> dict:
    """Suma de K por el método Crane TP-410; los K capturados (> 0) tienen prioridad."""
    ft = friccion_turbulencia_completa(d["rugosidad"], d["diametro"])
    k_codo = d["k_codo"] if d["k_codo"] > 0 else LD_CODO_90 * ft
    k_tee = d["k_tee"] if d["k_tee"] > 0 else LD_TEE_DERIVACION * ft
    k_valvula = d["k_valvula"] if d["k_valvula"] > 0 else VALVULAS[d["tipo_valvula"]] * ft
    partes = {
        "codos": d["codos"] * k_codo,
        "codos_rl": d["codos_rl"] * LD_CODO_RL * ft,
        "codos_45": d["codos_45"] * LD_CODO_45 * ft,
        "tees": d["tees"] * k_tee,
        "tees_paso": d["tees_paso"] * LD_TEE_PASO * ft,
        "valvulas": d["valvulas"] * k_valvula,
        "retenciones": d["retenciones"] * LD_RETENCION_COLUMPIO * ft,
        "entradas": d["entradas"] * K_ENTRADA,
        "salidas": d["salidas"] * K_SALIDA,
        "reducciones": d["reducciones"] * d["k_reduccion"],
    }
    capturados = [n for n, c, k in (("codo", d["codos"], d["k_codo"]), ("tee", d["tees"], d["k_tee"]),
                                     ("válvula", d["valvulas"], d["k_valvula"])) if c and k > 0]
    return {"ft": ft, "partes": partes, "total": sum(partes.values()), "capturados": capturados,
            "k_codo": k_codo, "k_tee": k_tee, "k_valvula": k_valvula}


def altura_estatica(d: dict) -> tuple[float, float]:
    pies_psi = K.PIES_POR_PSI_AGUA / d["ge"]
    h_presion = (d["presion_descarga"] - d["presion_succion"]) * pies_psi
    h_equipos = (d["cribas"] * d["h_criba"] + d["limpiadores"] * d["h_limpiador"]
                 + d["limpiadores_hd"] * d["h_limpiador_hd"] + d["limpiadores_rev"] * d["h_limpiador_rev"])
    return h_presion, h_equipos


def calcular(d: dict) -> Resultado:
    r = Resultado()
    p = _perdidas(d, d["caudal"])
    h_presion, h_equipos = altura_estatica(d)
    H = d["elevacion"] + h_presion + p["hf"] + p["hk"] + h_equipos
    requerir(H > 0, "La altura total resulta ≤ 0: el sistema fluye por gravedad o por presión; no requiere bomba.")
    whp = d["caudal"] * H * d["ge"] / K.GPM_PIE_POR_HP

    r.agregar("velocidad", "Velocidad en la tubería", p["v"], "ft/s", 2)
    r.agregar("reynolds", "Número de Reynolds", p["re"], "", 0)
    r.agregar("friccion", f"Factor de fricción de Darcy ({p['regimen']})", p["f"], "", 5)
    r.agregar("h_friccion", "Pérdida por fricción en tubería", p["hf"], "ft", 2)
    k = p["k"]
    nivel_k = ORIGINAL if d["reducciones"] > 0 else (DATO if k["capturados"] else EMPIRICA)
    r.agregar("friccion_ft", "Factor de fricción en turbulencia completa f_T (Crane)", k["ft"], "", 4, VERIFICADA)
    r.agregar("k_total", "Suma de coeficientes K de accesorios", k["total"], "", 2, nivel_k)
    r.agregar("h_accesorios", "Pérdida en accesorios", p["hk"], "ft", 2, nivel_k)
    r.agregar("h_equipos", "Pérdida en equipos (cribas, limpiadores)", h_equipos, "ft", 2, ORIGINAL)
    r.agregar("h_estatica", "Altura estática por elevación", d["elevacion"], "ft", 2, DATO)
    r.agregar("h_presion", "Altura por diferencia de presión", h_presion, "ft", 2)
    r.agregar("altura_total", "Altura dinámica total (TDH)", H, "ft", 2)
    r.agregar("altura_total_m", "Altura dinámica total (TDH)", H * K.M_POR_PIE, "m", 2, DATO)
    r.agregar("potencia_hidraulica", "Potencia hidráulica", whp, "HP", 2)
    if d["eficiencia"] > 0:
        bhp = whp / (d["eficiencia"] / 100.0)
        r.agregar("potencia_freno", "Potencia al freno (eje de la bomba)", bhp, "HP", 2)
        r.agregar("potencia_freno_kw", "Potencia al freno", K.hp_a_kw(bhp), "kW", 2, DATO)
    else:
        r.advertir("Sin eficiencia de la bomba solo se reporta la potencia hidráulica; la del motor será mayor.")

    # NPSH disponible
    patm = presion_por_altitud(d["altitud"]) / K.PA_POR_PSI
    pvap = d["presion_vapor"] if d["presion_vapor"] > 0 else psicrometria.presion_saturacion(d["temperatura"]) / K.PA_POR_PSI
    pies_psi = K.PIES_POR_PSI_AGUA / d["ge"]
    npsha = (patm + d["presion_succion"] - pvap) * pies_psi + d["elevacion_succion"] - d["perdidas_succion"]
    r.agregar("presion_atm", "Presión atmosférica del sitio", patm, "psia", 3, DATO)
    r.agregar("presion_vapor", "Presión de vapor usada", pvap, "psia", 4, DATO)
    r.agregar("npsha", "NPSH disponible", npsha, "ft", 2)
    r.agregar("npsha_m", "NPSH disponible", npsha * K.M_POR_PIE, "m", 2, DATO)
    if npsha <= 0:
        r.advertir("NPSH disponible ≤ 0: habrá cavitación con cualquier bomba.")
    r.nota("Compare el NPSH disponible con el requerido de la curva de la bomba más el margen de su criterio.")
    if p["regimen"] == "transición":
        r.advertir("Reynolds en zona de transición (2 300–4 000): factor de fricción incierto.")
    if k["capturados"]:
        r.nota(f"K capturado por el usuario para: {', '.join(k['capturados'])} (sustituye al valor Crane).")
    if d["reducciones"] > 0:
        r.advertir("K de reducciones: valor del original sin fuente (0.8 por defecto). Calcúlelo con Crane TP-410 "
                   "para la relación de diámetros y el ángulo reales.")
    if h_equipos > 0:
        r.advertir("Pérdidas en cribas y limpiadores: valores del original sin fuente. Confírmelas con el fabricante.")
    if d["valvulas"] and "Mariposa" in d["tipo_valvula"] and d["diametro"] > 8.5:
        r.advertir("L/D 45 de la válvula de mariposa corresponde a 2–8 plg; para tamaños mayores use el Cv del fabricante.")
    r.ecuacion("v = Q·0.002228/A;   h_f = f·(L/D)·v²/(2g);   h_k = ΣK·v²/(2g)")
    r.ecuacion("Crane TP-410: K = (L/D)·f_T;   f_T = 0.25/[log10(ε/(3.7·D))]²")
    r.ecuacion("TDH = Δz + (p_d − p_s)·2.309/GE + h_f + h_k + h_equipos")
    r.ecuacion("WHP = Q[gpm]·TDH[ft]·GE/3960;   BHP = WHP/η")
    r.ecuacion("NPSHa = (p_atm + p_s − p_vap)·2.309/GE + z_s − h_f,s")
    return r


def curva_sistema(d: dict, puntos: int = 60) -> tuple[list[float], list[float]]:
    """Curva del sistema de 0 a 1.5·Q de diseño.

    Altura estática (Δz + Δp) constante; fricción y accesorios con su ecuación a cada caudal;
    pérdidas en equipos (cribas, limpiadores) escaladas con (Q/Q_diseño)², porque son caídas de
    presión al caudal de diseño. En la versión 2.0.0 se sumaban constantes a todo caudal y la curva
    arrancaba 30 ft arriba de la altura estática real (hallazgo de la prueba en vivo).
    """
    q_d = d["caudal"]
    h_presion, h_equipos = altura_estatica(d)
    estatica = d["elevacion"] + h_presion
    qs, hs = [0.0], [estatica]
    for i in range(1, puntos + 1):
        q = 1.5 * q_d * i / puntos
        p = _perdidas(d, q)
        qs.append(q)
        hs.append(estatica + h_equipos * (q / q_d) ** 2 + p["hf"] + p["hk"])
    return qs, hs


def graficar(d: dict, resultado: Resultado):
    from matplotlib.figure import Figure

    qs, hs = curva_sistema(d)
    fig = Figure(figsize=(6.5, 4))
    ax = fig.add_subplot(111)
    ax.plot(qs, hs, label="Curva del sistema")
    ax.scatter([d["caudal"]], [resultado["altura_total"]], color="red", zorder=3, label="Punto de diseño")
    ax.axhline(hs[0], color="grey", linewidth=0.8, linestyle=":", label="Altura estática")
    ax.set_xlabel("Caudal (gpm)")
    ax.set_ylabel("Altura dinámica total (ft)")
    ax.set_title("Curva del sistema: estática + pérdidas ∝ Q²")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    return fig


CALCULADORA = Calculadora(
    id="bomba",
    nombre="Bomba centrífuga",
    disciplina="Máquinas de fluido y bombeo",
    descripcion="Altura dinámica total, potencia hidráulica y al freno, NPSH disponible y curva del sistema.",
    campos=CAMPOS,
    funcion=calcular,
    graficar=graficar,
    archivos_originales=tuple(["Calculo de bomba cemtrifuga.py"]
                              + [f"Calculo de bomba cemtrifuga rev{i}.py" for i in range(1, 7)]),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("Darcy-Weisbach, Colebrook-White y ecuación de energía.",
                 "Crane Co., Flow of Fluids Through Valves, Fittings and Pipe, TP-410: K = (L/D)·f_T, tabla de f_T "
                 "y L/D de codos, tees y válvulas (reproducidos en Machinery's Handbook, tabla de L/D).",
                 "NPSH disponible: definición del Hydraulic Institute; ejemplos de J. Elsey, «NPSHa Basics», "
                 "Pumps & Systems (2022)."),
    limitaciones=("Fluido newtoniano, flujo incompresible, tubería de diámetro único.",
                  "Validado: f_T contra la tabla Crane, K de válvula de globo contra Pumps & Systems, NPSHa contra "
                  "los ejemplos 1–3 de Pumps & Systems (tests/test_bomba.py).",
                  "Reducciones y pérdidas por equipo: valores del original sin fuente (nivel O).",
                  "Curva del sistema: pérdidas en equipos supuestas proporcionales a Q² (confirmar con el fabricante)."),
    imagenes=("NPSH Bomas 1.png", "NPSH Bomas 2.png"),
    palabras_clave=("bomba", "centrífuga", "tdh", "npsh", "tubería", "agua"),
)
