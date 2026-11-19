"""Tabla editable enlazada a una lista de objetos (dataclasses o diccionarios)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QComboBox,
                               QAbstractItemView, QHeaderView, QMessageBox)

from core import units as U
from .widgets import UnitContext, parse_float


@dataclass
class Col:
    key: str
    header: str
    kind: str = "str"           # 'str' | 'float' | 'ofloat' (opcional) | 'int' | 'combo' | 'bool'
    quantity: str | None = None
    options: Any = None         # lista [(clave, etiqueta)] o callable que la devuelve
    scale: float = 1.0          # p. ej. 100 para mostrar fracciones en %
    unit: str | None = None     # unidad fija (si no hay magnitud)
    readonly: bool = False
    width: int | None = None


def _get(obj, key):
    parts = key.split(".")
    cur = obj
    for p in parts:
        if cur is None:
            return None
        if isinstance(cur, (list, tuple)):
            i = int(p)
            cur = cur[i] if i < len(cur) else None
        else:
            cur = cur.get(p) if isinstance(cur, dict) else getattr(cur, p, None)
    return cur


def _set(obj, key, value):
    parts = key.split(".")
    cur = obj
    for p in parts[:-1]:
        nxt = cur.get(p) if isinstance(cur, dict) else getattr(cur, p, None)
        if nxt is None:
            nxt = {}
            if isinstance(cur, dict):
                cur[p] = nxt
            else:
                setattr(cur, p, nxt)
        cur = nxt
    last = parts[-1]
    if isinstance(cur, list):
        cur[int(last)] = value
    elif isinstance(cur, dict):
        cur[last] = value
    else:
        setattr(cur, last, value)


def pairs_to_text(pairs, q1, q2, system) -> str:
    out = []
    for a, b in pairs or []:
        x = U.to_display(float(a), q1, system) if q1 else float(a)
        y = U.to_display(float(b), q2, system) if q2 else float(b)
        out.append(f"{x:.6g}:{y:.6g}")
    return "; ".join(out)


def text_to_pairs(txt, q1, q2, system):
    pairs = []
    for chunk in (txt or "").split(";"):
        if not chunk.strip():
            continue
        a, b = chunk.split(":")
        x, y = parse_float(a), parse_float(b)
        pairs.append([U.from_display(x, q1, system) if q1 else x, U.from_display(y, q2, system) if q2 else y])
    return pairs


class EditableTable(QWidget):
    changed = Signal()
    current_changed = Signal(int)

    def __init__(self, cols: list[Col], items: list | None = None, factory: Callable[[], Any] | None = None,
                 allow_add=True, allow_remove=True, allow_move=False, on_remove: Callable | None = None):
        super().__init__()
        self.cols = cols
        self.items = items if items is not None else []
        self.factory = factory
        self.on_remove = on_remove
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        bar = QHBoxLayout()
        self.btn_add = QPushButton("＋ Agregar")
        self.btn_del = QPushButton("－ Eliminar")
        self.btn_del.setObjectName("danger")
        self.btn_up = QPushButton("↑")
        self.btn_dn = QPushButton("↓")
        for b, ok in ((self.btn_add, allow_add and factory is not None), (self.btn_del, allow_remove),
                      (self.btn_up, allow_move), (self.btn_dn, allow_move)):
            b.setVisible(ok)
            bar.addWidget(b)
        bar.addStretch(1)
        self.extra_bar = bar
        lay.addLayout(bar)
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        lay.addWidget(self.table)
        self.btn_add.clicked.connect(self._add)
        self.btn_del.clicked.connect(self._del)
        self.btn_up.clicked.connect(lambda: self._move(-1))
        self.btn_dn.clicked.connect(lambda: self._move(1))
        self.table.itemChanged.connect(self._item_changed)
        self.table.currentCellChanged.connect(lambda r, c, pr, pc: self.current_changed.emit(r) if r != pr else None)
        UnitContext.listeners.append(self.rebuild)
        self._building = False
        self.rebuild()

    def set_items(self, items: list):
        self.items = items
        self.rebuild()

    def _header(self, c: Col) -> str:
        if c.kind == "pairs":
            q1, q2 = (c.quantity or ",").split(",")
            u1 = U.display_unit(q1, UnitContext.system) if q1 else "-"
            u2 = U.display_unit(q2, UnitContext.system) if q2 else "-"
            return f"{c.header} [{u1}:{u2}; …]"
        if c.quantity:
            u = U.display_unit(c.quantity, UnitContext.system)
            return f"{c.header} [{u}]"
        if c.unit:
            return f"{c.header} [{c.unit}]"
        return c.header

    def _opts(self, c: Col):
        return c.options() if callable(c.options) else (c.options or [])

    def rebuild(self):
        self._building = True
        cur = self.table.currentRow()
        self.table.clear()
        self.table.setColumnCount(len(self.cols))
        self.table.setRowCount(len(self.items))
        self.table.setHorizontalHeaderLabels([self._header(c) for c in self.cols])
        for i, obj in enumerate(self.items):
            for j, c in enumerate(self.cols):
                v = _get(obj, c.key)
                if c.kind == "combo":
                    cb = QComboBox()
                    for k, lbl in self._opts(c):
                        cb.addItem(lbl, k)
                    idx = cb.findData(v)
                    if idx < 0 and v not in (None, ""):
                        cb.addItem(str(v), v)
                        idx = cb.count() - 1
                    cb.setCurrentIndex(max(idx, 0) if v is not None else -1)
                    cb.setEnabled(not c.readonly)
                    cb.currentIndexChanged.connect(lambda _i, row=i, col=j, w=cb: self._combo_changed(row, col, w))
                    self.table.setCellWidget(i, j, cb)
                    continue
                it = QTableWidgetItem()
                if c.kind == "bool":
                    it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                    it.setCheckState(Qt.Checked if v else Qt.Unchecked)
                elif c.kind == "pairs":
                    q1, q2 = (c.quantity or ",").split(",")
                    it.setText(pairs_to_text(v, q1 or None, q2 or None, UnitContext.system))
                else:
                    txt = ""
                    if v is not None and c.kind in ("float", "ofloat", "int"):
                        try:
                            dv = U.to_display(float(v), c.quantity, UnitContext.system) if c.quantity else float(v)
                            dv *= c.scale
                            txt = f"{dv:.6g}"
                        except (TypeError, ValueError):
                            txt = str(v)
                    elif v is not None:
                        txt = str(v)
                    it.setText(txt)
                    if c.readonly:
                        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    if c.kind in ("float", "ofloat", "int"):
                        it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(i, j, it)
        self.table.resizeColumnsToContents()
        for j, c in enumerate(self.cols):
            if c.width:
                self.table.setColumnWidth(j, c.width)
            elif self.table.columnWidth(j) < 70:
                self.table.setColumnWidth(j, 70)
        if 0 <= cur < len(self.items):
            self.table.setCurrentCell(cur, 0)
        self._building = False

    def _combo_changed(self, row, col, w):
        if self._building or row >= len(self.items):
            return
        _set(self.items[row], self.cols[col].key, w.currentData())
        self.changed.emit()

    def _item_changed(self, it: QTableWidgetItem):
        if self._building:
            return
        row, col = it.row(), it.column()
        if row >= len(self.items):
            return
        c = self.cols[col]
        obj = self.items[row]
        try:
            if c.kind == "bool":
                val = it.checkState() == Qt.Checked
            elif c.kind == "pairs":
                q1, q2 = (c.quantity or ",").split(",")
                val = text_to_pairs(it.text(), q1 or None, q2 or None, UnitContext.system)
            elif c.kind in ("float", "ofloat", "int"):
                v = parse_float(it.text())
                if v is None:
                    if c.kind != "ofloat":
                        raise ValueError("valor requerido")
                    val = None
                else:
                    v = v / c.scale
                    val = U.from_display(v, c.quantity, UnitContext.system) if c.quantity else v
                    if c.kind == "int":
                        val = int(round(val))
            else:
                val = it.text().strip()
        except ValueError as exc:
            QMessageBox.warning(self, "Dato inválido", f"{c.header}: {exc}")
            self.rebuild()
            return
        _set(obj, c.key, val)
        self.changed.emit()

    def _add(self):
        if not self.factory:
            return
        obj = self.factory()
        if obj is None:
            return
        self.items.append(obj)
        self.rebuild()
        self.table.setCurrentCell(len(self.items) - 1, 0)
        self.changed.emit()

    def _del(self):
        r = self.table.currentRow()
        if 0 <= r < len(self.items):
            obj = self.items.pop(r)
            if self.on_remove:
                self.on_remove(obj)
            self.rebuild()
            self.changed.emit()

    def _move(self, d):
        r = self.table.currentRow()
        n = r + d
        if 0 <= r < len(self.items) and 0 <= n < len(self.items):
            self.items[r], self.items[n] = self.items[n], self.items[r]
            self.rebuild()
            self.table.setCurrentCell(n, 0)
            self.changed.emit()

    def current_index(self) -> int:
        return self.table.currentRow()
