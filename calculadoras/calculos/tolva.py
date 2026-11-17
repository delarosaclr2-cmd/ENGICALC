"""Tolva de dosificación (transición de boca cuadrada a descarga circular).

Original: «calculo de tolva de dosificación.py».
Correcciones:
- Altura: el original usaba el área media de los extremos (23 % menos altura
  que un tronco de pirámide en el caso de prueba). Ahora V = h/3·(A1 + A2 + √(A1·A2)).
- Flujo de descarga: el original usaba k·A·√(g·h)·ρ/3.66 (modelo de líquido y
  un /3.66 en lugar de ×60). La descarga de sólidos granulares casi no depende de
  la altura del lecho; ahora se usa la correlación de Beverloo.
- Se informan los ángulos de pared en la cara plana y en la arista (valle), que
  es el más tendido y el que controla el deslizamiento.
"""
from __future__ import annotations

import math

from ..nucleo import solidos
from ..nucleo.materiales import ANGULOS_REPOSO_ORIGINALES, materiales_de, resolver_densidad
from ..nucleo.modelo import DATO, EMPIRICA, ORIGINAL, VERIFICADA, Calculadora, Campo, Resultado, requerir

CAMPOS = [
    Campo("masa", "Masa de material a almacenar", "kg", minimo=0, min_incluido=False, grupo="Material"),
    Campo("material", "Material", tipo="opcion", opciones=materiales_de("tolva"), defecto="Cemento",
          grupo="Material"),
    Campo("densidad", "Densidad aparente", "kg/m³", defecto=0, minimo=0, grupo="Material",
          ayuda="0 = tabla original de la tolva (sin fuente; varios valores son densidad real, no aparente)."),
    Campo("angulo_reposo", "Ángulo de reposo", "°", defecto=0, minimo=0, maximo=90, grupo="Material",
          ayuda="0 = tabla original. Solo se usa como comparación indicativa."),
    Campo("particula", "Tamaño medio de partícula", "mm", defecto=0, minimo=0, grupo="Material",
          ayuda="Para Beverloo. 0 = se desprecia el término k·d (polvo muy fino: la correlación sobreestima)."),
    Campo("area_superior", "Área de la boca superior cuadrada", "m²", minimo=0, min_incluido=False,
          grupo="Geometría"),
    Campo("area_inferior", "Área de la descarga circular", "m²", minimo=0, min_incluido=False, grupo="Geometría"),
]


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rho = resolver_densidad("tolva", d["material"], d["densidad"], r)
    a1, a2 = d["area_superior"], d["area_inferior"]
    lado = math.sqrt(a1)
    d0 = math.sqrt(4 * a2 / math.pi)
    requerir(d0 < lado, "La descarga circular debe caber dentro de la boca cuadrada (diámetro < lado).")

    volumen = d["masa"] / rho
    altura = 3 * volumen / (a1 + a2 + math.sqrt(a1 * a2))
    corrida_plana = lado / 2 - d0 / 2
    corrida_arista = lado * math.sqrt(2) / 2 - d0 / 2
    ang_plano = math.degrees(math.atan2(altura, corrida_plana))
    ang_arista = math.degrees(math.atan2(altura, corrida_arista))

    try:
        flujo = solidos.descarga_beverloo(rho, d0, d["particula"] / 1000.0)
    except ValueError as e:
        from ..nucleo.modelo import ErrorEntrada
        raise ErrorEntrada(str(e)) from e
    aviso_beverloo = solidos.advertencia_beverloo(d["particula"])

    r.agregar("volumen", "Volumen de material", volumen, "m³", 3)
    r.agregar("lado_superior", "Lado de la boca superior", lado, "m", 3, DATO)
    r.agregar("diametro_descarga", "Diámetro de la descarga", d0, "m", 3, DATO)
    r.agregar("altura", "Altura de la tolva (tronco de secciones semejantes)", altura, "m", 3)
    r.agregar("pared_plana", "Longitud de pared en la cara plana", math.hypot(altura, corrida_plana), "m", 3)
    r.agregar("angulo_plano", "Ángulo de la cara plana con la horizontal", ang_plano, "°", 1)
    r.agregar("angulo_arista", "Ángulo de la arista (valle) con la horizontal", ang_arista, "°", 1)
    r.agregar("flujo_kg_s", "Flujo de descarga (Beverloo)", flujo, "kg/s", 3, EMPIRICA)
    r.agregar("flujo_kg_min", "Flujo de descarga (Beverloo)", flujo * 60, "kg/min", 1, EMPIRICA)
    r.agregar("flujo_t_h", "Flujo de descarga (Beverloo)", flujo * 3.6, "t/h", 2, EMPIRICA)
    r.agregar("tiempo_vaciado", "Tiempo de vaciado a ese flujo", d["masa"] / flujo / 60, "min", 1, EMPIRICA)

    reposo = d["angulo_reposo"] if d["angulo_reposo"] > 0 else ANGULOS_REPOSO_ORIGINALES["tolva"].get(d["material"])
    if reposo:
        nivel = DATO if d["angulo_reposo"] > 0 else ORIGINAL
        r.agregar("angulo_reposo", "Ángulo de reposo de referencia", reposo, "°", 0, nivel)
        if ang_arista <= reposo:
            r.advertir(f"La arista de la tolva ({ang_arista:.1f}°) no es más inclinada que el ángulo de reposo "
                       f"({reposo:g}°): el material puede quedar retenido en los rincones.")
    if aviso_beverloo:
        r.advertir(aviso_beverloo)
    r.advertir("El ángulo de pared para flujo másico depende de la fricción con la pared (método de Jenike); "
               "no se verifica aquí.")
    r.nota("Beverloo es válida para sólidos gruesos no cohesivos. Con descarga controlada por un dosificador, "
           "el flujo lo define el dosificador.")
    r.ecuacion("V = m/ρ;   h = 3V/(A₁ + A₂ + √(A₁·A₂))")
    r.ecuacion("W = C·ρ·√g·(D₀ − k·d)^2.5,  C = 0.58,  k = 1.4   (Beverloo, 1961)")
    return r


CALCULADORA = Calculadora(
    id="tolva",
    nombre="Tolva de dosificación",
    disciplina="Manejo de sólidos a granel",
    descripcion="Volumen, altura, ángulos de pared y flujo de descarga (Beverloo) de una tolva de transición.",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("calculo de tolva de dosificación.py",),
    referencias=("Beverloo, Leniger y Van de Velde (1961), Chem. Eng. Sci. 15, 260: C ≈ 0.58, k ≈ 1.4.",
                 "Aplicabilidad: sólidos gruesos no cohesivos; los polvos finos descargan más lento "
                 "(Nedderman, Statics and Kinematics of Granular Materials, 1992)."),
    limitaciones=("Transición cuadrado–círculo aproximada como tronco de secciones semejantes.",
                  "Sin análisis de flujo másico (Jenike).",
                  "Flujo de Beverloo no aplicable a polvos finos (< ~0.4 mm)."),
    palabras_clave=("tolva", "dosificación", "descarga", "beverloo"),
)
