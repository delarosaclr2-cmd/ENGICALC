"""Geometría y dimensionamiento de ductos.

* Área circular A = π·D²/4; rectangular A = a·b.
* Diámetro hidráulico Dh = 4A/Pm  →  circular Dh = D; rectangular Dh = 2ab/(a + b).
  Se usa en Reynolds y en Darcy-Weisbach con la velocidad media real del ducto.
* Diámetro equivalente para igual fricción y caudal (Huebscher, 1948; ASHRAE
  Fundamentals cap. Duct Design):  De = 1.30·(ab)^0.625/(a + b)^0.25.
  NO es igual a Dh: De sirve para seleccionar un ducto rectangular con la misma
  pérdida por fricción que un circular que transporta el mismo caudal.

Métodos de dimensionamiento:
1. Velocidad constante: D = √(4Q/(πV)).
2. Fricción constante: D tal que ΔP/L (Darcy-Weisbach + Colebrook) = valor objetivo.
3. Recuperación estática (sistemas de inyección): V₂ tal que R·(VP₁ − VP₂) = pérdidas del
   tramo siguiente. No aplicable a extracción con transporte de partículas.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from scipy.optimize import brentq

from .friction import reynolds, darcy_factor, darcy_weisbach
from .trace import Trace, n

MODULE = "Diseño de ductos"
SRC_HUEBSCHER = "Huebscher (1948), ASHRAE Fundamentals cap. Duct Design (ec. de diámetro equivalente)"


class DuctError(ValueError):
    pass


def circle_area(D: float) -> float:
    return math.pi * D * D / 4.0


def rect_area(a: float, b: float) -> float:
    return a * b


def rect_perimeter(a: float, b: float) -> float:
    return 2.0 * (a + b)


def hydraulic_diameter(area: float, perimeter: float) -> float:
    """Dh = 4A/Pm."""
    if perimeter <= 0:
        raise DuctError("El perímetro mojado debe ser positivo")
    return 4.0 * area / perimeter


def hydraulic_diameter_rect(a: float, b: float) -> float:
    return hydraulic_diameter(rect_area(a, b), rect_perimeter(a, b))


def equivalent_diameter_rect(a: float, b: float) -> float:
    """Diámetro circular equivalente para igual fricción y caudal (Huebscher)."""
    return 1.30 * (a * b) ** 0.625 / (a + b) ** 0.25


@dataclass
class DuctGeometry:
    shape: str              # 'circular' | 'rectangular'
    D: float | None = None  # m
    a: float | None = None  # m (ancho)
    b: float | None = None  # m (alto)

    @property
    def area(self) -> float:
        if self.shape == "circular":
            return circle_area(self.D)
        return rect_area(self.a, self.b)

    @property
    def perimeter(self) -> float:
        if self.shape == "circular":
            return math.pi * self.D
        return rect_perimeter(self.a, self.b)

    @property
    def Dh(self) -> float:
        if self.shape == "circular":
            return self.D
        return hydraulic_diameter_rect(self.a, self.b)

    @property
    def De(self) -> float:
        if self.shape == "circular":
            return self.D
        return equivalent_diameter_rect(self.a, self.b)

    @property
    def aspect(self) -> float:
        if self.shape == "circular":
            return 1.0
        return max(self.a, self.b) / min(self.a, self.b)

    def validate(self) -> None:
        if self.shape == "circular":
            if not self.D or self.D <= 0:
                raise DuctError("El diámetro debe ser positivo")
        elif self.shape == "rectangular":
            if not self.a or not self.b or self.a <= 0 or self.b <= 0:
                raise DuctError("Las dimensiones del ducto rectangular deben ser positivas")
        else:
            raise DuctError(f"Forma de ducto desconocida: {self.shape}")

    def describe(self) -> str:
        if self.shape == "circular":
            return f"Ø{self.D * 1000:.0f} mm"
        return f"{self.a * 1000:.0f}×{self.b * 1000:.0f} mm"


def round_to_series(value_m: float, series_mm: list[float], rule: str = "nearest") -> float:
    """Redondea un diámetro/dimensión a una serie comercial.

    rule = 'down'  → tamaño inmediato inferior (mayor velocidad; práctica para transporte de partículas)
    rule = 'up'    → tamaño inmediato superior (menor velocidad y pérdida)
    rule = 'nearest' / 'none'
    """
    if rule == "none" or not series_mm:
        return value_m
    s = sorted(series_mm)
    v_mm = value_m * 1000.0
    if rule == "down":
        cands = [x for x in s if x <= v_mm + 1e-9]
        return (cands[-1] if cands else s[0]) / 1000.0
    if rule == "up":
        cands = [x for x in s if x >= v_mm - 1e-9]
        return (cands[0] if cands else s[-1]) / 1000.0
    return min(s, key=lambda x: abs(x - v_mm)) / 1000.0


@dataclass
class DuctSizingResult:
    method: str
    geometry: DuctGeometry
    Q: float
    V: float
    VP: float
    Re: float
    rel_rough: float
    f: float
    regime: str
    dp_per_m: float
    D_theoretical: float | None
    De: float
    Dh: float
    trace: Trace = field(default_factory=Trace)
    warnings: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)


def _evaluate(geom: DuctGeometry, Q: float, rho: float, mu: float, roughness: float, method_f: str = "colebrook"):
    A = geom.area
    V = Q / A
    VP = 0.5 * rho * V * V
    Re = reynolds(rho, V, geom.Dh, mu)
    fr = darcy_factor(Re, roughness / geom.Dh, method_f)
    dpm = darcy_weisbach(fr.f, 1.0, geom.Dh, rho, V)
    return V, VP, Re, fr, dpm


def _finish(method, geom, Q, rho, mu, roughness, D_theo, tr, method_f="colebrook") -> DuctSizingResult:
    V, VP, Re, fr, dpm = _evaluate(geom, Q, rho, mu, roughness, method_f)
    A = geom.area
    if geom.shape == "circular":
        tr.add(MODULE, "Área de la sección", "A = π·D²/4", [("D", geom.D, "m", "Diámetro adoptado")],
               f"A = π·{n(geom.D)}²/4", A, "m²", "Geometría")
    else:
        tr.add(MODULE, "Área de la sección", "A = a·b", [("a", geom.a, "m", ""), ("b", geom.b, "m", "")],
               f"A = {n(geom.a)}·{n(geom.b)}", A, "m²", "Geometría")
        tr.add(MODULE, "Diámetro hidráulico", "Dh = 4A/Pm = 2ab/(a + b)", [("a", geom.a, "m", ""), ("b", geom.b, "m", "")],
               f"Dh = 2·{n(geom.a)}·{n(geom.b)}/({n(geom.a)} + {n(geom.b)})", geom.Dh, "m", "Definición de Dh")
        tr.add(MODULE, "Diámetro equivalente (igual fricción)", "De = 1.30·(ab)^0.625/(a + b)^0.25",
               [("a", geom.a, "m", ""), ("b", geom.b, "m", "")],
               f"De = 1.30·({n(geom.a)}·{n(geom.b)})^0.625/({n(geom.a)} + {n(geom.b)})^0.25", geom.De, "m", SRC_HUEBSCHER)
    tr.add(MODULE, "Velocidad media", "V = Q/A", [("Q", Q, "m³/s", ""), ("A", A, "m²", "")], f"V = {n(Q)}/{n(A)}", V,
           "m/s", "Ecuación de continuidad")
    tr.add(MODULE, "Presión de velocidad", "VP = ρ·V²/2", [("ρ", rho, "kg/m³", ""), ("V", V, "m/s", "")],
           f"VP = {n(rho)}·{n(V)}²/2", VP, "Pa", "Definición (Bernoulli)")
    tr.add(MODULE, "Número de Reynolds", "Re = ρ·V·Dh/μ",
           [("ρ", rho, "kg/m³", ""), ("V", V, "m/s", ""), ("Dh", geom.Dh, "m", ""), ("μ", mu, "Pa·s", "")],
           f"Re = {n(rho)}·{n(V)}·{n(geom.Dh)}/{n(mu)}", Re, "-", "Definición")
    tr.add(MODULE, "Rugosidad relativa", "εr = ε/Dh", [("ε", roughness, "m", ""), ("Dh", geom.Dh, "m", "")],
           f"εr = {n(roughness)}/{n(geom.Dh)}", roughness / geom.Dh, "-", "Definición")
    tr.add(MODULE, f"Factor de fricción de Darcy ({fr.method})", "1/√f = −2·log10(εr/3.7 + 2.51/(Re·√f))"
           if fr.regime == "turbulento" else "f = 64/Re (o conservador en transición)",
           [("Re", Re, "-", ""), ("εr", fr.rel_rough, "-", "")], f"f({n(Re)}, {n(fr.rel_rough)})", fr.f, "-",
           "Colebrook-White / régimen según Re", notes="Factor de Darcy = 4·factor de Fanning.")
    tr.add(MODULE, "Pérdida por fricción unitaria", "ΔP/L = f·(1/Dh)·ρV²/2",
           [("f", fr.f, "-", ""), ("Dh", geom.Dh, "m", ""), ("VP", VP, "Pa", "")],
           f"ΔP/L = {n(fr.f)}·(1/{n(geom.Dh)})·{n(VP)}", dpm, "Pa/m", SRC_DW)
    return DuctSizingResult(method, geom, Q, V, VP, Re, fr.rel_rough, fr.f, fr.regime, dpm, D_theo, geom.De, geom.Dh,
                            tr, list(fr.warnings))


SRC_DW = "Darcy-Weisbach (ASHRAE Fundamentals, cap. Duct Design)"


def size_by_velocity(Q: float, V_target: float, rho: float, mu: float, roughness: float, shape: str = "circular",
                     aspect: float = 2.0, fixed_side: float | None = None, series_mm: list[float] | None = None,
                     rounding: str = "nearest") -> DuctSizingResult:
    """Método de velocidad constante."""
    if Q <= 0 or V_target <= 0:
        raise DuctError("Caudal y velocidad de diseño deben ser positivos")
    tr = Trace()
    A_req = Q / V_target
    tr.add(MODULE, "Área requerida", "A = Q/V", [("Q", Q, "m³/s", ""), ("V", V_target, "m/s", "Velocidad de diseño")],
           f"A = {n(Q)}/{n(V_target)}", A_req, "m²", "Continuidad")
    if shape == "circular":
        D = math.sqrt(4 * A_req / math.pi)
        tr.add(MODULE, "Diámetro teórico", "D = √(4A/π)", [("A", A_req, "m²", "")], f"D = √(4·{n(A_req)}/π)", D, "m",
               "Geometría")
        D_adopt = round_to_series(D, series_mm or [], rounding)
        geom = DuctGeometry("circular", D=D_adopt)
        res = _finish("Velocidad constante", geom, Q, rho, mu, roughness, D, tr)
    else:
        if fixed_side:
            a = fixed_side
            b = A_req / a
        else:
            b = math.sqrt(A_req / aspect)
            a = aspect * b
        a_r = round_to_series(a, series_mm or [], rounding)
        b_r = round_to_series(b, series_mm or [], rounding)
        geom = DuctGeometry("rectangular", a=a_r, b=b_r)
        res = _finish("Velocidad constante", geom, Q, rho, mu, roughness, None, tr)
        if geom.aspect > 4:
            res.warnings.append(f"Relación de aspecto {geom.aspect:.1f} > 4: aumenta la pérdida por fricción y el "
                                "costo de material; considere ducto circular o menor relación de aspecto.")
    if rounding != "none":
        res.warnings.append(f"Dimensión redondeada a la serie comercial (regla: {rounding}). Velocidad real "
                            f"{res.V:.2f} m/s frente a {V_target:.2f} m/s de diseño.")
    return res


def size_by_friction(Q: float, dp_per_m: float, rho: float, mu: float, roughness: float, shape: str = "circular",
                     aspect: float = 2.0, series_mm: list[float] | None = None, rounding: str = "nearest") -> DuctSizingResult:
    """Método de fricción constante: resuelve D tal que la pérdida unitaria iguale el objetivo."""
    if Q <= 0 or dp_per_m <= 0:
        raise DuctError("Caudal y pérdida unitaria objetivo deben ser positivos")
    tr = Trace()

    def resid_circ(D):
        g = DuctGeometry("circular", D=D)
        return _evaluate(g, Q, rho, mu, roughness)[4] - dp_per_m

    D = brentq(resid_circ, 0.005, 20.0, xtol=1e-9)
    tr.add(MODULE, "Diámetro para fricción constante", "f(Re,εr)·(1/D)·ρV²/2 = ΔP/L objetivo  (resuelto numéricamente)",
           [("Q", Q, "m³/s", ""), ("ΔP/L", dp_per_m, "Pa/m", "Pérdida unitaria objetivo")],
           "D por bisección (Brent) sobre Darcy-Weisbach + Colebrook", D, "m", SRC_DW)
    if shape == "circular":
        geom = DuctGeometry("circular", D=round_to_series(D, series_mm or [], rounding))
        res = _finish("Fricción constante", geom, Q, rho, mu, roughness, D, tr)
    else:
        # rectangular con el mismo De que el circular de igual fricción
        def resid_rect(b):
            return equivalent_diameter_rect(aspect * b, b) - D
        b = brentq(resid_rect, 0.001, 20.0, xtol=1e-9)
        a = aspect * b
        tr.add(MODULE, "Dimensiones rectangulares con De igual al circular", "De(a,b) = D, a = r·b",
               [("D", D, "m", ""), ("r", aspect, "-", "Relación de aspecto")], f"a = {n(a)}, b = {n(b)}", b, "m",
               SRC_HUEBSCHER)
        geom = DuctGeometry("rectangular", a=round_to_series(a, series_mm or [], rounding),
                            b=round_to_series(b, series_mm or [], rounding))
        res = _finish("Fricción constante", geom, Q, rho, mu, roughness, D, tr)
    return res


@dataclass
class RegainSection:
    Q: float        # m³/s caudal del tramo
    L: float        # m
    K_sum: float    # suma de K de accesorios del tramo (referidos a su velocidad)


def size_static_regain(V1: float, sections: list[RegainSection], R: float, rho: float, mu: float, roughness: float,
                       series_mm: list[float] | None = None, rounding: str = "none") -> list[DuctSizingResult]:
    """Recuperación estática para un tramo principal de inyección con derivaciones sucesivas.

    Para cada tramo i se busca V_i tal que R·(VP_{i−1} − VP_i) = ΔP_fricción,i + ΣK_i·VP_i
    con el caudal del tramo. R es el coeficiente de recuperación (dato del diseñador).
    """
    if not (0 < R <= 1):
        raise DuctError("El coeficiente de recuperación R debe estar en (0, 1]")
    out: list[DuctSizingResult] = []
    V_prev = V1
    for i, s in enumerate(sections):
        VP_prev = 0.5 * rho * V_prev ** 2

        def resid(V):
            D = math.sqrt(4 * s.Q / (math.pi * V))
            g = DuctGeometry("circular", D=D)
            _, VP, _, fr, dpm = _evaluate(g, s.Q, rho, mu, roughness)
            return R * (VP_prev - VP) - (dpm * s.L + s.K_sum * VP)

        try:
            V = brentq(resid, 0.2, V_prev * 0.99999, xtol=1e-7)
            note = ""
        except ValueError:
            V = V_prev
            note = "No existe velocidad que recupere las pérdidas del tramo; se mantiene la velocidad anterior."
        D = math.sqrt(4 * s.Q / (math.pi * V))
        tr = Trace()
        tr.add(MODULE, f"Recuperación estática — tramo {i + 1}", "R·(VP₁ − VP₂) = f·L/D·VP₂ + ΣK·VP₂",
               [("R", R, "-", "Coeficiente de recuperación"), ("VP₁", VP_prev, "Pa", ""), ("Q", s.Q, "m³/s", ""),
                ("L", s.L, "m", ""), ("ΣK", s.K_sum, "-", "")], "V₂ resuelto numéricamente", V, "m/s",
               "ASHRAE Fundamentals cap. Duct Design (método de recuperación estática)")
        g = DuctGeometry("circular", D=round_to_series(D, series_mm or [], rounding))
        r = _finish("Recuperación estática", g, s.Q, rho, mu, roughness, D, tr)
        if note:
            r.warnings.append(note)
        out.append(r)
        V_prev = r.V
    return out
