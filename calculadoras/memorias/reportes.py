"""Casos y exportaciones nativas de las memorias completas."""
from __future__ import annotations
import json
import math
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from .comun import exigir

LOGO=Path(__file__).resolve().parents[2]/"recursos"/"RMR_transparente.png"


def texto(valor):
    if valor is None:return "—"
    if isinstance(valor,bool):return "Sí" if valor else "No"
    if isinstance(valor,(float,int)):
        if not math.isfinite(valor):return "—"
        return f"{valor:,.6g}"
    return str(valor)


def aplanar(datos,prefijo=""):
    if isinstance(datos,dict):
        for k,v in datos.items():yield from aplanar(v,f"{prefijo}.{k}" if prefijo else k)
    elif isinstance(datos,list):
        for i,v in enumerate(datos):yield from aplanar(v,f"{prefijo}[{i+1}]")
    else:yield prefijo,texto(datos)


def guardar_caso(ruta,memoria,estado,documento,unidades="SI"):
    contenido=dict(formato="RMR-memoria",version=1,calculadora=memoria.id,datos=estado,documento=documento,preferencias={"unidades":unidades})
    serializado=json.dumps(contenido,ensure_ascii=False,indent=2,allow_nan=False)
    destino=Path(ruta);temporal=destino.with_name(destino.name+".tmp")
    temporal.write_text(serializado,encoding="utf-8");temporal.replace(destino)


def abrir_caso(ruta):
    contenido=json.loads(Path(ruta).read_text(encoding="utf-8"))
    exigir(isinstance(contenido,dict) and contenido.get("formato")=="RMR-memoria" and contenido.get("version")==1,"El archivo no es un caso de memoria RMR compatible.")
    exigir(isinstance(contenido.get("datos"),dict) and isinstance(contenido.get("documento",{}),dict),"El caso no contiene datos válidos.")
    exigir(isinstance(contenido.get("preferencias",{}),dict) and contenido.get("preferencias",{}).get("unidades","SI") in ["SI","US"],"Preferencia de unidades no válida.")
    from . import POR_ID
    exigir(contenido.get("calculadora") in POR_ID,"La memoria de este caso no está instalada.")
    # Se valida antes de reemplazar cualquier dato en una ventana.
    try:
        POR_ID[contenido["calculadora"]].motor.calcular(contenido["datos"])
    except (KeyError,TypeError,ArithmeticError) as error:
        from ..nucleo.modelo import ErrorEntrada
        raise ErrorEntrada("El caso tiene datos incompletos o no válidos: "+str(error)) from error
    return contenido


def exportar_pdf(ruta,memoria,estado,resultado,documento,figura):
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,Image,PageBreak,KeepTogether
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "RMRUnicode" not in pdfmetrics.getRegisteredFontNames():
        from matplotlib.font_manager import findfont
        pdfmetrics.registerFont(TTFont("RMRUnicode",findfont("DejaVu Sans")))
    estilos=getSampleStyleSheet()
    for style in estilos.byName.values():style.fontName="RMRUnicode"
    estilos.add(ParagraphStyle("RMRcell",fontName="RMRUnicode",fontSize=8,leading=11,alignment=TA_LEFT,wordWrap="CJK"))
    par=lambda t:Paragraph(escape(texto(t)),estilos["RMRcell"])
    story=[]
    if LOGO.is_file():story.extend([Image(str(LOGO),width=48*mm,height=48*mm*74/315,hAlign="LEFT"),Spacer(1,5*mm)])
    story += [Paragraph(escape(memoria.nombre),estilos["Title"]),Spacer(1,3*mm)]
    def tabla(rows,widths):
        t=Table([[par(c) for c in r] for r in rows],colWidths=widths,repeatRows=1,hAlign="LEFT")
        t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#eaf2f3")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#246c75")),("VALIGN",(0,0),(-1,-1),"TOP"),("LINEBELOW",(0,0),(-1,-1),.35,colors.HexColor("#e1e6eb")),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        return t
    story += [tabla([["Dato del documento","Valor"]]+list(documento.items()),[48*mm,137*mm]),Spacer(1,5*mm)]
    if resultado["warnings"]:
        story += [Paragraph("Observaciones del cálculo",estilos["Heading2"])]
        story += [par("• "+w) for w in resultado["warnings"]]
    story += [Paragraph("Resultados",estilos["Heading2"]),tabla([["Resultado","Valor","Unidad"]]+[[r["etiqueta"],texto(r["valor"]),r["unidad"]] for r in resultado["rows"]],[105*mm,48*mm,32*mm])]
    story += [PageBreak(),Paragraph("Esquema y curvas",estilos["Heading2"])]
    buffer=BytesIO();figura.savefig(buffer,format="png",dpi=150,facecolor="white",bbox_inches="tight");buffer.seek(0)
    from PIL import Image as PILImage
    with PILImage.open(buffer) as pic:w,h=pic.size
    width=min(180*mm,210*mm*w/h);height=width*h/w;buffer.seek(0)
    story += [Image(buffer,width=width,height=height),Spacer(1,5*mm),Paragraph("Ecuaciones y alcance",estilos["Heading2"])]
    story += [par(e) for e in resultado["equations"]]
    if resultado.get("references"):
        story += [Spacer(1,4*mm),Paragraph("Fuentes y alcance",estilos["Heading2"])]
        story += [par(e) for e in resultado["references"]]
    story += [PageBreak(),Paragraph("Datos de entrada · unidades SI internas",estilos["Heading2"])]
    if "inputs" in estado:
        schema={f["id"]:f for f in memoria.motor.catalogo(memoria.modulo)["fields"]}
        entradas=[(schema.get(k,{}).get("label",k)+f" [{k}]",v) for k,v in estado["inputs"].items()]
        extra={k:v for k,v in estado.items() if k!="inputs"}
        entradas+=list(aplanar(extra))
    else:entradas=list(aplanar(estado))
    story += [tabla([["Parámetro / ruta del dato","Valor SI"]]+entradas,[125*mm,60*mm])]
    def pie(canvas,doc):
        canvas.setFont("Helvetica",8);canvas.setFillColor(colors.HexColor("#73818f"));canvas.drawRightString(200*mm,10*mm,f"RMR · {doc.page}")
    SimpleDocTemplate(str(ruta),pagesize=letter,leftMargin=15*mm,rightMargin=15*mm,topMargin=14*mm,bottomMargin=17*mm,title=memoria.nombre,author=documento.get("Elaboró","RMR")).build(story,onFirstPage=pie,onLaterPages=pie)


def exportar_excel(ruta,memoria,estado,resultado,documento):
    from openpyxl import Workbook
    from openpyxl.styles import Font,PatternFill,Alignment
    wb=Workbook();ws=wb.active;ws.title="Resultados";ws.append([memoria.nombre]);ws.append(["Resultado","Valor","Unidad"])
    for r in resultado["rows"]:ws.append([r["etiqueta"],r["valor"],r["unidad"]])
    for nombre,rows in [("Documento",list(documento.items())),("Entradas SI",list(aplanar(estado))),("Ecuaciones",[[e] for e in resultado["equations"]]),("Fuentes",[[e] for e in resultado.get("references",[])]),("Observaciones",[[w] for w in resultado["warnings"]])]:
        hoja=wb.create_sheet(nombre)
        for row in rows:hoja.append(row)
    for hoja in wb:
        hoja.freeze_panes="A2"
        for cell in hoja[1]:cell.font=Font(bold=True,color="246C75");cell.fill=PatternFill("solid",fgColor="EAF2F3")
        for row in hoja:
            for cell in row:
                # Treat arbitrary project names and TAGs as text, never formulas.
                if isinstance(cell.value,str):cell.data_type="s"
                cell.alignment=Alignment(vertical="top",wrap_text=True)
        hoja.column_dimensions["A"].width=65;hoja.column_dimensions["B"].width=30;hoja.column_dimensions["C"].width=20
    wb.save(ruta)
