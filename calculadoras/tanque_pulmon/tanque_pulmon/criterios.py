"""Criterios de aceptación y clasificaciones normativas.

Los límites de aceptación (tiempo de retención, fracción de carga, arranques por hora) son
DATOS DEL PROYECTO o del fabricante: la calculadora no los inventa. Si no se capturan, la
verificación se reporta como "sin criterio".

Referencias verificadas:
- NOM-020-STPS-2011, numeral 7.1.1 (Tabla 1): clasificación por presión de calibración del
  dispositivo de relevo y volumen. Numeral 14.2: la presión de calibración debe ser <= PTMP y
  > presión de operación.
- ASME B31.3-2014 §300.1.1(b)(3): el aire está dentro del alcance; §300.1.3(d): excluye
  recipientes a presión (el tanque se diseña con ASME BPVC Sec. VIII); §300.2: Categoría D
  (no inflamable, no tóxico, p_diseño <= 1035 kPa man., T_diseño <= 186 °C), a designar por
  el propietario.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Criterios:
    t_retencion_min: Optional[float] = None
    fraccion_carga_max: Optional[float] = None
    ciclos_h_max: Optional[float] = None
    p_min_consumidor_pa: Optional[float] = None   # absoluta, en el punto de consumo
    dp_linea_pa: float = 0.0                      # caída de presión tanque -> consumidor
    p_calibracion_psv_pa_g: Optional[float] = None
    p_diseno_pa_g: Optional[float] = None
    t_diseno_c: Optional[float] = None


@dataclass
class Verificacion:
    criterio: str
    valor: str
    limite: str
    estado: str      # "CUMPLE", "NO CUMPLE", "SIN CRITERIO", "INFORMATIVO"
    referencia: str = ""


def clasificar_nom020(p_calibracion_kpa_g: float, volumen_m3: float, fluido_peligroso=False) -> str:
    """NOM-020-STPS-2011, numeral 7.1.1. Presión en kPa manométricos."""
    p, v = p_calibracion_kpa_g, volumen_m3
    if not fluido_peligroso:
        if p <= 490.33:
            return "I" if v <= 0.5 else "II"
        if p <= 784.53:
            return "II" if v <= 1.0 else "III"
        return "III"
    if p <= 686.47:
        return "II" if v <= 1.0 else "III"
    return "III"


def verificar(e, r, c: Criterios) -> List[Verificacion]:
    from .unidades import min_a_texto
    v: List[Verificacion] = []

    if c.t_retencion_min is None:
        v.append(Verificacion("Tiempo de retención", min_a_texto(r.t_retencion_min), "—", "SIN CRITERIO",
                              "Definir en bases de diseño / especificación del proyecto"))
    else:
        ok = r.t_retencion_min >= c.t_retencion_min
        v.append(Verificacion("Tiempo de retención", min_a_texto(r.t_retencion_min),
                              f"≥ {min_a_texto(c.t_retencion_min)}", "CUMPLE" if ok else "NO CUMPLE",
                              "Criterio del proyecto"))

    if r.fraccion_carga is not None:
        if c.fraccion_carga_max is None:
            v.append(Verificacion("Fracción de carga del compresor", f"{r.fraccion_carga*100:.1f} %", "—",
                                  "SIN CRITERIO", "Dato del fabricante del compresor"))
        else:
            ok = r.fraccion_carga <= c.fraccion_carga_max
            v.append(Verificacion("Fracción de carga del compresor", f"{r.fraccion_carga*100:.1f} %",
                                  f"≤ {c.fraccion_carga_max*100:.0f} %", "CUMPLE" if ok else "NO CUMPLE",
                                  "Dato del fabricante del compresor"))
    if r.ciclos_por_hora_max is not None:
        peor = r.ciclos_por_hora_max
        if c.ciclos_h_max is None:
            v.append(Verificacion("Ciclos/h, caso más desfavorable (consumo = 50 % FAD)", f"{peor:.1f}", "—",
                                  "SIN CRITERIO", "Dato del fabricante del compresor/motor"))
        else:
            ok = peor <= c.ciclos_h_max
            v.append(Verificacion("Ciclos/h, caso más desfavorable (consumo = 50 % FAD)", f"{peor:.1f}",
                                  f"≤ {c.ciclos_h_max:.0f}", "CUMPLE" if ok else "NO CUMPLE",
                                  "Dato del fabricante del compresor/motor"))

    if c.p_min_consumidor_pa is not None:
        req = c.p_min_consumidor_pa + c.dp_linea_pa
        ok = e.p_inferior_pa >= req
        v.append(Verificacion("Presión inferior ≥ mínima del consumidor + ΔP de línea",
                              f"{e.p_inferior_pa/1000:.1f} kPa a", f"≥ {req/1000:.1f} kPa a",
                              "CUMPLE" if ok else "NO CUMPLE", "Balance de presiones"))

    p_cal = c.p_calibracion_psv_pa_g
    p_op_g = e.p_superior_pa - e.p_atm_sitio_pa
    if p_cal is None:
        cat = clasificar_nom020(p_op_g / 1000.0, e.v_tanque_m3)
        v.append(Verificacion("Categoría NOM-020-STPS-2011 (con presión de operación como cota inferior)",
                              f"Categoría {cat}", "—", "INFORMATIVO",
                              "NOM-020-STPS-2011, num. 7.1.1; la presión de calibración real es mayor"))
    else:
        cat = clasificar_nom020(p_cal / 1000.0, e.v_tanque_m3)
        v.append(Verificacion("Categoría NOM-020-STPS-2011", f"Categoría {cat}", "—", "INFORMATIVO",
                              "NOM-020-STPS-2011, num. 7.1.1"))
        ok = p_cal > p_op_g
        v.append(Verificacion("Calibración de la válvula de seguridad > presión de operación",
                              f"{p_cal/1000:.1f} kPa man.", f"> {p_op_g/1000:.1f} kPa man.",
                              "CUMPLE" if ok else "NO CUMPLE", "NOM-020-STPS-2011, num. 14.2 b)"))
        if c.p_diseno_pa_g is not None:
            ok = p_cal <= c.p_diseno_pa_g
            v.append(Verificacion("Calibración de la válvula de seguridad ≤ PTMP / presión de diseño",
                                  f"{p_cal/1000:.1f} kPa man.", f"≤ {c.p_diseno_pa_g/1000:.1f} kPa man.",
                                  "CUMPLE" if ok else "NO CUMPLE", "NOM-020-STPS-2011, num. 14.2 a)"))

    if c.p_diseno_pa_g is not None and c.t_diseno_c is not None:
        elegible = c.p_diseno_pa_g <= 1_035_000.0 and c.t_diseno_c <= 186.0
        v.append(Verificacion("Tubería: elegible como Categoría D (B31.3) si el propietario la designa",
                              "Sí" if elegible else "No",
                              "p ≤ 1035 kPa man., T ≤ 186 °C", "INFORMATIVO",
                              "ASME B31.3-2014 §300.2 (verificar edición contractual)"))
    return v
