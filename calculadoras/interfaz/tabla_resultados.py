"""Tabla de resultados del rediseño: valor y unidad en columnas propias, insignia de nivel por fila.

Se dibuja sobre un ``Canvas`` porque ``ttk.Treeview`` no permite colorear una sola celda: el
diseño pide la insignia de nivel con color propio en lugar de colorear la fila entera, el valor
en mono alineado a la derecha y las filas clave (KPI) con fondo sutil.

Ofrece el subconjunto de la interfaz de ``Treeview`` que usa el programa y sus pruebas
(``insert``, ``get_children``, ``item``, ``delete``, ``exists``), de modo que la lógica de la
ventana no cambia.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..nucleo.modelo import NIVELES
from . import tema

COLUMNAS = (("Resultado", None, "w"), ("Valor", 128, "e"), ("Unidad", 96, "w"), ("Nivel", 64, "center"))


class TablaResultados(tk.Frame):
    def __init__(self, padre: tk.Misc):
        super().__init__(padre, background=tema.SUPERFICIE)
        self._filas: dict[str, dict] = {}
        self._orden: list[str] = []
        self._claves: set[str] = set()
        self._contador = 0
        self._pendiente = None
        self._tip = None
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.cabecera = tk.Canvas(self, height=tema._px(self, 34), background=tema.SUPERFICIE_2,
                                  highlightthickness=0, borderwidth=0)
        self.cabecera.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.lienzo = tk.Canvas(self, background=tema.SUPERFICIE, highlightthickness=0, borderwidth=0,
                                takefocus=1)
        self.lienzo.grid(row=1, column=0, sticky="nsew")
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.barra.grid(row=1, column=1, sticky="ns")
        self.lienzo.configure(yscrollcommand=self.barra.set)
        self.lienzo.bind("<Configure>", lambda e: self._programar())
        self.lienzo.bind("<Enter>", lambda e: self._rueda(True))
        self.lienzo.bind("<Leave>", lambda e: self._rueda(False))
        self.lienzo.bind("<Up>", lambda e: self.lienzo.yview_scroll(-1, "units"))
        self.lienzo.bind("<Down>", lambda e: self.lienzo.yview_scroll(1, "units"))
        self.lienzo.bind("<Prior>", lambda e: self.lienzo.yview_scroll(-1, "pages"))
        self.lienzo.bind("<Next>", lambda e: self.lienzo.yview_scroll(1, "pages"))
        self.bind("<Destroy>", lambda e: self._rueda(False) if e.widget is self else None)

    # ------------------------------------------------ interfaz compatible con ttk.Treeview
    def insert(self, padre="", indice="end", iid=None, text="", values=(), tags=(), **_opciones) -> str:
        self._contador += 1
        iid = iid or f"I{self._contador:03d}"
        self._filas[iid] = {"text": text, "values": list(values), "tags": list(tags)}
        if indice == "end":
            self._orden.append(iid)
        else:
            self._orden.insert(int(indice), iid)
        self._programar()
        return iid

    def get_children(self, item="") -> tuple:
        return tuple(self._orden) if not item else ()

    def item(self, iid, opcion=None, **_cambios):
        datos = self._filas[iid]
        if opcion is not None:
            return datos[opcion]
        return {"text": datos["text"], "values": list(datos["values"]), "tags": list(datos["tags"]),
                "image": "", "open": 0}

    def exists(self, iid) -> bool:
        return iid in self._filas

    def delete(self, *iids) -> None:
        for iid in iids:
            self._filas.pop(iid, None)
            if iid in self._orden:
                self._orden.remove(iid)
        self._programar()

    # ------------------------------------------------ resaltado de filas clave
    def destacar(self, etiquetas) -> None:
        """Filas cuyo texto coincide con un KPI: fondo sutil y negrita."""
        self._claves = set(etiquetas)
        self._programar()

    # ------------------------------------------------ dibujo
    def _programar(self) -> None:
        if self._pendiente is None:
            self._pendiente = self.after_idle(self._dibujar)

    def _anchos(self, total: int) -> list[int]:
        fijos = [c[1] for c in COLUMNAS[1:]]
        escala = [tema._px(self, a) for a in fijos]
        return [max(tema._px(self, 160), total - sum(escala)), *escala]

    def _dibujar(self) -> None:
        self._pendiente = None
        if not self.winfo_exists():
            return
        ancho = max(self.lienzo.winfo_width(), tema._px(self, 420))
        anchos = self._anchos(ancho)
        xs = [0]
        for a in anchos:
            xs.append(xs[-1] + a)
        pad = tema._px(self, 14)

        # cabecera fija
        c = self.cabecera
        c.delete("all")
        alto_cab = int(c.cget("height"))
        c.create_line(0, alto_cab - 1, ancho + 40, alto_cab - 1, fill=tema.BORDE_CONTROL)
        for (titulo, _, ancla), x0, x1 in zip(COLUMNAS, xs, xs[1:]):
            x = {"w": x0 + pad, "e": x1 - pad, "center": (x0 + x1) / 2}[ancla]
            c.create_text(x, alto_cab / 2, text=titulo.upper(), anchor={"w": "w", "e": "e", "center": "center"}[ancla],
                          font=tema.fuente("etiqueta"), fill=tema.TEXTO_2)

        # filas
        L = self.lienzo
        L.delete("all")
        self._tip_ocultar()
        y = 0
        alto_min = tema._px(self, 32)
        for iid in self._orden:
            fila = self._filas[iid]
            clave = fila["text"] in self._claves
            fuente_n = tema.fuente("cuerpo_negrita" if clave else "cuerpo")
            nombre = L.create_text(xs[0] + pad, y + alto_min / 2, text=fila["text"], anchor="w", font=fuente_n,
                                   fill=tema.TEXTO, width=anchos[0] - 2 * pad)
            x0, y0, x1, y1 = L.bbox(nombre)
            alto = max(alto_min, (y1 - y0) + tema._px(self, 12))
            L.coords(nombre, xs[0] + pad, y + alto / 2)
            if fila.get("nota"):  # el resultado tiene nota: indicador junto al nombre, se lee al pasar el cursor
                marca = f"nota_{iid}"
                L.create_text(min(x1 + tema._px(self, 8), xs[1] - pad), y + alto / 2, text="ⓘ", anchor="w",
                              font=tema.fuente("cuerpo_negrita"), fill=tema.AZUL, tags=(marca,))
                L.tag_bind(marca, "<Enter>", lambda e, i=iid: self._tip_mostrar(i, e))
                L.tag_bind(marca, "<Leave>", lambda e: self._tip_ocultar())
            if clave:
                fondo = L.create_rectangle(0, y, ancho, y + alto, fill=tema.RESALTE, outline="")
                L.tag_lower(fondo)
            valores = [str(v) for v in fila["values"]] + ["", "", ""]
            L.create_text(xs[2] - pad, y + alto / 2, text=valores[0], anchor="e",
                          font=tema.fuente("mono_negrita" if clave else "mono"), fill=tema.TEXTO)
            L.create_text(xs[2] + pad, y + alto / 2, text=valores[1], anchor="w", font=tema.fuente("mono_pequeno"),
                          fill=tema.TEXTO_2)
            nivel = valores[2]
            if nivel in tema.NIVEL_ESTILO:
                self._insignia(L, (xs[3] + xs[4]) / 2, y + alto / 2, nivel, iid)
            L.create_line(0, y + alto - 1, ancho, y + alto - 1, fill=tema.DIVISOR_FILA)
            y += alto
        L.configure(scrollregion=(0, 0, ancho, max(y, 1)))

    def _insignia(self, L: tk.Canvas, cx: float, cy: float, nivel: str, iid: str) -> None:
        claro, oscuro, contorno = tema.NIVEL_ESTILO[nivel]
        m = tema._px(self, 11)
        etiqueta = f"nivel_{iid}"
        L.create_rectangle(cx - m, cy - m, cx + m, cy + m, fill=claro, outline=contorno or claro,
                           tags=(etiqueta,))
        L.create_text(cx, cy, text=nivel, font=tema.fuente("mono_pequeno_negrita"), fill=oscuro, tags=(etiqueta,))
        L.tag_bind(etiqueta, "<Enter>", lambda e, i=iid: self._tip_mostrar(i, e))
        L.tag_bind(etiqueta, "<Leave>", lambda e: self._tip_ocultar())

    # ------------------------------------------------ fuente del nivel al pasar el cursor
    def texto_nivel(self, iid: str) -> str:
        fila = self._filas[iid]
        nivel = str(fila["values"][2]) if len(fila["values"]) > 2 else ""
        texto = NIVELES.get(nivel, nivel)
        nota = fila.get("nota", "")
        return f"{texto}. Nota: {nota}" if nota else texto

    def nota(self, iid: str, texto: str) -> None:
        """Fuente o nota del resultado (``Salida.nota``) que se muestra junto al nivel."""
        if iid in self._filas:
            self._filas[iid]["nota"] = texto

    def _tip_mostrar(self, iid: str, evento) -> None:
        self._tip_ocultar()
        self._tip = tk.Toplevel(self)
        self._tip.wm_overrideredirect(True)
        self._tip.wm_geometry(f"+{evento.x_root - tema._px(self, 260)}+{evento.y_root + tema._px(self, 16)}")
        tk.Label(self._tip, text=self.texto_nivel(iid), font=tema.fuente("pequeno"), foreground=tema.SUPERFICIE,
                 background=tema.TEXTO, padx=10, pady=6, justify="left",
                 wraplength=tema._px(self, 280)).pack()

    def _tip_ocultar(self) -> None:
        if self._tip is not None:
            try:
                self._tip.destroy()
            except tk.TclError:
                pass
            self._tip = None

    # ------------------------------------------------ rueda del ratón solo sobre la tabla
    def _desplazar(self, evento) -> str:
        if getattr(evento, "num", None) == 4:
            pasos = -1
        elif getattr(evento, "num", None) == 5:
            pasos = 1
        else:
            pasos = -1 if evento.delta > 0 else 1
        try:
            self.lienzo.yview_scroll(pasos, "units")
        except tk.TclError:
            self._rueda(False)
        return "break"

    def _rueda(self, activa: bool) -> None:
        try:
            for secuencia in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                if activa:
                    self.bind_all(secuencia, self._desplazar)
                else:
                    self.unbind_all(secuencia)
        except tk.TclError:
            pass


def leyenda(padre: tk.Misc) -> tk.Frame:
    """Leyenda fija bajo la tabla: los cuatro niveles del programa (V, E, O, D)."""
    pie = tk.Frame(padre, background=tema.SUPERFICIE_2)
    tema.separador(pie, "horizontal", tema.DIVISOR).pack(fill="x", side="top")
    flujo = tema.Flujo(pie, separacion=14, background=tema.SUPERFICIE_2)
    flujo.pack(fill="x", padx=14, pady=8)
    flujo.agregar(tema.etiqueta(flujo, "Nivel", "pequeno_negrita", tema.TEXTO_2, tema.SUPERFICIE_2))
    for nivel, nombre in NIVELES.items():
        item = tk.Frame(flujo, background=tema.SUPERFICIE_2)
        tema.insignia_nivel(item, nivel, pequena=True).pack(side="left", padx=(0, 6))
        tema.etiqueta(item, nombre, "pequeno", tema.TEXTO_2, tema.SUPERFICIE_2).pack(side="left")
        flujo.agregar(item)
    flujo.agregar(tema.etiqueta(flujo, "Pase el cursor sobre la letra o sobre ⓘ para ver el nivel y la nota",
                                "pequeno", tema.TEXTO_2, tema.SUPERFICIE_2))
    return pie
