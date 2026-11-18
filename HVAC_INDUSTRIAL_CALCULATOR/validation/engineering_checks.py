"""Verificaciones automáticas de ingeniería.

Cada verificación emite una ``Alert`` con: parámetro, valor, criterio, consecuencia,
recomendación y fuente. Los umbrales provienen de ``config/settings.json``
(criterios documentados) o de la base de datos técnica (``database/``).
"""
from __future__ import annotations

import math

from core import constants as C
from core.air_properties import pressure_from_altitude
from .alerts import Alert, BASIS_PHYSICS, BASIS_REFERENCE, BASIS_HYPOTHESIS, BASIS_DATA

M_AIR = "Propiedades del aire"
M_FLOW = "Caudales"
M_HOOD = "Campanas"
M_DUCT = "Diseño de ductos"
M_LOSS = "Pérdidas de presión"
M_NET = "Redes ramificadas"
M_FAN = "Selección de ventiladores"
M_POW = "Potencia y motores"


def _crit(settings, key):
    c = settings.crit(key)
    return c["value"], c.get("source", ""), c.get("basis", "hipótesis"), c.get("level", "MEDIO")


def _basis(b: str) -> str:
    return {"hipótesis": BASIS_HYPOTHESIS, "referencia": BASIS_REFERENCE, "física": BASIS_PHYSICS}.get(b, BASIS_HYPOTHESIS)


# ---------------------------------------------------------------------------
# Aire
# ---------------------------------------------------------------------------

def check_air(air_in, air, settings) -> list[Alert]:
    out: list[Alert] = []
    if air is None:
        return out
    tol, src, basis, lvl = _crit(settings, "p_altitude_tolerance_pct")
    if air_in.mode == "custom" and air_in.p_pa and air_in.altitude_m is not None:
        p_alt = pressure_from_altitude(air_in.altitude_m)
        dev = abs(air_in.p_pa - p_alt) / p_alt * 100
        if dev > tol:
            out.append(Alert(lvl, M_AIR, "Presión atmosférica", f"La presión indicada difiere {dev:.1f} % de la atmósfera "
                             f"estándar a {air_in.altitude_m:.0f} m", air_in.p_pa, "pressure",
                             criterion=f"|p − p_estándar(Z)|/p_estándar ≤ {tol} % (p_estándar = {p_alt:.0f} Pa)",
                             consequence="Si la presión o la altitud están mal capturadas, la densidad y todas las "
                                         "presiones del sistema quedan sesgadas.",
                             recommendation="Confirme la altitud del sitio y el origen de la presión barométrica "
                                            "(medición, estación meteorológica o valor de proyecto).",
                             source=src, basis=_basis(basis)))
        else:
            out.append(Alert("CORRECTO", M_AIR, "Presión atmosférica", "Presión consistente con la altitud",
                             air_in.p_pa, "pressure", criterion=f"desviación {dev:.1f} % ≤ {tol} %", source=src,
                             basis=_basis(basis)))
    dfac = air.rho / C.RHO_STD_AMCA
    if abs(dfac - 1) > 0.03:
        out.append(Alert("INFO", M_AIR, "Densidad del aire", f"La densidad real es {dfac * 100:.1f} % de la del aire "
                         "estándar de catálogo (1.2 kg/m³)", air.rho, "density",
                         criterion="ρ/ρ_estándar", consequence="Las curvas de catálogo sobrestiman presión y potencia "
                         "si no se corrigen; el caudal volumétrico no cambia.",
                         recommendation="El programa corrige las curvas del ventilador por densidad; verifique que la "
                                        "selección del fabricante también se haga a la densidad real.",
                         source="Leyes de ventiladores (AMCA 99); ACGIH (factor de densidad df)", basis=BASIS_PHYSICS))
    if air_in.rho_measured:
        tol2, src2, basis2, lvl2 = _crit(settings, "density_measured_tolerance_pct")
        dev = abs(air_in.rho_measured - air.rho) / air.rho * 100
        if dev > tol2:
            out.append(Alert(lvl2, M_AIR, "Densidad declarada", f"La densidad declarada difiere {dev:.1f} % de la "
                             "calculada con T, p y HR", air_in.rho_measured, "density",
                             criterion=f"desviación ≤ {tol2} % (calculada {air.rho:.4f} kg/m³)",
                             consequence="Densidad incompatible con las condiciones: se usará la calculada.",
                             recommendation="Revise temperatura, altitud/presión, humedad o la medición de densidad.",
                             source=src2, basis=_basis(basis2)))
    if air_in.t_min_surface_c is not None and not math.isnan(air.t_dew_c):
        m, src3, basis3, lvl3 = _crit(settings, "condensation_margin_K")
        if air_in.t_min_surface_c < air.t_dew_c + m:
            out.append(Alert(lvl3, M_AIR, "Riesgo de condensación", "La temperatura superficial mínima del ducto está "
                             "por debajo (o cerca) del punto de rocío del aire transportado", air_in.t_min_surface_c,
                             "temperature", criterion=f"t_superficie ≥ t_rocío + {m} K (t_rocío = {air.t_dew_c:.1f} °C)",
                             consequence="Condensación interna, corrosión, adherencia de polvo y obstrucción.",
                             recommendation="Aislar térmicamente el ducto, prever drenajes en puntos bajos o "
                                            "materiales resistentes a la corrosión.",
                             source=src3, basis=_basis(basis3)))
    return out


# ---------------------------------------------------------------------------
# Caudales
# ---------------------------------------------------------------------------

def check_airflow(af_in, airflow_res: dict, hoods: list, settings) -> tuple[list[Alert], bool]:
    """Devuelve (alertas, información_insuficiente)."""
    out: list[Alert] = []
    insufficient = False
    purpose = af_in.purpose
    has_ach = "ACH" in airflow_res
    has_dil = "Dilución" in airflow_res
    if purpose == "contaminant_control":
        if has_ach and not has_dil and not hoods:
            out.append(Alert("ALTO", M_FLOW, "Método de caudal", "Se usa ACH como único criterio para controlar un "
                             "contaminante", airflow_res["ACH"].Q, "flow",
                             criterion="El control de exposición requiere relacionar caudal con tasa de generación y "
                                       "concentración admisible",
                             consequence="Un número de renovaciones no garantiza concentraciones bajo el límite de "
                                         "exposición; puede sub o sobredimensionar el sistema.",
                             recommendation="Aplique balance de contaminantes (dilución) con la tasa de generación y el "
                                            "VLE, o captura localizada si la fuente es identificable.",
                             source="ACGIH, Industrial Ventilation Manual (ventilación por dilución vs. extracción "
                                    "localizada)", basis=BASIS_REFERENCE))
        if af_in.source_identifiable and not hoods:
            out.append(Alert("MEDIO", M_FLOW, "Estrategia de ventilación", "Fuente de contaminante identificable sin "
                             "captura localizada", criterion="Fuente puntual identificable → captura en origen",
                             consequence="La dilución requiere caudales mayores y no protege la zona respiratoria "
                                         "cercana a la fuente.",
                             recommendation="Evalúe campanas de extracción localizada en la fuente.",
                             source="ACGIH, Industrial Ventilation Manual", basis=BASIS_REFERENCE))
        if not has_dil:
            insufficient = insufficient or not hoods
            out.append(Alert("INFO", M_FLOW, "Datos de contaminante", "Faltan tasa de generación y concentración "
                             "objetivo", criterion="Datos mínimos: generación, VLE/objetivo, fondo, factor de mezcla",
                             consequence="No es posible verificar el control de la exposición por dilución.",
                             recommendation="Obtenga la tasa de generación (balance de materiales o mediciones) y el "
                                            "VLE aplicable (NOM-010-STPS o TLV de ACGIH).",
                             source="ACGIH; NOM-010-STPS-2014", basis=BASIS_DATA))
    if has_dil:
        d = airflow_res["Dilución"].details
        if not af_in.dilution.get("toxicity_known"):
            out.append(Alert("INFO", M_FLOW, "Toxicidad del contaminante", "No se ha confirmado la toxicidad / VLE del "
                             "contaminante", criterion="Concentración objetivo justificada con VLE",
                             consequence="La concentración objetivo podría no proteger a los trabajadores.",
                             recommendation="Documente el VLE (NOM-010-STPS-2014) y la fracción de diseño adoptada.",
                             source="NOM-010-STPS-2014", basis=BASIS_DATA))
        if has_ach and airflow_res["ACH"].Q < airflow_res["Dilución"].Q:
            out.append(Alert("ALTO", M_FLOW, "Caudal por ACH", "Las renovaciones por hora indicadas no alcanzan el "
                             "caudal de dilución requerido", airflow_res["ACH"].Q, "flow",
                             criterion=f"Q_ACH ≥ Q_dilución = {airflow_res['Dilución'].Q:.3f} m³/s",
                             consequence="Concentración en el recinto superior al objetivo.",
                             recommendation="Aumente el caudal o reduzca la generación residual con captura localizada.",
                             source="Balance de masa del contaminante", basis=BASIS_PHYSICS))
        if d.get("K", 1) == 1.0:
            out.append(Alert("MEDIO", M_FLOW, "Factor de mezcla K", "Se supone mezcla perfecta (K = 1)", 1.0,
                             criterion="K ≥ 1 según eficacia de mezcla", consequence="Subestima el caudal real necesario "
                             "si la distribución de aire no es ideal.", recommendation="Justifique K con la "
                             "distribución de inyección/extracción del recinto (ACGIH).",
                             source="ACGIH (ventilación por dilución)", basis=BASIS_REFERENCE))
    if "Térmico" in airflow_res:
        out.append(Alert("INFO", M_FLOW, "Balance térmico", "Caudal calculado con balance sensible simplificado",
                         airflow_res["Térmico"].Q, "flow", criterion="Hipótesis de mezcla completa, sin carga latente",
                         consequence="En naves altas con estratificación el caudal requerido puede ser menor; con "
                                     "fuentes radiantes la temperatura local puede exceder la de diseño.",
                         recommendation="Para naves con estratificación evalúe ventilación por desplazamiento o "
                                        "extracción en cubierta.", source="Balance de energía", basis=BASIS_HYPOTHESIS))
    return out, insufficient


# ---------------------------------------------------------------------------
# Campanas
# ---------------------------------------------------------------------------

def check_hoods(hoods, hood_res: dict, db, settings) -> list[Alert]:
    out: list[Alert] = []
    ranges = db.capture_ranges
    vmin_all = min(r["v_min_m_s"] for r in ranges)
    for h in hoods:
        r = hood_res.get(h.id)
        if r is None:
            continue
        for v in r.validity:
            out.append(Alert("MEDIO", M_HOOD, "Validez de la ecuación", v, item=h.id,
                             criterion="Rango de aplicación de las ecuaciones de DallaValle (ACGIH)",
                             consequence="El caudal calculado puede no producir la velocidad de captura supuesta.",
                             recommendation="Modifique geometría/distancia o use la ecuación del tipo de campana correcto.",
                             source="ACGIH, Industrial Ventilation Manual", basis=BASIS_REFERENCE))
        Vc = h.params.get("Vc")
        if h.type not in ("receiving",) and Vc is not None and Vc < vmin_all:
            out.append(Alert("ALTO", M_HOOD, "Velocidad de captura", "Velocidad de captura menor que el mínimo de los "
                             "rangos de referencia", Vc, "velocity", item=h.id,
                             criterion=f"Vc ≥ {vmin_all} m/s (rango más bajo de la tabla de captura)",
                             consequence="Captura deficiente; escape de contaminante hacia la zona de trabajo.",
                             recommendation="Aumente Vc según el tipo de liberación o acerque la campana.",
                             source="ACGIH, tabla de velocidades de captura (verificar edición)", basis=BASIS_REFERENCE))
        if h.cross_draft_m_s and Vc:
            ratio_max, src, basis, lvl = _crit(settings, "cross_draft_ratio_max")
            if h.cross_draft_m_s / Vc > ratio_max:
                out.append(Alert(lvl, M_HOOD, "Corrientes cruzadas", "Corriente de aire del local elevada frente a la "
                                 "velocidad de captura", h.cross_draft_m_s, "velocity", item=h.id,
                                 criterion=f"v_cruzada/Vc ≤ {ratio_max}",
                                 consequence="Las corrientes cruzadas desplazan el contaminante fuera de la zona de captura.",
                                 recommendation="Instale mamparas/bafles, reubique difusores o ventanas, aumente el "
                                                "encerramiento de la campana.", source=src, basis=_basis(basis)))
        if h.entry and h.entry.kind == "fh" and h.entry.Fh >= 0.9:
            out.append(Alert("BAJO", M_HOOD, "Pérdida de entrada", "Entrada de campana con coeficiente alto (extremo de "
                             "ducto liso u orificio)", h.entry.Fh, item=h.id, value_text="Fh",
                             criterion="Fh menor con brida o transición cónica",
                             consequence="Mayor presión estática de campana y mayor consumo del ventilador.",
                             recommendation="Considere brida o transición cónica/acampanada en la conexión.",
                             source="ACGIH (coeficientes de entrada)", basis=BASIS_REFERENCE))
        if h.type in ("slot", "slot_flanged") and (not h.entry or h.entry.kind != "slot"):
            out.append(Alert("MEDIO", M_HOOD, "Campana ranurada", "La pérdida de entrada no incluye la ranura",
                             item=h.id, criterion="Campanas compuestas: pérdida de ranura + entrada al ducto",
                             consequence="Se subestima la presión estática de campana.",
                             recommendation="Configure la entrada como compuesta (ranura + pleno) con el área de ranuras.",
                             source="ACGIH (campanas compuestas)", basis=BASIS_REFERENCE))
    return out


# ---------------------------------------------------------------------------
# Red y ductos
# ---------------------------------------------------------------------------

def transport_min_for(seg_class: dict | None, rho: float, settings) -> tuple[float, str]:
    if not seg_class:
        return 0.0, ""
    vmin = seg_class.get("v_min_m_s") or 0.0
    note = ""
    if vmin > 0 and settings.cval("transport_density_correction", True):
        df = rho / C.RHO_STD_AMCA
        if df < 1.0:
            vmin = vmin / math.sqrt(df)
            note = f" (corregida por densidad: V_min/√df, df = {df:.3f})"
    return vmin, note


def check_network(project, model, net_res, db, settings, hood_class: dict[str, str]) -> list[Alert]:
    out: list[Alert] = []
    if net_res is None:
        return out
    st = net_res.state
    over_pct, src_over, b_over, l_over = _crit(settings, "velocity_over_range_pct")
    default_cls = project.network_settings.contaminant_class
    clean_side = clean_side_segments(model)
    ok_count = 0
    # clase por tramo: la del ramal (campana aguas arriba) o la de la red
    for seg in model.segments:
        ev = st.seg_evals.get(seg.id)
        if ev is None:
            continue
        cls_id = seg.contaminant_class
        if not cls_id:
            ups = model.upstream_hoods(seg.from_node) if model.nodes[seg.from_node].kind != "fan" else []
            classes = {hood_class.get(h, default_cls) for h in ups}
            cls_id = _strictest(classes, db) if classes else default_cls
        if seg.id in clean_side and not seg.contaminant_class:
            cls_id = "clean_air"
        cls = db.transport_class(cls_id)
        vmin, note = transport_min_for(cls, ev.rho, settings)
        V = abs(ev.V)
        if cls and vmin > 0 and V < vmin:
            out.append(Alert("ALTO", M_DUCT, "Velocidad de transporte", f"Velocidad menor que la mínima de transporte "
                             f"({cls['name']}){note}", V, "velocity", item=seg.id,
                             criterion=f"V ≥ {vmin:.2f} m/s",
                             consequence="Sedimentación de partículas, obstrucción del ducto, pérdida de caudal en las "
                                         "campanas y, con polvos combustibles, riesgo de incendio/explosión.",
                             recommendation="Reduzca el diámetro del tramo (siguiente tamaño comercial inferior) o "
                                            "revise el caudal asignado.",
                             source="ACGIH — velocidades mínimas de transporte (verificar edición vigente)",
                             basis=BASIS_REFERENCE))
        elif cls and model.nodes[seg.to_node].kind == "outlet":
            ok_count += 1   # la chimenea se evalúa con los criterios de descarga
        elif cls:
            vr = cls.get("v_range_m_s") or [None, None]
            vmax = vr[1] if len(vr) > 1 else None
            if vmax and V > vmax * (1 + over_pct / 100):
                out.append(Alert(l_over if cls_id != "clean_air" else "BAJO", M_DUCT, "Velocidad elevada",
                                 f"Velocidad superior al rango de diseño de la clase '{cls['name']}'", V, "velocity",
                                 item=seg.id, criterion=f"V ≤ {vmax:.2f}·(1 + {over_pct:.0f} %) m/s",
                                 consequence="Mayor pérdida de presión (∝V²), ruido, abrasión y consumo energético.",
                                 recommendation="Evalúe el diámetro comercial inmediato superior verificando que se "
                                                "mantenga la velocidad mínima de transporte.",
                                 source=src_over, basis=_basis(b_over)))
            else:
                ok_count += 1
        if ev.regime == "transicional":
            out.append(Alert("MEDIO", M_LOSS, "Número de Reynolds", "Régimen transicional", ev.Re, "dimensionless",
                             item=seg.id, criterion="Re < 2300 o Re > 4000",
                             consequence="Factor de fricción incierto (se adoptó el valor conservador).",
                             recommendation="Revise el dimensionamiento; en ductos de aire normalmente Re ≫ 4000.",
                             source="Criterio clásico de régimen (Reynolds)", basis=BASIS_PHYSICS))
        if ev.regime == "turbulento" and not (0.006 <= ev.f <= 0.1):
            out.append(Alert("MEDIO", M_LOSS, "Factor de fricción", "Factor de Darcy fuera del rango del diagrama de "
                             "Moody", ev.f, item=seg.id, criterion="0.006 ≤ f ≤ 0.1",
                             consequence="Posible error de datos (rugosidad o diámetro).",
                             recommendation="Verifique rugosidad y dimensiones.", source="Diagrama de Moody",
                             basis=BASIS_PHYSICS))
        geom = seg.geometry
        if seg.shape == "rectangular":
            amax, src_a, b_a, l_a = _crit(settings, "rect_aspect_max")
            if geom.aspect > amax:
                out.append(Alert(l_a, M_DUCT, "Relación de aspecto", "Ducto rectangular con relación de aspecto alta",
                                 geom.aspect, item=seg.id, criterion=f"a/b ≤ {amax}",
                                 consequence="Más perímetro por unidad de área: mayor fricción, peso y costo.",
                                 recommendation="Use ducto circular o reduzca la relación de aspecto.",
                                 source=src_a, basis=_basis(b_a)))
            if cls and (cls.get("v_min_m_s") or 0) > 0:
                out.append(Alert("MEDIO", M_DUCT, "Ducto rectangular con partículas", "Transporte de partículas en ducto "
                                 "rectangular", item=seg.id, criterion="Preferir ducto circular para transporte de polvo",
                                 consequence="Acumulación en esquinas y zonas de baja velocidad.",
                                 recommendation="Use ducto circular en sistemas de captación de polvo.",
                                 source="ACGIH (práctica de diseño de ductos para polvo)", basis=BASIS_REFERENCE))
        mat = db.material(seg.material_id)
        if mat and mat.get("t_max_c") is not None and ev.t_c > mat["t_max_c"]:
            out.append(Alert("ALTO", M_DUCT, "Temperatura del material", f"Temperatura del aire superior al límite del "
                             f"material ({mat['name']})", ev.t_c, "temperature", item=seg.id,
                             criterion=f"t ≤ {mat['t_max_c']} °C", consequence="Degradación del material o del recubrimiento.",
                             recommendation="Seleccione un material apto para la temperatura o enfríe el aire.",
                             source=mat.get("source", ""), basis=BASIS_REFERENCE))
        # componentes dominantes
        share_max, src_s, b_s, l_s = _crit(settings, "fitting_loss_share_max_pct")
        total_fan = max(abs(st.FTP), 1e-9)
        for fe in ev.fittings:
            if fe.dp / total_fan * 100 > share_max:
                out.append(Alert(l_s, M_LOSS, "Pérdida local elevada", f"'{fe.name}' aporta "
                                 f"{fe.dp / total_fan * 100:.0f} % de la presión total del ventilador", fe.dp, "pressure",
                                 item=seg.id, criterion=f"aporte ≤ {share_max:.0f} %",
                                 consequence="Componente que domina el consumo energético.",
                                 recommendation="Revise la geometría (radio de codo, ángulo de unión, transición).",
                                 source=src_s, basis=_basis(b_s)))
            if fe.status not in ("fórmula verificable",):
                out.append(Alert("INFO", M_LOSS, "Coeficiente K por verificar", f"'{fe.name}': K = {fe.K:.3f} "
                                 f"({fe.status})", fe.K, item=seg.id, criterion="Coeficiente con fuente verificada",
                                 consequence="La pérdida local depende de un dato no verificado.",
                                 recommendation="Confirme K y su sección de referencia en la fuente indicada.",
                                 source=fe.source, basis=BASIS_DATA))
        for name, typ, dp in ev.equipment:
            if total_fan and dp / total_fan * 100 > 50:
                out.append(Alert("BAJO", M_LOSS, "Pérdida de equipo", f"{name} aporta {dp / total_fan * 100:.0f} % de la "
                                 "presión del ventilador", dp, "pressure", item=seg.id,
                                 criterion="Identificación de la contribución dominante",
                                 consequence="El consumo del sistema depende principalmente del equipo.",
                                 recommendation="Verifique la relación aire/tela o velocidad de cara del equipo con el "
                                                "fabricante; evalúe limpieza automática y monitoreo de ΔP.",
                                 source="Análisis de contribuciones", basis=BASIS_HYPOTHESIS))
    # cambios bruscos de sección sin transición
    for seg in model.segments:
        if model.nodes[seg.from_node].kind in ("hood",):
            continue
        ups = model.incoming(seg.from_node)
        if len(ups) != 1 or ups[0].equipment or seg.equipment:
            continue   # los equipos (colector, filtro) actúan como transición entre bridas
        a_up, a_dn = ups[0].geometry.area, seg.geometry.area
        ratio = max(a_up, a_dn) / min(a_up, a_dn)
        has_tr = any(f.fitting_id in ("sudden_expansion", "sudden_contraction", "diffuser", "reducer", "transition_user")
                     for f in seg.fittings + ups[0].fittings)
        if ratio > 1.5 and not has_tr and model.nodes[seg.from_node].kind != "fan":
            out.append(Alert("BAJO", M_LOSS, "Cambio de sección", "Cambio de sección sin accesorio de transición "
                             "modelado", ratio, item=seg.id, criterion="Modelar reducción/expansión cuando A₂/A₁ > 1.5",
                             consequence="Pérdida no contabilizada.", recommendation="Añada la transición con su K.",
                             source="Criterio del proyecto (hipótesis)", basis=BASIS_HYPOTHESIS))
    # balance
    for b in net_res.balance:
        if b.action.startswith("rediseñar"):
            sug = f" Diámetro sugerido: {b.suggested_D * 1000:.0f} mm (V = {b.suggested_D_velocity:.1f} m/s)." if b.suggested_D else ""
            out.append(Alert("ALTO", M_NET, "Ramal desbalanceado", f"Relación de presiones en {b.junction}: "
                             f"{b.ratio:.2f} (ramal {b.segment} frente a {b.governing_segment})", b.ratio, item=b.segment,
                             criterion=f"r ≤ 1 + {settings.cval('imbalance_flow_increase_max_pct', 20):.0f} % para "
                                       "corregir aumentando caudal",
                             consequence="En operación el ramal de menor resistencia tomará más caudal y el gobernante "
                                         "menos que el requerido.",
                             recommendation=f"Rediseñe el ramal (menor diámetro o más resistencia) o instale una "
                                            f"compuerta de balance (K ≈ {b.damper_K_required:.2f} en el tramo).{sug} "
                                            "No estrangule sin evaluar el aumento de presión y potencia.",
                             source=settings.crit("imbalance_flow_increase_max_pct")["source"], basis=BASIS_REFERENCE))
        elif b.action.startswith("aumento"):
            out.append(Alert("INFO", M_NET, "Equilibrado por diseño", f"Caudal del ramal {b.segment} aumentado "
                             f"{(b.scale - 1) * 100:.1f} % para igualar presiones en {b.junction}", b.Q_after, "flow",
                             item=b.segment, criterion="Corrección por igualación de presión total",
                             consequence="El caudal total del ventilador y el consumo aumentan respecto al requerido.",
                             recommendation="Aceptable si el exceso de caudal es tolerable; alternativamente reduzca el "
                                            "diámetro del ramal.", source="Método de equilibrado por diseño (ACGIH)",
                             basis=BASIS_REFERENCE))
        elif b.action.startswith("compuerta"):
            out.append(Alert("MEDIO", M_NET, "Compuerta de balance", f"Se requiere compuerta en {b.segment} "
                             f"(K = {b.damper_K_required:.2f})", b.damper_K_required, item=b.segment,
                             criterion="Equilibrado por compuertas",
                             consequence="Las compuertas pueden desajustarse o manipularse; aumentan la energía disipada.",
                             recommendation="Bloquee y marque la posición tras el balanceo en campo; prefiera "
                                            "equilibrado por diseño en sistemas de polvo.",
                             source="ACGIH (equilibrado por compuertas vs. por diseño)", basis=BASIS_REFERENCE))
    if not any(s.equipment for s in model.segments) and default_cls not in ("gases_vapors", "clean_air"):
        out.append(Alert("MEDIO", M_NET, "Equipo de control", "Sistema de partículas sin colector/filtro modelado",
                         criterion="Equipo de control de emisiones antes de la descarga",
                         consequence="Descarga de partículas a la atmósfera y posible incumplimiento ambiental.",
                         recommendation="Incluya el colector de polvo con su curva de pérdida (limpio y saturado).",
                         source="Práctica de diseño; normativa ambiental aplicable", basis=BASIS_REFERENCE))
    # filtros en estado limpio usados para diseño
    if project.network_settings.filter_state_design == "limpio" and any(
            e.model == "filter" for s in model.segments for e in s.equipment):
        out.append(Alert("ALTO", M_LOSS, "Estado del filtro de diseño", "El sistema se diseñó con el filtro limpio",
                         criterion="Diseñar con la pérdida final (filtro en condición de mantenimiento)",
                         consequence="Al ensuciarse el filtro el caudal caerá por debajo del requerido.",
                         recommendation="Diseñe con ΔP final y verifique la sobrecarga del motor con filtro limpio.",
                         source="Práctica de diseño (filtros de pérdida variable)", basis=BASIS_REFERENCE))
    # descarga
    path = model.discharge_path()
    if path:
        ev_out = st.seg_evals[path[-1].id]
        vmin, src_v, b_v, l_v = _crit(settings, "stack_exit_velocity_min_m_s")
        vnoise, src_n, b_n, l_n = _crit(settings, "stack_exit_velocity_noise_m_s")
        if ev_out.V < vmin:
            out.append(Alert(l_v, M_NET, "Velocidad de descarga", "Velocidad de salida en chimenea baja", ev_out.V,
                             "velocity", item=path[-1].id, criterion=f"V_salida ≥ {vmin:.2f} m/s",
                             consequence="Poca elevación del penacho; posible reingreso por tomas de aire cercanas.",
                             recommendation="Reduzca el diámetro de la chimenea o añada boquilla de descarga.",
                             source=src_v, basis=_basis(b_v)))
        elif ev_out.V > vnoise:
            out.append(Alert(l_n, M_NET, "Velocidad de descarga", "Velocidad de salida alta", ev_out.V, "velocity",
                             item=path[-1].id, criterion=f"V_salida ≤ {vnoise:.2f} m/s (ruido/energía)",
                             consequence="Ruido, vibración y pérdida de descarga elevada (∝V²).",
                             recommendation="Evalúe aumentar el diámetro de la chimenea.", source=src_n, basis=_basis(b_n)))
        h = model.outlet.stack_height_above_roof_m
        hmin, src_h, b_h, l_h = _crit(settings, "stack_height_min_m")
        if h is not None and h < hmin:
            out.append(Alert(l_h, M_NET, "Altura de chimenea", "Altura de descarga sobre cubierta menor que la referencia",
                             h, "length", item=model.outlet.id, criterion=f"h ≥ {hmin} m sobre la cubierta",
                             consequence="Exposición de trabajadores en cubierta y reingreso de contaminantes.",
                             recommendation="Aumente la altura de la chimenea y verifique distancias a tomas de aire "
                                            "(ASHRAE HVAC Applications, cap. de tomas y descargas).",
                             source=src_h, basis=_basis(b_h)))
        elif h is None:
            out.append(Alert("INFO", M_NET, "Altura de chimenea", "No se indicó la altura de descarga sobre cubierta",
                             criterion="Dato requerido para evaluar reingreso", recommendation="Indique la altura.",
                             source="ASHRAE HVAC Applications; ANSI/AIHA Z9.5", basis=BASIS_DATA))
        for s in path:
            e = st.seg_evals[s.id]
            if e.SP_end < -1.0 or e.SP_start < -1.0:
                out.append(Alert("MEDIO", M_LOSS, "Presión en descarga", "Presión estática negativa en el lado de "
                                 "descarga", min(e.SP_start, e.SP_end), "pressure", item=s.id,
                                 criterion="SP ≥ 0 aguas abajo del ventilador (salvo conversiones locales de VP)",
                                 consequence="Posible infiltración por juntas o efecto de un cambio de sección.",
                                 recommendation="Revise el área de descarga del ventilador y las transiciones.",
                                 source="Balance de energía (SP = TP − VP)", basis=BASIS_PHYSICS))
    if ok_count and not any(a.parameter in ("Velocidad de transporte", "Velocidad elevada") for a in out):
        out.append(Alert("CORRECTO", M_DUCT, "Velocidades de ducto", "Todas las velocidades dentro del rango de la clase "
                         "de contaminante", criterion="V_min ≤ V ≤ V_max", source="ACGIH (velocidades de transporte)",
                         basis=BASIS_REFERENCE))
    return out


def _is_collector(e) -> bool:
    return e.eq_type.startswith(("Colector", "Filtro", "Ciclón", "Lavador"))


def clean_side_segments(model) -> set[str]:
    """Tramos aguas abajo de un equipo de control (aire filtrado: sin requisito de transporte)."""
    out: set[str] = set()
    for seg in model.segments:
        if any(_is_collector(e) for e in seg.equipment):
            cur = seg.to_node
            while model.nodes[cur].kind != "outlet":
                nxt = model.outgoing(cur)[0]
                out.add(nxt.id)
                cur = nxt.to_node
    return out


def _has_collector(model) -> bool:
    return any(e.eq_type.startswith(("Colector", "Filtro", "Ciclón", "Lavador")) for s in model.segments for e in s.equipment)


def _strictest(class_ids: set, db) -> str:
    best, vbest = None, -1.0
    for cid in class_ids:
        c = db.transport_class(cid)
        v = (c or {}).get("v_min_m_s") or 0.0
        if v > vbest:
            best, vbest = cid, v
    return best


# ---------------------------------------------------------------------------
# Ventilador
# ---------------------------------------------------------------------------

def check_fan(fan_evals: dict, selected_id, net_design, op_net, settings, hood_q_req: dict) -> list[Alert]:
    out: list[Alert] = []
    if not fan_evals:
        out.append(Alert("INFO", M_FAN, "Curva del ventilador", "No se ha cargado ninguna curva de ventilador",
                         criterion="Curva del fabricante requerida para verificar el punto de operación",
                         consequence="No es posible verificar caudal real, estabilidad ni potencia.",
                         recommendation="Cargue la curva certificada del fabricante (CSV, Excel o captura manual).",
                         source="AMCA 210 / AMCA 211 (curvas certificadas)", basis=BASIS_DATA))
        return out
    fe = fan_evals.get(selected_id)
    if fe is None:
        out.append(Alert("INFO", M_FAN, "Selección", "No se ha seleccionado ventilador", basis=BASIS_DATA))
        return out
    fan = fe.adjusted
    curve = fan.curve
    if fe.error:
        out.append(Alert("CRÍTICO", M_FAN, "Curva del ventilador", fe.error, item=curve.id, basis=BASIS_PHYSICS,
                         recommendation="Corrija los datos de la curva.", source="Validación de datos"))
        return out
    if not curve.certified:
        out.append(Alert("MEDIO", M_FAN, "Curva no certificada", "La curva usada no está identificada como certificada",
                         item=curve.id, criterion="Curva certificada por el fabricante (p. ej. programa AMCA CRP)",
                         consequence="Incertidumbre en el punto de operación, potencia y eficiencia.",
                         recommendation="Solicite al fabricante la curva certificada a la densidad de operación.",
                         source="AMCA 210 / AMCA 211", basis=BASIS_REFERENCE))
    out.append(Alert("INFO", M_FAN, "Corrección por densidad", f"Curva corregida de ρ = {curve.rho_ref:.3f} a "
                     f"ρ = {fan.rho:.3f} kg/m³ y de {curve.rpm:.0f} a {fan.rpm:.0f} rpm", fan.rr, item=curve.id,
                     criterion="P ∝ ρ·N², Q ∝ N, W ∝ ρ·N³", source="Leyes de ventiladores (AMCA 99)", basis=BASIS_PHYSICS))
    op = fe.op
    if op is None:
        out.append(Alert("CRÍTICO", M_FAN, "Punto de operación", "La curva del ventilador no intersecta la curva del "
                         "sistema dentro de su dominio", item=curve.id,
                         criterion="Existencia de intersección curva ventilador / curva sistema",
                         consequence="El ventilador no puede entregar el caudal requerido contra la resistencia del sistema.",
                         recommendation="Seleccione otro ventilador, aumente la velocidad (si el fabricante lo permite) "
                                        "o reduzca la resistencia del sistema.",
                         source="Análisis curva ventilador–sistema (ASHRAE HVAC Systems and Equipment, cap. Fans)",
                         basis=BASIS_PHYSICS))
        return out
    if len(op.intersections) > 1:
        out.append(Alert("ALTO", M_FAN, "Múltiples puntos de operación", f"{len(op.intersections)} intersecciones con "
                         "la curva del sistema", item=curve.id, criterion="Intersección única",
                         consequence="Operación inestable (oscilación de caudal / bombeo).",
                         recommendation="Seleccione un ventilador cuya curva corte al sistema en la zona de pendiente "
                                        "negativa estable.", source="ASHRAE HVAC Systems and Equipment (cap. Fans)",
                         basis=BASIS_PHYSICS))
    if not op.in_domain:
        out.append(Alert("ALTO", M_FAN, "Extrapolación de curva", "El punto de operación está fuera de los datos del "
                         "fabricante", op.Q, "flow", item=curve.id, criterion="Q_min ≤ Q ≤ Q_max de la curva",
                         consequence="Resultado no respaldado por datos de ensayo.",
                         recommendation="Obtenga la curva extendida o seleccione otro ventilador.",
                         source="AMCA 210 (curvas de ensayo)", basis=BASIS_REFERENCE))
    stall, src_st, b_st, l_st = _crit(settings, "fan_stall_margin_pct")
    if op.on_positive_slope or op.Q < op.q_peak * (1 + stall / 100):
        out.append(Alert(l_st if not op.on_positive_slope else "ALTO", M_FAN, "Zona de inestabilidad",
                         "Punto de operación en o cerca de la zona de pendiente positiva (pérdida/bombeo)", op.Q, "flow",
                         item=curve.id, criterion=f"Q ≥ Q_presión máx·(1 + {stall:.0f} %) = "
                                                  f"{op.q_peak * (1 + stall / 100):.3f} m³/s",
                         consequence="Pulsaciones, ruido, vibración y caudal inestable.",
                         recommendation="Seleccione un ventilador más pequeño o con mayor velocidad para operar a la "
                                        "derecha del pico de presión.", source=src_st, basis=_basis(b_st)))
    if op.in_manufacturer_range is False:
        out.append(Alert("ALTO", M_FAN, "Rango del fabricante", "Operación fuera del rango recomendado por el fabricante",
                         op.Q, "flow", item=curve.id, criterion="Rango recomendado del catálogo",
                         consequence="Eficiencia baja, ruido o inestabilidad.", recommendation="Cambie la selección.",
                         source="Datos del fabricante", basis=BASIS_REFERENCE))
    elif op.in_manufacturer_range is None and op.eta_ratio is not None:
        rmin, src_r, b_r, l_r = _crit(settings, "fan_eta_ratio_min")
        if op.eta_ratio < rmin:
            out.append(Alert(l_r, M_FAN, "Distancia al BEP", f"Eficiencia en operación = {op.eta_ratio * 100:.0f} % "
                             "de la máxima", op.eta_ratio, item=curve.id, criterion=f"η/η_máx ≥ {rmin}",
                             consequence="Mayor consumo energético y posible ruido.",
                             recommendation="Evalúe otro tamaño/velocidad de ventilador más cercano al BEP.",
                             source=src_r, basis=_basis(b_r)))
        else:
            out.append(Alert("CORRECTO", M_FAN, "Distancia al BEP", "Operación cercana a la máxima eficiencia",
                             op.eta_ratio, item=curve.id, criterion=f"η/η_máx ≥ {rmin}", source=src_r, basis=_basis(b_r)))
    if op.q_bep is None:
        out.append(Alert("INFO", M_FAN, "BEP", "La curva no tiene datos de potencia ni eficiencia: no se identifica el BEP",
                         item=curve.id, recommendation="Incluya la curva de potencia absorbida.", basis=BASIS_DATA))
    low, src_l, b_l, l_l = _crit(settings, "fan_low_efficiency")
    if op.eta_total is not None and op.eta_total < low:
        out.append(Alert(l_l, M_FAN, "Eficiencia baja", "Eficiencia total del ventilador baja", op.eta_total, item=curve.id,
                         criterion=f"η_t ≥ {low}", consequence="Consumo energético elevado.",
                         recommendation="Compare con ventiladores de mayor eficiencia (álabes inclinados hacia atrás o "
                                        "aerodinámicos en el lado limpio).", source=src_l, basis=_basis(b_l)))
    if curve.max_rpm and fan.rpm > curve.max_rpm:
        out.append(Alert("CRÍTICO", M_FAN, "Velocidad máxima", "RPM de operación superiores al máximo del fabricante",
                         fan.rpm, "speed", item=curve.id, criterion=f"N ≤ {curve.max_rpm:.0f} rpm",
                         consequence="Riesgo mecánico (esfuerzos en el rodete, rodamientos).",
                         recommendation="Seleccione un ventilador de mayor tamaño o clase de construcción.",
                         source="Límite del fabricante", basis=BASIS_REFERENCE))
    if fe.rpm_required and curve.max_rpm and fe.rpm_required > curve.max_rpm:
        out.append(Alert("ALTO", M_FAN, "Velocidad requerida", "Para alcanzar el punto de diseño se requieren más rpm que "
                         "las permitidas", fe.rpm_required, "speed", item=curve.id,
                         criterion=f"N_req ≤ {curve.max_rpm:.0f} rpm", consequence="El punto de diseño no es alcanzable.",
                         recommendation="Seleccione un ventilador de mayor tamaño.", source="Leyes de semejanza",
                         basis=BASIS_PHYSICS))
    # caudales entregados
    tol, src_t, b_t, l_t = _crit(settings, "flow_deficit_tolerance_pct")
    if op_net is not None:
        defs = []
        for h, qreq in hood_q_req.items():
            q = op_net.hood_q_final.get(h)
            if q is not None and q < qreq * (1 - tol / 100):
                defs.append((h, q, qreq))
        for h, q, qreq in defs:
            out.append(Alert(l_t, M_FAN, "Caudal insuficiente", f"La campana {h} recibe {q / qreq * 100:.0f} % del caudal "
                             "requerido en el punto de operación", q, "flow", item=h,
                             criterion=f"Q ≥ Q_req·(1 − {tol:.0f} %) = {qreq * (1 - tol / 100):.3f} m³/s",
                             consequence="Velocidad de captura menor que la de diseño: escape de contaminante.",
                             recommendation="Aumente la velocidad del ventilador, reduzca la resistencia del ramal "
                                            "o rebalancee la red.", source=src_t, basis=_basis(b_t)))
        if not defs and hood_q_req:
            out.append(Alert("CORRECTO", M_FAN, "Caudal en campanas", "Todas las campanas reciben al menos el caudal "
                             "requerido (dentro de la tolerancia)", criterion=f"déficit ≤ {tol:.0f} %",
                             source=src_t, basis=_basis(b_t)))
        if not op_net.converged:
            out.append(Alert("ALTO", M_NET, "Convergencia", "La solución de operación de la red no convergió",
                             op_net.residual_pa, "pressure", criterion="residuo < 0.05 Pa",
                             consequence="Distribución de caudales no confiable.",
                             recommendation="Revise datos de la red y la curva del ventilador.",
                             source="Solucionador numérico", basis=BASIS_PHYSICS))
    if net_design is not None and op.Q > net_design.state.Q_fan * 1.25:
        out.append(Alert("BAJO", M_FAN, "Exceso de caudal", "El ventilador entrega más de 25 % sobre el caudal de diseño",
                         op.Q, "flow", item=curve.id, criterion="Q_op ≈ Q_diseño",
                         consequence="Consumo energético innecesario y velocidades de captura mayores a las necesarias.",
                         recommendation="Reduzca la velocidad (poleas o variador) a la requerida.",
                         source="Análisis energético", basis=BASIS_HYPOTHESIS))
    out.append(Alert("INFO", M_FAN, "Efecto del sistema", "Las curvas de catálogo se obtienen con conexiones ideales",
                     item=curve.id, criterion="Considerar el efecto del sistema en entrada y descarga",
                     consequence="Codos o transiciones cercanas al ventilador reducen su desempeño real.",
                     recommendation="Prevea tramos rectos en entrada/descarga o sume el efecto del sistema (AMCA 201).",
                     source="AMCA Publication 201", basis=BASIS_REFERENCE))
    return out


# ---------------------------------------------------------------------------
# Potencia
# ---------------------------------------------------------------------------

def check_power(pinp, pres, settings, overload_W: float | None, hot_ratio: float | None) -> list[Alert]:
    out: list[Alert] = []
    if pres is None:
        return out
    if pres.P_elec < pres.W_motor_out:
        out.append(Alert("CRÍTICO", M_POW, "Potencia eléctrica", "La potencia eléctrica resulta menor que la mecánica",
                         pres.P_elec, "power", criterion="P_elec ≥ W_motor", basis=BASIS_PHYSICS,
                         recommendation="Revise las eficiencias.", source="Conservación de la energía"))
    if pinp.drive_type.lower().startswith("banda") and pinp.eta_drive >= 0.999:
        out.append(Alert("MEDIO", M_POW, "Pérdidas de transmisión", "Transmisión por bandas con eficiencia 1.0",
                         pinp.eta_drive, criterion="η_bandas < 1", consequence="Se omiten las pérdidas de la transmisión.",
                         recommendation="Use la pérdida de transmisión del fabricante o de AMCA 203.",
                         source="AMCA 203", basis=BASIS_REFERENCE))
    motor = pres.motor_selected or pres.motor_nominal
    if motor:
        if pres.W_motor_out > motor * max(pres.service_factor, 1.0):
            out.append(Alert("CRÍTICO", M_POW, "Motor", "Potencia requerida mayor que la capacidad del motor incluso con "
                             "factor de servicio", pres.W_motor_out, "power",
                             criterion=f"W_motor ≤ P_nom·FS = {motor * pres.service_factor / 1000:.2f} kW",
                             consequence="Sobrecalentamiento y disparo de protecciones; daño del motor.",
                             recommendation="Seleccione un motor de mayor potencia.", source="Placa del motor (NEMA MG 1 / IEC 60034)",
                             basis=BASIS_REFERENCE))
        elif pres.W_motor_out > motor:
            out.append(Alert("ALTO", M_POW, "Motor", "El motor operaría dentro del factor de servicio",
                             pres.W_motor_out, "power", criterion=f"W_motor ≤ P_nom = {motor / 1000:.2f} kW",
                             consequence="Vida útil reducida; el factor de servicio no es un margen de diseño.",
                             recommendation="Seleccione el siguiente motor normalizado.", source="NEMA MG 1 (factor de servicio)",
                             basis=BASIS_REFERENCE))
        else:
            out.append(Alert("CORRECTO", M_POW, "Motor", f"Carga del motor {pres.W_motor_out / motor * 100:.0f} % de la nominal",
                             pres.W_motor_out, "power", criterion="W_motor ≤ P_nom", basis=BASIS_PHYSICS))
        if overload_W and overload_W > motor:
            out.append(Alert("MEDIO", M_POW, "Sobrecarga posible", "Con filtro limpio o compuertas abiertas la potencia "
                             "absorbida supera la nominal del motor", overload_W, "power",
                             criterion=f"W_máx ≤ P_nom = {motor / 1000:.2f} kW",
                             consequence="Disparo por sobrecarga en arranque o tras limpieza del filtro.",
                             recommendation="Verifique el motor en la condición de menor resistencia o use variador/control "
                                            "de presión.", source="Análisis de condición de filtro limpio", basis=BASIS_PHYSICS))
        if pres.motor_selected and pres.motor_nominal and pres.motor_selected > pres.motor_nominal * 1.6:
            out.append(Alert("BAJO", M_POW, "Sobredimensionamiento", "Motor seleccionado muy superior al requerido",
                             pres.motor_selected, "power", criterion="Evitar sobredimensionamientos innecesarios",
                             consequence="Menor eficiencia y factor de potencia a carga parcial; mayor costo.",
                             recommendation="Use el motor normalizado requerido.", source="Criterio energético",
                             basis=BASIS_HYPOTHESIS))
    if hot_ratio and hot_ratio > 1.1:
        out.append(Alert("MEDIO", M_POW, "Arranque en frío", f"El aire frío es {hot_ratio:.2f} veces más denso que el de "
                         "operación", hot_ratio, criterion="Verificar potencia a densidad de arranque",
                         consequence="Sobrecarga del motor en arranque con aire frío.",
                         recommendation="Verifique la potencia a la densidad fría o use arranque con compuerta cerrada/variador.",
                         source="Leyes de ventiladores (W ∝ ρ)", basis=BASIS_PHYSICS))
    if pres.warnings:
        for w in pres.warnings:
            out.append(Alert("INFO", M_POW, "Nota de cálculo", w, basis=BASIS_DATA))
    return out
