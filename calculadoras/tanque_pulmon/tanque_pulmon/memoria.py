"""Arma la memoria de cálculo del tanque pulmón (y su esquema) a partir de los resultados del motor."""
from . import __version__
from . import unidades as u
from . import presion as pres
from .constantes import espesor_nominal_in, od_in
from .caso import CasoUsuario
from .esquema import construir
from .reporte import ECUACIONES, ejecutar, sustitucion_retencion, tabla_entradas, tabla_resultados
from .ui.memoria_pdf import Memoria

_OPCIONALES = ("q_compresor", "p_min_consumidor", "dp_linea", "p_calibracion_psv", "p_diseno")
SUPUESTOS = [
    "Balance de masa en un volumen rígido (tanque + tubería conectada sin regulador ni retención intermedios).",
    "Aire como gas ideal (Z ≈ 1 verificado con CoolProp a < 25 bar); descarga isotérmica salvo que se indique n > 1.",
    "Consumo constante durante el intervalo; ciclo de compresor con control carga/vacío.",
]
FUENTES = [
    "Menon, E. S. Piping Calculations Manual. McGraw-Hill, 2005, cap. 5 (aire libre, estándar y real).",
    "NOM-020-STPS-2011, num. 7.1.1 (clasificación) y 14.2 (calibración de la válvula de seguridad).",
    "ASME B31.3-2014 §300.1.3(d): los recipientes a presión se rigen por ASME BPVC Sec. VIII (fuera de alcance).",
]


def normalizar(d: dict) -> dict:
    """La ventana trabaja con texto: convierte el caso a la forma que espera CasoUsuario."""
    d = dict(d)
    for k in _OPCIONALES:
        v = d.get(k)
        if isinstance(v, dict) and v.get("valor") in (None, ""):
            d[k] = None
    if isinstance(d.get("incluir_tuberia"), str):
        d["incluir_tuberia"] = d["incluir_tuberia"].strip().lower() in ("true", "sí", "si", "1")
    for k in ("t_retencion_req_min", "fraccion_carga_max_pct", "ciclos_h_max", "t_diseno_c"):
        if d.get(k) == "":
            d[k] = None
    return d


def presiones_tramos(caso, inf):
    """Presión máxima admisible de cada tramo de tubería conectado que traiga datos de material.

    El bloque `espesor` puede ir en cada tramo o, una sola vez, en el caso (se aplica a todos los
    tramos con NPS y cédula). La presión de comparación es la de calibración de la válvula de alivio
    si se capturó; si no, la presión superior del tanque.
    """
    comun = caso.espesor or {}
    p_ope = caso.a_criterios().p_calibracion_psv_pa_g
    filas, tablas, ver, adv = [], [], [], []
    for tu in caso.tramos:
        cfg = dict(comun)
        cfg.update(tu.espesor or {})
        if not (tu.nps and tu.cedula) or not pres.hay_material(cfg):
            continue
        try:
            od = od_in(tu.nps) * pres.PULG
            tn = espesor_nominal_in(tu.nps, tu.cedula) * pres.PULG
            s_adm, _ = pres.resolver_s(cfg)
            pm = pres.desde_caso(cfg, od, tn, s_adm, cfg.get("t_diseno_c"), p_operacion_pa=p_ope)
        except (KeyError, ValueError) as exc:
            adv.append(f"Tramo '{tu.descripcion}': no se evaluó la presión máxima ({exc})")
            continue
        filas += [(f"Tubería '{tu.descripcion}': {a}", b, n)
                  for a, b, n in pres.filas_datos(pm) + pres.filas_resultado(pm)]
        tit, enc, fl, anchos = pres.tabla(pm)
        tablas.append((f"{tu.descripcion} — {tit}", enc, fl, anchos))
        ver += [(f"{tu.descripcion}: {v[0]}", *v[1:]) for v in pres.verificaciones(pm)]
        adv += pm["avisos"]
    return filas, tablas, ver, adv


def evaluar(d: dict) -> Memoria:
    caso = CasoUsuario.from_dict(normalizar(d))
    inf = ejecutar(caso)
    e, r = inf.entradas, inf.resultados
    ver = [(v.criterio, v.valor, v.limite, v.estado, v.referencia) for v in inf.verificaciones]
    fil_p, tablas, ver_p, adv_p = presiones_tramos(caso, inf)
    ver += ver_p
    resumen = [("Tiempo de retención", f"{r.t_retencion_min:.2f} min ({u.min_a_texto(r.t_retencion_min)})"),
               ("Volumen del sistema", f"{r.v_sistema_m3:.3f} m³"),
               ("Masa útil entre límites", f"{r.masa_util_kg:.2f} kg")]
    if r.v_tanque_req_m3 is not None:
        resumen.append(("Tanque requerido", f"{r.v_tanque_req_m3:.2f} m³ para {e.t_retencion_req_min:g} min"))
    if r.fraccion_carga is not None:
        resumen.append(("Fracción de carga", f"{r.fraccion_carga*100:.1f} %"))
        resumen.append(("Ciclos por hora", f"{r.ciclos_por_hora:.2f}"))
    return Memoria(
        titulo="Tanque pulmón de aire comprimido", caso=caso.nombre, version=__version__, huella=inf.huella,
        documento=caso.documento,
        objetivo="Determinar el tiempo que el tanque y la tubería conectada sostienen el consumo sin aporte del "
                 "compresor, el volumen requerido para un tiempo dado y, si se conoce el FAD, el ciclo de carga.",
        datos=tabla_entradas(inf), resultados=tabla_resultados(inf) + fil_p, verificaciones=ver,
        advertencias=list(r.advertencias) + adv_p,
        ecuaciones=ECUACIONES + (pres.ECUACIONES if tablas else []),
        sustitucion=[sustitucion_retencion(inf)], supuestos=SUPUESTOS,
        referencias=FUENTES + (pres.REFERENCIAS if tablas else []),
        notas=caso.notas, escena=construir(inf), resumen=resumen, tablas=tablas)
