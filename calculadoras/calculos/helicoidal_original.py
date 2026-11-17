"""MÉTODO HEREDADO del transportador helicoidal — conservado solo para trazabilidad.

Desde la versión 2.1.0 la calculadora «helicoidal» usa el método KWS/CEMA validado
(ver calculos/helicoidal.py). Este módulo NO está registrado en el menú; se conserva
para que el resultado de la versión 2.0.x pueda reproducirse y compararse.

Texto original del módulo v2.0.x:

Transportador helicoidal (método original con factores tipo CEMA).

Original: «Calculo del transportador helicoidal.py».
El método se conserva (no se dispone de la fuente «Tabla de HP.png») pero se
corrige y se hace explícito:
- Entradas en SI (t/h, m, kg/m³); la fórmula empírica se evalúa internamente
  en unidades inglesas, como en el original.
- Los márgenes de 1.25 sobre la capacidad y sobre la potencia, y el factor de
  material 0.4 fijo, ahora son datos visibles con los valores originales.
- Inconsistencia corregida: el factor F (capacidad por rpm) se elegía por la
  capacidad, independiente del diámetro elegido para el factor D. Ahora el
  usuario puede capturar F del tornillo seleccionado; si usa la tabla original,
  se advierte la posible incongruencia.
- El ángulo se pedía y no se usaba: el método no considera inclinación y se advierte.
- Material desconocido ya no toma 1000 lb/ft³ (≈ 16 000 kg/m³) en silencio.
"""
from __future__ import annotations

from ..nucleo import constantes as K
from ..nucleo.materiales import materiales_de, resolver_densidad
from ..nucleo.modelo import DATO, EMPIRICA, ORIGINAL, Calculadora, Campo, ErrorEntrada, Resultado, requerir

# Tabla original de factor F [ft³/h por rpm] por coeficiente de carga y capacidad máxima [ft³/h]
TABLA_F = {
    40: [(368, 2.23), (1270, 8.2), (2820, 19.40), (4370, 31.20), (6060, 46.70), (8120, 67.60), (10300, 93.70)],
    30: [(180, 1.49), (545, 5.45), (1160, 12.9), (1770, 20.8), (2500, 31.20), (3380, 45.00), (4370, 62.50),
         (7100, 109.00)],
    15: [(45, 0.75), (325, 6.46), (520, 10.4), (700, 15.6), (1010, 22.5), (1250, 31.2), (2180, 54.6)],
}
FACTOR_D = {"3 plg": 15, "4 plg": 21, "6 plg": 33, "9 plg": 54, "10 plg": 66, "12 plg": 98, "14 plg": 135,
            "16 plg": 186, "18 plg": 240, "20 plg": 285, "24 plg": 390}
CARGAS = {"15 %": 15, "30 %": 30, "40 %": 40}

CAMPOS = [
    Campo("capacidad", "Capacidad requerida", "t/h", minimo=0, min_incluido=False, grupo="Capacidad"),
    Campo("factor_capacidad", "Factor de diseño sobre la capacidad", "", defecto=1.25, minimo=1, maximo=3,
          grupo="Capacidad", ayuda="1.25 era el margen fijo del original."),
    Campo("material", "Material", tipo="opcion", opciones=materiales_de("helicoidal"), defecto="Arena",
          grupo="Capacidad"),
    Campo("densidad", "Densidad aparente", "kg/m³", defecto=0, minimo=0, grupo="Capacidad",
          ayuda="0 = usar la tabla original del helicoidal (sin fuente)."),
    Campo("carga", "Coeficiente de carga de la artesa", tipo="opcion", opciones=tuple(CARGAS), defecto="30 %",
          grupo="Tornillo", ayuda="Verificar con la fuente si corresponde 40 % o 45 %."),
    Campo("diametro", "Diámetro del tornillo (factor D)", tipo="opcion", opciones=tuple(FACTOR_D),
          defecto="9 plg", grupo="Tornillo"),
    Campo("factor_f", "Capacidad por rpm del tornillo elegido (F)", "ft³/(h·rpm)", defecto=0, minimo=0,
          grupo="Tornillo", ayuda="0 = tabla original por rangos de capacidad (puede no coincidir con el diámetro)."),
    Campo("longitud", "Longitud del transportador", "m", minimo=0, min_incluido=False, grupo="Potencia"),
    Campo("factor_material", "Factor de material Fm", "", defecto=0.4, minimo=0, min_incluido=False, maximo=5,
          grupo="Potencia", ayuda="0.4 era fijo en el original para todos los materiales."),
    Campo("factor_sobrecarga", "Factor de sobrecarga de potencia Fo", "", defecto=1.25, minimo=1, maximo=3,
          grupo="Potencia", ayuda="1.25 era fijo en el original."),
    Campo("eficiencia", "Eficiencia del accionamiento", "%", minimo=0, maximo=100, min_incluido=False,
          grupo="Potencia"),
    Campo("angulo", "Ángulo de inclinación", "°", defecto=0, minimo=0, maximo=90, grupo="Potencia",
          ayuda="El método no considera inclinación."),
]


def factor_f_original(carga: int, capacidad_pie3h: float) -> tuple[float, float]:
    """Devuelve (F, capacidad máxima de la fila) de la tabla original."""
    for limite, f in TABLA_F[carga]:
        if capacidad_pie3h <= limite:
            return f, limite
    raise ErrorEntrada(f"Capacidad de {capacidad_pie3h:.0f} ft³/h fuera de la tabla original para {carga} % de carga.")


def calcular(d: dict) -> Resultado:
    r = Resultado()
    rho = resolver_densidad("helicoidal", d["material"], d["densidad"], r)
    rho_lb = rho / K.KGM3_POR_LBPIE3
    carga = CARGAS[d["carga"]]

    cap_lb_h = d["capacidad"] * d["factor_capacidad"] * 1000.0 / K.KG_POR_LIBRA
    cap_pie3_h = cap_lb_h / rho_lb

    if d["factor_f"] > 0:
        f, nivel_f = d["factor_f"], DATO
        limite = None
    else:
        f, limite = factor_f_original(carga, cap_pie3_h)
        nivel_f = ORIGINAL
        r.advertir("Factor F tomado de la tabla original por rangos de capacidad: implica un diámetro de tornillo "
                   "que puede no coincidir con el diámetro elegido para el factor D. Capture F del catálogo.")
    rpm = cap_pie3_h / f
    largo_pie = d["longitud"] / K.M_POR_PIE
    fd = FACTOR_D[d["diametro"]]
    hp = largo_pie * (fd * rpm + cap_lb_h * d["factor_material"]) / 1e6 * d["factor_sobrecarga"] / (d["eficiencia"] / 100)

    r.agregar("capacidad_diseno_lbh", "Capacidad de diseño", cap_lb_h, "lb/h", 0, DATO)
    r.agregar("capacidad_pie3h", "Capacidad volumétrica de diseño", cap_pie3_h, "ft³/h", 1)
    r.agregar("capacidad_m3h", "Capacidad volumétrica de diseño", cap_pie3_h * K.M3_POR_PIE3, "m³/h", 2, DATO)
    r.agregar("factor_f", "Capacidad por rpm usada (F)", f, "ft³/h·rpm", 2, nivel_f)
    r.agregar("rpm", "Velocidad de giro", rpm, "rpm", 1, EMPIRICA if nivel_f == DATO else ORIGINAL)
    if limite is not None:
        r.agregar("rpm_limite_tabla", "Velocidad máxima implícita en la fila de tabla", limite / f, "rpm", 0, ORIGINAL)
    r.agregar("factor_d", "Factor de diámetro Fd", fd, "", 0, ORIGINAL)
    r.agregar("potencia_hp", "Potencia demandada", hp, "HP", 2, ORIGINAL)
    r.agregar("potencia_kw", "Potencia demandada", K.hp_a_kw(hp), "kW", 2, ORIGINAL)

    if d["angulo"] > 0:
        r.advertir("El método no considera la inclinación: para transportadores inclinados la capacidad baja y la "
                   "potencia sube. Consulte la referencia del fabricante.")
    r.advertir("Método empírico heredado: estructura similar a CEMA 350 (potencia de fricción + material), pero "
               "sin factores Fb, Ff, Fp y con Fo constante. No validado: falta la fuente «Tabla de HP.png».")
    r.ecuacion("C = Q·f_cap·1000/0.45359 [lb/h];   C_v = C/ρ [ft³/h];   N = C_v/F [rpm]")
    r.ecuacion("HP = L[ft]·(Fd·N + C·Fm)/10⁶ · Fo/η")
    return r


CALCULADORA = Calculadora(
    id="helicoidal_original",
    nombre="Transportador helicoidal",
    disciplina="Manejo de sólidos a granel",
    descripcion="Velocidad de giro y potencia por el método empírico original (factores tipo CEMA).",
    campos=CAMPOS,
    funcion=calcular,
    archivos_originales=("Calculo del transportador helicoidal.py",),
    referencias=("Método original con estructura similar a CEMA 350 — fuente no disponible («Tabla de HP.png»).",),
    limitaciones=("Método empírico no validado.", "Sin inclinación.", "Tabla de 15 % con posible escalón omitido."),
    imagenes=(),
    palabras_clave=("helicoidal", "tornillo", "sinfín", "screw", "transportador"),
)
