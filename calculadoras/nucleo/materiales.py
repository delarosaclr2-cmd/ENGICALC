"""Tabla única de materiales heredada de las versiones originales.

AVISO: ninguno de estos valores tiene fuente documentada en el código original y
los módulos originales usaban valores distintos para el mismo material (por
ejemplo, caolín 400, 480, 600, 2 600 y 2 650 kg/m³). Varios corresponden al orden
de la densidad real de partícula, no a la densidad aparente a granel que se
necesita para dimensionar equipos.

Por eso cada calculadora:
1. pide la densidad aparente como dato (el valor 0 significa «usar la tabla»);
2. si se usa la tabla, toma el valor que tenía SU módulo original (trazabilidad)
   y emite una advertencia con la discrepancia entre módulos.

Valores en kg/m³ y grados. Los del helicoidal estaban en lb/ft³ y se guardan así.
"""
from __future__ import annotations

from .constantes import KGM3_POR_LBPIE3

# Densidades tal como estaban en cada archivo original [kg/m³]
DENSIDADES_ORIGINALES = {
    "elevador": {  # Calculo de Elevador vs3.py
        "Arena": 1600, "Asfalto": 2700, "Carbon": 2269, "Fluorita": 3180, "Cemento": 1440,
        "Caliza": 2750, "Marmol": 2700, "Arcilla": 1089, "Caolin": 400, "Yeso": 970,
    },
    "aerodeslizador": {  # Calculo de Deslizador vs2.py
        "Arena": 1600, "Asfalto": 2900, "Carbon": 2469, "Fluorita": 3380, "Cemento": 1600,
        "Caliza": 2950, "Marmol": 2900, "Arcilla": 1289, "Caolin": 600, "Yeso": 1070,
    },
    "tolva": {  # calculo de tolva de dosificación.py
        "Yeso": 1000, "Fluorita": 3100, "Cemento": 1440, "Cal": 1350, "Carbonato de calcio": 2710,
        "Arcilla": 1600, "Mineral de hierro": 5000, "Caolin": 2600,
    },
    "silo": {  # Calculo de un silo metalico.py
        "Yeso": 850, "Fluorita": 3200, "Cemento": 1500, "Cal": 1050, "Carbonato de calcio": 2710,
        "Arcilla": 1600, "Mineral de hierro": 5100, "Caolin": 2650,
    },
}

# Calculo del transportador helicoidal.py (lb/ft³)
DENSIDADES_HELICOIDAL_LBPIE3 = {
    "Arena": 99.88, "Asfalto": 168.55, "Carbon": 161.64, "Fluorita": 198.52, "Cemento": 89.89,
    "Caliza": 171.67, "Marmol": 168.55, "Arcilla": 67.98, "Caolin": 29.97, "Yeso": 60.55,
}
DENSIDADES_ORIGINALES["helicoidal"] = {
    m: round(v * KGM3_POR_LBPIE3, 1) for m, v in DENSIDADES_HELICOIDAL_LBPIE3.items()
}

# Ángulos de reposo originales [grados]
ANGULOS_REPOSO_ORIGINALES = {
    "tolva": {"Yeso": 35, "Fluorita": 32, "Cemento": 35, "Cal": 40, "Carbonato de calcio": 30,
              "Arcilla": 45, "Mineral de hierro": 37, "Caolin": 35},
    "silo": {"Yeso": 35, "Fluorita": 30, "Cemento": 32, "Cal": 40, "Carbonato de calcio": 34,
             "Arcilla": 30, "Mineral de hierro": 37, "Caolin": 29},
}

# Velocidades de banda por material (Calculo de banda vs5.py) [m/s]
VELOCIDADES_BANDA_ORIGINALES = {
    "Arena": 1.0, "Grava": 1.5, "Carbón": 2.0, "Mineral de Hierro": 2.5, "Cemento": 1.2,
}

OTRO = "Otro (capturar densidad)"


def materiales_de(modulo: str) -> tuple:
    return tuple(DENSIDADES_ORIGINALES[modulo].keys()) + (OTRO,)


def densidad_original(modulo: str, material: str) -> float | None:
    return DENSIDADES_ORIGINALES.get(modulo, {}).get(material)


def texto_discrepancia(material: str) -> str:
    valores = []
    for modulo, tabla in DENSIDADES_ORIGINALES.items():
        if material in tabla:
            valores.append(f"{modulo} {tabla[material]:g}")
    return ", ".join(valores)


def resolver_densidad(modulo: str, material: str, densidad_capturada: float, resultado) -> float:
    """Devuelve la densidad a usar y deja la advertencia correspondiente en ``resultado``.

    ``densidad_capturada > 0`` tiene prioridad. Con 0 se usa la tabla original del módulo.
    """
    from .modelo import ErrorEntrada

    if densidad_capturada and densidad_capturada > 0:
        resultado.nota(f"Densidad aparente capturada por el usuario: {densidad_capturada:g} kg/m³.")
        return float(densidad_capturada)
    valor = densidad_original(modulo, material)
    if valor is None:
        raise ErrorEntrada("Capture la densidad aparente del material (no hay valor de tabla para «Otro»).")
    resultado.advertir(
        f"Densidad de «{material}» tomada de la tabla original de este módulo ({valor:g} kg/m³), "
        f"sin fuente documentada. Valores en los módulos originales: {texto_discrepancia(material)}. "
        "Confirme la densidad APARENTE a granel con datos del material."
    )
    return float(valor)
