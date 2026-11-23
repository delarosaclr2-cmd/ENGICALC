"""Datos de referencia con su fuente. Ningún valor de esta tabla es inventado; verificar contra la
edición vigente de cada fuente antes de emitir.

- Diámetros: ASME B36.10M (OD y espesor, céd. 40 y 80).
- L/D: Menon, Piping Calculations Manual (2005), tabla 5.10.
- K por diámetro nominal: Menon (2005), tabla 5.11 (K = f_T·L/D, flujo turbulento).
- Rugosidad del acero comercial: 0.0018 in (Menon 2005, ej. 5.15).
"""
PULGADA = 0.0254
RUGOSIDAD_ACERO_M = 0.0018 * PULGADA

_TUBO = {  # NPS: (OD in, t céd.40 in, t céd.80 in)
    "1/2": (0.840, 0.109, 0.147), "3/4": (1.050, 0.113, 0.154), "1": (1.315, 0.133, 0.179),
    "1-1/4": (1.660, 0.140, 0.191), "1-1/2": (1.900, 0.145, 0.200), "2": (2.375, 0.154, 0.218),
    "2-1/2": (2.875, 0.203, 0.276), "3": (3.500, 0.216, 0.300), "4": (4.500, 0.237, 0.337),
    "6": (6.625, 0.280, 0.432), "8": (8.625, 0.322, 0.500), "10": (10.750, 0.365, 0.594),
    "12": (12.750, 0.406, 0.688),
}


def d_interior_m(nps: str, cedula: str) -> float:
    if nps not in _TUBO:
        raise KeyError(f"NPS {nps!r} fuera de tabla; capture el diámetro interior")
    od, t40, t80 = _TUBO[nps]
    t = {"40": t40, "80": t80}.get(str(cedula))
    if t is None:
        raise KeyError(f"Cédula {cedula!r} no tabulada; use 40, 80 o capture Di")
    return (od - 2 * t) * PULGADA


# Menon tabla 5.10
L_SOBRE_D = {"compuerta": 8, "globo": 340, "angulo": 55, "bola": 3, "check_columpio": 100,
             "check_columpio_t511": 50, "check_levantamiento": 600, "codo90": 30, "codo45": 16,
             "codo90_radio_largo": 16, "te_paso": 20, "te_rama": 60}

# Menon tabla 5.11: columnas por NPS
_COLS = ["1/2", "3/4", "1", "1-1/4", "1-1/2", "2", "2-1/2", "4", "6", "8", "12", "18"]
_K511 = {
    "compuerta":          [0.22, 0.20, 0.18, 0.18, 0.15, 0.15, 0.14, 0.14, 0.12, 0.11, 0.10, 0.10],
    "globo":              [9.20, 8.50, 7.80, 7.50, 7.10, 6.50, 6.10, 5.80, 5.10, 4.80, 4.40, 4.10],
    "angulo":             [1.48, 1.38, 1.27, 1.21, 1.16, 1.05, 0.99, 0.94, 0.83, 0.77, 0.72, 0.66],
    "bola":               [0.08, 0.08, 0.07, 0.07, 0.06, 0.06, 0.05, 0.05, 0.05, 0.04, 0.04, 0.04],
    "check_columpio_t511": [1.40, 1.30, 1.20, 1.10, 1.10, 1.00, 0.90, 0.90, 0.75, 0.70, 0.65, 0.60],
    "check_levantamiento": [16.2, 15.0, 13.8, 13.2, 12.6, 11.4, 10.8, 10.2, 9.00, 8.40, 7.80, 7.22],
    "codo90":             [0.81, 0.75, 0.69, 0.66, 0.63, 0.57, 0.54, 0.51, 0.45, 0.42, 0.39, 0.36],
    "codo45":             [0.43, 0.40, 0.37, 0.35, 0.34, 0.30, 0.29, 0.27, 0.24, 0.22, 0.21, 0.19],
    "codo90_radio_largo": [0.43, 0.40, 0.37, 0.35, 0.34, 0.30, 0.29, 0.27, 0.24, 0.22, 0.21, 0.19],
    "te_paso":            [0.54, 0.50, 0.46, 0.44, 0.42, 0.38, 0.36, 0.34, 0.30, 0.28, 0.26, 0.24],
    "te_rama":            [1.62, 1.50, 1.38, 1.32, 1.26, 1.14, 1.08, 1.02, 0.90, 0.84, 0.78, 0.72],
}
# NPS de la tabla de tubos -> columna de la tabla 5.11 (la tabla agrupa 2½–3, 8–10, 12–16, 18–24)
_MAPA_COL = {"1/2": "1/2", "3/4": "3/4", "1": "1", "1-1/4": "1-1/4", "1-1/2": "1-1/2", "2": "2",
             "2-1/2": "2-1/2", "3": "2-1/2", "4": "4", "6": "6", "8": "8", "10": "8", "12": "12"}


def k_menon(tipo: str, nps: str) -> float:
    """K de la tabla 5.11 de Menon. El check de columpio con L/D = 100 (tabla 5.10) se obtiene
    como 2× el de la tabla 5.11 (L/D = 50): ambas tablas del manual difieren y se conserva la
    mayor para el tipo 'check_columpio'."""
    if tipo == "check_columpio":
        return 2.0 * k_menon("check_columpio_t511", nps)
    if tipo not in _K511:
        raise KeyError(f"Accesorio {tipo!r} sin K tabulado; capture K directamente")
    col = _MAPA_COL.get(nps)
    if col is None:
        raise KeyError(f"NPS {nps!r} sin columna en la tabla 5.11; capture K directamente")
    return _K511[tipo][_COLS.index(col)]


def tipos_accesorio():
    return sorted(set(_K511) | {"check_columpio"})




def od_in(nps: str) -> float:
    return _TUBO[nps][0]


def espesor_nominal_in(nps: str, cedula: str) -> float:
    od, t40, t80 = _TUBO[nps]
    t = {"40": t40, "80": t80}.get(str(cedula))
    if t is None:
        raise KeyError(f"Cédula {cedula!r} no tabulada; use 40 u 80")
    return t


def nps_lista():
    return list(_TUBO)


def k_accesorio(tipo: str, nps, cantidad: float = 1, k=None, f_flujo=None, laminar=False) -> float:
    """K total de un renglón de accesorios.

    Turbulento: K de la tabla 5.11 de Menon (K = f_T·L/D). Laminar (Re < 2100): K = f·(L/D) con el f
    laminar del flujo (método de longitud equivalente), porque los K de la tabla suponen turbulencia
    completa. Si el usuario captura K, se usa tal cual."""
    if k is not None:
        return k * cantidad
    if laminar:
        ld = L_SOBRE_D.get(tipo if tipo != "check_columpio_t511" else "check_columpio")
        if tipo == "check_columpio_t511":
            ld = 50
        if ld is None:
            raise KeyError(f"Accesorio {tipo!r} sin L/D tabulado; capture K")
        return f_flujo * ld * cantidad
    if nps is None:
        raise KeyError("Para usar los K de Menon se requiere el NPS; capture K del accesorio")
    return k_menon(tipo, nps) * cantidad
