"""Banda transportadora: capacidad por geometría de la sección y potencia.

Originales: «calculo de banda.py» (vs1, consola), «calculo de banda_vs2.py», «vs3», «vs4» y «vs5» (menú).
Correcciones:
- «Área» = ancho × ocupación daba metros, no m² (con 1 000 mm y 0.6 equivalía a
  una capa de 0.6 m de alto). Ahora la sección se calcula por geometría:
  trapecio de la artesa + segmento parabólico de sobrecarga.
- La potencia trataba L·cos θ como altura de elevación con fricción unitaria
  (523 kW en horizontal y 0 kW en vertical). Ahora se usa la estructura de
  resistencias de ISO 5048 / DIN 22101: F_U = C·f·L·g·[q_R + (2q_B + q_G)·cos δ] + q_G·g·H.
  Los coeficientes f y C y las masas por metro los captura el usuario.
- La velocidad vuelve a ser dato (vs1 lo permitía); la tabla por material se
  conserva como valor por defecto sin fuente.
- Tambor y rodillo por ancho de banda: criterios originales sin fuente.

v2.1.0 (validación profesional, ISO 5048 / IS 11592:2000, alineada con ISO 5048):
- Ancho útil b = 0.9·B − 0.05 m (B ≤ 2 000 mm) o B − 0.25 m (B > 2 000 mm).
- Rodillo central por defecto: longitud normalizada ISO 1537 según el ancho.
- f = 0.020 por defecto (valor básico; 0.016 favorable, 0.030 desfavorable,
  0.012 descendente con freno).
- C por defecto: C = (L + L₀)/L con L₀ = 70–100 m (ISO 5048; aquí 100 m,
  conservador). Para L < 80 m el valor es incierto y se advierte.
- Factor de pendiente k (IS 11592, tabla 9) aplicado a la capacidad y a q_G.
- Validado contra MEKA Handbook (1 000 mm, 35°/20°, 2 m/s → 795 m³/h): ver
  tests/test_banda.py.
"""
from __future__ import annotations

import math

from ..nucleo import constantes as K
from ..nucleo.materiales import VELOCIDADES_BANDA_ORIGINALES
from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             Resultado, requerir)

OTRO = "Otro (capturar velocidad)"

# ISO 1537: longitud del rodillo de artesas de tres rodillos iguales [mm] por ancho de banda B [mm]
RODILLO_ISO_1537 = {400: 160, 500: 200, 650: 250, 800: 315, 1000: 380, 1200: 465, 1400: 530, 1600: 600,
                    1800: 670, 2000: 750, 2200: 800}
# IS 11592:2000, tabla 9 (alineada con ISO 5048): factor de pendiente k por inclinación [°]
PENDIENTE_K = ((0, 1.00), (2, 1.00), (4, 0.99), (6, 0.98), (8, 0.97), (10, 0.95), (12, 0.93), (14, 0.91),
               (16, 0.89), (18, 0.85), (20, 0.81), (21, 0.78), (22, 0.76), (23, 0.73), (24, 0.71), (25, 0.68),
               (26, 0.66), (27, 0.64), (28, 0.61), (29, 0.59), (30, 0.56))
F_BASICO_ISO = 0.020


def factor_pendiente(angulo_deg: float) -> float:
    """Factor k de la tabla 9 de IS 11592 con interpolación lineal (|δ| ≤ 30°)."""
    a = abs(angulo_deg)
    for (a0, k0), (a1, k1) in zip(PENDIENTE_K, PENDIENTE_K[1:]):
        if a <= a1:
            return k0 + (k1 - k0) * (a - a0) / (a1 - a0)
    raise ValueError("Inclinación fuera de la tabla (máx. 30°).")


def coeficiente_c_iso(longitud: float, l0: float) -> float:
    """C = (L + L₀)/L (ISO 5048), con C ≥ 1.02."""
    return max((longitud + l0) / longitud, 1.02)


def ancho_util_iso(ancho_m: float) -> float:
    return 0.9 * ancho_m - 0.05 if ancho_m <= 2.0 else ancho_m - 0.25

CAMPOS = [
    Campo("ancho", "Ancho de banda B", "mm", minimo=200, maximo=3000, grupo="Banda y material"),
    Campo("material", "Material", tipo="opcion", opciones=tuple(VELOCIDADES_BANDA_ORIGINALES) + (OTRO,),
          defecto="Arena", grupo="Banda y material"),
    Campo("velocidad", "Velocidad de la banda", "m/s", defecto=0, minimo=0, maximo=10, grupo="Banda y material",
          ayuda="0 = usar la velocidad por material del original (sin fuente)."),
    Campo("densidad", "Densidad aparente del material", "kg/m³", minimo=0, min_incluido=False,
          grupo="Banda y material"),
    Campo("ancho_util", "Ancho útil de carga b", "mm", defecto=0, minimo=0, grupo="Sección",
          ayuda="0 = ISO 5048: b = 0.9·B − 50 mm (B ≤ 2 000 mm) o B − 250 mm."),
    Campo("angulo_artesa", "Ángulo de artesa λ", "°", defecto=0, minimo=0, maximo=60, grupo="Sección",
          ayuda="0 = banda plana."),
    Campo("rodillo_central", "Longitud útil del rodillo central l₃", "mm", defecto=0, minimo=0, grupo="Sección",
          ayuda="0 = longitud normalizada ISO 1537 para el ancho B (o b/3 si B no es normalizado)."),
    Campo("angulo_sobrecarga", "Ángulo de sobrecarga β del material", "°", minimo=0, maximo=40, grupo="Sección",
          ayuda="Propiedad del material (dato de la referencia de la empresa)."),
    Campo("llenado", "Grado de llenado φ (0–1)", "", defecto=1.0, minimo=0, maximo=1, min_incluido=False,
          grupo="Sección", ayuda="Reemplaza la «ocupación» del original, ahora aplicada al área, no al ancho."),
    Campo("longitud", "Longitud entre centros L", "m", minimo=0, min_incluido=False, grupo="Potencia"),
    Campo("inclinacion", "Inclinación δ", "°", defecto=0, minimo=-30, maximo=30, grupo="Potencia",
          ayuda="Positiva si sube en el sentido del transporte."),
    Campo("f", "Coeficiente de fricción ficticio f", "", defecto=F_BASICO_ISO, minimo=0, maximo=0.1,
          min_incluido=False, grupo="Potencia",
          ayuda="ISO 5048: 0.020 básico; 0.016 bien alineado; hasta 0.030 desfavorable; 0.012 descendente frenado."),
    Campo("coef_c", "Coeficiente C de resistencias secundarias", "", defecto=0, minimo=0, maximo=10,
          grupo="Potencia", ayuda="0 = ISO 5048: C = (L + L₀)/L. Capture C si calcula las resistencias secundarias."),
    Campo("l0", "Longitud adicional L₀ para C", "m", defecto=100, minimo=70, maximo=100, grupo="Potencia",
          ayuda="ISO 5048: 70–100 m. 100 m es el valor conservador."),
    Campo("masa_rodillos", "Masa giratoria de rodillos q_R (ida + retorno)", "kg/m", defecto=0, minimo=0,
          grupo="Potencia", ayuda="Del catálogo de rodillos."),
    Campo("masa_banda", "Masa de la banda q_B", "kg/m", defecto=0, minimo=0, grupo="Potencia",
          ayuda="Del catálogo de la banda."),
    Campo("eficiencia", "Eficiencia de la transmisión (0–1)", "", minimo=0, maximo=1, min_incluido=False,
          grupo="Potencia", ayuda="El original indicaba 0.85–0.95."),
]


def tambor_original(ancho_mm: float) -> int:
    if ancho_mm <= 500:
        return 250
    if ancho_mm <= 800:
        return 315
    if ancho_mm <= 1200:
        return 400
    return 500


def rodillo_original(ancho_mm: float) -> int:
    if ancho_mm <= 500:
        return 89
    if ancho_mm <= 800:
        return 108
    if ancho_mm <= 1200:
        return 133
    return 159


def area_seccion(b: float, l3: float, lam_deg: float, beta_deg: float) -> tuple[float, float]:
    """Área teórica [m²] del material: (sobrecarga, artesa).

    Ancho superior de la artesa w = l3 + (b − l3)·cos λ.
    Sobrecarga: segmento parabólico de ancho w con pendiente de borde tan β → w²·tan β/6.
    Artesa: trapecio de bases l3 y w y altura ((b − l3)/2)·sen λ.
    """
    lam, beta = math.radians(lam_deg), math.radians(beta_deg)
    lado = (b - l3) / 2.0
    w = l3 + 2.0 * lado * math.cos(lam)
    a_sobrecarga = w ** 2 * math.tan(beta) / 6.0
    a_artesa = (l3 + w) / 2.0 * lado * math.sin(lam)
    return a_sobrecarga, a_artesa


def calcular(d: dict) -> Resultado:
    r = Resultado()
    B = d["ancho"] / 1000.0
    if d["velocidad"] > 0:
        v, nivel_v = d["velocidad"], DATO
    else:
        requerir(d["material"] in VELOCIDADES_BANDA_ORIGINALES, "Capture la velocidad de la banda.")
        v, nivel_v = VELOCIDADES_BANDA_ORIGINALES[d["material"]], ORIGINAL
        r.advertir(f"Velocidad tomada de la tabla original por material ({v:g} m/s), sin fuente documentada.")

    if d["ancho_util"] > 0:
        b, nivel_b = d["ancho_util"] / 1000.0, DATO
    else:
        b, nivel_b = ancho_util_iso(B), EMPIRICA
    requerir(0 < b <= B, "El ancho útil debe ser positivo y no mayor que el ancho de banda.")

    lam = d["angulo_artesa"]
    if lam == 0:
        l3, nivel_l3 = b, DATO
    elif d["rodillo_central"] > 0:
        l3, nivel_l3 = d["rodillo_central"] / 1000.0, DATO
    elif int(round(d["ancho"])) in RODILLO_ISO_1537:
        l3, nivel_l3 = RODILLO_ISO_1537[int(round(d["ancho"]))] / 1000.0, EMPIRICA
    else:
        l3, nivel_l3 = b / 3.0, EMPIRICA
        r.advertir("Ancho de banda no normalizado (ISO 1537): rodillo central supuesto = b/3. Capture l₃.")
    if lam > 0:
        requerir(0 < l3 < b, "La longitud útil del rodillo central debe ser menor que el ancho útil.")

    a_sob, a_art = area_seccion(b, l3, lam, d["angulo_sobrecarga"])
    area = (a_sob + a_art) * d["llenado"]
    requerir(area > 0, "La sección de material es nula: revise el ángulo de sobrecarga y la artesa.")
    k_pend = factor_pendiente(d["inclinacion"])
    cap_m3h = area * k_pend * v * 3600.0
    cap_th = cap_m3h * d["densidad"] / 1000.0

    delta = math.radians(d["inclinacion"])
    q_g = d["densidad"] * area * k_pend  # kg/m de material = ρ·A·k
    altura = d["longitud"] * math.sin(delta)
    g = K.G
    f_h = d["f"] * d["longitud"] * g * (d["masa_rodillos"] + (2 * d["masa_banda"] + q_g) * math.cos(delta))
    f_st = q_g * g * altura
    if d["coef_c"] > 0:
        coef_c, nivel_c = d["coef_c"], DATO
    else:
        coef_c, nivel_c = coeficiente_c_iso(d["longitud"], d["l0"]), EMPIRICA
        if d["longitud"] < 80:
            r.advertir("ISO 5048 / IS 11592: para L < 80 m el coeficiente C es incierto; el valor (L + L₀)/L puede ser "
                       "muy conservador. Calcule las resistencias secundarias y capture C.")
    f_u = coef_c * f_h + f_st
    p_tambor = f_u * v
    requerir(p_tambor > 0, "La fuerza tangencial resulta ≤ 0 (banda descendente que genera energía): "
                           "este caso requiere análisis de frenado, fuera del alcance.")
    p_motor = p_tambor / d["eficiencia"]
    p_elevacion = q_g * g * altura * v

    r.agregar("velocidad", "Velocidad usada", v, "m/s", 2, nivel_v)
    r.agregar("ancho_util", "Ancho útil b", b * 1000, "mm", 0, nivel_b)
    r.agregar("area_sobrecarga", "Área de sobrecarga", a_sob, "m²", 5)
    r.agregar("area_artesa", "Área de artesa", a_art, "m²", 5)
    r.agregar("rodillo_central", "Longitud del rodillo central l₃", l3 * 1000, "mm", 0, nivel_l3)
    r.agregar("area", "Área efectiva del material (φ·A)", area, "m²", 5)
    r.agregar("factor_pendiente", "Factor de pendiente k (IS 11592, tabla 9)", k_pend, "", 3, EMPIRICA)
    r.agregar("capacidad_m3h", "Capacidad volumétrica", cap_m3h, "m³/h", 1)
    r.agregar("capacidad_th", "Capacidad másica", cap_th, "t/h", 1)
    r.agregar("carga_lineal", "Carga de material por metro q_G", q_g, "kg/m", 2)
    r.agregar("altura", "Altura de elevación H", altura, "m", 2, DATO)
    r.agregar("coef_c", "Coeficiente C de resistencias secundarias", coef_c, "", 3, nivel_c)
    r.agregar("fuerza_tangencial", "Fuerza tangencial en el tambor motriz F_U", f_u / 1000, "kN", 3, EMPIRICA)
    r.agregar("potencia_tambor", "Potencia en el tambor motriz", p_tambor / 1000, "kW", 2, EMPIRICA)
    r.agregar("potencia_motor", "Potencia requerida del motor", p_motor / 1000, "kW", 2, EMPIRICA)
    r.agregar("potencia_elevacion", "Potencia solo de elevación (verificación)", p_elevacion / 1000, "kW", 2)
    r.agregar("tambor", "Diámetro de tambor sugerido", tambor_original(d["ancho"]), "mm", nivel=ORIGINAL)
    r.agregar("rodillo", "Diámetro de rodillo sugerido", rodillo_original(d["ancho"]), "mm", nivel=ORIGINAL)

    if d["masa_rodillos"] == 0 or d["masa_banda"] == 0:
        r.advertir("Masa de rodillos o de banda = 0: la potencia está subestimada. Capture los datos de catálogo.")
    if coef_c == 1.0:
        r.advertir("C = 1: no se incluyeron resistencias secundarias (carga, raspadores, tambores).")
    r.nota("No incluye resistencias especiales (faldones a lo largo, arados, rodillos inclinados) ni el cálculo de "
           "tensiones y selección de la banda.")
    r.advertir("Tambor y rodillo sugeridos: tablas originales por ancho, sin fuente. Seleccione según tensión "
               "de la banda y catálogo.")
    r.ecuacion("w = l₃ + (b − l₃)·cos λ;   A_sobrecarga = w²·tan β/6;   A_artesa = (l₃ + w)/2·((b − l₃)/2)·sen λ")
    r.ecuacion("Q = φ·A·k·v·3600 [m³/h];   Q_m = Q·ρ/1000 [t/h];   q_G = ρ·φ·A·k [kg/m]")
    r.ecuacion("C = (L + L₀)/L ≥ 1.02   (ISO 5048)")
    r.ecuacion("F_U = C·f·L·g·[q_R + (2·q_B + q_G)·cos δ] + q_G·g·H   (ISO 5048 / DIN 22101)")
    r.ecuacion("P_tambor = F_U·v;   P_motor = P_tambor/η")
    return r


CALCULADORA = Calculadora(
    id="banda",
    nombre="Banda transportadora",
    disciplina="Manejo de sólidos a granel",
    descripcion="Capacidad por geometría de la sección (artesa + sobrecarga) y potencia por resistencias (ISO 5048).",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("calculo de banda.py", "calculo de banda_vs2.py", "Calculo de banda vs3.py",
                         "Calculo de banda vs4.py", "Calculo de banda vs5.py"),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("ISO 5048:1989 e IS 11592:2000 (alineada con ISO 5048): sección S1 + S2, ancho útil b, f, C, "
                 "factor de pendiente k y fuerza tangencial F_U.",
                 "ISO 1537:1975: longitud de rodillos de artesas de tres rodillos.",
                 "Validación: MEKA Crushing, Screening and Mining Equipment Handbook (capacidad volumétrica de "
                 "referencia) — tests/test_banda.py."),
    limitaciones=("Validada la capacidad y la potencia por el método ISO 5048 con C global.",
                  "Masas de rodillos y de banda: datos de catálogo del usuario.",
                  "Sin cálculo de tensiones, selección de banda ni de tambores (tambor y rodillo sugeridos: O).",
                  "Para L < 80 m el C de ISO 5048 es incierto: capture C."),
    palabras_clave=("banda", "transportador", "cinta", "capacidad", "potencia"),
)
