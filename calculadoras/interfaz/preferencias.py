"""Favoritos y herramientas recientes del menú principal (preferencias de la interfaz, no de cálculo).

Se guardan en ``registro/preferencias_menu.json`` (o en la carpeta de ``CALCULADORAS_REGISTRO``).
Como el historial, una falla de lectura o escritura nunca impide usar el menú: se ignora.
"""
from __future__ import annotations

import json

from ..nucleo.historial import carpeta_registro

ARCHIVO = "preferencias_menu.json"
MAX_RECIENTES = 5


def _ruta():
    return carpeta_registro() / ARCHIVO


def cargar() -> dict:
    try:
        with open(_ruta(), encoding="utf-8") as archivo:
            datos = json.load(archivo)
    except (OSError, ValueError):
        datos = {}
    if not isinstance(datos, dict):
        datos = {}
    favoritos = [str(x) for x in datos.get("favoritos", []) if isinstance(x, str)]
    recientes = [str(x) for x in datos.get("recientes", []) if isinstance(x, str)][:MAX_RECIENTES]
    return {"favoritos": favoritos, "recientes": recientes}


def guardar(datos: dict) -> bool:
    try:
        ruta = _ruta()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as archivo:
            json.dump({"favoritos": list(datos.get("favoritos", [])),
                       "recientes": list(datos.get("recientes", []))[:MAX_RECIENTES]},
                      archivo, ensure_ascii=False, indent=1)
        return True
    except OSError:
        return False


def alternar_favorito(datos: dict, identificador: str) -> bool:
    """Agrega o quita un favorito; devuelve True si quedó como favorito."""
    favoritos = datos.setdefault("favoritos", [])
    if identificador in favoritos:
        favoritos.remove(identificador)
        es_favorito = False
    else:
        favoritos.append(identificador)
        es_favorito = True
    guardar(datos)
    return es_favorito


def registrar_reciente(datos: dict, identificador: str) -> None:
    recientes = [x for x in datos.setdefault("recientes", []) if x != identificador]
    datos["recientes"] = [identificador, *recientes][:MAX_RECIENTES]
    guardar(datos)
