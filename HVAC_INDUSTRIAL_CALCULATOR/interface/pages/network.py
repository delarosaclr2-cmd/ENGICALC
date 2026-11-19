"""Editor y resultados de redes ramificadas."""
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QTabWidget, QLabel, QPushButton, QHBoxLayout, QWidget

from core.equipment import Equipment, EQUIPMENT_TYPES
from core.fittings import FittingInstance
from core.network_solver import NetNode, NetSegment
from graphics.plots import plot_network, plot_velocity_profile
from reports import tables as T
from ..editable_table import EditableTable, Col
from ..widgets import combo, set_combo, group, note, ResultTable, PlotCanvas
from .base import BasePage, header, hrow

KINDS = [("hood", "Campana (entrada)"), ("junction", "Unión / nodo"), ("fan", "Ventilador"), ("outlet", "Descarga")]


class NetworkPage(BasePage):
    modules = ["Redes ramificadas", "Diseño de ductos"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Redes ramificadas", "Red de extracción en árbol: campanas → uniones → ventilador → "
                                  "descarga. Continuidad de masa, balance de presión total en nodos, equilibrado por "
                                  "diseño y solución de operación con la curva del ventilador. Cada tramo tiene su "
                                  "geometría, material, accesorios y equipos."))
        g, f = group("Criterios de la red")
        cls = lambda: [(c["id"], c["name"]) for c in self.ctx.db.transport_classes]  # noqa: E731
        self.cls = combo([])
        self._cls_opts = cls
        self.strategy = combo([("acgih", "Equilibrado por diseño (aceptar / aumentar caudal / rediseñar)"),
                               ("dampers", "Compuertas de balance en ramales no gobernantes"),
                               ("none", "Solo informar el desbalance")])
        f.addRow("Clase de contaminante por defecto (velocidad de transporte)", self.cls)
        f.addRow("Estrategia de balance", self.strategy)
        self.topo = QLabel()
        self.topo.setWordWrap(True)
        f.addRow("Topología", self.topo)
        f.addRow(note("Umbrales de equilibrado configurables en 'Configuración' (por defecto: ≤5 % aceptar, ≤20 % aumentar "
                      "caudal del ramal, >20 % rediseñar). No se recomienda estrangular sin evaluar su costo energético."))
        self.cls.currentIndexChanged.connect(self._apply_settings)
        self.strategy.currentIndexChanged.connect(self._apply_settings)
        self.lay.addWidget(g)
        hood_opts = lambda: [("", "—")] + [(h.id, f"{h.id} · {h.name}") for h in self.ctx.project.hoods]  # noqa: E731
        self.nodes_list: list[NetNode] = []
        self.t_nodes = EditableTable([
            Col("id", "ID", width=60), Col("kind", "Tipo", "combo", options=KINDS, width=150), Col("label", "Etiqueta"),
            Col("hood_id", "Campana vinculada", "combo", options=hood_opts, width=200),
            Col("q_design", "Q forzado (opcional)", "ofloat", "flow"),
            Col("temperature_c", "T del aire captado (opcional)", "ofloat", "temperature"),
            Col("exit_K", "K de salida (descarga)", "float"),
            Col("stack_height_above_roof_m", "Altura sobre cubierta (descarga)", "ofloat", "length"),
            Col("fan_outlet_area_m2", "Área de descarga del ventilador", "ofloat", "area"),
        ], self.nodes_list, factory=self._new_node, on_remove=self._node_removed)
        self.t_nodes.setMinimumHeight(220)
        self.t_nodes.changed.connect(self._nodes_changed)
        node_opts = lambda: [(n.id, n.id) for n in self.nodes_list]  # noqa: E731
        mat_opts = lambda: [(m["id"], m["name"]) for m in self.ctx.db.materials]  # noqa: E731
        self.t_segs = EditableTable([
            Col("id", "Tramo", width=60), Col("from_node", "Desde", "combo", options=node_opts, width=80),
            Col("to_node", "Hacia", "combo", options=node_opts, width=80),
            Col("shape", "Sección", "combo", options=[("circular", "Circular"), ("rectangular", "Rectangular")], width=100),
            Col("D", "D", "ofloat", "small_length"), Col("a", "a", "ofloat", "small_length"),
            Col("b", "b", "ofloat", "small_length"), Col("length", "Longitud", "float", "length"),
            Col("material_id", "Material", "combo", options=mat_opts, width=220),
            Col("roughness_m", "ε (opcional)", "ofloat", "roughness"),
            Col("damper_K", "K compuerta", "float"),
            Col("contaminant_class", "Clase (opcional)", "combo", options=lambda: [("", "— (heredada)")] + cls(), width=170),
        ], [], factory=self._new_seg)
        self.t_segs.setMinimumHeight(260)
        self.t_segs.changed.connect(self._segs_changed)
        self.t_segs.current_changed.connect(self._select_seg)
        tabs = QTabWidget()
        w1 = QWidget(); l1 = QVBoxLayout(w1); l1.addWidget(self.t_nodes)
        w2 = QWidget(); l2 = QVBoxLayout(w2); l2.addWidget(self.t_segs)
        tabs.addTab(w1, "Nodos")
        tabs.addTab(w2, "Tramos")
        tabs.setCurrentIndex(1)
        self.lay.addWidget(tabs)
        fit_opts = lambda: [(fd["id"], fd["name"]) for fd in self.ctx.db.fittings]  # noqa: E731
        self.seg_lbl = QLabel("<b>Seleccione un tramo para editar sus accesorios y equipos.</b>")
        self.t_fit = EditableTable([
            Col("fitting_id", "Accesorio (biblioteca)", "combo", options=fit_opts, width=300), Col("qty", "Cant.", "float"),
            Col("K_override", "K del usuario (opcional)", "ofloat"), Col("area_ref_m2", "A ref. (opcional)", "ofloat", "area"),
            Col("params.angle", "Ángulo (codo)", "ofloat", unit="°"), Col("params.R_D", "R/D (codo)", "ofloat"),
            Col("params.A_other_m2", "Área sección mayor (transición)", "ofloat", "area"),
            Col("params.theta", "θ transición", "ofloat", unit="°"), Col("note", "Nota / fuente"),
        ], [], factory=lambda: FittingInstance("elbow90_RD1.5", 1.0))
        self.t_fit.setMinimumHeight(180)
        self.t_fit.changed.connect(self.emit_changed)
        self.t_eq = EditableTable([
            Col("name", "Equipo", width=160), Col("eq_type", "Tipo", "combo", options=[(t, t) for t in EQUIPMENT_TYPES], width=170),
            Col("model", "Modelo de pérdida", "combo", options=[("fixed", "ΔP fijo"), ("power_law", "ΔP = ΔPref(Q/Qref)^n"),
                                                                ("table", "Curva por puntos"), ("filter", "Filtro limpio/saturado")], width=170),
            Col("dp_fixed", "ΔP fijo", "float", "pressure"), Col("dp_ref", "ΔP ref", "float", "pressure"),
            Col("q_ref", "Q ref", "float", "flow"), Col("n_exp", "n", "float"),
            Col("dp_clean", "ΔP limpio", "float", "pressure"), Col("dp_dirty", "ΔP saturado", "float", "pressure"),
            Col("state", "Estado", "combo", options=[("limpio", "Limpio"), ("sucio", "Saturado"), ("intermedio", "Intermedio")]),
            Col("state_fraction", "Fracción", "float"),
            Col("table", "Curva", "pairs", "flow,pressure", width=220), Col("source", "Fuente del dato", width=220),
        ], [], factory=lambda: Equipment("Filtro", "Filtro", "filter", q_ref=1.0, n_exp=1.0, dp_clean=250, dp_dirty=750,
                                          source="Dato del fabricante (indicar)"))
        self.t_eq.setMinimumHeight(150)
        self.t_eq.changed.connect(self.emit_changed)
        dg, dl = group("Accesorios y equipos del tramo seleccionado", QVBoxLayout())
        dl.addWidget(self.seg_lbl)
        dl.addWidget(note("Cada K se aplica con la velocidad de su sección de referencia (área propia del tramo si no se "
                          "indica otra). Los coeficientes de la biblioteca indican su fuente y estado de verificación."))
        dl.addWidget(self.t_fit)
        dl.addWidget(self.t_eq)
        self.lay.addWidget(dg)
        rg, rl = group("Resultados de la red", QVBoxLayout())
        rt = QTabWidget()
        self.r_bal = ResultTable()
        self.r_hood = ResultTable()
        rt.addTab(self.r_bal, "Balance en uniones")
        rt.addTab(self.r_hood, "Caudales por campana")
        rt.setMinimumHeight(230)
        rl.addWidget(rt)
        self.p_net = PlotCanvas(420)
        self.p_vel = PlotCanvas(380)
        rl.addWidget(self.p_net)
        rl.addWidget(self.p_vel)
        self.lay.addWidget(rg)
        t2, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(t2)
        self.cur_seg = None

    # --- carga ---
    def load(self):
        self._loading = True
        m = self.ctx.project.network
        self.cls.clear()
        for k, v in self._cls_opts():
            self.cls.addItem(v, k)
        ns = self.ctx.project.network_settings
        set_combo(self.cls, ns.contaminant_class)
        set_combo(self.strategy, ns.strategy)
        self.nodes_list[:] = list(m.nodes.values())
        self._ids = {id(n): n.id for n in self.nodes_list}
        self.t_nodes.set_items(self.nodes_list)
        self.t_segs.set_items(m.segments)
        self._loading = False
        self._topology()
        if m.segments:
            self.t_segs.table.setCurrentCell(0, 0)
            self._select_seg(0)

    def _apply_settings(self, *_):
        if self._loading:
            return
        ns = self.ctx.project.network_settings
        ns.contaminant_class = self.cls.currentData()
        ns.strategy = self.strategy.currentData()
        self.emit_changed()

    def _new_node(self):
        ids = {n.id for n in self.nodes_list}
        i = 1
        while f"N{i}" in ids:
            i += 1
        return NetNode(f"N{i}", "junction")

    def _node_removed(self, node):
        m = self.ctx.project.network
        m.segments[:] = [s for s in m.segments if s.from_node != node.id and s.to_node != node.id]
        self.t_segs.rebuild()

    def _nodes_changed(self):
        m = self.ctx.project.network
        # renombrado de nodos: actualizar referencias en tramos
        for n in self.nodes_list:
            old = self._ids.get(id(n))
            if old and old != n.id:
                for s in m.segments:
                    if s.from_node == old:
                        s.from_node = n.id
                    if s.to_node == old:
                        s.to_node = n.id
        m.nodes.clear()
        for n in self.nodes_list:
            m.nodes[n.id] = n
        self._ids = {id(n): n.id for n in self.nodes_list}
        self.t_segs.rebuild()
        self._topology()
        self.emit_changed()

    def _new_seg(self):
        segs = self.ctx.project.network.segments
        ids = {s.id for s in segs}
        i = 1
        while f"T{i}" in ids:
            i += 1
        first = self.nodes_list[0].id if self.nodes_list else ""
        return NetSegment(f"T{i}", first, first, "circular", 0.2, length=5.0)

    def _segs_changed(self):
        self._topology()
        self._select_seg(self.t_segs.current_index())
        self.emit_changed()

    def _select_seg(self, idx):
        segs = self.ctx.project.network.segments
        if not (0 <= idx < len(segs)):
            return
        s = segs[idx]
        self.cur_seg = s
        self.seg_lbl.setText(f"<b>Tramo {s.id}</b>: {s.from_node} → {s.to_node} · {s.geometry.describe() if (s.D or s.a) else ''}")
        self.t_fit.set_items(s.fittings)
        self.t_eq.set_items(s.equipment)

    def _topology(self):
        errs = self.ctx.project.network.validate() if self.ctx.project.network.nodes else ["Red vacía."]
        if errs:
            self.topo.setText("<span style='color:#B42318'>⚠ " + "<br>⚠ ".join(errs) + "</span>")
        else:
            m = self.ctx.project.network
            self.topo.setText(f"<span style='color:#2B7A4B'>✔ Árbol válido</span>: {len(m.nodes_of_kind('hood'))} campanas, "
                              f"{len(m.segments)} tramos, 1 ventilador, 1 descarga.")

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        s = self.ctx.system
        self.r_bal.set_data(*T.balance_table(r, s))
        self.r_hood.set_data(*T.hood_flows_table(r, s))
        if r.model is not None:
            self.p_net.set_figure(plot_network(r, self.ctx.project, s))
            self.p_vel.set_figure(plot_velocity_profile(r, self.ctx.db, self.ctx.settings, self.ctx.project, s))
        self.fill_common(self.alerts, self.dec, self.trace, "Redes ramificadas")
