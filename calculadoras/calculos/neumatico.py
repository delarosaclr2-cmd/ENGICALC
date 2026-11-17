"""Transporte neumático (fase diluida).

Originales: «Calculo transportador neumatico rev 0.py» y «rev 1.py».
Correcciones:
- La relación aire/material se pedía y no se usaba: ahora define el flujo de
  sólidos (μ = kg de material por kg de aire).
- El factor de fricción fijo 0.03/0.06 se sustituye por Colebrook con la rugosidad.
- Pérdida de los sólidos: forma de Barth ΔP_s = μ·Ks·ΔP_aire con Ks = λZ/λL
  capturado por el usuario (no se inventa el coeficiente). Con Ks = 0 solo se
  calcula la pérdida del aire y se advierte que se subestima.
"""
from __future__ import annotations

from ..nucleo import constantes as K, fluidos
from ..nucleo.atmosfera import presion_por_altitud
from ..nucleo.configuracion import altitud_sitio
from ..nucleo.modelo import DATO, EMPIRICA, VERIFICADA, Calculadora, Campo, Resultado

DILUIDA, DENSA = "Fase diluida", "Fase densa"

CAMPOS = [
    Campo("fase", "Tipo de transporte", tipo="opcion", opciones=(DILUIDA, DENSA), defecto=DILUIDA, grupo="Sistema"),
    Campo("caudal", "Caudal de aire de transporte", "m³/h", minimo=0, min_incluido=False, grupo="Sistema"),
    Campo("velocidad", "Velocidad del aire", "m/s", minimo=0, min_incluido=False, grupo="Sistema",
          ayuda="El original indicaba 15–25 m/s (rango de fase diluida)."),
    Campo("relacion", "Relación de carga μ (kg material / kg aire)", "", minimo=0, grupo="Sistema",
          ayuda="El original pedía «relación aire/material, ej. 4 para 1:4»: 1 kg de aire por 4 kg de material → μ = 4."),
    Campo("longitud", "Longitud equivalente de la tubería", "m", minimo=0, min_incluido=False, grupo="Tubería"),
    Campo("rugosidad", "Rugosidad absoluta de la tubería", "mm", defecto=0, minimo=0, maximo=10, grupo="Tubería",
          ayuda="0 = tubo liso (subestima la fricción). Tomar de su referencia."),
    Campo("k_accesorios", "Suma de coeficientes K de accesorios (aire)", "", defecto=0, minimo=0, grupo="Tubería"),
    Campo("ks", "Coeficiente de pérdida adicional por sólidos Ks = λZ/λL", "", defecto=0, minimo=0, grupo="Sólidos",
          ayuda="Dato del método de la empresa (Barth). 0 = no se calcula la pérdida de los sólidos."),
    Campo("temperatura", "Temperatura del aire", "°C", defecto=20, minimo=-40, maximo=300, grupo="Aire"),
    Campo("altitud", "Altitud del sitio", "m", defecto=altitud_sitio(), minimo=-500, maximo=5000, grupo="Aire"),
    Campo("eficiencia", "Eficiencia del soplador (0–1)", "", defecto=0.75, minimo=0, maximo=1, min_incluido=False,
          grupo="Aire", ayuda="0.75 era la constante del original."),
]


def calcular(d: dict) -> Resultado:
    r = Resultado()
    q = d["caudal"] / 3600.0
    v = d["velocidad"]
    p = presion_por_altitud(d["altitud"])
    rho = fluidos.densidad_aire_seco(p, d["temperatura"])
    mu = fluidos.viscosidad_aire_sutherland(d["temperatura"])
    diam = fluidos.diametro_por_caudal(q, v)
    re = fluidos.reynolds(rho, v, diam, mu)
    f, regimen = fluidos.factor_friccion_darcy(re, d["rugosidad"] / 1000.0 / diam)

    masa_aire = rho * q
    masa_solidos = d["relacion"] * masa_aire
    dp_aire = fluidos.perdida_darcy(f, d["longitud"], diam, rho, v) + fluidos.perdida_menor(d["k_accesorios"], rho, v)
    dp_solidos = d["relacion"] * d["ks"] * dp_aire
    dp_total = dp_aire + dp_solidos
    potencia = fluidos.potencia_incompresible(dp_total, q, d["eficiencia"])

    r.agregar("diametro_mm", "Diámetro interior de la tubería", diam * 1000, "mm", 1)
    r.agregar("densidad_aire", "Densidad del aire", rho, "kg/m³", 4, DATO)
    r.agregar("masa_aire_kg_h", "Flujo másico de aire", masa_aire * 3600, "kg/h", 1)
    r.agregar("capacidad_t_h", "Capacidad de sólidos", masa_solidos * 3.6, "t/h", 3)
    r.agregar("reynolds", "Número de Reynolds", re, "", 0)
    r.agregar("friccion", f"Factor de fricción de Darcy ({regimen})", f, "", 5)
    r.agregar("dp_aire_pa", "Pérdida de presión del aire", dp_aire, "Pa", 1)
    r.agregar("dp_solidos_pa", "Pérdida adicional por sólidos", dp_solidos, "Pa", 1, EMPIRICA)
    r.agregar("dp_total_pa", "Pérdida de presión total", dp_total, "Pa", 1, EMPIRICA if d["ks"] > 0 else VERIFICADA)
    r.agregar("dp_total_cmh2o", "Pérdida de presión total", dp_total / K.PA_POR_CMH2O, "cm H₂O", 2, DATO)
    r.agregar("potencia_kw", "Potencia al eje del soplador", potencia / 1000, "kW", 3)

    if d["ks"] == 0:
        r.advertir("Ks = 0: no se incluyó la pérdida de los sólidos, que suele dominar. La presión y la potencia "
                   "están SUBESTIMADAS. Capture Ks según el método de la empresa (Barth, Mills).")
    if d["rugosidad"] == 0:
        r.advertir("Rugosidad 0: tubería lisa; la fricción real será mayor.")
    if d["fase"] == DENSA:
        r.advertir("El modelo es de fase diluida. La fase densa opera a velocidades bajas y requiere otro método.")
    if dp_total > 0.10 * p:
        r.advertir("La pérdida supera el 10 % de la presión absoluta: el aire se expande a lo largo de la línea "
                   "y el cálculo incompresible deja de ser válido; divida la línea en tramos.")
    r.nota("No se incluyen la aceleración de los sólidos ni la elevación vertical de los sólidos.")
    r.ecuacion("D = √(4·Q/(π·v));  ṁ_aire = ρ·Q;  ṁ_s = μ·ṁ_aire")
    r.ecuacion("ΔP_aire = f·(L/D)·ρ·v²/2 + ΣK·ρ·v²/2   (f por Colebrook-White)")
    r.ecuacion("ΔP_sólidos = μ·Ks·ΔP_aire   (forma de Barth, Ks del usuario)")
    r.ecuacion("P = (ΔP_aire + ΔP_sólidos)·Q/η")
    return r


CALCULADORA = Calculadora(
    id="neumatico",
    nombre="Transportador neumático",
    disciplina="Manejo de sólidos a granel",
    descripcion="Diámetro, capacidad de sólidos, pérdidas de aire y de sólidos (Barth) y potencia del soplador.",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("Calculo transportador neumatico rev 0.py", "Calculo transportador neumatico rev 1.py"),
    referencias=("Darcy-Weisbach y Colebrook-White.",
                 "Separación de pérdidas aire + sólidos (Barth); Ks debe venir de la referencia de la empresa "
                 "(p. ej. Mills, Pneumatic Conveying Design Guide)."),
    limitaciones=("Sin aceleración de sólidos ni elevación de sólidos.", "Solo fase diluida."),
    palabras_clave=("neumático", "transporte", "polvo", "soplador", "fase diluida"),
)
