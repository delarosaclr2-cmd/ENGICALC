"""Modelo de datos del proyecto y persistencia (JSON, extensión .hvac.json).

Todas las magnitudes se almacenan en SI base. El archivo conserva la versión
del formato y la versión del programa con que se calculó, para trazabilidad.
"""
from __future__ import annotations

import copy
import datetime as _dt
import json
from dataclasses import dataclass, field, asdict

from .fan_curves import FanCurve
from .hood_design import HoodEntry
from .network_solver import NetworkModel

APP_VERSION = "1.0.1"
FORMAT_VERSION = 1


def _today() -> str:
    return _dt.date.today().isoformat()


@dataclass
class ProjectInfo:
    name: str = "Proyecto sin nombre"
    client: str = ""
    location: str = ""
    engineer: str = ""
    reviewer: str = ""
    date: str = field(default_factory=_today)
    revision: str = "0"
    ventilation_type: str = "Extracción localizada industrial"
    description: str = ""
    objective: str = ""


@dataclass
class AirInput:
    mode: str = "custom"
    t_c: float = 20.0
    altitude_m: float | None = 0.0
    p_pa: float | None = None          # None → estimada por altitud
    rh: float = 0.5
    rho_measured: float | None = None  # opcional: densidad medida/declarada para verificación
    t_min_surface_c: float | None = None  # temperatura superficial mínima de ductos (riesgo de condensación)


@dataclass
class AirflowInputs:
    ach: dict = field(default_factory=lambda: {"enabled": True, "L": 30.0, "W": 20.0, "H": 8.0, "ACH": 6.0, "V": None})
    dilution: dict = field(default_factory=lambda: {"enabled": False, "G_mg_s": 10.0, "C_target": 5.0, "C_bg": 0.0,
                                                     "K": 3.0, "capture_eff": 0.0, "C0": None, "toxicity_known": False})
    thermal: dict = field(default_factory=lambda: {"enabled": False, "sources_W": [10000.0], "t_in": 25.0, "t_out": 32.0})
    occupancy: dict = field(default_factory=lambda: {"enabled": False, "Rp": 0.0, "Pz": 0.0, "Ra": 0.0, "Az": 0.0, "Ez": 1.0})
    purpose: str = "general"   # 'general' | 'contaminant_control' | 'thermal' | 'comfort'
    source_identifiable: bool = True


@dataclass
class Hood:
    id: str = "H1"
    name: str = "Campana 1"
    type: str = "exterior_flanged"
    params: dict = field(default_factory=lambda: {"W": 0.3, "H": 0.3, "X": 0.25, "Vc": 1.0})
    entry_id: str = "flanged_duct_end"
    entry: HoodEntry = field(default_factory=HoodEntry)
    contaminant_class: str = "average_industrial"
    process: str = ""
    cross_draft_m_s: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["entry"] = dict(self.entry.__dict__)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Hood":
        h = cls()
        for k, v in d.items():
            if k == "entry" and isinstance(v, dict):
                h.entry = HoodEntry(**v)
            elif hasattr(h, k):
                setattr(h, k, v)
        return h


@dataclass
class NetworkSettings:
    contaminant_class: str = "average_industrial"
    strategy: str = "acgih"          # 'acgih' | 'dampers' | 'none'
    filter_state_design: str = "sucio"
    roof_height_m: float | None = None


@dataclass
class FanSelection:
    selected_id: str | None = None
    rpm: float | None = None          # None → rpm del catálogo
    diameter_m: float | None = None   # None → diámetro del catálogo
    use_operating_solution: bool = True


@dataclass
class PowerInputs:
    eta_fan_user: float = 0.65
    eta_basis: str = "total"
    drive_type: str = "Bandas"
    eta_drive: float = 0.95
    eta_motor: float = 0.92
    use_vfd: bool = False
    eta_vfd: float = 0.97
    margin: float = 0.10
    service_factor: float = 1.15
    motor_standard: str = "IEC"
    motor_selected_kw: float | None = None
    hours_per_year: float = 4000.0
    tariff: float = 2.5
    currency: str = "MXN"
    profile: list = field(default_factory=lambda: [[1.0, 0.5], [0.8, 0.3], [0.6, 0.2]])


@dataclass
class DuctTool:
    method: str = "velocity"   # 'velocity' | 'friction' | 'regain'
    Q: float = 1.0
    V_target: float = 18.0
    dp_per_m: float = 4.0
    shape: str = "circular"
    aspect: float = 2.0
    material_id: str = "galv_ashrae"
    rounding: str = "down"
    length: float = 10.0
    regain_R: float = 0.75
    regain_sections: list = field(default_factory=lambda: [[0.8, 6.0, 0.3], [0.6, 6.0, 0.3], [0.4, 6.0, 0.3]])


@dataclass
class Alternative:
    name: str
    project: dict
    complexity: int = 3          # 1 (simple) … 5 (compleja)
    maintenance: int = 3         # 1 (fácil) … 5 (difícil)
    capex_index: float | None = None
    notes: str = ""


@dataclass
class Project:
    info: ProjectInfo = field(default_factory=ProjectInfo)
    units: str = "SI"
    air: AirInput = field(default_factory=AirInput)
    airflow: AirflowInputs = field(default_factory=AirflowInputs)
    hoods: list[Hood] = field(default_factory=list)
    network: NetworkModel = field(default_factory=NetworkModel)
    network_settings: NetworkSettings = field(default_factory=NetworkSettings)
    fans: list[FanCurve] = field(default_factory=list)
    fan_selection: FanSelection = field(default_factory=FanSelection)
    power: PowerInputs = field(default_factory=PowerInputs)
    duct_tool: DuctTool = field(default_factory=DuctTool)
    alternatives: list[Alternative] = field(default_factory=list)
    notes: str = ""

    # --- serialización ---
    def to_dict(self, include_alternatives: bool = True) -> dict:
        return {
            "format_version": FORMAT_VERSION,
            "app_version": APP_VERSION,
            "saved": _dt.datetime.now().isoformat(timespec="seconds"),
            "info": asdict(self.info),
            "units": self.units,
            "air": asdict(self.air),
            "airflow": asdict(self.airflow),
            "hoods": [h.to_dict() for h in self.hoods],
            "network": self.network.to_dict(),
            "network_settings": asdict(self.network_settings),
            "fans": [f.to_dict() for f in self.fans],
            "fan_selection": asdict(self.fan_selection),
            "power": asdict(self.power),
            "duct_tool": asdict(self.duct_tool),
            "alternatives": [asdict(a) for a in self.alternatives] if include_alternatives else [],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        p = cls()
        p.info = _fill(ProjectInfo(), d.get("info", {}))
        p.units = d.get("units", "SI")
        p.air = _fill(AirInput(), d.get("air", {}))
        p.airflow = _fill(AirflowInputs(), d.get("airflow", {}))
        p.hoods = [Hood.from_dict(h) for h in d.get("hoods", [])]
        p.network = NetworkModel.from_dict(d.get("network", {}))
        p.network_settings = _fill(NetworkSettings(), d.get("network_settings", {}))
        p.fans = [FanCurve.from_dict(f) for f in d.get("fans", [])]
        p.fan_selection = _fill(FanSelection(), d.get("fan_selection", {}))
        p.power = _fill(PowerInputs(), d.get("power", {}))
        p.duct_tool = _fill(DuctTool(), d.get("duct_tool", {}))
        p.alternatives = [Alternative(**a) for a in d.get("alternatives", [])]
        p.notes = d.get("notes", "")
        return p

    def clone(self) -> "Project":
        return Project.from_dict(copy.deepcopy(self.to_dict()))

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str) -> "Project":
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh))

    def hood(self, hid: str) -> Hood | None:
        return next((h for h in self.hoods if h.id == hid), None)

    def fan(self, fid: str | None) -> FanCurve | None:
        return next((f for f in self.fans if f.id == fid), None)


def _fill(obj, d: dict):
    for k, v in (d or {}).items():
        if hasattr(obj, k):
            setattr(obj, k, v)
    return obj
