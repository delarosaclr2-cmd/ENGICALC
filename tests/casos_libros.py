"""Ejercicios resueltos de libros de texto: fuente única de datos para las pruebas y los ejemplos.

Cada caso indica la calculadora, la fuente bibliográfica, las entradas tal como se capturan en el
programa (con las conversiones del enunciado ya hechas y explicadas) y los valores publicados con la
tolerancia relativa aceptada. La usan ``tests/test_libros.py`` (verificación automática) y
``herramientas/generar_casos_libros.py`` (casos .json en ``docs/ejemplos/libros`` para abrirlos en el
programa y tabla de ``docs/VALIDACION_CON_LIBROS.md``).

Una comprobación es (etiqueta, salida, valor publicado, tolerancia relativa), donde «salida» es la clave
de un resultado o una función del resultado (para magnitudes derivadas, p. ej. pérdida en metros).
"""
from calculadoras.calculos import secador as S
from calculadoras.calculos import vacio as VAC
from calculadoras.calculos import viga as VG
from calculadoras.nucleo import constantes as K
from calculadoras.nucleo import psicrometria as ps

P_ATM = 101325.0
FT = 0.3048

# Problema 14-115: aire de entrada 15 °C y 20 % HR; salida 20 °C con ω = 0.014 kg/kg.
_W1_14_115 = ps.humedad_por_hr(15, 20, P_ATM)

CASOS_LIBROS = {
    "torre_cengel_boles_P14_112": {
        "calculadora": "torre",
        "fuente": "Çengel y Boles, Termodinámica (McGraw-Hill), cap. 14, problema 14-112; respuestas impresas "
                  "en el enunciado del libro.",
        "planteamiento": "Torre húmeda: 60 kg/s de agua de 40 a 26 °C; aire a 1 atm con 22 °C bs y 16 °C bh; "
                         "sale a 34 °C y 90 % HR.",
        "entradas": dict(flujo_agua=60, t_entrada=40, t_salida=26, cp=4.18, t_bulbo_seco=22, t_bulbo_humedo=16,
                         t_aire_salida=34, hr_aire_salida=90, relacion_lg=0, altitud=0),
        "comprobaciones": [
            ("Caudal de aire a la entrada [m³/s]", "volumen_aire_entrada", 44.9, 0.01),
            ("Agua de reposición [kg/s]", "evaporacion_kgs", 1.16, 0.01),
        ],
    },
    "torre_cengel_boles_P14_115": {
        "calculadora": "torre",
        "fuente": "Çengel y Boles, Termodinámica, 7.ª ed., problema 14-115 (manual de soluciones, "
                  "McGraw-Hill 2011).",
        "planteamiento": "4 kg/s de agua a 32 °C; aire a 1 atm, 15 °C y 20 % HR, 4.2 kg/s de aire seco; sale a "
                         "20 °C con ω = 0.014. Publicado: agua fría 23.4 °C, reposición 0.050 kg/s. Se resuelve el "
                         "problema inverso: con el agua fría publicada la calculadora debe dar el aire del enunciado.",
        "entradas": dict(flujo_agua=4, t_entrada=32, t_salida=23.4, cp=4.18, t_bulbo_seco=15,
                         t_bulbo_humedo=ps.bulbo_humedo(15, _W1_14_115, P_ATM), t_aire_salida=20,
                         hr_aire_salida=ps.hr_por_humedad(20, 0.014, P_ATM), relacion_lg=0, altitud=0),
        "comprobaciones": [
            ("Humedad absoluta del aire de entrada ω₁ [kg/kg]", "w_entrada", 0.00211, 0.01),
            ("Flujo de aire seco [kg/s] (dato del enunciado)", "flujo_aire", 4.2, 0.01),
            ("Agua de reposición [kg/s]", "evaporacion_kgs", 0.050, 0.02),
        ],
    },
    "bomba_cengel_cimbala_ej_8_3": {
        "calculadora": "bomba",
        "fuente": "Çengel y Cimbala, Mecánica de fluidos (McGraw-Hill), cap. 8, Ejemplo 8-3 «Determining the "
                  "Head Loss in a Water Pipe».",
        "planteamiento": "Agua a 60 °F (ρ = 62.36 lbm/ft³, μ = 7.536e-4 lbm/(ft·s)), 0.2 ft³/s en tubo horizontal de "
                         "acero inoxidable de 2 in y 200 ft (ε = 0.000007 ft). Caudal capturado en gpm y "
                         "viscosidad cinemática μ/ρ en cSt.",
        "entradas": dict(caudal=0.2 / K.PIE3S_POR_GPM, diametro=2, longitud=200, elevacion=0, presion_descarga=0,
                         presion_succion=0, ge=1.0, viscosidad=7.536e-4 / 62.36 * FT ** 2 * 1e6,
                         rugosidad=0.000084, friccion=0, eficiencia=0, altitud=0),
        "comprobaciones": [
            ("Velocidad [ft/s]", "velocidad", 9.17, 0.005),
            ("Número de Reynolds", "reynolds", 126_400, 0.005),
            ("Factor de fricción de Darcy", "friccion", 0.0174, 0.01),
            ("Pérdida de carga hL [ft]", "h_friccion", 27.3, 0.01),
            ("Potencia de bombeo [W]", lambda r: r["potencia_hidraulica"] * K.W_POR_HP, 461, 0.01),
        ],
    },
    "ductos_cengel_cimbala_ej_8_4": {
        "calculadora": "ductos",
        "fuente": "Çengel y Cimbala, Mecánica de fluidos (McGraw-Hill), cap. 8, Ejemplo 8-4 «Determining the "
                  "Diameter of an Air Duct».",
        "planteamiento": "Aire a 1 atm y 35 °C (ρ = 1.145 kg/m³), 0.35 m³/s, ducto liso de 150 m, pérdida "
                         "admisible 20 m. La calculadora dimensiona por velocidad: con la velocidad del libro "
                         "(6.24 m/s) debe dar el diámetro y la pérdida del libro.",
        "entradas": dict(caudal=0.35 * 3600, velocidad=6.24, velocidad_minima=0, temperatura=35, altitud=0,
                         densidad=1.145, longitud=150, friccion=0, rugosidad=1e-6, k_accesorios=0, eficiencia=1),
        "comprobaciones": [
            ("Diámetro [m]", "diametro_m", 0.267, 0.005),
            ("Número de Reynolds", "reynolds", 100_800, 0.01),
            ("Factor de fricción de Darcy", "friccion", 0.0180, 0.01),
            ("Pérdida de carga hL [m]", lambda r: r["dp_friccion_pa"] / (1.145 * K.G), 20.0, 0.01),
        ],
    },
    "vacio_cengel_boles_compresion": {
        "calculadora": "vacio",
        "fuente": "Çengel y Boles, Termodinámica (McGraw-Hill), cap. 7, sección «Reversible steady-flow work», "
                  "ejemplo de trabajo de compresión de aire por distintos procesos.",
        "planteamiento": "Aire de 100 kPa y 300 K a 900 kPa, compresión reversible. Se captura el caudal de "
                         "succión que corresponde a 1 kg/s, de modo que la potencia en kW es el trabajo en kJ/kg.",
        "entradas": dict(caudal=287.042 * 300 / 100_000 * 3600, unidad_caudal=VAC.M3H, presion_succion=100,
                         presion_descarga=900, altitud=0, temperatura=300 - 273.15, eficiencia=1.0, k=1.4,
                         velocidad_ducto=0),
        "comprobaciones": [
            ("Trabajo isentrópico, k = 1.4 [kJ/kg]", "potencia_teorica_kw", 263.2, 0.002),
            ("Trabajo isotérmico [kJ/kg]", "potencia_isotermica_kw", 189.2, 0.002),
        ],
    },
    "aerodeslizador_rhodes_ej_7_9": {
        "calculadora": "aerodeslizador",
        "fuente": "Rhodes, Introduction to Particle Technology, 2.ª ed. (Wiley), Ejercicio 7.9, inciso (a) "
                  "(solución publicada del capítulo 7).",
        "planteamiento": "Polvo de 60 µm, ρp = 1 800 kg/m³, aire 1.2 kg/m³ y 1.84e-5 Pa·s, ε_mf = 0.45, Umf por "
                         "Ergun. La densidad del lecho fluidizado que pide el programa es (1 − ε)(ρp − ρf) = "
                         "989.3 kg/m³. Ancho y altura del canal no intervienen en Umf.",
        "entradas": dict(densidad=(1 - 0.45) * (1800 - 1.2), porosidad=0.45, particula=60, viscosidad=1.84e-5,
                         densidad_aire=1.2, ancho=400, altura_lecho=60),
        "comprobaciones": [
            ("Velocidad mínima de fluidización Umf [mm/s]", "u_mf", 3.8, 0.02),
            ("ΔP de 60 mm de lecho por equilibrio de fuerzas [Pa] (Rhodes: 9 705.4 Pa/m)",
             "dp_lecho_fluidizado", 9705.4 * 0.060, 0.001),
        ],
    },
    "viga_strength_of_materials_ej_11_1": {
        "calculadora": "viga",
        "fuente": "Strength of Materials (libro abierto Engineering Mechanics OER), cap. 11 «Beam Deflection», "
                  "Ejemplo 11.1.",
        "planteamiento": "Viga simplemente apoyada, L = 10 m, w = 20 kN/m, E = 200 GPa, I = 350 × 10⁶ mm⁴ "
                         "(= 35 000 cm⁴). La carga se captura en kg/m (20 000/9.80665). Sección personalizada; c y A "
                         "solo afectan los esfuerzos.",
        "entradas": dict(tipo=VG.SIMPLE, longitud=10, carga_puntual=0, posicion=0, carga_distribuida=20_000 / K.G,
                         material=VG.PERSONALIZADO, modulo=200, seccion=VG.PERS, inercia=35_000, c=200, area=100,
                         norma=VG.NINGUNA),
        "comprobaciones": [
            ("Deflexión al centro [mm]", lambda r: abs(r["deflexion_max"]), 37.2, 0.005),
            ("Momento máximo wL²/8 [kN·m] (estática)", lambda r: abs(r["momento_max"]), 250, 0.005),
            ("Reacción en cada apoyo [kN] (estática)", lambda r: abs(r["reaccion_izq"]), 100, 0.005),
        ],
    },
    "secador_geankoplis_ej_9_10_2": {
        "calculadora": "secador",
        "fuente": "Geankoplis, Transport Processes and Unit Operations, 3.ª ed. (Prentice Hall), Ejemplo 9.10-2 "
                  "«Heat Balance on a Dryer» (solución reproducida en el Textbook Companion de FOSSEE).",
        "planteamiento": "Secador continuo a contracorriente: 453.6 kg sólido seco/h, X de 0.04 a 0.002 kg/kg "
                         "(base seca), cp sólido 1.465 kJ/(kg·K), sólido 26.7 → 62.8 °C, aire 93.3 → 37.8 °C con "
                         "H = 0.010 a la entrada, sin pérdidas. El programa pide el aire ambiente: 25 °C con la HR "
                         "que da H = 0.010.",
        "entradas": dict(alimentacion=453.6 * 1.04, base=S.SECA, humedad_inicial=4, humedad_final=0.2,
                         cp_solido=1.465, t_solido_entrada=26.7, t_solido_salida=62.8, t_aire_entrada=93.3,
                         t_aire_salida=37.8, flujo=S.CONTRACORRIENTE, t_ambiente=25,
                         hr_ambiente=ps.hr_por_humedad(25, 0.010, P_ATM), altitud=0, latente=0, perdidas=0,
                         velocidad_aire=2, pci=0),
        "comprobaciones": [
            ("Agua evaporada [kg/h] (balance de masa)", "agua_evaporada", 453.6 * (0.04 - 0.002), 1e-9),
            ("Flujo de aire seco G [kg/h]", "aire_seco", 1171, 0.01),
            ("Humedad del aire de salida H [kg/kg]", "w_salida", 0.0247, 0.01),
        ],
    },
}


def valor(resultado, salida):
    """Valor de una comprobación: clave del resultado o función del resultado."""
    return salida(resultado) if callable(salida) else resultado[salida]
