"""Gráficos técnicos generados con Matplotlib a partir de los resultados reales.

Todas las funciones devuelven ``matplotlib.figure.Figure`` (sin pyplot, apto para
Qt y para exportar PNG al reporte). Los datos se convierten al sistema de
unidades seleccionado. Cada figura registra series para el tooltip de la
interfaz en ``fig._hover`` (lista de (eje, x, y, etiquetas)).

Criterios de diseño: marcas finas (líneas de 2 px), rejilla sólida y tenue,
una sola escala vertical por gráfico (nunca doble eje), leyenda con ≥ 2 series
y etiquetas directas selectivas; el texto usa tintas neutras, el color solo
identifica la serie. Paleta categórica validada (azul, naranja, aqua) y colores
de estado reservados para condiciones bien/mal, siempre con etiqueta.
"""
from __future__ import annotations

import math

import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Rectangle, Polygon, FancyArrowPatch, FancyBboxPatch

from core.units import to_display, display_unit, format_number

# --- paleta (instancia de referencia validada) ---
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
BASE = "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"
S1_LIGHT = "#cde2fb"
GOOD, WARN, SERIOUS, CRIT = "#0ca30c", "#fab219", "#ec835a", "#d03b3b"
FONT = "DejaVu Sans"


def _fig(w=8.0, h=4.6) -> Figure:
    fig = Figure(figsize=(w, h), dpi=110, facecolor=SURFACE)
    fig._hover = []
    return fig


def _style(ax, xlabel="", ylabel="", title="", subtitle=""):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(BASE)
        ax.spines[side].set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=8, length=3, width=0.6)
    ax.grid(True, color=GRID, linewidth=0.7, linestyle="-")
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=INK2, fontsize=9, fontname=FONT)
    if ylabel:
        ax.set_ylabel(ylabel, color=INK2, fontsize=9, fontname=FONT)
    if title:
        ax.set_title(title, loc="left", color=INK, fontsize=11, fontweight="bold", fontname=FONT, pad=16 if subtitle else 8)
    if subtitle:
        ax.text(0, 1.015, subtitle, transform=ax.transAxes, color=INK2, fontsize=8.5, va="bottom")


def _legend(ax, **kw):
    lg = ax.legend(frameon=False, fontsize=8, labelcolor=INK2, **kw)
    return lg


def _u(v, q, system):
    return to_display(v, q, system)


def _tick_fmt(ax, axis="y"):
    from matplotlib.ticker import FuncFormatter
    f = FuncFormatter(lambda v, _: "0" if v == 0 else (f"{v:,.0f}" if abs(v) >= 100 else (f"{v:,.1f}" if abs(v) >= 1 else f"{v:,.2f}")))
    (ax.yaxis if axis == "y" else ax.xaxis).set_major_formatter(f)


# ---------------------------------------------------------------------------
# Disposición de la red (compartida por los gráficos 1 y 7)
# ---------------------------------------------------------------------------

def _leaf_order(model) -> list[str]:
    order: list[str] = []

    def visit(nid):
        inc = model.incoming(nid)
        if not inc:
            order.append(nid)
            return
        for s in inc:
            visit(s.from_node)

    visit(model.fan.id)
    return order


def tree_layout(model) -> dict[str, tuple[float, float]]:
    """x: profundidad desde las campanas hacia el ventilador; y: orden de hojas."""
    leaves = _leaf_order(model)
    ypos = {h: float(len(leaves) - 1 - i) for i, h in enumerate(leaves)}
    depth = {nid: model.depth(nid) for nid in model.nodes if model.nodes[nid].kind != "outlet"}
    maxd = max(depth.values()) if depth else 1
    pos: dict[str, tuple[float, float]] = {}

    def y_of(nid):
        if nid in ypos:
            return ypos[nid]
        ys = [y_of(s.from_node) for s in model.incoming(nid)]
        ypos[nid] = float(np.mean(ys)) if ys else 0.0
        return ypos[nid]

    for nid, nd in model.nodes.items():
        if nd.kind == "outlet":
            continue
        pos[nid] = (float(maxd - depth[nid]), y_of(nid))
    fx, fy = pos[model.fan.id]
    x = fx
    for s in model.discharge_path():
        x += 1.0
        pos[s.to_node] = (x, fy)
    return pos


# ---------------------------------------------------------------------------
# Gráfico 1 — Esquema del sistema de ventilación industrial
# ---------------------------------------------------------------------------

def plot_system_schematic(project, results, system="SI") -> Figure:
    fig = _fig(9.5, 4.8)
    ax = fig.add_subplot(111)
    ax.set_facecolor(SURFACE)
    ax.set_axis_off()
    model = results.model
    nr = results.network_design
    if model is None or nr is None:
        ax.text(0.5, 0.5, "Defina y calcule la red para ver el esquema", ha="center", va="center", color=MUTED)
        return fig
    leaves = _leaf_order(model)
    xh = {h: i * 2.0 for i, h in enumerate(leaves)}
    xs = {}

    def x_of(nid):
        if nid in xh:
            return xh[nid]
        if nid in xs:
            return xs[nid]
        xs[nid] = max(x_of(s.from_node) for s in model.incoming(nid))
        return xs[nid]

    for nid in model.suction_order():
        x_of(nid)
    # nodos de un solo ramal aguas abajo de la última unión se desplazan a la derecha
    last_x = max(xh.values()) if xh else 0
    chain = []
    cur = model.fan.id
    while True:
        inc = model.incoming(cur)
        if len(inc) == 1 and model.nodes[inc[0].from_node].kind not in ("hood",) and len(model.incoming(inc[0].from_node)) == 1:
            chain.insert(0, inc[0].from_node)
            cur = inc[0].from_node
        else:
            break
    off = 2.8
    for nid in chain + [model.fan.id]:
        xs[nid] = last_x + off
        off += 1.8
    y_floor, y_hood, y_main, y_roof = 0.0, 1.0, 4.2, 5.4
    x_wall = last_x + 1.1
    # nave
    ax.add_patch(Polygon([[-1.2, y_floor], [x_wall, y_floor], [x_wall, y_roof], [x_wall / 2 - 0.1, y_roof + 0.8],
                          [-1.2, y_roof]], closed=True, fill=True, facecolor="#f4f3f0", edgecolor=BASE, lw=1.2))
    ax.plot([-1.6, x_wall + 7], [y_floor, y_floor], color=INK2, lw=1.2)
    ax.text(-1.0, y_roof - 0.35, "Nave industrial", color=INK2, fontsize=9)
    st = nr.state
    ev = st.seg_evals
    q_u, v_u = display_unit("flow", system), display_unit("velocity", system)
    duct_w = 3.0
    # campanas y ramales
    for h in leaves:
        x = xh[h]
        ax.add_patch(Polygon([[x - 0.45, y_hood], [x + 0.45, y_hood], [x + 0.15, y_hood + 0.45], [x - 0.15, y_hood + 0.45]],
                             closed=True, facecolor=S1_LIGHT, edgecolor=S1, lw=1.2))
        ax.add_patch(Rectangle((x - 0.35, y_floor), 0.7, y_hood - 0.15 - y_floor, facecolor="#e9e8e3", edgecolor=BASE, lw=0.8))
        seg = model.outgoing(h)[0]
        nd = model.nodes[h]
        hood = project.hood(nd.hood_id) if nd.hood_id else None
        name = hood.name if hood else (nd.label or h)
        import textwrap
        ax.text(x, y_floor - 0.3, f"{h}\n" + "\n".join(textwrap.wrap(name, 16)), ha="center", va="top", fontsize=7,
                color=INK2)
        e = ev[seg.id]
        ax.plot([x, x], [y_hood + 0.45, y_main], color=INK2, lw=duct_w, solid_capstyle="butt")
        ax.text(x + 0.12, (y_hood + y_main) / 2, f"{seg.id}\n{format_number(_u(e.Q, 'flow', system), 3)} {q_u}\n"
                f"{format_number(_u(e.V, 'velocity', system), 3)} {v_u}", fontsize=6.8, color=INK2, va="center")
    # principal
    for s in model.segments:
        u, d = model.nodes[s.from_node], model.nodes[s.to_node]
        if u.kind == "hood" or d.kind == "outlet" or u.kind == "fan":
            if u.kind == "hood":
                xu, xd = xh[s.from_node], xs.get(s.to_node, xh.get(s.to_node))
                if xd is not None and xd != xu:
                    ax.plot([xu, xd], [y_main, y_main], color=INK2, lw=duct_w + 1, solid_capstyle="butt")
            continue
        xu, xd = xs.get(s.from_node), xs.get(s.to_node)
        if xu is None or xd is None:
            continue
        ax.plot([xu, xd], [y_main, y_main], color=INK2, lw=duct_w + 1.5, solid_capstyle="butt")
        e = ev[s.id]
        ax.text((xu + xd) / 2, y_main + 0.18, f"{s.id}\n{format_number(_u(e.Q, 'flow', system), 3)} {q_u}\n"
                f"{format_number(_u(e.V, 'velocity', system), 3)} {v_u}", ha="center", va="bottom", fontsize=6.6,
                color=INK2, linespacing=1.1)
        if any(eq for eq in s.equipment):
            xm = xd - 1.0
            ax.add_patch(FancyBboxPatch((xm - 0.45, y_main - 1.9), 0.9, 1.9, boxstyle="round,pad=0.02",
                                        facecolor="#eeeeea", edgecolor=INK2, lw=1.0))
            ax.add_patch(Polygon([[xm - 0.45, y_main - 1.9], [xm + 0.45, y_main - 1.9], [xm, y_main - 2.5]],
                                 closed=True, facecolor="#e2e1dc", edgecolor=INK2, lw=1.0))
            ax.text(xm, y_main - 0.95, s.equipment[0].name.replace(" ", "\n", 1), ha="center", va="center", fontsize=6.6,
                    color=INK)
    for nid in xs:
        if model.nodes[nid].kind == "junction" and len(model.incoming(nid)) > 1:
            ax.add_patch(Circle((xs[nid], y_main), 0.09, facecolor=INK, edgecolor=SURFACE, lw=1.5, zorder=5))
            ax.text(xs[nid] - 0.12, y_main - 0.18, nid, ha="right", va="top", fontsize=7, color=MUTED)
    # ventilador y chimenea
    xf = xs[model.fan.id]
    ax.add_patch(Circle((xf, y_main - 0.2), 0.45, facecolor="#ffffff", edgecolor=INK, lw=1.4, zorder=4))
    for k in range(6):
        a = k * math.pi / 3
        ax.plot([xf, xf + 0.38 * math.cos(a)], [y_main - 0.2, y_main - 0.2 + 0.38 * math.sin(a)], color=INK2, lw=1, zorder=5)
    ax.text(xf, y_main - 0.95, "Ventilador", ha="center", fontsize=7.5, color=INK)
    fe = results.selected_fan
    if fe and fe.op:
        ax.text(xf, y_main - 1.3, f"{format_number(_u(fe.op.Q, 'flow', system), 3)} {q_u}\n"
                f"FTP {format_number(_u(fe.op.FTP, 'pressure', system), 4)} {display_unit('pressure', system)}",
                ha="center", va="top", fontsize=6.8, color=INK2)
    xo = xf + 1.4
    top = y_roof + 2.6
    ax.plot([xf + 0.45, xo, xo], [y_main - 0.2, y_main - 0.2, top], color=INK2, lw=duct_w + 1.5, solid_capstyle="butt")
    ax.add_patch(FancyArrowPatch((xo, top), (xo, top + 0.9), arrowstyle="-|>", mutation_scale=14, color=INK2, lw=1.2))
    dpath = model.discharge_path()
    eo = ev[dpath[-1].id]
    ax.text(xo + 0.2, top + 0.2, f"Descarga\n{format_number(_u(eo.V, 'velocity', system), 3)} {v_u}", fontsize=7, color=INK2)
    # flecha de sentido del flujo
    ax.add_patch(FancyArrowPatch((-1.0, y_roof - 0.75), (0.3, y_roof - 0.75),
                                 arrowstyle="-|>", mutation_scale=12, color=MUTED, lw=1))
    ax.text(0.45, y_roof - 0.78, "sentido del flujo", fontsize=7, color=MUTED, va="center")
    ax.set_xlim(-1.8, xo + 2.2)
    ax.set_ylim(-1.4, top + 1.2)
    ax.set_aspect("equal")
    ax.set_title("Gráfico 1 — Esquema del sistema de ventilación", loc="left", color=INK, fontsize=11, fontweight="bold")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Gráfico 2 — Geometría de ductos
# ---------------------------------------------------------------------------

def plot_duct_geometry(D_m: float | None, a_m: float | None, b_m: float | None, system="SI", title_extra="") -> Figure:
    fig = _fig(8.0, 3.8)
    lu = display_unit("small_length", system)
    au = display_unit("area", system)
    items = []
    if D_m:
        items.append(("circ", D_m))
    if a_m and b_m:
        items.append(("rect", (a_m, b_m)))
    if not items:
        ax = fig.add_subplot(111)
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Sin geometría", ha="center", color=MUTED)
        return fig
    for i, (kind, g) in enumerate(items):
        ax = fig.add_subplot(1, len(items), i + 1)
        ax.set_axis_off()
        ax.set_aspect("equal")
        if kind == "circ":
            D = g
            A = math.pi * D * D / 4
            ax.add_patch(Circle((0, 0), D / 2, facecolor=S1_LIGHT, edgecolor=S1, lw=2))
            ax.annotate("", xy=(-D / 2, -D * 0.68), xytext=(D / 2, -D * 0.68),
                        arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.9))
            ax.text(0, -D * 0.78, f"D = {format_number(_u(D, 'small_length', system), 4)} {lu}", ha="center", va="top",
                    fontsize=8.5, color=INK)
            ax.text(0, 0.06 * D, f"A = {format_number(_u(A, 'area', system), 4)} {au}", ha="center", fontsize=8.5, color=INK)
            ax.text(0, -0.1 * D, f"Dh = D = {format_number(_u(D, 'small_length', system), 4)} {lu}", ha="center",
                    fontsize=8, color=INK2)
            ax.set_xlim(-D * 0.8, D * 0.8)
            ax.set_ylim(-D * 1.05, D * 0.75)
            ax.set_title("Sección circular", fontsize=10, color=INK, loc="left")
        else:
            a, b = g
            A = a * b
            Dh = 2 * a * b / (a + b)
            De = 1.30 * (a * b) ** 0.625 / (a + b) ** 0.25
            ax.add_patch(Rectangle((-a / 2, -b / 2), a, b, facecolor=S1_LIGHT, edgecolor=S1, lw=2))
            m = max(a, b)
            ax.annotate("", xy=(-a / 2, -b / 2 - 0.12 * m), xytext=(a / 2, -b / 2 - 0.12 * m),
                        arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.9))
            ax.text(0, -b / 2 - 0.17 * m, f"a = {format_number(_u(a, 'small_length', system), 4)} {lu}", ha="center",
                    va="top", fontsize=8.5, color=INK)
            ax.annotate("", xy=(a / 2 + 0.1 * m, -b / 2), xytext=(a / 2 + 0.1 * m, b / 2),
                        arrowprops=dict(arrowstyle="<->", color=INK2, lw=0.9))
            ax.text(a / 2 + 0.14 * m, 0, f"b = {format_number(_u(b, 'small_length', system), 4)} {lu}", va="center",
                    fontsize=8.5, color=INK)
            ax.text(0, 0.08 * b, f"A = {format_number(_u(A, 'area', system), 4)} {au}", ha="center", fontsize=8.5, color=INK)
            ax.text(0, -0.12 * b, f"Dh = {format_number(_u(Dh, 'small_length', system), 4)} {lu}\n"
                    f"De = {format_number(_u(De, 'small_length', system), 4)} {lu}", ha="center", va="top", fontsize=8,
                    color=INK2)
            ax.set_xlim(-a * 0.75 - 0.05 * m, a * 0.75 + 0.6 * m)
            ax.set_ylim(-b / 2 - 0.45 * m, b / 2 + 0.2 * m)
            ax.set_title("Sección rectangular", fontsize=10, color=INK, loc="left")
    fig.suptitle("Gráfico 2 — Geometría de ductos" + (f" ({title_extra})" if title_extra else ""), x=0.02, ha="left",
                 fontsize=11, fontweight="bold", color=INK)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Gráfico 3 — Perfil de velocidad por tramo
# ---------------------------------------------------------------------------

def plot_velocity_profile(results, db, settings, project, system="SI") -> Figure:
    from validation.engineering_checks import transport_min_for, clean_side_segments, _strictest
    fig = _fig(8.6, 4.2)
    ax = fig.add_subplot(111)
    nr, model = results.network_design, results.model
    vu = display_unit("velocity", system)
    if nr is None:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Sin resultados de red", ha="center", color=MUTED)
        return fig
    ids = [s.id for s in model.segments]
    V = [abs(nr.state.seg_evals[i].V) for i in ids]
    clean = clean_side_segments(model)
    hood_cls = {nd.id: (project.hood(nd.hood_id).contaminant_class if nd.hood_id and project.hood(nd.hood_id) else None)
                for nd in model.nodes_of_kind("hood")}
    vmins = []
    for s in model.segments:
        ev = nr.state.seg_evals[s.id]
        if s.id in clean or model.nodes[s.to_node].kind == "outlet":
            vmins.append(0.0)
            continue
        cls_id = s.contaminant_class
        if not cls_id:
            ups = model.upstream_hoods(s.from_node)
            cls_id = _strictest({hood_cls.get(h) or project.network_settings.contaminant_class for h in ups}, db)
        vmins.append(transport_min_for(db.transport_class(cls_id), ev.rho, settings)[0])
    x = np.arange(len(ids))
    Vd = [_u(v, "velocity", system) for v in V]
    Vm = [_u(v, "velocity", system) for v in vmins]
    colors = [CRIT if (vm > 0 and v < vm) else S1 for v, vm in zip(V, vmins)]
    bars = ax.bar(x, Vd, width=0.55, color=colors, edgecolor=SURFACE, linewidth=2, label="Velocidad del tramo", zorder=3)
    shown = False
    for xi, vm in zip(x, Vm):
        if vm > 0:
            ax.plot([xi - 0.36, xi + 0.36], [vm, vm], color=INK, lw=2, solid_capstyle="butt", zorder=4,
                    label="Velocidad mínima de transporte (corregida por densidad)" if not shown else None)
            shown = True
    for xi, v, vm in zip(x, Vd, Vm):
        if vm > 0 and v < vm:
            ax.text(xi, v + 0.3, "▼ bajo mín.", ha="center", fontsize=7, color=INK)
    ax.set_xticks(x, ids)
    low = any(vm > 0 and v < vm for v, vm in zip(V, vmins))
    for xi, s, vm in zip(x, model.segments, vmins):
        if vm == 0:
            tag = "chimenea" if model.nodes[s.to_node].kind == "outlet" else ("lado limpio" if s.id in clean else "sin mínimo")
            ax.text(xi, _u(abs(nr.state.seg_evals[s.id].V), "velocity", system) + 0.3, tag, ha="center", fontsize=7,
                    color=MUTED)
    _style(ax, "Tramo", f"Velocidad [{vu}]", "Gráfico 3 — Perfil de velocidad por tramo",
           "Rojo con ▼: tramo por debajo de la velocidad mínima de transporte" if low else
           "Todas las velocidades superan la mínima de transporte de su clase de contaminante")
    _legend(ax, loc="upper left", bbox_to_anchor=(0, -0.13), ncol=2)
    fig._hover.append(("bar", ax, list(x), Vd, [f"{i}: {format_number(v, 4)} {vu}" for i, v in zip(ids, Vd)]))
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Gráfico 4 — Distribución de presión a lo largo del camino crítico
# ---------------------------------------------------------------------------

def pressure_profile(results):
    nr, model = results.network_design, results.model
    st = nr.state
    xs, tp, sp, vp, lbl = [0.0], [0.0], [0.0], [0.0], ["Atmósfera"]
    L = 0.0
    for sid in nr.critical_path:
        ev = st.seg_evals[sid]
        seg = model.seg(sid)
        xs.append(L)
        tp.append(ev.TP_start - ev.dp_entry if model.nodes[seg.from_node].kind == "hood" else ev.TP_start)
        sp.append(tp[-1] - ev.VP)
        vp.append(ev.VP)
        lbl.append(f"Inicio {sid}")
        L += max(seg.length, 0.5)
        if ev.dp_equipment:
            xs.append(L)
            tp.append(ev.TP_end + ev.dp_equipment)
            sp.append(tp[-1] - ev.VP)
            vp.append(ev.VP)
            lbl.append(f"{sid} antes del equipo")
        xs.append(L)
        tp.append(ev.TP_end)
        sp.append(ev.SP_end)
        vp.append(ev.VP)
        lbl.append(f"Fin {sid}")
        if model.nodes[seg.to_node].kind == "outlet":
            xs.append(L + 0.8)
            tp.append(0.0)
            sp.append(0.0)
            vp.append(0.0)
            lbl.append("Descarga (atmósfera)")
    return xs, tp, sp, vp, lbl


def plot_pressure_distribution(results, system="SI") -> Figure:
    fig = _fig(8.8, 4.6)
    ax = fig.add_subplot(111)
    nr = results.network_design
    pu = display_unit("pressure", system)
    lu = display_unit("length", system)
    if nr is None:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Sin resultados de red", ha="center", color=MUTED)
        return fig
    xs, tp, sp, vp, lbl = pressure_profile(results)
    X = [_u(x, "length", system) for x in xs]
    TP = [_u(v, "pressure", system) for v in tp]
    SP = [_u(v, "pressure", system) for v in sp]
    VP = [_u(v, "pressure", system) for v in vp]
    ax.plot(X, TP, color=S1, lw=2, label="Presión total TP", solid_joinstyle="round", zorder=3)
    ax.plot(X, SP, color=S2, lw=2, label="Presión estática SP", solid_joinstyle="round", zorder=3)
    ax.plot(X, VP, color=S3, lw=2, label="Presión de velocidad VP", solid_joinstyle="round", zorder=3)
    ax.axhline(0, color=BASE, lw=1)
    # posición del ventilador
    model = results.model
    Lf = sum(max(model.seg(s).length, 0.5) for s in nr.critical_path if s not in [d.id for d in model.discharge_path()])
    ax.axvline(_u(Lf, "length", system), color=MUTED, lw=1)
    ax.text(_u(Lf, "length", system), 1.0, " Ventilador", color=INK2, fontsize=8, va="top",
            transform=ax.get_xaxis_transform())
    st = nr.state
    ax.annotate(f"TP entrada ventilador {format_number(_u(st.tp_fan_in, 'pressure', system), 4)} {pu}",
                xy=(_u(Lf, "length", system), _u(st.tp_fan_in, "pressure", system)), xytext=(-150, 10),
                textcoords="offset points", fontsize=7.5, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    _style(ax, f"Longitud acumulada del camino crítico [{lu}]", f"Presión manométrica [{pu}]",
           "Gráfico 4 — Distribución de presión (camino crítico)", " → ".join(nr.critical_path))
    _legend(ax, loc="lower center", bbox_to_anchor=(0.5, -0.32), ncol=3)
    _tick_fmt(ax)
    fig._hover.append(("line", ax, X, TP, [f"{l}: TP {format_number(v, 4)} {pu}" for l, v in zip(lbl, TP)]))
    fig._hover.append(("line", ax, X, SP, [f"{l}: SP {format_number(v, 4)} {pu}" for l, v in zip(lbl, SP)]))
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Gráfico 5 — Curva del ventilador y curva del sistema
# ---------------------------------------------------------------------------

def plot_fan_curve(results, fan_id: str | None = None, system="SI") -> Figure:
    fig = _fig(8.8, 6.0)
    gs = fig.add_gridspec(2, 1, height_ratios=[2.3, 1.0], hspace=0.12)
    ax = fig.add_subplot(gs[0])
    ax2 = fig.add_subplot(gs[1], sharex=ax)
    qu, pu = display_unit("flow", system), display_unit("pressure", system)
    fe = results.fans.get(fan_id or results.selected_fan_id) if results.fans else None
    sc = [p for p in results.system_curve if p[3]]
    scc = [p for p in results.system_curve_clean if p[3]]
    if sc:
        ax.plot([_u(p[0], "flow", system) for p in sc], [_u(p[1], "pressure", system) for p in sc], color=S2, lw=2,
                label="Sistema (filtro en estado de diseño)", zorder=3)
        fig._hover.append(("line", ax, [_u(p[0], "flow", system) for p in sc], [_u(p[1], "pressure", system) for p in sc],
                           [f"Sistema: {format_number(_u(p[0], 'flow', system), 4)} {qu}, {format_number(_u(p[1], 'pressure', system), 4)} {pu}" for p in sc]))
    if scc:
        ax.plot([_u(p[0], "flow", system) for p in scc], [_u(p[1], "pressure", system) for p in scc], color=S3, lw=2,
                label="Sistema (filtro limpio)", zorder=3)
    if fe is not None and fe.adjusted is not None:
        s = fe.adjusted.sample(160)
        Q = [_u(q, "flow", system) for q in s["Q"]]
        P = [_u(p, "pressure", system) for p in s["FTP"]]
        name = fe.adjusted.curve.model or fe.adjusted.curve.id
        ax.plot(Q, P, color=S1, lw=2, label=f"Ventilador {name} ({fe.adjusted.rpm:.0f} rpm, ρ={fe.adjusted.rho:.3f})",
                zorder=4)
        fig._hover.append(("line", ax, Q, P, [f"Ventilador: {format_number(q, 4)} {qu}, {format_number(p, 4)} {pu}" for q, p in zip(Q, P)]))
        qpk = fe.adjusted.peak_pressure_q()
        if qpk > fe.adjusted.q_min * 1.01:
            ax.axvspan(_u(fe.adjusted.q_min, "flow", system), _u(qpk, "flow", system), color="#efeeea", zorder=1)
            ax.text(_u(fe.adjusted.q_min, "flow", system), ax.get_ylim()[0], "  zona inestable\n  (pendiente positiva)",
                    fontsize=7, color=MUTED, va="bottom")
        eta = s["eta"]
        if not np.all(np.isnan(eta)):
            ax2.plot(Q, eta * 100, color=S1, lw=2, zorder=3)
            fig._hover.append(("line", ax2, Q, list(eta * 100), [f"η_t {e * 100:.1f} % a {format_number(q, 4)} {qu}" for q, e in zip(Q, eta)]))
        b = fe.adjusted.bep()
        if b:
            qb = _u(b[0], "flow", system)
            ax.plot([qb], [_u(fe.adjusted.ftp(b[0]), "pressure", system)], marker="D", ms=8, color=S1, mec=SURFACE,
                    mew=2, zorder=6, ls="none", label="BEP (máxima eficiencia)")
            ax2.plot([qb], [b[1] * 100], marker="D", ms=8, color=S1, mec=SURFACE, mew=2, zorder=6)
            ax2.text(qb, b[1] * 100, f"  BEP {b[1] * 100:.1f} %", fontsize=7.5, color=INK2, va="bottom")
        if fe.op is not None:
            qo, po = _u(fe.op.Q, "flow", system), _u(fe.op.FTP, "pressure", system)
            ax.plot([qo], [po], marker="o", ms=10, color=INK, mec=SURFACE, mew=2, zorder=7, ls="none", label="Punto de operación")
            ax.annotate(f"Operación\n{format_number(qo, 4)} {qu}\n{format_number(po, 4)} {pu}", xy=(qo, po), xytext=(14, 14),
                        textcoords="offset points", fontsize=7.8, color=INK,
                        arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
            if fe.op.eta_total:
                ax2.plot([qo], [fe.op.eta_total * 100], marker="o", ms=9, color=INK, mec=SURFACE, mew=2, zorder=7)
    nr = results.network_design
    if nr is not None:
        ax.plot([_u(nr.state.Q_fan, "flow", system)], [_u(nr.state.FTP, "pressure", system)], marker="s", ms=8,
                color=SURFACE, mec=INK, mew=1.6, zorder=6, ls="none", label="Punto de diseño requerido")
    _style(ax, "", f"Presión total del ventilador FTP [{pu}]", "Gráfico 5 — Curva del ventilador y curva del sistema",
           "Curva corregida por densidad y velocidad; solo dentro del dominio del fabricante")
    ax.tick_params(labelbottom=False)
    _legend(ax, loc="upper left", bbox_to_anchor=(0.16, 1.0))
    _tick_fmt(ax)
    _style(ax2, f"Caudal en la entrada del ventilador [{qu}]", "η total [%]")
    ax.set_ylim(bottom=0)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.9, bottom=0.1)
    return fig


# ---------------------------------------------------------------------------
# Gráfico 6 — Pérdidas por componente (camino crítico)
# ---------------------------------------------------------------------------

def plot_losses_by_component(results, system="SI") -> Figure:
    fig = _fig(8.4, 4.4)
    ax = fig.add_subplot(111)
    nr = results.network_design
    pu = display_unit("pressure", system)
    if nr is None:
        ax.set_axis_off()
        ax.text(0.5, 0.5, "Sin resultados de red", ha="center", color=MUTED)
        return fig
    br = nr.breakdown_critical()
    items = sorted(br.items(), key=lambda kv: kv[1])
    total = sum(v for _, v in items)
    names = [k for k, _ in items] + ["Pérdida total"]
    vals = [_u(v, "pressure", system) for _, v in items] + [_u(total, "pressure", system)]
    colors = [S1] * len(items) + [INK2]
    y = np.arange(len(names))
    ax.barh(y, vals, height=0.55, color=colors, edgecolor=SURFACE, linewidth=2, zorder=3)
    for yi, v in zip(y, vals):
        pct = v / vals[-1] * 100 if vals[-1] else 0
        vt = f"{v:,.0f}" if abs(v) >= 100 else (f"{v:,.1f}" if abs(v) >= 1 else f"{v:,.3f}")
        ax.text(v, yi, f"  {vt} {pu}  ({pct:.0f} %)", va="center", fontsize=7.8, color=INK2)
    ax.set_yticks(y, names)
    ax.set_xlim(0, max(vals) * 1.28)
    _style(ax, f"Pérdida de presión total [{pu}]", "", "Gráfico 6 — Pérdidas por componente",
           f"Camino crítico {' → '.join(nr.critical_path)}")
    ax.grid(axis="y", visible=False)
    _tick_fmt(ax, "x")
    fig._hover.append(("barh", ax, list(y), vals, [f"{n}: {format_number(v, 4)} {pu}" for n, v in zip(names, vals)]))
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Gráfico 7 — Red ramificada
# ---------------------------------------------------------------------------

def plot_network(results, project=None, system="SI", model=None) -> Figure:
    fig = _fig(9.0, 5.0)
    ax = fig.add_subplot(111)
    ax.set_axis_off()
    model = model or results.model if results is not None else model
    if model is None or not model.nodes:
        ax.text(0.5, 0.5, "Red sin definir", ha="center", color=MUTED)
        return fig
    try:
        pos = tree_layout(model)
    except Exception as exc:  # noqa: BLE001
        ax.text(0.5, 0.5, f"No se puede dibujar la red: {exc}", ha="center", color=CRIT)
        return fig
    nr = results.network_design if results is not None else None
    alerts = results.alerts if results is not None else []
    bad = {a.item for a in alerts if a.level in ("CRÍTICO", "ALTO") and a.parameter in ("Velocidad de transporte", "Ramal desbalanceado")}
    qu, vu = display_unit("flow", system), display_unit("velocity", system)
    for s in model.segments:
        if s.from_node not in pos or s.to_node not in pos:
            continue
        (x1, y1), (x2, y2) = pos[s.from_node], pos[s.to_node]
        col = CRIT if s.id in bad else INK2
        lw = 1.6
        if nr is not None and s.id in nr.state.seg_evals:
            q = abs(nr.state.seg_evals[s.id].Q)
            lw = 1.2 + 2.5 * q / max(nr.state.Q_fan, 1e-9)
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12, color=col, lw=lw,
                                     shrinkA=12, shrinkB=12, connectionstyle="arc3,rad=0.0", zorder=2))
        txt = s.id
        if nr is not None and s.id in nr.state.seg_evals:
            ev = nr.state.seg_evals[s.id]
            txt += f"\n{format_number(_u(abs(ev.Q), 'flow', system), 3)} {qu}\n{format_number(_u(abs(ev.V), 'velocity', system), 3)} {vu}"
        if s.id in bad:
            txt += "\n⚠ revisar"
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.06, txt, ha="center", va="bottom", fontsize=6.8, color=INK2,
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=0.6, alpha=0.9), zorder=3)
    for nid, (x, y) in pos.items():
        nd = model.nodes[nid]
        if nd.kind == "hood":
            ax.add_patch(Polygon([[x - 0.16, y - 0.12], [x + 0.16, y - 0.12], [x + 0.07, y + 0.12], [x - 0.07, y + 0.12]],
                                 closed=True, facecolor=S1_LIGHT, edgecolor=S1, lw=1.3, zorder=4))
            name = nid
            if project is not None and nd.hood_id and project.hood(nd.hood_id):
                name = f"{nid} · {project.hood(nd.hood_id).name}"
            ax.text(x - 0.22, y, name, ha="right", va="center", fontsize=7.5, color=INK)
        elif nd.kind == "fan":
            ax.add_patch(Circle((x, y), 0.15, facecolor="#ffffff", edgecolor=INK, lw=1.5, zorder=4))
            ax.text(x, y - 0.24, "Ventilador", ha="center", va="top", fontsize=7.5, color=INK)
        elif nd.kind == "outlet":
            ax.add_patch(Rectangle((x - 0.08, y - 0.15), 0.16, 0.3, facecolor="#eeeeea", edgecolor=INK, lw=1.2, zorder=4))
            ax.text(x, y - 0.24, "Descarga", ha="center", va="top", fontsize=7.5, color=INK)
        else:
            ax.add_patch(Circle((x, y), 0.07, facecolor=INK, edgecolor=SURFACE, lw=1.5, zorder=4))
            ax.text(x, y - 0.14, nid, ha="center", va="top", fontsize=7, color=MUTED)
    xs = [p[0] for p in pos.values()]
    ys = [p[1] for p in pos.values()]
    ax.set_xlim(min(xs) - 1.6, max(xs) + 0.5)
    ax.set_ylim(min(ys) - 0.6, max(ys) + 0.6)
    ax.set_title("Gráfico 7 — Red ramificada (nodos, sentido de flujo, caudal y velocidad)", loc="left", color=INK,
                 fontsize=11, fontweight="bold")
    ax.text(0, -0.02, "Grosor de línea proporcional al caudal. Rojo con ⚠: tramo con alerta ALTA/CRÍTICA.",
            transform=ax.transAxes, fontsize=7.5, color=MUTED, va="top")
    fig.tight_layout()
    return fig


def plot_alternatives(metrics, system="SI") -> Figure:
    """Comparación de potencia eléctrica por alternativa (una serie; no elegibles en gris con etiqueta)."""
    fig = _fig(8.0, 3.6)
    ax = fig.add_subplot(111)
    pu = display_unit("power", system)
    names = [m.name.split(" — ")[0] for m in metrics]
    vals = [_u(m.P_elec, "power", system) if m.P_elec else 0 for m in metrics]
    cols = [S1 if m.eligible else "#c3c2b7" for m in metrics]
    x = np.arange(len(names))
    ax.bar(x, vals, width=0.5, color=cols, edgecolor=SURFACE, linewidth=2, zorder=3)
    for xi, v, m in zip(x, vals, metrics):
        ax.text(xi, v, f"{format_number(v, 3)} {pu}\n" + ("elegible" if m.eligible else "no elegible"), ha="center",
                va="bottom", fontsize=7.5, color=INK2)
    ax.set_xticks(x, names)
    ax.set_ylim(0, max(vals + [1]) * 1.3)
    _style(ax, "Alternativa", f"Potencia eléctrica [{pu}]", "Comparación de alternativas — potencia eléctrica",
           "Gris: alternativa no elegible (riesgo técnico o déficit de caudal)")
    fig.tight_layout()
    return fig


ALL_PLOTS = {
    "system": "Gráfico 1 — Esquema del sistema",
    "geometry": "Gráfico 2 — Geometría de ductos",
    "velocity": "Gráfico 3 — Perfil de velocidad",
    "pressure": "Gráfico 4 — Distribución de presión",
    "fan": "Gráfico 5 — Curva del ventilador",
    "losses": "Gráfico 6 — Pérdidas por componente",
    "network": "Gráfico 7 — Red ramificada",
}


def build_all(project, results, db, settings, system="SI") -> dict[str, Figure]:
    figs: dict[str, Figure] = {}
    builders = {
        "system": lambda: plot_system_schematic(project, results, system),
        "velocity": lambda: plot_velocity_profile(results, db, settings, project, system),
        "pressure": lambda: plot_pressure_distribution(results, system),
        "fan": lambda: plot_fan_curve(results, None, system),
        "losses": lambda: plot_losses_by_component(results, system),
        "network": lambda: plot_network(results, project, system),
    }
    for k, f in builders.items():
        try:
            figs[k] = f()
        except Exception as exc:  # noqa: BLE001
            fig = _fig()
            ax = fig.add_subplot(111)
            ax.set_axis_off()
            ax.text(0.5, 0.5, f"Error al generar el gráfico: {exc}", ha="center", color=CRIT, wrap=True)
            figs[k] = fig
    # geometría: herramienta de ductos o primer tramo de la red
    try:
        g = None
        if results.duct_tool:
            g = results.duct_tool[0].geometry
        elif results.model and results.model.segments:
            g = results.model.segments[0].geometry
        if g is not None:
            if g.shape == "circular":
                a = math.sqrt(math.pi * g.D ** 2 / 4 / 2.0)
                figs["geometry"] = plot_duct_geometry(g.D, 2 * a, a, system, "circular de cálculo y rectangular de igual área 2:1")
            else:
                De = g.De
                figs["geometry"] = plot_duct_geometry(De, g.a, g.b, system, "rectangular y circular de igual fricción")
    except Exception:  # noqa: BLE001
        pass
    return figs


def save_png(fig: Figure, path: str, dpi: int = 160) -> str:
    fig.savefig(path, dpi=dpi, facecolor=fig.get_facecolor(), bbox_inches="tight")
    return path
