"""Interfaz de la línea de vapor. ENGICALC: from linea_vapor.gui_tk import abrir"""
import json
import os
import tkinter as tk

from . import __version__
from .memoria import evaluar
from .nucleo import unidades as u
from .nucleo.presion import E_JUNTA
from .nucleo.tubos import nps_lista

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
P_UNID = ["psig", "kPa g", "bar g", "kgf/cm² g", "MPa g"]
SECCIONES = [
    ("Caso", [("nombre", "Nombre del caso", None), ("documento", "Documento de referencia", None)]),
    ("Vapor", [("flujo.valor", "Flujo másico", None), ("flujo.unidad", "Unidad", u.UNIDADES_MASICO),
               ("p_entrada.valor", "Presión de entrada", None), ("p_entrada.unidad", "Unidad", u.UNIDADES_PRESION),
               ("estado", "Estado", ["saturado", "sobrecalentado", "titulo"]),
               ("temperatura_c", "Temperatura (si sobrecalentado, °C)", None), ("titulo", "Título x (si húmedo)", None),
               ("p_atm_kpa", "Presión atmosférica del sitio (kPa a)", None)]),
    ("Tubería", [("tuberia.nps", "NPS", nps_lista()), ("tuberia.cedula", "Cédula", ["40", "80"]),
                 ("tuberia.d_interior_mm", "Di capturado (mm; vacío = tabla)", None),
                 ("longitud_m", "Longitud (m; 0 = solo velocidad)", None), ("rugosidad_mm", "Rugosidad (mm)", None)]),
    ("Criterios", [("criterio_velocidad.v_min_m_s", "Velocidad mínima (m/s)", None),
                   ("criterio_velocidad.v_max_m_s", "Velocidad máxima (m/s)", None),
                   ("criterio_velocidad.fuente", "Fuente del criterio", None),
                   ("dp_max_kpa", "Caída de presión admisible (kPa)", None)]),
    ("Venteo a silenciador (opcional)", [("venteo.p_descarga.valor", "Presión de descarga", None),
                                          ("venteo.p_descarga.unidad", "Unidad", u.UNIDADES_PRESION)]),
    ("Espesor de pared (vacío = no evaluar)", [
        ("espesor.codigo", "Código", ["B31.1", "B31.3"]),
        ("espesor.p_diseno.valor", "Presión de diseño", None), ("espesor.p_diseno.unidad", "Unidad", P_UNID),
        ("espesor.p_operacion.valor", "Presión de operación (opcional)", None),
        ("espesor.p_operacion.unidad", "Unidad", P_UNID),
        ("espesor.t_diseno_c", "Temperatura de diseño (°C)", None),
        ("espesor.s.tabla", "Tabla de S", ["", "A106B_B313"]),
        ("espesor.s.valor", "Esfuerzo admisible S", None), ("espesor.s.unidad", "Unidad", ["psi", "ksi", "MPa"]),
        ("espesor.s.fuente", "Fuente de S", None),
        ("espesor.y", "Coeficiente Y", None), ("espesor.c_mm", "Sobreespesor c (mm)", None),
        ("espesor.c_por_ano_in", "Corrosión por año (in/año)", None),
        ("espesor.vida_util_anos", "Vida útil (años)", None),
        ("espesor.tolerancia_pct", "Tolerancia de fabricación (%)", None)]),
    ("Presión máxima por Barlow (vacío = no evaluar)", [
        ("espesor.barlow.s_cedencia.valor", "Cedencia SMYS", None),
        ("espesor.barlow.s_cedencia.unidad", "Unidad", ["psi", "ksi", "MPa"]),
        ("espesor.barlow.s_cedencia.fuente", "Fuente de la cedencia", None),
        ("espesor.barlow.clase_localizacion", "Clase de localización (F)", ["", "1", "2", "3", "4"]),
        ("espesor.barlow.f", "F capturado (anula la clase)", None),
        ("espesor.barlow.junta", "Junta longitudinal (E)", [""] + list(E_JUNTA)),
        ("espesor.barlow.e", "E capturado", None),
        ("espesor.barlow.t", "T capturado (vacío = por temperatura)", None),
        ("espesor.barlow.aplica_nom", "Es transporte de gas natural por ducto", ["false", "true"])]),
]
TABLAS = [("accesorios", "Accesorios: tipo, cantidad (k opcional). Tipos: codo90, codo45, codo90_radio_largo, te_paso, "
                         "te_rama, compuerta, globo, angulo, bola, check_columpio, check_levantamiento")]


def abrir(padre=None):
    from .ui.ventana import Ventana
    with open(os.path.join(CASOS, "DM011_principal_cog_V_VI_a_M3_12in.json"), encoding="utf-8") as fh:
        base = json.load(fh)
    v = tk.Toplevel(padre) if padre is not None else tk.Tk()
    f = Ventana(v, f"Línea de vapor — v{__version__}", SECCIONES, TABLAS, base, evaluar, CASOS)
    return v, f


def main():
    v, _ = abrir()
    v.mainloop()
    return 0
