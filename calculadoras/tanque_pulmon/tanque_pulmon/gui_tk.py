"""Interfaz del tanque pulmón. Integración ENGICALC: from tanque_pulmon.gui_tk import abrir"""
import json
import os
import tkinter as tk

from . import __version__
from . import unidades as u
from .constantes import REFERENCIAS
from .memoria import evaluar
from .presion import E_JUNTA

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
ABS = ["psia", "kPa a", "bar a"]
REFS = list(REFERENCIAS)
SECCIONES = [
    ("Caso", [("nombre", "Nombre del caso", None), ("documento", "Documento de referencia", None)]),
    ("Tanque y banda de presión", [
        ("v_tanque.valor", "Volumen del tanque", None), ("v_tanque.unidad", "Unidad", u.UNIDADES_VOLUMEN),
        ("p_superior.valor", "Presión superior (descarga/paro)", None), ("p_superior.unidad", "Unidad", u.UNIDADES_PRESION),
        ("p_inferior.valor", "Presión inferior admisible", None), ("p_inferior.unidad", "Unidad", u.UNIDADES_PRESION),
        ("p_atm_sitio.valor", "Presión atmosférica del sitio", None), ("p_atm_sitio.unidad", "Unidad (absoluta)", ABS)]),
    ("Aire y caudales (aire libre)", [
        ("t_aire.valor", "Temperatura del aire en el sistema", None), ("t_aire.unidad", "Unidad", u.UNIDADES_TEMPERATURA),
        ("q_consumo.valor", "Caudal de consumo", None), ("q_consumo.unidad", "Unidad", u.UNIDADES_CAUDAL),
        ("q_consumo.referencia", "Referencia", REFS), ("margen_consumo_pct", "Margen de consumo (%)", None),
        ("q_compresor.valor", "FAD del compresor (vacío = no evaluar)", None),
        ("q_compresor.unidad", "Unidad", u.UNIDADES_CAUDAL), ("q_compresor.referencia", "Referencia", REFS),
        ("n_politropico", "Exponente de descarga n (1–1.4)", None),
        ("incluir_tuberia", "Incluir volumen de tubería", ["True", "False"])]),
    ("Criterios del proyecto (vacío = sin criterio)", [
        ("t_retencion_req_min", "Tiempo de retención requerido (min)", None),
        ("fraccion_carga_max_pct", "Fracción de carga máxima (%)", None),
        ("ciclos_h_max", "Ciclos por hora máximos", None),
        ("p_min_consumidor.valor", "Presión mínima en el consumidor", None),
        ("p_min_consumidor.unidad", "Unidad", u.UNIDADES_PRESION),
        ("dp_linea.valor", "ΔP tanque → consumidor", None), ("dp_linea.unidad", "Unidad", ["kPa", "psi", "bar"]),
        ("p_calibracion_psv.valor", "Calibración de la válvula de seguridad", None),
        ("p_calibracion_psv.unidad", "Unidad", u.UNIDADES_PRESION)]),
    ("Material de la tubería conectada (vacío = no evaluar)", [
        ("espesor.s.valor", "Esfuerzo admisible S", None),
        ("espesor.s.unidad", "Unidad", ["psi", "ksi", "MPa"]),
        ("espesor.s.fuente", "Fuente de S", None),
        ("espesor.p_diseno.valor", "Presión de diseño de la tubería", None),
        ("espesor.p_diseno.unidad", "Unidad", ["psig", "kPa g", "bar g", "kgf/cm² g", "MPa g"]),
        ("espesor.e", "E del código", None), ("espesor.y", "Coeficiente Y", None),
        ("espesor.c_mm", "Sobreespesor c (mm)", None),
        ("espesor.c_por_ano_in", "Corrosión por año (in/año)", None),
        ("espesor.vida_util_anos", "Vida útil (años)", None),
        ("espesor.tolerancia_pct", "Tolerancia de fabricación (%)", None)]),
    ("Presión máxima por Barlow de la tubería (vacío = no evaluar)", [
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
TABLAS = [("tramos", "Tubería conectada: descripcion, longitud_m, nps + cedula o d_interior_mm")]


def _base():
    with open(os.path.join(CASOS, "PCGV-DM-014E_casoA_100Nm3h.json"), encoding="utf-8") as fh:
        return json.load(fh)


def abrir(padre=None):
    from .ui.ventana import Ventana
    v = tk.Toplevel(padre) if padre is not None else tk.Tk()
    f = Ventana(v, f"Tanque pulmón de aire comprimido — v{__version__}", SECCIONES, TABLAS, _base(), evaluar, CASOS)
    return v, f


def main():
    v, _ = abrir()
    v.mainloop()
    return 0
