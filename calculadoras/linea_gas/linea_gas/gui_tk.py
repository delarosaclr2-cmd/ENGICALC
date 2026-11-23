"""Interfaz de la calculadora de líneas de gas. Integración ENGICALC: from linea_gas.gui_tk import abrir"""
import json
import os
import tkinter as tk

from . import __version__
from . import unidades as u
from .datos import GASES, REFERENCIAS, nps_lista, tipos_accesorio
from .presion import E_JUNTA
from .memoria import evaluar

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
SECCIONES = [
    ("Línea", [("nombre", "Nombre de la línea", None), ("documento", "Documento de referencia", None),
               ("gas", "Gas", list(GASES))]),
    ("Caudal y condiciones", [
        ("caudal.valor", "Caudal", None), ("caudal.unidad", "Unidad de caudal", u.UNIDADES_CAUDAL),
        ("caudal.referencia", "Referencia del caudal", list(REFERENCIAS)),
        ("p_entrada.valor", "Presión de entrada", None), ("p_entrada.unidad", "Unidad de presión", u.UNIDADES_PRESION),
        ("p_atm_psia", "Presión atmosférica del sitio (psia)", None),
        ("temperatura.valor", "Temperatura", None),
        ("temperatura.unidad", "Unidad de temperatura", u.UNIDADES_TEMPERATURA), ("z", "Factor Z", None)]),
    ("Tubería", [("longitud_m", "Longitud (m)", None), ("tuberia.nps", "NPS", nps_lista()),
                 ("tuberia.cedula", "Cédula", ["40", "80"]), ("tuberia.d_interior_mm", "Di capturado (mm, opcional)", None),
                 ("rugosidad_mm", "Rugosidad (mm)", None)]),
    ("Criterios del proyecto (opcionales)", [("criterios.v_min_m_s", "Velocidad mínima (m/s)", None),
                                             ("criterios.v_max_m_s", "Velocidad máxima (m/s)", None)]),
    ("Espesor y presión máxima (vacío = no evaluar)", [
        ("espesor.p_diseno.valor", "Presión de diseño", None),
        ("espesor.p_diseno.unidad", "Unidad", ["psig", "kPa g", "bar g", "kgf/cm² g", "MPa g"]),
        ("espesor.t_diseno_c", "Temperatura de diseño (°C)", None),
        ("espesor.s.tabla", "Tabla de S", ["", "A106B_B313"]),
        ("espesor.s.valor", "Esfuerzo admisible S", None), ("espesor.s.unidad", "Unidad", ["psi", "ksi", "MPa"]),
        ("espesor.s.fuente", "Fuente de S", None),
        ("espesor.e", "E del código", None), ("espesor.y", "Coeficiente Y", None),
        ("espesor.c_mm", "Sobreespesor c (mm)", None),
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
TABLAS = [("accesorios", "Accesorios: tipo y cantidad (tipos: " + ", ".join(tipos_accesorio()) + ")")]


def _base():
    with open(os.path.join(CASOS, "DM014E_L1_rack_4in.json"), encoding="utf-8") as fh:
        return json.load(fh)


def abrir(padre=None):
    from .ui.ventana import Ventana
    v = tk.Toplevel(padre) if padre is not None else tk.Tk()
    f = Ventana(v, f"Líneas de gas y aire comprimido — v{__version__}", SECCIONES, TABLAS, _base(), evaluar, CASOS)
    return v, f


def main():
    v, _ = abrir()
    v.mainloop()
    return 0
