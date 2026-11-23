"""Motor de cálculo de líneas de vapor.

Método:
- Propiedades: IAPWS-IF97 (regiones 2 y 4) e IAPWS 2008 para la viscosidad.
- Velocidad: v = ṁ·ν/A (Menon 2005, ecs. 4.23–4.24) con el diámetro interior real.
- Caída de presión: Darcy por segmentos (Menon ecs. 4.29–4.31) con flujo adiabático (h constante):
  en cada segmento el estado se obtiene de (p, h) con IF97, de modo que la densidad sigue la caída
  de presión. Los accesorios (ΣK) se reparten uniformemente en la longitud.
- Velocidad sónica de referencia: Us = √(γ·p·ν) (Menon ec. 4.25), γ = 1.135 saturado y 1.3 sobrecalentado.
- Venteo/silenciador: expansión isentálpica hasta la presión de descarga; caudal real Q = ṁ·ν₂.
- Espesor: ASME B31.1 (S capturado) o B31.3 (Tabla A-1) con la misma forma t = PD/(2(SEW + PY)) + c.
"""
from __future__ import annotations

import hashlib
import json
import math

from .nucleo import espesor as esp
from .nucleo import if97
from .nucleo import presion as pres
from .nucleo import seleccion as sel
from .nucleo import unidades as u
from .nucleo.hidraulica import area, factor_friccion
from .nucleo.tubos import (RUGOSIDAD_ACERO_M, d_interior_m, espesor_nominal_in, k_accesorio, nps_lista, od_in)

AVISO = ("Herramienta de apoyo al cálculo. Sus resultados no sustituyen la revisión y aprobación de un "
         "ingeniero responsable ni constituyen una validación del proyecto.")
FT3_LB = 0.3048 ** 3 / u.LB     # m³/kg por ft³/lb
# Segmentos para las marchas AUXILIARES (capacidad, curva y barrido de diámetros), que se repiten
# decenas de veces al resolver el caudal de capacidad. El dictamen del tramo sigue usando los 60
# segmentos de calcular(). La iteración de punto medio converge cada segmento, así que el estado
# de salida ya coincide con el de 120 segmentos en 8 cifras con 4 (test_segmentacion_converge);
# 8 deja el doble de margen. Si se cambia, revisar ese test.
N_SEG_BARRIDO = 8
# Segmentos del DICTAMEN. Todo valor que se anuncie como límite (capacidad máxima) o como estado
# de un diámetro cerca del límite se comprueba con este mismo número, para que no lo contradiga.
N_SEG_DICTAMEN = 60
# Una fila del barrido se recalcula con N_SEG_DICTAMEN si su velocidad cae dentro de esta banda
# relativa alrededor de v_máx, o si la caída de presión supera DP_REL_REFINAR de la presión de
# entrada. Diferencia observada entre 8 y 60 segmentos: < 4·10⁻⁵ relativa cerca de 50.9 m/s, y
# ≈ 1·10⁻³ con ΔP/P₁ = 0.62 (Mach 0.54). Con ambas reglas ningún estado ni velocidad mostrada
# difiere del dictamen (test_barrido_coincide_con_el_dictamen_en_todos_los_casos).
BANDA_REFINAR = 5e-3
DP_REL_REFINAR = 0.2


class ErrorEntrada(ValueError):
    pass


def huella(c: dict) -> str:
    return hashlib.sha256(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _num(x, nombre):
    try:
        return float(x)
    except (TypeError, ValueError):
        raise ErrorEntrada(f"Dato numérico inválido: {nombre}")


def estado_entrada(c, patm):
    p = u.presion_a_pa_abs(_num(c["p_entrada"]["valor"], "presión de entrada"), c["p_entrada"]["unidad"], patm)
    tipo = c.get("estado", "saturado")
    try:
        if tipo == "saturado":
            return if97.estado_sat(p, 1.0)
        if tipo == "titulo":
            x = _num(c.get("titulo"), "título")
            return if97.estado_sat(p, x)
        t = _num(c["temperatura_c"], "temperatura") + 273.15
        if t <= if97.t_sat(p) + 1e-6:
            raise ErrorEntrada(f"A {p/1000:.1f} kPa a el vapor satura a {if97.t_sat(p)-273.15:.2f} °C: "
                               "la temperatura capturada no es de vapor sobrecalentado")
        return if97.estado_pt(p, t)
    except ValueError as exc:
        raise ErrorEntrada(str(exc))


def gamma(e):
    return 1.135 if (e.x is not None) else 1.3


def marcha(e1, d, eps, L, k_tot, m, n_seg: int = 60):
    """Marcha por segmentos a lo largo del tramo: estado de salida y perfil [(x, p, v)].

    Flujo adiabático (h constante): en cada segmento el estado se obtiene de (p, h) con IF97, de
    modo que el volumen específico sigue la caída de presión y la velocidad crece hacia la salida.
    Los accesorios (ΣK) se reparten uniformemente en la longitud.

    Está extraída de calcular() para que el barrido de diámetros y el caudal de capacidad usen
    EXACTAMENTE el mismo modelo que el dictamen, sin duplicar la física.
    """
    A = area(d)
    G = m / A
    perfil = [(0.0, e1.p, G * e1.v)]
    if not (L > 0 or k_tot > 0):
        return e1, perfil
    p, est, x = e1.p, e1, 0.0
    dx = L / n_seg if L > 0 else 0.0
    dk = k_tot / n_seg
    for i in range(n_seg):
        for _ in range(3):             # punto medio: ΔP con la densidad media del segmento
            re = G * d / est.mu
            f, _r = factor_friccion(re, eps, d)
            dp = (f * dx / d + dk) * G * G * est.v / 2
            if p - dp <= 0.3 * e1.p:
                raise ErrorEntrada("La caída de presión supera el 70 % de la presión de entrada: el modelo por "
                                   "segmentos sin término de aceleración no es válido (posible flujo crítico)")
            try:
                est = if97.estado_ph(p - dp / 2, e1.h)
            except ValueError as exc:
                raise ErrorEntrada(f"Estado fuera de IF97 a lo largo de la línea: {exc}")
        p -= dp
        est = if97.estado_ph(p, e1.h)
        x += dx
        perfil.append((x if L > 0 else (i + 1) / n_seg, p, G * est.v))
    return est, perfil


def calcular(c: dict, n_seg: int = N_SEG_DICTAMEN) -> dict:
    patm = _num(c.get("p_atm_kpa", 101.325), "presión atmosférica") * 1000
    tub = c["tuberia"]
    try:
        d = _num(tub["d_interior_mm"], "Di") / 1000 if tub.get("d_interior_mm") else d_interior_m(tub["nps"], tub["cedula"])
    except KeyError as exc:
        raise ErrorEntrada(str(exc).strip("'\""))
    m = u.masico_a_kgs(_num(c["flujo"]["valor"], "flujo másico"), c["flujo"]["unidad"])
    if m <= 0:
        raise ErrorEntrada("El flujo másico debe ser positivo")
    e1 = estado_entrada(c, patm)
    A = area(d)
    G = m / A
    eps = _num(c.get("rugosidad_mm", RUGOSIDAD_ACERO_M * 1000), "rugosidad") / 1000
    L = _num(c.get("longitud_m", 0) or 0, "longitud")
    v1 = G * e1.v
    re1 = G * d / e1.mu
    f1, reg1 = factor_friccion(re1, eps, d)
    detalle = []
    for a in c.get("accesorios", []):
        n = a.get("cantidad", 1)
        try:
            k = k_accesorio(a["tipo"], tub.get("nps"), n, a.get("k"))
        except KeyError as exc:
            raise ErrorEntrada(str(exc).strip("'\""))
        detalle.append((a["tipo"], n, k / n if n else 0.0, k))
    k_tot = sum(x[3] for x in detalle)
    res = {"m": m, "d": d, "A": A, "G": G, "L": L, "eps": eps, "patm": patm, "e1": e1, "v1": v1, "re1": re1,
           "f1": f1, "regimen": reg1, "detalle_k": detalle, "k_total": k_tot, "perfil": [(0.0, e1.p, v1)],
           "verificaciones": [], "advertencias": [], "espesor": None, "venteo": None}
    adv, ver = res["advertencias"], res["verificaciones"]
    if e1.x is not None and e1.x < 1:
        adv.append("Vapor húmedo: modelo homogéneo; la viscosidad es la del vapor saturado (aproximación).")
    # Caída de presión por segmentos (flujo adiabático, h constante)
    e2, res["perfil"] = marcha(e1, d, eps, L, k_tot, m, n_seg)
    res.update(e2=e2, v2=G * e2.v, dp=e1.p - e2.p)
    us = math.sqrt(gamma(e2) * e2.p * e2.v)
    res["mach2"] = res["v2"] / us
    res["us2"] = us
    if res["mach2"] > 0.3:
        adv.append(f"Mach {res['mach2']:.2f} a la salida: los efectos de compresibilidad son importantes.")
    if reg1.startswith("crítico"):
        adv.append("Reynolds entre 2100 y 4000: factor de fricción incierto.")
    # Criterio de velocidad (con la velocidad máxima del tramo, a la salida)
    cv = c.get("criterio_velocidad") or {}
    vmax, vmin = cv.get("v_max_m_s"), cv.get("v_min_m_s")
    vm = max(v1, res["v2"])
    if vmax not in (None, ""):
        ver.append(("Velocidad máxima del tramo ≤ recomendada", f"{vm:.2f} m/s", f"≤ {float(vmax):g} m/s",
                    "CUMPLE" if vm <= float(vmax) else "NO CUMPLE", cv.get("fuente", "criterio del usuario")))
    if vmin not in (None, "") and v1 < float(vmin):
        ver.append(("Velocidad ≥ mínima del intervalo", f"{v1:.2f} m/s", f"≥ {float(vmin):g} m/s", "INFORMATIVO",
                    "Por debajo del intervalo: tubería holgada (menor ΔP; no es un problema de seguridad)"))
    dpmax = c.get("dp_max_kpa")
    if dpmax not in (None, ""):
        ver.append(("Caída de presión ≤ admisible", f"{res['dp']/1000:.2f} kPa", f"≤ {float(dpmax):g} kPa",
                    "CUMPLE" if res["dp"] / 1000 <= float(dpmax) else "NO CUMPLE", c.get("fuente_dp_max", "criterio")))
    # Venteo / silenciador
    vt = c.get("venteo") or {}
    if vt.get("p_descarga") and vt["p_descarga"].get("valor") not in (None, ""):
        pd = u.presion_a_pa_abs(_num(vt["p_descarga"]["valor"], "p descarga"), vt["p_descarga"]["unidad"], patm)
        try:
            ed = if97.estado_ph(pd, e1.h)
        except ValueError as exc:
            raise ErrorEntrada(f"Venteo: {exc}")
        q = m * ed.v
        res["venteo"] = {"p": pd, "estado": ed, "q_m3s": q, "acfm": q / (0.3048 ** 3) * 60}
    # Espesor
    try:
        r_esp, datos_esp = esp.desde_caso(c.get("espesor"), tub)
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(f"Espesor: {exc}")
    if r_esp:
        res["espesor"], res["datos_espesor"] = r_esp, datos_esp
        ver.append(esp.verificacion(r_esp))
        adv.extend(r_esp["avisos"])
    # Presión máxima admisible y barridos de velocidad
    res["presion"] = presion_maxima(c, tub)
    if res["presion"]:
        ver.extend(pres.verificaciones(res["presion"]))
        adv.extend(res["presion"]["avisos"])
    res.update(barridos(c, res))
    return res


def presion_maxima(c, tub):
    """Presión máxima admisible de la tubería. None si no hay datos de espesor o de material."""
    cfg = c.get("espesor") or {}
    geo = esp.geometria(cfg, tub, od_in, espesor_nominal_in)
    if not geo or not pres.hay_material(cfg):
        return None
    try:
        s_adm, _ = esp.resolver_s(cfg)
        return pres.desde_caso(cfg, geo[0], geo[1], s_adm, cfg.get("t_diseno_c"))
    except (KeyError, ValueError) as exc:
        raise ErrorEntrada(f"Presión máxima: {str(exc).strip(chr(39) + chr(34))}")


def _k_total_para_nps(c: dict, nps) -> float:
    """ΣK del tramo si la línea fuera de ese NPS.

    Los accesorios con K capturado (k explícito) se conservan tal cual; los que tienen K tabulado
    se recalculan con la tabla de ese NPS. Sin NPS no se puede tabular: se exige el K capturado.
    """
    total = 0.0
    for a in c.get("accesorios", []):
        total += k_accesorio(a["tipo"], nps, a.get("cantidad", 1), a.get("k"))
    return total


def barridos(c, res):
    """Velocidad por diámetro al caudal real de entrada, capacidad de la línea y curva v(Q).

    El caudal volumétrico real es Q = ṁ·ν a la condición de ENTRADA; la velocidad crece a lo largo
    de la línea conforme cae la presión. Igual que el dictamen, el máximo se juzga con la mayor
    velocidad del tramo (salida) y el mínimo con la menor (entrada).
    """
    m, e1, eps, L, k_tot = res["m"], res["e1"], res["eps"], res["L"], res["k_total"]
    q = m * e1.v
    cv = c.get("criterio_velocidad") or {}
    vmin, vmax = cv.get("v_min_m_s"), cv.get("v_max_m_s")
    tub = c["tuberia"]
    ced = str(tub.get("cedula") or "40")
    hay_dp = L > 0 or k_tot > 0
    d0 = res["d"]

    def v_gobernante(q_entrada, n_seg=N_SEG_BARRIDO):
        """Velocidad MÁXIMA DEL TRAMO (diámetro y accesorios del caso) para ese caudal de entrada.

        Con caída de presión el volumen específico crece y la velocidad es mayor a la salida, así
        que ṁ·ν₁/A con la densidad de entrada subestima lo que gobierna. Se vuelve a marchar el
        tramo con el flujo másico correspondiente (ṁ = Q/ν₁, con la misma presión de entrada).
        Solo vale para el diámetro del caso: otro diámetro tiene otros K (ver calc).
        """
        mm = q_entrada / e1.v
        v_ent = mm * e1.v / area(d0)
        if not hay_dp:
            return v_ent
        e2, _ = marcha(e1, d0, eps, L, k_tot, mm, n_seg)
        return max(v_ent, mm * e2.v / area(d0))

    def v_dictamen(q_entrada):
        """La misma velocidad con los segmentos del dictamen: con ella se comprueba la capacidad."""
        return v_gobernante(q_entrada, N_SEG_DICTAMEN)

    cand = []
    for nps in nps_lista():
        try:
            cand.append((nps, ced, d_interior_m(nps, ced)))
        except KeyError:
            continue
    d_a_nps = {d: nps for nps, _c, d in cand}

    def calc(d):
        """Velocidad gobernante y ΔP del tramo completo con ese diámetro, al mismo flujo.

        Los accesorios se recalculan para el NPS de ESE diámetro: los K tabulados (Menon 5.11)
        cambian con el diámetro, mientras que los K capturados explícitamente se conservan. Si la
        velocidad cae cerca de v_máx o la caída de presión es grande, la fila se recalcula con los
        segmentos del dictamen, para que coincida con lo que daría calcular() con ese diámetro.
        """
        g = m / area(d)
        re = g * d / e1.mu
        f, _ = factor_friccion(re, eps, d)
        v_ent = g * e1.v
        k_d = _k_total_para_nps(c, d_a_nps.get(d, tub.get("nps")))
        if not (L > 0 or k_d > 0):
            return {"v": v_ent, "v_baja": v_ent, "re": re, "f": f, "dp_pa": None}
        e2, _ = marcha(e1, d, eps, L, k_d, m, N_SEG_BARRIDO)
        v = max(v_ent, g * e2.v)
        cerca = vmax not in (None, "") and abs(v - float(vmax)) <= BANDA_REFINAR * float(vmax)
        if cerca or (e1.p - e2.p) > DP_REL_REFINAR * e1.p:
            e2, _ = marcha(e1, d, eps, L, k_d, m, N_SEG_DICTAMEN)
            v = max(v_ent, g * e2.v)
        return {"v": v, "v_baja": v_ent, "re": re, "f": f, "dp_pa": e1.p - e2.p}

    # Sin caída de presión la velocidad es la misma en todo el tramo: no hace falta resolver nada.
    vg = v_gobernante if hay_dp else None
    vd = v_dictamen if hay_dp else None
    donde = "a la salida" if hay_dp else ""
    # La velocidad gobernante al caudal capturado ya la dio el dictamen: no se repite la marcha.
    v_act = max(res["v1"], res["v2"]) if "v2" in res else None
    lim = sel.limites_de_caudal(d0, q, vmin, vmax, vg, vd, v_actual=v_act)
    salida = {"q_entrada_m3s": q,
              "curva": sel.curva(d0, q, vmin, vmax, n=12 if hay_dp else 24, v_gobernante=vg,
                                 v_verificacion=vd, limites=lim),
              "tabla_capacidad": sel.tabla_capacidad(d0, q, vmin, vmax,
                                                     conv=lambda x: x / e1.v / u.masico_a_kgs(1, c["flujo"]["unidad"]),
                                                     unidad=c["flujo"]["unidad"], simbolo="ṁ",
                                                     v_gobernante=vg, donde_v=donde, v_verificacion=vd,
                                                     limites=lim),
              "diametro_requerido_m": sel.diametro_requerido(q, float(vmax)) if vmax not in (None, "") else None}
    cand = sel.ventana(cand, q, vmin, vmax, tub.get("nps"))
    if cand:
        salida["tabla_diametros"] = sel.tabla_diametros(
            cand, calc, vmin, vmax, tub.get("nps"), L or None, donde_v=donde,
            nota_dp="total del tramo ({} m y accesorios)" if hay_dp else "por fricción en {} m de tubo recto")
    return salida

