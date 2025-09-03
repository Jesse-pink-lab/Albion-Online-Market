from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt, QSize
from PySide6.QtGui import QIcon
from services.item_icons import ItemIconProvider
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QLabel, QPushButton,
    QTableView, QFileDialog, QSpinBox
)
from core.signals import signals
from utils.timefmt import rel_age, fmt_tooltip

COLUMNS = [
    ("Item", "item_id"),
    ("City", "city"),
    ("Quality", "quality"),
    ("Buy (max)", "buy_price_max"),
    ("Sell (min)", "sell_price_min"),
    ("Spread", "spread"),
    ("ROI %", "roi_pct"),
    ("Updated", "updated_dt"),  # render rel_age + tooltip
]

DEFAULT_CITIES = ["All Cities","Bridgewatch","Caerleon","Fort Sterling","Lymhurst","Martlock","Thetford","Black Market"]
QUALS = ["All","1","2","3","4","5"]


ICON_SIZE = 24


class ItemsModel(QAbstractTableModel):
    def __init__(self, cache_dir: str, rows: list[dict] | None = None):
        super().__init__()
        self.rows = rows or []
        self._cache_dir = cache_dir

    def rowCount(self, parent=QModelIndex()): return len(self.rows)
    def columnCount(self, parent=QModelIndex()): return len(COLUMNS)

    def data(self, idx: QModelIndex, role=Qt.DisplayRole):
        if not idx.isValid(): return None
        row = self.rows[idx.row()]
        header, key = COLUMNS[idx.column()]
        if role == Qt.DisplayRole:
            if key == "updated_dt":
                return rel_age(row.get("updated_dt"))
            val = row.get(key)
            if key == "roi_pct" and isinstance(val, (int, float)):
                return f"{val:.1f}"
            return "" if val is None else str(val)
        if role == Qt.DecorationRole and key == "item_id":
            prov = ItemIconProvider.instance(self._cache_dir)
            def cb(_pm):
                topLeft = self.index(idx.row(), 0)
                self.dataChanged.emit(topLeft, topLeft, [Qt.DecorationRole])
            pm = prov.get(row.get("item_id"), row.get("quality"), ICON_SIZE, cb)
            if not pm.isNull():
                return QIcon(pm)
            return QIcon()
        if role == Qt.ToolTipRole and key == "updated_dt":
            return fmt_tooltip(row.get("updated_dt"))
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section][0]
        return super().headerData(section, orientation, role)

    def setRows(self, rows: list[dict]):
        self.beginResetModel()
        self.rows = rows
        self.endResetModel()


class ItemsBrowser(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.rows_all: list[dict] = []
        self.rows_filtered: list[dict] = []
        self.page = 1
        self.page_size = 100

        # Controls
        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter by Item ID (e.g., T4_SWORD)")
        self.cboCity = QComboBox(); self.cboCity.addItems(DEFAULT_CITIES)
        self.cboQual = QComboBox(); self.cboQual.addItems(QUALS)
        self.lblCounts = QLabel("0 rows")
        self.btnPrev = QPushButton("◀ Prev")
        self.btnNext = QPushButton("Next ▶")
        self.spnPage = QSpinBox(); self.spnPage.setRange(1, 1)
        self.cboPageSize = QComboBox(); self.cboPageSize.addItems(["50","100","200","500"]); self.cboPageSize.setCurrentText("100")
        self.btnExport = QPushButton("Export CSV (page)")

        top.addWidget(self.search, 2)
        top.addWidget(QLabel("City:")); top.addWidget(self.cboCity)
        top.addWidget(QLabel("Quality:")); top.addWidget(self.cboQual)
        top.addWidget(QLabel("Page:")); top.addWidget(self.spnPage)
        top.addWidget(QLabel("Size:")); top.addWidget(self.cboPageSize)
        top.addWidget(self.btnPrev); top.addWidget(self.btnNext)
        top.addWidget(self.btnExport)
        top.addStretch()
        top.addWidget(self.lblCounts)

        # Table
        self.table = QTableView()
        cache_dir = self.main_window.icon_provider.cache_dir if self.main_window else ""
        self.model = ItemsModel(cache_dir, [])
        self.table.setModel(self.model)
        self.table.setSortingEnabled(True)
        self.table.setIconSize(QSize(24, 24))
        self.table.verticalHeader().setDefaultSectionSize(28)

        lay = QVBoxLayout(self)
        lay.addLayout(top)
        lay.addWidget(self.table)

        # Signals (UI)
        self.search.textChanged.connect(self._apply_filters)
        self.cboCity.currentIndexChanged.connect(self._apply_filters)
        self.cboQual.currentIndexChanged.connect(self._apply_filters)
        self.cboPageSize.currentTextChanged.connect(self._change_page_size)
        self.btnPrev.clicked.connect(self._prev)
        self.btnNext.clicked.connect(self._next)
        self.spnPage.valueChanged.connect(self._goto_page)
        self.btnExport.clicked.connect(self._export_csv)

        # App signal: new rows available
        signals.market_rows_updated.connect(self.on_rows_updated)

    # --- data flow ---
    def on_rows_updated(self, rows: list[dict]):
        self.rows_all = rows or []
        self.page = 1
        self._apply_filters()

    # --- filtering/paging ---
    def _apply_filters(self):
        text = (self.search.text() or "").strip().upper()
        city = self.cboCity.currentText()
        qual = self.cboQual.currentText()

        rf = self.rows_all
        if text:
            rf = [r for r in rf if text in (r.get("item_id","" ) or "")]
        if city and city != "All Cities":
            rf = [r for r in rf if r.get("city") == city]
        if qual and qual != "All":
            try:
                qn = int(qual)
                rf = [r for r in rf if int(r.get("quality") or 0) == qn]
            except:
                pass

        self.rows_filtered = rf
        # recompute pages
        total_pages = max(1, (len(self.rows_filtered) + self.page_size - 1) // self.page_size)
        self.spnPage.blockSignals(True)
        self.spnPage.setMaximum(total_pages)
        if self.page > total_pages:
            self.page = total_pages
        self.spnPage.setValue(self.page)
        self.spnPage.blockSignals(False)
        self._refresh_page()

    def _change_page_size(self, txt):
        try:
            self.page_size = int(txt)
        except:
            self.page_size = 100
        self.page = 1
        self._apply_filters()

    def _slice_for_page(self):
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        return start, end

    def _refresh_page(self):
        start, end = self._slice_for_page()
        page_rows = self.rows_filtered[start:end]
        self.model.setRows(page_rows)

        # counts
        total = len(self.rows_filtered)
        unique_items = len({r.get("item_id") for r in self.rows_filtered})
        if total == 0:
            rng = "0–0"
            total_pages = 1
        else:
            rng = f"{start+1}–{min(end,total)}"
            total_pages = max(1, (total + self.page_size - 1) // self.page_size)
        self.lblCounts.setText(f"Showing {rng} of {total} rows · Unique items: {unique_items} · Page {self.page}/{total_pages}")

        # nav buttons
        self.btnPrev.setEnabled(self.page > 1)
        self.btnNext.setEnabled(self.page < total_pages)

    def _prev(self):
        if self.page > 1:
            self.page -= 1
            self._refresh_page()

    def _next(self):
        total_pages = self.spnPage.maximum()
        if self.page < total_pages:
            self.page += 1
            self._refresh_page()

    def _goto_page(self, val: int):
        self.page = max(1, min(val, self.spnPage.maximum()))
        self._refresh_page()

    # --- export ---
    def _export_csv(self):
        import csv
        path, _ = QFileDialog.getSaveFileName(self, "Export current page to CSV", "items_page.csv", "CSV Files (*.csv)")
        if not path:
            return
        start, end = self._slice_for_page()
        rows = self.rows_filtered[start:end]
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([c[0] for c in COLUMNS])
            for r in rows:
                out = []
                for header, key in COLUMNS:
                    if key == "updated_dt":
                        out.append(fmt_tooltip(r.get(key)))
                    elif key == "roi_pct":
                        val = r.get(key) or 0
                        out.append(f"{val:.1f}")
                    else:
                        out.append(r.get(key, ""))
                w.writerow(out)
