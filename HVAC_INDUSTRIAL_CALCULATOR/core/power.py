"""Potencia, selección de motor y consumo energético.

Cadena de potencias (cada una se presenta por separado):
1. Potencia aerodinámica (transmitida al aire), base total:  P_aire = Q·FTP
   (base estática: P_aire,s = Q·FSP — solo informativa)
2. Potencia absorbida por el ventilador (= potencia en el eje del ventilador):
       W_vent = Q·FTP/η_total = Q·FSP/η_estática   (la presión y la eficiencia
       deben estar en la MISMA base; mezclarlas produce errores de 10–30 %)
   o directamente de la curva de potencia del fabricante corregida por densidad.
3. Potencia en el eje del motor (salida del motor):  W_motor = W_vent/η_transmisión
4. Potencia eléctrica de entrada:  P_elec = W_motor/(η_motor·η_variador)
5. Potencia nominal del motor: menor potencia normalizada ≥ W_motor·(1 + margen).
   El margen se aplica UNA sola vez. El factor de servicio del motor es una
   capacidad de sobrecarga térmica y NO se usa como margen de selección.

Unidades imperiales: BHP = Q[cfm]·P[in.wg]/(6356·η); el programa calcula en SI
y convierte (1 hp = 745.7 W; 1 in.wg (60 °F) = 248.84 Pa → la constante
equivalente es 6349.6; diferencia 0.1 % con 6356, que corresponde a agua a 68 °F).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .trace import Trace, n, KIND_HYPOTHESIS

MODULE = "Potencia y motores"
SRC_POWER = "ASHRAE Handbook—HVAC Systems and Equipment (cap. Fans); AMCA 203 (aplicación en campo)"


class PowerError(ValueError):
    pass


@dataclass
class PowerResult:
    Q: float
    FTP: float
    FSP: float | None
    P_air_total: float
    P_air_static: float | None
    W_fan: float
    W_fan_method: str
    eta_total: float | None
    eta_static: float | None
    eta_drive: float
    eta_motor: float
    eta_vfd: float
    W_motor_out: float
    P_elec: float
    margin: float
    W_motor_required: float
    motor_nominal: float | None
    motor_standard: str
    motor_selected: float | None
    motor_load_fraction: float | None
    service_factor: float
    hours: float
    tariff: float
    energy_kwh: float
    cost: float
    trace: Trace = field(default_factory=Trace)
    warnings: list[str] = field(default_factory=list)


def next_standard_rating(W_required: float, ratings_kw: list[float]) -> float | None:
    for r in sorted(ratings_kw):
        if r * 1000.0 >= W_required - 1e-9:
            return r * 1000.0
    return None


def power_chain(Q: float, FTP: float, FSP: float | None = None, W_fan_curve: float | None = None,
                eta_fan: float | None = None, eta_basis: str = "total", eta_drive: float = 1.0,
                eta_motor: float = 0.92, eta_vfd: float = 1.0, margin: float = 0.10, service_factor: float = 1.0,
                ratings_kw: list[float] | None = None, motor_standard: str = "IEC", motor_selected_W: float | None = None,
                hours: float = 0.0, tariff: float = 0.0) -> PowerResult:
    tr = Trace()
    warns: list[str] = []
    for name, val in (("η_transmisión", eta_drive), ("η_motor", eta_motor), ("η_variador", eta_vfd)):
        if not (0 < val <= 1):
            raise PowerError(f"{name} debe estar en (0, 1]")
    if Q <= 0 or FTP <= 0:
        raise PowerError("Caudal y presión total deben ser positivos")
    P_air = Q * FTP
    tr.add(MODULE, "Potencia aerodinámica (base total)", "P_aire = Q·FTP", [("Q", Q, "m³/s", ""), ("FTP", FTP, "Pa", "")],
           f"P_aire = {n(Q)}·{n(FTP)}", P_air, "W", SRC_POWER)
    P_air_s = Q * FSP if FSP is not None else None
    if P_air_s is not None:
        tr.add(MODULE, "Potencia aerodinámica (base estática, informativa)", "P_aire,s = Q·FSP",
               [("Q", Q, "m³/s", ""), ("FSP", FSP, "Pa", "")], f"P_aire,s = {n(Q)}·{n(FSP)}", P_air_s, "W", SRC_POWER)
    eta_t = eta_s = None
    if W_fan_curve is not None and W_fan_curve > 0:
        W_fan = W_fan_curve
        method = "Curva de potencia del fabricante (corregida por densidad y velocidad)"
        eta_t = P_air / W_fan
        eta_s = P_air_s / W_fan if P_air_s is not None else None
        tr.add(MODULE, "Potencia absorbida por el ventilador", "W_vent = W_curva(Q)·(N/N₀)³·(ρ/ρ₀)",
               [("Q", Q, "m³/s", "")], "lectura de la curva corregida", W_fan, "W", "Curva del fabricante")
        tr.add(MODULE, "Eficiencia total resultante", "η_t = Q·FTP/W_vent", [("P_aire", P_air, "W", ""), ("W_vent", W_fan, "W", "")],
               f"η_t = {n(P_air)}/{n(W_fan)}", eta_t, "-", "Definición (AMCA 210)")
        if eta_fan:
            ref = eta_t if eta_basis == "total" else eta_s
            if ref and abs(ref - eta_fan) / eta_fan > 0.05:
                warns.append(f"La eficiencia indicada ({eta_fan:.3f}, base {eta_basis}) difiere más de 5 % de la que "
                             f"resulta de la curva ({ref:.3f}). Se usa la curva.")
    else:
        if not eta_fan or not (0 < eta_fan <= 1):
            raise PowerError("Sin curva de potencia: indique la eficiencia del ventilador en (0, 1]")
        if eta_basis == "static":
            if FSP is None:
                raise PowerError("Eficiencia estática requiere la presión estática del ventilador")
            W_fan = Q * FSP / eta_fan
            eta_s = eta_fan
            eta_t = P_air / W_fan
            tr.add(MODULE, "Potencia absorbida por el ventilador (base estática)", "W_vent = Q·FSP/η_s",
                   [("Q", Q, "m³/s", ""), ("FSP", FSP, "Pa", ""), ("η_s", eta_fan, "-", "Eficiencia estática")],
                   f"W_vent = {n(Q)}·{n(FSP)}/{n(eta_fan)}", W_fan, "W", SRC_POWER)
        else:
            W_fan = P_air / eta_fan
            eta_t = eta_fan
            eta_s = P_air_s / W_fan if P_air_s is not None else None
            tr.add(MODULE, "Potencia absorbida por el ventilador (base total)", "W_vent = Q·FTP/η_t",
                   [("Q", Q, "m³/s", ""), ("FTP", FTP, "Pa", ""), ("η_t", eta_fan, "-", "Eficiencia total")],
                   f"W_vent = {n(Q)}·{n(FTP)}/{n(eta_fan)}", W_fan, "W", SRC_POWER)
        method = f"Eficiencia {eta_basis} indicada por el usuario"
        warns.append("Potencia calculada con una eficiencia supuesta: verifique con la curva certificada del fabricante.")
    W_motor = W_fan / eta_drive
    tr.add(MODULE, "Potencia en el eje del motor", "W_motor = W_vent/η_transmisión",
           [("W_vent", W_fan, "W", ""), ("η_tr", eta_drive, "-", "Transmisión (1.0 acople directo)")],
           f"W_motor = {n(W_fan)}/{n(eta_drive)}", W_motor, "W", "AMCA 203 (pérdidas de transmisión) — dato del usuario")
    P_elec = W_motor / (eta_motor * eta_vfd)
    tr.add(MODULE, "Potencia eléctrica de entrada", "P_elec = W_motor/(η_motor·η_variador)",
           [("W_motor", W_motor, "W", ""), ("η_m", eta_motor, "-", "Placa del motor / IEC 60034-30-1"),
            ("η_vfd", eta_vfd, "-", "Variador (1.0 si no hay)")],
           f"P_elec = {n(W_motor)}/({n(eta_motor)}·{n(eta_vfd)})", P_elec, "W", "Balance de potencias")
    W_req = W_motor * (1.0 + margin)
    tr.add(MODULE, "Potencia mínima del motor con margen", "W_req = W_motor·(1 + margen)",
           [("W_motor", W_motor, "W", ""), ("margen", margin, "-", "Margen de diseño (una sola vez)")],
           f"W_req = {n(W_motor)}·(1 + {n(margin)})", W_req, "W", "Criterio del proyecto", kind=KIND_HYPOTHESIS)
    nominal = next_standard_rating(W_req, ratings_kw or [])
    if nominal is None:
        warns.append("La potencia requerida supera la mayor potencia de la serie de motores configurada.")
    else:
        tr.add(MODULE, f"Motor normalizado ({motor_standard})", "P_nom = mín{P_serie ≥ W_req}", [("W_req", W_req, "W", "")],
               "selección en la serie normalizada", nominal, "W", "Serie de potencias normalizadas (base de datos)")
    load = None
    ref_motor = motor_selected_W or nominal
    if ref_motor:
        load = W_motor / ref_motor
    E = P_elec / 1000.0 * hours
    cost = E * tariff
    if hours > 0:
        tr.add(MODULE, "Consumo energético anual", "E = P_elec·t", [("P_elec", P_elec / 1000, "kW", ""), ("t", hours, "h/año", "")],
               f"E = {n(P_elec / 1000)}·{n(hours)}", E, "kWh/año", "Definición")
        tr.add(MODULE, "Costo energético anual", "C = E·tarifa", [("E", E, "kWh", ""), ("tarifa", tariff, "$/kWh", "")],
               f"C = {n(E)}·{n(tariff)}", cost, "$/año", "Definición (sin cargos por demanda)")
    return PowerResult(Q, FTP, FSP, P_air, P_air_s, W_fan, method, eta_t, eta_s, eta_drive, eta_motor, eta_vfd, W_motor,
                       P_elec, margin, W_req, nominal, motor_standard, motor_selected_W, load, service_factor, hours,
                       tariff, E, cost, tr, warns)


@dataclass
class PartLoadRow:
    fraction: float
    hours: float
    Q: float
    P_elec_damper: float | None
    P_elec_vfd: float | None
    speed_ratio: float | None


def part_load_comparison(fan, sys_ftp, Q_op: float, profile: list[tuple[float, float]], eta_drive: float,
                         eta_motor: float, eta_vfd: float, rho: float | None = None) -> tuple[list[PartLoadRow], dict]:
    """Compara regulación por compuerta (velocidad fija) frente a variador de frecuencia.

    ``fan``: AdjustedFan a velocidad nominal; ``sys_ftp(Q)``: FTP requerido por el sistema;
    ``profile``: [(fracción de caudal, horas/año)]. Hipótesis: eficiencias de motor y
    variador constantes (en la práctica disminuyen a carga parcial).
    """
    from .fan_curves import speed_for_design_point
    rows: list[PartLoadRow] = []
    e_d = e_v = 0.0
    for frac, hrs in profile:
        Q = Q_op * frac
        Pd = Pv = k = None
        if fan.in_domain(Q):
            W = fan.shaft_power(Q, rho)
            if W:
                Pd = W / (eta_drive * eta_motor)
        P_sys = sys_ftp(Q)
        rpm2 = speed_for_design_point(fan, Q, P_sys)
        if rpm2:
            k = rpm2 / fan.rpm
            Qc = Q / k
            Wc = fan.shaft_power(Qc, rho)
            if Wc:
                Pv = Wc * k ** 3 / (eta_drive * eta_motor * eta_vfd)
        rows.append(PartLoadRow(frac, hrs, Q, Pd, Pv, k))
        if Pd:
            e_d += Pd / 1000 * hrs
        if Pv:
            e_v += Pv / 1000 * hrs
    return rows, {"E_damper_kwh": e_d, "E_vfd_kwh": e_v, "saving_kwh": e_d - e_v}
