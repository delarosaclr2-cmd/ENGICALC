"""Constantes físicas, condiciones de referencia y tabla de diámetros interiores.

Todas las magnitudes internas del motor están en SI: Pa (absoluta), K, m3, kg, s.
"""
from dataclasses import dataclass

R_AIRE = 287.05            # J/(kg·K), aire seco
P_ATM_ESTANDAR = 101_325.0  # Pa (1 atm)


@dataclass(frozen=True)
class CondicionReferencia:
    """Condición de referencia a la que se expresa un caudal volumétrico de aire libre."""
    clave: str
    nombre: str
    presion_pa: float
    temperatura_k: float
    fuente: str


REFERENCIAS = {
    "normal": CondicionReferencia(
        "normal", "Normal: 0 °C y 101.325 kPa (Nm³)", 101_325.0, 273.15,
        "DIN 1343; Menon (2005), ej. 5.4"),
    "estandar_60F": CondicionReferencia(
        "estandar_60F", "Estándar: 60 °F (15.56 °C) y 14.696 psia (Sm³, SCF)", 101_325.0, 288.7056,
        "Menon (2005), ec. 5.10; convención de las memorias PCGV (14.7 psi y 15.6 °C)"),
    "estandar_20C": CondicionReferencia(
        "estandar_20C", "20 °C y 100 kPa", 100_000.0, 293.15,
        "Referencia usada por varios fabricantes para FAD; confirmar con la hoja de datos"),
}

# Diámetros exteriores y espesores (in) de ASME B36.10M, cédulas 40 y 80.
# Verificar contra la edición vigente de la norma antes de emitir.
_TUBO_ACERO = {
    # NPS: (OD, t_sch40, t_sch80)
    "1/2": (0.840, 0.109, 0.147),
    "3/4": (1.050, 0.113, 0.154),
    "1": (1.315, 0.133, 0.179),
    "1-1/4": (1.660, 0.140, 0.191),
    "1-1/2": (1.900, 0.145, 0.200),
    "2": (2.375, 0.154, 0.218),
    "2-1/2": (2.875, 0.203, 0.276),
    "3": (3.500, 0.216, 0.300),
    "4": (4.500, 0.237, 0.337),
    "6": (6.625, 0.280, 0.432),
    "8": (8.625, 0.322, 0.500),
    "10": (10.750, 0.365, 0.594),
    "12": (12.750, 0.406, 0.688),
}

PULGADA = 0.0254


def diametro_interior_m(nps: str, cedula: str) -> float:
    """Diámetro interior en metros para un NPS y cédula ('40' u '80')."""
    try:
        od, t40, t80 = _TUBO_ACERO[nps]
    except KeyError as exc:
        raise KeyError(f"NPS {nps!r} no está en la tabla; capture el diámetro interior directamente") from exc
    espesor = {"40": t40, "80": t80}.get(str(cedula))
    if espesor is None:
        raise KeyError(f"Cédula {cedula!r} no disponible; use '40', '80' o capture el diámetro interior")
    return (od - 2 * espesor) * PULGADA


def od_in(nps: str) -> float:
    """Diámetro exterior en pulgadas (ASME B36.10M)."""
    try:
        return _TUBO_ACERO[nps][0]
    except KeyError as exc:
        raise KeyError(f"NPS {nps!r} no está en la tabla") from exc


def espesor_nominal_in(nps: str, cedula: str) -> float:
    """Espesor nominal en pulgadas (ASME B36.10M)."""
    try:
        _, t40, t80 = _TUBO_ACERO[nps]
    except KeyError as exc:
        raise KeyError(f"NPS {nps!r} no está en la tabla") from exc
    t = {"40": t40, "80": t80}.get(str(cedula))
    if t is None:
        raise KeyError(f"Cédula {cedula!r} no disponible; use '40' u '80'")
    return t


def nps_disponibles():
    return list(_TUBO_ACERO.keys())
