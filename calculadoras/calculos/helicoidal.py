"""Transportador helicoidal horizontal — método CEMA 350 en la forma publicada por KWS.

Sustituye (v2.1.0) al método heredado sin fuente de «Calculo del transportador
helicoidal.py», que se conserva en ``helicoidal_original.py`` para trazabilidad.

Fuente de ecuaciones y tablas (consultadas en noviembre de 2026):
KWS Manufacturing, *Screw Conveyor Engineering Guide* (método CEMA):
- «Screw Conveyor Capacity»: capacidad de selección SC = CFH·CF1·CF2·CF3 y
  velocidad N = SC / (capacidad a 1 rpm); tabla de capacidades por diámetro y
  carga de artesa 15 %, 30A, 30B, 45 %; factores CF1 (paso), CF2 (hélice
  especial) y CF3 (paletas).
- «Screw Conveyor Horsepower»: FHP = L·N·DF·HBF/10⁶;
  MHP = CP·L·MF·SF·PF/10⁶ (CP en lb/h); TSHP = (FHP + MHP)/e.
- «Bulk Material Table»: densidad aparente, carga de artesa recomendada y
  factor de material MF.
- «Screw Conveyor Torque»: par a plena carga del motor T = 63 025·HP/N [lb·plg].

Corrección por sobrecarga para potencias pequeñas (dos variantes documentadas):
- KWS: si MHP < 5 HP se corrige con la gráfica «Corrected Material HP» (sin
  valores numéricos publicados en texto): el usuario captura el MHP corregido.
- CEMA 350 / catálogo Martin: HP = (HPf + HPm)·Fo/e con Fo de una gráfica que va
  de 3.0 a 1.0 y Fo = 1 para HPf + HPm > 5.2 HP. Cuando el usuario no captura Fo
  se usa una interpolación log-lineal entre (0.2 HP; 3.0) y (5.2 HP; 1.0):
  APROXIMACIÓN de la gráfica, identificada como tal en los resultados.

Validez: transportadores alimentados de forma controlada (no alimentadores de
tornillo), horizontales o con inclinación ≤ 10° (KWS: pérdida mínima). Para
inclinaciones mayores el usuario debe capturar la eficiencia de transporte y el
factor de potencia por inclinación de la fuente que utilice.
"""
from __future__ import annotations

import math

from ..nucleo import constantes as K
from ..nucleo.modelo import (DATO, EMPIRICA, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             ErrorEntrada, Resultado, requerir)
from ..nucleo.motores import motor_iec_kw, motor_nema_hp

FUENTE_KWS = "KWS Screw Conveyor Engineering Guide (método CEMA)"

# ---------------------------------------------------------------------------
# Tabla de capacidades KWS: diámetro [plg] -> (rpm máx., ft³/h a rpm máx., ft³/h a 1 rpm)
# ---------------------------------------------------------------------------
CAPACIDAD = {
    "15": {4: (69, 14.5, 0.2), 6: (60, 45, 0.8), 9: (55, 150, 2.7), 12: (50, 323, 6.5), 14: (50, 520, 10.4),
           16: (45, 702, 15.6), 18: (45, 1012, 22.5), 20: (40, 1248, 31.2), 24: (40, 2184, 54.6),
           30: (35, 3728, 106.5), 36: (30, 5532, 184.4)},
    "30A": {4: (139, 57, 0.4), 6: (120, 179, 1.5), 9: (100, 545, 5.5), 12: (90, 1161, 12.9), 14: (85, 1768, 20.8),
            16: (80, 2496, 31.2), 18: (75, 3375, 45.0), 20: (70, 4375, 62.5), 24: (65, 7085, 109.0),
            30: (60, 12798, 213.3), 36: (50, 18440, 368.8)},
    "30B": {4: (69, 28, 0.4), 6: (60, 90, 1.5), 9: (55, 305, 5.5), 12: (50, 645, 12.9), 14: (50, 1040, 20.8),
            16: (45, 1404, 31.2), 18: (45, 2025, 45.0), 20: (40, 2500, 62.5), 24: (40, 4360, 109.0),
            30: (35, 7465, 213.3), 36: (30, 11064, 368.8)},
    "45": {4: (190, 116, 0.61), 6: (165, 368, 2.2), 9: (155, 1271, 8.2), 12: (145, 2813, 19.4),
           14: (140, 4368, 31.2), 16: (130, 6071, 46.7), 18: (120, 8112, 67.6), 20: (110, 10307, 93.7),
           24: (100, 16400, 164.0), 30: (90, 28800, 320.0), 36: (75, 41490, 553.2)},
}
DIAMETROS = (4, 6, 9, 12, 14, 16, 18, 20, 24, 30, 36)
# Factor de diámetro DF (fricción del tornillo vacío)
DF = {4: 12, 6: 18, 9: 31, 12: 55, 14: 78, 16: 106, 18: 135, 20: 165, 24: 235, 30: 377, 36: 549}

# Clases de carga de artesa y su columna (15 %, 30 %, 45 %) en las tablas de factores especiales
CLASES = {"15": 0, "30A": 1, "30B": 1, "45": 2}
SEGUN_MATERIAL = "Según tabla del material"
CARGAS = {SEGUN_MATERIAL: None, "15 %": "15", "30 % (clase 30A)": "30A", "30 % (clase 30B)": "30B", "45 %": "45"}

# CF1: paso especial
PASOS = {"Estándar (paso = D)": 1.00, "Corto (paso = 2/3 D)": 1.50, "Medio (paso = 1/2 D)": 2.00,
         "Largo (paso = 1.5 D)": 0.67}

# Hélice especial: CF2 (capacidad) y SF (potencia) por columna 15/30/45 %; None = no recomendado («X» en KWS)
ESTANDAR, CORTADA, CORTADA_DOBLADA, LISTON = ("Estándar (hélice continua)", "Cortada (cut flight)",
                                              "Cortada y doblada (cut & folded)", "Listón (ribbon)")
CF2 = {
    CORTADA: (1.92, 1.57, 1.43),
    CORTADA_DOBLADA: (None, 3.75, 2.54),
}
CF2_LISTON = {4: (None, None, None), 6: (1.32, 1.52, 1.79), 9: (1.34, 1.54, 1.81), 12: (1.11, 1.27, 1.50),
              14: (1.27, 1.45, 1.71), 16: (1.55, 1.69, 1.90), 18: (1.33, 1.53, 1.80), 20: (1.60, 1.75, 1.96),
              24: (2.02, 2.14, 2.28), 30: (2.16, 2.29, 2.44), 36: (3.27, 3.37, 3.70)}
SF = {ESTANDAR: (1.0, 1.0, 1.0), CORTADA: (1.10, 1.15, 1.20), CORTADA_DOBLADA: (None, 1.50, 1.70),
      LISTON: (1.05, 1.14, 1.20)}

# Paletas de mezcla por paso: CF3 (capacidad) y PF (potencia)
CF3 = {0: 1.00, 1: 1.08, 2: 1.16, 3: 1.24, 4: 1.32}
PF = {0: 1.00, 1: 1.29, 2: 1.58, 3: 1.87, 4: 2.16}

# Cojinetes colgantes: HBF
COJINETES = {"Bolas, rodillos o sin colgantes": 1.0, "Bronce o madera": 1.7,
             "Plástico, nylon, UHMW o teflón": 2.0, "Hierro endurecido o stellite": 4.4}

# Tabla de materiales KWS: densidad aparente mín. y máx. [lb/ft³], clase de carga, MF (o intervalo de MF)
MATERIALES = {
    "Alúmina (alumina)": (55, 65, "15", 1.8),
    "Almidón (starch)": (25, 50, "45", 1.0),
    "Arcilla calcinada (clay, calcined)": (80, 100, "30B", 2.4),
    "Arcilla de ladrillo, finos secos (clay, brick, dry fines)": (100, 120, "30B", 2.0),
    "Arcilla seca en terrones (clay, dry lumpy)": (60, 75, "30A", 1.8),
    "Arena seca de banco (sand, dry bank)": (90, 110, "15", 1.7),
    "Arena sílica seca (sand, silica, dry)": (90, 100, "15", 2.0),
    "Aserrín seco (sawdust, dry)": (10, 13, "30A", 1.4),
    "Astillas de madera (wood chips)": (10, 30, "30A", 0.6),
    "Azúcar granulada seca (sugar, granulated dry)": (50, 55, "30A", (1.0, 1.2)),
    "Bentonita (bentonite)": (50, 60, "45", 0.7),
    "Cal hidratada (lime, hydrated)": (40, 40, "30A", 0.8),
    "Cal hidratada pulverizada (lime, hydrated, pulverized)": (32, 40, "30A", 0.6),
    "Cal viva en guijarros (lime, pebble, unslaked)": (53, 56, "45", 2.0),
    "Caliza agrícola (limestone, agricultural)": (68, 68, "30A", 2.0),
    "Caliza triturada (limestone, crushed)": (85, 90, "30B", 2.0),
    "Caliza en polvo (limestone, dust)": (55, 95, "30B", (1.6, 2.0)),
    "Caolín (kaolin clay)": (63, 63, "30A", 2.0),
    "Carbón bituminoso extraído (coal, bituminous, mined)": (40, 60, "30A", 0.9),
    "Carbonato de sodio denso (soda ash, heavy)": (55, 65, "30B", 1.0),
    "Carbonato de sodio ligero (soda ash, light)": (20, 35, "30B", 0.8),
    "Cemento Portland (cement, Portland)": (94, 94, "30B", 1.4),
    "Ceniza volante (fly ash)": (30, 45, "30B", 2.0),
    "Clínker de cemento (cement clinker)": (75, 95, "30B", 1.8),
    "Fluorita (fluorspar)": (80, 100, "30B", 2.0),
    "Harina de maíz (corn meal)": (32, 40, "30A", 0.5),
    "Harina de sílice (silica flour)": (80, 80, "30B", 1.5),
    "Mineral de hierro (iron ore)": (120, 180, "15", 2.2),
    "Potasa seca (potash, dry)": (70, 70, "15", 2.0),
    "Roca fosfórica pulverizada (phosphate rock, pulverized)": (60, 60, "30B", 1.7),
    "Sal seca gruesa (salt, dry, coarse)": (45, 60, "30B", 1.0),
    "Sal seca fina (salt, dry, fine)": (70, 80, "30B", 1.7),
    "Talco en polvo (talc, powdered)": (50, 60, "30B", 0.8),
    "Trigo (wheat)": (45, 48, "45", 0.4),
    "Yeso calcinado (gypsum, calcined)": (55, 60, "30A", 1.6),
    "Yeso crudo (gypsum, raw)": (70, 80, "30A", 2.0),
}
OTRO = "Otro (capturar densidad, carga y MF)"
AUTOMATICO = "Automático (menor diámetro que cumpla)"
OPCIONES_DIAMETRO = (AUTOMATICO,) + tuple(f"{d} plg" for d in DIAMETROS)

INCLINACION_SIN_CORRECCION = 10.0   # KWS: pérdida de eficiencia mínima hasta 10°
LB_PLG_A_NM = 0.1129848290276167    # 1 lbf·plg en N·m
PAR_HP_RPM = 63025.0                # T [lbf·plg] = 63 025·HP/N

CAMPOS = [
    Campo("material", "Material (tabla KWS)", tipo="opcion", opciones=tuple(MATERIALES) + (OTRO,),
          defecto="Cemento Portland (cement, Portland)", grupo="Material"),
    Campo("densidad", "Densidad aparente", "kg/m³", defecto=0, minimo=0, grupo="Material",
          ayuda="0 = valor mínimo del intervalo de la tabla KWS (el más conservador para capacidad y velocidad)."),
    Campo("carga", "Carga de la artesa", tipo="opcion", opciones=tuple(CARGAS), defecto=SEGUN_MATERIAL,
          grupo="Material", ayuda="30A y 30B difieren en la velocidad máxima recomendada (30B: materiales abrasivos)."),
    Campo("factor_material", "Factor de material MF", "", defecto=0, minimo=0, maximo=10, grupo="Material",
          ayuda="0 = tabla KWS (si la tabla da un intervalo se usa el valor mayor)."),
    Campo("capacidad", "Capacidad requerida", "t/h", minimo=0, min_incluido=False, grupo="Capacidad"),
    Campo("factor_capacidad", "Factor de diseño sobre la capacidad", "", defecto=1.0, minimo=1, maximo=3,
          grupo="Capacidad", ayuda="1.0 = capacidad requerida (KWS/CEMA). La versión original usaba 1.25 fijo."),
    Campo("diametro", "Diámetro del tornillo", tipo="opcion", opciones=OPCIONES_DIAMETRO, defecto=AUTOMATICO,
          grupo="Tornillo"),
    Campo("paso", "Paso del tornillo (CF1)", tipo="opcion", opciones=tuple(PASOS), defecto="Estándar (paso = D)",
          grupo="Tornillo"),
    Campo("helice", "Tipo de hélice (CF2, SF)", tipo="opcion", opciones=(ESTANDAR, CORTADA, CORTADA_DOBLADA, LISTON),
          defecto=ESTANDAR, grupo="Tornillo"),
    Campo("paletas", "Paletas de mezcla por paso (CF3, PF)", "", tipo="entero", defecto=0, minimo=0, maximo=4,
          grupo="Tornillo"),
    Campo("capacidad_rpm", "Capacidad a 1 rpm (catálogo del fabricante)", "ft³/(h·rpm)", defecto=0, minimo=0,
          grupo="Tornillo", ayuda="0 = tabla KWS. Requiere elegir un diámetro."),
    Campo("rpm_maxima", "Velocidad máxima recomendada (catálogo)", "rpm", defecto=0, minimo=0, grupo="Tornillo",
          ayuda="0 = tabla KWS. Requiere elegir un diámetro."),
    Campo("longitud", "Longitud del transportador", "m", minimo=0, min_incluido=False, grupo="Potencia"),
    Campo("cojinete", "Cojinetes colgantes (HBF)", tipo="opcion", opciones=tuple(COJINETES),
          defecto="Bronce o madera", grupo="Potencia",
          ayuda="Materiales abrasivos suelen requerir hierro endurecido (HBF 4.4)."),
    Campo("eficiencia", "Eficiencia del accionamiento", "%", defecto=88, minimo=0, maximo=100, min_incluido=False,
          grupo="Potencia", ayuda="KWS: típico 88 % (reductor montado en flecha); entre 85 y 95 %."),
    Campo("factor_sobrecarga", "Factor de sobrecarga Fo (CEMA)", "", defecto=0, minimo=0, maximo=5,
          grupo="Potencia", ayuda="0 = aproximación de la gráfica CEMA (Fo = 1 si HPf + HPm > 5.2 HP)."),
    Campo("mhp_corregido", "MHP corregido de la gráfica KWS", "HP", defecto=0, minimo=0, grupo="Potencia",
          ayuda="Si > 0 se usa el procedimiento KWS: TSHP = (FHP + MHP corregido)/e, sin Fo."),
    Campo("angulo", "Ángulo de inclinación", "°", defecto=0, minimo=0, maximo=45, grupo="Inclinación",
          ayuda="Hasta 10° sin corrección (KWS). Más de 10°: capture los dos factores siguientes."),
    Campo("eficiencia_inclinacion", "Eficiencia de transporte por inclinación", "", defecto=0, minimo=0, maximo=1,
          grupo="Inclinación", ayuda="Fracción de la capacidad horizontal (gráfica del fabricante). 0 = no capturado."),
    Campo("factor_inclinacion", "Factor de potencia por inclinación Fi", "", defecto=0, minimo=0, maximo=5,
          grupo="Inclinación", ayuda="Gráfica del fabricante. Se aplica a FHP + MHP (criterio conservador). 0 = 1."),
]


# ---------------------------------------------------------------------------
# Funciones del método
# ---------------------------------------------------------------------------
def fo_cema_aproximado(hp: float) -> float:
    """Factor de sobrecarga Fo: interpolación log-lineal de la gráfica CEMA entre (0.2; 3.0) y (5.2; 1.0).

    APROXIMACIÓN de una gráfica: Fo = 1 para HPf + HPm ≥ 5.2 HP (dato de CEMA) y 3.0 como tope inferior.
    """
    if hp >= 5.2:
        return 1.0
    if hp <= 0.2:
        return 3.0
    return 3.0 - 2.0 * math.log(hp / 0.2) / math.log(5.2 / 0.2)


def factor_cf2(helice: str, columna: int, diametro: int) -> float | None:
    if helice == ESTANDAR:
        return 1.0
    if helice == LISTON:
        return CF2_LISTON[diametro][columna]
    return CF2[helice][columna]


def potencia_friccion(longitud_pie: float, rpm: float, diametro: int, hbf: float) -> float:
    """FHP = L·N·DF·HBF/10⁶ [HP]."""
    return longitud_pie * rpm * DF[diametro] * hbf / 1e6


def potencia_material(capacidad_lbh: float, longitud_pie: float, mf: float, sf: float = 1.0, pf: float = 1.0) -> float:
    """MHP = CP·L·MF·SF·PF/10⁶ [HP], CP en lb/h."""
    return capacidad_lbh * longitud_pie * mf * sf * pf / 1e6


def _datos_material(d: dict, r: Resultado) -> tuple[float, str, float]:
    """Devuelve (densidad kg/m³, clase de carga, MF) aplicando la prioridad dato capturado > tabla."""
    material = d["material"]
    tabla = MATERIALES.get(material)
    if tabla is None:
        faltan = [n for n, ok in (("densidad aparente", d["densidad"] > 0),
                                  ("factor de material MF", d["factor_material"] > 0),
                                  ("carga de la artesa", CARGAS[d["carga"]] is not None)) if not ok]
        requerir(not faltan, f"Material «Otro»: capture {', '.join(faltan)}.")
        tabla = (None, None, None, None)
    rho_min, rho_max, clase_tabla, mf_tabla = tabla

    if d["densidad"] > 0:
        rho = float(d["densidad"])
        r.nota(f"Densidad aparente capturada: {rho:g} kg/m³.")
        if rho_min is not None:
            lo, hi = rho_min * K.KGM3_POR_LBPIE3, rho_max * K.KGM3_POR_LBPIE3
            if not (0.8 * lo <= rho <= 1.2 * hi):
                r.advertir(f"La densidad capturada ({rho:.0f} kg/m³) está fuera del intervalo de la tabla KWS para "
                           f"«{material}» ({lo:.0f}–{hi:.0f} kg/m³). Verifique el dato.")
    else:
        rho = rho_min * K.KGM3_POR_LBPIE3
        if rho_min == rho_max:
            r.nota(f"Densidad de la tabla KWS para «{material}»: {rho_min:g} lb/ft³ ({rho:.0f} kg/m³).")
        else:
            r.nota(f"Densidad de la tabla KWS para «{material}»: {rho_min:g}–{rho_max:g} lb/ft³; se usa el mínimo "
                   f"({rho:.0f} kg/m³), que da el mayor volumen y la mayor velocidad.")

    clase = CARGAS[d["carga"]]
    if clase is None:
        clase = clase_tabla
    elif clase_tabla is not None and clase != clase_tabla:
        r.advertir(f"La carga de artesa elegida ({clase}) difiere de la recomendada por la tabla KWS ({clase_tabla}).")

    if d["factor_material"] > 0:
        mf = float(d["factor_material"])
        r.nota(f"Factor de material MF capturado: {mf:g}.")
    elif isinstance(mf_tabla, tuple):
        mf = max(mf_tabla)
        r.nota(f"MF de la tabla KWS: intervalo {mf_tabla[0]:g}–{mf_tabla[1]:g}; se usa el mayor ({mf:g}).")
    else:
        mf = float(mf_tabla)
    return rho, clase, mf


def _seleccionar_diametro(d: dict, clase: str, sc_sin_cf2: float, r: Resultado):
    """Elige el diámetro y devuelve (D, CF2, SC, capacidad a 1 rpm, rpm máx., capacidad máx., niveles)."""
    columna = CLASES[clase]
    manual = d["diametro"] != AUTOMATICO
    if not manual:
        requerir(d["capacidad_rpm"] == 0 and d["rpm_maxima"] == 0,
                 "La capacidad a 1 rpm y la velocidad máxima de catálogo requieren elegir el diámetro del tornillo.")
    candidatos = [int(d["diametro"].split()[0])] if manual else list(DIAMETROS)
    for diam in candidatos:
        cf2 = factor_cf2(d["helice"], columna, diam)
        if cf2 is None:
            requerir(not manual, f"La hélice «{d['helice']}» no está recomendada (KWS «X») para {diam} plg con "
                                 f"carga {clase}.")
            continue
        rpm_max, cap_max, cap1 = CAPACIDAD[clase][diam]
        nivel_cap = EMPIRICA
        if d["capacidad_rpm"] > 0 or d["rpm_maxima"] > 0:
            nivel_cap = DATO
            cap1 = d["capacidad_rpm"] if d["capacidad_rpm"] > 0 else cap1
            rpm_max = d["rpm_maxima"] if d["rpm_maxima"] > 0 else rpm_max
            cap_max = cap1 * rpm_max
            r.nota("Capacidad por rpm y/o velocidad máxima tomadas del catálogo capturado por el usuario.")
        sc = sc_sin_cf2 * cf2
        if manual or sc <= cap_max:
            return diam, cf2, sc, cap1, rpm_max, cap_max, nivel_cap
    raise ErrorEntrada(f"Ningún diámetro de la tabla KWS (hasta 36 plg) admite la capacidad de selección con carga "
                       f"{clase} y hélice «{d['helice']}». Divida el flujo o consulte al fabricante.")


def _diametro_minimo(d: dict, clase: str, sc_sin_cf2: float) -> int | None:
    columna = CLASES[clase]
    for diam in DIAMETROS:
        cf2 = factor_cf2(d["helice"], columna, diam)
        if cf2 is not None and sc_sin_cf2 * cf2 <= CAPACIDAD[clase][diam][1]:
            return diam
    return None


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rho, clase, mf = _datos_material(d, r)
    columna = CLASES[clase]
    rho_lb = rho / K.KGM3_POR_LBPIE3

    # --- Capacidad --------------------------------------------------------
    masa_th = d["capacidad"] * d["factor_capacidad"]
    cp_lbh = masa_th * 1000.0 / K.KG_POR_LIBRA
    cfh = cp_lbh / rho_lb
    cf1 = PASOS[d["paso"]]
    cf3 = CF3[d["paletas"]]

    angulo = d["angulo"]
    eta_inc = d["eficiencia_inclinacion"]
    fi = d["factor_inclinacion"]
    if angulo > INCLINACION_SIN_CORRECCION:
        requerir(eta_inc > 0 and fi > 0,
                 f"Con {angulo:g}° de inclinación (> {INCLINACION_SIN_CORRECCION:g}°) capture la eficiencia de "
                 "transporte y el factor de potencia Fi de la gráfica del fabricante para el paso y la artesa usados.")
    if fi > 0:
        requerir(fi >= 1, "El factor de potencia por inclinación Fi debe ser ≥ 1.")
    eta_inc = eta_inc if eta_inc > 0 else 1.0
    fi = fi if fi > 0 else 1.0
    if 0 < angulo <= INCLINACION_SIN_CORRECCION and (d["eficiencia_inclinacion"] == 0 or d["factor_inclinacion"] == 0):
        r.advertir(f"Inclinación de {angulo:g}°: KWS indica pérdida mínima hasta 10°; no se aplicó corrección "
                   "por falta de factores capturados.")

    sc_sin_cf2 = cfh * cf1 * cf3 / eta_inc
    diam, cf2, sc, cap1, rpm_max, cap_max, nivel_cap = _seleccionar_diametro(d, clase, sc_sin_cf2, r)
    rpm = sc / cap1

    cumple = sc <= cap_max * (1 + 1e-9)
    if not cumple:
        sugerido = _diametro_minimo(d, clase, sc_sin_cf2)
        texto = f" El menor diámetro que cumple es {sugerido} plg." if sugerido else ""
        r.advertir(f"NO CUMPLE: la capacidad de selección ({sc:.0f} ft³/h) excede la capacidad a velocidad máxima "
                   f"del tornillo de {diam} plg ({cap_max:.0f} ft³/h).{texto}")
    elif rpm > rpm_max * 1.0001:
        r.advertir(f"La velocidad calculada ({rpm:.1f} rpm) supera ligeramente la máxima de tabla ({rpm_max:g} rpm) "
                   "por el redondeo de la capacidad a 1 rpm publicada; confirme con el fabricante.")

    # --- Potencia ---------------------------------------------------------
    hbf = COJINETES[d["cojinete"]]
    sf = SF[d["helice"]][columna]
    if sf is None:
        raise ErrorEntrada(f"La hélice «{d['helice']}» no está recomendada con carga {clase}.")
    pf = PF[d["paletas"]]
    largo_pie = d["longitud"] / K.M_POR_PIE
    e = d["eficiencia"] / 100.0
    fhp = potencia_friccion(largo_pie, rpm, diam, hbf)
    mhp = potencia_material(cp_lbh, largo_pie, mf, sf, pf)

    if d["mhp_corregido"] > 0:
        requerir(d["mhp_corregido"] >= mhp * 0.999,
                 f"El MHP corregido ({d['mhp_corregido']:g} HP) no puede ser menor que el MHP calculado ({mhp:.3f} HP).")
        metodo = "KWS (MHP corregido capturado)"
        fo, nivel_fo = 1.0, DATO
        tshp = (fhp + d["mhp_corregido"]) * fi / e
        if mhp >= 5:
            r.advertir("KWS corrige el MHP solo cuando es menor de 5 HP; revise el MHP corregido capturado.")
    else:
        metodo = "CEMA (Fo sobre HPf + HPm)"
        base = fhp + mhp
        if d["factor_sobrecarga"] > 0:
            requerir(d["factor_sobrecarga"] >= 1, "El factor de sobrecarga Fo debe ser ≥ 1.")
            fo, nivel_fo = float(d["factor_sobrecarga"]), DATO
        else:
            fo, nivel_fo = fo_cema_aproximado(base), EMPIRICA
            if base < 5.2:
                r.advertir("Fo obtenido por interpolación log-lineal de la gráfica CEMA (aproximación, no transcripción "
                           "de la gráfica). Para un valor exacto capture Fo leído de la gráfica o el MHP corregido KWS.")
        tshp = (fhp + mhp) * fo * fi / e
    kw = K.hp_a_kw(tshp)
    motor_hp = motor_nema_hp(tshp)
    motor_kw = motor_iec_kw(kw)

    # --- Salidas ------------------------------------------------------------
    nivel_mat = DATO if d["densidad"] > 0 else EMPIRICA
    r.agregar("densidad", "Densidad aparente usada", rho, "kg/m³", 0, nivel_mat)
    r.agregar("densidad_lbft3", "Densidad aparente usada", rho_lb, "lb/ft³", 1, nivel_mat)
    r.agregar("clase_carga", "Carga de artesa (clase KWS)", {"15": "15 %", "30A": "30 % (30A)", "30B": "30 % (30B)",
                                                             "45": "45 %"}[clase], "", 0,
              DATO if CARGAS[d["carga"]] else EMPIRICA)
    r.agregar("mf", "Factor de material MF", mf, "", 2, DATO if d["factor_material"] > 0 else EMPIRICA)
    r.agregar("capacidad_lbh", "Capacidad de diseño CP", cp_lbh, "lb/h", 0, DATO)
    r.agregar("cfh", "Capacidad volumétrica CFH", cfh, "ft³/h", 1, VERIFICADA)
    r.agregar("cfh_m3h", "Capacidad volumétrica CFH", cfh * K.M3_POR_PIE3, "m³/h", 2, DATO)
    r.agregar("cf1", "Factor de paso CF1", cf1, "", 2, EMPIRICA)
    r.agregar("cf2", "Factor de hélice especial CF2", cf2, "", 2, EMPIRICA)
    r.agregar("cf3", "Factor de paletas CF3", cf3, "", 2, EMPIRICA)
    if eta_inc < 1:
        r.agregar("eficiencia_inclinacion", "Eficiencia de transporte por inclinación", eta_inc, "", 2, DATO)
    r.agregar("sc", "Capacidad de selección SC", sc, "ft³/h", 1, EMPIRICA)
    r.agregar("diametro", "Diámetro del tornillo", diam, "plg", 0, DATO if d["diametro"] != AUTOMATICO else EMPIRICA)
    r.agregar("diametro_mm", "Diámetro del tornillo", diam * 25.4, "mm", 0, DATO)
    r.agregar("capacidad_1rpm", "Capacidad a 1 rpm", cap1, "ft³/(h·rpm)", 2, nivel_cap)
    r.agregar("rpm_maxima", "Velocidad máxima recomendada", rpm_max, "rpm", 0, nivel_cap)
    r.agregar("capacidad_maxima", "Capacidad a velocidad máxima", cap_max, "ft³/h", 0, nivel_cap)
    r.agregar("rpm", "Velocidad de giro requerida", rpm, "rpm", 1, EMPIRICA)
    r.agregar("cumple", "Cumple capacidad a velocidad máxima", cumple, "", 0, EMPIRICA)
    r.agregar("df", "Factor de diámetro DF", DF[diam], "", 0, EMPIRICA)
    r.agregar("hbf", "Factor de cojinete colgante HBF", hbf, "", 1, EMPIRICA)
    r.agregar("sf", "Factor de hélice especial SF (potencia)", sf, "", 2, EMPIRICA)
    r.agregar("pf", "Factor de paletas PF (potencia)", pf, "", 2, EMPIRICA)
    r.agregar("longitud_pie", "Longitud", largo_pie, "ft", 2, DATO)
    r.agregar("fhp", "Potencia de fricción FHP", fhp, "HP", 4, EMPIRICA)
    r.agregar("mhp", "Potencia de material MHP", mhp, "HP", 4, EMPIRICA)
    r.agregar("metodo_sobrecarga", "Corrección por sobrecarga", metodo, "", 0, DATO)
    if d["mhp_corregido"] > 0:
        r.agregar("mhp_corregido", "MHP corregido (gráfica KWS)", d["mhp_corregido"], "HP", 3, DATO)
    else:
        r.agregar("fo", "Factor de sobrecarga Fo", fo, "", 2, nivel_fo,
                  "" if nivel_fo == DATO else "Aproximación de la gráfica CEMA" if fhp + mhp < 5.2 else "")
    if fi > 1:
        r.agregar("fi", "Factor de potencia por inclinación Fi", fi, "", 2, DATO)
    r.agregar("tshp", "Potencia total en la flecha TSHP", tshp, "HP", 3, EMPIRICA)
    r.agregar("tshp_kw", "Potencia total en la flecha", kw, "kW", 3, EMPIRICA)
    if motor_hp is not None:
        r.agregar("motor_hp", "Motor comercial mínimo (NEMA MG 1)", motor_hp, "HP", 2, DATO)
        par = PAR_HP_RPM * motor_hp / rpm
        r.agregar("par_motor", "Par a plena carga del motor en el tornillo", par, "lbf·plg", 0, VERIFICADA)
        r.agregar("par_motor_nm", "Par a plena carga del motor en el tornillo", par * LB_PLG_A_NM, "N·m", 1, DATO)
    else:
        r.advertir("La potencia excede la serie NEMA incluida; seleccione el motor con el fabricante.")
    if motor_kw is not None:
        r.agregar("motor_kw", "Motor comercial mínimo (IEC 60072-1)", motor_kw, "kW", 2, DATO)

    if angulo > 0:
        masa_kgs = masa_th * 1000.0 / 3600.0
        elevacion = d["longitud"] * math.sin(math.radians(angulo))
        p_elev = masa_kgs * K.G * elevacion / 1000.0
        r.agregar("elevacion", "Elevación del material", elevacion, "m", 2, VERIFICADA)
        r.agregar("potencia_elevacion", "Potencia teórica mínima para elevar el material (ṁ·g·H)", p_elev, "kW", 3,
                  VERIFICADA, "Cota inferior física; no incluye fricción")
        if kw < p_elev / e:
            r.advertir("La potencia calculada es menor que la necesaria solo para elevar el material: revise los "
                       "factores de inclinación capturados.")

    r.nota("Método válido para transportadores alimentados de forma controlada; los alimentadores de tornillo "
           "(screw feeders) requieren consideraciones adicionales de arranque y par (KWS, CEMA 351).")
    r.nota("Verifique el par a plena carga contra la capacidad de la flecha motriz, flechas de acople, tornillos de "
           "acople y tubo del tornillo (tablas de par del fabricante) y el tamaño máximo de terrón admisible.")
    r.ecuacion("CP = Q·f·1000/0.45359237 [lb/h];   CFH = CP/ρ [ft³/h]")
    r.ecuacion("SC = CFH·CF1·CF2·CF3 / η_incl;   N = SC / (capacidad a 1 rpm)")
    r.ecuacion("FHP = L·N·DF·HBF/10⁶;   MHP = CP·L·MF·SF·PF/10⁶   (L en ft)")
    if d["mhp_corregido"] > 0:
        r.ecuacion("TSHP = (FHP + MHP_corregido)·Fi / e   (KWS)")
    else:
        r.ecuacion("TSHP = (FHP + MHP)·Fo·Fi / e   (CEMA)")
    r.ecuacion("T = 63 025·HP_motor / N [lbf·plg]")
    return r


CALCULADORA = Calculadora(
    id="helicoidal",
    nombre="Transportador helicoidal",
    disciplina="Manejo de sólidos a granel",
    descripcion="Selección de diámetro y velocidad, potencia y par por el método CEMA (tablas KWS).",
    campos=CAMPOS,
    funcion=calcular,
    estado_validacion=VALIDADA_CONDICIONES,
    archivos_originales=("Calculo del transportador helicoidal.py",),
    referencias=(
        f"{FUENTE_KWS}: Screw Conveyor Capacity, Screw Conveyor Horsepower, Bulk Material Table, "
        "Screw Conveyor Torque (kwsmfg.com, consultado nov. 2026).",
        "CEMA 350 — Screw Conveyors for Bulk Materials (método de potencia con Fo), según catálogo Martin, "
        "sección H (aprobado por la sección de transportadores helicoidales de CEMA).",
        "NEMA MG 1 (potencias nominales de motores, HP); IEC 60072-1 (potencias nominales, kW).",
    ),
    limitaciones=(
        "Validado con el ejemplo publicado por KWS (harina de maíz, 12 plg, 30A): ver tests/test_helicoidal.py.",
        "Fo por interpolación de la gráfica CEMA cuando no se captura: aproximación (nivel E).",
        "Inclinación > 10° solo con factores capturados por el usuario; > 45° fuera de alcance.",
        "No cubre alimentadores de tornillo, transportadores verticales ni sin flecha (shaftless).",
        "No verifica tamaño de terrón ni resistencia de componentes (solo calcula el par a plena carga).",
    ),
    imagenes=(),
    palabras_clave=("helicoidal", "tornillo", "sinfín", "screw", "transportador", "CEMA", "KWS"),
)
