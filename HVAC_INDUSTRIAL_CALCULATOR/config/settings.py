"""Carga y guardado de la configuración (``config/settings.json``).

Los criterios de evaluación son objetos con valor, unidad, base (física,
referencia o hipótesis), fuente y nivel de alerta, para que cada alerta del
programa sea trazable a un criterio documentado.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys

def app_root() -> str:
    """Raíz de la aplicación (compatible con ejecutable PyInstaller)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def user_data_dir() -> str:
    """Carpeta de datos del usuario (configuración editada, autoguardado)."""
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    d = os.path.join(base, "HVAC_Industrial_Calculator")
    os.makedirs(d, exist_ok=True)
    return d


DEFAULT_PATH = os.path.join(app_root(), "config", "settings.default.json")
SHIPPED_PATH = os.path.join(app_root(), "config", "settings.json")


class Settings:
    def __init__(self, data: dict, path: str | None = None):
        self.data = data
        self.path = path

    # --- acceso ---
    def crit(self, key: str) -> dict:
        return self.data["criteria"][key]

    def cval(self, key: str, default=None):
        try:
            return self.data["criteria"][key]["value"]
        except KeyError:
            return default

    def solver(self, key: str, default=None):
        return self.data.get("solver", {}).get(key, default)

    def app(self, key: str, default=None):
        return self.data.get("app", {}).get(key, default)

    @property
    def weights(self) -> dict:
        return {k: v for k, v in self.data.get("comparator_weights", {}).items() if not k.startswith("_")}

    def copy(self) -> "Settings":
        return Settings(copy.deepcopy(self.data), self.path)

    # --- persistencia ---
    def save(self, path: str | None = None) -> str:
        p = path or self.path or os.path.join(user_data_dir(), "settings.json")
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(self.data, fh, ensure_ascii=False, indent=2)
        self.path = p
        return p


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_settings(path: str | None = None) -> Settings:
    """Carga la configuración del usuario combinada con la de fábrica."""
    with open(DEFAULT_PATH, encoding="utf-8") as fh:
        base = json.load(fh)
    candidates = [path] if path else [os.path.join(user_data_dir(), "settings.json"), SHIPPED_PATH]
    for c in candidates:
        if c and os.path.exists(c):
            try:
                with open(c, encoding="utf-8") as fh:
                    return Settings(_merge(base, json.load(fh)), c)
            except (OSError, json.JSONDecodeError):
                continue
    return Settings(base, None)


def restore_default_settings() -> Settings:
    user = os.path.join(user_data_dir(), "settings.json")
    shutil.copyfile(DEFAULT_PATH, user)
    return load_settings(user)
