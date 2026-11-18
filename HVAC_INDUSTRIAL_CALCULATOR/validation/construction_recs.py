"""Recomendaciones constructivas y de instalación.

Se distinguen dos tipos:
* 'Conceptual'  — recomendación de práctica de ingeniería para el diseño básico.
* 'Requiere diseño especializado (…)' — verificación que debe hacer un especialista
  (estructural, eléctrico, seguridad de procesos, mecánico de detalle).
"""
from __future__ import annotations

from dataclasses import dataclass

CONCEPTUAL = "Conceptual"


@dataclass
class ConstructionRec:
    topic: str
    text: str
    kind: str
    source: str = ""


def build_recommendations(project, results) -> list[ConstructionRec]:
    recs: list[ConstructionRec] = []
    model = results.model
    dusty = project.network_settings.contaminant_class not in ("gases_vapors", "clean_air")
    hot = any((n.temperature_c or 0) > 50 for n in model.nodes.values()) if model else False
    air = results.air
    cond_risk = any(a.parameter == "Riesgo de condensación" for a in results.alerts)
    R = recs.append
    R(ConstructionRec("Distribución de ductos", "Trazar el recorrido más corto y directo; conectar ramales al principal "
      "con ángulos de 30°–45° y en el costado o parte superior del principal; evitar uniones a 90° y tees opuestas.",
      CONCEPTUAL, "ACGIH (práctica de diseño de sistemas de extracción)"))
    R(ConstructionRec("Distribución de ductos", "Usar codos de radio amplio (R/D entre 1.5 y 2.5) y transiciones "
      "graduales; no conectar dos ramales en el mismo punto del principal.", CONCEPTUAL, "ACGIH; Idelchik"))
    R(ConstructionRec("Soportería", "Calibres, refuerzos, uniones y separación de soportes según SMACNA HVAC Duct "
      "Construction Standards; considerar el peso del polvo que pueda acumularse en una falla del sistema, cargas de "
      "viento/sismo en ductos exteriores y la chimenea.", "Requiere diseño especializado (estructural)",
      "SMACNA HVAC Duct Construction Standards; reglamento de construcción local"))
    R(ConstructionRec("Accesibilidad", "Prever puertas de inspección y limpieza cerca de codos, uniones y puntos de "
      "posible acumulación; acceso seguro al ventilador, transmisión y colector.", CONCEPTUAL,
      "ACGIH; NFPA 91 (sistemas de extracción de partículas) — verificar aplicabilidad"))
    R(ConstructionRec("Conexiones flexibles", "Instalar conexiones flexibles en la succión y descarga del ventilador "
      "para aislar vibraciones; material compatible con la temperatura y abrasión del aire transportado.", CONCEPTUAL,
      "ASHRAE HVAC Applications (control de ruido y vibración)"))
    R(ConstructionRec("Ubicación del ventilador", "Ubicar el ventilador en el lado limpio, después del colector, para "
      "reducir la abrasión del rodete; preferentemente fuera del edificio para que los ductos interiores trabajen en "
      "presión negativa (fugas hacia adentro). Dejar tramos rectos en entrada y salida para minimizar el efecto del "
      "sistema.", CONCEPTUAL, "AMCA 201; ACGIH"))
    R(ConstructionRec("Descarga al exterior", "Descarga vertical libre, sin sombreretes que desvíen el chorro hacia "
      "abajo; altura y velocidad de salida suficientes y distancia a tomas de aire exterior para evitar reingreso.",
      CONCEPTUAL, "ASHRAE HVAC Applications (Building Air Intake and Exhaust Design); ACGIH"))
    R(ConstructionRec("Vibraciones y ruido", "Montar el ventilador sobre base de inercia o aisladores seleccionados "
      "por el fabricante; balanceo dinámico del rodete; evaluar silenciador si el nivel sonoro lo exige.",
      "Requiere diseño especializado (mecánico/acústico)", "ASHRAE HVAC Applications (Noise and Vibration Control)"))
    if dusty:
        R(ConstructionRec("Transporte de partículas", "Ductos circulares, sin tramos horizontales largos a velocidades "
          "marginales; no instalar compuertas que puedan acumular polvo; prever monitoreo de presión diferencial del "
          "colector.", CONCEPTUAL, "ACGIH (velocidades de transporte)"))
        R(ConstructionRec("Polvos combustibles", "Si el polvo es combustible se requiere análisis de riesgo de polvo "
          "(DHA): venteo o supresión de explosiones en el colector, aislamiento de explosión en ductos, puesta a tierra y "
          "control de fuentes de ignición.", "Requiere diseño especializado (seguridad de procesos)",
          "NFPA 652 / NFPA 654 (verificar aplicabilidad)"))
    if hot:
        R(ConstructionRec("Aislamiento térmico", "Aislar los tramos con aire caliente para protección del personal y "
          "para evitar condensación; considerar dilatación térmica (juntas y soportes deslizantes).",
          "Requiere diseño especializado (mecánico)", "ASHRAE Fundamentals (aislamiento)"))
    if cond_risk or hot:
        R(ConstructionRec("Drenajes y condensados", "Prever drenajes en puntos bajos, en la base de la chimenea y en el "
          "colector; pendiente de los tramos horizontales hacia los drenajes.", CONCEPTUAL, "Práctica de diseño"))
    R(ConstructionRec("Protección contra corrosión", "Seleccionar material/recubrimiento según la composición y humedad "
      "del aire transportado (galvanizado, inoxidable, recubrimientos epóxicos, plásticos).", CONCEPTUAL,
      "SMACNA; datos del fabricante"))
    R(ConstructionRec("Seguridad de operación", "Guardas en transmisiones, bloqueo y etiquetado para mantenimiento, "
      "protecciones del motor y paro de emergencia.", "Requiere diseño especializado (eléctrico/seguridad)",
      "NOM-004-STPS-1999; NOM-001-SEDE-2012"))
    R(ConstructionRec("Instalación eléctrica", "Alimentador, protecciones y arrancador/variador del motor dimensionados "
      "por el especialista eléctrico con la potencia y corriente de placa.", "Requiere diseño especializado (eléctrico)",
      "NOM-001-SEDE-2012"))
    R(ConstructionRec("Interferencias", "Coordinar trayectorias con estructura, charolas, tuberías y equipos (modelo 3D "
      "con detección de interferencias) antes de fabricar.", CONCEPTUAL, "Práctica de ingeniería de detalle"))
    R(ConstructionRec("Puesta en marcha", "Medir caudales y presión estática de cada campana (SPh) y registrar valores de "
      "referencia para el mantenimiento; ajustar rpm para el caudal de diseño.", CONCEPTUAL,
      "ACGIH (pruebas y mantenimiento de sistemas); AMCA 203"))
    return recs
