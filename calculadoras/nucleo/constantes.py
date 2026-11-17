"""Constantes físicas y factores de conversión.

Todos los factores son definiciones exactas o valores normalizados de uso
general. Centralizarlos aquí elimina los factores sueltos (102, 9.795, 3.66,
0.0013, etc.) que causaban errores en las versiones originales.
"""

# --- Constantes físicas ----------------------------------------------------
G = 9.80665                 # m/s², gravedad normal (definición CGPM)
R_AIRE_SECO = 287.042       # J/(kg·K), constante del aire seco (ASHRAE)
K_AIRE = 1.4                # relación de calores específicos del aire (gas ideal diatómico)
CP_AIRE = 1.006             # kJ/(kg·K), aire seco (ASHRAE)
CP_VAPOR = 1.86             # kJ/(kg·K), vapor de agua (ASHRAE)
CP_AGUA = 4.186             # kJ/(kg·K), agua líquida (valor usual a temperatura ambiente)
H_VAPORIZACION_0C = 2501.0  # kJ/kg, entalpía de vaporización a 0 °C (ASHRAE)
EPSILON_AGUA_AIRE = 0.621945  # relación de masas molares agua/aire seco (ASHRAE)
P_ATM_NORMAL = 101325.0     # Pa, atmósfera normal
T_CERO_K = 273.15           # K

# --- Longitud ----------------------------------------------------------------
M_POR_PULGADA = 0.0254
M_POR_PIE = 0.3048
MM_POR_M = 1000.0

# --- Masa ------------------------------------------------------------------
KG_POR_LIBRA = 0.45359237

# --- Volumen y caudal --------------------------------------------------------
M3_POR_PIE3 = M_POR_PIE ** 3                     # 0.028316846592
M3_POR_GALON_US = 3.785411784e-3
M3S_POR_CFM = M3_POR_PIE3 / 60.0                 # 1 ft³/min en m³/s
M3S_POR_GPM = M3_POR_GALON_US / 60.0             # 1 gal(US)/min en m³/s
PIE3S_POR_GPM = M3S_POR_GPM / M3_POR_PIE3        # ≈ 0.002228 ft³/s por gpm
L_POR_GALON_US = 3.785411784

# --- Densidad ---------------------------------------------------------------
KGM3_POR_LBPIE3 = KG_POR_LIBRA / M3_POR_PIE3      # ≈ 16.0185

# --- Presión ----------------------------------------------------------------
PA_POR_MMH2O = 9.80665       # mm de columna de agua convencional
PA_POR_CMH2O = 98.0665
PA_POR_PSI = 6894.757293168
PA_POR_KGFCM2 = 98066.5

# --- Potencia y energía -----------------------------------------------------
W_POR_HP = 745.6998715822702  # HP mecánico (550 ft·lbf/s)
W_POR_BTUH = 0.2930710701722222
KJ_POR_BTU = 1.05505585262

# --- Hidráulica en unidades inglesas -----------------------------------------
G_PIES = G / M_POR_PIE                # ≈ 32.174 ft/s²
PIES_POR_PSI_AGUA = PA_POR_PSI / (999.0 * G) / M_POR_PIE   # ≈ 2.31 ft por psi (agua ~15 °C)
GPM_PIE_POR_HP = 3960.0               # gpm·ft/3960 = HP hidráulico (agua, GE = 1)


def hp_a_kw(hp: float) -> float:
    """Convierte HP mecánico a kW."""
    return hp * W_POR_HP / 1000.0


def kw_a_hp(kw: float) -> float:
    """Convierte kW a HP mecánico."""
    return kw * 1000.0 / W_POR_HP
