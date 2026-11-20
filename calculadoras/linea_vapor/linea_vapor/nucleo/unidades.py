"""Conversión de unidades. El motor trabaja en SI; aquí se convierte desde/hacia unidades de usuario.

Presión: las unidades manométricas requieren la presión atmosférica del SITIO, que es distinta
de la presión de la condición de referencia del caudal (Menon 2005, ej. 5.4).
"""
PSI = 6_894.757293168   # Pa
BAR = 100_000.0
KGF_CM2 = 98_066.5
FT3 = 0.028316846592
GAL_US = 0.003785411784

_PRESION_ABS = {"Pa a": 1.0, "kPa a": 1_000.0, "bar a": BAR, "psia": PSI, "kgf/cm² a": KGF_CM2}
_PRESION_MAN = {"kPa g": 1_000.0, "bar g": BAR, "psig": PSI, "kgf/cm² g": KGF_CM2}
UNIDADES_PRESION = list(_PRESION_ABS) + list(_PRESION_MAN)


def presion_a_pa_abs(valor: float, unidad: str, p_atm_sitio_pa: float) -> float:
    if unidad in _PRESION_ABS:
        return valor * _PRESION_ABS[unidad]
    if unidad in _PRESION_MAN:
        return valor * _PRESION_MAN[unidad] + p_atm_sitio_pa
    raise ValueError(f"Unidad de presión no reconocida: {unidad}")


def pa_abs_a(valor_pa: float, unidad: str, p_atm_sitio_pa: float) -> float:
    if unidad in _PRESION_ABS:
        return valor_pa / _PRESION_ABS[unidad]
    if unidad in _PRESION_MAN:
        return (valor_pa - p_atm_sitio_pa) / _PRESION_MAN[unidad]
    raise ValueError(f"Unidad de presión no reconocida: {unidad}")


# Caudal de aire libre a condición de referencia (la referencia se elige aparte)
_CAUDAL = {"m³/h": 1 / 3600, "m³/min": 1 / 60, "m³/s": 1.0, "L/s": 1e-3, "ft³/min": FT3 / 60}
UNIDADES_CAUDAL = list(_CAUDAL)


def caudal_a_m3s(valor: float, unidad: str) -> float:
    try:
        return valor * _CAUDAL[unidad]
    except KeyError as exc:
        raise ValueError(f"Unidad de caudal no reconocida: {unidad}") from exc


def m3s_a(valor: float, unidad: str) -> float:
    return valor / _CAUDAL[unidad]


_VOLUMEN = {"m³": 1.0, "L": 1e-3, "ft³": FT3, "gal (US)": GAL_US}
UNIDADES_VOLUMEN = list(_VOLUMEN)


def volumen_a_m3(valor: float, unidad: str) -> float:
    try:
        return valor * _VOLUMEN[unidad]
    except KeyError as exc:
        raise ValueError(f"Unidad de volumen no reconocida: {unidad}") from exc


def m3_a(valor: float, unidad: str) -> float:
    return valor / _VOLUMEN[unidad]


UNIDADES_TEMPERATURA = ["°C", "°F", "K"]


def temperatura_a_k(valor: float, unidad: str) -> float:
    if unidad == "°C":
        return valor + 273.15
    if unidad == "°F":
        return (valor - 32.0) / 1.8 + 273.15
    if unidad == "K":
        return valor
    raise ValueError(f"Unidad de temperatura no reconocida: {unidad}")


def k_a(valor_k: float, unidad: str) -> float:
    if unidad == "°C":
        return valor_k - 273.15
    if unidad == "°F":
        return (valor_k - 273.15) * 1.8 + 32.0
    if unidad == "K":
        return valor_k
    raise ValueError(f"Unidad de temperatura no reconocida: {unidad}")


def min_a_texto(t_min: float) -> str:
    """10.7356 -> '10 min 44 s' (redondeo al segundo)."""
    if t_min != t_min or t_min in (float("inf"), float("-inf")):
        return "—"
    s = int(round(t_min * 60.0))
    h, s = divmod(s, 3600)
    m, s = divmod(s, 60)
    return f"{h} h {m:02d} min {s:02d} s" if h else f"{m} min {s:02d} s"


LB = 0.45359237
_MASICO = {"kg/h": 1 / 3600, "t/h": 1000 / 3600, "kg/s": 1.0, "lb/h": LB / 3600}
UNIDADES_MASICO = list(_MASICO)


def masico_a_kgs(valor: float, unidad: str) -> float:
    if unidad not in _MASICO:
        raise ValueError(f"Unidad de flujo másico no reconocida: {unidad}")
    return valor * _MASICO[unidad]


_LIQ = {"m³/h": 1 / 3600, "L/min": 1e-3 / 60, "L/s": 1e-3, "gpm (US)": GAL_US / 60, "m³/s": 1.0}
UNIDADES_CAUDAL_LIQ = list(_LIQ)


def caudal_liq_a_m3s(valor: float, unidad: str) -> float:
    if unidad not in _LIQ:
        raise ValueError(f"Unidad de caudal no reconocida: {unidad}")
    return valor * _LIQ[unidad]


def m3s_a_liq(valor: float, unidad: str) -> float:
    return valor / _LIQ[unidad]
