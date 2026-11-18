"""Ejecución independiente de las memorias para revisión de la rama."""
from __future__ import annotations

from . import POR_ID


def abrir_memoria(raiz, identificador):
    """Construye una memoria sobre una raíz Tk existente, sin usar el menú."""
    from .ventana import VentanaMemoria

    return VentanaMemoria(raiz, POR_ID[identificador])


def iniciar(identificador: str, pedir_acceso: bool = True) -> None:
    import tkinter as tk
    from tkinter import ttk

    from ..interfaz.acceso import solicitar_acceso
    from ..interfaz.menu import _manejar_excepcion

    # Un identificador inválido no debe dejar una raíz Tk abierta.
    if identificador not in POR_ID:
        raise ValueError(f"Memoria desconocida: {identificador}")
    raiz = tk.Tk()
    raiz.withdraw()
    raiz.report_callback_exception = _manejar_excepcion(raiz)
    try:
        estilo = ttk.Style(raiz)
        estilo.theme_use("vista" if "vista" in estilo.theme_names() else "clam")
        if pedir_acceso and not solicitar_acceso(raiz):
            return
        ventana = abrir_memoria(raiz, identificador)
        ventana.protocol("WM_DELETE_WINDOW", raiz.destroy)
        raiz.mainloop()
    finally:
        try:
            raiz.destroy()
        except tk.TclError:
            pass
