"""Interfaz de la calculadora de gas combustible. ENGICALC: from gas_combustible.gui_tk import abrir"""
import json
import os
import tkinter as tk

from . import __version__
from . import unidades as u
from .memoria import evaluar

CASOS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "casos")
SECCIONES = [
    ("Caso", [("nombre", "Nombre del caso", None), ("documento", "Documento de referencia", None),
              ("referencia", "Condición de referencia", ["estandar_60F", "estandar_15C", "normal"]),
              ("z_ref", "Z a la referencia (vacío = CoolProp)", None),
              ("lhv_laboratorio_mj_m3", "LHV del laboratorio (MJ/m³)", None)]),
    ("Turbina", [("turbina.nombre", "Nombre", None), ("turbina.heat_rate_kj_kwh", "Tasa de calor (kJ/kWh)", None),
                 ("turbina.potencia_kw", "Potencia eléctrica (kW)", None),
                 ("turbina.lhv_kj_kg", "LHV del fabricante (kJ/kg; vacío = laboratorio)", None)]),
    ("Condición de la línea (opcional)", [("linea.p.valor", "Presión", None),
                                          ("linea.p.unidad", "Unidad", u.UNIDADES_PRESION),
                                          ("linea.t_c", "Temperatura (°C)", None)]),
]
TABLAS = [("composicion", "Composición: componente, pct_mol"), ("consumidores_kg_h", "Otros consumidores: nombre, kg_h")]


def _base():
    with open(os.path.join(CASOS, "PCGV_cogeneracion5_turbina_LT16.json"), encoding="utf-8") as fh:
        c = json.load(fh)
    c["composicion"] = [{"componente": k, "pct_mol": v} for k, v in c["composicion"].items()]
    return c



def abrir(padre=None):
    from .ui.ventana import Ventana

    class V(Ventana):
        def poner(self, caso):
            caso = dict(caso)
            if isinstance(caso.get("composicion"), dict):
                caso["composicion"] = [{"componente": k, "pct_mol": v} for k, v in caso["composicion"].items()]
            super().poner(caso)

    v = tk.Toplevel(padre) if padre is not None else tk.Tk()
    f = V(v, f"Gas combustible — v{__version__}", SECCIONES, TABLAS, _base(), evaluar, CASOS)
    return v, f


def main():
    v, _ = abrir()
    v.mainloop()
    return 0
