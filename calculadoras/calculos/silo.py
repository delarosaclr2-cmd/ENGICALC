"""Silo metálico cilíndrico con tolva cónica.

Original: «Calculo de un silo metalico.py».
Correcciones (el original no tenía base estructural):
- Geometría: la altura de la tolva sale del semiángulo y del diámetro de
  descarga; el cilindro aloja el resto del volumen (antes reparto fijo 60/40).
- Presiones: teoría de Janssen (antes ρ·g·h llamado «presión lateral»).
- Espesor: anillo a presión horizontal t = ph·r/(σ_adm·E) + corrosión, con
  espesor mínimo constructivo (antes factor × D × 10 mm, con aluminio más
  delgado que acero).
- Caudal de descarga: Beverloo (antes masa/10, siempre 10 minutos).
NO se verifican: pandeo por compresión axial, presiones de descarga y
excentricidad según EN 1991-4, tolva, viento ni sismo.
"""
from __future__ import annotations

import math

from ..nucleo import solidos
from ..nucleo.materiales import materiales_de, resolver_densidad
from ..nucleo.modelo import (DATO, EMPIRICA, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo, ErrorEntrada,
                             Resultado, requerir)

CAMPOS = [
    Campo("masa", "Masa de material almacenado", "kg", minimo=0, min_incluido=False, grupo="Material"),
    Campo("material", "Material", tipo="opcion", opciones=materiales_de("silo"), defecto="Cemento", grupo="Material"),
    Campo("densidad", "Densidad aparente", "kg/m³", defecto=0, minimo=0, grupo="Material",
          ayuda="0 = tabla original del silo (sin fuente). Para presiones use el valor superior de diseño."),
    Campo("k", "Relación de presión lateral K", "", minimo=0, maximo=1.5, min_incluido=False, grupo="Material",
          ayuda="Propiedad del material (p. ej. EN 1991-4, anexo E). Jaky: K₀ = 1 − sen φ."),
    Campo("mu", "Coeficiente de fricción con la pared μ", "", minimo=0, maximo=1.5, min_incluido=False,
          grupo="Material", ayuda="Propiedad material–pared (ensayo o tabla de la norma)."),
    Campo("particula", "Tamaño medio de partícula", "mm", defecto=0, minimo=0, grupo="Material",
          ayuda="Para el caudal de descarga (Beverloo)."),
    Campo("diametro", "Diámetro del cilindro", "m", minimo=0, min_incluido=False, grupo="Geometría"),
    Campo("semiangulo", "Semiángulo de la tolva respecto a la vertical", "°", minimo=0, maximo=80,
          min_incluido=False, grupo="Geometría"),
    Campo("diametro_descarga", "Diámetro de la descarga", "m", minimo=0, min_incluido=False, grupo="Geometría"),
    Campo("esfuerzo_admisible", "Esfuerzo admisible de la lámina", "MPa", minimo=0, min_incluido=False,
          grupo="Envolvente", ayuda="Según el código y material de diseño de la empresa."),
    Campo("eficiencia_junta", "Eficiencia de junta soldada (0–1)", "", defecto=1.0, minimo=0, maximo=1,
          min_incluido=False, grupo="Envolvente"),
    Campo("corrosion", "Sobreespesor por corrosión/desgaste", "mm", defecto=0, minimo=0, grupo="Envolvente"),
    Campo("espesor_minimo", "Espesor mínimo constructivo", "mm", defecto=2, minimo=0, grupo="Envolvente",
          ayuda="2 mm era el mínimo del original."),
    Campo("factor_descarga", "Factor de sobrepresión de descarga", "", defecto=1.0, minimo=1, maximo=3,
          grupo="Envolvente", ayuda="Multiplica la presión estática de Janssen. Tomar de la norma (EN 1991-4)."),
]


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rho = resolver_densidad("silo", d["material"], d["densidad"], r)
    D, d0 = d["diametro"], d["diametro_descarga"]
    requerir(d0 < D, "El diámetro de descarga debe ser menor que el del cilindro.")
    alfa = math.radians(d["semiangulo"])

    volumen = d["masa"] / rho
    h_tolva = (D - d0) / 2 / math.tan(alfa)
    v_tolva = solidos.volumen_tronco_cono(D, d0, h_tolva)
    area = math.pi * D ** 2 / 4
    h_cil = max(0.0, (volumen - v_tolva) / area)
    if volumen <= v_tolva:
        r.advertir("Todo el material cabe en la tolva: el cilindro no es necesario con estas dimensiones.")

    j = solidos.janssen(h_cil, rho, D, d["k"], d["mu"])
    ph_diseno = j["ph"] * d["factor_descarga"]
    sigma = d["esfuerzo_admisible"] * 1e6
    t_req = ph_diseno * (D / 2) / (sigma * d["eficiencia_junta"]) * 1000 + d["corrosion"]
    t_adop = max(t_req, d["espesor_minimo"])

    try:
        flujo = solidos.descarga_beverloo(rho, d0, d["particula"] / 1000.0)
    except ValueError as e:
        raise ErrorEntrada(str(e)) from e
    aviso_beverloo = solidos.advertencia_beverloo(d["particula"])

    r.agregar("volumen", "Volumen de material", volumen, "m³", 3)
    r.agregar("altura_tolva", "Altura de la tolva cónica", h_tolva, "m", 3)
    r.agregar("volumen_tolva", "Volumen de la tolva", v_tolva, "m³", 3)
    r.agregar("altura_cilindro", "Altura de material en el cilindro", h_cil, "m", 3)
    r.agregar("altura_total", "Altura total (tolva + cilindro, sin cono de sobrecarga)", h_tolva + h_cil, "m", 3)
    r.agregar("ph", "Presión horizontal en la base del cilindro (Janssen)", j["ph"] / 1000, "kPa", 2)
    r.agregar("pv", "Presión vertical en la base del cilindro", j["pv"] / 1000, "kPa", 2)
    r.agregar("pw", "Fricción en pared en la base del cilindro", j["pw"] / 1000, "kPa", 2)
    r.agregar("ph_max", "Presión horizontal asintótica (cilindro infinito)", j["ph_max"] / 1000, "kPa", 2)
    r.agregar("n_axial", "Compresión axial en la pared por fricción (base)", j["n_axial"] / 1000, "kN/m", 2)
    r.agregar("ph_diseno", "Presión horizontal de diseño (× factor de descarga)", ph_diseno / 1000, "kPa", 2)
    r.agregar("espesor_requerido", "Espesor de predimensionamiento por presión circunferencial", t_req, "mm", 2,
              nota="Solo tensión circunferencial; no es espesor de diseño")
    r.agregar("espesor_adoptado", "Espesor mínimo de predimensionamiento (sin pandeo)", t_adop, "mm", 2,
              nota="No apto para diseño estructural")
    r.agregar("flujo_t_h", "Caudal de descarga por gravedad (Beverloo)", flujo * 3.6, "t/h", 2, EMPIRICA)
    r.agregar("flujo_kg_min", "Caudal de descarga por gravedad (Beverloo)", flujo * 60, "kg/min", 1, EMPIRICA)

    r.advertir("PREDIMENSIONAMIENTO — NO APTO PARA DISEÑO ESTRUCTURAL. No se verificó el pandeo por compresión "
               "axial (EN 1993-4-1), las presiones de descarga normativas (EN 1991-4), la tolva, el viento, el sismo "
               "ni los apoyos. El espesor reportado cubre solo la tensión circunferencial por presión de llenado.")
    if aviso_beverloo:
        r.advertir(aviso_beverloo)
    if d["factor_descarga"] == 1.0:
        r.advertir("Factor de descarga = 1: presiones solo estáticas. La descarga y la excentricidad las aumentan.")
    r.nota("No se calcularon presiones en la tolva, viento, sismo, apoyos ni la tapa.")
    r.ecuacion("h_tolva = (D − d₀)/(2·tan α);   V_tolva = π·h/12·(D² + D·d₀ + d₀²)")
    r.ecuacion("z₀ = R/(K·μ), R = D/4;   p_h = ρ·g·R/μ·(1 − e^(−z/z₀));   p_v = p_h/K;   p_w = μ·p_h   (Janssen)")
    r.ecuacion("n = R·(ρ·g·z − p_v)   (peso soportado por fricción por metro de perímetro)")
    r.ecuacion("t = p_h,diseño·(D/2)/(σ_adm·E) + c")
    r.ecuacion("W = 0.58·ρ·√g·(d₀ − 1.4·d)^2.5   (Beverloo)")
    return r


CALCULADORA = Calculadora(
    id="silo",
    nombre="Silo metálico (predimensionamiento)",
    disciplina="Manejo de sólidos a granel",
    descripcion="PREDIMENSIONAMIENTO: geometría, presiones de llenado de Janssen, espesor por presión "
                "circunferencial y descarga por gravedad. No apto para diseño estructural.",
    estado_validacion=VALIDADA_CONDICIONES,
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("Calculo de un silo metalico.py",),
    referencias=("Teoría de Janssen (1895) para presiones en silos; misma forma que las presiones de llenado de "
                 "EN 1991-4 para silos esbeltos: p_hf = γ·K·z₀·(1 − e^(−z/z₀)), z₀ = A/(K·μ·U).",
                 "EN 1991-4 (acciones en silos) y EN 1993-4-1 (silos de acero): referencias para factores y pandeo.",
                 "Beverloo et al. (1961) para la descarga; no aplicable a polvos finos (Nedderman, 1992)."),
    limitaciones=("Solo predimensionamiento (decisión del usuario): NO apto para diseño estructural.",
                  "Sin pandeo, sin presiones de descarga normativas, sin tolva, viento ni sismo.",
                  "K y μ: datos del material (EN 1991-4, anexo E, o ensayos)."),
    palabras_clave=("silo", "janssen", "almacenamiento", "espesor", "lámina"),
)
