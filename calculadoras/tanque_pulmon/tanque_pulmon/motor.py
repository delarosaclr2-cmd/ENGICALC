"""Motor de cálculo del tanque pulmón (recipiente de aire comprimido).

Modelo: balance de masa en un volumen de control rígido (tanque + tubería conectada sin
regulador ni válvula de retención intermedios), gas ideal con factor Z opcional.

    m = P·V / (Z·R·T)                                    (1)
    ṁ = Q_ref · P_ref / (R · T_ref)                      (2)  caudal de aire libre -> masa
    Δm = V/(R·T_r) · (P_s/Z_s − P_i/Z_i)                 (3)  masa útil entre límites (isotérmico)
    t  = Δm / ṁ_neto                                     (4)

Con Z = 1, (3)+(4) se reducen a  t = V·(P_s − P_i)·T_ref / (Q_ref·P_ref·T_r),
que es la ecuación del documento original más el cociente de temperaturas T_ref/T_r.

Descarga politrópica opcional (P/ρ^n = cte):  Δm = ρ_s·V·[1 − (P_i/P_s)^(1/n)];  n = 1 es isotérmico.

Ciclo de carga/descarga (compresor con control carga/vacío y consumo constante):
    t_carga = Δm / (ṁ_c − ṁ_d),  t_descarga = Δm / ṁ_d,  fracción de carga = ṁ_d / ṁ_c
    frecuencia máxima (ṁ_d = ṁ_c/2):  f_max = ṁ_c / (4·Δm)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict
from typing import List, Optional

from .constantes import R_AIRE, REFERENCIAS


@dataclass
class Tramo:
    descripcion: str
    longitud_m: float
    d_interior_m: float

    @property
    def volumen_m3(self) -> float:
        return math.pi * self.d_interior_m ** 2 / 4.0 * self.longitud_m


@dataclass
class Entradas:
    v_tanque_m3: float
    p_superior_pa: float          # límite superior de la banda (absoluta)
    p_inferior_pa: float          # límite inferior admisible (absoluta)
    t_aire_k: float               # temperatura del aire dentro del sistema
    q_consumo_m3s: float          # caudal de aire libre a la referencia indicada
    ref_consumo: str = "normal"
    p_atm_sitio_pa: float = 101_325.0
    tramos: List[Tramo] = field(default_factory=list)
    incluir_tuberia: bool = True
    margen_consumo: float = 0.0   # fracción (0.10 = +10 % por fugas/crecimiento)
    q_compresor_m3s: Optional[float] = None   # FAD a la referencia ref_compresor
    ref_compresor: str = "normal"
    t_retencion_req_min: Optional[float] = None
    n_politropico: float = 1.0
    z_superior: float = 1.0
    z_inferior: float = 1.0
    nombre_caso: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        d = dict(d)
        d["tramos"] = [Tramo(**t) for t in d.get("tramos", [])]
        return cls(**d)


@dataclass
class Resultados:
    v_tuberia_m3: float
    v_sistema_m3: float
    mdot_consumo_kg_s: float
    masa_util_kg: float
    t_retencion_min: float
    v_sistema_req_m3: Optional[float] = None
    v_tanque_req_m3: Optional[float] = None
    mdot_compresor_kg_s: Optional[float] = None
    t_carga_min: Optional[float] = None
    t_descarga_min: Optional[float] = None
    fraccion_carga: Optional[float] = None
    ciclos_por_hora: Optional[float] = None
    ciclos_por_hora_max: Optional[float] = None
    t_arranque_min: Optional[float] = None
    advertencias: List[str] = field(default_factory=list)


def flujo_masico(q_ref_m3s: float, ref: str) -> float:
    """Ec. (2): caudal volumétrico de aire libre a la referencia -> kg/s."""
    c = REFERENCIAS[ref]
    return q_ref_m3s * c.presion_pa / (R_AIRE * c.temperatura_k)


def masa(p_pa: float, v_m3: float, t_k: float, z: float = 1.0) -> float:
    """Ec. (1)."""
    return p_pa * v_m3 / (z * R_AIRE * t_k)


def masa_util(v_m3, p_s, p_i, t_k, n=1.0, z_s=1.0, z_i=1.0) -> float:
    """Masa entregable al bajar de p_s a p_i. n = 1 isotérmico; n > 1 politrópico (T cae)."""
    if n == 1.0:
        return masa(p_s, v_m3, t_k, z_s) - masa(p_i, v_m3, t_k, z_i)
    rho_s = p_s / (z_s * R_AIRE * t_k)
    return rho_s * v_m3 * (1.0 - (p_i / p_s) ** (1.0 / n))


def calcular(e: Entradas) -> Resultados:
    from .validacion import validar
    advertencias = validar(e)

    v_tub = sum(t.volumen_m3 for t in e.tramos) if e.incluir_tuberia else 0.0
    v_sis = e.v_tanque_m3 + v_tub
    mdot_d = flujo_masico(e.q_consumo_m3s, e.ref_consumo) * (1.0 + e.margen_consumo)

    dm = masa_util(v_sis, e.p_superior_pa, e.p_inferior_pa, e.t_aire_k,
                   e.n_politropico, e.z_superior, e.z_inferior)
    dm_por_m3 = dm / v_sis
    r = Resultados(v_tuberia_m3=v_tub, v_sistema_m3=v_sis, mdot_consumo_kg_s=mdot_d,
                   masa_util_kg=dm, t_retencion_min=dm / mdot_d / 60.0,
                   advertencias=advertencias)

    if e.t_retencion_req_min is not None:
        r.v_sistema_req_m3 = e.t_retencion_req_min * 60.0 * mdot_d / dm_por_m3
        r.v_tanque_req_m3 = max(r.v_sistema_req_m3 - v_tub, 0.0)

    if e.q_compresor_m3s is not None:
        mdot_c = flujo_masico(e.q_compresor_m3s, e.ref_compresor)
        r.mdot_compresor_kg_s = mdot_c
        # Carga: compresión del aire en el recipiente, se toma isotérmica (n = 1)
        dm_iso = masa_util(v_sis, e.p_superior_pa, e.p_inferior_pa, e.t_aire_k, 1.0,
                           e.z_superior, e.z_inferior)
        if mdot_c > mdot_d:
            r.t_carga_min = dm_iso / (mdot_c - mdot_d) / 60.0
            r.t_descarga_min = dm_iso / mdot_d / 60.0
            r.fraccion_carga = mdot_d / mdot_c
            r.ciclos_por_hora = 60.0 / (r.t_carga_min + r.t_descarga_min)
        r.ciclos_por_hora_max = mdot_c / (4.0 * dm_iso) * 3600.0
        dm_arr = masa(e.p_superior_pa, v_sis, e.t_aire_k, e.z_superior) - masa(e.p_atm_sitio_pa, v_sis, e.t_aire_k)
        r.t_arranque_min = dm_arr / mdot_c / 60.0   # sin consumo durante el arranque
    return r


def volumen_para_frecuencia(e: Entradas, ciclos_max_h: float) -> float:
    """Volumen de sistema que limita el ciclado a ciclos_max_h en el caso más desfavorable
    (consumo = 50 % del FAD):  V = ṁ_c / (4·f·Δm/V)."""
    if e.q_compresor_m3s is None:
        raise ValueError("Se requiere el FAD del compresor")
    mdot_c = flujo_masico(e.q_compresor_m3s, e.ref_compresor)
    dm_por_m3 = masa_util(1.0, e.p_superior_pa, e.p_inferior_pa, e.t_aire_k, 1.0,
                          e.z_superior, e.z_inferior)
    return mdot_c / (4.0 * (ciclos_max_h / 3600.0) * dm_por_m3)
