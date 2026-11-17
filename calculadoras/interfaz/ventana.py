"""Ventana genérica de calculadora construida a partir de la especificación ``Calculadora``.

- Formulario agrupado, con unidades visibles y ayuda por campo.
- Resultados de solo lectura con su nivel de confianza (V, E, O, D).
- Advertencias, ecuaciones y notas en un panel aparte.
- Guardar/abrir caso (JSON), exportar PDF y Excel, copiar como texto, gráficas e imágenes de referencia.
- Pestaña «Esquema» (todas menos la bomba): dibujo ajustable que se redibuja con los datos.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .. import esquemas
from ..nucleo import historial
from ..nucleo.configuracion import recurso
from ..nucleo.modelo import NIVELES, Calculadora, ErrorEntrada, Resultado
from . import reportes
from .panel_esquema import PanelEsquema

_PROYECTO: dict | None = None  # datos del proyecto compartidos por todas las ventanas de la sesión


def proyecto_actual() -> dict:
    """Datos del proyecto de la sesión (se cargan una vez de registro/proyecto.json)."""
    global _PROYECTO
    if _PROYECTO is None:
        _PROYECTO = historial.cargar_proyecto()
    return _PROYECTO


def establecer_proyecto(datos: dict, guardar: bool = True) -> dict:
    global _PROYECTO
    _PROYECTO = historial.normalizar_proyecto(datos)
    if guardar:
        historial.guardar_proyecto(_PROYECTO)
    return _PROYECTO

COLOR_NIVEL = {"V": "#1B5E20", "E": "#0D47A1", "O": "#B26A00", "D": "#455A64"}


class VentanaCalculadora(tk.Toplevel):
    def __init__(self, padre: tk.Misc, calc: Calculadora):
        super().__init__(padre)
        self.calc = calc
        self.title(f"{calc.nombre} — Calculadoras de Ingeniería")
        ancho = min(1280, self.winfo_screenwidth() - 40)
        alto = min(780, self.winfo_screenheight() - 90)
        self.geometry(f"{ancho}x{alto}+20+10")
        self.minsize(900, 520)
        self.variables: dict[str, tk.StringVar] = {}
        self.ultimo: tuple[dict, dict, Resultado] | None = None  # (texto capturado, datos validados, resultado)
        self._construir()
        self.restaurar_defectos()

    # ------------------------------------------------------------------ UI
    def _construir(self) -> None:
        cabecera = ttk.Frame(self, padding=(10, 8))
        cabecera.pack(fill="x")
        ttk.Label(cabecera, text=self.calc.nombre, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(cabecera, text=f"{self.calc.disciplina} · {self.calc.descripcion}", wraplength=1100).pack(anchor="w")
        ttk.Label(cabecera, text=f"Estado: {self.calc.estado_auditoria} — {self.calc.estado_validacion}",
                  foreground="#555555").pack(anchor="w")

        barra = ttk.Frame(self, padding=(10, 0))
        barra.pack(fill="x")
        botones = [("Calcular", self.calcular), ("Valores por defecto", self.restaurar_defectos),
                   ("Abrir caso…", self.abrir_caso), ("Guardar caso…", self.guardar_caso),
                   ("Exportar PDF…", self.exportar_pdf), ("Exportar Excel…", self.exportar_excel),
                   ("Copiar resultados", self.copiar_resultados), ("Datos del proyecto…", self.editar_proyecto),
                   ("Información técnica", self.info)]
        if self.calc.graficar:
            botones.insert(1, ("Gráfica", self.mostrar_grafica))
        self.botones = {}
        for texto, accion in botones:
            b = ttk.Button(barra, text=texto, command=accion)
            b.pack(side="left", padx=2, pady=4)
            self.botones[texto] = b
        if self.calc.imagenes:
            boton = ttk.Menubutton(barra, text="Imágenes ▾")
            menu = tk.Menu(boton, tearoff=0)
            for imagen in self.calc.imagenes:
                menu.add_command(label=imagen.rsplit(".", 1)[0], command=lambda i=imagen: self.ver_imagen(i))
            boton["menu"] = menu
            boton.pack(side="left", padx=2, pady=4)

        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=10, pady=6)

        # --- formulario con desplazamiento
        izq = ttk.Frame(cuerpo, width=500)
        cuerpo.add(izq, weight=0)
        self.ayuda = ttk.Label(izq, text="Seleccione un campo para ver su ayuda.", wraplength=480,
                               foreground="#0D47A1")
        self.ayuda.pack(side="bottom", fill="x", pady=4)
        barra_v = ttk.Scrollbar(izq, orient="vertical")
        barra_v.pack(side="right", fill="y")
        lienzo = tk.Canvas(izq, highlightthickness=0, width=480, yscrollcommand=barra_v.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra_v.configure(command=lienzo.yview)
        self.formulario = ttk.Frame(lienzo)
        ventana_form = lienzo.create_window((0, 0), window=self.formulario, anchor="nw")
        self.formulario.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        # el formulario toma exactamente el ancho visible: nada queda oculto a la derecha
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana_form, width=e.width))
        self._lienzo = lienzo
        # La rueda del ratón desplaza el formulario solo mientras el puntero está sobre él
        lienzo.bind("<Enter>", lambda e: self._rueda(True))
        lienzo.bind("<Leave>", lambda e: self._rueda(False))

        grupos: dict[str, ttk.LabelFrame] = {}
        siguiente_fila: dict[str, int] = {}
        self.entradas_widget = {}
        for campo in self.calc.campos:
            marco = grupos.get(campo.grupo)
            if marco is None:
                marco = ttk.LabelFrame(self.formulario, text=campo.grupo, padding=6)
                marco.pack(fill="x", padx=4, pady=4)
                marco.columnconfigure(0, weight=1)
                marco.columnconfigure(2, minsize=72)  # unidades alineadas; las largas no se recortan
                grupos[campo.grupo] = marco
            fila = siguiente_fila.get(campo.grupo, 0)
            if campo.tipo == "opcion":  # las listas ocupan su propio renglón: los textos largos se leen completos
                ttk.Label(marco, text=campo.etiqueta + (" *" if campo.obligatorio else ""), wraplength=440
                          ).grid(row=fila, column=0, columnspan=3, sticky="w", padx=2, pady=(4, 0))
                var = tk.StringVar()
                w = ttk.Combobox(marco, textvariable=var, values=campo.opciones, state="readonly", width=48)
                # evita que la rueda cambie la opción elegida al desplazar el formulario
                w.bind("<MouseWheel>", self._desplazar_formulario)
                w.bind("<Button-4>", self._desplazar_formulario)
                w.bind("<Button-5>", self._desplazar_formulario)
                w.grid(row=fila + 1, column=0, columnspan=3, sticky="ew", padx=(14, 2), pady=(0, 4))
                siguiente_fila[campo.grupo] = fila + 2
            else:
                ttk.Label(marco, text=campo.etiqueta + (" *" if campo.obligatorio else ""), wraplength=235
                          ).grid(row=fila, column=0, sticky="w", padx=2, pady=2)
                var = tk.StringVar()
                w = ttk.Entry(marco, textvariable=var, width=12, justify="right")
                w.grid(row=fila, column=1, sticky="e", padx=2, pady=2)
                ttk.Label(marco, text=campo.unidad).grid(row=fila, column=2, sticky="w", padx=2)
                siguiente_fila[campo.grupo] = fila + 1
            ayuda = campo.ayuda
            rango = campo.describir_rango()
            texto_ayuda = " ".join(t for t in (ayuda, f"Rango: {rango} {campo.unidad}." if rango else "") if t)
            w.bind("<FocusIn>", lambda e, t=texto_ayuda, c=campo: self._mostrar_ayuda(c.etiqueta, t))
            self.variables[campo.clave] = var
            self.entradas_widget[campo.clave] = w
        ttk.Label(self.formulario, text="* dato obligatorio", foreground="#777777").pack(anchor="w", padx=6)

        # --- resultados (y esquema ajustable en otra pestaña)
        der = ttk.Frame(cuerpo)
        cuerpo.add(der, weight=1)
        self.pestanas = None
        self.panel_esquema = None
        if esquemas.disponible(self.calc.id):
            self.pestanas = ttk.Notebook(der)
            self.pestanas.pack(fill="both", expand=True)
            der = ttk.Frame(self.pestanas)
            self.pestanas.add(der, text="Resultados")
            self.panel_esquema = PanelEsquema(self.pestanas, self)
            self.pestanas.add(self.panel_esquema, text="Esquema")
            self.pestanas.bind("<<NotebookTabChanged>>", lambda e: self.panel_esquema.al_mostrar())
            for var in self.variables.values():
                var.trace_add("write", lambda *a: self.panel_esquema.programar())
        columnas = ("valor", "unidad", "nivel")
        self.tabla = ttk.Treeview(der, columns=columnas, show="tree headings", height=16)
        self.tabla.heading("#0", text="Resultado")
        self.tabla.heading("valor", text="Valor")
        self.tabla.heading("unidad", text="Unidad")
        self.tabla.heading("nivel", text="Nivel")
        self.tabla.column("#0", width=380, minwidth=200, stretch=True)
        self.tabla.column("valor", width=110, minwidth=80, anchor="e", stretch=False)
        self.tabla.column("unidad", width=80, minwidth=50, stretch=False)
        self.tabla.column("nivel", width=48, minwidth=40, anchor="center", stretch=False)
        for nivel, color in COLOR_NIVEL.items():
            self.tabla.tag_configure(nivel, foreground=color)
        self.tabla.pack(fill="both", expand=True)
        ttk.Label(der, text="Nivel: " + " · ".join(f"{k} = {v}" for k, v in NIVELES.items()),
                  foreground="#555555", wraplength=700).pack(anchor="w")
        self.texto = tk.Text(der, height=11, wrap="word", font=("Segoe UI", 9))
        self.texto.tag_configure("adv", foreground="#B71C1C")
        self.texto.tag_configure("tit", font=("Segoe UI", 9, "bold"))
        self.texto.pack(fill="both", expand=False, pady=(6, 0))
        self.texto.configure(state="disabled")
        self.estado = ttk.Label(self, text="Capture los datos y presione Calcular.", anchor="w", padding=(10, 2))
        self.estado.pack(fill="x", side="bottom")
        self.bind("<Return>", lambda e: self.calcular())

    def _desplazar_formulario(self, evento) -> str:
        if getattr(evento, "num", None) == 4:
            pasos = -1
        elif getattr(evento, "num", None) == 5:
            pasos = 1
        else:
            pasos = -1 if evento.delta > 0 else 1
        try:
            self._lienzo.yview_scroll(pasos, "units")
        except tk.TclError:  # la ventana ya se cerró con la rueda activa
            self._rueda(False)
        return "break"

    def _rueda(self, activa: bool) -> None:
        for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            if activa:
                self.bind_all(secuencia, self._desplazar_formulario)
            else:
                self.unbind_all(secuencia)

    def _mostrar_ayuda(self, etiqueta: str, texto: str) -> None:
        self.ayuda.configure(text=f"{etiqueta}: {texto}" if texto else etiqueta)

    # ------------------------------------------------------------ datos
    def capturado(self) -> dict:
        return {clave: var.get() for clave, var in self.variables.items()}

    def asignar(self, valores: dict) -> None:
        for clave, valor in valores.items():
            if clave in self.variables:
                self.variables[clave].set("" if valor is None else
                                          (f"{valor:.12g}" if isinstance(valor, float) else str(valor)))

    def restaurar_defectos(self) -> None:
        self.asignar({c.clave: ("" if c.defecto is None else c.defecto) for c in self.calc.campos})
        self._limpiar_resultados()

    def _limpiar_resultados(self) -> None:
        self.ultimo = None
        self.tabla.delete(*self.tabla.get_children())
        self._escribir_texto([])

    def _escribir_texto(self, bloques: list[tuple[str, str]]) -> None:
        self.texto.configure(state="normal")
        self.texto.delete("1.0", "end")
        for texto, etiqueta in bloques:
            self.texto.insert("end", texto, etiqueta)
        self.texto.configure(state="disabled")

    # ------------------------------------------------------------ acciones
    def calcular(self) -> Resultado | None:
        crudo = self.capturado()
        try:
            datos = self.calc.validar(crudo)
            resultado = self.calc.calcular(datos)
        except ErrorEntrada as e:
            self._limpiar_resultados()
            self.estado.configure(text="Datos no válidos: corrija y vuelva a calcular.")
            self.mostrar_error("Datos no válidos", "\n".join(e.errores))
            return None
        self.ultimo = (crudo, datos, resultado)
        self.historial_ok = historial.registrar(self.calc, datos, resultado, proyecto_actual())
        self.tabla.delete(*self.tabla.get_children())
        for s in resultado.salidas:
            self.tabla.insert("", "end", text=s.etiqueta, values=(s.texto_valor(), s.unidad, s.nivel),
                              tags=(s.nivel,))
        bloques = []
        if resultado.advertencias:
            bloques.append(("ADVERTENCIAS\n", "tit"))
            bloques += [(f"• {a}\n", "adv") for a in resultado.advertencias]
        if resultado.ecuaciones:
            bloques.append(("\nECUACIONES\n", "tit"))
            bloques += [(f"{e}\n", "") for e in resultado.ecuaciones]
        if resultado.notas:
            bloques.append(("\nNOTAS\n", "tit"))
            bloques += [(f"• {n}\n", "") for n in resultado.notas]
        self._escribir_texto(bloques)
        self.estado.configure(text=f"Cálculo realizado: {len(resultado.salidas)} resultados, "
                                   f"{len(resultado.advertencias)} advertencias.")
        if self.panel_esquema is not None:
            if self.panel_esquema.visible():
                self.panel_esquema.actualizar(datos, resultado)
            else:
                self.panel_esquema.sucio = True
        return resultado

    def _requerir_calculo_vigente(self) -> bool:
        if self.ultimo is None:
            self.mostrar_error("Sin cálculo", "Primero realice un cálculo.")
            return False
        if self.capturado() != self.ultimo[0]:
            self.mostrar_error("Datos modificados", "Los datos cambiaron después del último cálculo. "
                                                    "Presione Calcular para actualizar los resultados antes de exportar.")
            return False
        return True

    def guardar_caso(self) -> None:
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=".json",
                                            initialfile=f"{self.calc.id}.json",
                                            filetypes=[("Caso de cálculo", "*.json")])
        if ruta:
            resultado = self.ultimo[2] if self.ultimo and self.capturado() == self.ultimo[0] else None
            reportes.guardar_caso(ruta, self.calc, self.capturado(), resultado, proyecto_actual())
            self.estado.configure(text=f"Caso guardado en {ruta}")

    def abrir_caso(self) -> None:
        ruta = filedialog.askopenfilename(parent=self, filetypes=[("Caso de cálculo", "*.json")])
        if ruta:
            self.cargar_caso(ruta)

    def cargar_caso(self, ruta: str) -> None:
        try:
            datos = reportes.abrir_caso(ruta)
        except (OSError, ValueError) as e:
            self.mostrar_error("No se pudo abrir", str(e))
            return
        if datos["calculadora"] != self.calc.id:
            self.mostrar_error("Caso de otra calculadora",
                               f"El archivo corresponde a «{datos['calculadora']}». Ábralo desde el menú principal.")
            return
        if historial.tiene_datos(datos.get("proyecto")):
            establecer_proyecto(datos["proyecto"])
        self.restaurar_defectos()
        self.asignar(datos["entradas"])
        self.calcular()

    def exportar_pdf(self) -> None:
        if not self._requerir_calculo_vigente():
            return
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=".pdf",
                                            initialfile=f"memoria_{self.calc.id}.pdf", filetypes=[("PDF", "*.pdf")])
        if ruta:
            self.exportar_pdf_a(ruta)

    def exportar_pdf_a(self, ruta: str) -> None:
        _, datos, resultado = self.ultimo
        figura, aviso = None, ""
        if self.calc.graficar:
            try:
                figura = self.calc.graficar(datos, resultado)
            except ImportError:  # sin matplotlib la memoria se genera completa, solo sin la gráfica
                aviso = " (sin gráfica: falta matplotlib, ejecute INSTALAR.bat)"
        reportes.generar_pdf(ruta, self.calc, datos, resultado, figura, proyecto_actual())
        self.estado.configure(text=f"PDF generado: {ruta}{aviso}")

    def exportar_excel(self) -> None:
        if not self._requerir_calculo_vigente():
            return
        ruta = filedialog.asksaveasfilename(parent=self, defaultextension=".xlsx",
                                            initialfile=f"memoria_{self.calc.id}.xlsx",
                                            filetypes=[("Excel", "*.xlsx")])
        if ruta:
            self.exportar_excel_a(ruta)

    def exportar_excel_a(self, ruta: str) -> None:
        _, datos, resultado = self.ultimo
        reportes.generar_excel(ruta, self.calc, datos, resultado, proyecto_actual())
        self.estado.configure(text=f"Excel generado: {ruta}")

    def copiar_resultados(self) -> None:
        if not self._requerir_calculo_vigente():
            return
        _, datos, resultado = self.ultimo
        self.clipboard_clear()
        self.clipboard_append(reportes.texto_reporte(self.calc, datos, resultado, proyecto_actual()))
        self.estado.configure(text="Resultados copiados al portapapeles.")

    def editar_proyecto(self) -> "DialogoProyecto":
        return DialogoProyecto(self, proyecto_actual(), self._proyecto_actualizado)

    def _proyecto_actualizado(self, datos: dict) -> None:
        establecer_proyecto(datos)
        self.estado.configure(text="Datos del proyecto actualizados (se usan en PDF, Excel, casos e historial).")

    def mostrar_grafica(self) -> None:
        if not self._requerir_calculo_vigente():
            return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        _, datos, resultado = self.ultimo
        figura = self.calc.graficar(datos, resultado)
        ventana = tk.Toplevel(self)
        ventana.title(f"Gráfica — {self.calc.nombre}")
        lienzo = FigureCanvasTkAgg(figura, master=ventana)
        lienzo.draw()
        lienzo.get_tk_widget().pack(fill="both", expand=True)
        ttk.Button(ventana, text="Cerrar", command=ventana.destroy).pack(pady=4)
        return ventana

    def ver_imagen(self, nombre: str) -> None:
        ruta = recurso(nombre)
        if not ruta.is_file():
            self.mostrar_error("Imagen no encontrada", f"No existe {ruta}.")
            return
        from PIL import Image, ImageTk

        ventana = tk.Toplevel(self)
        ventana.title(nombre)
        imagen = Image.open(ruta)
        imagen.thumbnail((900, 700))
        foto = ImageTk.PhotoImage(imagen)
        etiqueta = ttk.Label(ventana, image=foto)
        etiqueta.image = foto
        etiqueta.pack(padx=8, pady=8)
        return ventana

    def info(self) -> None:
        c = self.calc
        lineas = [f"{c.nombre}", "", f"Disciplina: {c.disciplina}", f"Estado de auditoría: {c.estado_auditoria}",
                  f"Estado de validación: {c.estado_validacion}", "", "Referencias:"]
        lineas += [f"  • {r}" for r in c.referencias] + ["", "Limitaciones:"]
        lineas += [f"  • {li}" for li in c.limitaciones] + ["", "Archivos originales que sustituye:"]
        lineas += [f"  • {a}" for a in c.archivos_originales] + ["", "Niveles de confianza:"]
        lineas += [f"  {k} = {v}" for k, v in NIVELES.items()]
        messagebox.showinfo("Información técnica", "\n".join(lineas), parent=self)

    def mostrar_error(self, titulo: str, mensaje: str) -> None:
        messagebox.showerror(titulo, mensaje, parent=self)


class DialogoProyecto(tk.Toplevel):
    """Captura de los datos del proyecto que encabezan las memorias de cálculo."""

    def __init__(self, padre: tk.Misc, datos: dict, al_guardar):
        super().__init__(padre)
        self.title("Datos del proyecto")
        self.resizable(False, False)
        self.transient(padre)
        self.al_guardar = al_guardar
        marco = ttk.Frame(self, padding=12)
        marco.pack(fill="both", expand=True)
        ttk.Label(marco, text="Encabezado de las memorias de cálculo (PDF, Excel), casos guardados e historial.",
                  wraplength=420).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        self.variables: dict[str, tk.StringVar] = {}
        for fila, (clave, etiqueta) in enumerate(historial.CAMPOS_PROYECTO, start=1):
            ttk.Label(marco, text=etiqueta).grid(row=fila, column=0, sticky="w", padx=(0, 8), pady=2)
            var = tk.StringVar(value=datos.get(clave, ""))
            ttk.Entry(marco, textvariable=var, width=44).grid(row=fila, column=1, sticky="ew", pady=2)
            self.variables[clave] = var
        botones = ttk.Frame(marco)
        botones.grid(row=len(historial.CAMPOS_PROYECTO) + 1, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(botones, text="Guardar", command=self.guardar).pack(side="left", padx=2)
        ttk.Button(botones, text="Limpiar", command=self.limpiar).pack(side="left", padx=2)
        ttk.Button(botones, text="Cancelar", command=self.destroy).pack(side="left", padx=2)

    def valores(self) -> dict:
        return {clave: var.get() for clave, var in self.variables.items()}

    def limpiar(self) -> None:
        for var in self.variables.values():
            var.set("")

    def guardar(self) -> None:
        self.al_guardar(self.valores())
        self.destroy()
