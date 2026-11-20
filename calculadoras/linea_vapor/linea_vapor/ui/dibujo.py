"""Escena vectorial sencilla para esquemas de ingeniería.

Una sola descripción del dibujo (en mm, eje y hacia arriba) se presenta de tres formas:
- en la ventana (tkinter.Canvas): acercar con la rueda, mover arrastrando, valores al pasar el cursor;
- en la memoria PDF (reportlab, vectorial);
- como archivo SVG.
El esquema NO calcula: recibe los resultados del motor.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from xml.sax.saxutils import escape

Punto = Tuple[float, float]

COLORES = {"tubo": "#5B7FA6", "acero": "#8A99A8", "aire": "#DCEBF7", "linea": "#1F3864", "texto": "#1A1A1A",
           "suave": "#6B6B6B", "ok": "#2E7D32", "mal": "#C62828", "aviso": "#E68A00", "banda": "#CFE8CF",
           "rejilla": "#E2E2E2", "fondo": "#FFFFFF", "acento": "#0B6FB8", "pasta": "#C9A66B", "agua": "#7FB3E6",
           "vapor": "#F2D7D5", "aceite": "#E8C872", "liquido": "#BFDBF5"}


@dataclass
class Elem:
    tipo: str                       # linea, poli, rect, circulo, texto
    puntos: List[Punto] = field(default_factory=list)
    color: str = "#1A1A1A"
    relleno: Optional[str] = None
    ancho: float = 0.35             # mm
    guion: Optional[Tuple[float, float]] = None
    flecha: bool = False            # flecha al final de una línea
    texto: str = ""
    tam: float = 3.0                # altura de letra, mm
    ancla: str = "c"                # c, w, e, n, s, nw, ne, sw, se
    negrita: bool = False
    rot: float = 0.0                # grados
    info: str = ""                  # texto al pasar el cursor


class Escena:
    def __init__(self, titulo: str = "", nota: str = ""):
        self.titulo = titulo
        self.nota = nota
        self.elems: List[Elem] = []

    # ---------------------------------------------------------------- primitivas
    def linea(self, pts, color=COLORES["linea"], ancho=0.35, guion=None, flecha=False, info=""):
        self.elems.append(Elem("linea", list(pts), color, None, ancho, guion, flecha, info=info))

    def poli(self, pts, color=COLORES["linea"], relleno=None, ancho=0.35, info=""):
        self.elems.append(Elem("poli", list(pts), color, relleno, ancho, info=info))

    def rect(self, x, y, w, h, color=COLORES["linea"], relleno=None, ancho=0.35, info=""):
        self.poli([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], color, relleno, ancho, info)

    def circulo(self, cx, cy, r, color=COLORES["linea"], relleno=None, ancho=0.35, info=""):
        self.elems.append(Elem("circulo", [(cx - r, cy - r), (cx + r, cy + r)], color, relleno, ancho, info=info))

    def texto(self, x, y, txt, tam=3.0, ancla="c", color=COLORES["texto"], negrita=False, rot=0.0, info=""):
        self.elems.append(Elem("texto", [(x, y)], color, texto=str(txt), tam=tam, ancla=ancla, negrita=negrita,
                               rot=rot, info=info))

    def flecha(self, p0, p1, color=COLORES["linea"], ancho=0.5, info=""):
        self.linea([p0, p1], color, ancho, flecha=True, info=info)

    def cota(self, p0, p1, txt, sep=4.0, tam=2.6):
        """Línea de cota paralela a p0-p1, desplazada 'sep' mm a la izquierda del sentido p0->p1."""
        dx, dy = p1[0] - p0[0], p1[1] - p0[1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L * sep, dx / L * sep
        a, b = (p0[0] + nx, p0[1] + ny), (p1[0] + nx, p1[1] + ny)
        self.linea([p0, (a[0] + nx * 0.3, a[1] + ny * 0.3)], COLORES["suave"], 0.2)
        self.linea([p1, (b[0] + nx * 0.3, b[1] + ny * 0.3)], COLORES["suave"], 0.2)
        self.linea([b, a], COLORES["suave"], 0.25, flecha=True)
        self.linea([a, b], COLORES["suave"], 0.25, flecha=True)
        ang = math.degrees(math.atan2(dy, dx))
        if ang > 90 or ang < -90:
            ang += 180
        self.texto((a[0] + b[0]) / 2 + nx * 0.45, (a[1] + b[1]) / 2 + ny * 0.45, txt, tam, "c", COLORES["suave"], rot=ang)

    # ---------------------------------------------------------------- gráficas
    def grafica(self, x0, y0, w, h, xlim, ylim, titulo="", xlabel="", ylabel="", nx=5, ny=5, fmt_x="{:g}", fmt_y="{:g}"):
        """Dibuja ejes con rejilla y devuelve la función de transformación (x, y) -> mm."""
        (xa, xb), (ya, yb) = xlim, ylim
        if xb == xa:
            xb = xa + 1
        if yb == ya:
            yb = ya + 1
        T = lambda x, y: (x0 + (x - xa) / (xb - xa) * w, y0 + (y - ya) / (yb - ya) * h)
        for i in range(nx + 1):
            xv = xa + (xb - xa) * i / nx
            px = T(xv, ya)[0]
            self.linea([(px, y0), (px, y0 + h)], COLORES["rejilla"], 0.15)
            self.texto(px, y0 - 1.5, fmt_x.format(xv), 2.3, "n", COLORES["suave"])
        ancho_tick = 0
        for j in range(ny + 1):
            yv = ya + (yb - ya) * j / ny
            ancho_tick = max(ancho_tick, len(fmt_y.format(yv)))
            py = T(xa, yv)[1]
            self.linea([(x0, py), (x0 + w, py)], COLORES["rejilla"], 0.15)
            self.texto(x0 - 1.5, py, fmt_y.format(yv), 2.3, "e", COLORES["suave"])
        self.poli([(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)], COLORES["suave"], None, 0.3)
        if titulo:
            self.texto(x0 + w / 2, y0 + h + 3.5, titulo, 3.0, "s", negrita=True)
        if xlabel:
            self.texto(x0 + w / 2, y0 - 6.5, xlabel, 2.6, "n")
        if ylabel:
            self.texto(x0 - max(12.0, 5.0 + 1.8 * ancho_tick), y0 + h / 2, ylabel, 2.6, "c", rot=90)
        return T

    # ---------------------------------------------------------------- utilidades
    def limites(self, margen=6.0):
        xs, ys = [], []
        for e in self.elems:
            for x, y in e.puntos:
                xs.append(x)
                ys.append(y)
            if e.tipo == "texto":
                x, y = e.puntos[0]
                largo = e.tam * 0.55 * max(len(e.texto), 1)
                xs += [x - largo, x + largo]
                ys += [y - e.tam, y + e.tam]
        if not xs:
            return (0, 0, 100, 60)
        return (min(xs) - margen, min(ys) - margen, max(xs) + margen, max(ys) + margen)

    def textos(self):
        return [e.texto for e in self.elems if e.tipo == "texto"]

    # ---------------------------------------------------------------- SVG
    def a_svg(self) -> str:
        x0, y0, x1, y1 = self.limites()
        w, h = x1 - x0, y1 - y0
        Y = lambda y: y1 - y + y0 - y0      # y hacia abajo en SVG
        out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.1f}mm" height="{h:.1f}mm" '
               f'viewBox="{x0:.2f} 0 {w:.2f} {h:.2f}" font-family="DejaVu Sans, Arial, sans-serif">',
               '<defs><marker id="f" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" '
               'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker></defs>',
               f'<rect x="{x0:.2f}" y="0" width="{w:.2f}" height="{h:.2f}" fill="white"/>']
        for e in self.elems:
            tit = f"<title>{escape(e.info)}</title>" if e.info else ""
            dash = f' stroke-dasharray="{e.guion[0]},{e.guion[1]}"' if e.guion else ""
            if e.tipo == "linea":
                pts = " ".join(f"{x:.2f},{Y(y):.2f}" for x, y in e.puntos)
                mk = ' marker-end="url(#f)"' if e.flecha else ""
                out.append(f'<polyline points="{pts}" fill="none" stroke="{e.color}" stroke-width="{e.ancho}"{dash}{mk}>{tit}</polyline>')
            elif e.tipo == "poli":
                pts = " ".join(f"{x:.2f},{Y(y):.2f}" for x, y in e.puntos)
                out.append(f'<polygon points="{pts}" fill="{e.relleno or "none"}" stroke="{e.color}" stroke-width="{e.ancho}">{tit}</polygon>')
            elif e.tipo == "circulo":
                (a, b), (c, d) = e.puntos
                out.append(f'<circle cx="{(a + c) / 2:.2f}" cy="{Y((b + d) / 2):.2f}" r="{(c - a) / 2:.2f}" '
                           f'fill="{e.relleno or "none"}" stroke="{e.color}" stroke-width="{e.ancho}">{tit}</circle>')
            else:
                x, y = e.puntos[0]
                anchor = {"w": "start", "nw": "start", "sw": "start", "e": "end", "ne": "end", "se": "end"}.get(e.ancla, "middle")
                dy = {"n": e.tam, "ne": e.tam, "nw": e.tam, "s": 0, "se": 0, "sw": 0}.get(e.ancla, e.tam * 0.35)
                peso = ' font-weight="bold"' if e.negrita else ""
                rot = f' transform="rotate({-e.rot:.1f} {x:.2f} {Y(y):.2f})"' if e.rot else ""
                out.append(f'<text x="{x:.2f}" y="{Y(y) + dy:.2f}" font-size="{e.tam:.2f}" fill="{e.color}" '
                           f'text-anchor="{anchor}"{peso}{rot}>{escape(e.texto)}{tit}</text>')
        out.append("</svg>")
        return "\n".join(out)

    # ---------------------------------------------------------------- reportlab (PDF vectorial)
    def a_reportlab(self, ancho_pt: float, alto_max_pt: float, fuente="DejaVu", fuente_b="DejaVu-Bold"):
        from reportlab.graphics.shapes import Circle, Drawing, Group, Line, PolyLine, Polygon, String
        from reportlab.lib.colors import HexColor
        from reportlab.pdfbase.pdfmetrics import stringWidth
        x0, y0, x1, y1 = self.limites()
        w, h = x1 - x0, y1 - y0
        s = min(ancho_pt / w, alto_max_pt / h)
        d = Drawing(w * s, h * s)
        P = lambda x, y: ((x - x0) * s, (y - y0) * s)
        for e in self.elems:
            col = HexColor(e.color)
            if e.tipo == "linea":
                pts = [c for p in e.puntos for c in P(*p)]
                d.add(PolyLine(pts, strokeColor=col, strokeWidth=e.ancho * s,
                               strokeDashArray=[e.guion[0] * s, e.guion[1] * s] if e.guion else None))
                if e.flecha and len(e.puntos) >= 2:
                    d.add(_cabeza(P(*e.puntos[-2]), P(*e.puntos[-1]), max(e.ancho * s * 5, 4), col))
            elif e.tipo == "poli":
                pts = [c for p in e.puntos for c in P(*p)]
                d.add(Polygon(pts, strokeColor=col, strokeWidth=e.ancho * s,
                              fillColor=HexColor(e.relleno) if e.relleno else None))
            elif e.tipo == "circulo":
                (a, b), (c, dd) = e.puntos
                cx, cy = P((a + c) / 2, (b + dd) / 2)
                d.add(Circle(cx, cy, (c - a) / 2 * s, strokeColor=col, strokeWidth=e.ancho * s,
                             fillColor=HexColor(e.relleno) if e.relleno else None))
            else:
                x, y = P(*e.puntos[0])
                fs = e.tam * s * 1.4
                fn = fuente_b if e.negrita else fuente
                anchor = {"w": "start", "nw": "start", "sw": "start", "e": "end", "ne": "end", "se": "end"}.get(e.ancla, "middle")
                dy = {"n": -fs * 0.8, "ne": -fs * 0.8, "nw": -fs * 0.8, "s": fs * 0.15, "se": fs * 0.15, "sw": fs * 0.15}.get(e.ancla, -fs * 0.35)
                st = String(0, dy, e.texto, fontName=fn, fontSize=fs, fillColor=col, textAnchor=anchor)
                g = Group(st)
                g.translate(x, y)
                if e.rot:
                    g.rotate(e.rot)
                d.add(g)
        return d


def _cabeza(p0, p1, tam, col):
    from reportlab.graphics.shapes import Polygon
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    a1, a2 = ang + math.radians(155), ang - math.radians(155)
    return Polygon([p1[0], p1[1], p1[0] + tam * math.cos(a1), p1[1] + tam * math.sin(a1),
                    p1[0] + tam * math.cos(a2), p1[1] + tam * math.sin(a2)], fillColor=col, strokeColor=col, strokeWidth=0.1)


class LienzoTk:
    """Presenta una Escena en un tkinter.Canvas con acercamiento, desplazamiento y valores al pasar el cursor."""

    def __init__(self, padre):
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.marco = ttk.Frame(padre)
        barra = ttk.Frame(self.marco)
        barra.pack(fill="x")
        for t, f in (("Ajustar", self.ajustar), ("Acercar +", lambda: self.zoom(1.25)), ("Alejar −", lambda: self.zoom(0.8)),
                     ("Guardar SVG…", self.guardar_svg)):
            ttk.Button(barra, text=t, command=f).pack(side="left", padx=2, pady=2)
        self.lbl = ttk.Label(barra, text="Rueda: acercar · arrastrar: mover · cursor sobre un elemento: valores",
                             foreground="#555")
        self.lbl.pack(side="left", padx=8)
        self.c = tk.Canvas(self.marco, background="white", highlightthickness=0)
        self.c.pack(fill="both", expand=True)
        self.escena: Optional[Escena] = None
        self.s, self.ox, self.oy = 1.0, 0.0, 0.0
        self._arr = None
        self._tip = None
        self.c.bind("<Configure>", lambda e: self.ajustar() if self.escena else None)
        self.c.bind("<MouseWheel>", lambda e: self.zoom(1.15 if e.delta > 0 else 1 / 1.15, e.x, e.y))
        self.c.bind("<Button-4>", lambda e: self.zoom(1.15, e.x, e.y))
        self.c.bind("<Button-5>", lambda e: self.zoom(1 / 1.15, e.x, e.y))
        self.c.bind("<ButtonPress-1>", self._ini)
        self.c.bind("<B1-Motion>", self._mov)

    # ---------------------------------------------------------------- vista
    def mostrar(self, escena: Escena, conservar_vista=False):
        nueva = self.escena is None or not conservar_vista
        self.escena = escena
        if nueva:
            self.ajustar()
        else:
            self.dibujar()

    def ajustar(self):
        if not self.escena:
            return
        x0, y0, x1, y1 = self.escena.limites()
        W, H = max(self.c.winfo_width(), 200), max(self.c.winfo_height(), 150)
        self.s = min(W / (x1 - x0), H / (y1 - y0))
        self.ox = (W - (x1 - x0) * self.s) / 2 - x0 * self.s
        self.oy = (H - (y1 - y0) * self.s) / 2 + y1 * self.s
        self.dibujar()

    def zoom(self, k, cx=None, cy=None):
        if not self.escena:
            return
        cx = self.c.winfo_width() / 2 if cx is None else cx
        cy = self.c.winfo_height() / 2 if cy is None else cy
        self.ox = cx - (cx - self.ox) * k
        self.oy = cy - (cy - self.oy) * k
        self.s *= k
        self.dibujar()

    def _ini(self, ev):
        self._arr = (ev.x, ev.y)

    def _mov(self, ev):
        if self._arr:
            self.ox += ev.x - self._arr[0]
            self.oy += ev.y - self._arr[1]
            self._arr = (ev.x, ev.y)
            self.dibujar()

    def P(self, x, y):
        return self.ox + x * self.s, self.oy - y * self.s

    # ---------------------------------------------------------------- dibujo
    def dibujar(self):
        c, s = self.c, self.s
        c.delete("all")
        if not self.escena:
            return
        for i, e in enumerate(self.escena.elems):
            tag = f"e{i}"
            w = max(e.ancho * s, 1)
            if e.tipo == "linea":
                pts = [v for p in e.puntos for v in self.P(*p)]
                c.create_line(*pts, fill=e.color, width=w, arrow="last" if e.flecha else "none",
                              arrowshape=(max(8, w * 4), max(10, w * 5), max(3, w * 1.6)),
                              dash=(max(1, int(e.guion[0] * s)), max(1, int(e.guion[1] * s))) if e.guion else (), tags=tag)
            elif e.tipo == "poli":
                pts = [v for p in e.puntos for v in self.P(*p)]
                c.create_polygon(*pts, outline=e.color, fill=e.relleno or "", width=w, tags=tag)
            elif e.tipo == "circulo":
                (a, b), (cc, d) = e.puntos
                x0, y0 = self.P(a, d)
                x1, y1 = self.P(cc, b)
                c.create_oval(x0, y0, x1, y1, outline=e.color, fill=e.relleno or "", width=w, tags=tag)
            else:
                px = max(int(round(e.tam * s * 1.05)), 6)
                if px > 200:
                    continue
                anchor = {"c": "center", "w": "w", "e": "e", "n": "n", "s": "s", "nw": "nw", "ne": "ne",
                          "sw": "sw", "se": "se"}[e.ancla]
                x, y = self.P(*e.puntos[0])
                kw = dict(text=e.texto, fill=e.color, anchor=anchor, tags=tag,
                          font=("Segoe UI", -px, "bold" if e.negrita else "normal"))
                try:
                    c.create_text(x, y, angle=e.rot, **kw)
                except self.tk.TclError:
                    c.create_text(x, y, **kw)
            if e.info:
                c.tag_bind(tag, "<Enter>", lambda ev, t=e.info: self._mostrar_tip(ev, t))
                c.tag_bind(tag, "<Leave>", lambda ev: self._ocultar_tip())

    def _mostrar_tip(self, ev, texto):
        self._ocultar_tip()
        x, y = ev.x + 14, ev.y + 10
        t = self.c.create_text(x + 6, y + 4, text=texto, anchor="nw", font=("Segoe UI", 9), fill="#111")
        b = self.c.bbox(t)
        r = self.c.create_rectangle(b[0] - 5, b[1] - 3, b[2] + 5, b[3] + 3, fill="#FFFBE6", outline="#C9A227")
        self.c.tag_raise(t, r)
        self._tip = (t, r)

    def _ocultar_tip(self):
        if self._tip:
            for i in self._tip:
                self.c.delete(i)
            self._tip = None

    def guardar_svg(self, ruta=None):
        if not self.escena:
            return None
        if ruta is None:
            from tkinter import filedialog
            ruta = filedialog.asksaveasfilename(defaultextension=".svg", filetypes=[("Dibujo SVG", "*.svg")])
        if ruta:
            with open(ruta, "w", encoding="utf-8") as fh:
                fh.write(self.escena.a_svg())
        return ruta
