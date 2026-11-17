"""Dimensionamiento de colector de polvo (filtro de mangas con ciclón).

Original: «calculo de colector de polvo.py».
Correcciones:
- Potencia: el original convertía mm H₂O a Pa y luego dividía entre 102
  (factor válido solo para mm H₂O); sobreestimaba 9.81 veces. Ahora P = ΔP·Q/η.
- Almacenamiento: el original suponía polvo = caudal de aire/10 (12 000 m³ de
  polvo en 12 h para 10 000 m³/h de aire). Ahora se calcula con la carga de
  polvo, la eficiencia de captación y la densidad aparente.
- La relación aire/tela 1.0 y 2.5 m/min se conserva como criterio original.

v2.1.0: relación aire/tela por tipo de polvo y de limpieza según EPA Air
Pollution Control Cost Manual (EPA/452/B-02-001), sección 6, cap. 1
«Baghouses and Filters», tabla 1.1 «Gas-to-cloth ratios for baghouse/fabric
combinations» (valores de diseño generalmente seguros, ft/min = m³/min por m²·
0.3048). Prioridad: valor capturado > tabla EPA > criterio original.
"""
from __future__ import annotations

from ..nucleo import constantes as K, fluidos
from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                             ErrorEntrada, Resultado)

FINO = "Fino — 1.0 m/min (criterio original)"
GRUESO = "Grueso — 2.5 m/min (criterio original)"
CAPTURAR = "Capturar relación aire/tela"
RELACION_ORIGINAL = {FINO: 1.0, GRUESO: 2.5}

# EPA/452/B-02-001, sec. 6 cap. 1, tabla 1.1 [ft/min]: (tela tejida: sacudido o aire inverso, fieltro: pulse jet)
EPA_TABLA_1_1 = {
    "Alúmina": (2.5, 8), "Arcilla": (2.5, 9), "Arena": (2.5, 10), "Aserrín (madera)": (3.5, 12),
    "Asbesto": (3.0, 10), "Azúcar": (2.0, 13), "Bauxita": (2.5, 8), "Cacao, chocolate": (2.8, 12),
    "Cal": (2.5, 10), "Caliza": (2.7, 8), "Carbón": (2.5, 8), "Cemento": (2.0, 8), "Ceniza volante": (2.5, 5),
    "Cosméticos": (1.5, 10), "Cuarzo": (2.8, 9), "Especias": (2.7, 10), "Feldespato": (2.2, 9),
    "Fertilizante": (3.0, 8), "Frita de esmalte": (2.5, 9), "Grafito": (2.0, 5), "Granos y alimento balanceado": (3.5, 14),
    "Harina": (3.0, 12), "Jabón y detergentes": (2.0, 5), "Mica": (2.7, 9), "Mineral de hierro": (3.0, 11),
    "Negro de humo": (1.5, 5), "Óxido de hierro": (2.5, 7), "Óxido de plomo": (2.0, 6), "Óxido de zinc": (2.0, None),
    "Papel": (3.5, 10), "Pigmentos de pintura": (2.5, 7), "Pizarra": (3.5, 12), "Plásticos": (2.5, 7),
    "Polvo de cuero": (3.5, 12), "Polvo de roca": (3.0, 9), "Sílice": (2.5, 7), "Sulfato de hierro": (2.0, 6),
    "Tabaco": (3.5, None), "Talco": (2.5, 5), "Yeso": (2.0, 10), "Almidón": (3.0, 8),
}
PULSE_JET = "Pulse jet, fieltro"
TEJIDA = "Sacudido o aire inverso, tela tejida"
M_POR_PIE = 0.3048

CAMPOS = [
    Campo("caudal", "Caudal de aire", "m³/h", minimo=0, min_incluido=False, grupo="Aire"),
    Campo("velocidad", "Velocidad en el ducto de entrada", "m/s", minimo=0, min_incluido=False, grupo="Aire",
          ayuda="El original indicaba 20–25 m/s."),
    Campo("tipo_polvo", "Polvo (relación aire/tela EPA, tabla 1.1)", tipo="opcion",
          opciones=tuple(sorted(EPA_TABLA_1_1)) + (FINO, GRUESO, CAPTURAR), defecto="Cemento", grupo="Filtro"),
    Campo("limpieza", "Tipo de limpieza y medio filtrante", tipo="opcion", opciones=(PULSE_JET, TEJIDA),
          defecto=PULSE_JET, grupo="Filtro"),
    Campo("relacion_aire_tela", "Relación aire/tela capturada", "m/min", defecto=0, minimo=0, grupo="Filtro",
          ayuda="Si se captura (> 0) tiene prioridad sobre la lista. Depende del polvo, de la limpieza y de la temperatura."),
    Campo("dp_filtro", "Pérdida de presión en filtro de mangas", "mm H₂O", minimo=0, grupo="Pérdidas",
          ayuda="El original indicaba 100–150 mm H₂O."),
    Campo("dp_ducto", "Pérdida de presión en ductos", "mm H₂O", minimo=0, grupo="Pérdidas",
          ayuda="El original indicaba 25–50 mm H₂O. Puede calcularse con la calculadora de ductos."),
    Campo("dp_ciclon", "Pérdida de presión en ciclón", "mm H₂O", defecto=0, minimo=0, grupo="Pérdidas",
          ayuda="El original indicaba 30–100 mm H₂O. 0 si no hay ciclón."),
    Campo("eficiencia", "Eficiencia del ventilador", "%", defecto=80, minimo=0, maximo=100, min_incluido=False,
          grupo="Ventilador"),
    Campo("carga_polvo", "Concentración de polvo en el aire", "g/m³", defecto=0, minimo=0, grupo="Almacenamiento",
          ayuda="0 = no calcular el almacenamiento."),
    Campo("eficiencia_captacion", "Eficiencia de captación", "%", defecto=100, minimo=0, maximo=100,
          min_incluido=False, grupo="Almacenamiento"),
    Campo("densidad_polvo", "Densidad aparente del polvo captado", "kg/m³", defecto=0, minimo=0,
          grupo="Almacenamiento"),
    Campo("horas", "Tiempo de almacenamiento en tolva", "h", defecto=12, minimo=0, min_incluido=False,
          grupo="Almacenamiento"),
]


def relacion_aire_tela(d: dict, r: Resultado) -> tuple[float, str]:
    """Relación aire/tela [m/min]. Prioridad: capturada > EPA tabla 1.1 > criterio original."""
    tipo = d["tipo_polvo"]
    if tipo == CAPTURAR or d["relacion_aire_tela"] > 0:
        if d["relacion_aire_tela"] <= 0:
            raise ErrorEntrada("Capture la relación aire/tela (m/min) o elija un polvo de la tabla EPA.")
        relacion = float(d["relacion_aire_tela"])
        if tipo != CAPTURAR:
            r.nota(f"Se usó la relación aire/tela capturada ({relacion:g} m/min) en lugar del valor de «{tipo}».")
        return relacion, DATO
    if tipo in EPA_TABLA_1_1:
        columna = 1 if d["limpieza"] == PULSE_JET else 0
        valor = EPA_TABLA_1_1[tipo][columna]
        if valor is None:
            raise ErrorEntrada(f"La tabla EPA 1.1 no da valor de «{tipo}» para {d['limpieza'].lower()}: "
                               "capture la relación aire/tela del fabricante.")
        r.nota(f"Relación aire/tela EPA (tabla 1.1) para {tipo}, {d['limpieza'].lower()}: {valor:g} ft/min "
               "(valor de diseño generalmente seguro; considere el tamaño de partícula y la carga de polvo).")
        return valor * M_POR_PIE, EMPIRICA
    r.advertir("Relación aire/tela tomada del criterio original (1.0 o 2.5 m/min) sin fuente documentada. "
               "Prefiera la tabla EPA o el dato del fabricante.")
    return RELACION_ORIGINAL[tipo], ORIGINAL


def calcular(d: dict) -> Resultado:
    r = Resultado()
    q_m3s = d["caudal"] / 3600.0
    q_m3min = d["caudal"] / 60.0

    relacion, nivel = relacion_aire_tela(d, r)

    diam = fluidos.diametro_por_caudal(q_m3s, d["velocidad"])
    area = q_m3min / relacion
    dp_mm = d["dp_filtro"] + d["dp_ducto"] + d["dp_ciclon"]
    dp_pa = dp_mm * K.PA_POR_MMH2O
    potencia = fluidos.potencia_incompresible(dp_pa, q_m3s, d["eficiencia"] / 100.0)

    r.agregar("diametro_mm", "Diámetro del ducto de entrada", diam * 1000, "mm", 1)
    r.agregar("relacion_aire_tela", "Relación aire/tela usada", relacion, "m/min", 2, nivel)
    r.agregar("relacion_aire_tela_ftmin", "Relación aire/tela usada", relacion / M_POR_PIE, "ft/min", 2, DATO)
    r.agregar("area_filtracion", "Área de filtración", area, "m²", 2, nivel)
    r.agregar("dp_total_mmh2o", "Pérdida de presión total", dp_mm, "mm H₂O", 1, DATO)
    r.agregar("dp_total_pa", "Pérdida de presión total", dp_pa, "Pa", 1, DATO)
    r.agregar("potencia_kw", "Potencia al eje del ventilador", potencia / 1000, "kW", 3)
    r.agregar("potencia_hp", "Potencia al eje del ventilador", potencia / K.W_POR_HP, "HP", 3, DATO)

    if d["carga_polvo"] > 0:
        if d["densidad_polvo"] <= 0:
            raise ErrorEntrada("Para el almacenamiento capture la densidad aparente del polvo captado.")
        masa_h = d["caudal"] * d["carga_polvo"] / 1000.0 * d["eficiencia_captacion"] / 100.0
        volumen = masa_h * d["horas"] / d["densidad_polvo"]
        r.agregar("polvo_kg_h", "Polvo captado", masa_h, "kg/h", 2)
        r.agregar("volumen_tolva", f"Volumen de polvo en {d['horas']:g} h", volumen, "m³", 3)
        r.ecuacion("ṁ_polvo = Q·c·η_captación;   V = ṁ_polvo·t/ρ_aparente")
    else:
        r.nota("Almacenamiento no calculado: capture la concentración de polvo (g/m³).")

    r.ecuacion("D = √(4·Q/(π·v))")
    r.ecuacion("A_filtración = Q[m³/min] / relación aire-tela[m/min]")
    r.ecuacion("ΔP[Pa] = ΔP[mm H₂O]·9.80665;   P = ΔP·Q/η")
    if d["limpieza"] == TEJIDA:
        r.nota("Sacudido o aire inverso: el área calculada es NETA; agregue los compartimentos fuera de línea "
               "para limpieza (EPA, tabla 1.3) para obtener el área bruta.")
    return r


CALCULADORA = Calculadora(
    id="colector",
    nombre="Colector de polvo",
    disciplina="Ventilación y control de polvo",
    descripcion="Área de filtración, pérdida total, potencia de ventilador y volumen de polvo captado.",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("calculo de colector de polvo.py",),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("Potencia de ventilador: P = ΔP·Q/η (mecánica de fluidos).",
                 "Relación aire/tela: EPA Air Pollution Control Cost Manual (EPA/452/B-02-001), sección 6, cap. 1, "
                 "tabla 1.1 (Turner et al.).",
                 "Validación: tests/test_colector.py (tabla 1.1 y ejemplo de la tabla 1.3 de la EPA)."),
    limitaciones=("Valores EPA: generalmente seguros; afinar con el fabricante según tamaño de partícula, carga de "
                  "polvo y temperatura.",
                  "Pérdidas de presión del filtro, ductos y ciclón: datos del usuario.",
                  "Sacudido y aire inverso: no se calculan los compartimentos fuera de línea (área bruta)."),
    palabras_clave=("filtro", "mangas", "ciclón", "colector", "polvo", "ventilador"),
)
