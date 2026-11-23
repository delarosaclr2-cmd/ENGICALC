"""Interfaz de la línea de aceite. ENGICALC: from linea_aceite.gui_tk import abrir"""
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
              ("p_operacion", "Presión de operación (texto informativo)", None)]),
    ("Aceite", [("caudal.valor", "Caudal", None), ("caudal.unidad", "Unidad", u.UNIDADES_CAUDAL_LIQ),
                ("temperatura_c", "Temperatura de operación (°C)", None),
                ("viscosidad.modo", "Viscosidad", ["dos_puntos", "directa"]),
                ("viscosidad.t1_c", "Punto 1: temperatura (°C)", None), ("viscosidad.nu1_cst", "Punto 1: ν (cSt)", None),
                ("viscosidad.t2_c", "Punto 2: temperatura (°C)", None), ("viscosidad.nu2_cst", "Punto 2: ν (cSt)", None),
                ("viscosidad.nu_cst", "ν directa a la temperatura de operación (cSt)", None),
                ("densidad.rho_kg_m3", "Densidad (kg/m³)", None), ("densidad.t_ref_c", "T de referencia de ρ (°C, opcional)", None),
                ("densidad.alfa_1_c", "Coeficiente α (1/°C, opcional)", None), ("densidad.fuente", "Fuente de ρ", None)]),
    ("Tubería", [("tuberia.nps", "NPS", nps_lista()), ("tuberia.cedula", "Cédula", ["40", "80"]),
                 ("tuberia.d_interior_mm", "Di capturado (mm; vacío = tabla)", None),
                 ("longitud_m", "Longitud (m)", None), ("rugosidad_mm", "Rugosidad (mm)", None),
                 ("dz_m", "Desnivel salida − entrada (m)", None)]),
    ("Criterios", [("criterio_velocidad.v_min_m_s", "Velocidad mínima (m/s)", None),
                   ("criterio_velocidad.v_max_m_s", "Velocidad máxima (m/s)", None),
                   ("criterio_velocidad.fuente", "Fuente del criterio", None),
                   ("dp_max_kpa", "Caída de presión admisible (kPa)", None)]),
    ("Espesor de pared (vacío = no evaluar)", [
        ("espesor.codigo", "Código", ["B31.3", "B31.1"]),
        ("espesor.p_diseno.valor", "Presión de diseño", None), ("espesor.p_diseno.unidad", "Unidad", P_UNID),
        ("espesor.p_operacion.valor", "Presión de operación (opcional)", None),
        ("espesor.p_operacion.unidad", "Unidad", P_UNID),
        ("espesor.t_diseno_c", "Temperatura de diseño (°C)", None),
        ("espesor.s.tabla", "S de tabla (A106B_B313) o vacío", ["A106B_B313", ""]),
        ("espesor.s.valor", "S capturado (si no hay tabla)", None), ("espesor.s.unidad", "Unidad", ["psi", "ksi", "MPa"]),
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
    with open(os.path.join(CASOS, "DM017_turbina_a_enfriador_4in.json"), encoding="utf-8") as fh:
        base = json.load(fh)
    v = tk.Toplevel(padre) if padre is not None else tk.Tk()
    f = Ventana(v, f"Línea de aceite — v{__version__}", SECCIONES, TABLAS, base, evaluar, CASOS)
    return v, f


def main():
    v, _ = abrir()
    v.mainloop()
    return 0
