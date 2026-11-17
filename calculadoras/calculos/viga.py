"""Viga en voladizo o simplemente apoyada (Euler-Bernoulli, elástico lineal).

Originales: «Calculo de Cantiliver.py», «rev1.py» y «rev2.py».
Correcciones:
- Las dimensiones de la sección ahora son datos (antes siempre 0.1 × 0.2 m).
- Coordenada única: x = 0 en el empotramiento (voladizo) o en el apoyo izquierdo.
  El original medía la deflexión desde el empotramiento y el momento desde el
  extremo libre (momento 3 veces mayor con la carga a 0.5 m de un voladizo de 2 m).
- Deflexión de viga simplemente apoyada con las ecuaciones exactas (el original
  daba 1.5 × PL³/48EI con la carga al centro).
- σ = M·c/I con c de la sección (antes c = 0.1 m fijo).
- rev0: reacción de momento P·(L − a) con a = L daba 0; corregido.
- Se agrega carga distribuida uniforme (rev0 la ofrecía) y cortante máximo.

Versión 2.1: revisión de resistencia por AISC 360-22 (LRFD) y NTC-DCEA (CDMX) con pandeo lateral-torsional
por tramo no soportado (Cb del diagrama de momentos), pandeo local del patín y cortante del alma
(ver calculadoras/nucleo/acero.py). Validada contra AISC Design Examples v16.0.
"""
from __future__ import annotations

import math

from ..nucleo import acero
from ..nucleo import constantes as K
from ..nucleo.modelo import (DATO, EMPIRICA, ORIGINAL, VALIDADA_CONDICIONES, VERIFICADA, Calculadora, Campo,
                              ErrorEntrada, Resultado, requerir)

VOLADIZO = "Voladizo (empotrada en x = 0)"
SIMPLE = "Simplemente apoyada (apoyos en x = 0 y x = L)"
MODULOS_ORIGINALES_GPA = {"Acero": 210.0, "Aluminio": 70.0, "Madera": 10.0, "Bronce": 110.0, "Hierro": 190.0}
PERSONALIZADO = "Personalizado (capturar E)"
RECT, CIRC, TUBO, IVIGA, PERS = ("Rectangular maciza", "Circular maciza", "Tubo circular", "I simétrica",
                                 "Personalizada (I, c, A)")
NINGUNA, AISC, NTC, AMBAS = ("Ninguna (solo análisis elástico)", "AISC 360-22 (LRFD)", "NTC-DCEA (CDMX)",
                             "AISC 360-22 y NTC-DCEA")
EXTREMOS, CONTINUO, PUNTOS = ("Solo en apoyos (sin soportes intermedios)", "Continuo (losa o cubierta conectada)",
                              "En puntos equidistantes (capturar número de tramos)")
LAMINADO, SOLDADO = "Laminado (rolado)", "Soldado (placas)"

CAMPOS = [
    Campo("tipo", "Tipo de viga", tipo="opcion", opciones=(VOLADIZO, SIMPLE), defecto=VOLADIZO, grupo="Viga"),
    Campo("longitud", "Longitud L", "m", minimo=0, min_incluido=False, grupo="Viga"),
    Campo("carga_puntual", "Carga puntual P", "kg", defecto=0, minimo=0, grupo="Cargas",
          ayuda="Masa; se convierte a N con g = 9.80665 m/s²."),
    Campo("posicion", "Posición de la carga puntual (desde x = 0)", "m", defecto=0, minimo=0, grupo="Cargas",
          ayuda="Voladizo: distancia desde el empotramiento. Simple: desde el apoyo izquierdo."),
    Campo("carga_distribuida", "Carga distribuida uniforme w (en toda la longitud)", "kg/m", defecto=0, minimo=0,
          grupo="Cargas", ayuda="Incluya aquí el peso propio si desea considerarlo."),
    Campo("material", "Material (módulo E)", tipo="opcion", opciones=tuple(MODULOS_ORIGINALES_GPA) + (PERSONALIZADO,),
          defecto="Acero", grupo="Material"),
    Campo("modulo", "Módulo de elasticidad E", "GPa", defecto=0, minimo=0, grupo="Material",
          ayuda="Un valor capturado tiene prioridad sobre la lista. 0 = valor de la lista del original (nivel O)."),
    Campo("seccion", "Sección transversal", tipo="opcion", opciones=(RECT, CIRC, TUBO, IVIGA, PERS), defecto=RECT,
          grupo="Sección"),
    Campo("b", "Ancho b (rectangular o patín de la I)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("h", "Peralte h (rectangular o I)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("d", "Diámetro exterior d (circular o tubo)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("t", "Espesor de pared t (tubo)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("tf", "Espesor del patín tf (I)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("tw", "Espesor del alma tw (I)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("inercia", "Momento de inercia I (personalizada)", "cm⁴", defecto=0, minimo=0, grupo="Sección"),
    Campo("c", "Distancia a la fibra extrema c (personalizada)", "mm", defecto=0, minimo=0, grupo="Sección"),
    Campo("area", "Área A (personalizada)", "cm²", defecto=0, minimo=0, grupo="Sección"),
    Campo("fabricacion", "Fabricación del perfil I", tipo="opcion", opciones=(LAMINADO, SOLDADO), defecto=LAMINADO,
          grupo="Sección"),
    Campo("ix_manual", "Ix del manual (perfil I)", "cm⁴", defecto=0, minimo=0, grupo="Propiedades del manual (I)",
          ayuda="0 = calcular con las placas (sin filetes). Para perfiles laminados capture las del manual IMCA/AISC."),
    Campo("area_manual", "Área A del manual", "cm²", defecto=0, minimo=0, grupo="Propiedades del manual (I)"),
    Campo("zx_manual", "Zx del manual", "cm³", defecto=0, minimo=0, grupo="Propiedades del manual (I)"),
    Campo("sx_manual", "Sx del manual", "cm³", defecto=0, minimo=0, grupo="Propiedades del manual (I)"),
    Campo("iy_manual", "Iy del manual", "cm⁴", defecto=0, minimo=0, grupo="Propiedades del manual (I)"),
    Campo("j_manual", "J (constante de torsión) del manual", "cm⁴", defecto=0, minimo=0,
          grupo="Propiedades del manual (I)"),
    Campo("cw_manual", "Cw (constante de alabeo) del manual", "cm⁶", defecto=0, minimo=0,
          grupo="Propiedades del manual (I)"),
    Campo("norma", "Revisión de resistencia", tipo="opcion", opciones=(AMBAS, AISC, NTC, NINGUNA), defecto=AMBAS,
          grupo="Revisión por norma (acero)"),
    Campo("fy", "Esfuerzo de fluencia Fy", "MPa", defecto=0, minimo=0, grupo="Revisión por norma (acero)",
          ayuda="Ej.: ASTM A36 = 250 MPa; ASTM A992 / A572 Gr. 50 = 345 MPa. Obligatorio si se revisa por norma."),
    Campo("factor_carga", "Factor de carga para resistencia (LRFD)", "", defecto=0, minimo=0,
          grupo="Revisión por norma (acero)",
          ayuda="Multiplica las cargas capturadas (de servicio) para obtener Mu y Vu. Use el de la combinación "
                "aplicable de su norma de cargas; la deflexión se calcula con las cargas sin factorizar."),
    Campo("soporte", "Soporte lateral del patín comprimido", tipo="opcion", opciones=(EXTREMOS, CONTINUO, PUNTOS),
          defecto=EXTREMOS, grupo="Revisión por norma (acero)"),
    Campo("tramos", "Número de tramos entre soportes laterales", "", tipo="entero", defecto=2, minimo=2, maximo=20,
          grupo="Revisión por norma (acero)", ayuda="Solo con soportes en puntos equidistantes."),
    Campo("esfuerzo_admisible", "Esfuerzo admisible a flexión", "MPa", defecto=0, minimo=0, grupo="Revisión",
          ayuda="0 = no comparar."),
    Campo("limite_deflexion", "Límite de deflexión L/n (capturar n)", "", defecto=0, minimo=0, grupo="Revisión",
          ayuda="Ej. 360 para L/360. 0 = no comparar."),
]


def propiedades_seccion(d: dict) -> dict:
    """I [m⁴], c [m], A [m²] y factor de cortante máximo (τmax = k·V/A)."""
    s = d["seccion"]
    mm = 1e-3
    if s == RECT:
        b, h = d["b"] * mm, d["h"] * mm
        requerir(b > 0 and h > 0, "Capture b y h de la sección rectangular.")
        return {"I": b * h ** 3 / 12, "c": h / 2, "A": b * h, "k_tau": 1.5, "nivel_tau": VERIFICADA}
    if s == CIRC:
        dd = d["d"] * mm
        requerir(dd > 0, "Capture el diámetro de la sección circular.")
        return {"I": math.pi * dd ** 4 / 64, "c": dd / 2, "A": math.pi * dd ** 2 / 4, "k_tau": 4 / 3,
                "nivel_tau": VERIFICADA}
    if s == TUBO:
        dd, t = d["d"] * mm, d["t"] * mm
        requerir(dd > 0 and 0 < t < dd / 2, "Capture d y t del tubo (0 < t < d/2).")
        di = dd - 2 * t
        return {"I": math.pi * (dd ** 4 - di ** 4) / 64, "c": dd / 2, "A": math.pi * (dd ** 2 - di ** 2) / 4,
                "k_tau": 2.0, "nivel_tau": DATO}
    if s == IVIGA:
        b, h, tf, tw = d["b"] * mm, d["h"] * mm, d["tf"] * mm, d["tw"] * mm
        requerir(b > 0 and h > 0 and tf > 0 and tw > 0, "Capture b, h, tf y tw de la sección I.")
        requerir(2 * tf < h and tw < b, "Dimensiones de la I incongruentes (2·tf < h y tw < b).")
        inercia = (b * h ** 3 - (b - tw) * (h - 2 * tf) ** 3) / 12
        area = 2 * b * tf + (h - 2 * tf) * tw
        return {"I": inercia, "c": h / 2, "A": area, "k_tau": None, "alma": h * tw, "nivel_tau": DATO}
    inercia, c, area = d["inercia"] * 1e-8, d["c"] * mm, d["area"] * 1e-4
    requerir(inercia > 0 and c > 0 and area > 0, "Capture I, c y A de la sección personalizada.")
    return {"I": inercia, "c": c, "A": area, "k_tau": 1.0, "nivel_tau": DATO}


def respuesta(tipo: str, L: float, P: float, a: float, w: float, EI: float, x: float) -> tuple[float, float, float]:
    """Cortante V [N], momento M [N·m] y deflexión y [m] (positiva hacia abajo) en x.

    Convención: cargas hacia abajo positivas; momento positivo produce compresión arriba
    (en voladizo el momento es negativo: tensión arriba).
    """
    if tipo == VOLADIZO:
        v = (P if x < a else 0.0) + w * (L - x)
        m = -(P * (a - x) if x < a else 0.0) - w * (L - x) ** 2 / 2
        if x <= a:
            yp = P * x ** 2 * (3 * a - x) / (6 * EI)
        else:
            yp = P * a ** 2 * (3 * x - a) / (6 * EI)
        yw = w * x ** 2 * (6 * L ** 2 - 4 * L * x + x ** 2) / (24 * EI)
        return v, m, yp + yw
    b = L - a
    r1 = P * b / L + w * L / 2
    v = r1 - (P if x > a else 0.0) - w * x
    m = r1 * x - (P * (x - a) if x > a else 0.0) - w * x ** 2 / 2
    if P > 0:
        if x <= a:
            yp = P * b * x * (L ** 2 - b ** 2 - x ** 2) / (6 * L * EI)
        else:
            xr = L - x
            yp = P * a * xr * (L ** 2 - a ** 2 - xr ** 2) / (6 * L * EI)
    else:
        yp = 0.0
    yw = w * x * (L ** 3 - 2 * L * x ** 2 + x ** 3) / (24 * EI)
    return v, m, yp + yw


def modulo_elasticidad(d: dict) -> tuple[float, str, str]:
    """Módulo E [Pa], su nivel de confianza y una nota cuando el dato capturado sustituye a la lista.

    Regla común de todas las calculadoras: un valor capturado (> 0) tiene prioridad; 0 = tabla original.
    En la 2.0.0 un E capturado se ignoraba sin aviso si el material no era «Personalizado»
    (hallazgo de la prueba en vivo: E = 200 GPa capturado, se usó 210 GPa).
    """
    if d["modulo"] > 0:
        nota = ""
        if d["material"] != PERSONALIZADO:
            nota = (f"Se usó el E capturado ({d['modulo']:g} GPa) en lugar del valor de la lista para "
                    f"{d['material']} ({MODULOS_ORIGINALES_GPA[d['material']]:g} GPa).")
        return d["modulo"] * 1e9, DATO, nota
    requerir(d["material"] != PERSONALIZADO, "Capture el módulo de elasticidad E.")
    return MODULOS_ORIGINALES_GPA[d["material"]] * 1e9, ORIGINAL, ""


# --------------------------------------------------------------------------- revisión por norma
def propiedades_i_norma(d: dict) -> tuple[dict, bool]:
    """Propiedades del perfil I para la revisión (m). Las del manual capturadas sustituyen a las calculadas."""
    mm = 1e-3
    p = acero.propiedades_i(d["h"] * mm, d["b"] * mm, d["tf"] * mm, d["tw"] * mm)
    manual = False
    for clave, campo, factor in (("A", "area_manual", 1e-4), ("Ix", "ix_manual", 1e-8), ("Zx", "zx_manual", 1e-6),
                                 ("Sx", "sx_manual", 1e-6),
                                 ("Iy", "iy_manual", 1e-8), ("J", "j_manual", 1e-8), ("Cw", "cw_manual", 1e-12)):
        if d[campo] > 0:
            p[clave] = d[campo] * factor
            manual = True
    return acero.completar_i(p), manual


def tramos_no_soportados(d: dict) -> list[tuple[float, float]]:
    L = d["longitud"]
    if d["soporte"] == CONTINUO:
        return [(0.0, L)]
    n = d["tramos"] if d["soporte"] == PUNTOS else 1
    return [(L * i / n, L * (i + 1) / n) for i in range(n)]


def momentos_tramo(d: dict, P: float, w: float, EI: float, x0: float, x1: float) -> dict:
    """|M| máximo y en los cuartos del tramo (para Cb, AISC F1-1 / NTC 6.2.1)."""
    def m(x):
        return abs(respuesta(d["tipo"], d["longitud"], P, d["posicion"], w, EI, x)[1])
    xs = [x0 + (x1 - x0) * i / 200 for i in range(201)]
    if x0 < d["posicion"] < x1:
        xs += [d["posicion"], math.nextafter(d["posicion"], 0.0)]
    m_max = max(m(x) for x in xs)
    q = (x1 - x0) / 4
    return {"Mmax": m_max, "MA": m(x0 + q), "MB": m(x0 + 2 * q), "MC": m(x0 + 3 * q)}


def revision_norma(d: dict, r: Resultado, P: float, w: float, EI: float, vmax: float) -> None:
    usa_aisc, usa_ntc = d["norma"] in (AISC, AMBAS), d["norma"] in (NTC, AMBAS)
    requerir(d["fy"] > 0, "Capture Fy para la revisión por norma (o elija «Ninguna»).")
    requerir(d["factor_carga"] > 0, "Capture el factor de carga LRFD para obtener Mu y Vu (o elija «Ninguna»).")
    requerir(d["material"] in ("Acero", PERSONALIZADO) or d["modulo"] > 0,
             "La revisión AISC/NTC aplica solo a acero estructural: elija «Ninguna» para otros materiales.")
    fy = d["fy"] * 1e6
    fc = d["factor_carga"]
    seccion = d["seccion"]
    requerir(seccion != PERS, "La sección personalizada no tiene datos para la revisión por norma: use la I con "
                              "propiedades del manual, o elija «Ninguna».")
    voladizo = d["tipo"] == VOLADIZO
    tramos = tramos_no_soportados(d)
    lb_texto = "continuo (Lb = 0)" if d["soporte"] == CONTINUO else f"{tramos[0][1] - tramos[0][0]:.3f} m"
    r.agregar("lb", "Longitud sin soporte lateral Lb", 0.0 if d["soporte"] == CONTINUO else tramos[0][1] - tramos[0][0],
              "m", 3, DATO)
    r.agregar("vu", "Cortante último Vu = factor·V", fc * vmax / 1000, "kN", 3)
    r.ecuacion("Mu(x) = factor de carga · M(x);  Cb = 12.5·Mmax/(2.5·Mmax + 3·MA + 4·MB + 3·MC) por tramo "
               "(voladizo: Cb = 1.0)")

    props, manual = (propiedades_i_norma(d) if seccion == IVIGA else (None, False))
    if seccion == IVIGA:
        cl = acero.clasificar_i(props, fy)
        r.agregar("clase_patin", "Patín (AISC Tabla B4.1b)", f"{cl['patin']} (bf/2tf = {cl['lam_f']:.2f})", "", 0,
                  VERIFICADA)
        r.agregar("clase_alma", "Alma (AISC Tabla B4.1b)", f"{cl['alma']} (h/tw = {cl['lam_w']:.1f})", "", 0,
                  VERIFICADA)
        if not manual and d["fabricacion"] == LAMINADO:
            r.advertir("Perfil laminado con propiedades calculadas sin filetes: Zx, J y Cw quedan ligeramente "
                       "subestimados. Capture las propiedades del manual IMCA/AISC para la revisión definitiva.")

    def evaluar(funcion):
        """Recorre los tramos y devuelve el más desfavorable (Mu/φMn máximo)."""
        peor = None
        for x0, x1 in tramos:
            mt = momentos_tramo(d, P, w, EI, x0, x1)
            cb = 1.0 if voladizo else acero.cb_aisc(mt["Mmax"], mt["MA"], mt["MB"], mt["MC"])
            lb = 0.0 if d["soporte"] == CONTINUO else x1 - x0
            res = funcion(lb, cb)
            relacion = fc * mt["Mmax"] / res["resistencia"] if res["resistencia"] > 0 else math.inf
            if peor is None or relacion > peor["relacion"]:
                peor = dict(res, relacion=relacion, cb=cb, mu=fc * mt["Mmax"], x0=x0, x1=x1)
        return peor

    try:
        if usa_aisc:
            if seccion == IVIGA:
                def f_aisc(lb, cb):
                    out = acero.aisc_flexion_i(props, fy, lb, cb)
                    return dict(out, resistencia=out["phiMn"])
            elif seccion == RECT:
                b, h = d["b"] * 1e-3, d["h"] * 1e-3
                requerir(h >= b, "Para la revisión AISC F11 la barra rectangular debe flexionarse en su eje mayor (h ≥ b).")
                def f_aisc(lb, cb):
                    out = acero.aisc_flexion_rect(fy, b, h, lb, cb)
                    return dict(out, resistencia=out["phiMn"])
            elif seccion == CIRC:
                def f_aisc(lb, cb):
                    out = acero.aisc_flexion_redonda(fy, d["d"] * 1e-3)
                    return dict(out, resistencia=out["phiMn"])
            else:
                def f_aisc(lb, cb):
                    out = acero.aisc_flexion_tubo(fy, d["d"] * 1e-3, d["t"] * 1e-3)
                    return dict(out, resistencia=out["phiMn"])
            res = evaluar(f_aisc)
            r.agregar("aisc_cb", "AISC: Cb del tramo crítico", res["cb"], "", 2, VERIFICADA)
            if "Lp" in res:
                r.agregar("aisc_lp", "AISC: Lp", res["Lp"], "m", 3, VERIFICADA)
                r.agregar("aisc_lr", "AISC: Lr", res["Lr"], "m", 3, VERIFICADA)
            r.agregar("aisc_mp", "AISC: Mp = Fy·Zx", res["Mp"] / 1000, "kN·m", 2, VERIFICADA)
            r.agregar("aisc_mn", "AISC: Mn (tramo crítico)", res["Mn"] / 1000, "kN·m", 2, VERIFICADA)
            r.agregar("aisc_phimn", "AISC: φb·Mn (φb = 0.90)", res["phiMn"] / 1000, "kN·m", 2, VERIFICADA)
            r.agregar("aisc_mu", "AISC: Mu del tramo crítico", res["mu"] / 1000, "kN·m", 2)
            r.agregar("aisc_rel_m", "AISC: Mu/φb·Mn", res["relacion"], "", 3, VERIFICADA)
            r.agregar("aisc_controla", "AISC: estado límite que controla", res["controla"], "", 0, VERIFICADA)
            if res["relacion"] > 1:
                r.advertir(f"AISC 360-22: la flexión NO cumple (Mu/φMn = {res['relacion']:.2f} > 1).")
            if seccion == IVIGA:
                v = acero.aisc_cortante_i(props, fy, d["fabricacion"] == LAMINADO)
                r.agregar("aisc_phivn", f"AISC: φv·Vn (φv = {v['phi']:.2f}, Cv1 = {v['Cv1']:.3f})",
                          v["phiVn"] / 1000, "kN", 2, VERIFICADA)
                r.agregar("aisc_rel_v", "AISC: Vu/φv·Vn", fc * vmax / v["phiVn"], "", 3, VERIFICADA)
                if fc * vmax > v["phiVn"]:
                    r.advertir("AISC 360-22: el cortante NO cumple.")
            elif seccion == TUBO:
                lv = d["longitud"] if voladizo else d["longitud"] / 2
                v = acero.aisc_cortante_tubo(fy, d["d"] * 1e-3, d["t"] * 1e-3, lv)
                r.agregar("aisc_phivn", "AISC G5: φv·Vn", v["phiVn"] / 1000, "kN", 2, VERIFICADA)
                r.agregar("aisc_rel_v", "AISC: Vu/φv·Vn", fc * vmax / v["phiVn"], "", 3, VERIFICADA)
                r.nota("Cortante del tubo con Lv = L (voladizo) o L/2 (simplemente apoyada).")
            else:
                r.nota("AISC no define el cortante de barras macizas en el capítulo G: se informa solo τ elástico.")
            r.ecuacion("AISC F2: Mn = Mp si Lb ≤ Lp; Cb[Mp − (Mp − 0.7FySx)(Lb − Lp)/(Lr − Lp)] ≤ Mp si Lp < Lb ≤ Lr; "
                       "Fcr·Sx ≤ Mp si Lb > Lr;  Lp = 1.76·ry·√(E/Fy)")
            r.ecuacion("AISC G2.1: Vn = 0.6·Fy·Aw·Cv1, Aw = d·tw")

        if usa_ntc:
            if seccion != IVIGA:
                r.nota("NTC-DCEA: la revisión implementada cubre perfiles I compactos; para esta sección use AISC.")
            else:
                cl = acero.clasificar_i(props, fy, acero.E_NTC)
                if cl["patin"] != "compacto" or cl["alma"] != "compacta":
                    r.advertir("NTC-DCEA: sección no compacta (tipo 3 o 4); la revisión 6.4 no está implementada. "
                               "Se informa solo AISC para esta sección.")
                else:
                    def f_ntc(lb, cb):
                        out = acero.ntc_flexion_i(props, fy, lb, cb)
                        return dict(out, resistencia=out["MR"])
                    res = evaluar(f_ntc)
                    if res["Me"] is not None:
                        r.agregar("ntc_me", "NTC: Me (momento crítico elástico, ec. 6.3.4)", res["Me"] / 1000, "kN·m",
                                  2, EMPIRICA)
                    r.agregar("ntc_mr", "NTC: MR = FR·Mn (FR = 0.9)", res["MR"] / 1000, "kN·m", 2, EMPIRICA)
                    r.agregar("ntc_rel_m", "NTC: Mu/MR", res["relacion"], "", 3, EMPIRICA)
                    r.agregar("ntc_controla", "NTC: estado límite que controla", res["controla"], "", 0, EMPIRICA)
                    if res["relacion"] > 1:
                        r.advertir(f"NTC-DCEA: la flexión NO cumple (Mu/MR = {res['relacion']:.2f} > 1).")
                    v = acero.ntc_cortante_i(props, fy, d["fabricacion"] == LAMINADO)
                    r.agregar("ntc_vr", f"NTC: VR (FR = {v['FR']:.2f}, Cv = {v['Cv']:.3f})", v["VR"] / 1000, "kN",
                              2, EMPIRICA)
                    r.agregar("ntc_rel_v", "NTC: Vu/VR", fc * vmax / v["VR"], "", 3, EMPIRICA)
                    if fc * vmax > v["VR"]:
                        r.advertir("NTC-DCEA: el cortante NO cumple.")
                    r.ecuacion("NTC 6.3.2: Me = (Cb·π/L)·√(E·Iy·G·J + (π·E/L)²·Iy·Ca);  si Me > 2/3·Mp: "
                               "MR = 1.15·FR·Mp(1 − 0.28·Mp/Me) ≤ FR·Mp;  si no: MR = FR·Me")
                    r.ecuacion("NTC 7.2: VR = FR·0.6·Fy·Aa·Cv, Aa = h·ta")
                    r.nota("NTC-DCEA según el texto publicado en 2020 (edición 2017). La edición 2023 no estuvo "
                           "disponible para esta revisión: confirme que las expresiones sigan vigentes.")
    except ValueError as e:
        raise ErrorEntrada(str(e)) from e
    r.nota("Revisión de resistencia de la viga aislada: no incluye conexiones, apoyos, cargas concentradas en el "
           "alma (fluencia y aplastamiento local), atiesadores ni efectos de segundo orden.")


def calcular(d: dict) -> Resultado:
    r = Resultado()
    L = d["longitud"]
    requerir(d["posicion"] <= L, "La posición de la carga puntual no puede exceder la longitud de la viga.")
    P = d["carga_puntual"] * K.G
    w = d["carga_distribuida"] * K.G
    requerir(P > 0 or w > 0, "Capture al menos una carga.")
    E, nivel_e, aviso_e = modulo_elasticidad(d)
    if aviso_e:
        r.nota(aviso_e)
    sec = propiedades_seccion(d)
    EI = E * sec["I"]
    a = d["posicion"]

    n = 2001
    xs = [L * i / (n - 1) for i in range(n)]
    if 0 < a < L:
        xs = sorted(set(xs + [a, math.nextafter(a, 0.0)]))
    datos = [respuesta(d["tipo"], L, P, a, w, EI, x) for x in xs]
    vmax = max(abs(t[0]) for t in datos)
    i_m = max(range(len(xs)), key=lambda i: abs(datos[i][1]))
    i_y = max(range(len(xs)), key=lambda i: abs(datos[i][2]))
    mmax, ymax = abs(datos[i_m][1]), abs(datos[i_y][2])

    sigma = mmax * sec["c"] / sec["I"]
    if sec["k_tau"] is None:
        tau = vmax / sec["alma"]
    else:
        tau = sec["k_tau"] * vmax / sec["A"]

    if d["tipo"] == VOLADIZO:
        r.agregar("reaccion", "Reacción vertical en el empotramiento", (P + w * L) / 1000, "kN", 3)
        r.agregar("momento_empotramiento", "Momento en el empotramiento", (P * a + w * L ** 2 / 2) / 1000, "kN·m", 3)
    else:
        r1 = P * (L - a) / L + w * L / 2
        r.agregar("reaccion_izq", "Reacción en x = 0", r1 / 1000, "kN", 3)
        r.agregar("reaccion_der", "Reacción en x = L", (P + w * L - r1) / 1000, "kN", 3)
    r.agregar("modulo_e", "Módulo de elasticidad E", E / 1e9, "GPa", 1, nivel_e)
    r.agregar("inercia", "Momento de inercia I", sec["I"] * 1e8, "cm⁴", 2)
    r.agregar("modulo_seccion", "Módulo de sección S = I/c", sec["I"] / sec["c"] * 1e6, "cm³", 2)
    r.agregar("cortante_max", "Cortante máximo", vmax / 1000, "kN", 3)
    r.agregar("momento_max", "Momento flector máximo", mmax / 1000, "kN·m", 3)
    r.agregar("x_momento_max", "Ubicación del momento máximo", xs[i_m], "m", 3)
    r.agregar("deflexion_max", "Deflexión máxima", ymax * 1000, "mm", 3)
    r.agregar("x_deflexion_max", "Ubicación de la deflexión máxima", xs[i_y], "m", 3)
    r.agregar("esfuerzo_flexion", "Esfuerzo máximo de flexión σ = M·c/I", sigma / 1e6, "MPa", 2)
    r.agregar("esfuerzo_cortante", "Esfuerzo cortante máximo (aprox. según sección)", tau / 1e6, "MPa", 2,
              sec["nivel_tau"])
    if d["esfuerzo_admisible"] > 0:
        r.agregar("relacion_flexion", "Relación σ/σ_adm", sigma / 1e6 / d["esfuerzo_admisible"], "", 3)
        if sigma / 1e6 > d["esfuerzo_admisible"]:
            r.advertir("El esfuerzo de flexión supera el admisible capturado.")
    if d["limite_deflexion"] > 0:
        lim = L / d["limite_deflexion"]
        r.agregar("deflexion_limite", f"Deflexión permitida L/{d['limite_deflexion']:g}", lim * 1000, "mm", 3, DATO)
        if ymax > lim:
            r.advertir("La deflexión supera el límite capturado.")
    if nivel_e == ORIGINAL:
        r.nota(f"E tomado de la lista original ({E / 1e9:g} GPa) para la deflexión. AISC usa 199 948 MPa y la NTC "
               "200 000 MPa (las revisiones por norma usan esos valores); «Hierro» y «Madera» son muy variables.")
    if d["norma"] == NINGUNA:
        r.advertir("Sin revisión por norma: no se verifican pandeo lateral-torsional, pandeo local ni cortante del "
                   "alma. Elija AISC 360-22 o NTC-DCEA para acero estructural.")
    else:
        revision_norma(d, r, P, w, EI, vmax)
    r.ecuacion("Voladizo, P en a: y(x) = P·x²(3a − x)/(6EI) para x ≤ a;  P·a²(3x − a)/(6EI) para x ≥ a")
    r.ecuacion("Voladizo, w: y(x) = w·x²(6L² − 4Lx + x²)/(24EI)")
    r.ecuacion("Simple, P en a (b = L − a): y(x) = P·b·x(L² − b² − x²)/(6·L·EI) para x ≤ a (simétrica para x > a)")
    r.ecuacion("Simple, w: y(x) = w·x(L³ − 2Lx² + x³)/(24EI)")
    r.ecuacion("σ = M·c/I;   τ_max = k·V/A (k = 1.5 rectangular, 4/3 circular, ≈2 tubo delgado; I: V/(h·tw))")
    return r


def graficar(d: dict, resultado: Resultado):
    from matplotlib.figure import Figure

    datos = d  # entradas ya validadas por la interfaz
    L, a = datos["longitud"], datos["posicion"]
    P, w = datos["carga_puntual"] * K.G, datos["carga_distribuida"] * K.G
    E = modulo_elasticidad(datos)[0]
    EI = E * propiedades_seccion(datos)["I"]
    xs = [L * i / 400 for i in range(401)]
    vals = [respuesta(datos["tipo"], L, P, a, w, EI, x) for x in xs]
    fig = Figure(figsize=(7, 8))
    titulos = ("Fuerza cortante (kN)", "Momento flector (kN·m)", "Deflexión (mm, hacia abajo)")
    escalas = (1e-3, 1e-3, 1e3)
    for i in range(3):
        ax = fig.add_subplot(3, 1, i + 1)
        ys = [v[i] * escalas[i] for v in vals]
        ax.plot(xs, ys)
        ax.fill_between(xs, ys, alpha=0.2)
        if i == 2:
            ax.invert_yaxis()
        ax.set_ylabel(titulos[i])
        ax.grid(True)
    fig.axes[-1].set_xlabel("x (m)")
    fig.suptitle(datos["tipo"])
    fig.tight_layout()
    return fig


CALCULADORA = Calculadora(
    id="viga",
    nombre="Viga en voladizo o simplemente apoyada",
    disciplina="Estructural",
    descripcion="Reacciones, cortante, momento, deflexión y esfuerzos para carga puntual y uniforme.",
    campos=CAMPOS,
    funcion=calcular,
    graficar=graficar,
    estado_validacion=VALIDADA_CONDICIONES,
    archivos_originales=("Calculo de Cantiliver.py", "Calculo de Cantiliver rev1.py", "Calculo de Cantiliver rev2.py"),
    referencias=("Fórmulas clásicas de vigas de Euler-Bernoulli (resistencia de materiales).",
                 "AISC 360-22, capítulos F y G (LRFD); validado con AISC Design Examples v16.0 (F.1-1B, F.1-2B, "
                 "F.1-3B, F.3B, G.1B).",
                 "NTC-DCEA, CDMX: secciones 6.2, 6.3 y 7.2 (texto publicado en 2020); verificar contra la edición 2023."),
    limitaciones=("Elástico lineal, pequeñas deflexiones, sección constante, cargas estáticas.",
                  "Revisión por norma: perfiles I de doble simetría con alma compacta, barras rectangulares y redondas, "
                  "tubos redondos (AISC); NTC solo perfiles I compactos.",
                  "No revisa conexiones, aplastamiento del alma, atiesadores ni flexocompresión."),
    palabras_clave=("viga", "cantiliver", "voladizo", "deflexión", "momento", "estructural"),
)
