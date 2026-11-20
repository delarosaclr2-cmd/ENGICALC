"""Ventana común de las calculadoras: datos a la izquierda; pestañas Resultados, Esquema y Memoria a la derecha.

- El cálculo se repite solo 0.5 s después de cambiar un dato (si los datos son válidos); con datos
  incompletos se conserva el último resultado y la barra de estado indica el problema.
- Memoria PDF, impresión, Excel y copia de resultados se generan SIEMPRE de los datos actuales
  (se recalcula antes de exportar), para que un reporte nunca mezcle entradas y resultados.
- La ventana no contiene fórmulas: llama a la función `evaluar(caso) -> Memoria` de cada calculadora.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from . import memoria_pdf
from .dibujo import LienzoTk

RECURSOS = memoria_pdf.RECURSOS


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
        master.title(titulo)
        try:
            master.iconbitmap(os.path.join(RECURSOS, "rmr.ico"))
        except tk.TclError:
            pass
        master.geometry("1360x820")
        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._construir()
        self.poner(caso_inicial)

    # ---------------------------------------------------------------- construcción
    def _construir(self):
        panel = ttk.PanedWindow(self, orient="horizontal")
        panel.grid(row=0, column=0, sticky="nsew")

        # Izquierda: formulario desplazable
        izq = ttk.Frame(panel)
        lienzo = tk.Canvas(izq, highlightthickness=0, width=470)
        barra = ttk.Scrollbar(izq, orient="vertical", command=lienzo.yview)
        cont = ttk.Frame(lienzo)
        cont.bind("<Configure>", lambda e: lienzo.configure(scrollregion=lienzo.bbox("all")))
        lienzo.create_window((0, 0), window=cont, anchor="nw")
        lienzo.configure(yscrollcommand=barra.set)
        lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        fila = 0
        for nombre, campos in self.secciones:
            g = ttk.LabelFrame(cont, text=nombre, padding=4)
            g.grid(row=fila, column=0, sticky="ew", pady=2, padx=2)
            fila += 1
            for i, (ruta, etiqueta, opciones) in enumerate(campos):
                ttk.Label(g, text=etiqueta).grid(row=i, column=0, sticky="w", padx=3, pady=1)
                var = tk.StringVar()
                if opciones:
                    w = ttk.Combobox(g, textvariable=var, values=opciones, width=24, state="readonly")
                else:
                    w = ttk.Entry(g, textvariable=var, width=26)
                w.grid(row=i, column=1, sticky="ew", padx=2)
                var.trace_add("write", lambda *a: self._programar())
                self.vars[ruta] = var
        for ruta, etiqueta in self.tablas:
            t = ttk.LabelFrame(cont, text=f"{etiqueta} (lista JSON)", padding=4)
            t.grid(row=fila, column=0, sticky="ew", pady=2, padx=2)
            fila += 1
            txt = tk.Text(t, width=58, height=7, font=("Consolas", 9), undo=True)
            txt.grid(sticky="ew")
            txt.bind("<KeyRelease>", lambda e: self._programar())
            self.textos[ruta] = txt
        panel.add(izq, weight=1)

        # Derecha: pestañas
        der = ttk.Frame(panel)
        der.rowconfigure(0, weight=1)
        der.columnconfigure(0, weight=1)
        self.nb = ttk.Notebook(der)
        self.nb.grid(row=0, column=0, sticky="nsew")

        res = ttk.Frame(self.nb, padding=4)
        res.columnconfigure(0, weight=1)
        self.resumen = ttk.Frame(res)
        self.resumen.grid(row=0, column=0, sticky="ew")
        estilo = ttk.Style(self)
        estilo.configure("Res.Treeview", rowheight=22)
        self.tv_res = self._arbol(res, 1, ("Resultado", "Valor", "Unidad / nota"), (300, 230, 260), 12)
        self.tv_ver = self._arbol(res, 2, ("Criterio", "Valor", "Límite", "Estado", "Referencia"), (240, 110, 110, 95, 240), 6)
        self.tv_ver.tag_configure("CUMPLE", background="#DFF0D8")
        self.tv_ver.tag_configure("NO CUMPLE", background="#F8D7DA")
        self.tv_ver.tag_configure("INFORMATIVO", background="#FFF3CD")
        self.tv_adv = self._arbol(res, 3, ("Advertencias",), (790,), 4)
        res.rowconfigure(1, weight=3)
        self.nb.add(res, text="Resultados")

        esq = ttk.Frame(self.nb)
        self.lienzo = LienzoTk(esq)
        self.lienzo.marco.pack(fill="both", expand=True)
        self.nb.add(esq, text="Esquema")

        # Pestaña de tablas (barridos de diámetro, capacidad, presión máxima): se arma en cada cálculo
        tab = ttk.Frame(self.nb)
        tab.rowconfigure(0, weight=1)
        tab.columnconfigure(0, weight=1)
        lz = tk.Canvas(tab, highlightthickness=0)
        sb_t = ttk.Scrollbar(tab, orient="vertical", command=lz.yview)
        self.cont_tablas = ttk.Frame(lz)
        self.cont_tablas.bind("<Configure>", lambda e: lz.configure(scrollregion=lz.bbox("all")))
        self._ventana_tablas = lz.create_window((0, 0), window=self.cont_tablas, anchor="nw")
        lz.bind("<Configure>", lambda e: lz.itemconfigure(self._ventana_tablas, width=e.width))
        lz.configure(yscrollcommand=sb_t.set)
        lz.grid(row=0, column=0, sticky="nsew")
        sb_t.grid(row=0, column=1, sticky="ns")
        self.nb.add(tab, text="Tablas")
        self.tab_tablas = tab

        mem = ttk.Frame(self.nb)
        self.txt_mem = tk.Text(mem, wrap="word", font=("Consolas", 9))
        sb = ttk.Scrollbar(mem, command=self.txt_mem.yview)
        self.txt_mem.configure(yscrollcommand=sb.set)
        self.txt_mem.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.nb.add(mem, text="Memoria (texto)")
        panel.add(der, weight=3)

        # Botones y estado
        b = ttk.Frame(self)
        b.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        for t, f in (("CALCULAR", self.calcular), ("Abrir caso", self.abrir), ("Guardar caso", self.guardar),
                     ("Memoria PDF", self.memoria_pdf), ("Imprimir", self.imprimir), ("Excel", self.excel),
                     ("Copiar resultados", self.copiar)):
            ttk.Button(b, text=t, command=f).pack(side="left", padx=2)
        self.con_esquema = tk.BooleanVar(value=True)
        ttk.Checkbutton(b, text="Esquema en la memoria", variable=self.con_esquema).pack(side="left", padx=8)
        self.estado = ttk.Label(self, text="", foreground="#555")
        self.estado.grid(row=2, column=0, sticky="ew")
        ttk.Label(self, text=memoria_pdf.AVISO, foreground="#777", wraplength=1300).grid(row=3, column=0, sticky="w")

    def _arbol(self, padre, fila, cols, anchos, alto):
        marco = ttk.Frame(padre)
        marco.grid(row=fila, column=0, sticky="nsew", pady=3)
        marco.columnconfigure(0, weight=1)
        marco.rowconfigure(0, weight=1)
        tv = ttk.Treeview(marco, columns=cols, show="headings", height=alto, style="Res.Treeview")
        for c, w in zip(cols, anchos):
            tv.heading(c, text=c, anchor="w")
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
                                  foreground="#C62828")
            if not silencioso:
                messagebox.showerror("Dato inválido", str(exc), parent=self.master)
            return None
        self.memoria = m
        self._presentar(m)
        self.estado.configure(text=f"Resultados actualizados {_dt.datetime.now():%H:%M:%S} · huella {m.huella}",
                              foreground="#2E7D32")
        return m

    def calcular(self):
        return self.recalcular(silencioso=False)

    def _presentar(self, m):
        for w in self.resumen.winfo_children():
            w.destroy()
        for i, (et, val) in enumerate(m.resumen[:6]):
            f = ttk.Frame(self.resumen, padding=(6, 2))
            f.grid(row=i // 3, column=i % 3, sticky="w")
            ttk.Label(f, text=et, foreground="#555").pack(anchor="w")
            ttk.Label(f, text=val, font=("Segoe UI", 12, "bold"), foreground="#1F3864").pack(anchor="w")
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
            ttk.Label(self.cont_tablas, text="Este caso no genera tablas auxiliares.",
                      foreground="#777", padding=8).grid(row=0, column=0, sticky="w")
            return
        self.cont_tablas.columnconfigure(0, weight=1)
        for i, (tit, enc, filas, *_) in enumerate(tablas):
            g = ttk.LabelFrame(self.cont_tablas, text=tit, padding=4)
            g.grid(row=i, column=0, sticky="ew", padx=4, pady=3)
            g.columnconfigure(0, weight=1)
            tv = ttk.Treeview(g, columns=list(enc), show="headings", height=min(len(filas) + 1, 20),
                              style="Res.Treeview")
            for c in enc:
                tv.heading(c, text=c, anchor="w")
                tv.column(c, width=max(70, min(300, int(len(str(c)) * 9 + 46))), anchor="w", stretch=True)
            for tag, col in (("CUMPLE", "#DFF0D8"), ("NO CUMPLE", "#F8D7DA"), ("INFORMATIVO", "#FFF3CD"),
                             ("actual", "#E3F2FD")):
                tv.tag_configure(tag, background=col)
            for f in filas:
                celdas = [str(x) for x in f]
                tag = next((c for c in celdas if c in ("CUMPLE", "NO CUMPLE", "INFORMATIVO")), None)
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
            self.estado.configure(text=f"Memoria guardada: {ruta}", foreground="#2E7D32")
        return ruta

    def excel(self, ruta=None):
        m = self._fresca()
        if m is None:
            return None
        ruta = ruta or filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")],
                                                    parent=self.master)
        if ruta:
            memoria_pdf.exportar_excel(m, ruta)
            self.estado.configure(text=f"Excel guardado: {ruta}", foreground="#2E7D32")
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
        self.estado.configure(text=f"Memoria enviada a imprimir ({ruta})", foreground="#2E7D32")
        return ruta

    def copiar(self):
        m = self._fresca()
        if m is None:
            return None
        self.clipboard_clear()
        self.clipboard_append(m.a_texto())
        self.estado.configure(text="Resultados copiados al portapapeles", foreground="#2E7D32")
        return m
