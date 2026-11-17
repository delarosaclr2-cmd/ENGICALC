"""Cálculo de soplador y tubería.

Originales: «Calculo de soplador Rev 0.py» (el que abría el menú), «Rev 1» y «Rev 2» (idénticos).
Correcciones:
- Potencia: P = ΔP·Q/(102·η) con ΔP en Pa sobreestimaba 9.81 veces (102 es
  para mm H₂O). Ahora se calcula P = ΔP·Q/η y, además, la potencia adiabática
  (gas compresible), que es la correcta cuando la relación de presiones crece.
- Rev 0 y Rev 2 clasificaban distinto el mismo punto; se conserva la
  clasificación de Rev 0 (la que usaba el menú) como criterio orientativo.
- La gráfica de Rev 1/Rev 2 usaba rangos marcados como «ejemplo»; se retira.

v2.1.0: se distingue el tipo de máquina. Un soplador de lóbulos (Roots) no
tiene compresión interna: la compresión es externa e isocórica y el trabajo
teórico es Q₁·Δp (Leybold, «How does a Roots pump work?»; Atlas Copco,
«Screw versus Roots technology»). Las máquinas dinámicas o con compresión
interna se evalúan con la compresión adiabática. Se agrega la temperatura de
descarga por balance de energía (carcasa adiabática): T₂ = T₁ + P_eje/(ṁ·cp).
"""
from __future__ import annotations

from ..nucleo import constantes as K, fluidos
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
from ..nucleo.modelo import DATO, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo, Resultado

DINAMICO = "Dinámico (centrífugo, canal lateral) o con compresión interna (tornillo)"
LOBULOS = "Desplazamiento positivo de lóbulos (Roots): compresión externa"

CAMPOS = [
    Campo("tipo_maquina", "Tipo de máquina", tipo="opcion", opciones=(DINAMICO, LOBULOS), defecto=DINAMICO),
    Campo("caudal", "Caudal de aire a condiciones de succión", "m³/h", minimo=0, min_incluido=False),
    Campo("presion", "Presión diferencial", "Pa", minimo=0, min_incluido=False),
    Campo("velocidad", "Velocidad del aire en la tubería", "m/s", defecto=20, minimo=0, min_incluido=False,
          ayuda="Valor por defecto del original (Rev 0)."),
    Campo("eficiencia", "Eficiencia del soplador (0–1)", "", defecto=0.8, minimo=0, maximo=1, min_incluido=False,
          ayuda="0.8 era la constante del original."),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000,
          ayuda="Define la presión absoluta de succión (succión atmosférica)."),
    Campo("temperatura", "Temperatura del aire en la succión", "°C", defecto=20, minimo=-40, maximo=200),
    Campo("k", "Relación de calores específicos k", "", defecto=K.K_AIRE, minimo=1.0, maximo=1.7,
          min_incluido=False),
]


def tipo_soplador_rev0(caudal_m3h: float, presion_pa: float) -> str:
    """Clasificación de Rev 0 (sin fuente documentada)."""
    if caudal_m3h <= 500 and presion_pa <= 5000:
        return "Soplador de canal lateral"
    if caudal_m3h <= 3000 and presion_pa <= 50000:
        return "Soplador centrífugo"
    if presion_pa > 50000:
        return "Soplador tipo Roots o de lóbulos"
    return "Soplador multietapas o personalizado"


def calcular(d: dict) -> Resultado:
    r = Resultado()
    q = d["caudal"] / 3600.0
    p1 = presion_por_altitud(d["altitud"])
    p2 = p1 + d["presion"]
    p_inc = fluidos.potencia_incompresible(d["presion"], q, d["eficiencia"])
    p_adi = fluidos.potencia_adiabatica(p1, q, p2, d["k"], d["eficiencia"])
    diam = fluidos.diametro_por_caudal(q, d["velocidad"])
    lobulos = d["tipo_maquina"] == LOBULOS
    p_eje = p_inc if lobulos else p_adi
    t1 = d["temperatura"] + K.T_CERO_K
    masa = p1 * q / (K.R_AIRE_SECO * t1)
    cp = d["k"] * K.R_AIRE_SECO / (d["k"] - 1.0)
    t2 = t1 + p_eje / (masa * cp)

    r.agregar("presion_succion_kpa", "Presión absoluta de succión", p1 / 1000, "kPa", 2, DATO)
    r.agregar("relacion_presiones", "Relación de presiones p₂/p₁", p2 / p1, "", 4)
    r.agregar("masa_kg_h", "Flujo másico de aire", masa * 3600, "kg/h", 1)
    r.agregar("potencia_eje_kw", "Potencia al eje recomendada para el tipo de máquina", p_eje / 1000, "kW", 3)
    r.agregar("potencia_eje_hp", "Potencia al eje recomendada", p_eje / K.W_POR_HP, "HP", 3, DATO)
    r.agregar("potencia_adiabatica_kw", "Potencia al eje (compresión adiabática)", p_adi / 1000, "kW", 3)
    r.agregar("potencia_adiabatica_hp", "Potencia al eje (adiabática)", p_adi / K.W_POR_HP, "HP", 3, DATO)
    r.agregar("potencia_incompresible_kw", "Potencia al eje (Q·Δp/η: isocórica, lóbulos)", p_inc / 1000, "kW", 3)
    r.agregar("t_descarga", "Temperatura de descarga (balance de energía, carcasa adiabática)", t2 - K.T_CERO_K,
              "°C", 1)
    r.agregar("diametro_mm", "Diámetro de la tubería", diam * 1000, "mm", 1)
    r.agregar("tipo", "Tipo de soplador sugerido", tipo_soplador_rev0(d["caudal"], d["presion"]), nivel=ORIGINAL,
              nota="Clasificación de Rev 0 sin fuente; Rev 2 daba otra para los mismos datos.")

    diferencia = (p_inc - p_adi) / p_adi * 100
    if lobulos:
        r.nota("Soplador de lóbulos: compresión externa (isocórica); trabajo teórico Q₁·Δp. La potencia adiabática "
               "se muestra solo como referencia (subestima la de esta máquina).")
    elif abs(diferencia) > 2:
        r.advertir(f"El modelo incompresible difiere {diferencia:+.1f} % del adiabático: para esta máquina use la "
                   "potencia adiabática.")
    if t2 - K.T_CERO_K > 150:
        r.advertir("Temperatura de descarga mayor de 150 °C: verifique el límite del fabricante y considere "
                   "enfriamiento o compresión en etapas.")
    r.advertir("La clasificación del tipo de soplador es orientativa (criterio original sin fuente). "
               "Seleccione el equipo con curvas del fabricante.")
    r.ecuacion("P_incompresible = ΔP·Q/η")
    r.ecuacion("P_adiabática = k/(k−1)·p₁·Q₁·[(p₂/p₁)^((k−1)/k) − 1]/η")
    r.ecuacion("ṁ = p₁·Q₁/(R·T₁);   T₂ = T₁ + P_eje/(ṁ·cp),   cp = k·R/(k−1)")
    r.ecuacion("D = √(4·Q/(π·v))")
    r.nota("Q es el caudal a condiciones de succión; p₁ es la presión atmosférica del sitio.")
    return r


CALCULADORA = Calculadora(
    id="soplador",
    nombre="Soplador",
    disciplina="Ventilación y control de polvo",
    descripcion="Potencia al eje (adiabática e incompresible), diámetro de tubería y tipo orientativo.",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("Calculo de soplador Rev 0.py", "Calculo de soplador Rev 1.py", "Calculo de soplador Rev 2.py"),
    estado_validacion=VALIDADA_CONDICIONES,
    referencias=("Compresión adiabática de gas ideal (termodinámica clásica).",
                 "Sopladores de lóbulos: compresión externa isocórica, P = Q₁·Δp (Leybold, Vacuum Fundamentals; "
                 "Atlas Copco, «Screw versus Roots technology in low pressure blowers»).",
                 "Validación: tests/test_soplador.py (ruta independiente por entalpía y ejemplo Atlas Copco)."),
    limitaciones=("Tipo de soplador sugerido: criterio original sin fuente (nivel O).",
                  "La temperatura de descarga supone carcasa adiabática (sin pérdidas de calor): es conservadora.",
                  "La eficiencia debe tomarse de la curva del fabricante."),
    palabras_clave=("soplador", "blower", "roots", "aire", "compresión"),
)
