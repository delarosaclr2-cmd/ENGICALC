"""Diálogo de acceso (equivalente al login del menú original, sin contraseña en texto plano)."""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..nucleo.configuracion import cargar, recurso, verificar_contrasena
from . import tema


class DialogoAcceso(tk.Toplevel):
    """Ventana modal; ``self.aceptado`` indica si la contraseña fue correcta."""

    INTENTOS = 5

    def __init__(self, padre: tk.Misc, config: dict | None = None):
        super().__init__(padre)
        tema.aplicar(self)
        self.config_app = config or cargar()
        self.aceptado = False
        self.intentos = 0
        self.title("Acceso — Calculadoras de Ingeniería RMR")
        self.resizable(False, False)
        self.configure(background=tema.SUPERFICIE)
        marco = tk.Frame(self, background=tema.SUPERFICIE, padx=24, pady=20)
        marco.pack(fill="both", expand=True)
        logo = tema.logotipo(marco, recurso(self.config_app["reportes"].get("logo", "")), 46, tema.SUPERFICIE)
        if logo is not None:
            logo.pack(pady=(0, 10))
        tema.etiqueta(marco, "Acceso — Calculadoras de Ingeniería", "subtitulo", tema.TEXTO,
                      tema.SUPERFICIE).pack(pady=(0, 14))
        tema.etiqueta(marco, "Usuario", "pequeno", tema.TEXTO, tema.SUPERFICIE).pack(anchor="w")
        self.usuario = tk.StringVar(value=self.config_app["acceso"].get("usuario", ""))
        ttk.Entry(marco, textvariable=self.usuario, width=30).pack(fill="x", pady=(4, 10))
        tema.etiqueta(marco, "Contraseña", "pequeno", tema.TEXTO, tema.SUPERFICIE).pack(anchor="w")
        self.contrasena = tk.StringVar()
        self.campo_contrasena = ttk.Entry(marco, textvariable=self.contrasena, show="•", width=30)
        self.campo_contrasena.pack(fill="x", pady=(4, 4))
        self.contrasena.trace_add("write", lambda *a: self.campo_contrasena.state(["!invalid"]))
        self.mensaje = tema.etiqueta(marco, "", "pequeno", tema.ERROR, tema.SUPERFICIE, wraplength=260)
        self.mensaje.pack(anchor="w", pady=(2, 0))
        pie = tk.Frame(self, background=tema.SUPERFICIE_2)
        pie.pack(fill="x", side="bottom")
        tema.separador(pie, "horizontal", tema.DIVISOR).pack(fill="x", side="top")
        botones = tk.Frame(pie, background=tema.SUPERFICIE_2, padx=20, pady=10)
        botones.pack(fill="x")
        ttk.Button(botones, text="Ingresar", command=self.ingresar, style="Primario.TButton").pack(side="right")
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="right", padx=(0, 8))
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
        self.campo_contrasena.state(["invalid"])
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
