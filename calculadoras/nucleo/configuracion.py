"""Lectura de ``config/configuracion.json``.

El archivo es opcional: si no existe o tiene un error, se usan los valores por
defecto y la aplicación sigue funcionando.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import secrets
from pathlib import Path

from .rutas import carpeta_datos, raiz_recursos

RAIZ = raiz_recursos()
RUTA_CONFIG_DISTRIBUIDA = RAIZ / "config" / "configuracion.json"
RUTA_CONFIG = carpeta_datos() / "config" / "configuracion.json"
RUTA_RECURSOS = RAIZ / "recursos"

POR_DEFECTO = {
    "sitio": {
        "nombre": "Nivel del mar (ajustar)",
        "altitud_m": 0.0,
    },
    "acceso": {
        "requerir_contrasena": False,
        "verificar_usuario": False,
        "usuario": "usuario",
        "sal": "",
        "hash_sha256": "",
    },
    "reportes": {
        "empresa": "RMR",
        "logo": "Etiqueta RMR.png",
        "elaboro": "",
    },
}


def _fusionar(base: dict, extra: dict) -> dict:
    salida = copy.deepcopy(base)
    for k, v in (extra or {}).items():
        if isinstance(v, dict) and isinstance(salida.get(k), dict):
            salida[k] = _fusionar(salida[k], v)
        else:
            salida[k] = v
    return salida


def cargar(ruta: os.PathLike | str | None = None) -> dict:
    candidatas = [Path(ruta)] if ruta is not None else [RUTA_CONFIG, RUTA_CONFIG_DISTRIBUIDA]
    for candidata in dict.fromkeys(candidatas):
        try:
            with open(candidata, encoding="utf-8") as f:
                return _fusionar(POR_DEFECTO, json.load(f))
        except (OSError, ValueError):
            continue
    return copy.deepcopy(POR_DEFECTO)


def altitud_sitio() -> float:
    try:
        return float(cargar()["sitio"]["altitud_m"])
    except (KeyError, TypeError, ValueError):
        return 0.0


def hash_contrasena(contrasena: str, sal: str) -> str:
    return hashlib.sha256((sal + contrasena).encode("utf-8")).hexdigest()


def verificar_contrasena(usuario: str, contrasena: str, config: dict | None = None) -> bool:
    acceso = (config or cargar())["acceso"]
    if not acceso.get("requerir_contrasena"):
        return True
    if acceso.get("verificar_usuario") and usuario.strip() != str(acceso.get("usuario", "")):
        return False
    return hmac.compare_digest(hash_contrasena(contrasena, acceso.get("sal", "")),
                               str(acceso.get("hash_sha256", "")))


def establecer_contrasena(nueva: str, ruta: os.PathLike | str | None = None,
                          requerir: bool = True) -> None:
    """Guarda una contraseña nueva (sal aleatoria + SHA-256) en el archivo de configuración.

    Es una barrera de acceso equivalente a la del menú original, no un mecanismo de
    seguridad: quien pueda editar la carpeta del programa puede desactivarla.
    """
    if requerir and len(nueva) < 4:
        raise ValueError("La contraseña debe tener al menos 4 caracteres.")
    ruta = Path(ruta) if ruta else RUTA_CONFIG
    try:
        with open(ruta, encoding="utf-8") as f:
            actual = json.load(f)
    except (OSError, ValueError):
        actual = cargar() if ruta == RUTA_CONFIG else {}
    config = _fusionar(POR_DEFECTO, actual)
    sal = secrets.token_hex(8)
    config["acceso"].update({"requerir_contrasena": requerir, "sal": sal,
                             "hash_sha256": hash_contrasena(nueva, sal) if requerir else ""})
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def recurso(nombre: str) -> Path:
    return RUTA_RECURSOS / nombre
