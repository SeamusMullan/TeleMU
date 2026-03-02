"""LMUPI — Le Mans Ultimate telemetry explorer."""

from __future__ import annotations

from pathlib import Path

import duckdb
from PySide6.QtCore import Qt, QSettings
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
)

from lmupi import splitter
from lmupi.advanced import AdvancedAnalysis
from lmupi.analyzer import SignalAnalyzer
from lmupi.theme import DARK_STYLESHEET
from lmupi.track_viewer import TrackViewer
from lmupi.widgets import ExplorerTab, SqlTab

MAX_RECENT = 10


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("LMUPI — Telemetry Explorer")
        self.resize(1280, 800)
        self.setAcceptDrops(True)

        self._conn: duckdb.DuckDBPyConnection | None = None
        self._db_path: Path | None = None
        self._is_in_memory: bool = False
        self._settings = QSettings("LMUPI", "TelemetryExplorer")

        self._setup_menu()
        self._setup_toolbar()
        self._setup_ui()
        self._setup_statusbar()
        self._setup_shortcuts()

    # ── Menus ──────────────────────────────────────────────

    def _setup_menu(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        open_act = file_menu.addAction("&Open .duckdb...")
        open_act.setShortcut(QKeySequence("Ctrl+O"))
        open_act.triggered.connect(self._open_file)

        self._recent_menu = QMenu("Recent Files", self)
        file_menu.addMenu(self._recent_menu)
        self._rebuild_recent_menu()

        file_menu.addSeparator()

        export_csv_act = file_menu.addAction("Export &CSV...")
        export_csv_act.setShortcut(QKeySequence("Ctrl+E"))
        export_csv_act.triggered.connect(self._export_csv)

        export_json_act = file_menu.addAction("Export &JSON...")
        export_json_act.setShortcut(QKeySequence("Ctrl+Shift+E"))
        export_json_act.triggered.connect(self._export_json)

        file_menu.addSeparator()

        import_csv_act = file_menu.addAction("&Import CSV...")
        import_csv_act.setShortcut(QKeySequence("Ctrl+I"))
        import_csv_act.triggered.connect(self._import_csv)

        import_json_act = file_menu.addAction("Import &JSON...")
        import_json_act.setShortcut(QKeySequence("Ctrl+Shift+I"))
        import_json_act.triggered.connect(self._import_json)

        file_menu.addSeparator()

        quit_act = file_menu.addAction("&Quit")
        quit_act.setShortcut(QKeySequence("Ctrl+Q"))
        quit_act.triggered.connect(self.close)

    # ── Toolbar ────────────────────────────────────────────

    def _setup_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        open_act = tb.addAction("Open")
        open_act.triggered.connect(self._open_file)

        tb.addSeparator()

        csv_act = tb.addAction("Export CSV")
        csv_act.triggered.connect(self._export_csv)

        json_act = tb.addAction("Export JSON")
        json_act.triggered.connect(self._export_json)

        tb.addSeparator()

        imp_csv_act = tb.addAction("Import CSV")
        imp_csv_act.triggered.connect(self._import_csv)

        imp_json_act = tb.addAction("Import JSON")
        imp_json_act.triggered.connect(self._import_json)

        tb.addSeparator()

        run_act = tb.addAction("Run SQL")
        run_act.triggered.connect(self._run_sql_from_toolbar)

        tb.addSeparator()

        analyze_act = tb.addAction("Analyze")
        analyze_act.triggered.connect(self._focus_analyzer)

    # ── Central UI ─────────────────────────────────────────

    def _setup_ui(self) -> None:
        splitter_widget = QSplitter(Qt.Orientation.Horizontal)

        # Left: table tree
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Tables"])
        self._tree.setMinimumWidth(180)
        self._tree.itemClicked.connect(self._on_tree_item_clicked)
        splitter_widget.addWidget(self._tree)

        # Right: tab widget
        self._tabs = QTabWidget()

        self._explorer = ExplorerTab()
        self._tabs.addTab(self._explorer, "Explorer")

        self._sql_tab = SqlTab()
        self._tabs.addTab(self._sql_tab, "SQL Query")

        self._analyzer = SignalAnalyzer()
        self._tabs.addTab(self._analyzer, "Signal Analyzer")

        self._track_viewer = TrackViewer()
        self._tabs.addTab(self._track_viewer, "Track Viewer")

        self._advanced = AdvancedAnalysis()
        self._tabs.addTab(self._advanced, "Advanced Analysis")

        splitter_widget.addWidget(self._tabs)
        splitter_widget.setSizes([220, 1060])

        self.setCentralWidget(splitter_widget)

    def _setup_statusbar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("No database loaded — open a .duckdb file or drag one here")

    def _setup_shortcuts(self) -> None:
        focus_filter = QAction(self)
        focus_filter.setShortcut(QKeySequence("Ctrl+F"))
        focus_filter.triggered.connect(self._focus_filter)
        self.addAction(focus_filter)

        focus_analyzer = QAction(self)
        focus_analyzer.setShortcut(QKeySequence("Ctrl+G"))
        focus_analyzer.triggered.connect(self._focus_analyzer)
        self.addAction(focus_analyzer)

    # ── Drag and drop ──────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                if url.toLocalFile().endswith((".duckdb", ".csv", ".json")):
                    event.acceptProposedAction()
                    return

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(".duckdb"):
                self._load_db(Path(path))
                return
            elif path.endswith(".csv"):
                self._do_import("csv", Path(path))
                return
            elif path.endswith(".json"):
                self._do_import("json", Path(path))
                return

    # ── File operations ────────────────────────────────────

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open DuckDB file", "", "DuckDB Files (*.duckdb);;All Files (*)"
        )
        if path:
            self._load_db(Path(path))

    def _load_db(self, path: Path) -> None:
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass

        try:
            self._conn = splitter.connect(path)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not open database:\n{exc}")
            return

        self._db_path = path
        self._is_in_memory = False
        self._add_recent(path)

        tables = splitter.list_tables(self._conn)
        self._populate_tree(tables, path.name)
        self._explorer.set_tables(tables)
        self._sql_tab.set_connection(self._conn)
        self._analyzer.set_connection(self._conn)
        self._analyzer.set_tables(tables)
        self._track_viewer.set_connection(self._conn)
        self._track_viewer.set_tables(tables)
        self._advanced.set_connection(self._conn)
        self._advanced.set_tables(tables)

        if tables:
            self._explorer.load_table(self._conn, tables[0])
            self._explorer.select_table(tables[0])

        self._status.showMessage(f"{path.name} — {len(tables)} tables")

    # ── Recent files ───────────────────────────────────────

    @staticmethod
    def _settings_list(val) -> list[str]:
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            return [val]
        return []

    def _add_recent(self, path: Path) -> None:
        recent = self._settings_list(self._settings.value("recent_files", []))
        s = str(path)
        if s in recent:
            recent.remove(s)
        recent.insert(0, s)
        recent = recent[:MAX_RECENT]
        self._settings.setValue("recent_files", recent)
        self._rebuild_recent_menu()

    def _rebuild_recent_menu(self) -> None:
        self._recent_menu.clear()
        recent = self._settings_list(self._settings.value("recent_files", []))
        if not recent:
            no_act = self._recent_menu.addAction("(none)")
            no_act.setEnabled(False)
            return
        for filepath in recent:
            act = self._recent_menu.addAction(Path(filepath).name)
            act.setData(filepath)
            act.triggered.connect(lambda checked=False, p=filepath: self._load_db(Path(p)))

    # ── Tree ───────────────────────────────────────────────

    def _populate_tree(self, tables: list[str], filename: str) -> None:
        self._tree.clear()
        root = QTreeWidgetItem(self._tree, [filename])
        root.setExpanded(True)
        for table in tables:
            count = splitter.table_row_count(self._conn, table)
            item = QTreeWidgetItem(root, [f"{table}  ({count:,} rows)"])
            item.setData(0, Qt.ItemDataRole.UserRole, table)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        table = item.data(0, Qt.ItemDataRole.UserRole)
        if table and self._conn:
            self._explorer.load_table(self._conn, table)
            self._explorer.select_table(table)
            self._tabs.setCurrentWidget(self._explorer)

    # ── Export ─────────────────────────────────────────────

    def _export_csv(self) -> None:
        self._export("csv")

    def _export_json(self) -> None:
        self._export("json")

    def _export(self, fmt: str) -> None:
        if self._conn is None:
            QMessageBox.warning(self, "No database", "Open a database first.")
            return

        ext = "csv" if fmt == "csv" else "json"
        filter_str = f"{ext.upper()} Files (*.{ext})"
        path, _ = QFileDialog.getSaveFileName(self, f"Export {ext.upper()}", "", filter_str)
        if not path:
            return

        try:
            # If SQL tab is active and has a query, export query results
            if self._tabs.currentWidget() is self._sql_tab and self._sql_tab.last_sql:
                if fmt == "csv":
                    splitter.export_query_csv(self._conn, self._sql_tab.last_sql, path)
                else:
                    splitter.export_query_json(self._conn, self._sql_tab.last_sql, path)
                self._status.showMessage(f"Exported query results to {path}")
            else:
                table = self._explorer.current_table
                if not table:
                    QMessageBox.warning(self, "No table", "Select a table first.")
                    return
                if fmt == "csv":
                    splitter.export_csv(self._conn, table, path)
                else:
                    splitter.export_json(self._conn, table, path)
                self._status.showMessage(f"Exported {table} to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Export Error", str(exc))

    # ── Import ─────────────────────────────────────────────

    def _import_csv(self) -> None:
        self._do_import("csv")

    def _import_json(self) -> None:
        self._do_import("json")

    def _do_import(self, fmt: str, path: Path | None = None) -> None:
        if path is None:
            ext = fmt
            filter_str = f"{ext.upper()} Files (*.{ext});;All Files (*)"
            p, _ = QFileDialog.getOpenFileName(self, f"Import {ext.upper()}", "", filter_str)
            if not p:
                return
            path = Path(p)

        table_name = path.stem

        # Reuse existing in-memory connection so multiple imports stack
        if self._conn is not None and self._is_in_memory:
            conn = self._conn
            existing = splitter.list_tables(conn)
            base = table_name
            i = 1
            while table_name in existing:
                table_name = f"{base}_{i}"
                i += 1
        else:
            if self._conn is not None:
                try:
                    self._conn.close()
                except Exception:
                    pass
            conn = duckdb.connect(":memory:")
            self._is_in_memory = True

        try:
            if fmt == "csv":
                splitter.import_csv(conn, str(path), table_name)
            else:
                splitter.import_json(conn, str(path), table_name)
        except Exception as exc:
            QMessageBox.critical(self, "Import Error", f"Could not import file:\n{exc}")
            return

        self._conn = conn
        self._db_path = None

        tables = splitter.list_tables(self._conn)
        self._populate_tree(tables, f"[imported] {path.name}")
        self._explorer.set_tables(tables)
        self._sql_tab.set_connection(self._conn)
        self._analyzer.set_connection(self._conn)
        self._analyzer.set_tables(tables)
        self._track_viewer.set_connection(self._conn)
        self._track_viewer.set_tables(tables)
        self._advanced.set_connection(self._conn)
        self._advanced.set_tables(tables)

        if tables:
            self._explorer.load_table(self._conn, tables[0])
            self._explorer.select_table(tables[0])

        self._status.showMessage(
            f"Imported '{path.name}' as table '{table_name}' — {len(tables)} table(s) loaded"
        )

    # ── Misc actions ───────────────────────────────────────

    def _run_sql_from_toolbar(self) -> None:
        self._tabs.setCurrentWidget(self._sql_tab)
        self._sql_tab.run_query()

    def _focus_analyzer(self) -> None:
        self._tabs.setCurrentWidget(self._analyzer)

    def _focus_filter(self) -> None:
        self._tabs.setCurrentWidget(self._explorer)
        self._explorer.filter_bar.focus_first()


def run() -> None:
    app = QApplication([])
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    app.exec()
