"""Tramo de tubería con líquido incompresible: Darcy-Weisbach (Menon 2005, ecs. 1.23, 1.25, 6.38, 6.49)."""
from __future__ import annotations

from .hidraulica import area, factor_friccion
from .tubos import k_accesorio

G = 9.80665


def tramo(q_m3s, rho, mu, d_m, nps, l_m, eps_m, accesorios, dz_m=0.0):
    """Pérdidas en un tramo. accesorios: lista de dicts {tipo, cantidad, k?}.

    Devuelve un dict con v, Re, f, régimen, detalle de K, alturas (m de líquido) y ΔP (Pa)."""
    if q_m3s <= 0 or d_m <= 0 or rho <= 0 or mu <= 0:
        raise ValueError("Caudal, diámetro, densidad y viscosidad deben ser positivos")
    if l_m < 0:
        raise ValueError("La longitud no puede ser negativa")
    a = area(d_m)
    v = q_m3s / a
    re = rho * v * d_m / mu
    f, regimen = factor_friccion(re, eps_m, d_m)
    laminar = regimen == "laminar"
    detalle = []
    for acc in accesorios:
        n = acc.get("cantidad", 1)
        k = k_accesorio(acc["tipo"], nps, n, acc.get("k"), f, laminar)
        detalle.append((acc["tipo"], n, k / n if n else 0.0, k))
    k_tot = sum(d[3] for d in detalle)
    hv = v * v / (2 * G)
    h_tub = f * l_m / d_m * hv
    h_acc = k_tot * hv
    return {"v": v, "re": re, "f": f, "regimen": regimen, "detalle_k": detalle, "k_total": k_tot,
            "h_velocidad": hv, "h_tuberia": h_tub, "h_accesorios": h_acc, "h_friccion": h_tub + h_acc,
            "dp_tuberia": rho * G * h_tub, "dp_accesorios": rho * G * h_acc,
            "dp_friccion": rho * G * (h_tub + h_acc), "dp_estatico": rho * G * dz_m,
            "dp_total": rho * G * (h_tub + h_acc + dz_m), "laminar": laminar}
