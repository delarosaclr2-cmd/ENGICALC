"""Exportación de resultados a Excel (openpyxl)."""
from __future__ import annotations

import os
import tempfile

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from core.project import APP_VERSION
from graphics.plots import build_all, save_png
from validation.alerts import LEVEL_COLORS
from . import tables as T

HEAD_FILL = PatternFill("solid", fgColor="14213D")
HEAD_FONT = Font(bold=True, color="FFFFFF")
THIN = Side(style="thin", color="D9D8D2")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)


def _sheet(wb, title, hdr, rows, widths=None, note=None):
    ws = wb.create_sheet(title[:31])
    r0 = 1
    if note:
        ws.cell(1, 1, note).font = Font(italic=True, color="52514E")
        r0 = 3
    for j, h in enumerate(hdr, start=1):
        c = ws.cell(r0, j, h)
        c.fill, c.font, c.border = HEAD_FILL, HEAD_FONT, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for i, row in enumerate(rows, start=r0 + 1):
        for j, v in enumerate(row, start=1):
            val = v
            if isinstance(v, str):
                try:
                    val = float(v.replace(",", "")) if v.replace(",", "").replace(".", "", 1).replace("-", "", 1).replace("e", "", 1).isdigit() else v
                except ValueError:
                    val = v
            c = ws.cell(i, j, val)
            c.border = BORDER
            c.alignment = Alignment(wrap_text=True, vertical="top")
    for j in range(1, len(hdr) + 1):
        ws.column_dimensions[get_column_letter(j)].width = (widths[j - 1] if widths and j - 1 < len(widths) else
                                                            min(max(12, len(str(hdr[j - 1])) + 4), 45))
    ws.freeze_panes = ws.cell(r0 + 1, 1)
    return ws


def export_excel(project, results, db, settings, path: str, comparison=None) -> str:
    system = project.units
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    info = project.info
    rows = [["Proyecto", info.name], ["Cliente", info.client], ["Ubicación", info.location], ["Elaboró", info.engineer],
            ["Fecha", info.date], ["Revisión", info.revision], ["Sistema de unidades", system],
            ["Programa", f"HVAC Industrial Engineering Calculator v{APP_VERSION}"], ["Cálculo", results.timestamp],
            ["Decisión técnica", results.dictamen.decision if results.dictamen else "—"]]
    for i, (k, v) in enumerate(rows, start=1):
        ws.cell(i, 1, k).font = Font(bold=True)
        ws.cell(i, 2, v)
    r = len(rows) + 2
    ws.cell(r, 1, "Decisiones por módulo").font = Font(bold=True, size=12)
    for m, d in results.decisions.items():
        r += 1
        ws.cell(r, 1, m)
        ws.cell(r, 2, d.decision).font = Font(color=d.color.strip("#"), bold=True)
    ws.column_dimensions["A"].width = 32
    ws.column_dimensions["B"].width = 80
    _sheet(wb, "Aire", *T.air_table(results.air, system), widths=[36, 16, 14, 40])
    _sheet(wb, "Caudales", *T.airflow_table(results, system), widths=[22, 18, 90])
    _sheet(wb, "Campanas", *T.hoods_table(project, results, system))
    _sheet(wb, "Caudales por campana", *T.hood_flows_table(results, system))
    _sheet(wb, "Geometría tramos", *T.segments_geometry_table(results, db, system))
    _sheet(wb, "Flujo y pérdidas", *T.segments_flow_table(results, system),
           note="Pérdidas de presión total por tramo; TP/SP manométricas referidas a la atmósfera.")
    _sheet(wb, "Accesorios", *T.fittings_table(results, system))
    _sheet(wb, "Equipos", *T.equipment_table(results, project, system))
    _sheet(wb, "Balance de red", *T.balance_table(results, system),
           note=f"Camino crítico: {' → '.join(results.network_design.critical_path)}" if results.network_design else None)
    _sheet(wb, "Ventiladores", *T.fans_table(results, system))
    sc = results.system_curve
    if sc:
        from core.units import to_display, display_unit
        _sheet(wb, "Curva del sistema", [f"Q [{display_unit('flow', system)}]", f"FTP [{display_unit('pressure', system)}]",
                                          f"FSP [{display_unit('pressure', system)}]", "Convergió"],
               [[round(to_display(q, "flow", system), 4), round(to_display(p, "pressure", system), 3),
                 round(to_display(s, "pressure", system), 3), "Sí" if ok else "No"] for q, p, s, ok in sc])
    _sheet(wb, "Potencia", *T.power_table(results, project, system), widths=[40, 16, 16, 50])
    hdr, rows = T.part_load_table(results, system)
    if hdr:
        _sheet(wb, "Carga parcial", hdr, rows)
    wsa = _sheet(wb, "Alertas", *T.alerts_table(results, system), widths=[11, 18, 20, 10, 45, 14, 35, 40, 45, 40])
    for i in range(2, wsa.max_row + 1):
        lv = wsa.cell(i, 1).value
        if lv in LEVEL_COLORS:
            wsa.cell(i, 1).font = Font(bold=True, color=LEVEL_COLORS[lv].strip("#"))
    d = results.dictamen
    if d:
        rows = []
        for t, items in [("Descripción", d.description), ("Objetivo", d.objective), ("Datos e hipótesis", d.inputs),
                         ("Resultados", d.results), ("Evaluación", d.evaluation), ("Problemas", d.problems),
                         ("Decisión", [d.decision]), ("Modificaciones", d.modifications), ("Alternativas", d.alternatives),
                         ("Información pendiente", d.pending), ("Referencias", d.references), ("Limitaciones", d.limitations)]:
            for it in items or ["—"]:
                rows.append([t, it])
        _sheet(wb, "Dictamen", ["Apartado", "Contenido"], rows, widths=[24, 140],
               note="DICTAMEN Y RECOMENDACIONES DE INGENIERÍA")
    if comparison and comparison[0]:
        mets, concl = comparison
        ws2 = _sheet(wb, "Comparador", *T.comparison_table(mets, project, system))
        r = ws2.max_row + 2
        for c in concl:
            ws2.cell(r, 1, c)
            r += 1
    _sheet(wb, "Recom. constructivas", ["Tema", "Recomendación", "Tipo", "Fuente"],
           [[x.topic, x.text, x.kind, x.source] for x in results.construction], widths=[22, 90, 30, 40])
    _sheet(wb, "Trazabilidad", ["Módulo", "Cálculo", "Ecuación", "Variables", "Sustitución", "Resultado", "Unidad", "Fuente",
                                "Tipo"],
           [[s.module, s.title, s.equation, "; ".join(v.text() for v in s.variables), s.substitution,
             s.result if isinstance(s.result, (int, float)) else str(s.result), s.unit, s.source, s.kind]
            for s in results.trace.steps], widths=[18, 30, 34, 40, 40, 14, 10, 40, 18])
    # gráficos
    wsg = wb.create_sheet("Gráficos")
    tmp = tempfile.mkdtemp(prefix="hvac_xl_")
    row = 1
    for k, fig in build_all(project, results, db, settings, system).items():
        pth = os.path.join(tmp, f"{k}.png")
        save_png(fig, pth, 90)
        img = XLImage(pth)
        wsg.add_image(img, f"A{row}")
        row += int(img.height / 20) + 2
    wb.save(path)
    return path
