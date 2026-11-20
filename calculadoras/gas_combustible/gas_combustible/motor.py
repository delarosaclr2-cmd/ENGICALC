"""Gas combustible: propiedades desde la cromatografía, flujo de combustible de una turbina y
estadística de consumos diarios.

Ecuaciones:
    M  = Σ x_i·M_i                                  (x_i fracción molar normalizada; M_i de GPA 2145-16)
    SG_ideal = M / M_aire,  M_aire = 28.9625         (GPA 2145-16)
    ρ_ref = P_ref·M / (Z_ref·R_u·T_ref)              (Z_ref: laboratorio, CoolProp o 1 con advertencia)
    ṁ_f = HR·P_el / (LHV·3600)                       (kg/s; HR en kJ/kWh, P_el en kW, LHV en kJ/kg)
    LHV_masa = LHV_vol / ρ_ref                       (misma condición de referencia en ambos)
    Q_ref = ṁ/ρ_ref ;  Q_real = ṁ/ρ(P,T,Z)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

R_U = 8314.462618
M_AIRE = 28.9625

# GPA 2145-16, kg/kmol. Claves en español como en el reporte de laboratorio; alias CoolProp.
COMPONENTES = {
    "metano": (16.0425, "Methane"), "etano": (30.069, "Ethane"), "propano": (44.0956, "n-Propane"),
    "isobutano": (58.1222, "IsoButane"), "n-butano": (58.1222, "n-Butane"),
    "isopentano": (72.1488, "Isopentane"), "n-pentano": (72.1488, "n-Pentane"),
    "hexano": (86.1754, "n-Hexane"), "heptano": (100.2019, "n-Heptane"), "octano": (114.2285, "n-Octane"),
    "nonano": (128.2551, "n-Nonane"), "oxigeno": (31.9988, "Oxygen"), "nitrogeno": (28.0134, "Nitrogen"),
    "co2": (44.0095, "CarbonDioxide"), "h2s": (34.0809, "HydrogenSulfide"), "agua": (18.0153, "Water"),
}

REFERENCIAS = {"normal": (101_325.0, 273.15), "estandar_60F": (101_325.0, 288.7056),
               "estandar_15C": (101_325.0, 288.15)}


class ErrorEntrada(ValueError):
    pass


@dataclass
class Propiedades:
    suma_pct: float
    m_kg_kmol: float
    sg_ideal: float
    z_ref: float
    fuente_z: str
    rho_ref: float
    ref: str
    advertencias: List[str] = field(default_factory=list)


def z_coolprop(composicion: Dict[str, float], t_k: float, p_pa: float) -> Optional[float]:
    try:
        import CoolProp.CoolProp as CP
    except ImportError:
        return None
    s = sum(composicion.values())
    fl = "HEOS::" + "&".join(f"{COMPONENTES[k][1]}[{v / s}]" for k, v in composicion.items() if v > 0)
    return CP.PropsSI("Z", "T", t_k, "P", p_pa, fl)


def propiedades(composicion: Dict[str, float], ref="estandar_60F", z_ref: Optional[float] = None,
                usar_coolprop=True) -> Propiedades:
    if not composicion:
        raise ErrorEntrada("Composición vacía")
    for k, v in composicion.items():
        if k not in COMPONENTES:
            raise ErrorEntrada(f"Componente desconocido: {k}. Válidos: {', '.join(COMPONENTES)}")
        if v is None or not math.isfinite(v) or v < 0:
            raise ErrorEntrada(f"Fracción inválida para {k}")
    if ref not in REFERENCIAS:
        raise ErrorEntrada(f"Referencia desconocida: {ref}")
    s = sum(composicion.values())
    adv = []
    if abs(s - 100.0) > 0.5:
        raise ErrorEntrada(f"La composición suma {s:.3f} % mol; revise el reporte (tolerancia ±0.5 %)")
    if abs(s - 100.0) > 0.01:
        adv.append(f"La composición suma {s:.3f} % mol; se normalizó a 100 %")
    m = sum(v * COMPONENTES[k][0] for k, v in composicion.items()) / s
    p, t = REFERENCIAS[ref]
    fuente = "capturado"
    if z_ref is None and usar_coolprop:
        z_ref = z_coolprop(composicion, t, p)
        fuente = "CoolProp (HEOS)"
    if z_ref is None:
        z_ref, fuente = 1.0, "gas ideal (Z = 1)"
        adv.append("Z de referencia no disponible: se usó gas ideal (error ≈ 0.2 % en densidad)")
    if not 0.95 <= z_ref <= 1.0:
        adv.append(f"Z de referencia = {z_ref:.4f} fuera de lo esperado (≈0.997–0.999) a condición estándar")
    rho = p * m / (z_ref * R_U * t)
    return Propiedades(s, m, m / M_AIRE, z_ref, fuente, rho, ref, adv)


def flujo_turbina_kg_s(heat_rate_kj_kwh: float, potencia_kw: float, lhv_kj_kg: float) -> float:
    for n, v in (("tasa de calor", heat_rate_kj_kwh), ("potencia", potencia_kw), ("LHV", lhv_kj_kg)):
        if v is None or not math.isfinite(v) or v <= 0:
            raise ErrorEntrada(f"{n}: debe ser positivo")
    if not 5_000 <= heat_rate_kj_kwh <= 25_000:
        raise ErrorEntrada("Tasa de calor fuera de 5 000–25 000 kJ/kWh: revise unidades")
    if not 30_000 <= lhv_kj_kg <= 60_000:
        raise ErrorEntrada("LHV fuera de 30 000–60 000 kJ/kg: ¿se capturó en kJ/m³ o MJ/kg?")
    return heat_rate_kj_kwh * potencia_kw / (lhv_kj_kg * 3600.0)


def lhv_masico(lhv_vol_mj_m3: float, rho_ref: float) -> float:
    """kJ/kg a partir de MJ/m³ a la MISMA condición de referencia de ρ_ref."""
    return lhv_vol_mj_m3 * 1000.0 / rho_ref


def rho_real(m_kg_kmol, p_pa, t_k, z):
    return p_pa * m_kg_kmol / (z * R_U * t_k)


@dataclass
class EstadisticaConsumo:
    unidades: List[str]
    total_por_dia: List[float]
    dia_max: str
    total_max: float
    promedio: float
    max_por_unidad: Dict[str, float]
    dia_max_por_unidad: Dict[str, str]
    suma_max_no_coincidentes: float


def estadistica(fechas: List[str], consumos: Dict[str, List[float]]) -> EstadisticaConsumo:
    """Totales diarios sumando TODAS las unidades (no rangos parciales)."""
    if not fechas:
        raise ErrorEntrada("Tabla de consumos vacía")
    for k, serie in consumos.items():
        if len(serie) != len(fechas):
            raise ErrorEntrada(f"La serie {k} tiene {len(serie)} datos y hay {len(fechas)} fechas")
        if any(v is None or v < 0 for v in serie):
            raise ErrorEntrada(f"La serie {k} tiene valores vacíos o negativos")
    tot = [sum(consumos[k][i] for k in consumos) for i in range(len(fechas))]
    imax = max(range(len(tot)), key=tot.__getitem__)
    mx = {k: max(v) for k, v in consumos.items()}
    dmx = {k: fechas[max(range(len(v)), key=v.__getitem__)] for k, v in consumos.items()}
    return EstadisticaConsumo(list(consumos), tot, fechas[imax], tot[imax], sum(tot) / len(tot), mx, dmx,
                              sum(mx.values()))
