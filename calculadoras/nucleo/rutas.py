"""Recursos distribuidos y datos editables, tanto desde Python como en portable."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def empaquetado() -> bool:
    return bool(getattr(sys, "frozen", False))


def raiz_recursos() -> Path:
    if empaquetado():
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def raiz_instalacion() -> Path:
    return Path(sys.executable).resolve().parent if empaquetado() else raiz_recursos()


def carpeta_datos() -> Path:
    """No crea carpetas al importar; conserva las rutas del código fuente."""
    if not empaquetado():
        return raiz_recursos()
    instalacion = raiz_instalacion()
    if (instalacion / "portable.flag").is_file():
        return instalacion / "datos_usuario"
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return base / "RMR" / "ENGICALC"
