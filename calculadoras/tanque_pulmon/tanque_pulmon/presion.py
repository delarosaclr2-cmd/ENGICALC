"""Presión máxima admisible de la tubería y espesor por la ecuación de Barlow.

Dos criterios independientes, que se presentan juntos para poder compararlos:

A) BARLOW con factores de diseño, como lo plantean las memorias PCGV-DM-005/006/012/017 citando
   la NOM-007-SECRE-2010 (DOF 08/02/2011), «Transporte de gas natural»:

       t = P·D / (2·S·F·E·T)                 ->       P = 2·S·t·F·E·T / D

   S = resistencia mínima a la cedencia (SMYS) de la especificación del tubo (numeral 7.8);
   F = factor de diseño por clase de localización (numeral 7.10, cuadro 2);
   E = factor de eficiencia de la junta longitudinal (numeral 7.11, cuadro 3);
   T = factor de corrección por temperatura (numeral 7.12, cuadro 4, interpolación directa).

   LÍMITE DE APLICACIÓN: esta norma rige el TRANSPORTE DE GAS NATURAL por ducto. El factor F es un
   factor de clase de localización (densidad de población a lo largo del derecho de vía), por lo que
   el criterio no es aplicable a líneas de proceso dentro de una planta (agua de alimentación, vapor,
   aceite de lubricación, pasta). En esos servicios el resultado se entrega como INFORMATIVO, para
   comparar con la memoria original, y gobierna el criterio del código de diseño (B).

B) CÓDIGO DE TUBERÍA A PRESIÓN, ASME B31.3-2014 §304.1.2 ec. (3a) y ASME B31.1 §104.1.2
   (misma forma; Menon 2005 ec. 4.53):

       t = P·D / (2·(S·E·W + P·Y))           ->       P = 2·S·E·W·t / (D − 2·Y·t)

   S = esfuerzo admisible del material a la temperatura de diseño (B31.3 Tabla A-1), NO la cedencia.

ESPESOR QUE RESISTE LA PRESIÓN. Se distinguen tres espesores, porque la presión máxima depende de
cuál se use:
    t_nominal                                   espesor de catálogo (ASME B36.10M)
    t_disponible = t_nominal·(1 − tolerancia)   descontando la tolerancia de fabricación (12.5 %
                                                para grado B, ASTM A106/A530)
    t_resistente = t_disponible − c             descontando además el sobreespesor por corrosión c
                                                (las memorias usan 0.00625 in por año de vida útil)

La presión máxima admisible que se reporta como gobernante es la calculada con t_resistente: es la
que la línea soporta al final de su vida útil con el tubo en el límite inferior de fabricación.
Las otras dos se informan para ver el efecto de cada descuento.

No se verifican aquí: presión de prueba hidrostática, esfuerzos por expansión térmica, cargas
externas, refuerzo de ramales, clase de brida ni accesorios. La presión máxima de un sistema la
limita además el componente más débil (bridas, válvulas, juntas), que no se evalúa en este módulo.
"""
from __future__ import annotations

PSI = 6894.757293168
PULG = 0.0254

# --- NOM-007-SECRE-2010, cuadro 2 (numeral 7.10): factor de diseño por clase de localización
F_CLASE = {"1": 0.72, "2": 0.60, "3": 0.50, "4": 0.40}

# --- NOM-007-SECRE-2010, cuadro 3 (numeral 7.11): factor de eficiencia de junta longitudinal
E_JUNTA = {
    "A53 sin costura": 1.00,
    "A53 soldado por resistencia eléctrica": 1.00,
    "A53 soldado a tope en horno": 0.60,
    "A106 sin costura": 1.00,
    "A135 soldado por resistencia eléctrica": 1.00,
    "A139 soldado por fusión eléctrica": 0.80,
    "A211 soldadura helicoidal": 0.80,
    "A333 sin costura o resistencia eléctrica": 1.00,
    "A381 doble arco sumergido": 1.00,
    "A671/A672 clases 13,23,33,43,53": 0.80,
    "A671/A672 clases 12,22,32,42,52": 1.00,
    "API 5L sin costura o soldado (no a tope en horno)": 1.00,
    "API 5L soldado a tope en horno": 0.60,
    "Otra o desconocida, NPS ≥ 4": 0.80,
    "Otra o desconocida, NPS < 4": 0.60,
}

# --- NOM-007-SECRE-2010, cuadro 4 (numeral 7.12): factor de corrección por temperatura, en K
T_TEMPERATURA_K = [(400.0, 1.000), (420.0, 0.967), (450.0, 0.933), (480.0, 0.900), (500.0, 0.867)]


def factor_temperatura(t_c: float) -> float:
    """T de la NOM-007-SECRE-2010 cuadro 4 por interpolación directa. t_c en °C."""
    t_k = t_c + 273.15
    tab = T_TEMPERATURA_K
    if t_k <= tab[0][0]:
        return tab[0][1]
    if t_k > tab[-1][0]:
        raise ValueError(f"Temperatura {t_c:g} °C ({t_k:.1f} K) mayor que 500 K: fuera del cuadro 4 "
                         "de la NOM-007-SECRE-2010")
    for (k0, v0), (k1, v1) in zip(tab, tab[1:]):
        if k0 <= t_k <= k1:
            return v0 + (v1 - v0) * (t_k - k0) / (k1 - k0)


# ---------------------------------------------------------------- Barlow (NOM-007-SECRE-2010)
def barlow_espesor(p_pa: float, od_m: float, s_pa: float, f: float = 0.5, e: float = 1.0,
                   tf: float = 1.0) -> float:
    """t = P·D/(2·S·F·E·T), en m. P manométrica de diseño."""
    if min(s_pa, f, e, tf) <= 0:
        raise ValueError("S, F, E y T deben ser positivos")
    if p_pa < 0:
        raise ValueError("La presión de diseño (manométrica) no puede ser negativa")
    return p_pa * od_m / (2.0 * s_pa * f * e * tf)


def barlow_presion(t_m: float, od_m: float, s_pa: float, f: float = 0.5, e: float = 1.0,
                   tf: float = 1.0) -> float:
    """P = 2·S·t·F·E·T/D, en Pa manométricos: inversa de barlow_espesor."""
    if t_m <= 0:
        raise ValueError("El espesor que resiste la presión es nulo o negativo: revise el "
                         "sobreespesor por corrosión y la tolerancia de fabricación")
    return 2.0 * s_pa * t_m * f * e * tf / od_m


# ---------------------------------------------------------------- código a presión (B31.1 / B31.3)
def presion_codigo(t_m: float, od_m: float, s_pa: float, e: float = 1.0, w: float = 1.0,
                   y: float = 0.4) -> float:
    """P = 2·S·E·W·t/(D − 2·Y·t), en Pa manométricos: inversa de t = P·D/(2(S·E·W + P·Y))."""
    if t_m <= 0:
        raise ValueError("El espesor que resiste la presión es nulo o negativo: revise el "
                         "sobreespesor por corrosión y la tolerancia de fabricación")
    den = od_m - 2.0 * y * t_m
    if den <= 0:
        raise ValueError("D − 2·Y·t ≤ 0: la ecuación (3a) no aplica a esa relación espesor/diámetro")
    return 2.0 * s_pa * e * w * t_m / den


# ---------------------------------------------------------------- evaluación conjunta
def espesores(t_nominal_m: float, tolerancia: float = 0.125, c_m: float = 0.0) -> dict:
    """Los tres espesores: nominal, disponible (menos tolerancia) y resistente (menos corrosión)."""
    disp = t_nominal_m * (1.0 - tolerancia)
    return {"t_nominal_m": t_nominal_m, "t_disponible_m": disp, "t_resistente_m": disp - c_m,
            "tolerancia": tolerancia, "c_m": c_m}


def evaluar(od_m: float, t_nominal_m: float, *, s_adm_pa: float, s_cedencia_pa: float | None = None,
            f: float = 0.5, e_nom: float = 1.0, tf: float = 1.0, e: float = 1.0, w: float = 1.0,
            y: float = 0.4, c_m: float = 0.0, tolerancia: float = 0.125,
            p_diseno_pa: float | None = None, p_operacion_pa: float | None = None,
            aplica_nom: bool = False) -> dict:
    """Presión máxima admisible por el código y, si hay cedencia, por Barlow.

    s_adm_pa        esfuerzo admisible del material a la temperatura de diseño (B31.3 Tabla A-1)
    s_cedencia_pa   SMYS de la especificación del tubo (para Barlow); None = no evaluar Barlow
    f, e_nom, tf    factores F, E y T de la NOM-007-SECRE-2010
    e, w, y         factores E, W e Y del código a presión
    aplica_nom      True solo si el servicio es transporte de gas natural por ducto
    """
    r = espesores(t_nominal_m, tolerancia, c_m)
    r["od_m"] = od_m
    r["aplica_nom"] = aplica_nom
    r["avisos"] = []
    etiquetas = (("nominal", "t_nominal_m"), ("nuevo", "t_disponible_m"), ("fin_vida", "t_resistente_m"))

    r["codigo"] = {}
    for nombre, clave in etiquetas:
        try:
            r["codigo"][nombre] = presion_codigo(r[clave], od_m, s_adm_pa, e, w, y)
        except ValueError as exc:
            r["codigo"][nombre] = None
            r["avisos"].append(f"Presión máxima por el código ({nombre}): {exc}")
    r["p_max_pa"] = r["codigo"]["fin_vida"]
    r["s_adm_pa"] = s_adm_pa

    if s_cedencia_pa:
        r["barlow"] = {}
        for nombre, clave in etiquetas:
            try:
                r["barlow"][nombre] = barlow_presion(r[clave], od_m, s_cedencia_pa, f, e_nom, tf)
            except ValueError as exc:
                r["barlow"][nombre] = None
                r["avisos"].append(f"Presión máxima por Barlow ({nombre}): {exc}")
        r["p_max_barlow_pa"] = r["barlow"]["fin_vida"]
        r["s_cedencia_pa"] = s_cedencia_pa
        r["f"], r["e_nom"], r["tf"] = f, e_nom, tf
        if p_diseno_pa is not None:
            r["t_barlow_m"] = barlow_espesor(p_diseno_pa, od_m, s_cedencia_pa, f, e_nom, tf)
            r["t_barlow_requerido_m"] = r["t_barlow_m"] + c_m
        if not aplica_nom:
            r["avisos"].append(
                "El criterio de Barlow con factor de clase de localización F proviene de la "
                "NOM-007-SECRE-2010, que rige el transporte de gas natural por ducto. En este servicio "
                "se reporta solo para comparar con la memoria original; gobierna el código a presión.")
    else:
        r["barlow"] = None

    r["e"], r["w"], r["y"] = e, w, y
    r["p_diseno_pa"], r["p_operacion_pa"] = p_diseno_pa, p_operacion_pa
    for nombre, p in (("de diseño", p_diseno_pa), ("de operación", p_operacion_pa)):
        if p is not None and r["p_max_pa"] is not None:
            r[f"margen_{'diseno' if 'dise' in nombre else 'operacion'}"] = (r["p_max_pa"] / p) if p > 0 else None
    r["cumple"] = None if (p_diseno_pa is None or r["p_max_pa"] is None) else p_diseno_pa <= r["p_max_pa"]
    if r["t_resistente_m"] >= od_m / 6:
        r["avisos"].append("t ≥ D/6: pared gruesa, la ecuación (3a) no aplica (B31.3 §304.1.2(b)).")
    return r


# ---------------------------------------------------------------- material
# ASME B31.3-2014 Tabla A-1, A106 Gr. B (sin costura, E = 1.00): S [ksi] por temperatura [°F].
S_A106B_B313_KSI = [(100, 20.0), (200, 20.0), (300, 20.0), (400, 19.9), (500, 19.0), (600, 17.9),
                    (650, 17.3), (700, 16.7), (750, 13.9), (800, 11.4)]


def s_a106b_b313(t_c: float) -> float:
    """S [Pa] de A106 B por B31.3-2014 Tabla A-1, interpolado linealmente (como permite la tabla)."""
    tf = t_c * 1.8 + 32.0
    tab = S_A106B_B313_KSI
    if tf <= tab[0][0]:
        return tab[0][1] * 1000 * PSI
    if tf > tab[-1][0]:
        raise ValueError("Temperatura mayor que 800 °F: fuera de la tabla implementada")
    for (t0, s0), (t1, s1) in zip(tab, tab[1:]):
        if t0 <= tf <= t1:
            return (s0 + (s1 - s0) * (tf - t0) / (t1 - t0)) * 1000 * PSI


# ---------------------------------------------------------------- lectura del caso
_S_UNID = {"psi": PSI, "ksi": 1000 * PSI, "MPa": 1e6, "kgf/cm²": 98066.5}
_P_UNID = {"psig": PSI, "kPa g": 1000.0, "bar g": 1e5, "kgf/cm² g": 98066.5, "MPa g": 1e6}


def hay_material(cfg: dict) -> bool:
    """True si el caso trae con qué calcular la presión máxima (S de tabla o capturado)."""
    s_cfg = (cfg or {}).get("s") or {}
    return bool(s_cfg.get("tabla")) or s_cfg.get("valor") not in (None, "")


def resolver_s(cfg: dict):
    """Esfuerzo admisible S [Pa] y su fuente, desde el bloque `espesor` del caso."""
    s_cfg = (cfg or {}).get("s") or {}
    if s_cfg.get("tabla") == "A106B_B313":
        if cfg.get("t_diseno_c") in (None, ""):
            raise ValueError("capture la temperatura de diseño para leer la tabla A-1")
        s = s_a106b_b313(float(cfg["t_diseno_c"]))
        return s, f"ASME B31.3-2014 Tabla A-1, A106 Gr. B a {float(cfg['t_diseno_c']):g} °C"
    if s_cfg.get("valor") in (None, ""):
        raise ValueError("capture el esfuerzo admisible S o elija la tabla A106B_B313")
    return float(s_cfg["valor"]) * _S_UNID[s_cfg.get("unidad") or "psi"], s_cfg.get("fuente", "capturado")


def _bool(x) -> bool:
    """Acepta True/False, 1/0 y las cadenas que escriben los combos de la interfaz."""
    if isinstance(x, str):
        return x.strip().lower() in ("true", "si", "sí", "1", "x")
    return bool(x)


def _mag(m, tabla, nombre):
    """Magnitud {valor, unidad} -> unidades SI; None si no se capturó."""
    if not m or m.get("valor") in (None, ""):
        return None
    u = m.get("unidad") or next(iter(tabla))
    if u not in tabla:
        raise ValueError(f"{nombre}: unidad '{u}' no reconocida")
    return float(m["valor"]) * tabla[u]


def sobreespesor(cfg: dict) -> tuple:
    """c en m y su justificación. Usa vida útil × corrosión anual si se capturan; si no, c_mm."""
    por_ano, anos = cfg.get("c_por_ano_in"), cfg.get("vida_util_anos")
    if por_ano not in (None, "") and anos not in (None, ""):
        c = float(por_ano) * float(anos) * PULG
        return c, f"{float(por_ano):g} in por año × {float(anos):g} años de vida útil"
    return (cfg.get("c_mm") or 0.0) / 1000.0, "capturado"


def desde_caso(cfg: dict, od_m: float, t_nom_m: float, s_adm_pa: float,
               t_diseno_c: float | None = None, p_operacion_pa: float | None = None) -> dict | None:
    """Evalúa la presión máxima admisible con el bloque `espesor` del caso. None si falta el espesor.

    Lee del bloque: p_diseno, p_operacion, tolerancia_pct, c_mm (o c_por_ano_in + vida_util_anos),
    e, w, y, y el subbloque `barlow` (s_cedencia, clase_localizacion o f, junta o e, t o la
    temperatura de diseño, aplica_nom).
    """
    if not cfg or t_nom_m in (None, 0):
        return None
    p_dis = _mag(cfg.get("p_diseno"), _P_UNID, "presión de diseño")
    p_ope = p_operacion_pa if p_operacion_pa is not None else _mag(cfg.get("p_operacion"), _P_UNID,
                                                                   "presión de operación")
    c_m, origen_c = sobreespesor(cfg)
    b = cfg.get("barlow") or {}
    s_ced = _mag(b.get("s_cedencia"), _S_UNID, "cedencia S")
    f = b.get("f")
    if f in (None, ""):
        clase = str(b.get("clase_localizacion") or "")
        f = F_CLASE.get(clase)
        if s_ced and f is None:
            raise ValueError("Barlow: capture el factor F o una clase de localización 1, 2, 3 o 4 "
                             "(NOM-007-SECRE-2010 cuadro 2)")
    e_nom = b.get("e")
    if e_nom in (None, ""):
        junta = b.get("junta")
        e_nom = E_JUNTA.get(junta, 1.0) if junta else 1.0
    tf = b.get("t")
    if tf in (None, ""):
        base = b.get("t_gas_c", t_diseno_c if t_diseno_c is not None else cfg.get("t_diseno_c"))
        tf = factor_temperatura(float(base)) if base not in (None, "") else 1.0
    r = evaluar(od_m, t_nom_m, s_adm_pa=s_adm_pa, s_cedencia_pa=s_ced,
                f=float(f) if f not in (None, "") else 0.5, e_nom=float(e_nom), tf=float(tf),
                e=float(cfg.get("e", 1.0)), w=float(cfg.get("w", 1.0)), y=float(cfg.get("y", 0.4)),
                c_m=c_m, tolerancia=float(cfg.get("tolerancia_pct", 12.5)) / 100.0,
                p_diseno_pa=p_dis, p_operacion_pa=p_ope, aplica_nom=_bool(b.get("aplica_nom")))
    r["origen_c"] = origen_c
    r["fuente_s_cedencia"] = (b.get("s_cedencia") or {}).get("fuente", "especificación del tubo")
    r["clase_localizacion"] = b.get("clase_localizacion")
    r["junta"] = b.get("junta")
    return r


# ---------------------------------------------------------------- presentación
def _psi_bar(p):
    return "—" if p is None else f"{p/PSI:,.1f} psig ({p/1e5:.2f} bar g)"


def filas_datos(r: dict, ya=()) -> list:
    """Filas (parámetro, valor, nota) para la memoria; omite las etiquetas que ya estén en `ya`."""
    inm = lambda m: f"{m*1000:.3f} mm ({m/PULG:.4f} in)"
    filas = [("Diámetro exterior D", inm(r["od_m"]), "ASME B36.10M"),
             ("Espesor nominal", inm(r["t_nominal_m"]), "ASME B36.10M"),
             ("Tolerancia de fabricación", f"{r['tolerancia']*100:g} %", "ASTM A106 / A530, grado B"),
             ("Sobreespesor por corrosión c", inm(r["c_m"]), r.get("origen_c", "capturado")),
             ("Esfuerzo admisible S (código)", f"{r['s_adm_pa']/PSI:,.0f} psi "
              f"({r['s_adm_pa']/1e6:.1f} MPa)", "B31.3 Tabla A-1 o capturado")]
    if r.get("barlow"):
        nota_f = f"clase de localización {r['clase_localizacion']}" if r.get("clase_localizacion") else "F capturado"
        nota_e = r.get("junta") or "E capturado"
        filas += [("Cedencia mínima especificada S (SMYS)",
                   f"{r['s_cedencia_pa']/PSI:,.0f} psi ({r['s_cedencia_pa']/1e6:.1f} MPa)",
                   r.get("fuente_s_cedencia", "especificación del tubo")),
                  ("Factor de diseño F (Barlow)", f"{r['f']:g}",
                   f"NOM-007-SECRE-2010 cuadro 2: {nota_f}"),
                  ("Factor de junta longitudinal E (Barlow)", f"{r['e_nom']:g}",
                   f"NOM-007-SECRE-2010 cuadro 3: {nota_e}"),
                  ("Factor de temperatura T (Barlow)", f"{r['tf']:.4g}",
                   "NOM-007-SECRE-2010 cuadro 4, interpolación directa")]
    return [f for f in filas if f[0] not in set(ya)]


def filas_resultado(r: dict) -> list:
    """Filas (resultado, valor, nota) con los tres espesores y las presiones máximas."""
    inm = lambda m: f"{m*1000:.3f} mm ({m/PULG:.4f} in)"
    filas = [("Espesor disponible (nominal − tolerancia)", inm(r["t_disponible_m"]),
              f"−{r['tolerancia']*100:g} %"),
             ("Espesor que resiste la presión (− corrosión)", inm(r["t_resistente_m"]),
              "gobierna la presión máxima")]
    if r.get("t_barlow_m") is not None:
        filas += [("Espesor por Barlow a la presión de diseño", inm(r["t_barlow_m"]),
                   "t = P·D/(2·S·F·E·T)"),
                  ("Espesor requerido por Barlow (+ corrosión)", inm(r["t_barlow_requerido_m"]),
                   "t_r = t + t_c")]
    c = r["codigo"]
    filas += [("Presión máxima admisible, fin de vida útil", _psi_bar(c["fin_vida"]),
               "código a presión, con t − tolerancia − corrosión"),
              ("Presión máxima admisible, tubo nuevo", _psi_bar(c["nuevo"]),
               "sin descontar corrosión"),
              ("Presión máxima con el espesor nominal", _psi_bar(c["nominal"]),
               "sin descuentos: solo de referencia")]
    if r.get("barlow"):
        nota = "Barlow NOM-007-SECRE-2010" + ("" if r["aplica_nom"] else " — INFORMATIVO, no aplica a este servicio")
        filas += [("Presión máxima por Barlow, fin de vida útil", _psi_bar(r["barlow"]["fin_vida"]), nota),
                  ("Presión máxima por Barlow, espesor nominal", _psi_bar(r["barlow"]["nominal"]), nota)]
    if r.get("margen_diseno"):
        filas.append(("Margen sobre la presión de diseño", f"{r['margen_diseno']:.2f} ×",
                      "P máx. admisible / P de diseño"))
    if r.get("margen_operacion"):
        filas.append(("Margen sobre la presión de operación", f"{r['margen_operacion']:.2f} ×",
                      "P máx. admisible / P de operación"))
    return filas


def verificaciones(r: dict) -> list:
    """Filas (criterio, valor, límite, estado, referencia)."""
    v = []
    if r["p_diseno_pa"] is not None and r["p_max_pa"] is not None:
        v.append(("Presión de diseño ≤ presión máxima admisible",
                  f"{r['p_diseno_pa']/PSI:,.1f} psig", f"≤ {r['p_max_pa']/PSI:,.1f} psig",
                  "CUMPLE" if r["cumple"] else "NO CUMPLE",
                  "ASME B31.3 §304.1.2 / B31.1 §104.1.2, con t − tolerancia − corrosión"))
    if r["p_operacion_pa"] is not None and r["p_max_pa"] is not None:
        ok = r["p_operacion_pa"] <= r["p_max_pa"]
        v.append(("Presión de operación ≤ presión máxima admisible",
                  f"{r['p_operacion_pa']/PSI:,.1f} psig", f"≤ {r['p_max_pa']/PSI:,.1f} psig",
                  "CUMPLE" if ok else "NO CUMPLE", "ASME B31.3 §304.1.2 / B31.1 §104.1.2"))
    if r.get("barlow") and r["p_diseno_pa"] is not None and r["barlow"]["fin_vida"] is not None:
        ok = r["p_diseno_pa"] <= r["barlow"]["fin_vida"]
        if r["aplica_nom"]:
            estado, ref = ("CUMPLE" if ok else "NO CUMPLE"), "NOM-007-SECRE-2010 numeral 7.7"
        else:   # no es transporte de gas natural: el criterio se informa, no dictamina
            estado = "INFORMATIVO"
            ref = ("NOM-007-SECRE-2010 numeral 7.7 — no aplica a este servicio; comparación con la "
                   "memoria original" + ("" if ok else ". Con este criterio NO alcanzaría"))
        v.append(("Presión de diseño ≤ presión máxima por Barlow (informativo)",
                  f"{r['p_diseno_pa']/PSI:,.1f} psig", f"≤ {r['barlow']['fin_vida']/PSI:,.1f} psig",
                  estado, ref))
    return v


def sustitucion(r: dict) -> list:
    """Líneas de sustitución de valores para la memoria."""
    inp = lambda m: f"{m/PULG:.4f}"
    l = [f"t_resistente = {inp(r['t_nominal_m'])}·(1 − {r['tolerancia']:g}) − {inp(r['c_m'])} = "
         f"{inp(r['t_resistente_m'])} in"]
    if r["codigo"]["fin_vida"]:
        l.append(f"P_máx = 2·{r['s_adm_pa']/PSI:,.0f}·{r.get('e', 1):g}·{r.get('w', 1):g}·{inp(r['t_resistente_m'])}"
                 f"/({inp(r['od_m'])} − 2·{r.get('y', 0.4):g}·{inp(r['t_resistente_m'])}) = "
                 f"{r['codigo']['fin_vida']/PSI:,.1f} psig")
    if r.get("barlow"):
        if r.get("t_barlow_m") is not None:
            l.append(f"t Barlow = {r['p_diseno_pa']/PSI:.3f}·{inp(r['od_m'])}/(2·{r['s_cedencia_pa']/PSI:,.0f}·"
                     f"{r['f']:g}·{r['e_nom']:g}·{r['tf']:g}) = {r['t_barlow_m']/PULG:.5f} in;  "
                     f"t_r = t + t_c = {r['t_barlow_requerido_m']/PULG:.5f} in")
        if r["barlow"]["fin_vida"]:
            l.append(f"P_máx Barlow = 2·{r['s_cedencia_pa']/PSI:,.0f}·{inp(r['t_resistente_m'])}·{r['f']:g}·"
                     f"{r['e_nom']:g}·{r['tf']:g}/{inp(r['od_m'])} = {r['barlow']['fin_vida']/PSI:,.1f} psig")
    return l


def tabla(r: dict) -> tuple:
    """Tabla comparativa (título, encabezados, filas, anchos) para la memoria."""
    enc = ["Espesor considerado", "mm", "in", "P máx. código", "P máx. Barlow"]
    filas = []
    for nombre, clave, etiqueta in (("nominal", "t_nominal_m", "Nominal de catálogo"),
                                    ("nuevo", "t_disponible_m", "Nominal − tolerancia (tubo nuevo)"),
                                    ("fin_vida", "t_resistente_m", "− corrosión (fin de vida útil)")):
        pb = r["barlow"][nombre] if r.get("barlow") else None
        pc = r["codigo"][nombre]
        filas.append([etiqueta, f"{r[clave]*1000:.3f}", f"{r[clave]/PULG:.4f}",
                      "—" if pc is None else f"{pc/PSI:,.1f} psig",
                      "—" if pb is None else f"{pb/PSI:,.1f} psig"])
    return ("Presión máxima admisible según el espesor considerado", enc, filas, [5.6, 2.0, 2.0, 3.6, 3.6])


ECUACIONES = [
    "Barlow (NOM-007-SECRE-2010 numeral 7.7):  t = P·D/(2·S·F·E·T)  ->  P_máx = 2·S·t·F·E·T/D",
    "Código a presión (ASME B31.3 §304.1.2 ec. 3a; B31.1 §104.1.2):  t = P·D/(2·(S·E·W + P·Y))  ->  "
    "P_máx = 2·S·E·W·t/(D − 2·Y·t)",
    "Espesores:  t_disponible = t_nominal·(1 − tolerancia);  t_resistente = t_disponible − c",
]
REFERENCIAS = [
    "NOM-007-SECRE-2010, Transporte de gas natural (DOF 08/02/2011), numerales 7.7 a 7.12 y cuadros 2, 3 y 4.",
    "ASME B31.3-2014, §304.1.2 y Tabla A-1. ASME B31.1 §104.1.2 (no proporcionado: S capturado).",
    "ASME B36.10M (diámetros y espesores). ASTM A106/A530 (tolerancia de fabricación de 12.5 % para grado B).",
]
