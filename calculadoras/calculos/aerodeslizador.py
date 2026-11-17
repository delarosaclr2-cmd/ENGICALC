"""Aerodeslizador (deslizador de polvo por fluidización).

Originales: «Calculo de Deslizador vs1.py» y «vs2.py» (menú).
Correcciones:
- La pérdida de presión no era la ecuación de Ergun ((1−ε) sin cuadrado, ε³
  multiplicando, d y v sin cuadrado, sin altura de lecho, /10 000 sin origen).
  Ahora se usa Ergun completa y la condición de lecho fluidizado ΔP = ρb·g·H.
- El caudal de aire era «sección del colchón × velocidad del material», que no
  representa el aire de fluidización. Ahora: caudal específico × área de tela.
- Tamaño de partícula en µm (el original decía mm con valores de 8–10 nm).
- La inclinación no interviene en ninguna fórmula disponible: se advierte.
- Velocidades por tipo de descarga: tabla original sin fuente.
"""
from __future__ import annotations

import math

from ..nucleo import constantes as K
from ..nucleo.materiales import materiales_de, resolver_densidad
from ..nucleo.modelo import DATO, ORIGINAL, VERIFICADA, Calculadora, Campo, Resultado, requerir

VELOCIDADES = {"Descarga materiales livianos": 5.0, "Descarga materiales secos": 3.0, "Descarga combinada": 2.0}

CAMPOS = [
    Campo("material", "Material", tipo="opcion", opciones=materiales_de("aerodeslizador"), defecto="Cemento",
          grupo="Material"),
    Campo("densidad", "Densidad aparente del material fluidizado", "kg/m³", defecto=0, minimo=0, grupo="Material",
          ayuda="0 = tabla original del deslizador (sin fuente)."),
    Campo("descarga", "Tipo de descarga", tipo="opcion", opciones=tuple(VELOCIDADES),
          defecto="Descarga materiales secos", grupo="Transporte"),
    Campo("velocidad", "Velocidad del material", "m/s", defecto=0, minimo=0, maximo=10, grupo="Transporte",
          ayuda="0 = tabla original por tipo de descarga (sin fuente)."),
    Campo("ancho", "Ancho del canal", "mm", minimo=0, min_incluido=False, grupo="Transporte",
          ayuda="El original indicaba 300–1000 mm."),
    Campo("altura_lecho", "Altura del lecho de material en movimiento", "mm", minimo=0, min_incluido=False,
          grupo="Transporte", ayuda="El original lo llamaba «altura del colchón (2–5 mm)»; confirme su significado."),
    Campo("inclinacion", "Inclinación", "°", defecto=0, minimo=0, maximo=30, grupo="Transporte",
          ayuda="No interviene en el cálculo."),
    Campo("longitud", "Longitud del aerodeslizador", "m", defecto=0, minimo=0, grupo="Aire de fluidización",
          ayuda="0 = no calcular el aire."),
    Campo("aire_especifico", "Caudal específico de aire", "m³/(min·m²)", defecto=0, minimo=0,
          grupo="Aire de fluidización", ayuda="Dato del fabricante de la tela porosa. 0 = no calcular."),
    Campo("porosidad", "Porosidad del lecho ε", "", minimo=0, maximo=1, min_incluido=False, max_incluido=False,
          grupo="Lecho", ayuda="El original indicaba 0.45–0.55."),
    Campo("particula", "Tamaño medio de partícula", "µm", minimo=0, min_incluido=False, grupo="Lecho"),
    Campo("viscosidad", "Viscosidad del aire", "Pa·s", defecto=1.8e-5, minimo=0, min_incluido=False, grupo="Lecho"),
    Campo("densidad_aire", "Densidad del aire", "kg/m³", defecto=1.2, minimo=0, min_incluido=False, grupo="Lecho"),
]


def ergun_por_metro(u: float, eps: float, d: float, mu: float, rho_g: float) -> float:
    """Ecuación de Ergun: ΔP/H [Pa/m] para velocidad superficial u [m/s]."""
    a = 150.0 * mu * (1 - eps) ** 2 / (eps ** 3 * d ** 2)
    b = 1.75 * rho_g * (1 - eps) / (eps ** 3 * d)
    return a * u + b * u ** 2


def velocidad_minima_fluidizacion(eps: float, d: float, mu: float, rho_g: float, rho_b: float) -> float:
    """u_mf de Ergun(u)·H = ρb·g·H (peso aparente del lecho por unidad de área)."""
    a = 150.0 * mu * (1 - eps) ** 2 / (eps ** 3 * d ** 2)
    b = 1.75 * rho_g * (1 - eps) / (eps ** 3 * d)
    c = -rho_b * K.G
    return (-a + math.sqrt(a * a - 4 * b * c)) / (2 * b)


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rho_b = resolver_densidad("aerodeslizador", d["material"], d["densidad"], r)
    if d["velocidad"] > 0:
        v, nivel_v = d["velocidad"], DATO
    else:
        v, nivel_v = VELOCIDADES[d["descarga"]], ORIGINAL
        r.advertir("Velocidad del material tomada de la tabla original (sin fuente).")
    b = d["ancho"] / 1000.0
    h = d["altura_lecho"] / 1000.0
    eps, dp, mu, rho_g = d["porosidad"], d["particula"] * 1e-6, d["viscosidad"], d["densidad_aire"]

    cap = v * b * h * rho_b * 3.6  # t/h
    dp_fluid = rho_b * K.G * h
    u_mf = velocidad_minima_fluidizacion(eps, dp, mu, rho_g, rho_b)

    r.agregar("velocidad", "Velocidad del material usada", v, "m/s", 2, nivel_v)
    r.agregar("capacidad_th", "Capacidad de transporte", cap, "t/h", 2,
              ORIGINAL if nivel_v == ORIGINAL else VERIFICADA)
    r.agregar("dp_lecho_fluidizado", "ΔP del lecho fluidizado (peso por área)", dp_fluid, "Pa", 1)
    r.agregar("dp_lecho_fluidizado_mm", "ΔP del lecho fluidizado", dp_fluid / K.PA_POR_MMH2O, "mm H₂O", 2, DATO)
    r.agregar("u_mf", "Velocidad mínima de fluidización (Ergun)", u_mf * 1000, "mm/s", 3)

    if d["longitud"] > 0 and d["aire_especifico"] > 0:
        area = b * d["longitud"]
        q = d["aire_especifico"] * area  # m³/min
        u = d["aire_especifico"] / 60.0
        dp_ergun = ergun_por_metro(u, eps, dp, mu, rho_g) * h
        fluidiza = u >= u_mf
        r.agregar("area_tela", "Área de tela porosa", area, "m²", 2)
        r.agregar("caudal_aire", "Caudal de aire de fluidización", q, "m³/min", 3)
        r.agregar("caudal_aire_h", "Caudal de aire de fluidización", q * 60, "m³/h", 1, DATO)
        r.agregar("u_superficial", "Velocidad superficial del aire", u * 1000, "mm/s", 3)
        r.agregar("dp_ergun", "ΔP de Ergun a esa velocidad (lecho fijo)", dp_ergun, "Pa", 1)
        r.agregar("fluidiza", "¿El lecho se fluidiza? (u ≥ u_mf)", fluidiza, nivel=VERIFICADA)
        r.agregar("dp_lecho", "ΔP a través del lecho", min(dp_ergun, dp_fluid), "Pa", 1)
        if not fluidiza:
            r.advertir("La velocidad superficial es menor que la de mínima fluidización: el material no fluidiza.")
        r.nota("La pérdida de la tela porosa no está incluida (dato del fabricante).")
    else:
        r.nota("Aire de fluidización no calculado: capture la longitud y el caudal específico de la tela.")

    if d["inclinacion"] > 0:
        r.advertir("La inclinación no interviene en este cálculo: la relación capacidad–pendiente es empírica "
                   "y no estaba documentada en el original.")
    r.ecuacion("Q_m = v·b·h·ρb·3.6 [t/h]")
    r.ecuacion("ΔP/H = 150·μ·(1−ε)²·u/(ε³·d²) + 1.75·ρg·(1−ε)·u²/(ε³·d)   (Ergun)")
    r.ecuacion("ΔP_fluidizado = ρb·g·H;   u_mf: Ergun(u_mf)·H = ρb·g·H")
    r.ecuacion("Q_aire = q_específico·b·L")
    return r


CALCULADORA = Calculadora(
    id="aerodeslizador",
    nombre="Aerodeslizador (deslizador de polvo)",
    disciplina="Manejo de sólidos a granel",
    descripcion="Capacidad, aire de fluidización y pérdidas de presión (Ergun y lecho fluidizado).",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("Calculo de Deslizador vs1.py", "Calculo de Deslizador vs2.py"),
    referencias=("Ecuación de Ergun y criterio de mínima fluidización (Kunii y Levenspiel, Fluidization Engineering).",),
    limitaciones=("Capacidad depende de la velocidad del material (tabla original sin fuente).",
                  "Sin pérdida de la tela porosa ni efecto de la pendiente."),
    palabras_clave=("aerodeslizador", "deslizador", "airslide", "fluidización", "cemento"),
)
