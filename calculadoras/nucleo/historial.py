"""Datos del proyecto (encabezado de las memorias) e historial automático de cálculos.

- Los datos del proyecto (proyecto, cliente, documento, revisión, elaboró,
  revisó, aprobó) se comparten entre las calculadoras de la sesión y se guardan
  en ``registro/proyecto.json`` para la siguiente sesión.
- Cada cálculo válido se agrega a ``registro/historial.jsonl`` (una línea JSON
  por cálculo: fecha, versión, calculadora, datos del proyecto, entradas y
  resultado). El historial permite reabrir un cálculo anterior con sus datos.

Ninguna falla de escritura del historial debe impedir un cálculo: las funciones
de escritura devuelven False en lugar de lanzar excepciones.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .rutas import carpeta_datos

CAMPOS_PROYECTO = (
    ("proyecto", "Proyecto"),
    ("cliente", "Cliente"),
    ("documento", "No. de documento"),
    ("revision", "Revisión"),
    ("elaboro", "Elaboró"),
    ("reviso", "Revisó"),
    ("aprobo", "Aprobó"),
)
LIMITE_HISTORIAL = 2000  # líneas conservadas al compactar


def carpeta_registro(carpeta: os.PathLike | str | None = None) -> Path:
    """Carpeta del registro: argumento > variable de entorno CALCULADORAS_REGISTRO > <programa>/registro."""
    if carpeta:
        return Path(carpeta)
    return Path(os.environ.get("CALCULADORAS_REGISTRO") or carpeta_datos() / "registro")


def proyecto_vacio() -> dict:
    return {clave: "" for clave, _ in CAMPOS_PROYECTO}


def normalizar_proyecto(datos: dict | None) -> dict:
    limpio = proyecto_vacio()
    for clave in limpio:
        valor = (datos or {}).get(clave, "")
        limpio[clave] = str(valor).strip()[:200]
    return limpio


def cargar_proyecto(carpeta: os.PathLike | str | None = None) -> dict:
    ruta = carpeta_registro(carpeta) / "proyecto.json"
    try:
        with open(ruta, encoding="utf-8") as f:
            return normalizar_proyecto(json.load(f))
    except (OSError, ValueError):
        return proyecto_vacio()


def guardar_proyecto(datos: dict, carpeta: os.PathLike | str | None = None) -> bool:
    destino = carpeta_registro(carpeta)
    try:
        destino.mkdir(parents=True, exist_ok=True)
        with open(destino / "proyecto.json", "w", encoding="utf-8") as f:
            json.dump(normalizar_proyecto(datos), f, ensure_ascii=False, indent=2)
        return True
    except OSError:
        return False


def tiene_datos(proyecto: dict | None) -> bool:
    return any(str(v).strip() for v in (proyecto or {}).values())


def registrar(calc, entradas: dict, resultado, proyecto: dict | None = None,
              carpeta: os.PathLike | str | None = None) -> bool:
    """Agrega un cálculo al historial. Devuelve False si no se pudo escribir."""
    from .. import __version__

    linea = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "version": __version__,
        "calculadora": calc.id,
        "nombre": calc.nombre,
        "proyecto": normalizar_proyecto(proyecto),
        "entradas": {k: (v if isinstance(v, (int, float, str, bool)) or v is None else str(v))
                     for k, v in entradas.items()},
        "resultado": resultado.como_dict(),
    }
    destino = carpeta_registro(carpeta)
    try:
        destino.mkdir(parents=True, exist_ok=True)
        with open(destino / "historial.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(linea, ensure_ascii=False, default=str) + "\n")
        return True
    except (OSError, TypeError, ValueError):
        return False


def leer(limite: int = 500, carpeta: os.PathLike | str | None = None) -> list[dict]:
    """Últimos ``limite`` cálculos, del más reciente al más antiguo. Ignora líneas dañadas."""
    ruta = carpeta_registro(carpeta) / "historial.jsonl"
    try:
        with open(ruta, encoding="utf-8") as f:
            lineas = f.readlines()
    except OSError:
        return []
    registros = []
    for texto in reversed(lineas):
        try:
            dato = json.loads(texto)
        except ValueError:
            continue
        if isinstance(dato, dict) and "calculadora" in dato and "entradas" in dato:
            registros.append(dato)
        if len(registros) >= limite:
            break
    return registros


def compactar(carpeta: os.PathLike | str | None = None, conservar: int = LIMITE_HISTORIAL) -> bool:
    """Conserva solo las últimas ``conservar`` líneas del historial."""
    ruta = carpeta_registro(carpeta) / "historial.jsonl"
    try:
        with open(ruta, encoding="utf-8") as f:
            lineas = f.readlines()
        if len(lineas) <= conservar:
            return True
        with open(ruta, "w", encoding="utf-8") as f:
            f.writelines(lineas[-conservar:])
        return True
    except OSError:
        return False
