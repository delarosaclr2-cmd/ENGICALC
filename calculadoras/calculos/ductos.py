"""Dimensionamiento de ductos de aire con polvo.

Original: «Calculo de dimensionamientos de ductos con polvo.py».
Corrección: el método original era consistente; se agregan factor de fricción por
Colebrook (opcional), pérdidas por accesorios, densidad por altitud y la
verificación de velocidad mínima de transporte. Se usa 9.80665 Pa/mm H₂O
(antes 9.795).

v2.1.0 (validación profesional):
- Rugosidad por material según las categorías de ASHRAE Handbook — Fundamentals,
  capítulo «Duct Design», tabla 1 (liso 0.03 mm, medianamente liso 0.09 mm,
  promedio 0.15 mm, medianamente rugoso 0.9 mm, rugoso 3.0 mm). Antes, con
  rugosidad 0 el ducto se calculaba liso.
- Velocidad mínima de transporte por tipo de contaminante según ACGIH,
  Industrial Ventilation — A Manual of Recommended Practice for Design («Range
  of minimum duct design velocities»), corregida por densidad con la ecuación
  5.1 de la 31.ª edición: v_min/√df, df = ρ/0.075 lb/ft³.
- Validado contra el ejemplo ASHRAE DFDB de ducto redondo de 24 plg (610 mm):
  ver tests/test_ductos.py.
"""
from __future__ import annotations

from ..nucleo import constantes as K, fluidos
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
import math

from ..nucleo.modelo import (DATO, EMPIRICA, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo, Resultado,
                             requerir)

# ASHRAE Fundamentals, Duct Design, tabla 1: categorías de rugosidad absoluta [mm]
MATERIALES_DUCTO = {
    "Liso — acero al carbono limpio, PVC, aluminio (0.03 mm)": 0.03,
    "Medianamente liso — acero galvanizado, costura longitudinal o espiral (0.09 mm)": 0.09,
    "Promedio — galvanizado por inmersión, juntas a 760 mm (0.15 mm)": 0.15,
    "Medianamente rugoso — fibra de vidrio rígido, espiral corrugado (0.9 mm)": 0.9,
    "Rugoso — ducto flexible extendido (3.0 mm)": 3.0,
}
# ACGIH, «Range of minimum duct design velocities» [ft/min]: (mínimo, máximo o None)
CONTAMINANTES = {
    "No verificar / capturar velocidad mínima": None,
    "Vapores, gases y humo (cualquier velocidad; óptimo 1000–2000 fpm)": (1000, 2000),
    "Humos metálicos — soldadura (2000–2500 fpm)": (2000, 2500),
    "Polvo muy fino y ligero — pelusa de algodón, harina de madera (2500–3000 fpm)": (2500, 3000),
    "Polvos secos — polvo de hule, baquelita, jabón, virutas ligeras (3000–4000 fpm)": (3000, 4000),
    "Polvo industrial promedio — caliza, arcilla, harina de sílice, manejo de materiales (3500–4000 fpm)":
        (3500, 4000),
    "Polvos pesados — aserrín húmedo, rebaba metálica, arena de chorro, plomo (4000–4500 fpm)": (4000, 4500),
    "Polvos pesados o húmedos — cemento húmedo, cal viva (4500 fpm o más)": (4500, None),
}
RHO_ESTANDAR_ACGIH = 0.075 * 16.01846337  # 0.075 lb/ft³ en kg/m³
M_S_POR_FPM = 0.3048 / 60.0

CAMPOS = [
    Campo("caudal", "Caudal de aire", "m³/h", minimo=0, min_incluido=False, grupo="Flujo"),
    Campo("velocidad", "Velocidad de diseño en el ducto", "m/s", minimo=0, min_incluido=False, grupo="Flujo",
          ayuda="Debe ser mayor o igual a la velocidad mínima de transporte del polvo."),
    Campo("contaminante", "Tipo de contaminante (velocidad mínima ACGIH)", tipo="opcion",
          opciones=tuple(CONTAMINANTES), defecto="No verificar / capturar velocidad mínima", grupo="Flujo"),
    Campo("velocidad_minima", "Velocidad mínima de transporte capturada", "m/s", defecto=0, minimo=0,
          grupo="Flujo", ayuda="Si > 0 sustituye a la tabla ACGIH (dato de la empresa o del fabricante)."),
    Campo("temperatura", "Temperatura del aire", "°C", defecto=20, minimo=-40, maximo=400, grupo="Aire"),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000, grupo="Aire"),
    Campo("densidad", "Densidad del aire", "kg/m³", defecto=0, minimo=0, grupo="Aire",
          ayuda="0 = calcular como aire seco con la altitud y la temperatura."),
    Campo("longitud", "Longitud del ducto", "m", minimo=0, min_incluido=False, grupo="Ducto"),
    Campo("friccion", "Factor de fricción de Darcy", "", defecto=0, minimo=0, maximo=0.2, grupo="Ducto",
          ayuda="0 = calcular con Colebrook-White a partir de la rugosidad. Es el factor de DARCY (4 × Fanning)."),
    Campo("material_ducto", "Material del ducto (rugosidad ASHRAE)", tipo="opcion", opciones=tuple(MATERIALES_DUCTO),
          defecto="Medianamente liso — acero galvanizado, costura longitudinal o espiral (0.09 mm)", grupo="Ducto"),
    Campo("rugosidad", "Rugosidad absoluta capturada", "mm", defecto=0, minimo=0, maximo=10, grupo="Ducto",
          ayuda="0 = según el material elegido. Se usa solo si el factor de fricción es 0."),
    Campo("k_accesorios", "Suma de coeficientes K de accesorios", "", defecto=0, minimo=0, grupo="Ducto",
          ayuda="Campanas, codos, transiciones (ΣK). 0 = solo tramo recto."),
    Campo("eficiencia", "Eficiencia del ventilador (0–1)", "", minimo=0, maximo=1, min_incluido=False,
          grupo="Ventilador"),
]


def velocidad_minima(d: dict, rho: float, r: Resultado) -> tuple[float | None, float | None]:
    """Velocidad mínima de transporte [m/s] y extremo superior del intervalo ACGIH (si existe).

    Prioridad: valor capturado > tabla ACGIH corregida por densidad (v/√df, df = ρ/ρ_estándar).
    """
    if d["velocidad_minima"] > 0:
        r.nota(f"Velocidad mínima de transporte capturada: {d['velocidad_minima']:g} m/s.")
        return float(d["velocidad_minima"]), None
    intervalo = CONTAMINANTES[d["contaminante"]]
    if intervalo is None:
        return None, None
    if d["contaminante"].startswith("Vapores"):
        r.nota("Vapores, gases y humo: ACGIH admite cualquier velocidad; el intervalo 1000–2000 fpm es el óptimo "
               "económico, no un mínimo de transporte.")
        return None, None
    df = rho / RHO_ESTANDAR_ACGIH
    correccion = 1.0 / math.sqrt(df)
    v_min = intervalo[0] * M_S_POR_FPM * correccion
    v_max = intervalo[1] * M_S_POR_FPM * correccion if intervalo[1] else None
    r.nota(f"Velocidad mínima ACGIH {intervalo[0]} fpm corregida por densidad (df = {df:.3f}): ×{correccion:.3f}.")
    return v_min, v_max


def calcular(d: dict) -> Resultado:
    r = Resultado()
    q = d["caudal"] / 3600.0
    v = d["velocidad"]
    presion = presion_por_altitud(d["altitud"])
    rho = d["densidad"] if d["densidad"] > 0 else fluidos.densidad_aire_seco(presion, d["temperatura"])
    mu = fluidos.viscosidad_aire_sutherland(d["temperatura"])

    diam = fluidos.diametro_por_caudal(q, v)
    re = fluidos.reynolds(rho, v, diam, mu)
    rugosidad = d["rugosidad"] if d["rugosidad"] > 0 else MATERIALES_DUCTO[d["material_ducto"]]
    if d["friccion"] > 0:
        f, regimen = d["friccion"], "capturado"
    else:
        f, regimen = fluidos.factor_friccion_darcy(re, rugosidad / 1000.0 / diam)
        if d["rugosidad"] > 0:
            r.nota(f"Rugosidad capturada: {rugosidad:g} mm (sustituye a la categoría ASHRAE del material).")
        if regimen == "transición":
            r.advertir("Reynolds en zona de transición (2 300–4 000): factor de fricción incierto.")

    dp_friccion = fluidos.perdida_darcy(f, d["longitud"], diam, rho, v)
    dp_acc = fluidos.perdida_menor(d["k_accesorios"], rho, v)
    dp_total = dp_friccion + dp_acc
    potencia = fluidos.potencia_incompresible(dp_total, q, d["eficiencia"])

    r.agregar("diametro_m", "Diámetro interior del ducto", diam, "m", 4)
    r.agregar("diametro_mm", "Diámetro interior del ducto", diam * 1000, "mm", 1)
    r.agregar("densidad", "Densidad del aire usada", rho, "kg/m³", 4, DATO)
    r.agregar("reynolds", "Número de Reynolds", re, "", 0)
    if d["friccion"] == 0:
        r.agregar("rugosidad", "Rugosidad absoluta usada", rugosidad, "mm", 2, DATO if d["rugosidad"] > 0 else EMPIRICA)
    r.agregar("friccion", f"Factor de fricción de Darcy ({regimen})", f, "", 5)
    r.agregar("dp_friccion_pa", "Pérdida por fricción", dp_friccion, "Pa", 1)
    r.agregar("dp_accesorios_pa", "Pérdida por accesorios", dp_acc, "Pa", 1)
    r.agregar("dp_total_pa", "Pérdida de presión total", dp_total, "Pa", 1)
    r.agregar("dp_total_mmh2o", "Pérdida de presión total", dp_total / K.PA_POR_MMH2O, "mm H₂O", 2)
    r.agregar("potencia_kw", "Potencia al eje del ventilador", potencia / 1000, "kW", 3)
    r.agregar("potencia_hp", "Potencia al eje del ventilador", potencia / K.W_POR_HP, "HP", 3, DATO)

    v_min, v_max = velocidad_minima(d, rho, r)
    if v_min is not None:
        r.agregar("velocidad_minima", "Velocidad mínima de transporte", v_min, "m/s", 1,
                  DATO if d["velocidad_minima"] > 0 else EMPIRICA)
        cumple = v >= v_min * (1 - 1e-9)
        r.agregar("cumple_velocidad", "Cumple velocidad mínima de transporte", cumple, "", 0,
                  DATO if d["velocidad_minima"] > 0 else EMPIRICA)
        if not cumple:
            r.advertir(f"NO CUMPLE: la velocidad de diseño ({v:g} m/s) es menor que la mínima de transporte "
                       f"({v_min:.1f} m/s): el polvo puede sedimentar en el ducto.")
        elif v_max is not None and v > v_max * 1.25:
            r.advertir(f"La velocidad de diseño supera ampliamente el intervalo ACGIH ({v_max:.1f} m/s máx. del "
                       "intervalo): mayor desgaste por abrasión y mayor consumo de energía.")
    else:
        r.nota("No se verificó la velocidad mínima de transporte del polvo (dato no capturado).")
    if dp_total > 0.05 * presion:
        r.advertir("La pérdida supera el 5 % de la presión absoluta: la hipótesis de flujo incompresible pierde validez.")

    r.ecuacion("D = √(4·Q / (π·v))")
    r.ecuacion("Re = ρ·v·D/μ   (μ del aire por la ley de Sutherland)")
    r.ecuacion("1/√f = −2·log₁₀(ε/(3.7·D) + 2.51/(Re·√f))   (Colebrook-White, si f no se captura)")
    r.ecuacion("ΔP = f·(L/D)·ρ·v²/2 + ΣK·ρ·v²/2")
    r.ecuacion("P = ΔP·Q/η")
    r.ecuacion("v_min = v_min,ACGIH/√df;   df = ρ/(0.075 lb/ft³)   (ACGIH, 31.ª ed., ec. 5.1)")
    r.nota("Condiciones de validez: tramo de sección circular, flujo incompresible, carga de polvo baja "
           "(no se corrige la densidad de la mezcla).")
    return r


CALCULADORA = Calculadora(
    id="ductos",
    nombre="Ductos de aire con polvo",
    disciplina="Ventilación y control de polvo",
    descripcion="Diámetro, pérdida de presión (Darcy-Weisbach) y potencia de ventilador para un ducto circular.",
    campos=CAMPOS,
    funcion=calcular,
    estado_validacion=VALIDADA_CONDICIONES,
    archivos_originales=("Calculo de dimensionamientos de ductos con polvo.py",),
    referencias=("Darcy-Weisbach y Colebrook-White (mecánica de fluidos clásica).",
                 "Viscosidad del aire: ley de Sutherland.",
                 "Rugosidad: ASHRAE Handbook — Fundamentals, Duct Design, tabla 1 (categorías de rugosidad).",
                 "Velocidades mínimas de diseño: ACGIH, Industrial Ventilation — A Manual of Recommended Practice "
                 "for Design; corrección por densidad: 31.ª ed., ec. 5.1.",
                 "Validación: ejemplo de ducto redondo de 24 plg con la base ASHRAE DFDB (tests/test_ductos.py)."),
    limitaciones=("No incluye campanas ni accesorios salvo por ΣK capturado.",
                  "No corrige por la carga de polvo en la densidad del aire."),
    palabras_clave=("ventilación", "ducto", "polvo", "darcy", "ventilador"),
)
