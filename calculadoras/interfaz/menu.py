"""Menú principal: calculadoras organizadas por disciplina, buscador y estado de auditoría.

Sustituye al «manejador de archivos» original, que abría scripts por rutas fijas
``D:\\Python\\...`` con ``subprocess`` (rutas rotas en cualquier otra PC). Aquí cada
calculadora o memoria se abre como ventana dentro del mismo proceso a partir de
el catálogo de ``calculadoras.catalogo``. HVAC industrial usa su propio proceso Qt.
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
from ..nucleo.modelo import NIVELES, VALIDACION_PENDIENTE, VALIDADA_CONDICIONES

ESTADO_CORTO = {VALIDADA_CONDICIONES: "Validada con condiciones", VALIDACION_PENDIENTE: "Validación pendiente"}
from . import reportes
from .ventana import VentanaCalculadora


BIBLIOTECAS = {"reportlab": "memoria PDF", "openpyxl": "exportar a Excel", "matplotlib": "gráficas",
               "PIL": "logotipo e imágenes de referencia"}


def bibliotecas_faltantes() -> list[str]:
    """Bibliotecas opcionales de requirements.txt que no están instaladas (el cálculo no las necesita)."""
    import importlib.util

    return [nombre for nombre in BIBLIOTECAS if importlib.util.find_spec(nombre) is None]


class MenuPrincipal(ttk.Frame):
    def __init__(self, raiz: tk.Tk):
        super().__init__(raiz, padding=10)
        self.raiz = raiz
        self.config_app = cargar()
        self.ventanas: dict[str, tk.Toplevel] = {}
        self.procesos = {}
        self._vigias = {}
        raiz.title("Calculadoras de Ingeniería RMR")
        raiz.geometry("1000x640")
        raiz.minsize(760, 480)
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
        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x")
        self._logo(cabecera)
        ttk.Label(cabecera, text="Calculadoras de Ingeniería", font=("Segoe UI", 15, "bold")).pack(side="left", padx=10)
        busqueda = ttk.Frame(self)
        busqueda.pack(fill="x", pady=(8, 4))
        ttk.Label(busqueda, text="Buscar:").pack(side="left")
        self.texto_busqueda = tk.StringVar()
        self.texto_busqueda.trace_add("write", lambda *a: self.filtrar())
        entrada = ttk.Entry(busqueda, textvariable=self.texto_busqueda, width=40)
        entrada.pack(side="left", padx=6)
        entrada.focus_set()
        ttk.Button(busqueda, text="Limpiar", command=lambda: self.texto_busqueda.set("")).pack(side="left")

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.columnconfigure(0, weight=3, uniform="col")
        cuerpo.columnconfigure(1, weight=2, uniform="col")
        cuerpo.rowconfigure(0, weight=1)
        izq = ttk.Frame(cuerpo)
        izq.grid(row=0, column=0, sticky="nsew")
        self.arbol = ttk.Treeview(izq, columns=("estado",), show="tree headings", selectmode="browse")
        self.arbol.heading("#0", text="Calculadora")
        self.arbol.heading("estado", text="Validación")
        self.arbol.column("#0", width=290, minwidth=180)
        self.arbol.column("estado", width=200, minwidth=120, stretch=False)
        self.arbol.pack(side="left", fill="both", expand=True)
        barra = ttk.Scrollbar(izq, orient="vertical", command=self.arbol.yview)
        barra.pack(side="right", fill="y")
        self.arbol.configure(yscrollcommand=barra.set)
        self.arbol.bind("<<TreeviewSelect>>", lambda e: self.describir())
        self.arbol.bind("<Double-1>", lambda e: self.abrir_seleccion())
        self.arbol.bind("<Return>", lambda e: self.abrir_seleccion())

        der = ttk.Frame(cuerpo, padding=(10, 0))
        der.grid(row=0, column=1, sticky="nsew")
        self.titulo = ttk.Label(der, text="Seleccione una calculadora", font=("Segoe UI", 12, "bold"), wraplength=360)
        self.titulo.pack(anchor="w")
        self.detalle = tk.Text(der, wrap="word", width=40, height=18, font=("Segoe UI", 9), relief="flat")
        self.detalle.pack(fill="both", expand=True, pady=6)
        self.detalle.configure(state="disabled")
        self.boton_abrir = ttk.Button(der, text="Abrir calculadora", command=self.abrir_seleccion, state="disabled")
        self.boton_abrir.pack(anchor="e")

        sitio = self.config_app["sitio"]
        self.estado = ttk.Label(self, anchor="w",
                                text=f"Versión {__version__} · {len(CALCULADORAS)} calculadoras · Sitio por defecto: "
                                     f"{sitio.get('nombre', '')} ({sitio.get('altitud_m', 0)} m) · "
                                     f"{len(HERRAMIENTAS)} herramientas disponibles")
        self.estado.pack(fill="x", pady=(6, 0))
        faltantes = bibliotecas_faltantes()
        if faltantes:
            self.aviso_bibliotecas = ttk.Label(
                self, anchor="w", foreground="#B71C1C",
                text="Faltan bibliotecas: " + ", ".join(faltantes) + ". Funciones afectadas: "
                     + "; ".join(BIBLIOTECAS[b] for b in faltantes) + ". Ejecute INSTALAR.bat.")
            self.aviso_bibliotecas.pack(fill="x")

    def _logo(self, padre) -> None:
        ruta = recurso(self.config_app["reportes"].get("logo", ""))
        if not ruta.is_file():
            return
        try:
            from PIL import Image, ImageTk

            imagen = Image.open(ruta)
            imagen.thumbnail((220, 58))
            self._foto_logo = ImageTk.PhotoImage(imagen)
            ttk.Label(padre, image=self._foto_logo).pack(side="left")
        except Exception:  # sin Pillow o imagen dañada: el menú sigue funcionando
            pass

    # ------------------------------------------------------------ lógica
    def filtrar(self) -> None:
        texto = self.texto_busqueda.get()
        visibles = {c.id for c in buscar(texto)}
        self.arbol.delete(*self.arbol.get_children())
        grupos = por_disciplina()
        for disciplina, lista in grupos.items():
            lista = [c for c in lista if c.id in visibles]
            if not lista:
                continue
            nodo = self.arbol.insert("", "end", iid=f"disciplina::{disciplina}", text=disciplina, open=True)
            for c in lista:
                self.arbol.insert(nodo, "end", iid=c.id, text=c.nombre, values=(ESTADO_CORTO.get(c.estado_validacion, c.estado_validacion),))
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
        self.detalle.configure(state="normal")
        self.detalle.delete("1.0", "end")
        if c is None:
            self.titulo.configure(text="Seleccione una calculadora")
            self.boton_abrir.configure(state="disabled")
        else:
            self.titulo.configure(text=c.nombre)
            texto = [c.descripcion, "", f"Disciplina: {c.disciplina}", f"Auditoría: {c.estado_auditoria}",
                     f"Validación: {c.estado_validacion}", "", "Limitaciones principales:"]
            texto += [f"• {li}" for li in c.limitaciones[:4]]
            texto += ["", "Sustituye a: " + ", ".join(c.archivos_originales)]
            self.detalle.insert("1.0", "\n".join(texto))
            self.boton_abrir.configure(state="normal")
        self.detalle.configure(state="disabled")

    def abrir_seleccion(self):
        c = self.seleccion()
        if c is not None:
            return self.abrir(c.id)
        return None

    def abrir(self, id_calculadora: str):
        """Abre (o trae al frente) una calculadora o memoria completa."""
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

    def niveles(self) -> None:
        messagebox.showinfo("Niveles de confianza", "\n".join(f"{k} = {v}" for k, v in NIVELES.items()) +
                            "\n\nLos resultados de nivel O provienen de tablas o criterios del programa original "
                            "sin fuente identificada: verifíquelos con el fabricante o la norma aplicable.",
                            parent=self.raiz)

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
    try:
        ttk.Style(raiz).theme_use("vista" if "vista" in ttk.Style(raiz).theme_names() else "clam")
    except tk.TclError:
        pass
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


class VentanaHistorial(tk.Toplevel):
    """Lista de los últimos cálculos (registro/historial.jsonl); doble clic reabre el cálculo."""

    def __init__(self, menu: "MenuPrincipal"):
        super().__init__(menu.raiz)
        from ..nucleo import historial

        self.menu = menu
        self.title("Historial de cálculos")
        self.geometry("900x420")
        self.registros = historial.leer(500)
        marco = ttk.Frame(self, padding=8)
        marco.pack(fill="both", expand=True)
        columnas = ("fecha", "calculadora", "proyecto", "documento", "version")
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings", selectmode="browse")
        for col, titulo, ancho in (("fecha", "Fecha", 150), ("calculadora", "Calculadora", 230),
                                   ("proyecto", "Proyecto", 230), ("documento", "Documento", 150),
                                   ("version", "Versión", 70)):
            self.tabla.heading(col, text=titulo)
            self.tabla.column(col, width=ancho, anchor="w")
        barra = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=barra.set)
        self.tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="left", fill="y")
        for i, reg in enumerate(self.registros):
            proyecto = reg.get("proyecto") or {}
            self.tabla.insert("", "end", iid=str(i), values=(
                reg.get("fecha", "").replace("T", " "), reg.get("nombre", reg.get("calculadora")),
                proyecto.get("proyecto", ""), proyecto.get("documento", ""), reg.get("version", "")))
        self.tabla.bind("<Double-1>", lambda _e: self.abrir())
        pie = ttk.Frame(self, padding=(8, 0, 8, 8))
        pie.pack(fill="x")
        texto = f"{len(self.registros)} cálculos registrados." if self.registros else "Aún no hay cálculos registrados."
        ttk.Label(pie, text=texto).pack(side="left")
        ttk.Button(pie, text="Cerrar", command=self.destroy).pack(side="right", padx=2)
        ttk.Button(pie, text="Abrir cálculo", command=self.abrir).pack(side="right", padx=2)

    def abrir(self):
        seleccion = self.tabla.selection()
        if not seleccion:
            return None
        return self.menu.abrir_registro(self.registros[int(seleccion[0])])
