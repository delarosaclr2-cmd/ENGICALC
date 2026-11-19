"""Memoria de cálculo en PDF (ReportLab).

Estructura: portada; secciones 2–21 de la especificación; DICTAMEN Y
RECOMENDACIONES DE INGENIERÍA; comparador de alternativas; recomendaciones
constructivas; Anexo A (trazabilidad: ecuación, variables, sustitución,
resultado, unidad y fuente de cada cálculo) y Anexo B (validación del software).
Numeración "Página X de Y".
"""
from __future__ import annotations

import csv
import datetime as _dt
import os
import tempfile
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer, Table, TableStyle, Image,
                                PageBreak, KeepTogether, NextPageTemplate)

from config.settings import app_root
from core.project import APP_VERSION
from core.units import display_unit, fmt
from graphics.plots import build_all, save_png, plot_alternatives
from validation.alerts import LEVEL_COLORS
from validation.decision_engine import DEC_COLORS
from . import tables as T

NAVY = colors.HexColor("#14213D")
INK = colors.HexColor("#0b0b0b")
INK2 = colors.HexColor("#52514e")
GRID = colors.HexColor("#d9d8d2")
HEAD = colors.HexColor("#eef1f6")
ACCENT = colors.HexColor("#2a78d6")

_FONTS_OK = False


def _fonts():
    global _FONTS_OK
    if _FONTS_OK:
        return
    fdir = os.path.join(app_root(), "assets", "fonts")
    pdfmetrics.registerFont(TTFont("DejaVu", os.path.join(fdir, "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", os.path.join(fdir, "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("DejaVu-Oblique", os.path.join(fdir, "DejaVuSans-Oblique.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold", italic="DejaVu-Oblique", boldItalic="DejaVu-Bold")
    _FONTS_OK = True


def _styles():
    s = {}
    s["title"] = ParagraphStyle("title", fontName="DejaVu-Bold", fontSize=22, leading=27, textColor=NAVY, spaceAfter=8)
    s["subtitle"] = ParagraphStyle("subtitle", fontName="DejaVu", fontSize=12, leading=16, textColor=INK2)
    s["h1"] = ParagraphStyle("h1", fontName="DejaVu-Bold", fontSize=13.5, leading=17, textColor=NAVY, spaceBefore=10,
                             spaceAfter=6)
    s["h2"] = ParagraphStyle("h2", fontName="DejaVu-Bold", fontSize=10.5, leading=14, textColor=INK, spaceBefore=6,
                             spaceAfter=3)
    s["body"] = ParagraphStyle("body", fontName="DejaVu", fontSize=9, leading=12.2, textColor=INK, spaceAfter=3)
    s["small"] = ParagraphStyle("small", fontName="DejaVu", fontSize=7.4, leading=9.2, textColor=INK2)
    s["cell"] = ParagraphStyle("cell", fontName="DejaVu", fontSize=7.2, leading=8.8, textColor=INK)
    s["cellb"] = ParagraphStyle("cellb", fontName="DejaVu-Bold", fontSize=7.2, leading=8.8, textColor=INK)
    s["bullet"] = ParagraphStyle("bullet", parent=s["body"], leftIndent=10, bulletIndent=2)
    s["center"] = ParagraphStyle("center", parent=s["body"], alignment=TA_CENTER)
    return s


class NumberedCanvas(rl_canvas.Canvas):
    """Canvas que escribe 'Página X de Y' al final."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved = []

    def showPage(self):
        self._saved.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._saved)
        for st in self._saved:
            self.__dict__.update(st)
            self._footer(n)
            super().showPage()
        super().save()

    def _footer(self, total):
        if self._pageNumber == 1:
            return
        w, h = self._pagesize
        self.setFont("DejaVu", 7.5)
        self.setFillColor(INK2)
        self.drawRightString(w - 15 * mm, 9 * mm, f"Página {self._pageNumber} de {total}")
        self.drawString(15 * mm, 9 * mm, getattr(self, "_footer_text", ""))
        self.setStrokeColor(GRID)
        self.setLineWidth(0.5)
        self.line(15 * mm, 12 * mm, w - 15 * mm, 12 * mm)


def _p(text, st):
    return Paragraph(escape(str(text)).replace("\n", "<br/>"), st)


def _table(hdr, rows, st, col_widths=None, font_size=None, zebra=True, first_col_colors=None):
    if not hdr:
        return _p("Sin datos.", st["small"])
    cs = st["cell"] if not font_size else ParagraphStyle("c2", parent=st["cell"], fontSize=font_size, leading=font_size + 1.6)
    hs = st["cellb"] if not font_size else ParagraphStyle("h2c", parent=st["cellb"], fontSize=font_size, leading=font_size + 1.6)
    data = [[_p(h, hs) for h in hdr]]
    for r in rows:
        cells = [_p(c, cs) for c in r]
        if first_col_colors and r and r[0] in first_col_colors:
            cells[0] = _p(r[0], ParagraphStyle("lvl", parent=hs, textColor=colors.HexColor(first_col_colors[r[0]])))
        data.append(cells)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), HEAD), ("LINEBELOW", (0, 0), (-1, 0), 0.8, NAVY),
             ("GRID", (0, 0), (-1, -1), 0.25, GRID), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LEFTPADDING", (0, 0), (-1, -1), 3), ("RIGHTPADDING", (0, 0), (-1, -1), 3),
             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    if zebra:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f8f8f6")))
    t.setStyle(TableStyle(style))
    return t


def _trace_table(steps, st, width):
    hdr = ["Cálculo", "Ecuación", "Variables", "Sustitución", "Resultado", "Fuente / tipo"]
    rows = []
    for s in steps:
        vars_ = "; ".join(v.text() for v in s.variables)
        rows.append([s.title, s.equation, vars_, s.substitution, s.result_text(), f"{s.source} [{s.kind}]"
                     + (f" — {s.notes}" if s.notes else "")])
    return _table(hdr, rows, st, [width * x for x in (0.14, 0.17, 0.2, 0.18, 0.11, 0.2)], font_size=6.5)


def _img(fig, w, tmpdir, name):
    path = os.path.join(tmpdir, f"{name}.png")
    save_png(fig, path, 170)
    from reportlab.lib.utils import ImageReader
    ir = ImageReader(path)
    iw, ih = ir.getSize()
    return Image(path, width=w, height=w * ih / iw)


def _bullets(items, st):
    return [Paragraph(escape(str(x).lstrip("• ")), st["bullet"], bulletText="•") for x in items] or [_p("—", st["body"])]


def generate_pdf(project, results, db, settings, path: str, comparison=None, include_traces: bool = True) -> str:
    """Genera la memoria de cálculo. ``comparison`` = (métricas, conclusiones) del comparador.

    Rechaza (``StaleResultsError``) resultados que no correspondan a las entradas actuales.
    """
    from .consistency import require_current_results
    require_current_results(project, results, settings, db)
    _fonts()
    st = _styles()
    system = project.units
    tmpdir = tempfile.mkdtemp(prefix="hvac_rep_")
    figs = build_all(project, results, db, settings, system)
    doc = BaseDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm,
                          bottomMargin=17 * mm, title=f"Memoria de cálculo — {project.info.name}",
                          author=project.info.engineer or "HVAC Industrial Engineering Calculator")
    W = A4[0] - 30 * mm
    frame = Frame(doc.leftMargin, doc.bottomMargin, W, A4[1] - doc.topMargin - doc.bottomMargin, id="f")
    WL = A4[1] - 30 * mm
    frame_l = Frame(15 * mm, 17 * mm, WL, A4[0] - 33 * mm, id="fl")

    def on_page(c, d):
        c._footer_text = f"{project.info.name} — Memoria de cálculo — Rev. {project.info.revision} — HVAC IEC v{APP_VERSION}"
        if c.getPageNumber() > 1:
            c.setFont("DejaVu", 7.5)
            c.setFillColor(INK2)
            c.drawString(15 * mm, c._pagesize[1] - 10 * mm, "HVAC INDUSTRIAL ENGINEERING CALCULATOR")
            c.drawRightString(c._pagesize[0] - 15 * mm, c._pagesize[1] - 10 * mm, _dt.date.today().isoformat())

    doc.addPageTemplates([PageTemplate("p", [frame], onPage=on_page),
                          PageTemplate("l", [frame_l], onPage=on_page, pagesize=landscape(A4))])
    E = []
    info = project.info
    # 1. Portada ----------------------------------------------------------------
    E += [Spacer(1, 30 * mm), _p("MEMORIA DE CÁLCULO", st["subtitle"]),
          _p("Sistema de ventilación y extracción industrial", st["title"]), _p(info.name, st["h1"]), Spacer(1, 6 * mm)]
    cover = [["Cliente", info.client or "—"], ["Ubicación", info.location or "—"], ["Tipo de ventilación", info.ventilation_type],
             ["Elaboró", info.engineer or "—"], ["Revisó", info.reviewer or "—"], ["Fecha", info.date], ["Revisión", info.revision],
             ["Sistema de unidades", "SI" if system == "SI" else "Imperial (IP)"],
             ["Programa", f"HVAC Industrial Engineering Calculator v{APP_VERSION} — cálculo del {results.timestamp}"]]
    E.append(_table(["Dato", "Valor"], cover, st, [45 * mm, W - 45 * mm], zebra=False))
    E.append(Spacer(1, 8 * mm))
    if results.dictamen:
        code = results.dictamen.decision_code
        box = Table([[_p("DECISIÓN TÉCNICA", ParagraphStyle("bx", parent=st["cellb"], textColor=colors.white, fontSize=9))],
                     [_p(results.dictamen.decision, ParagraphStyle("bx2", parent=st["h2"], textColor=colors.white))]],
                    colWidths=[W])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(DEC_COLORS[code])),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 5)]))
        E.append(box)
    E += [Spacer(1, 8 * mm), _p("Esta memoria es una herramienta de apoyo al diseño. No constituye certificación de "
                                "cumplimiento normativo ni sustituye la revisión y responsabilidad del ingeniero a cargo.",
                                st["small"]), PageBreak()]

    def H(n, t):
        E.append(_p(f"{n}. {t}", st["h1"]))

    def trace(module_titles):
        if not include_traces:
            return
        steps = [s for s in results.trace.steps if s.module in module_titles]
        if steps:
            E.append(_p("Desarrollo de cálculos (ecuación, sustitución y fuente):", st["h2"]))
            E.append(_trace_table(steps[:40], st, W))
            if len(steps) > 40:
                E.append(_p(f"… {len(steps) - 40} pasos adicionales en el Anexo A.", st["small"]))

    # 2. Datos generales
    H(2, "Datos generales")
    E.append(_table(["Concepto", "Descripción"], [["Proyecto", info.name], ["Descripción", info.description or "—"],
                                                  ["Objetivo del diseño", info.objective or "—"],
                                                  ["Notas", project.notes or "—"]], st, [40 * mm, W - 40 * mm], zebra=False))
    # 3. Condiciones ambientales
    H(3, "Condiciones ambientales")
    a = project.air
    E.append(_table(["Dato de entrada", "Valor"], [
        ["Modo", a.mode], ["Temperatura", fmt(a.t_c, "temperature", system)],
        ["Altitud", fmt(a.altitude_m, "length", system) if a.altitude_m is not None else "—"],
        ["Presión barométrica indicada", fmt(a.p_pa, "pressure", system) if a.p_pa else "estimada por altitud"],
        ["Humedad relativa", f"{a.rh * 100:.0f} %"],
        ["Temperatura superficial mínima de ductos", fmt(a.t_min_surface_c, "temperature", system) if a.t_min_surface_c is not None else "—"]],
        st, [70 * mm, W - 70 * mm]))
    # 4. Propiedades del aire
    H(4, "Propiedades del aire")
    E.append(_table(*T.air_table(results.air, system), st, [55 * mm, 28 * mm, 25 * mm, W - 108 * mm]))
    trace(["Propiedades del aire"])
    # 5. Caudales de diseño
    H(5, "Caudales de diseño")
    hdr, rows = T.airflow_table(results, system)
    if rows:
        E.append(_p("Ventilación general:", st["h2"]))
        E.append(_table(hdr, rows, st, [35 * mm, 30 * mm, W - 65 * mm]))
    E.append(_p("Extracción localizada (campanas):", st["h2"]))
    E.append(_table(*T.hoods_table(project, results, system), st, font_size=6.6))
    E.append(_table(*T.hood_flows_table(results, system), st))
    trace(["Caudales", "Campanas"])
    # 6. Geometría
    E.append(PageBreak())
    H(6, "Geometría de ductos")
    E.append(_table(*T.segments_geometry_table(results, db, system), st, font_size=6.8))
    if "geometry" in figs:
        E.append(_img(figs["geometry"], W * 0.8, tmpdir, "g2"))
    # 7–12: tablas por tramo (apaisado)
    E.append(NextPageTemplate("l"))
    E.append(PageBreak())
    H(7, "Velocidades")
    E.append(_p("Velocidad media V = Q/A en cada tramo con el caudal másico y la densidad local (mezcla adiabática).",
                st["body"]))
    hdr, rows = T.segments_flow_table(results, system)
    if hdr:
        E.append(_table(hdr[:6], [r[:6] for r in rows], st))
    if "velocity" in figs:
        E.append(_img(figs["velocity"], WL * 0.62, tmpdir, "g3"))
    H(8, "Número de Reynolds")
    E.append(_p("Re = ρ·V·Dh/μ. Régimen laminar Re < 2300; transicional 2300–4000 (factor incierto, valor conservador); "
                "turbulento Re > 4000.", st["body"]))
    if hdr:
        E.append(_table([hdr[0], hdr[6], hdr[9]], [[r[0], r[6], r[9]] for r in rows], st, [30 * mm, 40 * mm, 40 * mm]))
    H(9, "Factor de fricción")
    E.append(_p("Factor de Darcy por Colebrook-White (iterativo, tolerancia 10⁻¹²). El factor de Darcy es 4 veces el de "
                "Fanning. Contraste con Swamee-Jain, Churchill y Altshul-Tsal en las pruebas de validación.", st["body"]))
    if hdr:
        E.append(_table([hdr[0], hdr[7], hdr[8], hdr[9]], [[r[0], r[7], r[8], r[9]] for r in rows], st,
                        [30 * mm, 35 * mm, 35 * mm, 35 * mm]))
    H(10, "Pérdidas distribuidas")
    E.append(_p("ΔPf = f·(L/Dh)·ρV²/2 (Darcy-Weisbach).", st["body"]))
    if hdr:
        E.append(_table(hdr[:1] + hdr[10:11] + hdr[15:], [r[:1] + r[10:11] + r[15:] for r in rows], st))
    H(11, "Pérdidas locales")
    E.append(_p("ΔP = K·ρ·V_ref²/2, con la sección de referencia indicada para cada coeficiente; incluye entradas de "
                "campana, uniones, compuertas y descarga.", st["body"]))
    E.append(_table(*T.fittings_table(results, system), st, font_size=6.6))
    H(12, "Pérdidas de equipos")
    E.append(_table(*T.equipment_table(results, project, system), st))
    trace(["Diseño de ductos"])
    # 13. Camino crítico
    E.append(NextPageTemplate("p"))
    E.append(PageBreak())
    H(13, "Camino crítico y balance de la red")
    nr = results.network_design
    if nr is not None:
        E.append(_p(f"Camino crítico: {' → '.join(nr.critical_path)} (campana gobernante {nr.governing_hood}). Los planos de "
                    "referencia para el balance son: presión total nula en la atmósfera en reposo frente a cada campana y "
                    "a la salida de la chimenea; la presión total de cada nodo corresponde al inicio del tramo aguas abajo.",
                    st["body"]))
        E.append(_p("Balance en uniones (equilibrado por diseño):", st["h2"]))
        E.append(_table(*T.balance_table(results, system), st, font_size=6.5))
        for k in ("network", "pressure", "losses"):
            if k in figs:
                E.append(_img(figs[k], W, tmpdir, f"g_{k}"))
    # 14. Presión requerida
    H(14, "Presión requerida del ventilador")
    if nr is not None:
        s2 = nr.state
        E.append(_table(["Magnitud", "Valor", "Definición"], [
            ["Caudal en la entrada del ventilador", fmt(s2.Q_fan, "flow", system), "Q = ṁ/ρ_entrada"],
            ["Temperatura / densidad en la entrada", f"{s2.t_fan:.1f} °C / {fmt(s2.rho_fan, 'density', system)}", "Mezcla adiabática"],
            ["Presión total en la entrada", fmt(s2.tp_fan_in, "pressure", system), "Camino crítico (succión)"],
            ["Presión total en la salida", fmt(s2.tp_fan_out, "pressure", system), "Pérdidas de descarga incl. salida"],
            ["Presión de velocidad de salida", fmt(s2.VP_fan_out, "pressure", system), "Área de descarga del ventilador o ducto"],
            ["Presión total del ventilador FTP", fmt(s2.FTP, "pressure", system), "FTP = TP_sal − TP_ent"],
            ["Presión estática del ventilador FSP", fmt(s2.FSP, "pressure", system), "FSP = FTP − VP_sal"],
        ], st, [65 * mm, 45 * mm, W - 110 * mm]))
    # 15. Ventilador
    H(15, "Selección del ventilador")
    E.append(_table(*T.fans_table(results, system), st, font_size=6.2))
    fe = results.selected_fan
    if fe and fe.op:
        E.append(_p("Distribución de caudales en el punto de operación:", st["h2"]))
        E.append(_table(*T.hood_flows_table(results, system), st))
    if "fan" in figs:
        E.append(_img(figs["fan"], W, tmpdir, "g5"))
    # 16–17. Potencias
    H(16, "Potencia al eje")
    pw = results.power
    if pw is not None:
        E.append(_p(f"Potencia aerodinámica P = Q·FTP = {fmt(pw.P_air_total, 'power', system)}; potencia absorbida por el "
                    f"ventilador (eje del ventilador) = {fmt(pw.W_fan, 'power', system)} ({pw.W_fan_method}); potencia en el "
                    f"eje del motor = W_vent/η_transmisión = {fmt(pw.W_motor_out, 'power', system)}.", st["body"]))
    elif getattr(results, "power_blocked", ""):
        E.append(_p("CÁLCULO DE POTENCIA BLOQUEADO — " + results.power_blocked, st["body"]))
    H(17, "Potencia eléctrica, motor y energía")
    if pw is None and getattr(results, "power_blocked", ""):
        E.append(_p("No se selecciona motor ni se estima la energía hasta corregir la incoherencia de datos indicada "
                    "en la sección 16 (ver alertas CRÍTICAS).", st["body"]))
    else:
        E.append(_table(*T.power_table(results, project, system), st, [62 * mm, 28 * mm, 25 * mm, W - 115 * mm]))
    hdr, rows = T.part_load_table(results, system)
    if hdr:
        E.append(_p("Regulación a carga parcial: compuerta frente a variador de frecuencia (eficiencias constantes):",
                    st["h2"]))
        E.append(_table(hdr, rows, st))
    trace(["Potencia y motores", "Selección de ventiladores"])
    # 18. Gráficas
    E.append(PageBreak())
    H(18, "Gráficas y esquemas")
    if "system" in figs:
        E.append(_img(figs["system"], W, tmpdir, "g1"))
    E.append(_p("Los gráficos 2 a 7 se presentan en las secciones correspondientes (6, 7, 13 y 15). Todos se generan a "
                "partir de los datos ingresados y los resultados calculados.", st["small"]))
    # 19. Advertencias
    E.append(NextPageTemplate("l"))
    E.append(PageBreak())
    H(19, "Advertencias y verificaciones")
    hdr, rows = T.alerts_table(results, system)
    if rows:
        E.append(_table(hdr, rows, st, [WL * x for x in (0.065, 0.08, 0.08, 0.06, 0.13, 0.07, 0.12, 0.13, 0.14, 0.125)],
                        font_size=6.2, first_col_colors=LEVEL_COLORS))
    E.append(NextPageTemplate("p"))
    E.append(PageBreak())
    # 20. Referencias
    H(20, "Referencias técnicas")
    E.append(_table(["Referencia", "Tipo", "Uso en el programa", "Acceso"],
                    [[r["title"], r["type"], r["use"], r["access"]] for r in db.references], st,
                    [W * 0.42, W * 0.14, W * 0.3, W * 0.14], font_size=6.6))
    E.append(_p("Las normas y manuales de acceso restringido no se reproducen; los valores tomados de ellos están marcados "
                "'verificar en edición vigente' en la base de datos editable.", st["small"]))
    # 21. Hipótesis y limitaciones
    H(21, "Hipótesis y limitaciones")
    hyp = ["Aire como gas ideal; psicrometría ASHRAE sin factor de realce (error < 0.5 % en W).",
           "Viscosidad por Sutherland (≤ 0.8 % hasta 100 °C; 2.4 % a 400 °C, efecto < 0.5 % en f).",
           "Densidad de cada tramo a la presión barométrica (se desprecia la presión manométrica del ducto).",
           "Mezcla adiabática en uniones; sin transferencia de calor por las paredes de los ductos.",
           "Balance de presión total en nodos con pérdidas de unión asignadas a los tramos que llegan.",
           "Coeficientes de captura de DallaValle válidos dentro de su rango geométrico (verificado por el programa).",
           "Curvas de ventilador corregidas por leyes de semejanza; sin efecto del sistema cuantitativo (AMCA 201).",
           f"Filtros evaluados en estado '{project.network_settings.filter_state_design}' para diseño y 'limpio' para sobrecarga."]
    E += _bullets(hyp, st)
    if results.dictamen:
        E += _bullets(results.dictamen.limitations, st)
    # 22. DICTAMEN --------------------------------------------------------------
    E.append(PageBreak())
    E.append(_p("22. DICTAMEN Y RECOMENDACIONES DE INGENIERÍA", st["h1"]))
    d = results.dictamen
    if d is not None:
        sections = [("1. Descripción del sistema analizado", d.description), ("2. Objetivo del diseño", d.objective),
                    ("3. Datos de entrada e hipótesis", d.inputs), ("4. Resultados principales", d.results),
                    ("5. Evaluación de los resultados", d.evaluation),
                    ("6. Problemas o desviaciones identificados", d.problems or ["No se identificaron problemas de nivel MEDIO o superior."])]
        for t, items in sections:
            E.append(_p(t, st["h2"]))
            E += _bullets(items, st)
        E.append(_p("7. Decisión técnica", st["h2"]))
        box = Table([[_p(d.decision, ParagraphStyle("dx", parent=st["h2"], textColor=colors.white))]], colWidths=[W])
        box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(DEC_COLORS[d.decision_code])),
                                 ("LEFTPADDING", (0, 0), (-1, -1), 8)]))
        E.append(box)
        for t, items in [("8. Modificaciones recomendadas", d.modifications or ["Ninguna obligatoria."]),
                         ("9. Alternativas que conviene estudiar", d.alternatives),
                         ("10. Información pendiente para cerrar el diseño", d.pending),
                         ("11. Referencias técnicas utilizadas", d.references),
                         ("12. Limitaciones y alcance del dictamen", d.limitations)]:
            E.append(_p(t, st["h2"]))
            E += _bullets(items, st)
        E.append(_p("Conclusiones por módulo (A. Diagnóstico · B. Decisión · C. Justificación · D. Acción recomendada)",
                    st["h1"]))
        for m, dec in results.decisions.items():
            blk = [_p(f"{m} — {dec.decision}", ParagraphStyle("mh", parent=st["h2"], textColor=colors.HexColor(dec.color)))]
            blk.append(_p("A. Diagnóstico: " + " ".join(dec.diagnosis) + f" ¿Viable? {dec.viable}", st["body"]))
            if dec.satisfactory:
                blk.append(_p("Parámetros satisfactorios: " + "; ".join(dec.satisfactory), st["small"]))
            if dec.problems:
                blk.append(_p("Parámetros con problemas: " + "; ".join(dec.problems), st["small"]))
            blk.append(_p("C. Justificación: " + " ".join(dec.justification), st["small"]))
            blk.append(_p("D. Acción recomendada: " + " ".join(dec.actions), st["small"]))
            E.append(KeepTogether(blk))
    # 23. Comparador
    if comparison and comparison[0]:
        mets, concl = comparison
        E.append(NextPageTemplate("l"))
        E.append(PageBreak())
        E.append(_p("23. Comparador de alternativas de diseño", st["h1"]))
        E.append(_table(*T.comparison_table(mets, project, system), st, font_size=6.0))
        E.append(Spacer(1, 3 * mm))
        E += _bullets(concl, st)
        E.append(_img(plot_alternatives(mets, system), WL * 0.55, tmpdir, "alt"))
        E.append(NextPageTemplate("p"))
    # 24. Recomendaciones constructivas
    E.append(PageBreak())
    E.append(_p("24. Recomendaciones constructivas y de instalación", st["h1"]))
    E.append(_table(["Tema", "Recomendación", "Tipo", "Fuente"],
                    [[r.topic, r.text, r.kind, r.source] for r in results.construction], st,
                    [W * 0.15, W * 0.5, W * 0.15, W * 0.2], font_size=6.8))
    # Anexo A
    if include_traces:
        E.append(NextPageTemplate("l"))
        E.append(PageBreak())
        E.append(_p("Anexo A. Trazabilidad de cálculos", st["h1"]))
        E.append(_p("Todas las sustituciones numéricas se presentan en SI (sistema interno de cálculo).", st["small"]))
        E.append(_trace_table(results.trace.steps, st, WL))
        E.append(NextPageTemplate("p"))
    # Anexo B
    E.append(PageBreak())
    E.append(_p("Anexo B. Validación del software", st["h1"]))
    rep = os.path.join(app_root(), "tests", "results", "registro_pruebas.csv")
    if os.path.exists(rep):
        with open(rep, encoding="utf-8-sig") as fh:
            recs = list(csv.DictReader(fh))
        n_ok = sum(r["estado"] == "APROBADA" for r in recs)
        E.append(_p(f"Última ejecución de pruebas: {len(recs)} comprobaciones numéricas, {n_ok} aprobadas, "
                    f"{len(recs) - n_ok} fallidas. Referencias independientes: CoolProp/IAPWS, soluciones analíticas, "
                    "ecuaciones elementales y una segunda formulación del solucionador de red.", st["body"]))
        sample = recs[:60]
        E.append(_table(["Prueba", "Comprobación", "Esperado", "Obtenido", "Error rel.", "Referencia", "Estado"],
                        [[r["prueba"][:40], r["comprobación"], f"{float(r['esperado']):.6g}", f"{float(r['obtenido']):.6g}",
                          f"{float(r['error_rel']):.2e}", r["referencia"], r["estado"]] for r in sample], st, font_size=6.0))
    else:
        E.append(_p("No se encontró el registro de pruebas (ejecute run_tests).", st["body"]))
    doc.build(E, canvasmaker=NumberedCanvas)
    return path
