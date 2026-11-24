"""Pestaña «Esquema» de la ventana de calculadora: dibujo ajustable que se redibuja con los datos.

- Se redibuja medio segundo después de cada cambio en el formulario (si los datos son válidos) y al
  presionar Calcular. Con datos incompletos conserva el último dibujo válido y lo indica.
- Barra compacta del rediseño (Restablecer vista, Acercar, Desplazar, Guardar imagen…) en lugar de
  la barra de herramientas de matplotlib; usa las mismas funciones de matplotlib por debajo.
- Si matplotlib no está instalado, la pestaña lo indica; el resto de la calculadora funciona igual.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import esquemas
from ..nucleo.modelo import ErrorEntrada
from . import tema

RETARDO_MS = 500


class PanelEsquema(tk.Frame):
    def __init__(self, cuaderno: ttk.Notebook, ventana) -> None:
        super().__init__(cuaderno, background=tema.SUPERFICIE)
        self.cuaderno = cuaderno
        self.ventana = ventana
        self.figura = None
        self.lienzo = None
        self.herramientas = None
        self.sucio = True
        self.dibujado = False
        self._pendiente = None
        cabecera = tk.Frame(self, background=tema.SUPERFICIE)
        cabecera.pack(fill="x", side="top")
        self.estado = tema.etiqueta(cabecera, "El esquema se dibuja con los datos capturados.", "pequeno",
                                    tema.TEXTO_2, tema.SUPERFICIE, wraplength=tema._px(self, 700))
        self.estado.pack(fill="x", padx=16, pady=(10, 10))
        tema.separador(cabecera, "horizontal", tema.DIVISOR_FILA).pack(fill="x")
        cabecera.bind("<Configure>", lambda e: self.estado.configure(wraplength=max(200, e.width - 40)))

    # ------------------------------------------------------------------ lienzo
    def _crear_lienzo(self) -> bool:
        if self.lienzo is not None:
            return True
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            from matplotlib.figure import Figure
        except ImportError:
            self._estado("Instale matplotlib (INSTALAR.bat) para ver el esquema. El cálculo no se afecta.", tema.ERROR)
            return False
        self.figura = Figure(figsize=esquemas.TAMANO, dpi=90, facecolor=tema.SUPERFICIE)
        self.lienzo = FigureCanvasTkAgg(self.figura, master=self)
        pie = tk.Frame(self, background=tema.SUPERFICIE_2)
        pie.pack(side="bottom", fill="x")
        tema.separador(pie, "horizontal", tema.DIVISOR).pack(fill="x", side="top")
        barra = tk.Frame(pie, background=tema.SUPERFICIE_2)
        barra.pack(fill="x", padx=12, pady=6)
        # las funciones de la barra de matplotlib, sin mostrarla
        oculto = tk.Frame(self)
        self.herramientas = NavigationToolbar2Tk(self.lienzo, oculto, pack_toolbar=False)
        self.botones_vista = {}
        for texto, accion in (("Restablecer vista", self._restablecer), ("Acercar", self._acercar),
                              ("Desplazar", self._desplazar)):
            b = ttk.Button(barra, text=texto, command=accion, style="Compacto.TButton")
            b.pack(side="left", padx=(0, 6))
            self.botones_vista[texto] = b
        ttk.Button(barra, text="Guardar imagen…", command=self.herramientas.save_figure,
                   style="Compacto.TButton").pack(side="right")
        self.lienzo.get_tk_widget().configure(background=tema.SUPERFICIE, highlightthickness=0)
        self.lienzo.get_tk_widget().pack(side="top", fill="both", expand=True, padx=8, pady=8)
        return True

    def _modo(self) -> str:
        return str(getattr(getattr(self.herramientas, "mode", ""), "name", ""))

    def _marcar_modo(self) -> None:
        modo = self._modo()
        for texto, nombre in (("Acercar", "ZOOM"), ("Desplazar", "PAN")):
            self.botones_vista[texto].configure(style="CompactoActivo.TButton" if modo == nombre
                                                else "Compacto.TButton")

    def _restablecer(self) -> None:
        self.herramientas.home()

    def _acercar(self) -> None:
        self.herramientas.zoom()
        self._marcar_modo()

    def _desplazar(self) -> None:
        self.herramientas.pan()
        self._marcar_modo()

    def _estado(self, texto: str, color: str = tema.TEXTO_2) -> None:
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
                             if self.dibujado else "Capture los datos obligatorios para ver el esquema.",
                             tema.ADVERTENCIA)
                return False
        if not self._crear_lienzo():
            return False
        try:
            esquemas.dibujar(self.figura, self.ventana.calc.id, datos, resultado)
        except Exception as e:  # el dibujo nunca debe interrumpir el uso de la calculadora
            self._estado(f"No se pudo dibujar el esquema con estos datos ({e.__class__.__name__}: {e}).", tema.ERROR)
            return False
        self.lienzo.draw_idle()
        self.herramientas.update()  # la vista «Restablecer» vuelve a este dibujo
        self.sucio = False
        self.dibujado = True
        vigente = self.ventana.ultimo is not None and self.ventana.ultimo[0] == self.ventana.capturado()
        self._estado("Esquema con los datos actuales" + (" (coinciden con la tabla de resultados)." if vigente else
                     ". Presione Calcular para actualizar la tabla de resultados.")
                     + " Use la barra inferior para acercar, desplazar o guardar la imagen.")
        return True
