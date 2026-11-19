"""Campanas de extracción localizada."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QVBoxLayout, QComboBox, QLineEdit, QFormLayout

from core.hood_design import HOOD_TYPES, HoodEntry
from core.project import Hood
from reports import tables as T
from ..editable_table import EditableTable, Col
from ..widgets import QField, combo, set_combo, group, note, ResultTable
from .base import BasePage, header, hrow

PARAMS = {
    "W": ("Ancho de la cara W", "length"), "H": ("Alto de la cara H", "length"), "X": ("Distancia de captura X", "length"),
    "Vc": ("Velocidad de captura / de cara", "velocity"), "L": ("Longitud de ranura L", "length"),
    "Ws": ("Ancho de ranura", "length"), "A_open": ("Área de aberturas", "area"), "P": ("Perímetro del proceso P", "length"),
    "D": ("Altura sobre el proceso D", "length"), "Q_source": ("Caudal inducido por la fuente", "flow"),
    "margin": ("Margen de diseño", None),
}


class HoodsPage(BasePage):
    modules = ["Campanas"]

    def __init__(self, ctx):
        super().__init__(ctx)
        self.lay.addWidget(header("Campanas de extracción", "Ecuaciones de DallaValle por geometría (ACGIH), validez "
                                  "geométrica verificada, pérdida de entrada he = Fh·VPd y presión estática de campana."))
        cls_opts = lambda: [(c["id"], c["name"]) for c in self.ctx.db.transport_classes]  # noqa: E731
        self.list = EditableTable([
            Col("id", "ID", width=60), Col("name", "Nombre", width=210),
            Col("type", "Tipo", "combo", options=[(k, v["label"]) for k, v in HOOD_TYPES.items()], width=230),
            Col("contaminant_class", "Clase de contaminante (transporte)", "combo", options=cls_opts, width=230),
        ], self.ctx.project.hoods, factory=self._new)
        self.list.setMinimumHeight(190)
        self.list.changed.connect(self._list_changed)
        self.list.current_changed.connect(self._select)
        lg, lf = group("Campanas del proyecto", QVBoxLayout())
        lf.addWidget(self.list)
        self.lay.addWidget(lg)
        g, self.form = group("Geometría y entrada de la campana seleccionada")
        self.eq = note("")
        self.form.addRow(self.eq)
        self.fields = {}
        for k, (lbl, q) in PARAMS.items():
            fld = QField(q, unit_override=None if q else "%", scale=1 if q else 100.0, optional=True)
            fld.changed.connect(lambda v, key=k: self._param(key, v))
            self.fields[k] = fld
            self.form.addRow(lbl, fld)
        self.entry = QComboBox()
        self.entry.currentIndexChanged.connect(self._entry_changed)
        self.kind = combo([("fh", "Simple (Fh·VPd)"), ("slot", "Compuesta: ranura + pleno")])
        self.kind.currentIndexChanged.connect(self._entry_fields)
        self.Fh = QField(None, unit_override="-")
        self.Fs = QField(None, unit_override="-")
        self.slot_area = QField("area", optional=True)
        self.plenum = QCheckBox("Considerar perdida la energía cinética de la ranura en el pleno (hipótesis)")
        self.cross = QField("velocity", optional=True)
        self.process = QLineEdit()
        for w in (self.Fh, self.Fs, self.slot_area, self.cross):
            w.changed.connect(self._entry_fields)
        self.plenum.toggled.connect(self._entry_fields)
        self.process.editingFinished.connect(self._entry_fields)
        self.form.addRow("Tipo de entrada (biblioteca)", self.entry)
        self.form.addRow("Modelo de pérdida", self.kind)
        self.form.addRow("Fh (entrada al ducto)", self.Fh)
        self.form.addRow("Fs (ranura)", self.Fs)
        self.form.addRow("Área total de ranuras", self.slot_area)
        self.form.addRow(self.plenum)
        self.form.addRow("Corriente cruzada del local (opcional)", self.cross)
        self.form.addRow("Proceso / descripción", self.process)
        rg, rf = group("Guía de velocidades de captura (ACGIH — verificar edición vigente)", QVBoxLayout())
        self.cap = ResultTable()
        self.cap.setMinimumHeight(200)
        rf.addWidget(self.cap)
        self.lay.addWidget(hrow(g, rg))
        og, of = group("Resultados por campana", QVBoxLayout())
        self.table = ResultTable()
        self.table.setMinimumHeight(170)
        of.addWidget(self.table)
        of.addWidget(note("Q requerido a la temperatura de la campana. SPh y Ce se obtienen con el caudal del diseño "
                          "balanceado y el diámetro del primer tramo de la red."))
        self.lay.addWidget(og)
        tabs, self.alerts, self.dec, self.trace = self.results_tabs()
        self.lay.addWidget(tabs)
        self.cur = None

    def _new(self):
        ids = {h.id for h in self.ctx.project.hoods}
        i = 1
        while f"C{i}" in ids:
            i += 1
        return Hood(id=f"C{i}", name=f"Campana {i}")

    def load(self):
        self._loading = True
        self.list.set_items(self.ctx.project.hoods)
        self.entry.blockSignals(True)
        self.entry.clear()
        for e in self.ctx.db.hood_entries:
            lab = e["name"] + (f" (Ce {e['Ce']}, Fh {e['Fh']})" if e.get("Fh") is not None else "")
            self.entry.addItem(lab, e["id"])
        self.entry.blockSignals(False)
        rows = [[r["condition"], r["examples"], f"{r['v_min_m_s']}–{r['v_max_m_s']} m/s ({r['fpm'][0]}–{r['fpm'][1]} fpm)"]
                for r in self.ctx.db.capture_ranges]
        self.cap.set_data(["Condición de liberación", "Ejemplos", "Velocidad de captura"], rows)
        self._loading = False
        if self.ctx.project.hoods:
            self.list.table.setCurrentCell(0, 0)
            self._select(0)

    def _list_changed(self):
        self._select(self.list.current_index())
        self.emit_changed()

    def _select(self, idx):
        hs = self.ctx.project.hoods
        if not (0 <= idx < len(hs)):
            self.cur = None
            return
        self.cur = hs[idx]
        h = self.cur
        self._loading = True
        self.eq.setText(f"<b>{h.id}</b> — {HOOD_TYPES.get(h.type, {}).get('label', h.type)}:  "
                        f"<b>{HOOD_TYPES.get(h.type, {}).get('eq', '')}</b>")
        needed = set(HOOD_TYPES.get(h.type, {}).get("params", []))
        for k, fld in self.fields.items():
            fld.set_value(h.params.get(k))
            self.form.setRowVisible(fld, k in needed)
        set_combo(self.entry, h.entry_id)
        set_combo(self.kind, h.entry.kind)
        self.Fh.set_value(h.entry.Fh)
        self.Fs.set_value(h.entry.Fs)
        self.slot_area.set_value(h.entry.slot_area)
        self.plenum.setChecked(h.entry.plenum_loss)
        self.cross.set_value(h.cross_draft_m_s)
        self.process.setText(h.process)
        slot = h.entry.kind == "slot"
        for w in (self.Fs, self.slot_area, self.plenum):
            self.form.setRowVisible(w, slot)
        self._loading = False

    def _param(self, key, v):
        if self._loading or self.cur is None:
            return
        if v is None:
            self.cur.params.pop(key, None)
        else:
            self.cur.params[key] = v
        self.emit_changed()

    def _entry_changed(self, *_):
        if self._loading or self.cur is None:
            return
        eid = self.entry.currentData()
        self.cur.entry_id = eid
        e = next((x for x in self.ctx.db.hood_entries if x["id"] == eid), None)
        if e and e.get("Fh") is not None:
            self.cur.entry.Fh = float(e["Fh"])
            self.cur.entry.source = e.get("source", "")
            self.Fh.set_value(self.cur.entry.Fh)
        self.emit_changed()

    def _entry_fields(self, *_):
        if self._loading or self.cur is None:
            return
        h = self.cur
        h.entry.kind = self.kind.currentData()
        h.entry.Fh = self.Fh.value() if self.Fh.value() is not None else h.entry.Fh
        h.entry.Fs = self.Fs.value() if self.Fs.value() is not None else h.entry.Fs
        h.entry.slot_area = self.slot_area.value()
        h.entry.plenum_loss = self.plenum.isChecked()
        h.cross_draft_m_s = self.cross.value()
        h.process = self.process.text()
        slot = h.entry.kind == "slot"
        for w in (self.Fs, self.slot_area, self.plenum):
            self.form.setRowVisible(w, slot)
        self.emit_changed()

    def render(self):
        r = self.ctx.results
        if r is None:
            return
        self.table.set_data(*T.hoods_table(self.ctx.project, r, self.ctx.system))
        self.fill_common(self.alerts, self.dec, self.trace, "Campanas")
