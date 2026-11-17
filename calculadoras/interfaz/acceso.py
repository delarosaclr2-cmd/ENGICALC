"""Diálogo de acceso (equivalente al login del menú original, sin contraseña en texto plano)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..nucleo.configuracion import cargar, verificar_contrasena


class DialogoAcceso(tk.Toplevel):
    """Ventana modal; ``self.aceptado`` indica si la contraseña fue correcta."""

    INTENTOS = 5

    def __init__(self, padre: tk.Misc, config: dict | None = None):
        super().__init__(padre)
        self.config_app = config or cargar()
        self.aceptado = False
        self.intentos = 0
        self.title("Acceso — Calculadoras de Ingeniería RMR")
        self.resizable(False, False)
        marco = ttk.Frame(self, padding=16)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Usuario:").grid(row=0, column=0, sticky="w", pady=4)
        self.usuario = tk.StringVar(value=self.config_app["acceso"].get("usuario", ""))
        ttk.Entry(marco, textvariable=self.usuario, width=24).grid(row=0, column=1, pady=4)
        ttk.Label(marco, text="Contraseña:").grid(row=1, column=0, sticky="w", pady=4)
        self.contrasena = tk.StringVar()
        self.campo_contrasena = ttk.Entry(marco, textvariable=self.contrasena, show="*", width=24)
        self.campo_contrasena.grid(row=1, column=1, pady=4)
        self.mensaje = ttk.Label(marco, text="", foreground="#B71C1C")
        self.mensaje.grid(row=2, column=0, columnspan=2, sticky="w")
        botones = ttk.Frame(marco)
        botones.grid(row=3, column=0, columnspan=2, pady=(8, 0), sticky="e")
        ttk.Button(botones, text="Ingresar", command=self.ingresar).pack(side="left", padx=4)
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="left")
        self.bind("<Return>", lambda e: self.ingresar())
        self.bind("<Escape>", lambda e: self.destroy())
        self.campo_contrasena.focus_set()

    def ingresar(self) -> bool:
        if verificar_contrasena(self.usuario.get(), self.contrasena.get(), self.config_app):
            self.aceptado = True
            self.destroy()
            return True
        self.intentos += 1
        self.contrasena.set("")
        if self.intentos >= self.INTENTOS:
            self.destroy()
            return False
        self.mensaje.configure(text=f"Usuario o contraseña incorrectos ({self.intentos}/{self.INTENTOS}).")
        return False


def solicitar_acceso(raiz: tk.Tk, config: dict | None = None) -> bool:
    """Muestra el diálogo si la configuración lo requiere. Devuelve True si se permite el acceso."""
    config = config or cargar()
    if not config["acceso"].get("requerir_contrasena"):
        return True
    dialogo = DialogoAcceso(raiz, config)
    try:
        dialogo.wait_visibility()
        dialogo.grab_set()
    except tk.TclError:  # algunos gestores de ventanas no permiten el modo modal
        pass
    raiz.wait_window(dialogo)
    return dialogo.aceptado
