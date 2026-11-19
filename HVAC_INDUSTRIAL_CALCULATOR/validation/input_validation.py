"""Validación de entradas antes del cálculo (datos imposibles o incompletos)."""
from __future__ import annotations

from .alerts import Alert, BASIS_PHYSICS, BASIS_DATA


def validate_project_inputs(project) -> list[Alert]:
    out: list[Alert] = []
    a = project.air

    def crit(module, param, msg, rec):
        out.append(Alert("CRÍTICO", module, param, msg, recommendation=rec, basis=BASIS_PHYSICS,
                         source="Validación de entradas (dominio físico)"))

    if a.t_c <= -273.15:
        crit("Propiedades del aire", "Temperatura", "Temperatura absoluta no positiva", "Corrija la temperatura.")
    if not (0.0 <= a.rh <= 1.0):
        crit("Propiedades del aire", "Humedad relativa", "Humedad relativa fuera de 0–100 %", "Corrija la humedad relativa.")
    if a.p_pa is not None and a.p_pa <= 0:
        crit("Propiedades del aire", "Presión", "Presión atmosférica no positiva", "Corrija la presión.")
    if a.altitude_m is not None and not (-500 <= a.altitude_m <= 11000):
        out.append(Alert("ALTO", "Propiedades del aire", "Altitud", "Altitud fuera del dominio de la atmósfera estándar "
                         "(−500 a 11 000 m)", a.altitude_m, "length", recommendation="Indique la presión barométrica medida.",
                         basis=BASIS_PHYSICS, source="ASHRAE Fundamentals cap. 1, ec. 3"))
    pw = project.power
    for name, v in (("η transmisión", pw.eta_drive), ("η motor", pw.eta_motor), ("η variador", pw.eta_vfd)):
        if v is not None and not (0 < v <= 1):
            crit("Potencia y motores", name, f"Eficiencia fuera de (0, 1]: {v}", "Las eficiencias deben estar en (0, 1] "
                 "(1.0 = acople directo o sin variador).")
    if pw.eta_fan_user is not None and not (0 < pw.eta_fan_user < 1):
        crit("Potencia y motores", "η ventilador", f"Eficiencia del ventilador físicamente imposible: {pw.eta_fan_user}",
             "La eficiencia del ventilador debe estar en (0, 1): un ventilador no puede transmitir al aire toda la "
             "potencia que absorbe.")
    if pw.margin < 0:
        crit("Potencia y motores", "Margen", "Margen de selección negativo", "Use un margen ≥ 0.")
    for h in project.hoods:
        for k, v in h.params.items():
            if isinstance(v, (int, float)) and v < 0:
                crit("Campanas", f"{h.id}.{k}", f"Valor negativo en {k}", "Corrija la geometría de la campana.")
    for s in project.network.segments:
        if s.shape == "circular" and (not s.D or s.D <= 0):
            crit("Redes ramificadas", f"Tramo {s.id}", "Diámetro no positivo", "Indique el diámetro.")
        if s.shape == "rectangular" and (not s.a or not s.b or s.a <= 0 or s.b <= 0):
            crit("Redes ramificadas", f"Tramo {s.id}", "Dimensiones rectangulares no positivas", "Indique a y b.")
        if s.length < 0:
            crit("Redes ramificadas", f"Tramo {s.id}", "Longitud negativa", "Corrija la longitud.")
        for e in s.equipment:
            if e.model == "filter" and (e.dp_clean <= 0 or e.dp_dirty <= 0):
                out.append(Alert("ALTO", "Pérdidas de presión", f"{e.name} ({s.id})", "Filtro sin pérdidas inicial/final",
                                 recommendation="Ingrese ΔP limpio y ΔP final del fabricante.", basis=BASIS_DATA,
                                 source="Datos del fabricante"))
    if project.network.nodes and not project.fans:
        out.append(Alert("INFO", "Selección de ventiladores", "Curvas", "No hay curvas de ventilador cargadas",
                         recommendation="Cargue la curva del fabricante para verificar el punto de operación.",
                         basis=BASIS_DATA))
    return out
