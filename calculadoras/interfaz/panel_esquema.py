"""Pestaña «Esquema» de la ventana de calculadora: dibujo ajustable que se redibuja con los datos.

- Se redibuja medio segundo después de cada cambio en el formulario (si los datos son válidos) y al
  presionar Calcular. Con datos incompletos conserva el último dibujo válido y lo indica.
- La barra de herramientas de matplotlib permite acercar, desplazar, restablecer y guardar la imagen.
- Si matplotlib no está instalado, la pestaña lo indica; el resto de la calculadora funciona igual.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import esquemas
from ..nucleo.modelo import ErrorEntrada

RETARDO_MS = 500


class PanelEsquema(ttk.Frame):
    def __init__(self, cuaderno: ttk.Notebook, ventana) -> None:
        super().__init__(cuaderno)
        self.cuaderno = cuaderno
        self.ventana = ventana
        self.figura = None
        self.lienzo = None
        self.sucio = True
        self.dibujado = False
        self._pendiente = None
        self.estado = ttk.Label(self, text="El esquema se dibuja con los datos capturados.", anchor="w",
                                foreground="#455A64", wraplength=700)
        self.estado.pack(fill="x", padx=4, pady=(4, 2))

    # ------------------------------------------------------------------ lienzo
    def _crear_lienzo(self) -> bool:
        if self.lienzo is not None:
            return True
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            from matplotlib.figure import Figure
        except ImportError:
            self._estado("Instale matplotlib (INSTALAR.bat) para ver el esquema. El cálculo no se afecta.", "#B71C1C")
            return False
        self.figura = Figure(figsize=esquemas.TAMANO, dpi=90)
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        barra = NavigationToolbar2Tk(self.lienzo, self, pack_toolbar=False)
        barra.update()
        barra.pack(side="bottom", fill="x")
        self.lienzo.get_tk_widget().pack(side="top", fill="both", expand=True)
        return True

    def _estado(self, texto: str, color: str = "#455A64") -> None:
        self.estado.configure(text=texto, foreground=color)

    # ------------------------------------------------------------------ control
    def visible(self) -> bool:
        try:
            return self.cuaderno.select() == str(self)
        except tk.TclError:
            return False

    def programar(self) -> None:
        """Los datos cambiaron: redibuja en breve si la pestaña está a la vista."""
        self.sucio = True
        if self._pendiente is not None:
            self.after_cancel(self._pendiente)
            self._pendiente = None
        if self.visible():
            self._pendiente = self.after(RETARDO_MS, self.actualizar)

    def al_mostrar(self) -> None:
        if self.visible() and self.sucio:
            self.actualizar()

    def actualizar(self, datos: dict | None = None, resultado=None) -> bool:
        """Redibuja el esquema. Sin datos, valida y calcula en silencio con lo capturado."""
        self._pendiente = None
        if datos is None:
            try:
                datos = self.ventana.calc.validar(self.ventana.capturado())
                resultado = self.ventana.calc.calcular(datos)
            except ErrorEntrada:
                self._estado("Datos incompletos o no válidos: el esquema muestra los últimos datos válidos."
                             if self.dibujado else "Capture los datos obligatorios para ver el esquema.", "#B26A00")
                return False
        if not self._crear_lienzo():
            return False
        try:
            esquemas.dibujar(self.figura, self.ventana.calc.id, datos, resultado)
        except Exception as e:  # el dibujo nunca debe interrumpir el uso de la calculadora
            self._estado(f"No se pudo dibujar el esquema con estos datos ({e.__class__.__name__}: {e}).", "#B71C1C")
            return False
        self.lienzo.draw_idle()
        self.sucio = False
        self.dibujado = True
        vigente = self.ventana.ultimo is not None and self.ventana.ultimo[0] == self.ventana.capturado()
        self._estado("Esquema con los datos actuales" + (" (coinciden con la tabla de resultados)." if vigente else
                     ". Presione Calcular para actualizar la tabla de resultados.")
                     + " Use la barra inferior para acercar, desplazar o guardar la imagen.")
        return True
