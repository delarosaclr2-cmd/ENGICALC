"""Constantes físicas y de conversión utilizadas por los motores de cálculo.

Cada constante indica su procedencia. Ningún motor de cálculo debe declarar
valores físicos "sueltos": todos deben importarse desde este módulo o desde la
base de datos técnica editable (carpeta ``database``).
"""

# --- Aire seco y vapor de agua (ASHRAE Handbook—Fundamentals, cap. 1 "Psychrometrics") ---
R_DRY_AIR = 287.042          # J/(kg·K)  constante del aire seco (ASHRAE Fundamentals, cap. 1)
R_WATER_VAPOR = 461.524      # J/(kg·K)  constante del vapor de agua (ASHRAE Fundamentals, cap. 1)
MW_RATIO = 0.621945          # Mw/Mda  relación de masas molares (ASHRAE Fundamentals, cap. 1, ec. 22)
CP_DRY_AIR_KJ = 1.006        # kJ/(kg·K) calor específico del aire seco (ASHRAE, ec. de entalpía 32)
CP_VAPOR_KJ = 1.86           # kJ/(kg·K) calor específico del vapor de agua (ASHRAE, ec. 32)
H_FG0_KJ = 2501.0            # kJ/kg entalpía de vaporización a 0 °C (ASHRAE, ec. 32)
VOLUME_FACTOR_VAPOR = 1.607858  # Mda/Mw (ASHRAE ec. 26: v = Rda·T·(1+1.607858·W)/p)

# --- Atmósfera estándar (ASHRAE Fundamentals cap. 1 ec. 3 y 4; equivalente ISA/US Std. Atm. 1976) ---
P_STD_SEA_LEVEL = 101325.0   # Pa
T_STD_SEA_LEVEL_C = 15.0     # °C
LAPSE_RATE = 0.0065          # K/m (troposfera)
ALT_COEF = 2.25577e-5        # 1/m  (= LAPSE_RATE / 288.15 K)
ALT_EXPONENT = 5.2559        # g·M/(R·L)
ALT_VALID_MIN_M = -500.0
ALT_VALID_MAX_M = 11000.0    # límite de la troposfera para la ecuación

# --- Ley de Sutherland para viscosidad del aire (White, Viscous Fluid Flow) ---
SUTHERLAND_MU0 = 1.716e-5    # Pa·s a T0
SUTHERLAND_T0 = 273.15       # K
SUTHERLAND_S = 110.4         # K

# --- Condiciones de referencia del aire ---
T_ZERO_K = 273.15            # K
RHO_STD_ASHRAE = 1.204       # kg/m³ aire seco 20 °C, 101.325 kPa (referencia informativa)
RHO_STD_AMCA = 1.2           # kg/m³ aire estándar AMCA (0.075 lb/ft³) — condición de catálogo típica

# --- Conversión de unidades (NIST SP 811 / ASHRAE, factores exactos donde aplica) ---
FT = 0.3048                  # m (exacto)
INCH = 0.0254                # m (exacto)
LBM = 0.45359237             # kg (exacto)
IN_WG_60F = 248.84           # Pa por pulgada de agua a 60 °F (ASHRAE / NIST SP 811)
MM_H2O = 9.80665             # Pa por mm de agua convencional
HP = 745.69987               # W por hp mecánico
PSI = 6894.757               # Pa
IN_HG_32F = 3386.389         # Pa
BTU = 1055.056               # J (IT)
CFM = FT ** 3 / 60.0         # m³/s por ft³/min
FPM = FT / 60.0              # m/s por ft/min

# Constante histórica de la ecuación imperial de potencia BHP = Q·P/(6356·η)
# (cfm, in. wg, hp). Corresponde a la pulgada de agua a ~68 °F (≈248.6 Pa).
# El programa calcula internamente en SI; esta constante solo se usa para
# reproducir la ecuación imperial en la memoria y en las pruebas.
BHP_IP_CONSTANT = 6356.0

# Rango de Reynolds para régimen laminar / transicional en ductos (criterio clásico de textos)
RE_LAMINAR_MAX = 2300.0
RE_TURBULENT_MIN = 4000.0

GRAVITY = 9.80665            # m/s²
