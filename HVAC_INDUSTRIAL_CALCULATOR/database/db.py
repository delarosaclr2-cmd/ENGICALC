"""Acceso a la base de datos técnica editable (archivos JSON).

Los archivos de fábrica están en ``database/defaults``. Las ediciones del usuario
se guardan en la carpeta de datos del usuario y prevalecen sobre las de fábrica;
"Restaurar" vuelve a los valores originales.
"""
from __future__ import annotations

import json
import os
import shutil

from config.settings import app_root, user_data_dir
from core.fittings import FittingDef

DB_FILES = ["materials.json", "fittings.json", "hood_entries.json", "transport_velocities.json",
            "capture_velocities.json", "motors.json", "commercial_diameters.json", "references.json"]


def _default_dir() -> str:
    return os.path.join(app_root(), "database", "defaults")


def _user_dir() -> str:
    d = os.path.join(user_data_dir(), "database")
    os.makedirs(d, exist_ok=True)
    return d


class TechDB:
    def __init__(self, data: dict[str, dict]):
        self.data = data

    # --- consultas ---
    @property
    def materials(self) -> list[dict]:
        return self.data["materials.json"]["materials"]

    def roughness_lib(self) -> dict[str, float]:
        return {m["id"]: float(m["roughness_mm"]) / 1000.0 for m in self.materials if m.get("roughness_mm") is not None}

    def material(self, mid: str) -> dict | None:
        return next((m for m in self.materials if m["id"] == mid), None)

    @property
    def fittings(self) -> list[dict]:
        return self.data["fittings.json"]["fittings"]

    def fittings_lib(self) -> dict[str, FittingDef]:
        return {f["id"]: FittingDef.from_dict(f) for f in self.fittings}

    @property
    def hood_entries(self) -> list[dict]:
        return self.data["hood_entries.json"]["entries"]

    @property
    def transport_classes(self) -> list[dict]:
        return self.data["transport_velocities.json"]["classes"]

    def transport_class(self, cid: str | None) -> dict | None:
        return next((c for c in self.transport_classes if c["id"] == cid), None)

    @property
    def capture_ranges(self) -> list[dict]:
        return self.data["capture_velocities.json"]["ranges"]

    def motor_ratings_kw(self, standard: str = "IEC") -> list[float]:
        m = self.data["motors.json"]
        if standard == "NEMA":
            return [round(hp * 0.745699872, 4) for hp in m["NEMA_hp"]]
        return list(m["IEC_kW"])

    def diameter_series_mm(self, system: str = "SI") -> list[float]:
        c = self.data["commercial_diameters.json"]
        if system == "IP":
            return [x * 25.4 for x in c["imperial_in"]]
        return list(c["metric_mm"])

    @property
    def references(self) -> list[dict]:
        return self.data["references.json"]["references"]

    # --- persistencia ---
    def save(self, name: str) -> str:
        p = os.path.join(_user_dir(), name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(self.data[name], fh, ensure_ascii=False, indent=2)
        return p


def load_db() -> TechDB:
    data: dict[str, dict] = {}
    for name in DB_FILES:
        user = os.path.join(_user_dir(), name)
        path = user if os.path.exists(user) else os.path.join(_default_dir(), name)
        try:
            with open(path, encoding="utf-8") as fh:
                data[name] = json.load(fh)
        except (OSError, json.JSONDecodeError):
            with open(os.path.join(_default_dir(), name), encoding="utf-8") as fh:
                data[name] = json.load(fh)
    return TechDB(data)


def restore_defaults(name: str | None = None) -> TechDB:
    names = [name] if name else DB_FILES
    for nm in names:
        user = os.path.join(_user_dir(), nm)
        if os.path.exists(user):
            os.remove(user)
    return load_db()


def export_defaults_copy(dest_dir: str) -> None:
    for nm in DB_FILES:
        shutil.copyfile(os.path.join(_default_dir(), nm), os.path.join(dest_dir, nm))
