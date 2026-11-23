"""Ejecución de un caso y generación de reportes (texto, Excel y PDF)."""
from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import List

from . import __version__
from . import unidades as u
from .caso import CasoUsuario
from .constantes import REFERENCIAS
from .criterios import Verificacion, verificar
from .motor import Entradas, Resultados, calcular

AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación "
         "de un ingeniero responsable ni constituyen una validación del proyecto.")


@dataclass
class Informe:
    caso: CasoUsuario
    entradas: Entradas
    resultados: Resultados
    verificaciones: List[Verificacion]
    huella: str
    fecha: str
    version: str = __version__


def ejecutar(caso: CasoUsuario) -> Informe:
    e = caso.a_entradas()
    r = calcular(e)
    v = verificar(e, r, caso.a_criterios())
    return Informe(caso, e, r, v, caso.huella(), _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))


# ---------------------------------------------------------------------------- tablas
def _fmt(x, nd=3):
    return "—" if x is None else f"{x:,.{nd}f}"


def tabla_entradas(inf: Informe):
    c, e = inf.caso, inf.entradas
    psia = lambda pa: f"{pa / u.PSI:.3f} psia ({pa / 1e5:.4f} bar a)"
    filas = [
        ("Volumen del tanque", f"{c.v_tanque.valor:g} {c.v_tanque.unidad}", ""),
        ("Presión superior de la banda", psia(e.p_superior_pa), f"capturada: {c.p_superior.valor:g} {c.p_superior.unidad}"),
        ("Presión inferior admisible", psia(e.p_inferior_pa), f"capturada: {c.p_inferior.valor:g} {c.p_inferior.unidad}"),
        ("Presión atmosférica del sitio", psia(e.p_atm_sitio_pa), "solo para convertir presiones manométricas"),
        ("Temperatura del aire en el sistema", f"{e.t_aire_k - 273.15:.2f} °C", ""),
        ("Caudal de consumo", f"{c.q_consumo.valor:g} {c.q_consumo.unidad}",
         REFERENCIAS[e.ref_consumo].nombre),
        ("Margen de consumo", f"{c.margen_consumo_pct:g} %", "fugas / crecimiento"),
        ("FAD del compresor", "no capturado" if c.q_compresor is None else
         f"{c.q_compresor.valor:g} {c.q_compresor.unidad}",
         "" if c.q_compresor is None else REFERENCIAS[e.ref_compresor].nombre),
        ("Exponente de descarga n", f"{e.n_politropico:g}", "1 = isotérmico"),
    ]
    for t, tu in zip(e.tramos, c.tramos):
        filas.append((f"Tramo: {t.descripcion}", f"L = {t.longitud_m:g} m; Di = {t.d_interior_m * 1000:.2f} mm",
                      f"NPS {tu.nps} céd. {tu.cedula}" if tu.nps else "Di capturado"))
    filas.append(("Volumen de tubería incluido", "Sí" if e.incluir_tuberia else "No", ""))
    return filas


def tabla_resultados(inf: Informe):
    r = inf.resultados
    filas = [
        ("Volumen de tubería", _fmt(r.v_tuberia_m3, 4), "m³"),
        ("Volumen del sistema (tanque + tubería)", _fmt(r.v_sistema_m3, 4), "m³"),
        ("Flujo másico de consumo (con margen)", _fmt(r.mdot_consumo_kg_s * 3600, 2), "kg/h"),
        ("Masa útil entre límites de presión", _fmt(r.masa_util_kg, 2), "kg"),
        ("Tiempo de retención sin aporte del compresor", f"{_fmt(r.t_retencion_min, 2)} ({u.min_a_texto(r.t_retencion_min)})", "min"),
    ]
    if r.v_sistema_req_m3 is not None:
        filas += [("Volumen de sistema requerido para el tiempo de retención", _fmt(r.v_sistema_req_m3, 3), "m³"),
                  ("Volumen de tanque requerido (descontando tubería)", _fmt(r.v_tanque_req_m3, 3), "m³")]
    if r.mdot_compresor_kg_s is not None:
        filas.append(("Flujo másico del compresor", _fmt(r.mdot_compresor_kg_s * 3600, 2), "kg/h"))
        if r.t_carga_min is not None:
            filas += [("Tiempo de carga (P inferior → P superior)", f"{_fmt(r.t_carga_min, 2)} ({u.min_a_texto(r.t_carga_min)})", "min"),
                      ("Tiempo en vacío / paro (P superior → P inferior)", f"{_fmt(r.t_descarga_min, 2)} ({u.min_a_texto(r.t_descarga_min)})", "min"),
                      ("Fracción de carga del compresor", _fmt(r.fraccion_carga * 100, 1), "%"),
                      ("Ciclos por hora con el consumo capturado", _fmt(r.ciclos_por_hora, 2), "ciclos/h")]
        else:
            filas.append(("Tiempo de carga", "∞ (FAD ≤ consumo)", ""))
        filas += [("Ciclos por hora, caso más desfavorable (consumo = 50 % FAD)", _fmt(r.ciclos_por_hora_max, 2), "ciclos/h"),
                  ("Tiempo de arranque desde presión atmosférica (sin consumo)", f"{_fmt(r.t_arranque_min, 2)} ({u.min_a_texto(r.t_arranque_min)})", "min")]
    return filas


def sustitucion_retencion(inf: Informe) -> str:
    e, r = inf.entradas, inf.resultados
    ref = REFERENCIAS[e.ref_consumo]
    q = e.q_consumo_m3s * (1 + e.margen_consumo) * 60
    return (f"t = V·(Ps − Pi)·T_ref / (Q_ref·P_ref·T_r) = "
            f"{r.v_sistema_m3:.4f} m³ × ({e.p_superior_pa/1000:.3f} − {e.p_inferior_pa/1000:.3f}) kPa × {ref.temperatura_k:.2f} K"
            f" / ({q:.5f} m³/min × {ref.presion_pa/1000:.3f} kPa × {e.t_aire_k:.2f} K) = {r.t_retencion_min:.3f} min"
            + ("" if e.n_politropico == 1.0 else f"  [descarga politrópica n = {e.n_politropico:g}; la expresión cambia]"))


ECUACIONES = [
    "m = P·V / (Z·R·T)   — masa contenida (gas ideal, Z ≈ 1 para aire < 25 bar)",
    "ṁ = Q_ref·P_ref / (R·T_ref)   — caudal de aire libre a flujo másico (Menon 2005, ec. 5.9–5.12)",
    "t_ret = V·(Ps − Pi)·T_ref / (Q_ref·P_ref·T_r)   — retención sin aporte del compresor",
    "V_req = t·Q_ref·P_ref·T_r / ((Ps − Pi)·T_ref)   — volumen para un tiempo de retención",
    "t_carga = Δm/(ṁc − ṁd);  t_vacío = Δm/ṁd;  fracción de carga = ṁd/ṁc",
    "f_max = ṁc / (4·Δm)   — ciclado máximo, ocurre con ṁd = ṁc/2",
]


def a_texto(inf: Informe) -> str:
    l = [f"TANQUE PULMÓN — {inf.caso.nombre}", f"Documento: {inf.caso.documento}",
         f"Versión calculadora {inf.version} | {inf.fecha} | huella de entradas {inf.huella}", "",
         "ENTRADAS"]
    l += [f"  {a}: {b}" + (f"  [{c}]" if c else "") for a, b, c in tabla_entradas(inf)]
    l += ["", "RESULTADOS"] + [f"  {a}: {b} {c}" for a, b, c in tabla_resultados(inf)]
    l += ["", "SUSTITUCIÓN", "  " + sustitucion_retencion(inf), "", "VERIFICACIONES"]
    l += [f"  [{v.estado}] {v.criterio}: {v.valor} (límite {v.limite}) — {v.referencia}" for v in inf.verificaciones]
    if inf.resultados.advertencias:
        l += ["", "ADVERTENCIAS"] + [f"  - {a}" for a in inf.resultados.advertencias]
    l += ["", AVISO]
    return "\n".join(l)


# ---------------------------------------------------------------------------- Excel
def exportar_excel(inf: Informe, ruta: str) -> str:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill

    wb = Workbook()
    titulo = Font(bold=True, size=13)
    cab = Font(bold=True, color="FFFFFF")
    relleno = PatternFill("solid", fgColor="1F3864")

    def hoja(ws, encabezado, filas, anchos):
        ws.append([f"Tanque pulmón — {inf.caso.nombre}"])
        ws["A1"].font = titulo
        ws.append([f"{inf.caso.documento} | v{inf.version} | {inf.fecha} | huella {inf.huella}"])
        ws.append([])
        ws.append(encabezado)
        for celda in ws[4]:
            celda.font, celda.fill = cab, relleno
        for f in filas:
            ws.append(list(f))
        for i, a in enumerate(anchos):
            ws.column_dimensions[chr(65 + i)].width = a
        for fila in ws.iter_rows(min_row=5):
            for celda in fila:
                celda.alignment = Alignment(wrap_text=True, vertical="top")

    hoja(wb.active, ["Parámetro", "Valor", "Nota"], tabla_entradas(inf), [44, 40, 50])
    wb.active.title = "Entradas"
    hoja(wb.create_sheet("Resultados"), ["Resultado", "Valor", "Unidad"], tabla_resultados(inf), [58, 30, 12])
    ws = wb["Resultados"]
    ws.append([])
    ws.append(["Sustitución", sustitucion_retencion(inf)])
    hoja(wb.create_sheet("Verificaciones"), ["Criterio", "Valor", "Límite", "Estado", "Referencia"],
         [(v.criterio, v.valor, v.limite, v.estado, v.referencia) for v in inf.verificaciones], [50, 20, 20, 14, 50])
    hoja(wb.create_sheet("Ecuaciones y avisos"), ["Contenido"],
         [(x,) for x in ECUACIONES + [""] + [f"Advertencia: {a}" for a in inf.resultados.advertencias] + ["", AVISO]],
         [120])
    wb.save(ruta)
    return ruta


# ---------------------------------------------------------------------------- PDF
def exportar_pdf(inf: Informe, ruta: str) -> str:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    st = getSampleStyleSheet()
    normal = st["BodyText"]
    normal.fontSize = 8.5
    normal.leading = 10.5
    p = lambda t: Paragraph(str(t).replace("&", "&amp;").replace("<", "&lt;"), normal)

    def tabla(encabezado, filas, anchos):
        datos = [[p(x) for x in encabezado]] + [[p(c) for c in f] for f in filas]
        t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        return t

    doc = SimpleDocTemplate(ruta, pagesize=letter, leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                            topMargin=1.6 * cm, bottomMargin=1.6 * cm,
                            title=f"Tanque pulmón — {inf.caso.nombre}")
    h = st["Heading2"]
    cuerpo = [
        Paragraph(f"Cálculo de tanque pulmón de aire comprimido — {inf.caso.nombre}", st["Title"]),
        p(f"Documento: {inf.caso.documento} | Calculadora v{inf.version} | {inf.fecha} | huella de entradas {inf.huella}"),
        Spacer(1, 6),
        Paragraph("1. Datos de entrada", h), tabla(["Parámetro", "Valor", "Nota"], tabla_entradas(inf), [5.5, 6, 6]),
        Paragraph("2. Ecuaciones", h), *[p("• " + x) for x in ECUACIONES],
        Paragraph("3. Sustitución (tiempo de retención)", h), p(sustitucion_retencion(inf)),
        Paragraph("4. Resultados", h), tabla(["Resultado", "Valor", "Unidad"], tabla_resultados(inf), [9, 6, 2.5]),
        Paragraph("5. Verificaciones", h),
        tabla(["Criterio", "Valor", "Límite", "Estado", "Referencia"],
              [(v.criterio, v.valor, v.limite, v.estado, v.referencia) for v in inf.verificaciones],
              [5, 2.8, 2.6, 2.1, 5]),
    ]
    if inf.resultados.advertencias:
        cuerpo += [Paragraph("6. Advertencias", h)] + [p("• " + a) for a in inf.resultados.advertencias]
    if inf.caso.notas:
        cuerpo += [Paragraph("Notas", h), p(inf.caso.notas)]
    cuerpo += [Spacer(1, 10), p(AVISO)]
    doc.build(cuerpo)
    return ruta
