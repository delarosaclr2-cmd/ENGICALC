"""Ventana común de las calculadoras: datos a la izquierda; pestañas Resultados, Esquema y Memoria a la derecha.

- El cálculo se repite solo 0.5 s después de cambiar un dato (si los datos son válidos); con datos
  incompletos se conserva el último resultado y la barra de estado indica el problema.
- Memoria PDF, impresión, Excel y copia de resultados se generan SIEMPRE de los datos actuales
  (se recalcula antes de exportar), para que un reporte nunca mezcle entradas y resultados.
- La ventana no contiene fórmulas: llama a la función `evaluar(caso) -> Memoria` de cada calculadora.
- Sistema visual ENGICALC v1 (``ui/tema.py``, copia idéntica de ``calculadoras/interfaz/tema.py`` para que la
  aplicación también funcione sola desde su carpeta): solo apariencia; textos, cálculos y memorias no cambian.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import memoria_pdf, tema
from .dibujo import LienzoTk

RECURSOS = memoria_pdf.RECURSOS
# Unidades que, al final de una etiqueta «Nombre (unidad)», pasan a la pastilla de unidad del rediseño
UNIDADES_PASTILLA = {"m", "mm", "m/s", "°C", "kPa", "kPa a", "%", "cP", "cSt", "in/año", "años", "min", "kW",
                     "kJ/kWh", "kJ/kg", "psia", "m³", "kg/h", "kg/m³"}
COLOR_ESTADO = {"CUMPLE": tema.TONOS["correcto"]["fondo"], "NO CUMPLE": tema.TONOS["critico"]["fondo"],
                "INFORMATIVO": tema.TONOS["advertencia"]["fondo"], "NO EVALUABLE": tema.DESHABILITADO,
                "actual": tema.AZUL_50}


def _separar_unidad(etiqueta):
    """«Longitud (m)» -> («Longitud», «m»). Un paréntesis que no es una unidad simple queda en la etiqueta."""
    m = re.match(r"^(.*\S)\s+\(([^()]+)\)$", etiqueta)
    if m and m.group(2).strip() in UNIDADES_PASTILLA:
        return m.group(1), m.group(2).strip()
    return etiqueta, ""


def _get(d, ruta):
    for p in ruta.split("."):
        if not isinstance(d, dict):
            return None
        d = d.get(p)
    return d


def _set(d, ruta, valor):
    partes = ruta.split(".")
    for p in partes[:-1]:
        if not isinstance(d.get(p), dict):
            d[p] = {}
        d = d[p]
    if valor is None:
        d.pop(partes[-1], None)
    else:
        d[partes[-1]] = valor


class Ventana(ttk.Frame):
    RETARDO_MS = 500

    def __init__(self, master, titulo, secciones, tablas, caso_inicial, evaluar, dir_casos=None):
        super().__init__(master, padding=6)
        self.master, self.secciones, self.tablas = master, secciones, tablas
        self.evaluar, self.dir_casos = evaluar, dir_casos
        self.campos = [c for _, cs in secciones for c in cs]
        self.vars, self.textos = {}, {}
        self.memoria = None
        self._pendiente = None
        self._cargando = False
        self.titulo = titulo
        tema.aplicar(master)
        master.configure(background=tema.FONDO)
        master.title(titulo)
        try:
            master.iconbitmap(os.path.join(RECURSOS, "rmr.ico"))
        except tk.TclError:
            pass
        master.geometry(f"{min(1440, master.winfo_screenwidth() - 40)}x{min(900, master.winfo_screenheight() - 90)}")
        self.configure(style="TFrame", padding=0)
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        self._construir()
        self.poner(caso_inicial)

    # ---------------------------------------------------------------- construcción
    def _construir(self):
        nombre = self.titulo.split(" — ")[0]
        raiz = self.master._root()
        volver = None if raiz is self.master else (lambda: (raiz.deiconify(), raiz.lift()))
        logo = os.path.join(RECURSOS, "logo_rmr.png")
        tema.encabezado_ventana(self, logo, ["Calculadoras", nombre], al_volver=volver).grid(row=0, column=0,
                                                                                         sticky="ew")
        # Título y barra de acciones: actualización automática, por eso Exportar es la acción principal
        cab = tk.Frame(self, background=tema.FONDO)
        cab.grid(row=1, column=0, sticky="ew", padx=24, pady=(16, 0))
        cab.columnconfigure(0, weight=1)
        bloque = tk.Frame(cab, background=tema.FONDO)
        bloque.grid(row=0, column=0, sticky="w")
        fila_t = tk.Frame(bloque, background=tema.FONDO)
        fila_t.pack(anchor="w")
        tema.etiqueta(fila_t, nombre, "titulo", tema.MARINO).pack(side="left")
        tema.chip(fila_t, "● Actualización automática", "correcto").pack(side="left", padx=(12, 0))
        tema.etiqueta(bloque, self.titulo, "pequeno", tema.TEXTO_2).pack(anchor="w", pady=(4, 0))
        acciones = tema.Flujo(cab, separacion=8, alinear="right")
        acciones.grid(row=0, column=1, sticky="se")
        self.boton_calcular = ttk.Button(acciones, text="Calcular", command=self.calcular)
        acciones.agregar(self.boton_calcular)
        acciones.agregar(tema.boton_menu(acciones, "Caso", [("Abrir caso…", self.abrir),
                                                            ("Guardar caso…", self.guardar)]))
        acciones.agregar(tema.boton_menu(acciones, "Exportar", [
            ("Memoria PDF…", self.memoria_pdf), ("Excel…", self.excel), ("Imprimir…", self.imprimir), None,
            ("Copiar resultados", self.copiar)], primario=True))
        self.con_esquema = tk.BooleanVar(value=True)
        acciones.agregar(ttk.Checkbutton(acciones, text="Esquema en la memoria", variable=self.con_esquema), 6)

        def ajustar(evento):
            en_linea = evento.width >= bloque.winfo_reqwidth() + acciones.ancho_natural() + 24
            fila = 0 if en_linea else 1
            if int(acciones.grid_info().get("row", -1)) != fila:
                acciones.grid_forget()
                acciones.alinear = "right" if en_linea else "left"
                acciones.grid(row=fila, column=1 if en_linea else 0, columnspan=1 if en_linea else 2,
                              sticky="se" if en_linea else "ew", pady=(0 if en_linea else 10, 0))
                acciones.after_idle(acciones.acomodar)

        cab.bind("<Configure>", ajustar)

        panel = ttk.PanedWindow(self, orient="horizontal")
        panel.grid(row=2, column=0, sticky="nsew", padx=24, pady=(14, 8))

        # Izquierda: formulario desplazable, en tarjetas por grupo
        izq = tk.Frame(panel, background=tema.FONDO)
        lienzo = tk.Canvas(izq, highlightthickness=0, width=480, background=tema.FONDO)
        barra = ttk.Scrollbar(izq, orient="vertical", command=lienzo.yview)
        cont = tk.Frame(lienzo, background=tema.FONDO)
        cont.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        ventana_form = lienzo.create_window((0, 0), window=cont, anchor="nw")
        lienzo.bind("<Configure>", lambda e: lienzo.itemconfigure(ventana_form, width=max(e.width - 6,
                                                                                          cont.winfo_reqwidth())))
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        cont.columnconfigure(0, weight=1)
        fila = 0
        for nombre_g, campos in self.secciones:
            g = tema.tarjeta(cont, padx=14, pady=10)
            g.grid(row=fila, column=0, sticky="ew", pady=(0, 10), padx=(0, 4))
            g.columnconfigure(0, weight=1)
            tema.etiqueta(g, nombre_g, "grupo", tema.MARINO, tema.SUPERFICIE, wraplength=400).grid(
                row=0, column=0, columnspan=3, sticky="w", pady=(0, 6))
            fila += 1
            for i, (ruta, etiqueta, opciones) in enumerate(campos, start=1):
                texto, unidad = _separar_unidad(etiqueta)
                tema.etiqueta(g, texto, "cuerpo", tema.TEXTO, tema.SUPERFICIE, wraplength=190).grid(
                    row=i, column=0, sticky="w", padx=(0, 8), pady=2)
                var = tk.StringVar()
                if opciones:
                    w = ttk.Combobox(g, textvariable=var, values=opciones, width=18, state="readonly",
                                     font=tema.fuente("cuerpo"))
                    w.grid(row=i, column=1, columnspan=2, sticky="ew", pady=2)
                else:
                    w = ttk.Entry(g, textvariable=var, width=17, font=tema.fuente("mono"))
                    w.grid(row=i, column=1, sticky="ew", pady=2)
                    if unidad:
                        tema.unidad(g, unidad).grid(row=i, column=2, sticky="w", padx=(8, 0))
                var.trace_add("write", lambda *a: self._programar())
                self.vars[ruta] = var
        for ruta, etiqueta in self.tablas:
            t = tema.tarjeta(cont, padx=14, pady=10)
            t.grid(row=fila, column=0, sticky="ew", pady=(0, 10), padx=(0, 4))
            t.columnconfigure(0, weight=1)
            tema.etiqueta(t, f"{etiqueta} (lista JSON)", "grupo", tema.MARINO, tema.SUPERFICIE,
                          wraplength=400).grid(row=0, column=0, sticky="w", pady=(0, 6))
            fila += 1
            txt = tk.Text(t, width=46, height=7, font=tema.fuente("mono_pequeno"), undo=True, relief="flat",
                          background=tema.SUPERFICIE_2, highlightthickness=1, highlightbackground=tema.BORDE_CONTROL,
                          highlightcolor=tema.AZUL, foreground=tema.TEXTO, insertbackground=tema.TEXTO)
            txt.grid(row=1, column=0, sticky="ew")
            txt.bind("<KeyRelease>", lambda e: self._programar())
            self.textos[ruta] = txt
        panel.add(izq, weight=1)

        # Derecha: avisos al frente, indicadores y pestañas
        der = tk.Frame(panel, background=tema.FONDO)
        der.rowconfigure(2, weight=1)
        der.columnconfigure(0, weight=1)
        self.zona_avisos = tk.Frame(der, background=tema.FONDO)
        self.zona_avisos.grid(row=0, column=0, sticky="ew")
        self.resumen = tema.tarjeta(der)
        self.resumen.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        tarjeta = tema.tarjeta(der)
        tarjeta.grid(row=2, column=0, sticky="nsew")
        self.nb = ttk.Notebook(tarjeta)
        self.nb.pack(fill="both", expand=True)

        res = ttk.Frame(self.nb, padding=8, style="Superficie.TFrame")
        res.columnconfigure(0, weight=1)
        estilo = ttk.Style(self)
        estilo.configure("Res.Treeview", rowheight=tema._px(self, 26))
        self.tv_res = self._arbol(res, 1, ("Resultado", "Valor", "Unidad / nota"), (300, 230, 260), 12)
        self.tv_ver = self._arbol(res, 2, ("Criterio", "Valor", "Límite", "Estado", "Referencia"), (240, 110, 110, 95, 240), 6)
        self.tv_ver.tag_configure("CUMPLE", background=COLOR_ESTADO["CUMPLE"])
        self.tv_ver.tag_configure("NO CUMPLE", background=COLOR_ESTADO["NO CUMPLE"])
        self.tv_ver.tag_configure("INFORMATIVO", background=COLOR_ESTADO["INFORMATIVO"])
        # NO EVALUABLE: el criterio quedó fuera del dominio del método. No es un aprobado ni un
        # rechazo, así que no puede quedar sin color y parecer un renglón cualquiera.
        self.tv_ver.tag_configure("NO EVALUABLE", background=COLOR_ESTADO["NO EVALUABLE"])
        self.tv_adv = self._arbol(res, 3, ("Advertencias",), (790,), 4)
        res.rowconfigure(1, weight=3)
        self.nb.add(res, text="Resultados")

        esq = ttk.Frame(self.nb, style="Superficie.TFrame")
        self.lienzo = LienzoTk(esq)
        self.lienzo.marco.pack(fill="both", expand=True)
        self.nb.add(esq, text="Esquema")

        # Pestaña de tablas (barridos de diámetro, capacidad, presión máxima): se arma en cada cálculo
        tab = ttk.Frame(self.nb, style="Superficie.TFrame")
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        lz = tk.Canvas(tab, highlightthickness=0, background=tema.SUPERFICIE)
        sb_t = ttk.Scrollbar(tab, orient="vertical", command=lz.yview)
        self.cont_tablas = ttk.Frame(lz, style="Superficie.TFrame")
        self.cont_tablas.bind("<Configure>", lambda e: lz.configure(scrollregion=lz.bbox("all")))
        self._ventana_tablas = lz.create_window((0, 0), window=self.cont_tablas, anchor="nw")
        lz.bind("<Configure>", lambda e: lz.itemconfigure(self._ventana_tablas, width=e.width))
        lz.configure(yscrollcommand=sb_t.set)
        lz.grid(row=0, column=0, sticky="nsew")
        sb_t.grid(row=0, column=1, sticky="ns")
        self.nb.add(tab, text="Tablas")
        self.tab_tablas = tab

        mem = ttk.Frame(self.nb, style="Superficie.TFrame")
        self.txt_mem = tk.Text(mem, wrap="word", font=tema.fuente("mono_pequeno"), relief="flat", borderwidth=0,
                               highlightthickness=0, padx=14, pady=12, foreground=tema.TEXTO,
                               background=tema.SUPERFICIE)
        sb = ttk.Scrollbar(mem, command=self.txt_mem.yview)
        self.txt_mem.configure(yscrollcommand=sb.set)
        self.txt_mem.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.nb.add(mem, text="Memoria (texto)")
        panel.add(der, weight=3)

        # Descargo y barra de estado
        aviso = tema.etiqueta(self, memoria_pdf.AVISO, "pequeno", tema.TEXTO_2, wraplength=1300)
        aviso.grid(row=3, column=0, sticky="ew", padx=24, pady=(0, 6))
        self.bind("<Configure>", lambda e: aviso.configure(wraplength=max(400, e.width - 48)), add="+")
        self.estado = tema.BarraEstado(self, "")
        self.estado.grid(row=4, column=0, sticky="ew")

    def _arbol(self, padre, fila, cols, anchos, alto):
        marco = ttk.Frame(padre, style="Superficie.TFrame")
        marco.grid(row=fila, column=0, sticky="nsew", pady=3)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)
        tv = ttk.Treeview(marco, columns=cols, show="headings", height=alto, style="Res.Treeview")
        for c, w in zip(cols, anchos):
            tv.heading(c, text=c.upper(), anchor="w")
            tv.column(c, width=w, anchor="w", stretch=True)
        sb = ttk.Scrollbar(marco, command=tv.yview)
        tv.configure(yscrollcommand=sb.set)
        tv.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        return tv

    # ---------------------------------------------------------------- caso <-> formulario
    def poner(self, caso):
        self._cargando = True
        self.base = json.loads(json.dumps(caso))
        for ruta, var in self.vars.items():
            v = _get(caso, ruta)
            var.set("" if v is None else (f"{v:.12g}" if isinstance(v, float) else str(v)))
        for ruta, txt in self.textos.items():
            txt.delete("1.0", "end")
            txt.insert("1.0", json.dumps(_get(caso, ruta) or [], ensure_ascii=False, indent=1))
        self._cargando = False
        self.recalcular(silencioso=True)

    def _es_combo(self, ruta):
        return any(r == ruta and op for r, _, op in self.campos)

    def leer(self):
        caso = json.loads(json.dumps(self.base))
        for ruta, var in self.vars.items():
            s = var.get().strip()
            if s == "":
                _set(caso, ruta, None)
                continue
            if isinstance(_get(self.base, ruta), str) or self._es_combo(ruta):
                v = s
            else:
                try:
                    v = float(s.replace(",", "."))
                except ValueError:
                    v = s
            _set(caso, ruta, v)
        for ruta, txt in self.textos.items():
            try:
                _set(caso, ruta, json.loads(txt.get("1.0", "end") or "[]"))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Tabla '{ruta}': JSON inválido ({exc.msg}, renglón {exc.lineno})") from exc
        return caso

    # ---------------------------------------------------------------- cálculo
    def _programar(self):
        if self._cargando:
            return
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self._pendiente = self.after(self.RETARDO_MS, lambda: self.recalcular(silencioso=True))

    def recalcular(self, silencioso=False):
        self._pendiente = None
        try:
            m = self.evaluar(self.leer())
        except Exception as exc:   # se informa al usuario; el motor valida tipos y rangos
            self.estado.configure(text=f"Datos incompletos o inválidos: {exc}  (se conserva el último resultado)",
                                  foreground=tema.ERROR)
            if not silencioso:
                messagebox.showerror("Dato inválido", str(exc), parent=self.master)
            return None
        self.memoria = m
        self._presentar(m)
        self.estado.configure(text=f"Resultados actualizados {_dt.datetime.now():%H:%M:%S} · huella {m.huella}",
                              foreground=tema.CORRECTO)
        return m

    def calcular(self):
        return self.recalcular(silencioso=False)

    def _presentar(self, m):
        for w in self.resumen.winfo_children():
            w.destroy()
        for i, (et, val) in enumerate(m.resumen[:6]):
            f = tk.Frame(self.resumen, background=tema.SUPERFICIE, padx=16, pady=10)
            f.grid(row=i // 3, column=i % 3, sticky="nw")
            self.resumen.columnconfigure(i % 3, weight=1, uniform="kpi")
            tema.etiqueta(f, et, "pequeno", tema.TEXTO_2, tema.SUPERFICIE, wraplength=260).pack(anchor="w")
            tema.etiqueta(f, val, "mono_negrita", tema.MARINO, tema.SUPERFICIE, wraplength=260).pack(anchor="w",
                                                                                                    pady=(2, 0))
        for w in self.zona_avisos.winfo_children():
            w.destroy()
        if m.advertencias:
            tema.Aviso(self.zona_avisos, "advertencia", [str(a) for a in m.advertencias],
                       titulo="Advertencia" if len(m.advertencias) == 1 else "Advertencias",
                       max_lineas=4).pack(fill="x", pady=(0, 12))
        for tv, filas in ((self.tv_res, m.resultados), (self.tv_ver, m.verificaciones),
                          (self.tv_adv, [(a,) for a in m.advertencias])):
            tv.delete(*tv.get_children())
            for f in filas:
                tag = (f[3],) if tv is self.tv_ver else ()
                tv.insert("", "end", values=[str(x) for x in f], tags=tag)
        self._poner_tablas(m.tablas)
        if m.escena is not None:
            self.lienzo.mostrar(m.escena, conservar_vista=True)
        self.txt_mem.configure(state="normal")
        self.txt_mem.delete("1.0", "end")
        self.txt_mem.insert("1.0", m.a_texto())
        self.txt_mem.configure(state="disabled")

    def _poner_tablas(self, tablas):
        """Rearma la pestaña Tablas con las tablas que devolvió la memoria."""
        for w in self.cont_tablas.winfo_children():
            w.destroy()
        if not tablas:
            ttk.Label(self.cont_tablas, text="Este caso no genera tablas auxiliares.", style="Superficie.TLabel",
                      foreground=tema.TEXTO_2, padding=12).grid(row=0, column=0, sticky="w")
            return
        self.cont_tablas.columnconfigure(0, weight=1)
        for i, (tit, enc, filas, *_) in enumerate(tablas):
            g = ttk.LabelFrame(self.cont_tablas, text=tit, padding=8)
            g.grid(row=i, column=0, sticky="ew", padx=8, pady=6)
            g.columnconfigure(0, weight=1)
            tv = ttk.Treeview(g, columns=list(enc), show="headings", height=min(len(filas) + 1, 20),
                              style="Res.Treeview")
            for c in enc:
                tv.heading(c, text=str(c).upper(), anchor="w")
                tv.column(c, width=max(70, min(300, int(len(str(c)) * 9 + 46))), anchor="w", stretch=True)
            for tag, col in COLOR_ESTADO.items():
                tv.tag_configure(tag, background=col)
            ESTADOS = ("CUMPLE", "NO CUMPLE", "INFORMATIVO", "NO EVALUABLE")
            for f in filas:
                celdas = [str(x) for x in f]
                tag = next((c for c in celdas if c in ESTADOS), None)
                if tag is None and any(x.startswith("no evaluable") for x in celdas):
                    tag = "NO EVALUABLE"
                if celdas and celdas[0].endswith(" *"):
                    tag = "actual"
                tv.insert("", "end", values=celdas, tags=(tag,) if tag else ())
            tv.grid(row=0, column=0, sticky="ew")

    # ---------------------------------------------------------------- archivo
    def abrir(self, ruta=None):
        ruta = ruta or filedialog.askopenfilename(initialdir=self.dir_casos, filetypes=[("Caso", "*.json")],
                                                  parent=self.master)
        if ruta:
            with open(ruta, encoding="utf-8") as fh:
                self.poner(json.load(fh))

    def guardar(self, ruta=None):
        ruta = ruta or filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Caso", "*.json")],
                                                    parent=self.master)
        if ruta:
            with open(ruta, "w", encoding="utf-8") as fh:
                json.dump(self.leer(), fh, indent=2, ensure_ascii=False)
        return ruta

    def _fresca(self):
        """Recalcula con los datos actuales; None si no son válidos."""
        return self.recalcular(silencioso=False)

    def memoria_pdf(self, ruta=None):
        m = self._fresca()
        if m is None:
            return None
        ruta = ruta or filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
                                                    initialfile=f"Memoria {m.titulo} - {m.caso}.pdf"[:120],
                                                    parent=self.master)
        if ruta:
            memoria_pdf.exportar_pdf(m, ruta, self.con_esquema.get())
            self.estado.configure(text=f"Memoria guardada: {ruta}", foreground=tema.CORRECTO)
        return ruta

    def excel(self, ruta=None):
        m = self._fresca()
        if m is None:
            return None
        ruta = ruta or filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                    parent=self.master)
        if ruta:
            memoria_pdf.exportar_excel(m, ruta)
            self.estado.configure(text=f"Excel guardado: {ruta}", foreground=tema.CORRECTO)
        return ruta

    def imprimir(self):
        m = self._fresca()
        if m is None:
            return None
        try:
            ruta = memoria_pdf.imprimir(m)
        except Exception as exc:   # p. ej. sin impresora o sin visor de PDF
            messagebox.showerror("Imprimir", f"No se pudo imprimir: {exc}", parent=self.master)
            return None
        self.estado.configure(text=f"Memoria enviada a imprimir ({ruta})", foreground=tema.CORRECTO)
        return ruta

    def copiar(self):
        m = self._fresca()
        if m is None:
            return None
        self.clipboard_clear()
        self.clipboard_append(m.a_texto())
        self.estado.configure(text="Resultados copiados al portapapeles", foreground=tema.CORRECTO)
        return m
