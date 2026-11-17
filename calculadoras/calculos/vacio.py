"""Dimensionamiento de bomba de vacío y ducto de succión.

Originales: «calculo de bomba de vacio.py» (rev0) y «calculo de bomba de vacio rev1.py».
Correcciones:
- La rev1 usaba k/(k−1)·Patm·Q·[1 − (ps/Patm)^m], que no es la compresión de ps
  a la atmósfera (error de 45 % a 60 kPa y de 27 veces a 1 kPa). Ahora:
  P = k/(k−1)·ps·Qs·[(pd/ps)^m − 1]/η con Qs a condiciones de succión.
- Presión de descarga = presión atmosférica del sitio (antes 101.3 kPa fija).
- Se valida 0 < ps < pd (antes daba potencia negativa o un número complejo).
- Tipo de bomba y velocidad de ducto por rangos: criterios originales sin fuente.
"""
from __future__ import annotations

from ..nucleo import constantes as K, fluidos
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
from ..nucleo.modelo import DATO, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo, Resultado, requerir

CFM, M3H = "CFM (ft³/min)", "m³/h"

CAMPOS = [
    Campo("caudal", "Caudal a condiciones de succión", "", minimo=0, min_incluido=False, grupo="Bomba"),
    Campo("unidad_caudal", "Unidad del caudal", tipo="opcion", opciones=(CFM, M3H), defecto=CFM, grupo="Bomba"),
    Campo("presion_succion", "Presión absoluta de succión", "kPa", minimo=0, min_incluido=False, grupo="Bomba"),
    Campo("presion_descarga", "Presión absoluta de descarga", "kPa", defecto=0, minimo=0, grupo="Bomba",
          ayuda="0 = presión atmosférica del sitio (por altitud)."),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000, grupo="Bomba"),
    Campo("temperatura", "Temperatura del gas en la succión", "°C", defecto=20, minimo=-40, maximo=200,
          grupo="Bomba"),
    Campo("eficiencia", "Eficiencia global (0–1)", "", defecto=0.85, minimo=0, maximo=1, min_incluido=False,
          grupo="Bomba", ayuda="0.85 era la constante del original. Use el dato del fabricante."),
    Campo("k", "Relación de calores específicos k", "", defecto=K.K_AIRE, minimo=1.0, maximo=1.7,
          min_incluido=False, grupo="Bomba"),
    Campo("velocidad_ducto", "Velocidad en el ducto de succión", "m/s", defecto=0, minimo=0, grupo="Ducto",
          ayuda="0 = usar la tabla de velocidades por presión del original (sin fuente)."),
]


def velocidad_ducto_original(presion_kpa: float) -> float:
    """Tabla original de velocidad recomendada según presión absoluta (sin fuente)."""
    if 60 < presion_kpa:
        return 15.0
    if 10 < presion_kpa <= 60:
        return 10.0
    if 1 < presion_kpa <= 10:
        return 6.5
    if 0.01 < presion_kpa <= 1:
        return 2.5
    if 0.00001 < presion_kpa <= 0.01:
        return 0.8
    return 0.5


def tipo_bomba_original(presion_kpa: float) -> str:
    """Clasificación original por presión de succión (sin fuente)."""
    if presion_kpa > 59:
        return "Bomba de anillo líquido"
    if presion_kpa > 10:
        return "Paletas rotativas"
    if presion_kpa > 1:
        return "Bomba de tornillo"
    if presion_kpa > 0.01:
        return "Bomba Roots (booster)"
    return "Bomba de difusión o criogénica"


def calcular(d: dict) -> Resultado:
    r = Resultado()
    q = d["caudal"] * (K.M3S_POR_CFM if d["unidad_caudal"] == CFM else 1 / 3600.0)
    ps = d["presion_succion"] * 1000.0
    pd = d["presion_descarga"] * 1000.0 if d["presion_descarga"] > 0 else presion_por_altitud(d["altitud"])
    requerir(ps < pd, f"La presión de succión ({ps / 1000:.3f} kPa) debe ser menor que la de descarga "
                      f"({pd / 1000:.3f} kPa); de lo contrario no hay vacío.")

    p_teorica = fluidos.potencia_adiabatica(ps, q, pd, d["k"], 1.0)
    p_eje = p_teorica / d["eficiencia"]
    p_iso = fluidos.potencia_isotermica(ps, q, pd)
    masa = ps * q / (K.R_AIRE_SECO * (d["temperatura"] + K.T_CERO_K)) * 3600

    if d["velocidad_ducto"] > 0:
        v, nivel_v = d["velocidad_ducto"], DATO
    else:
        v, nivel_v = velocidad_ducto_original(d["presion_succion"]), ORIGINAL
        r.advertir("Velocidad del ducto tomada de la tabla original por rangos de presión (sin fuente).")
    diam = fluidos.diametro_por_caudal(q, v)

    r.agregar("caudal_m3h", "Caudal a succión", q * 3600, "m³/h", 2, DATO)
    r.agregar("presion_descarga_kpa", "Presión absoluta de descarga", pd / 1000, "kPa", 2, DATO)
    r.agregar("relacion_compresion", "Relación de compresión pd/ps", pd / ps, "", 2)
    r.agregar("masa_kg_h", "Flujo másico de aire seco", masa, "kg/h", 3)
    r.agregar("potencia_teorica_kw", "Potencia teórica adiabática", p_teorica / 1000, "kW", 3)
    r.agregar("potencia_isotermica_kw", "Potencia teórica isotérmica (mínima ideal)", p_iso / 1000, "kW", 3)
    r.agregar("potencia_eje_kw", "Potencia al eje (adiabática/η)", p_eje / 1000, "kW", 3)
    r.agregar("potencia_eje_hp", "Potencia al eje", p_eje / K.W_POR_HP, "HP", 3, DATO)
    r.agregar("tipo", "Tipo de bomba sugerido", tipo_bomba_original(d["presion_succion"]), nivel=ORIGINAL)
    r.agregar("velocidad_ducto", "Velocidad en ducto de succión", v, "m/s", 2, nivel_v)
    r.agregar("diametro_ducto_mm", "Diámetro del ducto de succión", diam * 1000, "mm", 1)

    r.advertir("Tipo de bomba: criterio original sin fuente. Verifique con curvas del fabricante.")
    r.nota("Las bombas de anillo líquido se acercan más al modelo isotérmico; las secas, al adiabático.")
    r.ecuacion("P = k/(k−1)·ps·Qs·[(pd/ps)^((k−1)/k) − 1]/η")
    r.ecuacion("P_iso = ps·Qs·ln(pd/ps)")
    r.ecuacion("ṁ = ps·Qs/(R·T)")
    r.ecuacion("D = √(4·Qs/(π·v))")
    return r


CALCULADORA = Calculadora(
    id="vacio",
    nombre="Bomba de vacío",
    disciplina="Máquinas de fluido y bombeo",
    descripcion="Potencia de compresión de la presión de vacío a la atmosférica y ducto de succión.",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("calculo de bomba de vacio.py", "calculo de bomba de vacio rev1.py"),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("Compresión adiabática e isotérmica de gas ideal.",
                 "Presión atmosférica: ASHRAE Fundamentals, cap. 1, ec. 3.",
                 "Validación de la potencia: tests/test_vacio.py (ruta independiente por entalpía e integral p·dV)."),
    limitaciones=("Validada solo la potencia de compresión de gas ideal (adiabática e isotérmica).",
                  "Tipo de bomba y velocidades de ducto: criterios originales sin fuente (nivel O).",
                  "La tabla «Tabla aplicación Bomba de vacio.png» (F:\\) no está en el proyecto."),
    palabras_clave=("vacío", "bomba", "anillo líquido", "succión"),
)
