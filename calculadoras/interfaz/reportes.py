"""Memoria de cálculo en PDF y Excel, y archivos de caso (JSON).

Todos los reportes se generan a partir del ÚLTIMO cálculo realizado (entradas
validadas + resultado), nunca leyendo los campos de la ventana; así el reporte
no puede mezclar entradas de un caso con resultados de otro (problema de la
bomba original) ni contener valores editados a mano.
"""
from __future__ import annotations

import io
import json
import os
from datetime import datetime
from pathlib import Path

from .. import __version__
from ..nucleo.configuracion import cargar, recurso
from ..nucleo.historial import CAMPOS_PROYECTO, normalizar_proyecto, tiene_datos
from ..nucleo.modelo import NIVELES, Calculadora, Resultado

AVISO = ("Herramienta de apoyo para cálculos de ingeniería. Sus resultados no constituyen una memoria "
         "certificada ni sustituyen la revisión y firma de un ingeniero responsable.")


# ---------------------------------------------------------------------------
# Casos (guardar / abrir)
# ---------------------------------------------------------------------------
def guardar_caso(ruta: os.PathLike | str, calc: Calculadora, entradas: dict,
                 resultado: Resultado | None = None, proyecto: dict | None = None) -> None:
    datos = {
        "programa": "Calculadoras de Ingeniería RMR",
        "version": __version__,
        "calculadora": calc.id,
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "proyecto": normalizar_proyecto(proyecto),
        "entradas": {k: v for k, v in entradas.items()},
        "resultado": resultado.como_dict() if resultado else None,
    }
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)


def abrir_caso(ruta: os.PathLike | str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if "calculadora" not in datos or "entradas" not in datos:
        raise ValueError("El archivo no es un caso de Calculadoras de Ingeniería RMR.")
    return datos


# ---------------------------------------------------------------------------
# Texto plano
# ---------------------------------------------------------------------------
def filas_proyecto(proyecto: dict | None) -> list[tuple[str, str]]:
    """(etiqueta, valor) de los datos del proyecto capturados (vacío si no hay ninguno)."""
    datos = normalizar_proyecto(proyecto)
    if not tiene_datos(datos):
        return []
    return [(etiqueta, datos[clave] or "—") for clave, etiqueta in CAMPOS_PROYECTO]


def texto_reporte(calc: Calculadora, entradas: dict, resultado: Resultado, proyecto: dict | None = None) -> str:
    lineas = [f"{calc.nombre} — {calc.disciplina}",
              f"Fecha: {datetime.now():%d/%m/%Y %H:%M}   Versión del programa: {__version__}",
              f"Estado: {calc.estado_auditoria} / {calc.estado_validacion}"]
    lineas += [f"{etiqueta}: {valor}" for etiqueta, valor in filas_proyecto(proyecto)]
    lineas += ["", "DATOS DE ENTRADA"]
    for c in calc.campos:
        lineas.append(f"  {c.etiqueta}: {_valor_entrada(entradas.get(c.clave))} {c.unidad}".rstrip())
    lineas += ["", "RESULTADOS"]
    for s in resultado.salidas:
        lineas.append(f"  [{s.nivel}] {s.etiqueta}: {s.texto_valor()} {s.unidad}".rstrip())
    if resultado.advertencias:
        lineas += ["", "ADVERTENCIAS"] + [f"  - {a}" for a in resultado.advertencias]
    if resultado.ecuaciones:
        lineas += ["", "ECUACIONES"] + [f"  {e}" for e in resultado.ecuaciones]
    if resultado.notas:
        lineas += ["", "NOTAS"] + [f"  - {n}" for n in resultado.notas]
    lineas += ["", "Niveles: " + "; ".join(f"{k} = {v}" for k, v in NIVELES.items()), "", AVISO]
    return "\n".join(lineas)


def _valor_entrada(v) -> str:
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
def _registrar_fuentes() -> tuple[str, str]:
    """Registra una fuente Unicode para que el PDF muestre griegas, subíndices y superíndices (Δ, ρ, H₂O, m³, v²).

    Orden: DejaVu Sans incluida en ``recursos/fuentes`` (licencia libre, ver LICENSE_DEJAVU) →
    Segoe UI de Windows → Helvetica (último recurso: sin Δ, ₂ ni ²).
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    fuentes_windows = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    candidatos = [("DejaVu", recurso("fuentes") / "DejaVuSans.ttf", recurso("fuentes") / "DejaVuSans-Bold.ttf"),
                  ("SegoeUI", fuentes_windows / "segoeui.ttf", fuentes_windows / "segoeuib.ttf")]
    for nombre, normal, negrita in candidatos:
        if normal.is_file() and negrita.is_file():
            try:
                if nombre not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(nombre, str(normal)))
                    pdfmetrics.registerFont(TTFont(f"{nombre}-Bold", str(negrita)))
                return nombre, f"{nombre}-Bold"
            except Exception:  # archivo de fuente dañado o no compatible: se prueba el siguiente
                continue
    return "Helvetica", "Helvetica-Bold"


def generar_pdf(ruta: os.PathLike | str, calc: Calculadora, entradas: dict, resultado: Resultado,
                figura=None, proyecto: dict | None = None) -> None:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    fuente, negrita = _registrar_fuentes()
    config = cargar()
    estilos = getSampleStyleSheet()
    base = ParagraphStyle("base", parent=estilos["Normal"], fontName=fuente, fontSize=8.5, leading=11)
    titulo = ParagraphStyle("titulo", parent=base, fontName=negrita, fontSize=14, leading=18, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=base, fontName=negrita, fontSize=10.5, leading=14, spaceBefore=8, spaceAfter=3)
    peq = ParagraphStyle("peq", parent=base, fontSize=7.5, leading=9.5, textColor=colors.grey)

    def p(texto, estilo=base):
        return Paragraph(_escapar(str(texto)), estilo)

    doc = SimpleDocTemplate(str(ruta), pagesize=letter, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.5 * cm, bottomMargin=1.5 * cm,
                            title=f"Memoria de cálculo — {calc.nombre}", author=config["reportes"].get("empresa", ""))
    ancho = letter[0] - 3.6 * cm
    flujo = []
    logo = recurso(config["reportes"].get("logo", ""))
    if logo.is_file():
        try:
            flujo.append(Image(str(logo), width=4.5 * cm, height=1.1 * cm, kind="proportional"))
        except Exception:
            pass
    flujo.append(p(f"Memoria de cálculo: {calc.nombre}", titulo))
    flujo.append(p(f"{config['reportes'].get('empresa', '')} · {calc.disciplina} · "
                   f"{datetime.now():%d/%m/%Y %H:%M} · versión {__version__}"))
    filas_p = filas_proyecto(proyecto)
    if not filas_p and config["reportes"].get("elaboro"):
        flujo.append(p(f"Elaboró: {config['reportes']['elaboro']}"))
    flujo.append(p(f"Estado de auditoría: {calc.estado_auditoria}. Estado de validación: {calc.estado_validacion}."))
    flujo.append(Spacer(1, 4))
    if filas_p:
        mitad = (len(filas_p) + 1) // 2
        izquierda, derecha = filas_p[:mitad], filas_p[mitad:]
        filas = []
        for i in range(mitad):
            fila = [p(izquierda[i][0], ParagraphStyle("pe", parent=base, fontName=negrita)), p(izquierda[i][1])]
            if i < len(derecha):
                fila += [p(derecha[i][0], ParagraphStyle("pe", parent=base, fontName=negrita)), p(derecha[i][1])]
            else:
                fila += ["", ""]
            filas.append(fila)
        tp = Table(filas, colWidths=[ancho * 0.16, ancho * 0.34, ancho * 0.16, ancho * 0.34])
        tp.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), fuente), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA5B1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF1F5")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#EEF1F5")),
        ]))
        flujo.append(tp)
        flujo.append(Spacer(1, 4))

    estilo_tabla = TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), fuente), ("FONTNAME", (0, 0), (-1, 0), negrita),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EA")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA5B1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (2, 1), (2, -1), "RIGHT"),
    ])
    flujo.append(p("Datos de entrada", sub))
    filas = [["Dato", "Valor", "Unidad"]]
    for c in calc.campos:
        filas.append([p(c.etiqueta), p(_valor_entrada(entradas.get(c.clave))), p(c.unidad)])
    t = Table(filas, colWidths=[ancho * 0.62, ancho * 0.24, ancho * 0.14], repeatRows=1)
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), fuente), ("FONTNAME", (0, 0), (-1, 0), negrita),
        ("FONTSIZE", (0, 0), (-1, -1), 8), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DDE3EA")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9AA5B1")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    flujo.append(t)

    flujo.append(p("Resultados", sub))
    filas = [["Resultado", "Nivel", "Valor", "Unidad"]]
    for s in resultado.salidas:
        filas.append([p(s.etiqueta + (f" — {s.nota}" if s.nota else "")), p(s.nivel), p(s.texto_valor()), p(s.unidad)])
    t = Table(filas, colWidths=[ancho * 0.56, ancho * 0.08, ancho * 0.22, ancho * 0.14], repeatRows=1)
    t.setStyle(estilo_tabla)
    flujo.append(t)
    flujo.append(p("Nivel: " + "; ".join(f"{k} = {v}" for k, v in NIVELES.items()), peq))

    if resultado.advertencias:
        flujo.append(p("Advertencias", sub))
        flujo += [p("• " + a) for a in resultado.advertencias]
    if resultado.ecuaciones:
        flujo.append(p("Ecuaciones empleadas", sub))
        flujo += [p(e) for e in resultado.ecuaciones]
    if resultado.notas:
        flujo.append(p("Notas", sub))
        flujo += [p("• " + n) for n in resultado.notas]
    if calc.referencias or calc.limitaciones:
        flujo.append(p("Referencias y limitaciones", sub))
        flujo += [p("Referencia: " + r) for r in calc.referencias]
        flujo += [p("Limitación: " + li) for li in calc.limitaciones]
    if figura is not None:
        buffer = io.BytesIO()
        figura.savefig(buffer, format="png", dpi=150)
        buffer.seek(0)
        alto = ancho * figura.get_figheight() / figura.get_figwidth()
        flujo.append(KeepTogether([p("Gráfica", sub), Image(buffer, width=ancho * 0.85, height=alto * 0.85)]))
    flujo.append(Spacer(1, 8))
    flujo.append(p(AVISO, peq))
    flujo.append(p("Archivos originales sustituidos: " + ", ".join(calc.archivos_originales), peq))
    doc.build(flujo)


def _escapar(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Excel
# ---------------------------------------------------------------------------
def generar_excel(ruta: os.PathLike | str, calc: Calculadora, entradas: dict, resultado: Resultado,
                  proyecto: dict | None = None) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    libro = Workbook()
    hoja = libro.active
    hoja.title = "Memoria"
    negrita = Font(bold=True)
    relleno = PatternFill("solid", fgColor="DDE3EA")

    hoja.append([f"Memoria de cálculo: {calc.nombre}"])
    hoja["A1"].font = Font(bold=True, size=13)
    hoja.append([f"{calc.disciplina} · {datetime.now():%d/%m/%Y %H:%M} · versión {__version__}"])
    hoja.append([f"Estado: {calc.estado_auditoria} / {calc.estado_validacion}"])
    for etiqueta, valor in filas_proyecto(proyecto):
        hoja.append([etiqueta, valor])
        hoja.cell(hoja.max_row, 1).font = negrita
    hoja.append([])
    hoja.append(["DATOS DE ENTRADA"])
    hoja.cell(hoja.max_row, 1).font = negrita
    hoja.append(["Dato", "Valor", "Unidad"])
    for celda in hoja[hoja.max_row]:
        celda.font, celda.fill = negrita, relleno
    for c in calc.campos:
        hoja.append([c.etiqueta, entradas.get(c.clave), c.unidad])
    hoja.append([])
    hoja.append(["RESULTADOS"])
    hoja.cell(hoja.max_row, 1).font = negrita
    hoja.append(["Resultado", "Valor", "Unidad", "Nivel", "Nota"])
    for celda in hoja[hoja.max_row]:
        celda.font, celda.fill = negrita, relleno
    for s in resultado.salidas:
        valor = s.valor if isinstance(s.valor, (int, float, str)) else str(s.valor)
        if isinstance(valor, bool):
            valor = "Sí" if valor else "No"
        hoja.append([s.etiqueta, valor, s.unidad, s.nivel, s.nota])
        if isinstance(valor, float):
            hoja.cell(hoja.max_row, 2).number_format = "0.000"
    for titulo_bloque, lista in (("ADVERTENCIAS", resultado.advertencias), ("ECUACIONES", resultado.ecuaciones),
                                 ("NOTAS", resultado.notas)):
        if lista:
            hoja.append([])
            hoja.append([titulo_bloque])
            hoja.cell(hoja.max_row, 1).font = negrita
            for elemento in lista:
                hoja.append([elemento])
                hoja.cell(hoja.max_row, 1).alignment = Alignment(wrap_text=False)
    hoja.append([])
    hoja.append(["Niveles: " + "; ".join(f"{k} = {v}" for k, v in NIVELES.items())])
    hoja.append([AVISO])
    hoja.column_dimensions["A"].width = 62
    hoja.column_dimensions["B"].width = 18
    hoja.column_dimensions["C"].width = 14
    hoja.column_dimensions["D"].width = 8
    hoja.column_dimensions["E"].width = 50
    libro.save(ruta)
