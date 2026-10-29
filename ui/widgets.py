"""Widgets réutilisables : champs de date « vides possibles », éditeur de tableau générique."""
from __future__ import annotations

from datetime import date, datetime
from typing import Callable, Dict, List, Optional

from PySide6.QtCore import QDate, QDateTime, QEvent, QObject, QStringListModel, Qt, QTime, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (QAbstractItemView, QCalendarWidget, QComboBox, QCompleter, QDateEdit, QDateTimeEdit, QHBoxLayout,
                               QHeaderView, QLineEdit, QPushButton, QStyledItemDelegate, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from config import theme
from core.schema import Col  # noqa: F401  (réexporté)
from core.storage import parse_date, parse_datetime

ERR_BG = QColor("#FDE2E1")
ANNEE_MIN = theme.ANNEE_MIN          # les calendriers commencent en 2026


def _sentinel(year: int = ANNEE_MIN) -> QDate:
    """Valeur minimale = « inconnue » : le 31 décembre de l'année précédente."""
    return QDate(year - 1, 12, 31)


class _JumpToToday(QObject):
    """Quand le calendrier s'ouvre sur une date inconnue, afficher le mois en cours."""
    def __init__(self, edit):
        super().__init__(edit)
        self.edit = edit

    def eventFilter(self, obj, ev):
        if ev.type() == QEvent.Show and self.edit.is_empty():
            QTimer.singleShot(0, self.edit.jump_to_today)
        return False


class _CalendarMixin:
    def _setup_calendar(self):
        self.setCalendarPopup(True)
        self.setMinimumDate(_sentinel())
        self.setMaximumDate(QDate(2100, 12, 31))
        self.setSpecialValueText("— inconnue —")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda _: self.set_value(None))
        self.setToolTip("Calendrier à partir de " + str(ANNEE_MIN) + ". « inconnue » si la date n'est pas connue. "
                        "Clic droit : effacer.")
        cal = self.calendarWidget()
        cal.setGridVisible(False)
        cal.setVerticalHeaderFormat(QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader)
        cal.installEventFilter(_JumpToToday(self))

    def is_empty(self) -> bool:
        return self.date() == self.minimumDate()

    def jump_to_today(self):
        t = QDate.currentDate()
        self.calendarWidget().setCurrentPage(t.year(), t.month())

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        if self.is_empty():
            QTimer.singleShot(0, self.jump_to_today)

    def _ensure_range(self, d: QDate):
        # une date antérieure à 2026 (donnée existante) reste affichée correctement
        if d.isValid() and d <= self.minimumDate():
            self.setMinimumDate(_sentinel(d.year()))


class DateField(_CalendarMixin, QDateEdit):
    """Date avec calendrier (à partir de 2026) ; la valeur minimale signifie « inconnue »."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy")
        self._setup_calendar()
        self.setDate(self.minimumDate())
        self.setMinimumWidth(150)

    def value(self) -> Optional[date]:
        d = self.date()
        return None if self.is_empty() else date(d.year(), d.month(), d.day())

    def set_value(self, d: Optional[date]):
        if d:
            q = QDate(d.year, d.month, d.day)
            self._ensure_range(q)
            self.setDate(q)
        else:
            self.setDate(self.minimumDate())


class DateTimeField(_CalendarMixin, QDateTimeEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDisplayFormat("dd/MM/yyyy HH:mm")
        self._setup_calendar()
        self.setDateTime(QDateTime(self.minimumDate(), QTime(0, 0)))

    def value(self) -> Optional[datetime]:
        if self.is_empty():
            return None
        d, t = self.date(), self.time()
        return datetime(d.year(), d.month(), d.day(), t.hour(), t.minute())

    def set_value(self, v: Optional[datetime]):
        if v:
            q = QDate(v.year, v.month, v.day)
            self._ensure_range(q)
            self.setDateTime(QDateTime(q, QTime(v.hour, v.minute)))
        else:
            self.setDateTime(QDateTime(self.minimumDate(), QTime(0, 0)))


class _DateDelegate(QStyledItemDelegate):
    """Cellule de tableau « date » / « date-heure » éditée avec un calendrier."""
    def __init__(self, kind: str, parent=None):
        super().__init__(parent)
        self.kind = kind

    def createEditor(self, parent, option, index):
        return DateTimeField(parent) if self.kind == "datetime" else DateField(parent)

    def setEditorData(self, editor, index):
        txt = index.data() or ""
        try:
            v = parse_datetime(txt) if self.kind == "datetime" else parse_date(txt)
        except ValueError:
            v = None
        editor.set_value(v)

    def setModelData(self, editor, model, index):
        v = editor.value()
        fmt = "%d/%m/%Y %H:%M" if self.kind == "datetime" else "%d/%m/%Y"
        model.setData(index, v.strftime(fmt) if v else "")


class SearchCombo(QComboBox):
    """Liste déroulante avec recherche (tape quelques lettres) ; saisie libre autorisée."""
    changed = Signal(str)

    def __init__(self, placeholder: str = "", parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.setMaxVisibleItems(18)
        self.setMinimumWidth(260)
        self.lineEdit().setPlaceholderText(placeholder)
        comp = QCompleter(self.model(), self)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        comp.setCompletionMode(QCompleter.PopupCompletion)
        self.setCompleter(comp)
        self.currentTextChanged.connect(self.changed)

    def set_items(self, items: List[str]):
        cur = self.currentText()
        self.blockSignals(True)
        self.clear()
        self.addItems([""] + list(items))
        self.setCurrentText(cur)
        self.blockSignals(False)

    def text(self) -> str:
        return self.currentText().strip()

    def setText(self, v: str):
        self.setCurrentText(v or "")


class OptionalNumber(QLineEdit):
    """Nombre entier ou « ? » (inconnu). Vide = inconnu."""
    def __init__(self, parent=None, placeholder="? si inconnu"):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)

    def value(self) -> Optional[int]:
        t = self.text().strip()
        if t in ("", "?"):
            return None
        try:
            return int(t)
        except ValueError:
            return None

    def set_value(self, v: Optional[int]):
        self.setText("" if v is None else str(v))


# ---------------------------------------------------------------------------
# Éditeur de tableau générique
# ---------------------------------------------------------------------------
class _CompleterDelegate(QStyledItemDelegate):
    def __init__(self, model: QStringListModel, parent=None):
        super().__init__(parent)
        self.model = model

    def createEditor(self, parent, option, index):
        ed = QLineEdit(parent)
        comp = QCompleter(self.model, ed)
        comp.setCaseSensitivity(Qt.CaseInsensitive)
        comp.setFilterMode(Qt.MatchContains)
        ed.setCompleter(comp)
        return ed


class TableEditor(QWidget):
    changed = Signal()

    def __init__(self, cols: List[Col], model_cls, parent=None, add_label="Ajouter une ligne"):
        super().__init__(parent)
        self.cols = cols
        self.model_cls = model_cls
        self.errors: List[str] = []
        self._loading = False
        self.place_model = QStringListModel()

        self.table = QTableWidget(0, len(cols))
        self.table.setHorizontalHeaderLabels([c.label for c in cols])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setDefaultSectionSize(40)
        self.table.setWordWrap(False)
        hh = self.table.horizontalHeader()
        for i, c in enumerate(cols):
            hh.setSectionResizeMode(i, QHeaderView.Interactive)
            self.table.setColumnWidth(i, c.width or 120)
            item = self.table.horizontalHeaderItem(i)
            if c.tip:
                item.setToolTip(c.tip)
            if c.complete:
                self.table.setItemDelegateForColumn(i, _CompleterDelegate(self.place_model, self.table))
            elif c.kind in ("date", "datetime"):
                self.table.setItemDelegateForColumn(i, _DateDelegate(c.kind, self.table))
        hh.setStretchLastSection(True)
        self.table.itemChanged.connect(self._on_item_changed)

        btns = QHBoxLayout()
        self.buttons: Dict[str, QPushButton] = {}
        for key, label, slot in [("add", "＋ " + add_label, self.add_row), ("dup", "Dupliquer", self.duplicate_row),
                                 ("up", "▲ Monter", lambda: self.move(-1)), ("down", "▼ Descendre", lambda: self.move(1)),
                                 ("del", "✕ Supprimer", self.delete_rows)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            btns.addWidget(b)
            self.buttons[key] = b
        btns.addStretch(1)
        self.extra = btns
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addLayout(btns)
        lay.addWidget(self.table)

    # -- conversions ------------------------------------------------------
    @staticmethod
    def _fmt(kind, v) -> str:
        if v is None:
            return ""
        if kind == "date":
            return v.strftime("%d/%m/%Y")
        if kind == "datetime":
            return v.strftime("%d/%m/%Y %H:%M")
        return str(v)

    def _make_combo(self, c: Col, value: str) -> QComboBox:
        cb = QComboBox()
        cb.setEditable(c.kind == "combo")
        cb.addItems(list(c.choices))
        if value and cb.findText(value) < 0:
            cb.addItem(value)
        cb.setCurrentText(value or (c.choices[0] if c.choices else ""))
        cb.currentTextChanged.connect(lambda _: self._emit())
        return cb

    def _set_row(self, r: int, data: dict):
        for i, c in enumerate(self.cols):
            v = data.get(c.key)
            if c.kind in ("combo", "choice"):
                self.table.setCellWidget(r, i, self._make_combo(c, "" if v is None else str(v)))
            elif c.kind == "bool":
                it = QTableWidgetItem()
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                it.setCheckState(Qt.Checked if v else Qt.Unchecked)
                self.table.setItem(r, i, it)
            elif c.kind == "computed":
                it = QTableWidgetItem("")
                it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.table.setItem(r, i, it)
            else:
                txt = "?" if (c.kind == "int?" and v is None) else self._fmt(c.kind, v)
                self.table.setItem(r, i, QTableWidgetItem(txt))
        first = self.table.item(r, 0) or QTableWidgetItem()
        if self.table.item(r, 0) is None:
            self.table.setItem(r, 0, first)
        first.setData(Qt.UserRole, data.get("id"))

    def _row_data(self, r: int) -> dict:
        d = {}
        for i, c in enumerate(self.cols):
            if c.kind == "computed":
                continue
            if c.kind in ("combo", "choice"):
                w = self.table.cellWidget(r, i)
                d[c.key] = w.currentText().strip() if w else ""
            elif c.kind == "bool":
                it = self.table.item(r, i)
                d[c.key] = bool(it and it.checkState() == Qt.Checked)
            else:
                it = self.table.item(r, i)
                d[c.key] = it.text().strip() if it else ""
        it0 = self.table.item(r, 0)
        if it0 is not None and it0.data(Qt.UserRole):
            d["id"] = it0.data(Qt.UserRole)
        return d

    def _parse(self, c: Col, raw, r: int, errors: List[str]):
        try:
            if c.kind == "date":
                return parse_date(raw)
            if c.kind == "datetime":
                return parse_datetime(raw)
            if c.kind == "int?":
                return None if raw in ("", "?") else int(raw)
            if c.kind == "float?":
                return None if raw == "" else float(str(raw).replace(",", "."))
        except (ValueError, TypeError) as exc:
            errors.append(f"Ligne {r + 1}, « {c.label} » : {exc if str(exc) else 'valeur invalide'}")
            it = self.table.item(r, self.cols.index(c))
            if it:
                it.setBackground(QBrush(ERR_BG))
                it.setToolTip(str(exc))
            return None
        return raw

    # -- API ----------------------------------------------------------------
    def set_items(self, items: list):
        self._loading = True
        self.table.setRowCount(0)
        for obj in items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self._set_row(r, obj.model_dump())
        self._loading = False

    def get_items(self) -> list:
        self.errors = []
        out = []
        for r in range(self.table.rowCount()):
            raw = self._row_data(r)
            for i, c in enumerate(self.cols):
                it = self.table.item(r, i)
                if it and c.kind not in ("bool", "computed"):
                    it.setBackground(QBrush())
                    it.setToolTip("")
            if all(v in ("", False, None) for k, v in raw.items() if k != "id" and not
                   any(c.key == k and c.kind in ("combo", "choice") for c in self.cols)):
                continue
            data = {}
            for c in self.cols:
                if c.kind == "computed":
                    continue
                data[c.key] = self._parse(c, raw[c.key], r, self.errors)
            if "id" in raw:
                data["id"] = raw["id"]
            data = {k: v for k, v in data.items() if v is not None or self._optional(k)}
            out.append(self.model_cls(**data))
        return out

    def _optional(self, key) -> bool:
        from typing import get_args
        ann = self.model_cls.model_fields[key].annotation
        return type(None) in get_args(ann)

    def set_computed(self, key: str, values: List[tuple]):
        """values : (texte, info-bulle, couleur hex | None) par ligne non vide, dans l'ordre."""
        if key not in [c.key for c in self.cols]:
            return
        ci = [c.key for c in self.cols].index(key)
        self._loading = True
        for r in range(min(self.table.rowCount(), len(values))):
            txt, tip, color = values[r]
            it = self.table.item(r, ci) or QTableWidgetItem()
            it.setText(txt)
            it.setToolTip(tip)
            it.setForeground(QBrush(QColor(color)) if color else QBrush())
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.table.setItem(r, ci, it)
        self._loading = False

    def set_place_names(self, names: List[str]):
        self.place_model.setStringList(sorted(set(n for n in names if n)))

    def add_row(self, data: Optional[dict] = None):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self._loading = True
        self._set_row(r, data or self.model_cls().model_dump())
        self._loading = False
        self.table.setCurrentCell(r, 0)
        self._emit()

    def _all_rows(self) -> List[dict]:
        return [self._row_data(r) for r in range(self.table.rowCount())]

    def _rewrite(self, rows: List[dict], select: int = -1):
        self._loading = True
        self.table.setRowCount(0)
        for d in rows:
            r = self.table.rowCount()
            self.table.insertRow(r)
            # les valeurs texte sont déjà formatées
            for i, c in enumerate(self.cols):
                v = d.get(c.key)
                if c.kind in ("combo", "choice"):
                    self.table.setCellWidget(r, i, self._make_combo(c, v or ""))
                elif c.kind == "bool":
                    it = QTableWidgetItem()
                    it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                    it.setCheckState(Qt.Checked if v else Qt.Unchecked)
                    self.table.setItem(r, i, it)
                else:
                    it = QTableWidgetItem("" if v is None else str(v))
                    if c.kind == "computed":
                        it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                    self.table.setItem(r, i, it)
            if self.table.item(r, 0) is None:
                self.table.setItem(r, 0, QTableWidgetItem())
            self.table.item(r, 0).setData(Qt.UserRole, d.get("id"))
        self._loading = False
        if 0 <= select < len(rows):
            self.table.selectRow(select)
        self._emit()

    def duplicate_row(self):
        r = self.table.currentRow()
        if r < 0:
            return
        rows = self._all_rows()
        copy = dict(rows[r])
        copy.pop("id", None)
        rows.insert(r + 1, copy)
        self._rewrite(rows, r + 1)

    def move(self, delta: int):
        r = self.table.currentRow()
        rows = self._all_rows()
        j = r + delta
        if r < 0 or not (0 <= j < len(rows)):
            return
        rows[r], rows[j] = rows[j], rows[r]
        self._rewrite(rows, j)

    def delete_rows(self):
        sel = sorted({i.row() for i in self.table.selectedIndexes()} or {self.table.currentRow()}, reverse=True)
        rows = self._all_rows()
        for r in sel:
            if 0 <= r < len(rows):
                rows.pop(r)
        self._rewrite(rows, min(sel[-1] if sel else 0, len(rows) - 1))

    def sort_by(self, key_fn: Callable[[dict], object]):
        rows = self._all_rows()
        rows.sort(key=key_fn)
        self._rewrite(rows)

    def _on_item_changed(self, _item):
        self._emit()

    def _emit(self):
        if not self._loading:
            self.changed.emit()
