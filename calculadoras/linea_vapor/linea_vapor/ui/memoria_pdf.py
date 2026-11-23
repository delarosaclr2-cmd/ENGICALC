"""Memoria de cálculo: estructura común, PDF (reportlab), Excel (openpyxl) y texto.

Cada calculadora llena un objeto Memoria con los resultados de SU motor; este módulo solo da formato.
"""
from __future__ import annotations

import datetime as _dt
import os
from dataclasses import dataclass, field
from typing import List, Optional

RECURSOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recursos")
EMPRESA = "Ingeniería Industrial y Automatización RMR S.A. de C.V."
AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un "
         "ingeniero responsable ni constituyen una validación del proyecto.")


@dataclass
class Memoria:
    titulo: str
    caso: str
    version: str
    huella: str
    documento: str = ""
    objetivo: str = ""
    datos: List[tuple] = field(default_factory=list)            # (parámetro, valor, nota)
    resultados: List[tuple] = field(default_factory=list)       # (resultado, valor, nota)
    verificaciones: List[tuple] = field(default_factory=list)   # (criterio, valor, límite, estado, referencia)
    advertencias: List[str] = field(default_factory=list)
    ecuaciones: List[str] = field(default_factory=list)
    sustitucion: List[str] = field(default_factory=list)
    supuestos: List[str] = field(default_factory=list)
    referencias: List[str] = field(default_factory=list)
    notas: str = ""
    escena: object = None                                       # dibujo.Escena
    fecha: str = field(default_factory=lambda: _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    resumen: List[tuple] = field(default_factory=list)          # (etiqueta, valor) destacados
    tablas: List[tuple] = field(default_factory=list)           # (título, encabezados, filas, anchos_cm)

    # ---------------------------------------------------------------- texto
    def a_texto(self) -> str:
        l = [f"{self.titulo.upper()} — {self.caso}", f"{self.documento}".strip(),
             f"v{self.version} | {self.fecha} | huella de entradas {self.huella}", ""]
        def bloque(t, filas):
            if filas:
                l.append(t)
                l.extend(f"  {a}: {b}" + (f"  [{c}]" if c else "") for a, b, c in filas)
                l.append("")
        bloque("DATOS DE ENTRADA", self.datos)
        bloque("RESULTADOS", self.resultados)
        for tit, enc, filas, *_ in self.tablas:
            l.append(tit.upper())
            anchos = [max(len(str(enc[i])), *(len(str(f[i])) for f in filas)) if filas else len(str(enc[i]))
                      for i in range(len(enc))]
            l.append("  " + " | ".join(str(h).ljust(a) for h, a in zip(enc, anchos)))
            l.append("  " + "-+-".join("-" * a for a in anchos))
            l.extend("  " + " | ".join(str(c).ljust(a) for c, a in zip(f, anchos)) for f in filas)
            l.append("")
        if self.verificaciones:
            l.append("VERIFICACIONES")
            l.extend(f"  [{e}] {c}: {v} (límite {lim}) — {r}" for c, v, lim, e, r in self.verificaciones)
            l.append("")
        if self.advertencias:
            l.append("ADVERTENCIAS")
            l.extend(f"  - {a}" for a in self.advertencias)
            l.append("")
        l.append(AVISO)
        return "\n".join(x for x in l if x is not None)


# ---------------------------------------------------------------- PDF
_FUENTES = False


def registrar_fuentes():
    global _FUENTES
    if _FUENTES:
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(RECURSOS, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(RECURSOS, "DejaVuSans-Bold.ttf")))
    from reportlab.lib.fonts import addMapping
    addMapping("DejaVu", 0, 0, "DejaVu")
    addMapping("DejaVu", 1, 0, "DejaVu-Bold")
    _FUENTES = True


def exportar_pdf(m: Memoria, ruta: str, incluir_esquema=True) -> str:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_JUSTIFY
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

    registrar_fuentes()
    base = ParagraphStyle("b", fontName="DejaVu", fontSize=8.6, leading=11, alignment=TA_JUSTIFY)
    celda = ParagraphStyle("c", parent=base, fontSize=7.8, leading=9.6, alignment=0)
    h1 = ParagraphStyle("h1", parent=base, fontName="DejaVu-Bold", fontSize=11.5, leading=14, spaceBefore=8,
                        spaceAfter=4, textColor=colors.HexColor("#1F3864"), alignment=0)
    tit = ParagraphStyle("t", parent=h1, fontSize=15, leading=19, spaceBefore=0)
    esc = lambda t: (str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    P = lambda t, st=celda: Paragraph(esc(t), st)

    def tabla(enc, filas, anchos, estado_col=None):
        datos = [[Paragraph(f"<b>{esc(h)}</b>", celda) for h in enc]] + [[P(c) for c in f] for f in filas]
        t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1)
        estilo = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
                  ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#8C8C8C")),
                  ("VALIGN", (0, 0), (-1, -1), "TOP"),
                  ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
        if estado_col is not None:
            # NO EVALUABLE: fuera del dominio del método; ni aprobado ni rechazado, pero debe
            # distinguirse a simple vista de un renglón sin estado.
            for i, f in enumerate(filas, start=1):
                col = {"CUMPLE": "#DFF0D8", "NO CUMPLE": "#F8D7DA", "INFORMATIVO": "#FFF3CD",
                       "NO EVALUABLE": "#E0E0E0"}.get(f[estado_col])
                if col:
                    estilo.append(("BACKGROUND", (estado_col, i), (estado_col, i), colors.HexColor(col)))
        t.setStyle(TableStyle(estilo))
        return t

    ancho_util = letter[0] - 3.4 * cm

    def encabezado(canv, doc):
        canv.saveState()
        logo = os.path.join(RECURSOS, "logo_rmr.png")
        if os.path.exists(logo):
            canv.drawImage(logo, 1.7 * cm, letter[1] - 2.05 * cm, width=1.1 * cm, height=1.1 * cm, mask="auto")
        canv.setFont("DejaVu-Bold", 9.5)
        canv.setFillColor(colors.HexColor("#1F3864"))
        canv.drawString(3.0 * cm, letter[1] - 1.35 * cm, EMPRESA)
        canv.setFont("DejaVu", 8)
        canv.setFillColor(colors.HexColor("#555555"))
        canv.drawString(3.0 * cm, letter[1] - 1.8 * cm, f"Memoria de cálculo — {m.titulo}")
        canv.drawRightString(letter[0] - 1.7 * cm, letter[1] - 1.35 * cm, m.fecha)
        canv.setStrokeColor(colors.HexColor("#1F3864"))
        canv.setLineWidth(0.8)
        canv.line(1.7 * cm, letter[1] - 2.2 * cm, letter[0] - 1.7 * cm, letter[1] - 2.2 * cm)
        canv.setFont("DejaVu", 7)
        canv.drawString(1.7 * cm, 1.1 * cm, f"v{m.version} · huella de entradas {m.huella}")
        canv.drawRightString(letter[0] - 1.7 * cm, 1.1 * cm, f"Página {doc.page}")
        canv.restoreState()

    doc = SimpleDocTemplate(ruta, pagesize=letter, leftMargin=1.7 * cm, rightMargin=1.7 * cm, topMargin=2.6 * cm,
                            bottomMargin=1.7 * cm, title=f"Memoria de cálculo — {m.titulo}", author="RMR Ingeniería")
    E = [Paragraph(esc(m.titulo), tit), P(f"Caso: {m.caso}", base)]
    if m.documento:
        E.append(P(f"Documento de referencia: {m.documento}", base))
    E.append(Spacer(1, 4))
    if m.resumen:
        E.append(tabla(["Resultado principal", "Valor"], m.resumen, [9.5, 8.1]))
    n = 1
    def seccion(t):
        nonlocal n
        E.append(Paragraph(f"{n}. {esc(t)}", h1))
        n += 1
    if m.objetivo:
        seccion("Objetivo")
        E.append(P(m.objetivo, base))
    if m.datos:
        seccion("Datos de entrada")
        E.append(tabla(["Parámetro", "Valor", "Nota / origen"], m.datos, [5.6, 6.0, 6.0]))
    if m.supuestos:
        seccion("Supuestos")
        E += [P("• " + s, base) for s in m.supuestos]
    if incluir_esquema and m.escena is not None:
        seccion("Esquema")
        titulo = E.pop()                      # el título viaja con el dibujo (no queda huérfano al pie)
        dib = m.escena.a_reportlab(ancho_util, 12.5 * cm)
        E.append(KeepTogether([titulo, dib] + ([P(m.escena.nota, celda)] if m.escena.nota else [])))
    if m.ecuaciones:
        seccion("Ecuaciones")
        E += [P(e, base) for e in m.ecuaciones]
    if m.sustitucion:
        seccion("Sustitución de valores")
        E += [P(s, base) for s in m.sustitucion]
    if m.resultados:
        seccion("Resultados")
        E.append(tabla(["Resultado", "Valor", "Unidad / nota"], m.resultados, [7.2, 5.6, 4.8]))
    for tit, enc, filas, *resto in m.tablas:
        if not filas:
            continue
        anchos = resto[0] if resto else [ancho_util / cm / len(enc)] * len(enc)
        col_estado = len(enc) - 1 if str(enc[-1]).strip().lower() == "estado" else None
        seccion(tit)
        t = tabla(enc, filas, anchos, estado_col=col_estado)
        if len(filas) <= 18:                       # cabe en una página: el título viaja con la tabla
            E.append(KeepTogether([E.pop(), t]))
        else:
            E.append(t)
    if m.verificaciones:
        seccion("Verificaciones y criterios de aceptación")
        E.append(tabla(["Criterio", "Valor", "Límite", "Estado", "Referencia"], m.verificaciones,
                       [4.5, 2.7, 2.7, 2.7, 5.0], estado_col=3))
    if m.advertencias:
        seccion("Advertencias")
        E += [P("• " + a, base) for a in m.advertencias]
    if m.referencias:
        seccion("Referencias")
        E += [P("• " + r, base) for r in m.referencias]
    if m.notas:
        seccion("Notas del caso")
        E.append(P(m.notas, base))
    E += [Spacer(1, 10), P(AVISO, celda),
          Spacer(1, 16),
          tabla(["Elaboró", "Revisó", "Aprobó"], [["", "", ""]], [5.87, 5.87, 5.86])]
    doc.build(E, onFirstPage=encabezado, onLaterPages=encabezado)
    return ruta


# ---------------------------------------------------------------- Excel
def exportar_excel(m: Memoria, ruta: str) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    cab, rel = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3864")

    def hoja(ws, enc, filas, anchos):
        ws.append([f"{m.titulo} — {m.caso}"])
        ws["A1"].font = Font(bold=True, size=12)
        ws.append([f"{EMPRESA} | v{m.version} | {m.fecha} | huella {m.huella}"])
        ws.append([])
        ws.append(enc)
        for c in ws[4]:
            c.font, c.fill = cab, rel
        for f in filas:
            ws.append([str(x) for x in f])
        for i, a in enumerate(anchos):
            ws.column_dimensions[chr(65 + i)].width = a
        for fila in ws.iter_rows(min_row=5):
            for c in fila:
                c.alignment = Alignment(wrap_text=True, vertical="top")

    hoja(wb.active, ["Parámetro", "Valor", "Nota"], m.datos, [42, 40, 50])
    wb.active.title = "Datos"
    hoja(wb.create_sheet("Resultados"), ["Resultado", "Valor", "Unidad / nota"], m.resultados, [50, 36, 40])
    if m.verificaciones:
        hoja(wb.create_sheet("Verificaciones"), ["Criterio", "Valor", "Límite", "Estado", "Referencia"],
             m.verificaciones, [44, 18, 18, 13, 45])
    usados = set()
    for tit, enc, filas, *_ in m.tablas:
        if not filas:
            continue
        nombre = "".join(ch for ch in tit[:28] if ch not in "[]:*?/\\").strip() or "Tabla"
        while nombre in usados:
            nombre = nombre[:27] + "'"
        usados.add(nombre)
        hoja(wb.create_sheet(nombre), list(enc), filas, [max(12, min(40, len(str(h)) * 3)) for h in enc])
    hoja(wb.create_sheet("Método"), ["Contenido"],
         [(x,) for x in m.ecuaciones + [""] + m.sustitucion + [""] + [f"Advertencia: {a}" for a in m.advertencias]
          + [""] + [f"Referencia: {r}" for r in m.referencias] + ["", AVISO]], [120])
    wb.save(ruta)
    return ruta


def imprimir(m: Memoria, carpeta=None) -> str:
    """Genera la memoria en PDF y la envía a la impresora predeterminada (Windows). Si no hay
    programa asociado para imprimir PDF, la abre para imprimir desde el visor."""
    import sys
    import tempfile
    carpeta = carpeta or tempfile.gettempdir()
    ruta = os.path.join(carpeta, f"memoria_{m.huella}.pdf")
    exportar_pdf(m, ruta)
    if sys.platform.startswith("win"):
        try:
            os.startfile(ruta, "print")          # noqa: S606 (archivo generado por la propia app)
        except OSError:
            os.startfile(ruta)                   # noqa: S606
    return ruta
