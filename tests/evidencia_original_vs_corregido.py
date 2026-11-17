"""Evidencia numérica: fórmula ORIGINAL vs versión CORREGIDA vs cálculo INDEPENDIENTE.

Uso:  python tests/evidencia_original_vs_corregido.py  > docs/EVIDENCIA_ORIGINAL_VS_CORREGIDO.txt

- ORIGINAL: expresión transcrita literalmente del archivo original (ver Fase 1).
- CORREGIDO: resultado de la calculadora nueva (motor de cálculo de esta versión).
- INDEPENDIENTE: cálculo escrito aparte, a mano, con la ecuación de referencia.

Las mismas comprobaciones existen como pruebas automáticas en tests/test_calculadoras.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from calculadoras.calculos import POR_ID  # noqa: E402
from calculadoras.calculos.aerodeslizador import ergun_por_metro  # noqa: E402
from calculadoras.nucleo import psicrometria as ps  # noqa: E402
from tests.casos import CASOS  # noqa: E402

FILAS: list[tuple] = []


def fila(calc, caso, magnitud, original, corregido, independiente, unidad):
    FILAS.append((calc, caso, magnitud, original, corregido, independiente, unidad))


def caso(cid, **cambios):
    datos = dict(CASOS[cid])
    datos.update(cambios)
    return POR_ID[cid].calcular(datos)


# 1. Torre de enfriamiento (rev0 divide entre 1000)
r = caso("torre", flujo_agua=10, t_entrada=35, t_salida=29)
fila("Torre", "10 kg/s, ΔT = 6 °C", "Carga térmica", 10 * 4.18 * 6 / 1000, r["carga_kw"], 10 * 4.186 * 6, "kW")

# 2. Soplador (ΔP en Pa dividido entre 102)
r = caso("soplador", caudal=1000, presion=5000, eficiencia=0.8, altitud=0)
q = 1000 / 3600
fila("Soplador", "1000 m³/h, 5000 Pa, η 0.8", "Potencia (incompresible)", 5000 * q / (102 * 0.8),
     r["potencia_incompresible_kw"], 5000 * q / 0.8 / 1000, "kW")
p1 = 101325.0
p2 = p1 + 5000
indep_ad = 1.4 / 0.4 * p1 * q * ((p2 / p1) ** (0.4 / 1.4) - 1) / 0.8 / 1000
fila("Soplador", "mismo caso", "Potencia (adiabática)", float("nan"), r["potencia_adiabatica_kw"], indep_ad, "kW")

# 3. Colector de polvo (mismo error de unidades; almacenamiento = aire/10)
r = caso("colector", caudal=10000, dp_filtro=150, dp_ducto=30, dp_ciclon=20, eficiencia=80)
q = 10000 / 3600
fila("Colector", "10 000 m³/h, 200 mm H₂O, η 80 %", "Potencia", 200 * 9.80665 * q / (102 * 0.8),
     r["potencia_kw"], 200 * 9.80665 * q / 0.8 / 1000, "kW")
fila("Colector", "10 g/m³, captura 99 %, 1100 kg/m³, 12 h", "Volumen de polvo en 12 h", 10000 / 10 * 12,
     r["volumen_tolva"], 10000 * 0.010 * 0.99 * 12 / 1100, "m³")

# 4. Ductos (control: el original era correcto)
r = caso("ductos", caudal=10000, velocidad=20, densidad=1.2, longitud=50, friccion=0.02, k_accesorios=0,
         eficiencia=0.7, rugosidad=0)
q = 10000 / 3600
diam = math.sqrt(4 * q / (math.pi * 20))
dp = 0.02 * 50 / diam * 1.2 * 20 ** 2 / 2
fila("Ductos", "10 000 m³/h, 20 m/s, f 0.02, 50 m", "ΔP por fricción", dp / 9.795, r["dp_total_mmh2o"],
     dp / 9.80665, "mm H₂O")

# 5. Bomba de vacío (ecuación de compresión mal planteada)
for presion in (60, 10, 1):
    r = caso("vacio", caudal=100, unidad_caudal="CFM (ft³/min)", presion_succion=presion, presion_descarga=0,
             altitud=0, k=1.4)
    qs = 100 * 0.000471947443
    m = 0.4 / 1.4
    original = 1.4 / 0.4 * 101.3 * qs * (1 - (presion / 101.3) ** m)
    indep = 1.4 / 0.4 * presion * qs * ((101.325 / presion) ** m - 1)
    fila("Bomba de vacío", f"100 CFM a {presion} kPa abs → atmósfera", "Potencia teórica", original,
         r["potencia_teorica_kw"], indep, "kW")

# 6. Transportador neumático (la relación de carga no se usaba)
r = caso("neumatico")
d = CASOS["neumatico"]
fila("Neumático", "1500 m³/h, μ = 4", "Capacidad de sólidos", float("nan"), r["capacidad_t_h"],
     r["masa_aire_kg_h"] * d["relacion"] / 1000, "t/h")

# 7. Banda transportadora (ancho × ocupación tomado como área)
r = caso("banda", ancho=1000, velocidad=1.0, densidad=1600, material="Arena", inclinacion=0)
fila("Banda", "B 1000 mm, 1 m/s, 1600 kg/m³", "Capacidad", 1.0 * 0.6 * 1.0 * 3600 * 1600 / 1000,
     r["capacidad_th"], r["area"] * 1.0 * 3600 * 1600 / 1000, "t/h")

# 8. Elevador (cangilones por metro truncados)
r = caso("elevador", paso_tabla="L8 — paso 350 mm")
fila("Elevador", "paso 350 mm", "Cangilones por metro", 2, r["cangilones_m"], 1000 / 350, "1/m")

# 9. Tolva (área media de extremos; /3.66)
r = caso("tolva", masa=2880, densidad=1440, area_superior=4, area_inferior=0.1)
a1, a2, v = 4.0, 0.1, 2.0
fila("Tolva", "V = 2 m³, A1 = 4 m², A2 = 0.1 m²", "Altura", v / ((a1 + a2) / 2), r["altura"],
     3 * v / (a1 + a2 + math.sqrt(a1 * a2)), "m")
r = caso("tolva", masa=2880, densidad=1440, area_superior=4, area_inferior=0.1, particula=2)
d0 = math.sqrt(4 * a2 / math.pi)
beverloo = 0.58 * 1440 * math.sqrt(9.80665) * (d0 - 1.4 * 0.002) ** 2.5 * 60
fila("Tolva", "mismo caso, sólido grueso d = 2 mm", "Flujo de descarga", 0.5 * a2 * math.sqrt(9.81 * v / ((a1 + a2) / 2)) * 1440 / 3.66,
     r["flujo_kg_min"], beverloo, "kg/min")

# 10. Silo (espesor = factor·D·10)
r = caso("silo")
d_silo = CASOS["silo"]
t_indep = (r["ph"] * 1000 * d_silo["factor_descarga"] * (d_silo["diametro"] / 2)
           / (d_silo["esfuerzo_admisible"] * 1e6 * d_silo["eficiencia_junta"]) * 1000 + d_silo["corrosion"])
fila("Silo", "D 4 m, cemento, 100 t, σ 150 MPa", "Espesor requerido (tensión circunf.)", max(2, 1 * 4 * 10),
     r["espesor_requerido"], t_indep, "mm")
fila("Silo", "mismo caso", "Presión lateral máx. (Janssen)", float("nan"), r["ph_max"],
     1300 * 9.80665 * 4 / (4 * 0.4) / 1000, "kPa")

# 11. Aerodeslizador (no era la ecuación de Ergun)
eps, mu, u, dpart, rho = 0.5, 1.8e-5, 0.02, 1e-5, 1.2
erg = (150 * mu * (1 - eps) ** 2 * u / (eps ** 3 * dpart ** 2) + 1.75 * rho * (1 - eps) * u ** 2 / (eps ** 3 * dpart))
orig = (150 * (1 - eps) * (2 * eps ** 3) * (mu * u) / dpart) + (1.75 * (1 - eps) / eps ** 3) * (rho * u / (dpart * 10000))
fila("Aerodeslizador", "ε 0.5, u 0.02 m/s, d 10 µm, lecho 0.05 m", "ΔP de Ergun", orig, ergun_por_metro(u, eps, dpart, mu, rho) * 0.05,
     erg * 0.05, "Pa")

# 12. Bomba centrífuga: reproduce prueba.pdf y agrega eficiencia
r = caso("bomba", friccion=0.02, limpiadores_hd=14, elevacion=0, presion_succion=0, altitud=0)
fila("Bomba centrífuga", "prueba.pdf (1234 gpm)", "Altura total", 562.85, r["altura_total"], 562.85, "ft")
fila("Bomba centrífuga", "prueba.pdf, η 75 %", "Potencia al freno", 175.39, r["potencia_freno"],
     1234 * r["altura_total"] / 3960 / 0.75, "HP")

# 13. Viga
r = caso("viga", posicion=0.5, carga_puntual=1000, longitud=2)
fila("Viga", "voladizo 2 m, 1000 kg a 0.5 m del empotre", "Momento máximo", 1000 * 9.81 * 1.5 / 1000,
     r["momento_max"], 1000 * 9.80665 * 0.5 / 1000, "kN·m")
r = caso("viga", tipo="Simplemente apoyada (apoyos en x = 0 y x = L)", posicion=1.0)
inercia = 0.1 * 0.2 ** 3 / 12
e_acero = r["modulo_e"] * 1e9
f = 1000 * 9.81
orig_delta = (f * 1.0 * 1.0 ** 2) / (3 * e_acero * inercia * 2) * (2 - 0.5)
fila("Viga", "apoyada 2 m, 1000 kg al centro", "Deflexión máxima", orig_delta * 1000, r["deflexion_max"],
     1000 * 9.80665 * 2 ** 3 / (48 * e_acero * inercia) * 1000, "mm")
r = caso("viga", seccion="Circular maciza", b=0, h=0, d=100, posicion=2)
ic = math.pi * 0.1 ** 4 / 64
mom = 1000 * 9.80665 * 2
fila("Viga", "voladizo, circular d 100 mm", "Esfuerzo de flexión", mom * 0.1 / ic / 1e6, r["esfuerzo_flexion"],
     mom * 0.05 / ic / 1e6, "MPa")

# 14. Secador rev0–2: bulbo húmedo (Stull truncada) vs psicrometría ASHRAE
p = 101325.0
w = ps.humedad_por_hr(35, 80, p)
stull = (35 * math.atan(0.151977 * (80 + 8.313659) ** 0.5) + math.atan(35 + 80) - math.atan(80 - 1.676331)
         + 0.00391838 * 80 ** 1.5 * math.atan(0.023101 * 80) - 4.686035)
fila("Secador", "35 °C, 80 % HR, nivel del mar", "Bulbo húmedo", math.atan(0.151977 * math.sqrt(88.313659)) * 35 - 4.27,
     ps.bulbo_humedo(35, w, p), stull, "°C")
r = caso("secador")
fila("Secador", "caso de prueba (3763.6 kg/h)", "Balance de agua: W = F·xi − agua final", float("nan"),
     r["agua_evaporada"], 3763.6 * 0.12 - 3763.6 * 0.88 * 0.03 / 0.97, "kg/h")


def imprimir() -> None:
    print("EVIDENCIA NUMÉRICA — ORIGINAL vs CORREGIDO vs INDEPENDIENTE")
    print("(NaN = el original no calculaba esa magnitud o no hay fórmula independiente cerrada)\n")
    encabezado = f"{'Calculadora':<17}{'Caso':<44}{'Magnitud':<40}{'Original':>12}{'Corregido':>12}{'Independiente':>14}  Unidad   Dif. corregido/indep."
    print(encabezado)
    print("-" * len(encabezado))
    for calc, caso_, mag, o, c, i, u in FILAS:
        dif = "—" if (i != i or i == 0) else f"{(c - i) / i * 100:+.3f} %"
        def fmt(x):
            return "—" if x != x else f"{x:12.4g}"
        print(f"{calc:<17}{caso_:<44}{mag:<40}{fmt(o):>12}{fmt(c):>12}{fmt(i):>14}  {u:<8} {dif}")


if __name__ == "__main__":
    imprimir()
