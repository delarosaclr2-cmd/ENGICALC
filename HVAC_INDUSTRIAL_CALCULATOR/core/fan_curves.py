"""Curvas de ventiladores: importación, interpolación, corrección y punto de operación.

* Interpolación monótona por tramos PCHIP (Fritsch-Carlson): no genera
  oscilaciones espurias entre puntos del catálogo.
* Corrección por velocidad, diámetro y densidad mediante leyes de semejanza.
  Las curvas de catálogo se publican a una densidad de referencia (normalmente
  1.2 kg/m³); a la altitud/temperatura reales la presión y la potencia se
  reducen en proporción ρ/ρ_ref, el caudal volumétrico no cambia.
* Si el catálogo está en presión ESTÁTICA, la presión total se obtiene con
  FTP = FSP + VP_salida, con VP_salida = ρ·(Q/A_salida)²/2 (se requiere el área
  de descarga del ventilador).
* Fuera del dominio de la curva NO se interpola: se extrapola linealmente solo
  para permitir el cálculo y se marca el resultado como extrapolado.
"""
from __future__ import annotations

import csv
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import brentq

MODULE = "Selección de ventiladores"


class FanCurveError(ValueError):
    pass


@dataclass
class FanCurve:
    id: str = "FAN-1"
    manufacturer: str = ""
    model: str = ""
    fan_type: str = "Centrífugo"          # 'Centrífugo' | 'Axial' | otro
    rpm: float = 1750.0
    rho_ref: float = 1.2                  # kg/m³ densidad de la curva publicada
    diameter_m: float | None = None
    outlet_area_m2: float | None = None
    pressure_basis: str = "total"         # 'total' | 'static'
    points: list[dict] = field(default_factory=list)  # {"Q": m³/s, "P": Pa, "eta": fracción?, "W": W?}
    max_rpm: float | None = None
    q_min_rec: float | None = None        # rango recomendado por el fabricante (a rpm y ρ de catálogo)
    q_max_rec: float | None = None
    certified: bool = False               # curva certificada (p. ej. sello AMCA)
    source: str = ""
    notes: str = ""

    def to_dict(self) -> dict:
        return dict(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "FanCurve":
        fc = cls()
        for k, v in d.items():
            if hasattr(fc, k):
                setattr(fc, k, v)
        return fc

    def total_pressure_at_point(self, pt: dict) -> float:
        """Presión total del punto de catálogo (a ρ_ref): FTP = FSP + VP_salida si la base es estática."""
        P = float(pt["P"])
        if self.pressure_basis == "static" and self.outlet_area_m2:
            P += 0.5 * self.rho_ref * (float(pt["Q"]) / self.outlet_area_m2) ** 2
        return P

    def validate(self) -> list[str]:
        """Errores que impiden usar la curva (datos incompletos o físicamente imposibles).

        Coherencia caudal–presión–potencia: en cada punto con potencia absorbida W debe
        cumplirse η_t = Q·FTP/W < 1 (conservación de la energía: el ventilador no puede
        entregar al aire más potencia que la que absorbe en el eje). Las leyes de
        semejanza conservan η, de modo que basta verificarlo a las condiciones del
        catálogo. Las eficiencias declaradas deben estar en [0, 1) (η = 0 solo es
        posible a caudal nulo).
        """
        errs = []
        if len(self.points) < 3:
            errs.append("La curva requiere al menos 3 puntos (Q, P).")
        qs = [p["Q"] for p in self.points]
        if any(q < 0 for q in qs):
            errs.append("Caudales negativos en la curva.")
        if any(q2 <= q1 for q1, q2 in zip(qs, qs[1:])):
            errs.append("Los caudales de la curva deben ser estrictamente crecientes.")
        if any(p["P"] < 0 for p in self.points):
            errs.append("Presiones negativas en la curva.")
        if self.rpm <= 0 or self.rho_ref <= 0:
            errs.append("RPM y densidad de referencia deben ser positivas.")
        if self.pressure_basis == "static" and not self.outlet_area_m2:
            errs.append("Curva en presión estática: indique el área de descarga del ventilador para obtener la presión total.")
        bad: list[tuple[float, float, float, float]] = []   # (Q, W, Q·FTP, η_t) con η_t ≥ 1
        for pt in self.points:
            Q = float(pt["Q"])
            eta = pt.get("eta")
            if eta is not None and eta != "":
                eta = float(eta)
                if not (0.0 <= eta < 1.0) or (eta == 0.0 and Q > 0):
                    errs.append(f"Eficiencia físicamente imposible en Q = {Q:.4g} m³/s: η = {eta * 100:.1f} % "
                                "(debe estar entre 0 y 100 %, y ser mayor que 0 si hay caudal).")
            W = pt.get("W")
            if W is not None and W != "" and float(W) != 0.0:
                W = float(W)
                if W < 0:
                    errs.append(f"Potencia absorbida negativa en Q = {Q:.4g} m³/s.")
                    continue
                P_air = Q * self.total_pressure_at_point(pt)
                eta_t = P_air / W
                if eta_t >= 1.0:
                    bad.append((Q, W, P_air, eta_t))
        if bad:
            worst = max(bad, key=lambda b: b[3])
            pts = "; ".join(f"Q = {q:.4g} m³/s → η_t = {e * 100:.1f} %" for q, _, _, e in bad[:4])
            more = f"; … ({len(bad) - 4} más)" if len(bad) > 4 else ""
            errs.append(f"Incoherencia caudal–presión–potencia en {len(bad)} punto(s) de la curva: la potencia "
                        f"absorbida no supera la potencia transmitida al aire (η_t = Q·FTP/W ≥ 100 %). Peor caso: "
                        f"Q = {worst[0]:.4g} m³/s, W = {worst[1]:.4g} W < Q·FTP = {worst[2]:.4g} W "
                        f"(η_t = {worst[3] * 100:.1f} %). Puntos: {pts}{more}. Revise las unidades de potencia "
                        "(W, kW, hp), de presión y de caudal, y la base de presión (total/estática) de la curva.")
        return errs

    def coherence_warnings(self, rel_tol: float = 0.05) -> list[str]:
        """Diferencias entre la eficiencia declarada y la que resulta de Q·P/W (misma base de presión).

        La potencia de la curva tiene prioridad en el cálculo; una diferencia mayor que
        ``rel_tol`` indica datos transcritos de forma inconsistente.
        """
        out = []
        for pt in self.points:
            eta, W, Q = pt.get("eta"), pt.get("W"), float(pt["Q"])
            if not eta or not W or Q <= 0:
                continue
            eta_w = Q * float(pt["P"]) / float(W)
            if abs(eta_w - float(eta)) / float(eta) > rel_tol:
                out.append(f"Q = {Q:.4g} m³/s: η declarada {float(eta) * 100:.1f} % frente a Q·P/W = "
                           f"{eta_w * 100:.1f} %")
        return out


def load_curve_csv(path: str, q_unit: str = "m³/s", p_unit: str = "Pa", w_unit: str = "W") -> list[dict]:
    """Lee puntos (Q, P[, eta][, W]) de un CSV con encabezados Q,P,eta,W (eta en fracción o %)."""
    from .units import to_si
    pts = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        rd = csv.DictReader(fh)
        for row in rd:
            row = {k.strip().lower(): v for k, v in row.items() if k}
            if not row.get("q") or not row.get("p"):
                continue
            p = {"Q": to_si(float(row["q"]), "flow", q_unit), "P": to_si(float(row["p"]), "pressure", p_unit)}
            if row.get("eta"):
                e = float(row["eta"])
                p["eta"] = e / 100.0 if e > 1.0 else e
            if row.get("w"):
                p["W"] = to_si(float(row["w"]), "power", w_unit)
            pts.append(p)
    return sorted(pts, key=lambda x: x["Q"])


def load_curve_excel(path: str, q_unit: str = "m³/s", p_unit: str = "Pa", w_unit: str = "W") -> list[dict]:
    """Lee la primera hoja de un Excel con encabezados Q, P[, eta][, W]."""
    import openpyxl
    from .units import to_si
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h).strip().lower() if h is not None else "" for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    pts = []
    for r in rows[1:]:
        if r[idx["q"]] is None or r[idx["p"]] is None:
            continue
        p = {"Q": to_si(float(r[idx["q"]]), "flow", q_unit), "P": to_si(float(r[idx["p"]]), "pressure", p_unit)}
        if "eta" in idx and r[idx["eta"]] is not None:
            e = float(r[idx["eta"]])
            p["eta"] = e / 100.0 if e > 1.0 else e
        if "w" in idx and r[idx["w"]] is not None:
            p["W"] = to_si(float(r[idx["w"]]), "power", w_unit)
        pts.append(p)
    return sorted(pts, key=lambda x: x["Q"])


class AdjustedFan:
    """Curva del ventilador ajustada a velocidad, diámetro y densidad de operación."""

    def __init__(self, curve: FanCurve, rpm: float | None = None, rho: float | None = None,
                 diameter_m: float | None = None):
        errs = curve.validate()
        if errs:
            more = f" (y {len(errs) - 3} error(es) más)" if len(errs) > 3 else ""
            raise FanCurveError("; ".join(errs[:3]) + more)
        self.curve = curve
        self.rpm = rpm or curve.rpm
        self.rho = rho or curve.rho_ref
        self.rn = self.rpm / curve.rpm
        self.rd = (diameter_m / curve.diameter_m) if (diameter_m and curve.diameter_m) else 1.0
        self.rr = self.rho / curve.rho_ref
        pts = sorted(curve.points, key=lambda p: p["Q"])
        self._q = np.array([p["Q"] for p in pts])
        self._p = np.array([p["P"] for p in pts])
        self._p_int = PchipInterpolator(self._q, self._p)
        self._has_w = all("W" in p and p["W"] for p in pts)
        self._has_eta = all("eta" in p and p["eta"] for p in pts)
        self._w_int = PchipInterpolator(self._q, np.array([p["W"] for p in pts])) if self._has_w else None
        self._eta_int = PchipInterpolator(self._q, np.array([p["eta"] for p in pts])) if self._has_eta else None
        self.outlet_area = (curve.outlet_area_m2 * self.rd ** 2) if curve.outlet_area_m2 else None

    # --- dominio ---
    @property
    def q_min(self) -> float:
        return float(self._q[0]) * self.rn * self.rd ** 3

    @property
    def q_max(self) -> float:
        return float(self._q[-1]) * self.rn * self.rd ** 3

    def in_domain(self, Q: float) -> bool:
        return self.q_min - 1e-12 <= Q <= self.q_max + 1e-12

    def _qcat(self, Q: float) -> float:
        return Q / (self.rn * self.rd ** 3)

    def _interp(self, f, xs, ys, x):
        if xs[0] <= x <= xs[-1]:
            return float(f(x))
        # extrapolación lineal desde el extremo (solo para continuidad numérica)
        if x < xs[0]:
            s = (ys[1] - ys[0]) / (xs[1] - xs[0])
            return float(ys[0] + s * (x - xs[0]))
        s = (ys[-1] - ys[-2]) / (xs[-1] - xs[-2])
        return float(ys[-1] + s * (x - xs[-1]))

    # --- presiones ---
    def p_catalog_basis(self, Q: float, rho: float | None = None) -> float:
        """Presión en la base del catálogo (total o estática) a las condiciones de operación."""
        rr = (rho / self.curve.rho_ref) if rho else self.rr
        pc = self._interp(self._p_int, self._q, self._p, self._qcat(Q))
        return pc * self.rn ** 2 * self.rd ** 2 * rr

    def vp_outlet(self, Q: float, rho: float | None = None) -> float | None:
        if not self.outlet_area:
            return None
        r = rho or self.rho
        return 0.5 * r * (Q / self.outlet_area) ** 2

    def ftp(self, Q: float, rho: float | None = None) -> float:
        p = self.p_catalog_basis(Q, rho)
        if self.curve.pressure_basis == "static":
            return p + (self.vp_outlet(Q, rho) or 0.0)
        return p

    def fsp(self, Q: float, rho: float | None = None, vp_out_fallback: float | None = None) -> float:
        p = self.p_catalog_basis(Q, rho)
        if self.curve.pressure_basis == "static":
            return p
        vp = self.vp_outlet(Q, rho)
        if vp is None:
            vp = vp_out_fallback or 0.0
        return p - vp

    def shaft_power(self, Q: float, rho: float | None = None) -> float | None:
        rr = (rho / self.curve.rho_ref) if rho else self.rr
        qc = self._qcat(Q)
        if self._w_int is not None:
            wc = self._interp(self._w_int, self._q, np.array([p["W"] for p in sorted(self.curve.points, key=lambda p: p["Q"])]), qc)
            return wc * self.rn ** 3 * self.rd ** 5 * rr
        if self._eta_int is not None:
            eta = self._interp(self._eta_int, self._q, np.array([p["eta"] for p in sorted(self.curve.points, key=lambda p: p["Q"])]), qc)
            if eta <= 0:
                return None
            p_basis = self.p_catalog_basis(Q, rho)
            return Q * p_basis / eta
        return None

    def eta_total(self, Q: float, rho: float | None = None) -> float | None:
        W = self.shaft_power(Q, rho)
        if not W or W <= 0:
            return None
        return Q * self.ftp(Q, rho) / W

    def eta_static(self, Q: float, rho: float | None = None, vp_out_fallback: float | None = None) -> float | None:
        W = self.shaft_power(Q, rho)
        if not W or W <= 0:
            return None
        return Q * self.fsp(Q, rho, vp_out_fallback) / W

    # --- puntos característicos ---
    def peak_pressure_q(self) -> float:
        qs = np.linspace(self.q_min, self.q_max, 400)
        ps = [self.ftp(q) for q in qs]
        return float(qs[int(np.argmax(ps))])

    def bep(self) -> tuple[float, float] | None:
        """(Q_BEP, η_total máx) si la curva tiene datos de potencia o eficiencia."""
        if self._w_int is None and self._eta_int is None:
            return None
        qs = np.linspace(self.q_min, self.q_max, 600)
        etas = [self.eta_total(q) or 0.0 for q in qs]
        i = int(np.argmax(etas))
        return float(qs[i]), float(etas[i])

    def positive_slope(self, Q: float) -> bool:
        h = (self.q_max - self.q_min) * 1e-3
        return self.ftp(min(Q + h, self.q_max)) - self.ftp(max(Q - h, self.q_min)) > 0

    def sample(self, n_pts: int = 120) -> dict:
        qs = np.linspace(self.q_min, self.q_max, n_pts)
        return {"Q": qs, "FTP": np.array([self.ftp(q) for q in qs]),
                "W": np.array([self.shaft_power(q) or np.nan for q in qs]),
                "eta": np.array([self.eta_total(q) or np.nan for q in qs])}


def speed_for_design_point(fan: AdjustedFan, Q_d: float, P_d: float) -> float | None:
    """RPM necesarias para que la curva pase por (Q_d, P_d) (parábola de semejanza P = P_d·(Q/Q_d)²)."""
    def h(Q):
        return fan.ftp(Q) - P_d * (Q / Q_d) ** 2
    qs = np.linspace(fan.q_min, fan.q_max, 300)
    vals = [h(q) for q in qs]
    for i in range(len(qs) - 1):
        if vals[i] == 0:
            Q1 = qs[i]
            break
        if vals[i] * vals[i + 1] < 0:
            Q1 = brentq(h, qs[i], qs[i + 1])
            break
    else:
        return None
    return fan.rpm * Q_d / Q1


@dataclass
class OperatingPoint:
    Q: float
    FTP: float
    FSP: float | None
    W_shaft: float | None
    eta_total: float | None
    eta_static: float | None
    in_domain: bool
    intersections: list[float]
    q_bep: float | None
    eta_max: float | None
    q_peak: float
    on_positive_slope: bool
    q_ratio_bep: float | None
    eta_ratio: float | None
    in_manufacturer_range: bool | None
    warnings: list[str] = field(default_factory=list)


def find_intersections(fan: AdjustedFan, sys_q: list[float], sys_p: list[float], rho: float | None = None) -> list[float]:
    """Intersecciones entre la curva del ventilador y la curva del sistema muestreada."""
    sq = np.array(sys_q)
    sp = np.array(sys_p)
    order = np.argsort(sq)
    sq, sp = sq[order], sp[order]
    sys_int = PchipInterpolator(sq, sp)
    lo = max(fan.q_min, sq[0])
    hi = min(fan.q_max, sq[-1])
    if hi <= lo:
        return []

    def g(Q):
        return fan.ftp(Q, rho) - float(sys_int(Q))

    qs = np.linspace(lo, hi, 500)
    vals = [g(q) for q in qs]
    roots = []
    for i in range(len(qs) - 1):
        if vals[i] == 0:
            roots.append(float(qs[i]))
        elif vals[i] * vals[i + 1] < 0:
            roots.append(float(brentq(g, qs[i], qs[i + 1], xtol=1e-10)))
    return roots


def analyze_operating_point(fan: AdjustedFan, Q: float, intersections: list[float], rho: float | None = None,
                            vp_out_fallback: float | None = None, stall_margin: float = 0.10,
                            eta_ratio_min: float = 0.90) -> OperatingPoint:
    warns: list[str] = []
    ftp = fan.ftp(Q, rho)
    fsp = fan.fsp(Q, rho, vp_out_fallback)
    W = fan.shaft_power(Q, rho)
    et = fan.eta_total(Q, rho)
    es = fan.eta_static(Q, rho, vp_out_fallback)
    dom = fan.in_domain(Q)
    if not dom:
        warns.append("Punto de operación fuera del dominio de la curva del fabricante (extrapolado).")
    b = fan.bep()
    q_bep, eta_max = (b if b else (None, None))
    qpk = fan.peak_pressure_q()
    pos = fan.positive_slope(Q)
    q_ratio = Q / q_bep if q_bep else None
    eta_ratio = (et / eta_max) if (et and eta_max) else None
    rng = None
    if fan.curve.q_min_rec is not None and fan.curve.q_max_rec is not None:
        f = fan.rn * fan.rd ** 3
        rng = fan.curve.q_min_rec * f <= Q <= fan.curve.q_max_rec * f
    return OperatingPoint(Q, ftp, fsp, W, et, es, dom, intersections, q_bep, eta_max, qpk, pos, q_ratio, eta_ratio,
                          rng, warns)
