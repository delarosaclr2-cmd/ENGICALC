"""Gestión de unidades SI / IP.

Convención interna del programa: **todos los motores de cálculo trabajan en SI
base** (m, m², m³/s, m/s, Pa, K o °C según se indique, W, kg/m³, Pa·s).
La interfaz y los reportes convierten con este módulo.

Cada unidad se define como ``SI = valor·factor + offset``.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import constants as C


@dataclass(frozen=True)
class UnitDef:
    symbol: str
    factor: float       # multiplicador hacia la unidad SI base de la magnitud
    offset: float = 0.0  # desplazamiento (solo temperaturas absolutas)


# Unidad SI base de cada magnitud (la que usan los motores de cálculo)
BASE_UNITS = {
    "length": "m",
    "small_length": "m",
    "roughness": "m",
    "area": "m²",
    "volume": "m³",
    "flow": "m³/s",
    "velocity": "m/s",
    "pressure": "Pa",
    "temperature": "°C",
    "temperature_diff": "K",
    "power": "W",
    "heat": "W",
    "density": "kg/m³",
    "dyn_viscosity": "Pa·s",
    "kin_viscosity": "m²/s",
    "mass_flow": "kg/s",
    "enthalpy": "kJ/kg",
    "humidity_ratio": "kg/kg",
    "spec_volume": "m³/kg",
    "cp": "kJ/(kg·K)",
    "friction_rate": "Pa/m",
    "concentration": "mg/m³",
    "gen_rate": "mg/s",
    "energy": "kWh",
    "speed": "rpm",
    "dimensionless": "-",
    "percent": "%",
    "time": "h",
    "money": "$",
}

_U = UnitDef
UNITS: dict[str, dict[str, UnitDef]] = {
    "length": {"m": _U("m", 1.0), "mm": _U("mm", 1e-3), "ft": _U("ft", C.FT), "in": _U("in", C.INCH)},
    "small_length": {"m": _U("m", 1.0), "mm": _U("mm", 1e-3), "in": _U("in", C.INCH), "ft": _U("ft", C.FT)},
    "roughness": {"m": _U("m", 1.0), "mm": _U("mm", 1e-3), "ft": _U("ft", C.FT), "in": _U("in", C.INCH)},
    "area": {"m²": _U("m²", 1.0), "ft²": _U("ft²", C.FT ** 2), "mm²": _U("mm²", 1e-6), "in²": _U("in²", C.INCH ** 2)},
    "volume": {"m³": _U("m³", 1.0), "ft³": _U("ft³", C.FT ** 3)},
    "flow": {
        "m³/s": _U("m³/s", 1.0),
        "m³/h": _U("m³/h", 1.0 / 3600.0),
        "L/s": _U("L/s", 1e-3),
        "cfm": _U("cfm", C.CFM),
    },
    "velocity": {"m/s": _U("m/s", 1.0), "fpm": _U("fpm", C.FPM), "ft/s": _U("ft/s", C.FT)},
    "pressure": {
        "Pa": _U("Pa", 1.0),
        "kPa": _U("kPa", 1e3),
        "in.wg": _U("in.wg", C.IN_WG_60F),
        "mmH2O": _U("mmH2O", C.MM_H2O),
        "psi": _U("psi", C.PSI),
        "inHg": _U("inHg", C.IN_HG_32F),
    },
    "temperature": {
        "°C": _U("°C", 1.0, 0.0),
        "K": _U("K", 1.0, -C.T_ZERO_K),
        "°F": _U("°F", 1.0 / 1.8, -32.0 / 1.8),
        "°R": _U("°R", 1.0 / 1.8, -C.T_ZERO_K),
    },
    "temperature_diff": {"K": _U("K", 1.0), "°C": _U("°C", 1.0), "°F": _U("°F", 1.0 / 1.8), "°R": _U("°R", 1.0 / 1.8)},
    "power": {"W": _U("W", 1.0), "kW": _U("kW", 1e3), "hp": _U("hp", C.HP)},
    "heat": {"W": _U("W", 1.0), "kW": _U("kW", 1e3), "Btu/h": _U("Btu/h", C.BTU / 3600.0)},
    "density": {"kg/m³": _U("kg/m³", 1.0), "lb/ft³": _U("lb/ft³", C.LBM / C.FT ** 3)},
    "dyn_viscosity": {"Pa·s": _U("Pa·s", 1.0), "lb/(ft·s)": _U("lb/(ft·s)", C.LBM / C.FT)},
    "kin_viscosity": {"m²/s": _U("m²/s", 1.0), "ft²/s": _U("ft²/s", C.FT ** 2)},
    "mass_flow": {"kg/s": _U("kg/s", 1.0), "kg/h": _U("kg/h", 1 / 3600.0), "lb/min": _U("lb/min", C.LBM / 60.0)},
    "enthalpy": {"kJ/kg": _U("kJ/kg", 1.0), "Btu/lb": _U("Btu/lb", C.BTU / 1000.0 / C.LBM)},
    "humidity_ratio": {"kg/kg": _U("kg/kg", 1.0), "g/kg": _U("g/kg", 1e-3), "gr/lb": _U("gr/lb", 1.0 / 7000.0)},
    "spec_volume": {"m³/kg": _U("m³/kg", 1.0), "ft³/lb": _U("ft³/lb", C.FT ** 3 / C.LBM)},
    "cp": {"kJ/(kg·K)": _U("kJ/(kg·K)", 1.0), "Btu/(lb·°F)": _U("Btu/(lb·°F)", C.BTU / 1000.0 / C.LBM * 1.8)},
    "friction_rate": {"Pa/m": _U("Pa/m", 1.0), "in.wg/100ft": _U("in.wg/100ft", C.IN_WG_60F / (100 * C.FT))},
    "concentration": {"mg/m³": _U("mg/m³", 1.0)},
    "gen_rate": {"mg/s": _U("mg/s", 1.0), "g/h": _U("g/h", 1000.0 / 3600.0), "lb/h": _U("lb/h", C.LBM * 1e6 / 3600.0)},
    "energy": {"kWh": _U("kWh", 1.0), "MWh": _U("MWh", 1000.0)},
    "speed": {"rpm": _U("rpm", 1.0)},
    "dimensionless": {"-": _U("-", 1.0)},
    "percent": {"%": _U("%", 1.0)},
    "time": {"h": _U("h", 1.0), "s": _U("s", 1 / 3600.0), "min": _U("min", 1 / 60.0)},
    "money": {"$": _U("$", 1.0)},
}

# Unidad de presentación por defecto para cada sistema
DISPLAY_UNITS = {
    "SI": {
        "length": "m", "small_length": "mm", "roughness": "mm", "area": "m²", "volume": "m³",
        "flow": "m³/h", "velocity": "m/s", "pressure": "Pa", "temperature": "°C",
        "temperature_diff": "K", "power": "kW", "heat": "kW", "density": "kg/m³",
        "dyn_viscosity": "Pa·s", "kin_viscosity": "m²/s", "mass_flow": "kg/s", "enthalpy": "kJ/kg",
        "humidity_ratio": "g/kg", "spec_volume": "m³/kg", "cp": "kJ/(kg·K)", "friction_rate": "Pa/m",
        "concentration": "mg/m³", "gen_rate": "mg/s", "energy": "kWh", "speed": "rpm",
        "dimensionless": "-", "percent": "%", "time": "h", "money": "$",
    },
    "IP": {
        "length": "ft", "small_length": "in", "roughness": "ft", "area": "ft²", "volume": "ft³",
        "flow": "cfm", "velocity": "fpm", "pressure": "in.wg", "temperature": "°F",
        "temperature_diff": "°F", "power": "hp", "heat": "Btu/h", "density": "lb/ft³",
        "dyn_viscosity": "lb/(ft·s)", "kin_viscosity": "ft²/s", "mass_flow": "lb/min", "enthalpy": "Btu/lb",
        "humidity_ratio": "gr/lb", "spec_volume": "ft³/lb", "cp": "Btu/(lb·°F)",
        "friction_rate": "in.wg/100ft", "concentration": "mg/m³", "gen_rate": "lb/h", "energy": "kWh",
        "speed": "rpm", "dimensionless": "-", "percent": "%", "time": "h", "money": "$",
    },
}


class UnitError(ValueError):
    """Unidad no reconocida para la magnitud indicada."""


def _get(quantity: str, unit: str) -> UnitDef:
    try:
        return UNITS[quantity][unit]
    except KeyError as exc:
        raise UnitError(f"Unidad '{unit}' no definida para la magnitud '{quantity}'") from exc


def to_si(value: float, quantity: str, unit: str) -> float:
    """Convierte ``value`` expresado en ``unit`` a la unidad SI base de ``quantity``."""
    u = _get(quantity, unit)
    return value * u.factor + u.offset


def from_si(value: float, quantity: str, unit: str) -> float:
    """Convierte un valor SI base de ``quantity`` a ``unit``."""
    u = _get(quantity, unit)
    return (value - u.offset) / u.factor


def convert(value: float, quantity: str, unit_from: str, unit_to: str) -> float:
    return from_si(to_si(value, quantity, unit_from), quantity, unit_to)


def display_unit(quantity: str, system: str = "SI") -> str:
    return DISPLAY_UNITS.get(system, DISPLAY_UNITS["SI"]).get(quantity, BASE_UNITS.get(quantity, ""))


def to_display(value_si: float | None, quantity: str, system: str = "SI") -> float | None:
    if value_si is None:
        return None
    return from_si(value_si, quantity, display_unit(quantity, system))


def from_display(value: float | None, quantity: str, system: str = "SI") -> float | None:
    if value is None:
        return None
    return to_si(value, quantity, display_unit(quantity, system))


def fmt(value_si: float | None, quantity: str, system: str = "SI", digits: int = 4, with_unit: bool = True) -> str:
    """Formatea un valor SI en el sistema de presentación indicado."""
    if value_si is None:
        return "—"
    try:
        v = to_display(value_si, quantity, system)
    except UnitError:
        v = value_si
    txt = format_number(v, digits)
    return f"{txt} {display_unit(quantity, system)}" if with_unit else txt


def format_number(v: float, digits: int = 4) -> str:
    """Formato de ingeniería con cifras significativas razonables."""
    if v is None:
        return "—"
    try:
        av = abs(v)
    except TypeError:
        return str(v)
    if v != v:  # NaN
        return "NaN"
    if av == 0:
        return "0"
    if av >= 1e6 or av < 1e-4:
        return f"{v:.{max(digits - 1, 1)}e}"
    if av >= 1000:
        return f"{v:,.0f}" if digits <= 4 else f"{v:,.1f}"
    # cifras significativas
    import math
    decimals = max(0, digits - 1 - int(math.floor(math.log10(av))))
    return f"{v:.{decimals}f}"
