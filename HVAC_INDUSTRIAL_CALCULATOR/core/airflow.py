"""Cálculo de caudales de ventilación general.

Métodos:
A. Renovaciones por hora (ACH):            Q = V·ACH/3600
B. Velocidad de captura → ver ``hood_design.py`` (ecuaciones por geometría)
C. Balance de contaminantes (dilución, mezcla con factor K):
       Q = K·G·(1 − ηc)/(C_obj − C_fondo)
   y modelo transitorio de mezcla perfecta:
       C(t) = C_ss + (C0 − C_ss)·exp(−Q't/V),  Q' = Q/K,  C_ss = C_fondo + G'/Q'
D. Balance térmico sensible:
       ṁ_as = q/(cp·Δt),   Q_entrada = ṁ_as·v_entrada
   (forma simplificada Q = q/(ρ·cp·Δt) mostrada como comparación)
E. Ventilación por ocupación (procedimiento de tasa de ventilación, ASHRAE 62.1):
       Vbz = Rp·Pz + Ra·Az,   Voz = Vbz/Ez
   Rp, Ra y Ez deben tomarse de la edición vigente de ASHRAE 62.1 (no se incluyen
   valores tabulados en el programa).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .air_properties import AirState, air_state_from_W
from .trace import Trace, n, KIND_EXTERNAL

MODULE = "Caudales"
SRC_ACGIH_DIL = "ACGIH, Industrial Ventilation Manual — ventilación por dilución (factor K de mezcla)"
SRC_ASHRAE_621 = "ANSI/ASHRAE Standard 62.1 — Ventilation Rate Procedure (ec. Vbz = Rp·Pz + Ra·Az)"


class AirflowError(ValueError):
    pass


@dataclass
class AirflowResult:
    method: str
    Q: float                                # m³/s (a las condiciones indicadas)
    details: dict = field(default_factory=dict)
    trace: Trace = field(default_factory=Trace)
    notes: list[str] = field(default_factory=list)


def airflow_ach(length: float, width: float, height: float, ach: float, volume: float | None = None) -> AirflowResult:
    """Caudal por renovaciones por hora. Si ``volume`` se indica, prevalece sobre L·A·H."""
    tr = Trace()
    if volume is None or volume <= 0:
        if min(length, width, height) <= 0:
            raise AirflowError("Las dimensiones del recinto deben ser positivas")
        volume = length * width * height
        tr.add(MODULE, "Volumen del recinto", "V = L·A·H",
               [("L", length, "m", "Largo"), ("A", width, "m", "Ancho"), ("H", height, "m", "Altura")],
               f"V = {n(length)}·{n(width)}·{n(height)}", volume, "m³", "Geometría")
    if ach <= 0:
        raise AirflowError("El número de renovaciones por hora debe ser positivo")
    Q = volume * ach / 3600.0
    tr.add(MODULE, "Caudal por renovaciones por hora", "Q = V·ACH/3600",
           [("V", volume, "m³", "Volumen"), ("ACH", ach, "1/h", "Renovaciones por hora")],
           f"Q = {n(volume)}·{n(ach)}/3600", Q, "m³/s", "Definición de renovaciones por hora",
           notes="El valor de ACH es un dato de diseño; no garantiza por sí mismo el control de contaminantes.")
    res = AirflowResult("ACH", Q, {"V": volume, "ACH": ach}, tr)
    res.notes.append("Las renovaciones por hora no consideran la tasa de generación ni la toxicidad del "
                     "contaminante; para control de exposición use balance de contaminantes o captura localizada.")
    return res


def airflow_dilution(G_mg_s: float, C_target: float, C_background: float = 0.0, K_mixing: float = 1.0,
                     capture_eff: float = 0.0, volume: float | None = None, C0: float | None = None) -> AirflowResult:
    """Caudal de dilución en estado estacionario con factor de mezcla K.

    Parámetros
    ----------
    G_mg_s : tasa de generación del contaminante [mg/s].
    C_target : concentración objetivo en el recinto [mg/m³] (p. ej. fracción del VLE de NOM-010-STPS
               o TLV de ACGIH; dato del usuario).
    C_background : concentración en el aire de reposición [mg/m³].
    K_mixing : factor de mezcla incompleta (≥ 1). ACGIH indica seleccionarlo según la eficacia de
               mezcla y la distribución del aire; consulte el manual.
    capture_eff : fracción de la generación capturada por extracción localizada (0–1).
    volume, C0 : opcionales para el análisis transitorio de purga.
    """
    tr = Trace()
    if G_mg_s < 0:
        raise AirflowError("La tasa de generación no puede ser negativa")
    if not (0.0 <= capture_eff < 1.0):
        raise AirflowError("La eficiencia de captura debe estar en [0, 1)")
    if K_mixing < 1.0:
        raise AirflowError("El factor de mezcla K debe ser ≥ 1 (K = 1 equivale a mezcla perfecta)")
    if C_target <= C_background:
        raise AirflowError("La concentración objetivo debe ser mayor que la concentración de fondo: "
                           "con aire de reposición contaminado la dilución no puede alcanzar el objetivo")
    G_eff = G_mg_s * (1.0 - capture_eff)
    if capture_eff > 0:
        tr.add(MODULE, "Generación residual no capturada", "G' = G·(1 − ηc)",
               [("G", G_mg_s, "mg/s", "Generación"), ("ηc", capture_eff, "-", "Eficiencia de captura")],
               f"G' = {n(G_mg_s)}·(1 − {n(capture_eff)})", G_eff, "mg/s", "Balance de masa")
    Q = K_mixing * G_eff / (C_target - C_background)
    tr.add(MODULE, "Caudal de dilución (estado estacionario)", "Q = K·G'/(C_obj − C_fondo)",
           [("K", K_mixing, "-", "Factor de mezcla incompleta"), ("G'", G_eff, "mg/s", ""),
            ("C_obj", C_target, "mg/m³", "Concentración objetivo"), ("C_fondo", C_background, "mg/m³", "Fondo")],
           f"Q = {n(K_mixing)}·{n(G_eff)}/({n(C_target)} − {n(C_background)})", Q, "m³/s",
           SRC_ACGIH_DIL + "; balance de masa en mezcla perfecta",
           notes="K se elige por criterio del diseñador: ver ACGIH. El modelo supone concentración uniforme.")
    det = {"G": G_mg_s, "G_eff": G_eff, "C_target": C_target, "C_bg": C_background, "K": K_mixing,
           "capture_eff": capture_eff}
    res = AirflowResult("Dilución", Q, det, tr)
    res.notes.append("Modelo de mezcla perfecta corregido con K: no representa gradientes cerca de la fuente; "
                     "la exposición en la zona respiratoria del trabajador puede superar el promedio del recinto.")
    res.notes.append("La dilución no es adecuada para contaminantes de alta toxicidad, fuentes puntuales intensas "
                     "o generación variable; en esos casos prefiera captura localizada.")
    if volume and volume > 0 and C0 is not None:
        Qe = Q / K_mixing
        C_ss = C_background + G_eff / Qe
        tau = volume / Qe
        det.update({"volume": volume, "C0": C0, "C_ss": C_ss, "tau_s": tau})
        tr.add(MODULE, "Constante de tiempo del recinto", "τ = V·K/Q", [("V", volume, "m³", ""), ("Q/K", Qe, "m³/s", "")],
               f"τ = {n(volume)}/{n(Qe)}", tau, "s", "Modelo transitorio de mezcla perfecta")
        if C0 > C_target:
            t_reach = time_to_concentration(C_target * 1.0001, volume, Q, G_eff, K_mixing, C0, C_background)
            det["t_reach_s"] = t_reach
            tr.add(MODULE, "Tiempo para alcanzar C_obj desde C0", "t = −τ·ln[(C_obj − C_ss)/(C0 − C_ss)]",
                   [("C0", C0, "mg/m³", ""), ("C_ss", C_ss, "mg/m³", ""), ("τ", tau, "s", "")],
                   f"t = −{n(tau)}·ln[({n(C_target)} − {n(C_ss)})/({n(C0)} − {n(C_ss)})]", t_reach, "s",
                   "Solución analítica de dC/dt = (G' − Q'(C − C_fondo))/V")
    return res


def concentration_vs_time(t_s: float, volume: float, Q: float, G_eff: float, K_mixing: float, C0: float,
                          C_background: float = 0.0) -> float:
    """C(t) en un recinto de mezcla perfecta con caudal efectivo Q/K."""
    Qe = Q / K_mixing
    C_ss = C_background + G_eff / Qe
    return C_ss + (C0 - C_ss) * math.exp(-Qe * t_s / volume)


def time_to_concentration(C_t: float, volume: float, Q: float, G_eff: float, K_mixing: float, C0: float,
                          C_background: float = 0.0) -> float:
    Qe = Q / K_mixing
    C_ss = C_background + G_eff / Qe
    ratio = (C_t - C_ss) / (C0 - C_ss)
    if ratio <= 0 or ratio > 1:
        return float("inf")
    return -volume / Qe * math.log(ratio)


def airflow_thermal(q_sensible_W: float, t_in_c: float, t_out_c: float, air_in: AirState) -> AirflowResult:
    """Caudal para evacuar una carga térmica sensible (balance de energía en aire seco)."""
    tr = Trace()
    dT = t_out_c - t_in_c
    if dT <= 0:
        raise AirflowError("La temperatura de salida debe ser mayor que la de entrada para evacuar calor")
    if q_sensible_W <= 0:
        raise AirflowError("La carga térmica debe ser positiva")
    cp = air_in.cp_da * 1000.0  # J/(kg a.s.·K)
    m_da = q_sensible_W / (cp * dT)
    tr.add(MODULE, "Flujo másico de aire seco", "ṁ = q/(cp·Δt)",
           [("q", q_sensible_W, "W", "Carga sensible"), ("cp", cp, "J/(kg a.s.·K)", "1.006 + 1.86·W"),
            ("Δt", dT, "K", "t_salida − t_entrada")],
           f"ṁ = {n(q_sensible_W)}/({n(cp)}·{n(dT)})", m_da, "kg a.s./s", "Balance de energía sensible; ASHRAE cap. 1")
    Q_in = m_da * air_in.v_m3_kg
    tr.add(MODULE, "Caudal a condiciones de entrada", "Q = ṁ·v_entrada",
           [("ṁ", m_da, "kg/s", ""), ("v", air_in.v_m3_kg, "m³/kg a.s.", "Volumen específico a la entrada")],
           f"Q = {n(m_da)}·{n(air_in.v_m3_kg)}", Q_in, "m³/s", "Definición")
    out = air_state_from_W(t_out_c, air_in.W, air_in.p_pa)
    Q_out = m_da * out.v_m3_kg
    tr.add(MODULE, "Caudal a condiciones de salida", "Q = ṁ·v_salida",
           [("ṁ", m_da, "kg/s", ""), ("v", out.v_m3_kg, "m³/kg a.s.", "")], f"Q = {n(m_da)}·{n(out.v_m3_kg)}",
           Q_out, "m³/s", "Definición")
    Q_simple = q_sensible_W / (air_in.rho * air_in.cp_mix * 1000.0 * dT)
    tr.add(MODULE, "Forma simplificada (comparación)", "Q = q/(ρ·cp·Δt)",
           [("ρ", air_in.rho, "kg/m³", ""), ("cp", air_in.cp_mix * 1000, "J/(kg·K)", ""), ("Δt", dT, "K", "")],
           f"Q = {n(q_sensible_W)}/({n(air_in.rho)}·{n(air_in.cp_mix * 1000)}·{n(dT)})", Q_simple, "m³/s",
           "Balance sensible simplificado")
    res = AirflowResult("Térmico", Q_in, {"m_da": m_da, "Q_in": Q_in, "Q_out": Q_out, "Q_simple": Q_simple,
                                         "dT": dT, "q": q_sensible_W}, tr)
    res.notes.append("Balance sensible: no incluye carga latente, estratificación ni radiación directa sobre los "
                     "ocupantes. La temperatura de salida supone mezcla completa del recinto.")
    return res


def airflow_occupancy(Rp_Ls_person: float, Pz: float, Ra_Ls_m2: float, Az_m2: float, Ez: float = 1.0) -> AirflowResult:
    """Caudal de aire exterior por ocupación (ASHRAE 62.1, VRP). Valores Rp, Ra y Ez: dato del usuario."""
    tr = Trace()
    if Ez <= 0 or Ez > 1.5:
        raise AirflowError("La eficacia de distribución Ez debe ser positiva (valores típicos de la tabla de 62.1)")
    Vbz = (Rp_Ls_person * Pz + Ra_Ls_m2 * Az_m2) / 1000.0
    tr.add(MODULE, "Aire exterior en la zona de respiración", "Vbz = Rp·Pz + Ra·Az",
           [("Rp", Rp_Ls_person, "L/(s·persona)", "Tasa por persona (tabla de ASHRAE 62.1)"),
            ("Pz", Pz, "personas", ""), ("Ra", Ra_Ls_m2, "L/(s·m²)", "Tasa por área (tabla de ASHRAE 62.1)"),
            ("Az", Az_m2, "m²", "")],
           f"Vbz = ({n(Rp_Ls_person)}·{n(Pz)} + {n(Ra_Ls_m2)}·{n(Az_m2)})/1000", Vbz, "m³/s", SRC_ASHRAE_621,
           kind=KIND_EXTERNAL, notes="Rp y Ra son datos tabulados en ASHRAE 62.1; verifique la edición vigente.")
    Voz = Vbz / Ez
    tr.add(MODULE, "Aire exterior de la zona", "Voz = Vbz/Ez", [("Ez", Ez, "-", "Eficacia de distribución")],
           f"Voz = {n(Vbz)}/{n(Ez)}", Voz, "m³/s", SRC_ASHRAE_621)
    res = AirflowResult("Ocupación (ASHRAE 62.1)", Voz, {"Vbz": Vbz, "Voz": Voz, "Pz": Pz, "Az": Az_m2}, tr)
    res.notes.append("ASHRAE 62.1 aplica a calidad de aire interior por ocupación; no sustituye el control de "
                     "contaminantes de proceso industrial.")
    return res
