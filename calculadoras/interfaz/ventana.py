"""Ventana genérica de calculadora construida a partir de la especificación ``Calculadora``.

Arquetipo A del rediseño de interfaz (ENGICALC · sistema visual v1):

- Encabezado con logotipo y ruta «Calculadoras › Categoría › Herramienta»; título con la
  etiqueta de guardado y barra de acciones con una sola acción primaria (Calcular).
- Datos a la izquierda, en tarjetas por grupo, con la unidad visible en una pastilla junto a
  cada campo; los obligatorios pendientes se marcan en ámbar y los no válidos en rojo.
- Resultados a la derecha: KPI, panel ámbar de advertencias y pestañas Resultados · Esquema ·
  Ecuaciones y notas. Cada resultado conserva su nivel de confianza (V, E, O, D).
- Guardar/abrir caso (JSON), exportar PDF y Excel, copiar como texto, gráficas e imágenes de referencia.

El rediseño solo cambia la disposición y el estilo: etiquetas, unidades, valores, validaciones,
ecuaciones, avisos y exportaciones se generan exactamente igual que antes.
"""
from __future__ import annotations

import tkinter as tk
from functools import lru_cache
from tkinter import filedialog, messagebox, ttk

from .. import esquemas
from ..nucleo import historial
from ..nucleo.configuracion import cargar, recurso
from ..nucleo.modelo import (CORREGIDA, EN_AUDITORIA, ERROR_DETECTADO, NIVELES, NO_REVISADA, VALIDACION_PENDIENTE,
                             VALIDADA_CONDICIONES, Calculadora, ErrorEntrada, Resultado)
from . import reportes, tema
from .kpi import KPI
from .panel_esquema import PanelEsquema
from .tabla_resultados import TablaResultados, leyenda

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


def texto_proyecto() -> str:
    nombre = proyecto_actual().get("proyecto", "")
    return f"Proyecto: {nombre}" if nombre else "Proyecto: [sin datos del proyecto]"


@lru_cache(maxsize=1)
def ruta_logo():
    return recurso(cargar()["reportes"].get("logo", ""))


COLOR_NIVEL = {nivel: estilo[1] for nivel, estilo in tema.NIVEL_ESTILO.items()}
TONO_VALIDACION = {VALIDADA_CONDICIONES: "correcto", VALIDACION_PENDIENTE: "advertencia", CORREGIDA: "info",
                   EN_AUDITORIA: "info", ERROR_DETECTADO: "critico", NO_REVISADA: "nota",
                   "Revisión de código aprobada": "info", "Verificación numérica documentada": "nota"}
ESTADO_CORTO = {VALIDADA_CONDICIONES: "Validada con condiciones", VALIDACION_PENDIENTE: "Validación pendiente"}
SIMBOLO_VALIDACION = {"correcto": "●", "advertencia": "◐", "info": "◆", "nota": "≡", "critico": "✕"}


def chip_validacion(padre: tk.Misc, estado: str) -> tk.Label:
    """Insignia del estado de validación (texto corto del menú; el estado completo al pasar el cursor)."""
    tono = TONO_VALIDACION.get(estado, "nota")
    etiqueta = tema.chip(padre, f"{SIMBOLO_VALIDACION[tono]} {ESTADO_CORTO.get(estado, estado)}", tono)
    if ESTADO_CORTO.get(estado, estado) != estado:
        tema.Tooltip(etiqueta, estado)
    return etiqueta


ANCHO_DATOS = 404  # px de la maqueta (1280–1599 px: datos de 400 px)


class VentanaCalculadora(tk.Toplevel):
    def __init__(self, padre: tk.Misc, calc: Calculadora):
        super().__init__(padre)
        tema.aplicar(self)
        self.configure(background=tema.FONDO)
        self.calc = calc
        self.title(f"{calc.nombre} — Calculadoras de Ingeniería")
        ancho = min(1440, self.winfo_screenwidth() - 40)
        alto = min(900, self.winfo_screenheight() - 90)
        self.geometry(f"{ancho}x{alto}+20+10")
        # mínimo del diseño 1024 × 700, sin exceder pantallas pequeñas
        self.minsize(min(1024, self.winfo_screenwidth() - 40), min(640, self.winfo_screenheight() - 90))
        self.variables: dict[str, tk.StringVar] = {}
        self.ultimo: tuple[dict, dict, Resultado] | None = None  # (texto capturado, datos validados, resultado)
        self.historial_ok = False
        self._guardado: dict | None = None      # datos capturados la última vez que se guardó/abrió el caso
        self._refresco = None
        self._construir()
        self.restaurar_defectos()

    # ------------------------------------------------------------------ UI
    def _construir(self) -> None:
        c = self.calc
        tema.encabezado_ventana(self, ruta_logo(), ["Calculadoras", c.disciplina, c.nombre],
                                al_volver=self._ir_al_menu).pack(fill="x", side="top")
        self.estado = tema.BarraEstado(self, "Capture los datos y presione Calcular.", texto_proyecto())
        self.estado.pack(fill="x", side="bottom")
        self._construir_titulo()

        cuerpo = ttk.PanedWindow(self, orient="horizontal")
        cuerpo.pack(fill="both", expand=True, padx=tema._px(self, 24), pady=(tema._px(self, 14), tema._px(self, 16)))
        izq = tk.Frame(cuerpo, background=tema.FONDO)
        der = tk.Frame(cuerpo, background=tema.FONDO)
        cuerpo.add(izq, weight=0)
        cuerpo.add(der, weight=1)
        self._construir_formulario(izq)
        self._construir_resultados(der)
        self.bind("<Return>", lambda e: self.calcular())

    def _construir_titulo(self) -> None:
        c = self.calc
        cab = tk.Frame(self, background=tema.FONDO)
        cab.pack(fill="x", padx=tema._px(self, 24), pady=(tema._px(self, 16), 0))
        cab.columnconfigure(0, weight=1)
        self._cabecera = cab
        bloque = tk.Frame(cab, background=tema.FONDO)
        bloque.grid(row=0, column=0, sticky="ew")
        self._bloque_titulo = bloque
        fila = tk.Frame(bloque, background=tema.FONDO)
        fila.pack(anchor="w")
        tema.etiqueta(fila, c.nombre, "titulo", tema.MARINO).pack(side="left")
        self.chip_guardado = tema.chip(fila, "sin guardar", "advertencia")
        self.chip_guardado.pack(side="left", padx=(12, 0))
        self.descripcion = tema.etiqueta(bloque, f"{c.disciplina} · {c.descripcion}", "cuerpo", tema.TEXTO_2,
                                         wraplength=tema._px(self, 760))
        self.descripcion.pack(anchor="w", pady=(4, 0))
        estado = tema.Flujo(bloque, separacion=12, separacion_v=4)
        estado.pack(anchor="w", fill="x", pady=(6, 0))
        estado.agregar(chip_validacion(estado, c.estado_validacion))
        estado.agregar(tema.etiqueta(estado, f"Auditoría: {c.estado_auditoria}", "pequeno", tema.TEXTO_2))
        enlace = tema.etiqueta(estado, "Información técnica →", "pequeno_negrita", tema.AZUL, cursor="hand2")
        enlace.bind("<Button-1>", lambda e: self.info())
        estado.agregar(enlace)
        self._fila_titulo = fila

        acciones = tema.Flujo(cab, separacion=8, alinear="right")
        self.acciones = acciones
        self.botones: dict[str, ttk.Widget] = {}

        def boton(texto, comando, estilo="TButton", clave=None, espacio=0):
            b = ttk.Button(acciones, text=texto, command=comando, style=estilo)
            acciones.agregar(b, espacio)
            self.botones[clave or texto] = b
            return b

        boton("Calcular", self.calcular, "Primario.TButton")
        acciones.agregar(tema.separador(acciones), 4)
        boton("Valores por defecto", self.restaurar_defectos, espacio=4)
        caso = tema.boton_menu(acciones, "Caso", [("Abrir caso…", self.abrir_caso),
                                                  ("Guardar caso…", self.guardar_caso)])
        acciones.agregar(caso)
        exportar = tema.boton_menu(acciones, "Exportar", [("Exportar a PDF…", self.exportar_pdf),
                                                          ("Exportar a Excel…", self.exportar_excel), None,
                                                          ("Copiar resultados", self.copiar_resultados)])
        acciones.agregar(exportar)
        self.botones["Caso"], self.botones["Exportar"] = caso, exportar
        if c.graficar:
            boton("Gráfica", self.mostrar_grafica)
        if c.imagenes:
            imagenes = tema.boton_menu(acciones, "Imágenes",
                                       [(i.rsplit(".", 1)[0], lambda i=i: self.ver_imagen(i)) for i in c.imagenes])
            acciones.agregar(imagenes)
            self.botones["Imágenes"] = imagenes
        acciones.agregar(tema.separador(acciones), 4)
        boton("Datos del proyecto…", self.editar_proyecto, "FantasmaFondo.TButton", espacio=4)
        cab.bind("<Configure>", self._ajustar_cabecera)

    def _ajustar_cabecera(self, evento=None) -> None:
        """Las acciones van a la derecha del título; si no caben, pasan a una segunda línea."""
        ancho = self._cabecera.winfo_width()
        if ancho <= 1:
            return
        natural = self.acciones.ancho_natural()
        titulo = max(self._fila_titulo.winfo_reqwidth(), tema._px(self, 360))
        en_linea = ancho >= titulo + natural + tema._px(self, 24)
        info = self.acciones.grid_info()
        fila = 0 if en_linea else 1
        if not info or int(info.get("row", -1)) != fila:
            self.acciones.grid_forget()
            if en_linea:
                self.acciones.alinear = "right"
                self.acciones.grid(row=0, column=1, sticky="se", padx=(tema._px(self, 20), 0))
            else:
                self.acciones.alinear = "left"
                self.acciones.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(tema._px(self, 10), 0))
            self.acciones.after_idle(self.acciones.acomodar)
        self.descripcion.configure(wraplength=max(tema._px(self, 320),
                                                  ancho - (natural + tema._px(self, 40) if en_linea else 0)))

    def _construir_formulario(self, izq: tk.Frame) -> None:
        cab = tk.Frame(izq, background=tema.FONDO)
        cab.pack(fill="x", pady=(0, 8))
        tema.titulo_seccion(cab, "Datos de entrada").pack(side="left", padx=(2, 0))
        nota = tk.Frame(cab, background=tema.FONDO)
        nota.pack(side="right", padx=(0, 16))
        tema.etiqueta(nota, "*", "pequeno_negrita", tema.ERROR).pack(side="left")
        tema.etiqueta(nota, " dato obligatorio", "pequeno", tema.TEXTO_2).pack(side="left")

        caja = tk.Frame(izq, background=tema.TONOS["info"]["fondo"], padx=12, pady=10)
        caja.pack(side="bottom", fill="x", pady=(10, 0))
        tema.icono(caja, "info", tema.AZUL, tema.TONOS["info"]["fondo"], 18).pack(side="left", anchor="n",
                                                                                 padx=(0, 10))
        self.ayuda = tema.etiqueta(caja, "Seleccione un campo para ver su ayuda.", "pequeno", tema.MARINO,
                                   tema.TONOS["info"]["fondo"], wraplength=tema._px(self, ANCHO_DATOS - 60))
        self.ayuda.pack(side="left", fill="x", expand=True)

        barra_v = ttk.Scrollbar(izq, orient="vertical")
        barra_v.pack(side="right", fill="y")
        lienzo = tk.Canvas(izq, highlightthickness=0, borderwidth=0, background=tema.FONDO,
                           width=tema._px(self, ANCHO_DATOS), yscrollcommand=barra_v.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra_v.configure(command=lienzo.yview)
        self.formulario = tk.Frame(lienzo, background=tema.FONDO)
        ventana_form = lienzo.create_window((0, 0), window=self.formulario, anchor="nw")
        self.formulario.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        # el formulario toma exactamente el ancho visible: nada queda oculto a la derecha
        lienzo.bind("<Configure>", lambda e: (lienzo.itemconfigure(ventana_form, width=e.width - 6),
                                              self._ajustar_rotulos(e.width - 6)))
        self._lienzo = lienzo
        # La rueda del ratón desplaza el formulario solo mientras el puntero está sobre él
        lienzo.bind("<Enter>", lambda e: self._rueda(True))
        lienzo.bind("<Leave>", lambda e: self._rueda(False))

        grupos: dict[str, dict] = {}
        self._rotulos: list[tuple[tk.Label, bool]] = []
        self.entradas_widget = {}
        self._pistas: dict[str, tk.Label] = {}
        self._grupo_de: dict[str, str] = {}
        for campo in self.calc.campos:
            g = grupos.get(campo.grupo)
            if g is None:
                tarjeta = tema.tarjeta(self.formulario, padx=tema._px(self, 16), pady=tema._px(self, 12))
                tarjeta.pack(fill="x", pady=(0, tema._px(self, 12)))
                tarjeta.columnconfigure(0, weight=1)
                tarjeta.columnconfigure(2, minsize=tema._px(self, 56))
                titulo = tk.Frame(tarjeta, background=tema.SUPERFICIE)
                titulo.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0, 6))
                tema.etiqueta(titulo, campo.grupo, "grupo", tema.MARINO, tema.SUPERFICIE).pack(side="left")
                insignia = tk.Label(titulo, text="", font=tema.fuente("mono_pequeno"), padx=7,
                                    background=tema.TONOS["advertencia"]["fondo"],
                                    foreground=tema.TONOS["advertencia"]["color"])
                g = grupos[campo.grupo] = {"marco": tarjeta, "fila": 1, "insignia": insignia, "claves": []}
            marco, fila = g["marco"], g["fila"]
            g["claves"].append(campo.clave)
            self._grupo_de[campo.clave] = campo.grupo
            rotulo = tk.Frame(marco, background=tema.SUPERFICIE)
            texto_etiqueta = tema.etiqueta(rotulo, campo.etiqueta, "cuerpo", tema.TEXTO, tema.SUPERFICIE,
                                           wraplength=tema._px(self, 205 if campo.tipo != "opcion" else 330))
            texto_etiqueta.pack(side="left")
            self._rotulos.append((texto_etiqueta, campo.tipo == "opcion"))
            if campo.obligatorio:
                tema.etiqueta(rotulo, "*", "cuerpo_negrita", tema.ERROR, tema.SUPERFICIE).pack(side="left",
                                                                                              anchor="n", padx=(2, 0))
            var = tk.StringVar()
            if campo.tipo == "opcion":  # las listas ocupan su propio renglón: los textos largos se leen completos
                rotulo.grid(row=fila, column=0, columnspan=3, sticky="w", pady=(6, 2))
                w = ttk.Combobox(marco, textvariable=var, values=campo.opciones, state="readonly", width=40,
                                 font=tema.fuente("cuerpo"))
                # evita que la rueda cambie la opción elegida al desplazar el formulario
                w.bind("<MouseWheel>", self._desplazar_formulario)
                w.bind("<Button-4>", self._desplazar_formulario)
                w.bind("<Button-5>", self._desplazar_formulario)
                w.grid(row=fila + 1, column=0, columnspan=3, sticky="ew", pady=(0, 4))
                fila += 2
            else:
                rotulo.grid(row=fila, column=0, sticky="w", pady=3, padx=(0, 8))
                w = ttk.Entry(marco, textvariable=var, width=11, justify="right", font=tema.fuente("mono"))
                w.grid(row=fila, column=1, sticky="ew", pady=3)
                tema.unidad(marco, campo.unidad).grid(row=fila, column=2, sticky="w", padx=(8, 0))
                fila += 1
            pista = tema.etiqueta(marco, "", "pequeno", tema.ERROR, tema.SUPERFICIE,
                                  wraplength=tema._px(self, ANCHO_DATOS - 60))
            pista.grid(row=fila, column=0, columnspan=3, sticky="w", pady=(0, 4))
            pista.grid_remove()
            self._pistas[campo.clave] = pista
            g["fila"] = fila + 1
            ayuda = campo.ayuda
            rango = campo.describir_rango()
            texto_ayuda = " ".join(t for t in (ayuda, f"Rango: {rango} {campo.unidad}." if rango else "") if t)
            w.bind("<FocusIn>", lambda e, t=texto_ayuda, c=campo: self._mostrar_ayuda(c.etiqueta, t))
            texto_etiqueta.bind("<Button-1>", lambda e, w=w: w.focus_set())
            self.variables[campo.clave] = var
            self.entradas_widget[campo.clave] = w
            var.trace_add("write", lambda *a, k=campo.clave: self._al_editar(k))
        self._grupos = grupos

    def _ajustar_rotulos(self, ancho_formulario: int) -> None:
        """Las etiquetas se ajustan al ancho de la columna de datos: nunca quedan tapadas por el campo."""
        interior = ancho_formulario - tema._px(self, 2 * 16 + 2)
        campo = tema._px(self, 11 * 8 + 24) + tema._px(self, 56 + 8 + 8 + 12)
        for rotulo, es_opcion in self._rotulos:
            rotulo.configure(wraplength=max(tema._px(self, 110), interior - (0 if es_opcion else campo)))
        self.ayuda.configure(wraplength=max(tema._px(self, 160), ancho_formulario - tema._px(self, 50)))

    def _construir_resultados(self, der: tk.Frame) -> None:
        self.zona_kpi = tk.Frame(der, background=tema.FONDO)
        self.zona_kpi.pack(fill="x")
        self.zona_avisos = tk.Frame(der, background=tema.FONDO)
        self.zona_avisos.pack(fill="x")
        tarjeta = tema.tarjeta(der)
        tarjeta.pack(fill="both", expand=True)
        self.pestanas = ttk.Notebook(tarjeta, style="Oculto.TNotebook")
        self.barra_pestanas = tema.BarraPestanas(tarjeta, self.pestanas)
        self.barra_pestanas.pack(fill="x")
        tema.separador(tarjeta, "horizontal").pack(fill="x")
        self.pestanas.pack(fill="both", expand=True)

        pagina = tk.Frame(self.pestanas, background=tema.SUPERFICIE)
        self.pagina_resultados = pagina
        self.pestanas.add(pagina, text="Resultados")
        self.barra_pestanas.agregar(pagina, "Resultados")
        self.vacio = self._construir_vacio(pagina)
        self.marco_tabla = tk.Frame(pagina, background=tema.SUPERFICIE)
        self.tabla = TablaResultados(self.marco_tabla)
        self.tabla.pack(fill="both", expand=True)
        leyenda(self.marco_tabla).pack(fill="x", side="bottom")

        self.panel_esquema = None
        if esquemas.disponible(self.calc.id):
            self.panel_esquema = PanelEsquema(self.pestanas, self)
            self.pestanas.add(self.panel_esquema, text="Esquema")
            self.barra_pestanas.agregar(self.panel_esquema, "Esquema")
            self.pestanas.bind("<<NotebookTabChanged>>", lambda e: self.panel_esquema.al_mostrar(), add="+")
            for var in self.variables.values():
                var.trace_add("write", lambda *a: self.panel_esquema.programar())

        notas = tk.Frame(self.pestanas, background=tema.SUPERFICIE)
        self.pagina_ecuaciones = notas
        self.pestanas.add(notas, text="Ecuaciones y notas")
        self.barra_pestanas.agregar(notas, "Ecuaciones y notas")
        barra = ttk.Scrollbar(notas, orient="vertical")
        barra.pack(side="right", fill="y")
        self.texto = tk.Text(notas, wrap="word", font=tema.fuente("cuerpo"), foreground=tema.TEXTO,
                             background=tema.SUPERFICIE, relief="flat", borderwidth=0, highlightthickness=0,
                             padx=tema._px(self, 20), pady=tema._px(self, 16), spacing1=2, spacing3=2,
                             yscrollcommand=barra.set)
        barra.configure(command=self.texto.yview)
        self.texto.pack(fill="both", expand=True)
        self.texto.tag_configure("tit", font=tema.fuente("etiqueta"), foreground=tema.TEXTO_2, spacing1=10,
                                 spacing3=6)
        self.texto.tag_configure("ec", font=tema.fuente("mono"), background=tema.SUPERFICIE_2,
                                 lmargin1=tema._px(self, 12), lmargin2=tema._px(self, 12),
                                 rmargin=tema._px(self, 12), spacing1=3, spacing3=3)
        self.texto.tag_configure("adv", foreground=tema.TONOS["advertencia"]["texto"])
        self.texto.tag_configure("nota", foreground=tema.TEXTO)
        self.texto.configure(state="disabled")

    def _construir_vacio(self, pagina: tk.Frame) -> tk.Frame:
        """Estado vacío: indicación actual del programa y lista de datos obligatorios pendientes."""
        vacio = tk.Frame(pagina, background=tema.SUPERFICIE)
        bloque = tk.Frame(vacio, background=tema.SUPERFICIE)
        bloque.place(relx=0.5, rely=0.42, anchor="center")
        tema.icono(bloque, "calcular", tema.ICONO_VACIO, tema.SUPERFICIE, 40).pack(anchor="w")
        tema.etiqueta(bloque, "Capture los datos y presione Calcular.", "subtitulo", tema.TEXTO,
                      tema.SUPERFICIE).pack(anchor="w", pady=(12, 4))
        tema.etiqueta(bloque, "Los resultados, su nivel de confianza, el esquema y las advertencias aparecerán "
                      "aquí.", "cuerpo", tema.TEXTO_2, tema.SUPERFICIE,
                      wraplength=tema._px(self, 440)).pack(anchor="w")
        t = tema.TONOS["advertencia"]
        self.caja_pendientes = tk.Frame(bloque, background="#FFF8EB", highlightthickness=1,
                                        highlightbackground=t["borde"], padx=14, pady=10)
        self.titulo_pendientes = tema.etiqueta(self.caja_pendientes, "", "pequeno_negrita", t["color"], "#FFF8EB")
        self.titulo_pendientes.pack(anchor="w", pady=(0, 4))
        self.lista_pendientes = tk.Frame(self.caja_pendientes, background="#FFF8EB")
        self.lista_pendientes.pack(anchor="w")
        self.boton_abrir_caso = ttk.Button(bloque, text="Abrir caso…", command=self.abrir_caso)
        self.boton_abrir_caso.pack(anchor="w", pady=(14, 0))
        return vacio

    # ------------------------------------------------------------ estado de la vista
    def _mostrar_vista_resultados(self, con_resultados: bool) -> None:
        if con_resultados:
            self.vacio.pack_forget()
            self.marco_tabla.pack(fill="both", expand=True)
        else:
            self.marco_tabla.pack_forget()
            self.vacio.pack(fill="both", expand=True)

    def _al_editar(self, clave: str) -> None:
        pista = self._pistas.get(clave)
        if pista is not None and pista.winfo_ismapped():
            pista.grid_remove()
        widget = self.entradas_widget.get(clave)
        if widget is not None:
            try:
                widget.state(["!invalid"])
            except tk.TclError:
                pass
        if self._refresco is None:
            try:
                self._refresco = self.after_idle(self._refrescar_formulario)
            except tk.TclError:
                self._refresco = None

    def _refrescar_formulario(self) -> None:
        """Datos obligatorios pendientes (ámbar), conteo por grupo, lista del estado vacío y etiqueta de guardado."""
        self._refresco = None
        if not self.winfo_exists():
            return
        pendientes = []
        for campo in self.calc.campos:
            if campo.tipo == "opcion":
                continue
            vacio = campo.obligatorio and not self.variables[campo.clave].get().strip()
            w = self.entradas_widget[campo.clave]
            estilo = "Pendiente.TEntry" if vacio else "TEntry"
            if str(w.cget("style")) != estilo:
                w.configure(style=estilo)
            if vacio:
                pendientes.append(campo)
        for nombre, g in self._grupos.items():
            n = sum(1 for c in pendientes if c.grupo == nombre)
            if n:
                g["insignia"].configure(text=f"{n} pendiente" + ("s" if n > 1 else ""))
                g["insignia"].pack(side="right")
            else:
                g["insignia"].pack_forget()
        for hijo in self.lista_pendientes.winfo_children():
            hijo.destroy()
        if pendientes:
            self.titulo_pendientes.configure(text=f"Datos obligatorios pendientes · {len(pendientes)}")
            for campo in pendientes:
                enlace = tema.etiqueta(self.lista_pendientes, campo.etiqueta, "pequeno",
                                       tema.TONOS["advertencia"]["texto"], "#FFF8EB", cursor="hand2")
                enlace.configure(font=(tema.fuente("pequeno")))
                enlace.pack(anchor="w")
                enlace.bind("<Button-1>", lambda e, k=campo.clave: self.enfocar_campo(k))
            self.caja_pendientes.pack(anchor="w", fill="x", pady=(14, 0), before=self.boton_abrir_caso)
        else:
            self.caja_pendientes.pack_forget()
        self._actualizar_chip_guardado()

    def _actualizar_chip_guardado(self) -> None:
        guardado = self._guardado is not None and self.capturado() == self._guardado
        t = tema.TONOS["correcto" if guardado else "advertencia"]
        self.chip_guardado.configure(text="guardado" if guardado else "sin guardar", foreground=t["color"],
                                     background=t["fondo"], highlightbackground=t["borde"])

    def enfocar_campo(self, clave: str) -> None:
        """Lleva el foco al campo y desplaza el formulario hasta él."""
        widget = self.entradas_widget[clave]
        self.update_idletasks()
        try:
            alto = max(self.formulario.winfo_height(), 1)
            y = widget.winfo_rooty() - self.formulario.winfo_rooty()
            self._lienzo.yview_moveto(max(0.0, (y - 60) / alto))
        except tk.TclError:
            pass
        widget.focus_set()

    def _marcar_errores(self, errores: list[str]) -> None:
        """Marca en rojo los campos con el mensaje existente debajo; el foco vuelve al primer error."""
        primero = None
        for campo in self.calc.campos:
            prefijo = f"«{campo.etiqueta}»"
            mensajes = [e for e in errores if e.startswith(prefijo)]
            if not mensajes:
                continue
            try:
                self.entradas_widget[campo.clave].state(["invalid"])
            except tk.TclError:
                pass
            pista = self._pistas[campo.clave]
            pista.configure(text=" ".join(m[len(prefijo):].lstrip(": ").strip() for m in mensajes))
            pista.grid()
            primero = primero or campo.clave
        if primero:
            self.enfocar_campo(primero)

    def _mostrar_kpis(self, resultado: Resultado | None) -> list[str]:
        for hijo in self.zona_kpi.winfo_children():
            hijo.destroy()
        if resultado is None:
            return []
        salidas = [resultado.salida(k) for k in KPI.get(self.calc.id, ()) if k in resultado]
        if not salidas:
            return []
        tarjeta = tema.tarjeta(self.zona_kpi)
        tarjeta.pack(fill="x", pady=(0, tema._px(self, 14)))
        celdas = []
        for s in salidas:
            celda = tk.Frame(tarjeta, background=tema.SUPERFICIE, padx=tema._px(self, 16), pady=tema._px(self, 12))
            rotulo = tema.etiqueta(celda, s.etiqueta, "pequeno", tema.TEXTO_2, tema.SUPERFICIE,
                                   wraplength=tema._px(self, 220))
            rotulo.pack(anchor="w")
            valor = tk.Frame(celda, background=tema.SUPERFICIE)
            valor.pack(anchor="w", pady=(2, 2))
            tema.etiqueta(valor, s.texto_valor(), "kpi", tema.MARINO, tema.SUPERFICIE).pack(side="left")
            if s.unidad:
                tema.etiqueta(valor, " " + s.unidad, "kpi_unidad", tema.TEXTO_2, tema.SUPERFICIE).pack(
                    side="left", anchor="s", pady=(0, 3))
            nivel = tk.Frame(celda, background=tema.SUPERFICIE)
            nivel.pack(anchor="w")
            insignia = tema.insignia_nivel(nivel, s.nivel, pequena=True)
            insignia.pack(side="left", padx=(0, 6))
            tema.etiqueta(nivel, NIVELES.get(s.nivel, s.nivel), "pequeno", tema.TEXTO_2, tema.SUPERFICIE).pack(
                side="left")
            if s.nota:
                tema.Tooltip(insignia, f"{NIVELES.get(s.nivel, s.nivel)}. Nota: {s.nota}")
            celdas.append((celda, rotulo))
        self._celdas_kpi = celdas
        tarjeta.bind("<Configure>", lambda e: self._distribuir_kpis(tarjeta, e.width))
        self._distribuir_kpis(tarjeta, max(tarjeta.winfo_width(), self.zona_kpi.winfo_width()))
        return [s.etiqueta for s in salidas]

    def _distribuir_kpis(self, tarjeta: tk.Frame, ancho: int) -> None:
        """Cuatro KPI en una fila; por debajo de ~760 px quedan en 2 × 2."""
        n = len(self._celdas_kpi)
        columnas = n if ancho >= tema._px(self, 190) * n or ancho <= 1 else min(2, n)
        for hijo in tarjeta.grid_slaves():
            if getattr(hijo, "_divisor", False):
                hijo.destroy()
        for i, (celda, rotulo) in enumerate(self._celdas_kpi):
            fila, col = divmod(i, columnas)
            celda.grid(row=fila * 2, column=col * 2, sticky="nsew")
            rotulo.configure(wraplength=max(tema._px(self, 120), ancho // columnas - tema._px(self, 40)))
            if col < columnas - 1 and i < n - 1:
                d = tema.separador(tarjeta, "vertical", tema.DIVISOR)
                d._divisor = True
                d.grid(row=fila * 2, column=col * 2 + 1, sticky="ns", pady=tema._px(self, 10))
            if fila < (n - 1) // columnas:
                d = tema.separador(tarjeta, "horizontal", tema.DIVISOR)
                d._divisor = True
                d.grid(row=fila * 2 + 1, column=col * 2, sticky="ew", padx=tema._px(self, 12))
        for col in range(8):
            tarjeta.columnconfigure(col, weight=1 if col % 2 == 0 and col // 2 < columnas else 0, uniform="")
        for col in range(0, columnas * 2, 2):
            tarjeta.columnconfigure(col, weight=1, uniform="kpi")

    def _mostrar_avisos(self, resultado: Resultado | None) -> None:
        for hijo in self.zona_avisos.winfo_children():
            hijo.destroy()
        if resultado is None or not resultado.advertencias:
            return
        n = len(resultado.advertencias)
        aviso = tema.Aviso(self.zona_avisos, "advertencia", resultado.advertencias,
                           titulo="Advertencia" if n == 1 else "Advertencias",
                           max_lineas=4 if self.winfo_height() < tema._px(self, 820) else 8)
        aviso.pack(fill="x", pady=(0, tema._px(self, 14)))

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

    def _ir_al_menu(self) -> None:
        raiz = self._root()
        try:
            if raiz.state() == "withdrawn":
                return
            raiz.deiconify()
            raiz.lift()
            raiz.focus_force()
        except tk.TclError:
            pass

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
        self._mostrar_kpis(None)
        self._mostrar_avisos(None)
        self.barra_pestanas.contador(self.pagina_resultados, None)
        self._mostrar_vista_resultados(False)
        self._refrescar_formulario()

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
            self.estado.mostrar("Datos no válidos: corrija y vuelva a calcular.", "critico")
            self._marcar_errores(e.errores)
            self.mostrar_error("Datos no válidos", "\n".join(e.errores))
            return None
        self.ultimo = (crudo, datos, resultado)
        self.historial_ok = historial.registrar(self.calc, datos, resultado, proyecto_actual())
        self.tabla.delete(*self.tabla.get_children())
        for s in resultado.salidas:
            iid = self.tabla.insert("", "end", text=s.etiqueta, values=(s.texto_valor(), s.unidad, s.nivel),
                                    tags=(s.nivel,))
            if s.nota:
                self.tabla.nota(iid, s.nota)
        claves = self._mostrar_kpis(resultado)
        self.tabla.destacar(claves)
        self._mostrar_avisos(resultado)
        self._mostrar_vista_resultados(True)
        self.barra_pestanas.contador(self.pagina_resultados, len(resultado.salidas))
        bloques = []
        if resultado.ecuaciones:
            bloques.append(("ECUACIONES\n", "tit"))
            bloques += [(f"{e}\n", "ec") for e in resultado.ecuaciones]
        if resultado.notas:
            bloques.append(("\nNOTAS\n" if bloques else "NOTAS\n", "tit"))
            bloques += [(f"• {n}\n", "nota") for n in resultado.notas]
        if resultado.advertencias:
            bloques.append(("\nADVERTENCIAS\n" if bloques else "ADVERTENCIAS\n", "tit"))
            bloques += [(f"• {a}\n", "adv") for a in resultado.advertencias]
        self._escribir_texto(bloques)
        self.estado.mostrar(f"Cálculo realizado: {len(resultado.salidas)} resultados, "
                            f"{len(resultado.advertencias)} advertencias.", "correcto")
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
            self._guardado = self.capturado()
            self._actualizar_chip_guardado()
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
            self.estado.derecha.configure(text=texto_proyecto())
        self.restaurar_defectos()
        self.asignar(datos["entradas"])
        self._guardado = self.capturado()
        self.calcular()
        self._actualizar_chip_guardado()

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
        self.estado.derecha.configure(text=texto_proyecto())
        self.estado.configure(text="Datos del proyecto actualizados (se usan en PDF, Excel, casos e historial).")

    def mostrar_grafica(self) -> None:
        if not self._requerir_calculo_vigente():
            return
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        _, datos, resultado = self.ultimo
        figura = self.calc.graficar(datos, resultado)
        ventana = tk.Toplevel(self)
        ventana.title(f"Gráfica — {self.calc.nombre}")
        ventana.configure(background=tema.SUPERFICIE)
        pie = tk.Frame(ventana, background=tema.SUPERFICIE_2)
        pie.pack(fill="x", side="bottom")
        tema.separador(pie, "horizontal", tema.DIVISOR).pack(fill="x", side="top")
        ttk.Button(pie, text="Cerrar", command=ventana.destroy).pack(side="right", padx=16, pady=8)
        lienzo = FigureCanvasTkAgg(figura, master=ventana)
        lienzo.draw()
        lienzo.get_tk_widget().pack(fill="both", expand=True, padx=12, pady=12)
        return ventana

    def ver_imagen(self, nombre: str) -> None:
        ruta = recurso(nombre)
        if not ruta.is_file():
            self.mostrar_error("Imagen no encontrada", f"No existe {ruta}.")
            return
        from PIL import Image, ImageTk

        ventana = tk.Toplevel(self)
        ventana.title(nombre)
        ventana.configure(background=tema.SUPERFICIE)
        imagen = Image.open(ruta)
        imagen.thumbnail((900, 700))
        foto = ImageTk.PhotoImage(imagen)
        etiqueta = tk.Label(ventana, image=foto, background=tema.SUPERFICIE)
        etiqueta.image = foto
        etiqueta.pack(padx=12, pady=12)
        return ventana

    def info(self) -> "DialogoInformacion":
        return DialogoInformacion(self, self.calc)

    def mostrar_error(self, titulo: str, mensaje: str) -> None:
        messagebox.showerror(titulo, mensaje, parent=self)


class DialogoInformacion(tema.DialogoBase):
    """Información técnica de la calculadora (mismo contenido que antes, con el formato de diálogo común)."""

    def __init__(self, padre: tk.Misc, c: Calculadora):
        super().__init__(padre, "Información técnica", c.nombre)
        self.transient(padre)
        self.geometry(f"{tema._px(self, 640)}x{min(tema._px(self, 720), self.winfo_screenheight() - 120)}")
        self.boton("Aceptar", self.destroy, primario=True)
        barra = ttk.Scrollbar(self.cuerpo, orient="vertical")
        barra.pack(side="right", fill="y")
        texto = tk.Text(self.cuerpo, wrap="word", font=tema.fuente("cuerpo"), foreground=tema.TEXTO,
                        background=tema.SUPERFICIE, relief="flat", borderwidth=0, highlightthickness=0,
                        yscrollcommand=barra.set, spacing1=2, spacing3=2, padx=2)
        barra.configure(command=texto.yview)
        texto.pack(fill="both", expand=True)
        texto.tag_configure("tit", font=tema.fuente("etiqueta"), foreground=tema.TEXTO_2, spacing1=12, spacing3=4)
        texto.tag_configure("mono", font=tema.fuente("mono_pequeno"), foreground=tema.TEXTO_2)
        texto.tag_configure("lim", foreground=tema.TONOS["advertencia"]["texto"],
                            background=tema.TONOS["advertencia"]["fondo"], lmargin1=8, lmargin2=20, rmargin=8)
        for etiqueta, valor in (("Disciplina", c.disciplina), ("Estado de auditoría", c.estado_auditoria),
                                ("Estado de validación", c.estado_validacion)):
            texto.insert("end", f"{etiqueta}: ", "")
            texto.insert("end", f"{valor}\n", "")
        secciones = (("Referencias", c.referencias, ""), ("Limitaciones", c.limitaciones, "lim"),
                     ("Archivos originales que sustituye", c.archivos_originales, "mono"))
        for titulo, lineas, etiqueta in secciones:
            texto.insert("end", f"\n{titulo.upper()}\n", "tit")
            for linea in lineas:
                texto.insert("end", f"• {linea}\n", etiqueta)
        texto.insert("end", "\nNIVELES DE CONFIANZA\n", "tit")
        for nivel, nombre in NIVELES.items():
            insignia = tema.insignia_nivel(texto, nivel, pequena=True)
            texto.window_create("end", window=insignia, padx=2, pady=2)
            texto.insert("end", f"  {nombre}\n")
        texto.configure(state="disabled")
        self.texto = texto


class DialogoProyecto(tema.DialogoBase):
    """Captura de los datos del proyecto que encabezan las memorias de cálculo."""

    def __init__(self, padre: tk.Misc, datos: dict, al_guardar):
        super().__init__(padre, "Datos del proyecto",
                         "Encabezado de las memorias de cálculo (PDF, Excel), casos guardados e historial.")
        self.resizable(False, False)
        self.transient(padre)
        self.al_guardar = al_guardar
        self.variables: dict[str, tk.StringVar] = {}
        self.cuerpo.columnconfigure(1, weight=1)
        fila = 0
        for clave, etiqueta in historial.CAMPOS_PROYECTO:
            if clave == "elaboro":  # separa los datos del documento de las firmas
                tema.separador(self.cuerpo, "horizontal", tema.DIVISOR).grid(row=fila, column=0, columnspan=2,
                                                                            sticky="ew", pady=6)
                fila += 1
            tema.etiqueta(self.cuerpo, etiqueta, "cuerpo", tema.TEXTO, tema.SUPERFICIE).grid(
                row=fila, column=0, sticky="w", padx=(0, 12), pady=4)
            var = tk.StringVar(value=datos.get(clave, ""))
            ttk.Entry(self.cuerpo, textvariable=var, width=40 if clave != "revision" else 10).grid(
                row=fila, column=1, sticky="ew" if clave != "revision" else "w", pady=4)
            self.variables[clave] = var
            fila += 1
        self.boton("Guardar", self.guardar, primario=True)
        self.boton("Cancelar", self.destroy)
        self.boton("Limpiar", self.limpiar, izquierda=True, estilo="FantasmaPie.TButton")

    def valores(self) -> dict:
        return {clave: var.get() for clave, var in self.variables.items()}

    def limpiar(self) -> None:
        for var in self.variables.values():
            var.set("")

    def guardar(self) -> None:
        self.al_guardar(self.valores())
        self.destroy()
