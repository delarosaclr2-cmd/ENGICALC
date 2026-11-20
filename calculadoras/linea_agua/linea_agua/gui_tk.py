"""Interfaz de la línea de agua. ENGICALC: from linea_agua.gui_tk import abrir"""
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
    ("Caso", [("nombre", "Nombre del caso", None), ("documento", "Documento de referencia", None),
              ("servicio", "Servicio", ["descarga", "succion"])]),
    ("Agua", [("caudal.valor", "Caudal", None), ("caudal.unidad", "Unidad", u.UNIDADES_CAUDAL_LIQ),
              ("temperatura_c", "Temperatura (°C)", None),
              ("propiedades", "Propiedades", ["IF97", "capturadas"]),
              ("estado", "Estado (IF97)", ["saturado", "presion"]),
              ("presion.valor", "Presión de operación (si estado = presion)", None),
              ("presion.unidad", "Unidad", u.UNIDADES_PRESION),
              ("rho_kg_m3", "Densidad (si capturadas, kg/m³)", None), ("mu_cp", "Viscosidad (si capturadas, cP)", None),
              ("p_atm_kpa", "Presión atmosférica del sitio (kPa a)", None)]),
    ("Tubería", [("tuberia.nps", "NPS", nps_lista()), ("tuberia.cedula", "Cédula", ["40", "80"]),
                 ("tuberia.d_interior_mm", "Di capturado (mm; vacío = tabla)", None),
                 ("longitud_m", "Longitud (m)", None), ("rugosidad_mm", "Rugosidad (mm)", None),
                 ("dz_m", "Desnivel salida − entrada (m)", None)]),
    ("Criterio de velocidad", [("criterio_velocidad.v_min_m_s", "Mínima (m/s)", None),
                               ("criterio_velocidad.v_max_m_s", "Máxima (m/s)", None),
                               ("criterio_velocidad.fuente", "Fuente del criterio", None)]),
    ("NPSH (solo succión)", [("npsh.p_superficie.valor", "Presión en la superficie del líquido", None),
                             ("npsh.p_superficie.unidad", "Unidad", u.UNIDADES_PRESION),
                             ("npsh.nivel_m", "Nivel sobre el eje de la bomba (m)", None),
                             ("npsh.npshr_m", "NPSHr del fabricante (m)", None), ("npsh.margen_m", "Margen (m)", None)]),
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
    with open(os.path.join(CASOS, "DM012_deareador_a_HRSG_descarga_4in.json"), encoding="utf-8") as fh:
        base = json.load(fh)
    v = tk.Toplevel(padre) if padre is not None else tk.Tk()
    f = Ventana(v, f"Línea de agua — v{__version__}", SECCIONES, TABLAS, base, evaluar, CASOS)
    return v, f


def main():
    v, _ = abrir()
    v.mainloop()
    return 0
