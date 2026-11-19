"""Genera el banco de pruebas industrial: nave con 4 campanas, red ramificada,
colector de mangas, ventilador y chimenea (Valle de México, 2 240 m).

IMPORTANTE: las curvas de ventilador de este ejemplo son SINTÉTICAS (de
demostración); no corresponden a ningún fabricante. Las pérdidas del colector son
hipótesis del banco de pruebas y deben sustituirse por datos del fabricante.

Uso:  python examples/build_example.py
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.project import (Project, ProjectInfo, AirInput, AirflowInputs, Hood, NetworkSettings, FanSelection,
                          PowerInputs, DuctTool, Alternative)
from core.hood_design import HoodEntry
from core.network_solver import NetworkModel, NetNode, NetSegment
from core.fittings import FittingInstance as F
from core.equipment import Equipment
from core.fan_curves import FanCurve


def fan(fid, model, ftype, rpm, Q, P, eta, max_rpm, outlet_area, notes):
    pts = [{"Q": q, "P": p, "eta": e, "W": q * p / e} for q, p, e in zip(Q, P, eta)]
    return FanCurve(id=fid, manufacturer="EJEMPLO (curva sintética)", model=model, fan_type=ftype, rpm=rpm,
                    rho_ref=1.2, diameter_m=None, outlet_area_m2=outlet_area, pressure_basis="total", points=pts,
                    max_rpm=max_rpm, certified=False,
                    source="Curva sintética de demostración — NO es dato de fabricante", notes=notes)


def build() -> Project:
    p = Project()
    p.info = ProjectInfo(
        name="Banco de pruebas — Nave industrial con 4 campanas", client="Caso de validación interno",
        location="Valle de México (altitud 2 240 m)", engineer="", revision="0",
        ventilation_type="Extracción localizada industrial (polvo y humos de soldadura)",
        description="Nave con estación de vaciado de sacos, mesa de soldadura, cabina de llenado de sacos y punto de "
                    "transferencia de banda conectados a un colector de mangas.",
        objective="Capturar polvo industrial y humos de soldadura en su origen, transportarlos sin sedimentación al "
                  "colector de mangas y descargar aire filtrado por chimenea.")
    p.air = AirInput(mode="custom", t_c=25.0, altitude_m=2240.0, p_pa=None, rh=0.5, t_min_surface_c=18.0)
    p.airflow = AirflowInputs()
    p.airflow.ach = {"enabled": True, "L": 40.0, "W": 20.0, "H": 8.0, "ACH": 4.0, "V": None}
    p.airflow.dilution = {"enabled": False, "G_mg_s": 10.0, "C_target": 5.0, "C_bg": 0.0, "K": 3.0, "capture_eff": 0.0,
                          "C0": None, "toxicity_known": False}
    p.airflow.thermal = {"enabled": True, "sources_W": [25000.0, 15000.0], "t_in": 25.0, "t_out": 31.0}
    p.airflow.purpose = "general"

    p.hoods = [
        Hood("C1", "Estación de vaciado de sacos", "exterior_flanged", {"W": 0.60, "H": 0.45, "X": 0.25, "Vc": 1.0},
             "flanged_duct_end", HoodEntry("fh", 0.49), "average_industrial", "Vaciado manual de sacos de 25 kg"),
        Hood("C2", "Mesa de soldadura", "slot_flanged", {"L": 1.0, "Ws": 0.05, "X": 0.30, "Vc": 0.5},
             "flanged_duct_end", HoodEntry("slot", Fh=0.49, Fs=1.78, slot_area=0.05, plenum_loss=False), "fumes",
             "Soldadura GMAW en banco"),
        Hood("C3", "Cabina de llenado de sacos", "booth", {"W": 1.0, "H": 1.0, "Vc": 0.75},
             "flanged_duct_end", HoodEntry("fh", 0.49), "average_industrial", "Ensacadora"),
        Hood("C4", "Transferencia de banda (encerramiento)", "enclosure", {"A_open": 0.38, "Vc": 1.0},
             "flanged_duct_end", HoodEntry("fh", 0.49), "average_industrial", "Punto de transferencia"),
    ]
    m = NetworkModel()
    for nd in [NetNode("H1", "hood", "Vaciado", hood_id="C1"), NetNode("H2", "hood", "Soldadura", hood_id="C2"),
               NetNode("H3", "hood", "Llenado", hood_id="C3"), NetNode("H4", "hood", "Banda", hood_id="C4"),
               NetNode("J1", "junction", "Unión 1"), NetNode("J2", "junction", "Unión 2"),
               NetNode("J3", "junction", "Unión 3"), NetNode("COL", "junction", "Salida colector"),
               NetNode("FAN", "fan", "Ventilador"),
               NetNode("OUT", "outlet", "Chimenea", exit_K=1.0, stack_height_above_roof_m=3.5)]:
        m.nodes[nd.id] = nd
    E = F
    m.segments = [
        NetSegment("R1", "H1", "J1", "circular", 0.200, length=6.0, fittings=[E("elbow90_RD2.0", 2)]),
        NetSegment("R2", "H2", "J1", "circular", 0.160, length=4.0,
                   fittings=[E("elbow90_RD2.0", 1), E("elbow45_RD2.0", 1), E("branch_entry_30", 1)]),
        NetSegment("M1", "J1", "J2", "circular", 0.250, length=8.0),
        NetSegment("R3", "H3", "J2", "circular", 0.200, length=5.0, fittings=[E("elbow90_RD2.0", 2), E("branch_entry_30", 1)]),
        NetSegment("M2", "J2", "J3", "circular", 0.315, length=8.0),
        NetSegment("R4", "H4", "J3", "circular", 0.150, length=12.0, fittings=[E("elbow90_RD2.0", 1), E("branch_entry_45", 1)]),
        NetSegment("M3", "J3", "COL", "circular", 0.355, length=12.0, fittings=[E("elbow90_RD2.0", 2)],
                   equipment=[Equipment("Colector de mangas", "Colector de polvo (mangas)", "filter", q_ref=2.3,
                                        n_exp=1.0, dp_clean=600.0, dp_dirty=1500.0, state="sucio",
                                        source="Hipótesis del banco de pruebas (sustituir por dato del fabricante)")]),
        NetSegment("M4", "COL", "FAN", "circular", 0.500, length=3.0, fittings=[E("elbow90_RD2.0", 1)]),
        NetSegment("D1", "FAN", "OUT", "circular", 0.450, length=10.0),
    ]
    p.network = m
    p.network_settings = NetworkSettings("average_industrial", "acgih", "sucio", roof_height_m=9.0)
    Q = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
    p.fans = [
        fan("BI-560", "EJEMPLO BI-560 (inclinado hacia atrás)", "Centrífugo", 2200, Q,
            [3300, 3450, 3450, 3300, 3020, 2620, 2100, 1450], [0.45, 0.62, 0.72, 0.78, 0.80, 0.78, 0.70, 0.55],
            2600, 0.16, "Rodete de álabes inclinados hacia atrás; lado limpio."),
        fan("RT-500", "EJEMPLO RT-500 (punta radial)", "Centrífugo", 2600, Q,
            [3400, 3420, 3380, 3280, 3120, 2900, 2600, 2200], [0.40, 0.55, 0.63, 0.67, 0.68, 0.66, 0.60, 0.50],
            3000, 0.14, "Rodete de punta radial; mayor tolerancia a la abrasión, menor eficiencia."),
        fan("BI-450", "EJEMPLO BI-450 (subdimensionado)", "Centrífugo", 2200, Q,
            [2600, 2700, 2650, 2450, 2150, 1750, 1250, 700], [0.45, 0.62, 0.72, 0.78, 0.79, 0.76, 0.66, 0.50],
            2600, 0.12, "Ventilador pequeño para demostrar el déficit de caudal."),
    ]
    p.fan_selection = FanSelection("BI-560", None, None)
    p.power = PowerInputs(eta_fan_user=0.75, eta_basis="total", drive_type="Bandas", eta_drive=0.95, eta_motor=0.917,
                          use_vfd=False, eta_vfd=0.97, margin=0.10, service_factor=1.15, motor_standard="IEC",
                          motor_selected_kw=None, hours_per_year=4800.0, tariff=2.40, currency="MXN",
                          profile=[[1.0, 0.6], [0.85, 0.3], [0.7, 0.1]])
    p.duct_tool = DuctTool(method="velocity", Q=2.3, V_target=21.0, shape="circular", material_id="galv_ashrae",
                           rounding="down")
    return p


def alternatives(base: Project) -> list[Alternative]:
    import copy
    alts = [Alternative("A — Diseño base (BI-560, 2 200 rpm)", copy.deepcopy(base.to_dict(include_alternatives=False)),
                        complexity=3, maintenance=3, notes="Diámetros para velocidad de transporte corregida por densidad.")]
    b = Project.from_dict(base.to_dict(include_alternatives=False))
    for s in b.network.segments:
        if s.id == "M1":
            s.D = 0.280
        if s.id == "M2":
            s.D = 0.355
        if s.id == "M3":
            s.D = 0.400
    # Comparación justa: con menor resistencia y velocidad fija el ventilador movería MÁS aire y consumiría
    # más potencia; por eso la alternativa B ajusta las rpm para pasar por su punto de diseño.
    from config.settings import load_settings
    from database.db import load_db
    from core.calculation import run_project
    rb = run_project(b, load_db(), load_settings())
    if rb.selected_fan and rb.selected_fan.rpm_required:
        b.fan_selection.rpm = round(rb.selected_fan.rpm_required + 5.0, -1)
    alts.append(Alternative("B — Principal un diámetro mayor y rpm ajustadas", b.to_dict(include_alternatives=False),
                            complexity=3, maintenance=4,
                            notes="Menor velocidad en el principal; rpm ajustadas a su punto de diseño."))
    c = Project.from_dict(base.to_dict(include_alternatives=False))
    c.fan_selection.selected_id = "RT-500"
    alts.append(Alternative("C — Ventilador de punta radial RT-500", c.to_dict(include_alternatives=False),
                            complexity=3, maintenance=2, notes="Mayor robustez ante abrasión; menor eficiencia."))
    d = Project.from_dict(base.to_dict(include_alternatives=False))
    d.fan_selection.selected_id = "BI-450"
    alts.append(Alternative("D — Ventilador pequeño BI-450", d.to_dict(include_alternatives=False),
                            complexity=2, maintenance=3, notes="Menor costo de equipo."))
    return alts


if __name__ == "__main__":
    proj = build()
    proj.alternatives = alternatives(proj)
    out = os.path.join(ROOT, "examples", "nave_industrial_4_campanas.hvac.json")
    proj.save(out)
    # curva de ejemplo en CSV para probar la importación
    with open(os.path.join(ROOT, "examples", "curva_ventilador_ejemplo.csv"), "w", encoding="utf-8") as fh:
        fh.write("Q,P,eta,W\n")
        for pt in proj.fans[0].points:
            fh.write(f"{pt['Q']},{pt['P']},{pt['eta']},{pt['W']:.1f}\n")
    print("Ejemplo escrito en", out)
