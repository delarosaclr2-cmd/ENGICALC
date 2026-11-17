"""Elevador de cangilones.

Originales: «Calculo de Elevador vs1.py» (no compilaba), «vs2.py» y «vs3.py» (menú).
Correcciones:
- Cangilones por metro = 1000/paso, sin truncar a entero (paso 350 mm daba 2 en vez de 2.86).
- El volumen de la tabla ya incluía 80 % de llenado y además se multiplicaba por
  la eficiencia mecánica; ahora llenado (φ) y eficiencia (η) son datos separados.
- La eficiencia aparecía en capacidad y en potencia y se cancelaba; ahora solo
  afecta a la potencia.
- Se informa v²/(g·R) en el tambor de cabeza para revisar la descarga centrífuga.
- Pasos, volúmenes (prisma l×a×p) y velocidades por tipo de descarga: tablas
  originales sin fuente; el usuario puede capturar sus datos de catálogo.

v2.1.0: potencia de dragado y fricción por el método de longitud equivalente de
KWS (Bucket Elevator Engineering Guide, «Horsepower Calculation»):
P = G·(DH + Leq·d)/(33 000·60) [HP], G en lb/h, DH y d (tambor de cola) en ft,
Leq de 5 a 15 según la aplicación. En SI: P = ṁ·g·(H + Leq·d)/η. Una altura
equivalente capturada por el usuario tiene prioridad.
"""
from __future__ import annotations

from ..nucleo import constantes as K
from ..nucleo.materiales import materiales_de, resolver_densidad
from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             Resultado, requerir)

VELOCIDADES = {
    "Descarga centrífuga, materiales livianos": 1.2,
    "Descarga centrífuga, materiales secos": 2.5,
    "Descarga por gravedad, materiales pesados": 0.6,
    "Descarga por gravedad, materiales abrasivos": 1.2,
    "Descarga combinada": 1.8,
}
PASOS_MM = {  # «L» del original: paso (esparcimiento) en mm
    "L1 — paso 200 mm": 200, "L3 — paso 250 mm": 250, "L5 — paso 300 mm": 300, "L6 — paso 300 mm": 300,
    "L8 — paso 350 mm": 350, "L12 — paso 400 mm": 400, "L14 — paso 330 mm": 330, "L20 — paso 400 mm": 400,
    "L30 — paso 500 mm": 500,
}
CANGILONES_MM = {  # «C» del original: proyección × ancho × fondo (mm)
    "C1 — 80 × 150 × 110": (80, 150, 110), "C3 — 80 × 180 × 130": (80, 180, 130),
    "C5 — 80 × 200 × 150": (80, 200, 150), "C6 — 80 × 250 × 150": (80, 250, 150),
    "C8 — 80 × 300 × 200": (80, 300, 200), "C12 — 80 × 400 × 250": (80, 400, 250),
    "C14 — 90 × 400 × 250": (90, 400, 250), "C20 — 90 × 500 × 320": (90, 500, 320),
    "C30 — 90 × 600 × 400": (90, 600, 400),
}
CAPTURAR_PASO = "Capturar paso"
CAPTURAR_VOLUMEN = "Capturar volumen de catálogo"
CENTRIFUGAS = ("Descarga centrífuga, materiales livianos", "Descarga centrífuga, materiales secos")

CAMPOS = [
    Campo("material", "Material", tipo="opcion", opciones=materiales_de("elevador"), defecto="Arena",
          grupo="Material"),
    Campo("densidad", "Densidad aparente", "kg/m³", defecto=0, minimo=0, grupo="Material",
          ayuda="0 = usar la tabla original del elevador (sin fuente)."),
    Campo("descarga", "Tipo de descarga", tipo="opcion", opciones=tuple(VELOCIDADES),
          defecto="Descarga centrífuga, materiales livianos", grupo="Cangilones"),
    Campo("velocidad", "Velocidad de la banda/cadena", "m/s", defecto=0, minimo=0, maximo=5, grupo="Cangilones",
          ayuda="0 = velocidad de la tabla original según el tipo de descarga."),
    Campo("paso_tabla", "Paso de cangilones", tipo="opcion", opciones=tuple(PASOS_MM) + (CAPTURAR_PASO,),
          defecto="L1 — paso 200 mm", grupo="Cangilones"),
    Campo("paso", "Paso capturado", "mm", defecto=0, minimo=0, grupo="Cangilones"),
    Campo("cangilon_tabla", "Cangilón", tipo="opcion", opciones=tuple(CANGILONES_MM) + (CAPTURAR_VOLUMEN,),
          defecto="C1 — 80 × 150 × 110", grupo="Cangilones"),
    Campo("volumen_cangilon", "Volumen de catálogo del cangilón", "L", defecto=0, minimo=0, grupo="Cangilones",
          ayuda="Capacidad de agua o volumen útil del fabricante."),
    Campo("llenado", "Grado de llenado φ (0–1)", "", defecto=0.8, minimo=0, maximo=1, min_incluido=False,
          grupo="Cangilones", ayuda="0.8 era el llenado implícito en la tabla original."),
    Campo("altura", "Altura de elevación H", "m", minimo=0, min_incluido=False, grupo="Potencia"),
    Campo("altura_carga", "Altura equivalente de dragado y fricción capturada", "m", defecto=0, minimo=0,
          grupo="Potencia", ayuda="Si > 0 sustituye al método KWS (dato del fabricante)."),
    Campo("leq", "Factor de longitud equivalente Leq (KWS)", "", defecto=10, minimo=5, maximo=15, grupo="Potencia",
          ayuda="KWS: 5 a 15 según la aplicación; el ejemplo KWS de arena usa 7."),
    Campo("diametro_cola", "Diámetro del tambor de cola", "mm", defecto=0, minimo=0, grupo="Potencia",
          ayuda="0 = igual al tambor de cabeza."),
    Campo("eficiencia", "Eficiencia mecánica de la transmisión (0–1)", "", minimo=0, maximo=1, min_incluido=False,
          grupo="Potencia", ayuda="El original indicaba 0.70–0.90."),
    Campo("ancho_banda", "Ancho de banda", "mm", minimo=0, min_incluido=False, grupo="Tambor"),
    Campo("diametro_tambor", "Diámetro del tambor de cabeza", "mm", defecto=0, minimo=0, grupo="Tambor",
          ayuda="0 = tabla original por ancho de banda (sin fuente)."),
]


def tambor_original(ancho_mm: float) -> int:
    return 450 if ancho_mm <= 500 else (750 if ancho_mm <= 800 else 950)


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rho = resolver_densidad("elevador", d["material"], d["densidad"], r)

    if d["velocidad"] > 0:
        v, nivel_v = d["velocidad"], DATO
    else:
        v, nivel_v = VELOCIDADES[d["descarga"]], ORIGINAL
        r.advertir("Velocidad tomada de la tabla original por tipo de descarga (sin fuente).")

    if d["paso_tabla"] == CAPTURAR_PASO or d["paso"] > 0:  # el dato capturado tiene prioridad
        requerir(d["paso"] > 0, "Capture el paso de cangilones en mm.")
        paso, nivel_p = d["paso"], DATO
        if d["paso_tabla"] != CAPTURAR_PASO:
            r.nota(f"Se usó el paso capturado ({paso:g} mm) en lugar de «{d['paso_tabla']}».")
    else:
        paso, nivel_p = PASOS_MM[d["paso_tabla"]], ORIGINAL

    if d["cangilon_tabla"] == CAPTURAR_VOLUMEN or d["volumen_cangilon"] > 0:  # el dato capturado tiene prioridad
        requerir(d["volumen_cangilon"] > 0, "Capture el volumen de catálogo del cangilón en litros.")
        vol, nivel_c = d["volumen_cangilon"] / 1000.0, DATO
        if d["cangilon_tabla"] != CAPTURAR_VOLUMEN:
            r.nota(f"Se usó el volumen capturado ({d['volumen_cangilon']:g} L) en lugar de «{d['cangilon_tabla']}».")
    else:
        a, b, c = CANGILONES_MM[d["cangilon_tabla"]]
        vol, nivel_c = a * b * c * 1e-9, ORIGINAL
        r.advertir("Volumen del cangilón = proyección × ancho × fondo (prisma) de la tabla original: "
                   "no es la capacidad de catálogo. Capture el volumen del fabricante.")

    n_m = 1000.0 / paso
    cap_m3h = n_m * v * vol * d["llenado"] * 3600.0
    cap_th = cap_m3h * rho / 1000.0
    masa_s = cap_th / 3.6
    diam = d["diametro_tambor"] if d["diametro_tambor"] > 0 else tambor_original(d["ancho_banda"])
    nivel_t = DATO if d["diametro_tambor"] > 0 else ORIGINAL
    if d["altura_carga"] > 0:
        h_drag, nivel_h = d["altura_carga"], DATO
        r.nota(f"Altura equivalente de dragado capturada: {h_drag:g} m (sustituye al método KWS).")
    else:
        d_cola = (d["diametro_cola"] if d["diametro_cola"] > 0 else diam) / 1000.0
        h_drag, nivel_h = d["leq"] * d_cola, EMPIRICA
    altura_total = d["altura"] + h_drag
    p_elev = masa_s * K.G * altura_total
    p_motor = p_elev / d["eficiencia"]
    relacion = v ** 2 / (K.G * diam / 2000.0)

    r.agregar("velocidad", "Velocidad usada", v, "m/s", 2, nivel_v)
    r.agregar("paso", "Paso de cangilones", paso, "mm", 0, nivel_p)
    r.agregar("cangilones_m", "Cangilones por metro", n_m, "1/m", 3)
    r.agregar("volumen_cangilon", "Volumen del cangilón (sin llenado)", vol * 1000, "L", 3, nivel_c)
    r.agregar("capacidad_m3h", "Capacidad volumétrica", cap_m3h, "m³/h", 2)
    r.agregar("capacidad_th", "Capacidad másica", cap_th, "t/h", 2)
    r.agregar("altura_dragado", "Altura equivalente de dragado y fricción", h_drag, "m", 2, nivel_h)
    r.agregar("potencia_elevacion", "Potencia en el eje de cabeza (elevación + dragado)", p_elev / 1000, "kW", 3,
              EMPIRICA)
    r.agregar("potencia_motor", "Potencia requerida del motor", p_motor / 1000, "kW", 3, EMPIRICA)
    r.agregar("diametro_tambor", "Diámetro del tambor de cabeza", diam, "mm", 0, nivel_t)
    r.agregar("relacion_centrifuga", "v²/(g·R) en el tambor de cabeza", relacion, "", 3)

    if nivel_t == ORIGINAL and d["altura_carga"] == 0 and d["diametro_cola"] == 0:
        r.advertir("Diámetro de tambor de la tabla original (sin fuente) usado también para el dragado KWS: "
                   "capture los diámetros reales.")
    if d["descarga"] in CENTRIFUGAS and relacion < 1.0:
        r.advertir(f"Descarga centrífuga con v²/(g·R) = {relacion:.2f} < 1: en la parte superior del tambor la "
                   "fuerza centrífuga es menor que el peso; revise velocidad y diámetro con el fabricante.")
    r.ecuacion("n = 1000/paso [cangilones/m]")
    r.ecuacion("Q = n·v·V·φ·3600 [m³/h];   Q_m = Q·ρ/1000 [t/h]")
    r.ecuacion("P = ṁ·g·(H + Leq·d_cola)/η   (KWS: P[HP] = G·(DH + Leq·d)/(33 000·60))")
    r.ecuacion("v²/(g·R): relación entre fuerza centrífuga y peso en el tambor de cabeza")
    return r


CALCULADORA = Calculadora(
    id="elevador",
    nombre="Elevador de cangilones",
    disciplina="Manejo de sólidos a granel",
    descripcion="Capacidad, potencia de elevación y verificación de descarga centrífuga.",
    campos=CAMPOS,
    funcion=calcular,
    estado_validacion=VALIDADA_CONDICIONES,
    archivos_originales=("Calculo de Elevador vs1.py", "Calculo de Elevador vs2.py", "Calculo de Elevador vs3.py"),
    referencias=("Balance de energía: P = ṁ·g·H/η (física básica).",
                 "Dragado y fricción: KWS Bucket Elevator Engineering Guide, «Horsepower Calculation» "
                 "(método de longitud equivalente, Leq 5–15).",
                 "Pasos, cangilones y velocidades: tablas originales sin fuente (usar catálogo)."),
    limitaciones=("Capacidad con volumen de catálogo capturado; la tabla original usa un prisma (nivel O).",
                  "Leq depende de la aplicación (5–15): confirmar con el fabricante.",
                  "Velocidad y diámetros de tambor de tablas originales sin fuente si no se capturan."),
    palabras_clave=("elevador", "cangilones", "capacidad"),
)
