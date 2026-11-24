"""Menú principal: calculadoras organizadas por disciplina, buscador y estado de auditoría.

Sustituye al «manejador de archivos» original, que abría scripts por rutas fijas
``D:\\Python\\...`` con ``subprocess`` (rutas rotas en cualquier otra PC). Aquí cada
calculadora o memoria se abre como ventana dentro del mismo proceso a partir de
el catálogo de ``calculadoras.catalogo``. HVAC industrial usa su propio proceso Qt.

Rediseño de interfaz v1: encabezado con logotipo y buscador, categorías con conteo,
favoritos y recientes a la izquierda, catálogo agrupado al centro y ficha de la
herramienta (limitaciones principales, estado de validación) a la derecha.
"""
from __future__ import annotations

import json
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import __version__
from ..calculos import CALCULADORAS, POR_ID
from ..memorias import POR_ID as MEMORIAS_POR_ID
from ..catalogo import HERRAMIENTAS, POR_ID as POR_HERRAMIENTA, buscar, por_disciplina
from ..aplicaciones import POR_ID as APLICACIONES_POR_ID, abrir_nativa, abrir_externa
from ..nucleo.configuracion import RAIZ, cargar, recurso
from ..nucleo.modelo import NIVELES
from . import preferencias, reportes, tema
from .ventana import ESTADO_CORTO, VentanaCalculadora, chip_validacion  # noqa: F401 (ESTADO_CORTO: compatibilidad)

TODAS = "Todas"
TEXTO_BUSQUEDA = "Buscar calculadora, categoría o norma (p. ej. ISO 5048)"


BIBLIOTECAS = {"reportlab": "memoria PDF", "openpyxl": "exportar a Excel", "matplotlib": "gráficas",
               "PIL": "logotipo e imágenes de referencia"}


def bibliotecas_faltantes() -> list[str]:
    """Bibliotecas opcionales de requirements.txt que no están instaladas (el cálculo no las necesita)."""
    import importlib.util

    return [nombre for nombre in BIBLIOTECAS if importlib.util.find_spec(nombre) is None]


class MenuPrincipal(ttk.Frame):
    def __init__(self, raiz: tk.Tk):
        tema.aplicar(raiz)
        super().__init__(raiz, padding=0)
        self.raiz = raiz
        self.config_app = cargar()
        self.ventanas: dict[str, tk.Toplevel] = {}
        self.procesos = {}
        self._vigias = {}
        self.preferencias = preferencias.cargar()
        self.categoria = TODAS
        raiz.title("Calculadoras de Ingeniería RMR")
        raiz.configure(background=tema.FONDO)
        raiz.geometry(f"{min(1360, raiz.winfo_screenwidth() - 40)}x{min(820, raiz.winfo_screenheight() - 80)}")
        raiz.minsize(min(980, raiz.winfo_screenwidth() - 40), min(600, raiz.winfo_screenheight() - 80))
        self._icono()
        self._menu()
        self._construir()
        self.pack(fill="both", expand=True)
        self.filtrar()

    # ------------------------------------------------------------------ UI
    def _icono(self) -> None:
        ico = recurso("Nueva etiqueta RMR.ico")
        try:
            if ico.is_file():
                self.raiz.iconbitmap(default=str(ico))
        except tk.TclError:  # Linux/macOS no aceptan .ico: se ignora
            pass

    def _menu(self) -> None:
        barra = tk.Menu(self.raiz)
        archivo = tk.Menu(barra, tearoff=0)
        archivo.add_command(label="Abrir caso guardado…", command=self.abrir_caso)
        archivo.add_command(label="Historial de cálculos…", command=self.ver_historial)
        archivo.add_command(label="Datos del proyecto…", command=self.editar_proyecto)
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.salir)
        barra.add_cascade(label="Archivo", menu=archivo)
        ayuda = tk.Menu(barra, tearoff=0)
        ayuda.add_command(label="Niveles de confianza de los resultados", command=self.niveles)
        ayuda.add_command(label="Abrir carpeta de documentación", command=self.documentacion)
        ayuda.add_command(label="Acerca de", command=self.acerca_de)
        barra.add_cascade(label="Ayuda", menu=ayuda)
        self.raiz.config(menu=barra)

    def _construir(self) -> None:
        self._construir_encabezado()
        sitio = self.config_app["sitio"]
        self.estado = tema.BarraEstado(
            self, f"Versión {__version__} · {len(CALCULADORAS)} calculadoras · Sitio por defecto: "
                  f"{sitio.get('nombre', '')} ({sitio.get('altitud_m', 0)} m) · "
                  f"{len(HERRAMIENTAS)} herramientas disponibles")
        self.estado.pack(fill="x", side="bottom")
        faltantes = bibliotecas_faltantes()
        if faltantes:
            t = tema.TONOS["critico"]
            caja = tk.Frame(self, background=t["fondo"], highlightthickness=1, highlightbackground=t["borde"],
                            padx=12, pady=8)
            caja.pack(fill="x", side="bottom", padx=24, pady=(0, 10))
            tema.icono(caja, "error", t["color"], t["fondo"]).pack(side="left", padx=(0, 10))
            self.aviso_bibliotecas = tema.etiqueta(
                caja, "Faltan bibliotecas: " + ", ".join(faltantes) + ". Funciones afectadas: "
                + "; ".join(BIBLIOTECAS[b] for b in faltantes) + ". Ejecute INSTALAR.bat.", "cuerpo", t["texto"],
                t["fondo"])
            self.aviso_bibliotecas.pack(side="left", fill="x", expand=True)

        cuerpo = tk.Frame(self, background=tema.FONDO)
        cuerpo.pack(fill="both", expand=True, padx=tema._px(self, 24), pady=tema._px(self, 20))
        cuerpo.columnconfigure(0, minsize=tema._px(self, 230))
        cuerpo.columnconfigure(1, weight=1)
        cuerpo.columnconfigure(2, minsize=tema._px(self, 360))
        cuerpo.rowconfigure(0, weight=1)
        self._construir_navegacion(cuerpo)
        self._construir_catalogo(cuerpo)
        self._construir_detalle(cuerpo)

    def _construir_encabezado(self) -> None:
        banda = tk.Frame(self, background=tema.SUPERFICIE)
        banda.pack(fill="x", side="top")
        tema.separador(banda, "horizontal", tema.DIVISOR).pack(fill="x", side="top")
        fila = tk.Frame(banda, background=tema.SUPERFICIE)
        fila.pack(fill="x", padx=tema._px(self, 24), pady=tema._px(self, 14))
        logo = tema.logotipo(fila, recurso(self.config_app["reportes"].get("logo", "")), 48, tema.SUPERFICIE)
        if logo is not None:
            logo.pack(side="left", padx=(0, tema._px(self, 24)))
        titulos = tk.Frame(fila, background=tema.SUPERFICIE)
        titulos.pack(side="left")
        tema.etiqueta(titulos, "Calculadoras de Ingeniería", "titulo_app", tema.MARINO).pack(anchor="w")
        categorias = len([d for d, lista in por_disciplina().items() if lista])
        tema.etiqueta(titulos, f"{len(HERRAMIENTAS)} herramientas · {categorias} categorías", "pequeno",
                      tema.TEXTO_2).pack(anchor="w", pady=(2, 0))

        caja = tk.Frame(fila, background=tema.SUPERFICIE_2, highlightthickness=1,
                        highlightbackground=tema.BORDE_CONTROL, highlightcolor=tema.AZUL)
        caja.pack(side="right", fill="x", expand=True, padx=(tema._px(self, 40), 0), ipady=2)
        caja.configure(width=tema._px(self, 520))
        tema.icono(caja, "buscar", tema.TEXTO_2, tema.SUPERFICIE_2, 18).pack(side="left", padx=(10, 6))
        self.texto_busqueda = tk.StringVar()
        self.texto_busqueda.trace_add("write", lambda *a: self.filtrar())
        entrada = tk.Entry(caja, textvariable=self.texto_busqueda, relief="flat", borderwidth=0,
                           highlightthickness=0, background=tema.SUPERFICIE_2, foreground=tema.TEXTO,
                           insertbackground=tema.TEXTO, font=tema.fuente("cuerpo"))
        entrada.pack(side="left", fill="x", expand=True, ipady=5)
        self.entrada_busqueda = entrada
        indicacion = tema.etiqueta(caja, TEXTO_BUSQUEDA, "cuerpo", tema.TEXTO_3, tema.SUPERFICIE_2)
        indicacion.bind("<Button-1>", lambda e: entrada.focus_set())
        limpiar = tema.etiqueta(caja, "×", "subtitulo", tema.TEXTO_2, tema.SUPERFICIE_2, cursor="hand2")
        limpiar.bind("<Button-1>", lambda e: (self.texto_busqueda.set(""), entrada.focus_set()))
        self._limpiar_busqueda = limpiar

        def indicar(*_):
            vacio = not self.texto_busqueda.get()
            if vacio:
                indicacion.place(in_=entrada, x=0, rely=0.5, anchor="w")
                limpiar.pack_forget()
            else:
                indicacion.place_forget()
                limpiar.pack(side="right", padx=(6, 10))

        self.texto_busqueda.trace_add("write", indicar)
        entrada.bind("<Escape>", lambda e: self.texto_busqueda.set(""))
        entrada.bind("<Down>", lambda e: self._enfocar_catalogo())
        entrada.bind("<Return>", lambda e: self._enfocar_catalogo())
        entrada.after_idle(indicar)
        entrada.focus_set()
        tema.separador(banda, "horizontal").pack(fill="x", side="bottom")

    def _construir_navegacion(self, cuerpo: tk.Frame) -> None:
        nav = tk.Frame(cuerpo, background=tema.FONDO)
        nav.grid(row=0, column=0, sticky="nsew", padx=(0, tema._px(self, 20)))
        tema.titulo_seccion(nav, "Categoría").pack(anchor="w", padx=10, pady=(0, 6))
        self.facetas: dict[str, dict] = {}
        conteos = {d: len(lista) for d, lista in por_disciplina().items() if lista}
        for nombre, n in ((TODAS, len(HERRAMIENTAS)), *conteos.items()):
            fila = tk.Frame(nav, background=tema.FONDO, cursor="hand2", padx=10, pady=6)
            fila.pack(fill="x", pady=1)
            rotulo = tema.etiqueta(fila, nombre, "cuerpo", tema.TEXTO, tema.FONDO, wraplength=tema._px(self, 175))
            rotulo.pack(side="left")
            cuenta = tema.etiqueta(fila, str(n), "mono_pequeno", tema.TEXTO_2, tema.FONDO)
            cuenta.pack(side="right")
            for w in (fila, rotulo, cuenta):
                w.bind("<Button-1>", lambda e, c=nombre: self.elegir_categoria(c))
                w.bind("<Enter>", lambda e, c=nombre: self._pintar_faceta(c, sobre=True))
                w.bind("<Leave>", lambda e, c=nombre: self._pintar_faceta(c))
            self.facetas[nombre] = {"fila": fila, "rotulo": rotulo, "cuenta": cuenta}
        self._pintar_facetas()

        self.caja_favoritos = self._caja_lista(nav, "Favoritos", estrella=True)
        self.caja_recientes = self._caja_lista(nav, "Recientes")
        self._actualizar_listas()

    def _caja_lista(self, padre: tk.Misc, titulo: str, estrella: bool = False) -> tk.Frame:
        caja = tema.tarjeta(padre, padx=12, pady=10)
        caja.pack(fill="x", pady=(tema._px(self, 18), 0))
        cab = tk.Frame(caja, background=tema.SUPERFICIE)
        cab.pack(fill="x", pady=(0, 4))
        if estrella:
            tk.Label(cab, image=tema.imagen_estrella(self, True, 14), background=tema.SUPERFICIE).pack(
                side="left", padx=(0, 6))
        tema.titulo_seccion(cab, titulo, tema.SUPERFICIE).pack(side="left")
        caja.lista = tk.Frame(caja, background=tema.SUPERFICIE)
        caja.lista.pack(fill="x")
        return caja

    def _actualizar_listas(self) -> None:
        for caja, ids, vacio in ((self.caja_favoritos, self.preferencias["favoritos"],
                                  "Marque con la estrella sus herramientas frecuentes."),
                                 (self.caja_recientes, self.preferencias["recientes"],
                                  "Aún no ha abierto herramientas.")):
            for hijo in caja.lista.winfo_children():
                hijo.destroy()
            validos = [i for i in ids if i in POR_HERRAMIENTA]
            if not validos:
                tema.etiqueta(caja.lista, vacio, "pequeno", tema.TEXTO_2, tema.SUPERFICIE,
                              wraplength=tema._px(self, 190)).pack(anchor="w")
            for identificador in validos:
                enlace = tema.etiqueta(caja.lista, POR_HERRAMIENTA[identificador].nombre, "pequeno", tema.AZUL,
                                       tema.SUPERFICIE, cursor="hand2", wraplength=tema._px(self, 190))
                enlace.pack(anchor="w", pady=1)
                enlace.bind("<Button-1>", lambda e, i=identificador: self.abrir(i))

    def _construir_catalogo(self, cuerpo: tk.Frame) -> None:
        tarjeta = tema.tarjeta(cuerpo, padx=8, pady=8)
        tarjeta.grid(row=0, column=1, sticky="nsew")
        self.arbol = ttk.Treeview(tarjeta, columns=("descripcion",), show="tree headings", selectmode="browse",
                                  style="Catalogo.Treeview")
        self.arbol.heading("#0", text="CALCULADORA", anchor="w")
        self.arbol.heading("descripcion", text="DESCRIPCIÓN", anchor="w")
        self.arbol.column("#0", width=tema._px(self, 300), minwidth=tema._px(self, 200))
        self.arbol.column("descripcion", width=tema._px(self, 380), minwidth=tema._px(self, 120))
        self.arbol.tag_configure("grupo", font=tema.fuente("grupo"), foreground=tema.MARINO)
        self.arbol.tag_configure("herramienta", font=tema.fuente("cuerpo"), foreground=tema.TEXTO)
        barra = ttk.Scrollbar(tarjeta, orient="vertical", command=self.arbol.yview)
        barra.pack(side="right", fill="y")
        self.arbol.pack(side="left", fill="both", expand=True)
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.bind("<<TreeviewSelect>>", lambda e: self.describir())
        self.arbol.bind("<Double-1>", lambda e: self.abrir_seleccion())
        self.arbol.bind("<Return>", lambda e: self.abrir_seleccion())
        self.arbol.bind("<Button-1>", self._clic_catalogo, add="+")
        self.arbol.bind("<KeyPress-f>", lambda e: self.alternar_favorito())

    def _construir_detalle(self, cuerpo: tk.Frame) -> None:
        tarjeta = tema.tarjeta(cuerpo)
        tarjeta.grid(row=0, column=2, sticky="nsew", padx=(tema._px(self, 20), 0))
        ancho = tema._px(self, 330)
        cab = tk.Frame(tarjeta, background=tema.SUPERFICIE, padx=20, pady=18)
        cab.pack(fill="x")
        self.categoria_detalle = tema.etiqueta(cab, "", "pequeno", tema.TEXTO_2, tema.SUPERFICIE)
        self.categoria_detalle.pack(anchor="w")
        self.titulo = tema.etiqueta(cab, "Seleccione una calculadora", "titulo_panel", tema.MARINO, tema.SUPERFICIE,
                                    wraplength=ancho)
        self.titulo.pack(anchor="w", pady=(4, 6))
        self.descripcion = tema.etiqueta(cab, "Elija una herramienta del catálogo para ver su descripción, su "
                                         "estado de validación y sus limitaciones.", "cuerpo", tema.TEXTO,
                                         tema.SUPERFICIE, wraplength=ancho)
        self.descripcion.pack(anchor="w")
        self.fila_estado = tk.Frame(cab, background=tema.SUPERFICIE)
        self.fila_estado.pack(anchor="w", fill="x", pady=(10, 0))
        tema.separador(tarjeta, "horizontal", tema.DIVISOR).pack(fill="x")

        pie = tk.Frame(tarjeta, background=tema.SUPERFICIE_2)
        pie.pack(fill="x", side="bottom")
        tema.separador(pie, "horizontal", tema.DIVISOR).pack(fill="x", side="top")
        fila_pie = tk.Frame(pie, background=tema.SUPERFICIE_2, padx=20, pady=12)
        fila_pie.pack(fill="x")
        self.boton_abrir = ttk.Button(fila_pie, text="Abrir calculadora →", command=self.abrir_seleccion,
                                      state="disabled", style="Primario.TButton")
        self.boton_abrir.pack(side="right")
        tema.etiqueta(fila_pie, "Doble clic o Intro\ntambién abren", "pequeno", tema.TEXTO_2,
                      tema.SUPERFICIE_2).pack(side="left")

        self.detalle = tk.Frame(tarjeta, background=tema.SUPERFICIE, padx=20, pady=16)
        self.detalle.pack(fill="both", expand=True)
        self._ancho_detalle = ancho

    def _pintar_faceta(self, nombre: str, sobre: bool = False) -> None:
        f = self.facetas[nombre]
        activa = nombre == self.categoria
        fondo = tema.AZUL_50 if activa else (tema.DESHABILITADO if sobre else tema.FONDO)
        for w in (f["fila"], f["rotulo"], f["cuenta"]):
            w.configure(background=fondo)
        f["rotulo"].configure(font=tema.fuente("cuerpo_negrita" if activa else "cuerpo"),
                              foreground=tema.MARINO if activa else tema.TEXTO)
        f["cuenta"].configure(foreground=tema.AZUL if activa else tema.TEXTO_2)

    def _pintar_facetas(self) -> None:
        for nombre in self.facetas:
            self._pintar_faceta(nombre)

    def elegir_categoria(self, nombre: str) -> None:
        self.categoria = nombre
        self._pintar_facetas()
        self.filtrar()

    def _enfocar_catalogo(self) -> str:
        hijos = [h for d in self.arbol.get_children() for h in self.arbol.get_children(d)]
        if hijos:
            seleccion = self.arbol.selection()
            objetivo = seleccion[0] if seleccion and seleccion[0] in hijos else hijos[0]
            self.arbol.selection_set(objetivo)
            self.arbol.focus(objetivo)
            self.arbol.see(objetivo)
        self.arbol.focus_set()
        return "break"

    def _clic_catalogo(self, evento) -> str | None:
        """Clic sobre la estrella: agrega o quita la herramienta de favoritos."""
        fila = self.arbol.identify_row(evento.y)
        if fila in POR_HERRAMIENTA and self.arbol.identify_element(evento.x, evento.y) == "image":
            self.alternar_favorito(fila)
            return "break"
        return None

    def alternar_favorito(self, identificador: str | None = None) -> bool:
        if identificador is None:
            c = self.seleccion()
            if c is None:
                return False
            identificador = c.id
        es_favorito = preferencias.alternar_favorito(self.preferencias, identificador)
        if self.arbol.exists(identificador):
            self.arbol.item(identificador, image=tema.imagen_estrella(self, es_favorito))
        self._actualizar_listas()
        self.describir()
        return es_favorito

    # ------------------------------------------------------------ lógica
    def filtrar(self) -> None:
        texto = self.texto_busqueda.get()
        visibles = {c.id for c in buscar(texto)
                    if self.categoria == TODAS or c.disciplina == self.categoria}
        self.arbol.delete(*self.arbol.get_children())
        grupos = por_disciplina()
        favoritos = set(self.preferencias["favoritos"])
        for disciplina, lista in grupos.items():
            lista = [c for c in lista if c.id in visibles]
            if not lista:
                continue
            nodo = self.arbol.insert("", "end", iid=f"disciplina::{disciplina}", text=disciplina, open=True,
                                     values=(f"{len(lista)} herramienta" + ("s" if len(lista) > 1 else ""),),
                                     tags=("grupo",))
            for c in lista:
                self.arbol.insert(nodo, "end", iid=c.id, text=c.nombre,
                                  values=(c.descripcion,), tags=("herramienta",),
                                  image=tema.imagen_estrella(self, c.id in favoritos))
        if len(visibles) == 1:
            unico = next(iter(visibles))
            self.arbol.selection_set(unico)
            self.arbol.see(unico)
        self.describir()  # el panel de detalle no debe mostrar una calculadora que el filtro ocultó

    def seleccion(self):
        sel = self.arbol.selection()
        return POR_HERRAMIENTA.get(sel[0]) if sel else None

    def describir(self) -> None:
        c = self.seleccion()
        for hijo in self.detalle.winfo_children():
            hijo.destroy()
        for hijo in self.fila_estado.winfo_children():
            hijo.destroy()
        if c is None:
            self.categoria_detalle.configure(text="")
            self.titulo.configure(text="Seleccione una calculadora")
            self.descripcion.configure(text="Elija una herramienta del catálogo para ver su descripción, su estado "
                                            "de validación y sus limitaciones.")
            self.boton_abrir.configure(state="disabled")
            return
        self.categoria_detalle.configure(text=c.disciplina)
        self.titulo.configure(text=c.nombre)
        self.descripcion.configure(text=c.descripcion)
        chip_validacion(self.fila_estado, c.estado_validacion).pack(anchor="w")
        tema.etiqueta(self.fila_estado, f"Auditoría: {c.estado_auditoria}", "pequeno", tema.TEXTO_2,
                      tema.SUPERFICIE, wraplength=self._ancho_detalle).pack(anchor="w", pady=(6, 0))
        ancho = self._ancho_detalle
        t = tema.TONOS["advertencia"]
        limitaciones = list(c.limitaciones[:4])
        if limitaciones:
            caja = tk.Frame(self.detalle, background="#FFF8EB", highlightthickness=1, highlightbackground=t["borde"],
                            padx=14, pady=10)
            caja.pack(fill="x")
            tema.etiqueta(caja, "Limitaciones principales", "pequeno_negrita", t["color"], "#FFF8EB").pack(
                anchor="w", pady=(0, 4))
            for linea in limitaciones:
                tema.etiqueta(caja, f"•  {linea}", "pequeno", "#3D2600", "#FFF8EB",
                              wraplength=ancho - tema._px(self, 30)).pack(anchor="w", pady=1)
        favorito = c.id in self.preferencias["favoritos"]
        acciones = tk.Frame(self.detalle, background=tema.SUPERFICIE)
        acciones.pack(fill="x", pady=(12, 0))
        boton_favorito = ttk.Button(acciones, text="Quitar de favoritos" if favorito else "Agregar a favoritos",
                                    image=tema.imagen_estrella(self, favorito, 16), compound="left",
                                    style="Fantasma.TButton", command=self.alternar_favorito)
        boton_favorito.pack(side="left")
        self.boton_favorito = boton_favorito
        if c.archivos_originales:
            sustituye = tk.Frame(self.detalle, background=tema.SUPERFICIE)
            sustituye.pack(fill="x", pady=(8, 0))
            conmutador = tema.etiqueta(sustituye, "▸ Sustituye a", "pequeno", tema.TEXTO_2, tema.SUPERFICIE,
                                       cursor="hand2")
            conmutador.pack(anchor="w")
            archivos = tema.etiqueta(sustituye, ", ".join(c.archivos_originales), "mono_pequeno", tema.TEXTO_2,
                                     tema.SUPERFICIE, wraplength=ancho)

            def alternar(_e=None):
                if archivos.winfo_ismapped():
                    archivos.pack_forget()
                    conmutador.configure(text="▸ Sustituye a")
                else:
                    archivos.pack(anchor="w", pady=(4, 0))
                    conmutador.configure(text="▾ Sustituye a")

            conmutador.bind("<Button-1>", alternar)
        self.boton_abrir.configure(state="normal")

    def abrir_seleccion(self):
        c = self.seleccion()
        if c is not None:
            return self.abrir(c.id)
        return None

    def abrir(self, id_calculadora: str):
        """Abre (o trae al frente) una calculadora o memoria completa."""
        preferencias.registrar_reciente(self.preferencias, id_calculadora)
        self._actualizar_listas()
        return self._abrir(id_calculadora)

    def _abrir(self, id_calculadora: str):
        aplicacion = APLICACIONES_POR_ID.get(id_calculadora)
        if aplicacion and aplicacion.carpeta:
            proceso = self.procesos.get(id_calculadora)
            if proceso is not None and proceso.poll() is None:
                messagebox.showinfo("Aplicación en ejecución", f"{aplicacion.nombre} se está abriendo "
                                    "o ya está abierta. Puede volver a su ventana desde la barra de tareas.",
                                    parent=self.raiz)
                return proceso
            try:
                proceso = abrir_externa(aplicacion)
            except (OSError, ValueError) as error:
                messagebox.showerror("No se pudo abrir", str(error), parent=self.raiz)
                return None
            anterior = self._vigias.pop(id_calculadora, None)
            if anterior:
                self.after_cancel(anterior)
            self.procesos[id_calculadora] = proceso
            self._vigilar_aplicacion(id_calculadora, proceso)
            return proceso
        ventana = self.ventanas.get(id_calculadora)
        if ventana is not None and ventana.winfo_exists():
            ventana.deiconify()
            ventana.lift()
            return ventana
        if id_calculadora in MEMORIAS_POR_ID:
            from ..memorias.lanzador import abrir_memoria

            ventana = abrir_memoria(self.raiz, id_calculadora)
        elif aplicacion:
            ventana = abrir_nativa(self.raiz, aplicacion)
        else:
            ventana = VentanaCalculadora(self.raiz, POR_ID[id_calculadora])
        self.ventanas[id_calculadora] = ventana
        return ventana

    def _vigilar_aplicacion(self, identificador, proceso):
        """Recoge errores del proceso sin hacer esperar al menú durante los imports de HVAC."""
        if self.procesos.get(identificador) is not proceso:
            return
        codigo = proceso.poll()
        if codigo is None:
            self._vigias[identificador] = self.after(
                250, lambda: self._vigilar_aplicacion(identificador, proceso))
            return
        self._vigias.pop(identificador, None)
        mensaje = proceso.mensaje_error() if codigo and hasattr(proceso, "mensaje_error") else ""
        if hasattr(proceso, "cerrar_registro"):
            proceso.cerrar_registro()
        if codigo:
            messagebox.showerror("Error de HVAC industrial", mensaje or
                                 "La aplicación terminó con un error.", parent=self.raiz)

    def destroy(self):
        for token in self._vigias.values():
            try:
                self.after_cancel(token)
            except tk.TclError:
                pass
        self._vigias.clear()
        super().destroy()

    def abrir_caso(self) -> None:
        ruta = filedialog.askopenfilename(parent=self.raiz, filetypes=[("Caso de cálculo", "*.json")])
        if not ruta:
            return
        try:
            with open(ruta, encoding="utf-8") as archivo:
                cabecera = json.load(archivo)
            if not isinstance(cabecera, dict):
                raise ValueError("El archivo no es un caso de cálculo RMR.")
            if cabecera.get("formato") == "RMR-memoria":
                from ..memorias import reportes as reportes_memorias

                datos = reportes_memorias.abrir_caso(ruta)
            else:
                datos = reportes.abrir_caso(ruta)
        except (OSError, ValueError) as e:
            messagebox.showerror("No se pudo abrir", str(e), parent=self.raiz)
            return
        if datos["calculadora"] not in {*POR_ID, *MEMORIAS_POR_ID}:
            messagebox.showerror("Calculadora desconocida", f"«{datos['calculadora']}» no existe en esta versión.",
                                 parent=self.raiz)
            return
        self.abrir(datos["calculadora"]).cargar_caso(ruta)

    def ver_historial(self) -> "VentanaHistorial":
        return VentanaHistorial(self)

    def editar_proyecto(self):
        from .ventana import DialogoProyecto, establecer_proyecto, proyecto_actual

        return DialogoProyecto(self.raiz, proyecto_actual(), establecer_proyecto)

    def abrir_registro(self, registro: dict) -> VentanaCalculadora | None:
        """Abre la calculadora de un registro del historial con sus datos de entrada y recalcula."""
        if registro.get("calculadora") not in POR_ID:
            messagebox.showerror("Calculadora desconocida",
                                 f"«{registro.get('calculadora')}» no existe en esta versión.", parent=self.raiz)
            return None
        ventana = self.abrir(registro["calculadora"])
        ventana.restaurar_defectos()
        ventana.asignar(registro["entradas"])
        ventana.calcular()
        return ventana

    def niveles(self) -> "DialogoNiveles":
        return DialogoNiveles(self.raiz)

    def documentacion(self) -> None:
        webbrowser.open((RAIZ / "docs").as_uri())

    def acerca_de(self) -> None:
        messagebox.showinfo("Acerca de", f"Calculadoras de Ingeniería RMR — versión {__version__}\n\n{reportes.AVISO}",
                            parent=self.raiz)

    def salir(self) -> None:
        if messagebox.askyesno("Salir", "¿Desea salir del programa?", parent=self.raiz):
            self.raiz.destroy()


def registrar_error(exc: BaseException) -> Path:
    """Escribe la traza completa en registro/errores.log y devuelve la ruta del archivo."""
    import logging
    import traceback

    from ..nucleo.historial import carpeta_registro

    carpeta = carpeta_registro()
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta = carpeta / "errores.log"
    registro = logging.getLogger("calculadoras")
    if not registro.handlers:
        manejador = logging.FileHandler(ruta, encoding="utf-8")
        manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        registro.addHandler(manejador)
        registro.setLevel(logging.INFO)
    registro.error("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    return ruta


def _manejar_excepcion(raiz: tk.Misc):
    """Muestra al usuario los errores no previstos de la interfaz y los registra (no se pierden en silencio)."""

    def manejar(tipo, valor, traza):
        valor.__traceback__ = traza
        ruta = registrar_error(valor)
        if isinstance(valor, ImportError):
            from ..nucleo.rutas import empaquetado

            ayuda = ("Extraiga nuevamente el ZIP completo de ENGICALC en una carpeta nueva."
                     if empaquetado() else "Ejecute INSTALAR.bat (o: py -m pip install -r requirements.txt) "
                     "y vuelva a abrir el programa.")
            mensaje = f"Falta una biblioteca: {valor.name or valor}.\n\n{ayuda}"
        else:
            mensaje = f"{tipo.__name__}: {valor}\n\nEl detalle quedó registrado en:\n{ruta}"
        try:  # el aviso aparece sobre la ventana en la que se trabajaba, no sobre el menú
            enfocado = raiz.focus_get()
            padre = enfocado.winfo_toplevel() if enfocado is not None else raiz
        except (KeyError, tk.TclError):
            padre = raiz
        messagebox.showerror("Error inesperado", mensaje, parent=padre)

    return manejar


def iniciar(id_calculadora: str | None = None, pedir_acceso: bool = True) -> None:
    from .acceso import solicitar_acceso

    raiz = tk.Tk()
    raiz.report_callback_exception = _manejar_excepcion(raiz)
    tema.aplicar(raiz)  # sistema visual ENGICALC v1 (sobre el tema «clam» de ttk)
    raiz.withdraw()
    if pedir_acceso and not solicitar_acceso(raiz):
        raiz.destroy()
        return
    raiz.deiconify()
    menu = MenuPrincipal(raiz)
    raiz.protocol("WM_DELETE_WINDOW", menu.salir)
    if id_calculadora:
        menu.abrir(id_calculadora)
    raiz.mainloop()


class VentanaHistorial(tema.DialogoBase):
    """Lista de los últimos cálculos (registro/historial.jsonl); doble clic reabre el cálculo."""

    def __init__(self, menu: "MenuPrincipal"):
        super().__init__(menu.raiz, "Historial de cálculos",
                         "Últimos cálculos registrados con sus datos de entrada. Doble clic reabre el cálculo.",
                         ancho_texto=760)
        from ..nucleo import historial

        self.menu = menu
        self.geometry(f"{tema._px(self, 900)}x{tema._px(self, 460)}")
        self.registros = historial.leer(500)
        columnas = ("fecha", "calculadora", "proyecto", "documento", "version")
        self.tabla = ttk.Treeview(self.cuerpo, columns=columnas, show="headings", selectmode="browse")
        for col, titulo, ancho in (("fecha", "Fecha", 150), ("calculadora", "Calculadora", 230),
                                   ("proyecto", "Proyecto", 230), ("documento", "Documento", 150),
                                   ("version", "Versión", 70)):
            self.tabla.heading(col, text=titulo.upper())
            self.tabla.column(col, width=tema._px(self, ancho), anchor="w")
        barra = ttk.Scrollbar(self.cuerpo, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        for i, reg in enumerate(self.registros):
            proyecto = reg.get("proyecto") or {}
            self.tabla.insert("", "end", iid=str(i), values=(
                reg.get("fecha", "").replace("T", " "), reg.get("nombre", reg.get("calculadora")),
                proyecto.get("proyecto", ""), proyecto.get("documento", ""), reg.get("version", "")))
        self.tabla.bind("<Double-1>", lambda _e: self.abrir())
        self.tabla.bind("<Return>", lambda _e: self.abrir())
        texto = f"{len(self.registros)} cálculos registrados." if self.registros else "Aún no hay cálculos registrados."
        self.boton("Abrir cálculo", self.abrir, primario=True)
        self.boton("Cerrar", self.destroy)
        tema.etiqueta(self.botones, texto, "pequeno", tema.TEXTO_2, tema.SUPERFICIE_2).pack(side="left")

    def abrir(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            return None
        return self.menu.abrir_registro(self.registros[int(seleccion[0])])


class DialogoNiveles(tema.DialogoBase):
    """Niveles de confianza de los resultados (mismo texto que el aviso anterior)."""

    def __init__(self, padre: tk.Misc):
        super().__init__(padre, "Niveles de confianza")
        self.resizable(False, False)
        self.transient(padre)
        for nivel, nombre in NIVELES.items():
            fila = tk.Frame(self.cuerpo, background=tema.SUPERFICIE)
            fila.pack(fill="x", pady=3)
            tema.insignia_nivel(fila, nivel).pack(side="left", padx=(0, 10))
            tema.etiqueta(fila, nombre, "cuerpo", tema.TEXTO, tema.SUPERFICIE).pack(side="left")
        aviso = tema.Aviso(self.cuerpo, "advertencia", "Los resultados de nivel O provienen de tablas o criterios "
                           "del programa original sin fuente identificada: verifíquelos con el fabricante o la "
                           "norma aplicable.", titulo="Nivel O")
        aviso.configure(width=tema._px(self, 380))
        aviso.pack(fill="x", pady=(12, 0))
        self.boton("Aceptar", self.destroy, primario=True)
