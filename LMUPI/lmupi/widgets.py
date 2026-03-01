"""Reusable widget components for the LMUPI explorer."""

from __future__ import annotations

import time

import duckdb
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QFont, QKeySequence, QShortcut

from lmupi import splitter


class FilterBar(QWidget):
    """Dynamic row of per-column filter inputs with debounced signal."""

    filters_changed = Signal(dict)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._inputs: dict[str, QLineEdit] = {}
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(300)
        self._debounce.timeout.connect(self._emit_filters)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFixedHeight(36)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._inner = QWidget()
        self._inner_layout = QHBoxLayout(self._inner)
        self._inner_layout.setContentsMargins(0, 0, 0, 0)
        self._inner_layout.setSpacing(4)
        self._scroll.setWidget(self._inner)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.setFixedWidth(50)
        self._clear_btn.clicked.connect(self.clear_filters)

        self._layout.addWidget(self._scroll, 1)
        self._layout.addWidget(self._clear_btn)

    def set_columns(self, columns: list[str]) -> None:
        """Rebuild filter inputs for the given column names."""
        for inp in self._inputs.values():
            inp.deleteLater()
        self._inputs.clear()

        while self._inner_layout.count():
            item = self._inner_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for col in columns:
            inp = QLineEdit()
            inp.setPlaceholderText(col)
            inp.setMinimumWidth(80)
            inp.setMaximumWidth(160)
            inp.textChanged.connect(self._on_text_changed)
            self._inputs[col] = inp
            self._inner_layout.addWidget(inp)

        self._inner_layout.addStretch()

    def get_filters(self) -> dict[str, str]:
        return {col: inp.text() for col, inp in self._inputs.items() if inp.text().strip()}

    def clear_filters(self) -> None:
        for inp in self._inputs.values():
            inp.blockSignals(True)
            inp.clear()
            inp.blockSignals(False)
        self._emit_filters()

    def focus_first(self) -> None:
        if self._inputs:
            first = next(iter(self._inputs.values()))
            first.setFocus()

    def _on_text_changed(self) -> None:
        self._debounce.start()

    def _emit_filters(self) -> None:
        self.filters_changed.emit(self.get_filters())


class ExplorerTab(QWidget):
    """Table data explorer with schema, statistics, filters, and data preview."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._current_table: str | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Top bar: table selector + row limit
        top = QHBoxLayout()
        self._table_combo = QComboBox()
        self._table_combo.currentTextChanged.connect(self._on_table_changed)
        top.addWidget(QLabel("Table:"))
        top.addWidget(self._table_combo, 1)

        self._limit_combo = QComboBox()
        self._limit_combo.addItems(["100", "500", "1000", "All"])
        self._limit_combo.setCurrentIndex(0)
        self._limit_combo.currentTextChanged.connect(self._reload_data)
        top.addWidget(QLabel("Rows:"))
        top.addWidget(self._limit_combo)
        layout.addLayout(top)

        # Inner tabs: Schema | Statistics
        self._inner_tabs = QTabWidget()

        # Schema tab
        self._schema_table = QTableWidget()
        self._schema_table.setColumnCount(3)
        self._schema_table.setHorizontalHeaderLabels(["Column", "Type", "Nullable"])
        self._schema_table.horizontalHeader().setStretchLastSection(True)
        self._schema_table.setAlternatingRowColors(True)
        self._schema_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._inner_tabs.addTab(self._schema_table, "Schema")

        # Statistics tab
        self._stats_table = QTableWidget()
        self._stats_table.setColumnCount(6)
        self._stats_table.setHorizontalHeaderLabels(["Column", "Type", "Min", "Max", "Avg", "Nulls"])
        self._stats_table.horizontalHeader().setStretchLastSection(True)
        self._stats_table.setAlternatingRowColors(True)
        self._stats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._inner_tabs.addTab(self._stats_table, "Statistics")

        layout.addWidget(self._inner_tabs)

        # Filter bar
        self._filter_bar = FilterBar()
        self._filter_bar.filters_changed.connect(self._on_filters_changed)
        layout.addWidget(self._filter_bar)

        # Data table
        self._data_table = QTableWidget()
        self._data_table.setAlternatingRowColors(True)
        self._data_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._data_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._data_table, 1)

    @property
    def filter_bar(self) -> FilterBar:
        return self._filter_bar

    @property
    def current_table(self) -> str | None:
        return self._current_table

    def set_tables(self, tables: list[str]) -> None:
        self._table_combo.blockSignals(True)
        self._table_combo.clear()
        self._table_combo.addItems(tables)
        self._table_combo.blockSignals(False)

    def select_table(self, table: str) -> None:
        idx = self._table_combo.findText(table)
        if idx >= 0:
            self._table_combo.setCurrentIndex(idx)

    def load_table(self, conn: duckdb.DuckDBPyConnection, table: str) -> None:
        self._conn = conn
        self._current_table = table

        # Schema
        schema = splitter.table_schema(conn, table)
        self._schema_table.setRowCount(len(schema))
        for i, col in enumerate(schema):
            self._schema_table.setItem(i, 0, QTableWidgetItem(col["name"]))
            self._schema_table.setItem(i, 1, QTableWidgetItem(col["type"]))
            self._schema_table.setItem(i, 2, QTableWidgetItem("YES" if col["nullable"] else "NO"))

        # Statistics
        stats = splitter.all_column_stats(conn, table)
        self._stats_table.setRowCount(len(stats))
        for i, s in enumerate(stats):
            self._stats_table.setItem(i, 0, QTableWidgetItem(s["column"]))
            self._stats_table.setItem(i, 1, QTableWidgetItem(s["type"]))
            self._stats_table.setItem(i, 2, QTableWidgetItem(str(s["min"]) if s["min"] is not None else ""))
            self._stats_table.setItem(i, 3, QTableWidgetItem(str(s["max"]) if s["max"] is not None else ""))
            self._stats_table.setItem(i, 4, QTableWidgetItem(str(s["avg"]) if s["avg"] is not None else ""))
            self._stats_table.setItem(i, 5, QTableWidgetItem(str(s["nulls"])))

        # Filter bar columns
        columns = [col["name"] for col in schema]
        self._filter_bar.set_columns(columns)

        # Data
        self._reload_data()

    def _get_limit(self) -> int:
        text = self._limit_combo.currentText()
        return 0 if text == "All" else int(text)

    def _reload_data(self) -> None:
        if self._conn is None or self._current_table is None:
            return
        limit = self._get_limit()
        filters = self._filter_bar.get_filters()
        if filters:
            columns, rows = splitter.filtered_preview(
                self._conn, self._current_table, filters, limit or 999_999_999
            )
        else:
            columns, rows = splitter.preview_table(
                self._conn, self._current_table, limit or 999_999_999
            )
        self._populate_data(columns, rows)

    def _on_table_changed(self, table: str) -> None:
        if self._conn and table:
            self.load_table(self._conn, table)

    def _on_filters_changed(self, filters: dict[str, str]) -> None:
        self._reload_data()

    def _populate_data(self, columns: list[str], rows: list[tuple]) -> None:
        self._data_table.setColumnCount(len(columns))
        self._data_table.setHorizontalHeaderLabels(columns)
        self._data_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, val in enumerate(row):
                self._data_table.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ""))


class SqlTab(QWidget):
    """SQL query editor with results display."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._last_sql: str = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # SQL editor
        self._editor = QPlainTextEdit()
        self._editor.setPlaceholderText("Enter SQL query...")
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._editor.setFont(font)
        self._editor.setMaximumHeight(160)
        layout.addWidget(self._editor)

        # Run bar
        run_bar = QHBoxLayout()
        self._run_btn = QPushButton("Run (Ctrl+Return)")
        self._run_btn.setObjectName("accent")
        self._run_btn.clicked.connect(self.run_query)
        run_bar.addWidget(self._run_btn)

        self._status = QLabel()
        run_bar.addWidget(self._status, 1)
        layout.addLayout(run_bar)

        # Keyboard shortcut
        shortcut = QShortcut(QKeySequence("Ctrl+Return"), self._editor)
        shortcut.activated.connect(self.run_query)

        # Results table
        self._results = QTableWidget()
        self._results.setAlternatingRowColors(True)
        self._results.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._results.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self._results, 1)

    @property
    def last_sql(self) -> str:
        return self._last_sql

    def set_connection(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def run_query(self) -> None:
        if self._conn is None:
            self._status.setText("No database open")
            self._status.setObjectName("error")
            self._status.setStyleSheet("")  # force re-style
            return

        sql = self._editor.toPlainText().strip()
        if not sql:
            return

        self._last_sql = sql
        t0 = time.perf_counter()
        try:
            columns, rows = splitter.execute_sql(self._conn, sql)
            elapsed = time.perf_counter() - t0
            self._results.setColumnCount(len(columns))
            self._results.setHorizontalHeaderLabels(columns)
            self._results.setRowCount(len(rows))
            for r, row in enumerate(rows):
                for c, val in enumerate(row):
                    self._results.setItem(r, c, QTableWidgetItem(str(val) if val is not None else ""))
            self._status.setObjectName("success")
            self._status.setText(f"{len(rows)} rows in {elapsed:.3f}s")
        except duckdb.Error as exc:
            elapsed = time.perf_counter() - t0
            self._results.setRowCount(0)
            self._results.setColumnCount(0)
            self._status.setObjectName("error")
            self._status.setText(str(exc))
        self._status.setStyleSheet("")  # force QSS re-evaluation after objectName change
