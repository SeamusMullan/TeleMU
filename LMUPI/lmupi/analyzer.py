"""Signal Analyzer — multi-table, multi-variable comparison plotting widget."""

from __future__ import annotations

import datetime

import numpy as np
import duckdb
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.colors import Normalize as plt_Normalize
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lmupi import splitter
from lmupi.theme import PLOT_COLORS, apply_plot_theme

PLOT_TYPES = [
    "Line",
    "Scatter",
    "Histogram",
    "Track Map",
    "Correlation Matrix",
    "Cross-Correlation",
    "Correlation Finder",
]

# Table names we recognise as GPS latitude / longitude (case-insensitive check)
_LAT_TABLE_NAMES = {"latitude", "lat", "gps_lat", "gps latitude", "gpslat", "gps_latitude"}
_LON_TABLE_NAMES = {"longitude", "lon", "lng", "gps_lon", "gps longitude", "gpslon", "gpslng", "gps_longitude"}
_SPEED_TABLE_NAMES = {"speed", "gps speed", "gps_speed", "gpsspeed", "velocity"}


def _to_float(val):
    """Convert a value to float, handling datetime objects and None."""
    if val is None:
        return np.nan
    if isinstance(val, datetime.datetime):
        return val.timestamp()
    try:
        return float(val)
    except (ValueError, TypeError):
        return np.nan


class SignalAnalyzer(QWidget):
    """Plotting widget for overlaying and comparing telemetry signals."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._tables: list[str] = []

        self._fig = Figure(tight_layout=True)
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter_widget = QSplitter(Qt.Orientation.Horizontal)

        # ── Left sidebar ──
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self._signals_label = QLabel("Signals")
        sidebar_layout.addWidget(self._signals_label)

        self._signal_tree = QTreeWidget()
        self._signal_tree.setHeaderHidden(True)
        self._signal_tree.itemChanged.connect(self._on_tree_changed)
        sidebar_layout.addWidget(self._signal_tree, stretch=1)

        sidebar_layout.addWidget(QLabel("X:"))
        self._x_combo = QComboBox()
        self._x_combo.addItems(["ts", "(row index)"])
        sidebar_layout.addWidget(self._x_combo)

        sidebar_layout.addWidget(QLabel("Type:"))
        self._type_combo = QComboBox()
        self._type_combo.addItems(PLOT_TYPES)
        sidebar_layout.addWidget(self._type_combo)

        self._normalize_cb = QCheckBox("Normalize (0-1)")
        sidebar_layout.addWidget(self._normalize_cb)

        # ── Filters group ──
        filters_box = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_box)
        filters_layout.setContentsMargins(4, 4, 4, 4)

        self._exclude_zeros_cb = QCheckBox("Exclude zeros")
        filters_layout.addWidget(self._exclude_zeros_cb)

        self._exclude_nan_cb = QCheckBox("Exclude NaN")
        filters_layout.addWidget(self._exclude_nan_cb)

        filters_layout.addWidget(QLabel("From:"))
        self._range_from = QLineEdit()
        self._range_from.setPlaceholderText("start")
        filters_layout.addWidget(self._range_from)

        filters_layout.addWidget(QLabel("To:"))
        self._range_to = QLineEdit()
        self._range_to.setPlaceholderText("end")
        filters_layout.addWidget(self._range_to)

        filters_layout.addWidget(QLabel("Min:"))
        self._val_min = QLineEdit()
        self._val_min.setPlaceholderText("min")
        filters_layout.addWidget(self._val_min)

        filters_layout.addWidget(QLabel("Max:"))
        self._val_max = QLineEdit()
        self._val_max.setPlaceholderText("max")
        filters_layout.addWidget(self._val_max)

        sidebar_layout.addWidget(filters_box)

        self._plot_btn = QPushButton("Plot")
        self._plot_btn.setObjectName("accent")
        self._plot_btn.clicked.connect(self._plot)
        sidebar_layout.addWidget(self._plot_btn)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        sidebar_layout.addWidget(self._status_label)

        sidebar.setMinimumWidth(180)

        # ── Right plot area ──
        plot_area = QWidget()
        plot_layout = QVBoxLayout(plot_area)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self._toolbar)
        plot_layout.addWidget(self._canvas, stretch=1)

        splitter_widget.addWidget(sidebar)
        splitter_widget.addWidget(plot_area)
        splitter_widget.setSizes([220, 600])

        layout.addWidget(splitter_widget)

    # ── Public API ──

    def set_connection(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def set_tables(self, tables: list[str]) -> None:
        self._tables = tables
        self._signal_tree.blockSignals(True)
        self._signal_tree.clear()
        self._tables_with_ts: set[str] = set()
        if not self._conn:
            self._signal_tree.blockSignals(False)
            return
        # Check which tables have a ts column
        for tbl in tables:
            schema = splitter.table_schema(self._conn, tbl)
            if any(col["name"] == "ts" for col in schema):
                self._tables_with_ts.add(tbl)
        all_cols = splitter.all_numeric_columns(self._conn, tables)
        for table, cols in all_cols.items():
            has_ts = table in self._tables_with_ts
            label = table if has_ts else f"{table}  (no ts)"
            parent = QTreeWidgetItem(self._signal_tree, [label])
            parent.setData(0, Qt.ItemDataRole.UserRole, table)
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.CheckState.Unchecked)
            if not has_ts:
                parent.setForeground(0, Qt.GlobalColor.darkYellow)
            for col in cols:
                child = QTreeWidgetItem(parent, [col])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
        self._signal_tree.expandAll()
        self._signal_tree.blockSignals(False)
        self._update_signals_label()

    # ── Helpers ──

    def _on_tree_changed(self) -> None:
        self._update_signals_label()

    def _update_signals_label(self) -> None:
        count = sum(
            len(cols) for cols in self._get_selected_signals().values()
        )
        self._signals_label.setText(f"Signals ({count})" if count else "Signals")

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _get_selected_signals(self) -> dict[str, list[str]]:
        """Read checked items from the tree, returns {table: [cols]}."""
        result: dict[str, list[str]] = {}
        root = self._signal_tree.invisibleRootItem()
        for i in range(root.childCount()):
            table_item = root.child(i)
            table_name = table_item.data(0, Qt.ItemDataRole.UserRole) or table_item.text(0)
            for j in range(table_item.childCount()):
                col_item = table_item.child(j)
                if col_item.checkState(0) == Qt.CheckState.Checked:
                    result.setdefault(table_name, []).append(col_item.text(0))
        return result

    def _fetch_data(
        self, signals: dict[str, list[str]], x_col: str | None
    ) -> tuple[list[str], list[tuple]]:
        """Fetch data for the selected signals. Joins across tables if needed."""
        if not self._conn:
            return [], []

        tables = list(signals.keys())
        if not tables:
            return [], []

        fetch_signals: dict[str, list[str]] = {
            tbl: list(cols) for tbl, cols in signals.items()
        }

        if len(tables) == 1:
            tbl = tables[0]
            cols = fetch_signals[tbl]
            # Only include x_col if the table actually has it
            has_ts = hasattr(self, "_tables_with_ts") and tbl in self._tables_with_ts
            if x_col and x_col not in cols:
                if x_col == "ts" and not has_ts:
                    # Table lacks ts — can't use it as X axis
                    pass
                else:
                    cols = [x_col] + cols
            # Deduplicate preserving order
            seen: set[str] = set()
            unique: list[str] = []
            for c in cols:
                if c not in seen:
                    seen.add(c)
                    unique.append(c)
            col_names, rows = splitter.fetch_columns(self._conn, tbl, unique)
            # Prefix column names with table name for consistency
            prefixed = []
            for c in col_names:
                prefixed.append(f"{tbl}.{c}")
            return prefixed, rows
        else:
            # Split tables into joinable (have ts) and non-joinable
            ts_tables = getattr(self, "_tables_with_ts", set())
            joinable = {t: c for t, c in fetch_signals.items() if t in ts_tables}
            non_joinable = {t: c for t, c in fetch_signals.items() if t not in ts_tables}

            # If we can join on ts, do that for the joinable tables
            if x_col == "ts" and len(joinable) >= 2:
                if non_joinable:
                    self._set_status(
                        f"Skipped {len(non_joinable)} table(s) without 'ts': "
                        f"{', '.join(sorted(non_joinable))}"
                    )
                return splitter.fetch_joined_columns(self._conn, joinable, on="ts")

            # Otherwise fetch each table independently, align by row index
            all_col_names: list[str] = []
            all_columns: list[np.ndarray] = []
            min_rows = float("inf")

            for tbl, cols in fetch_signals.items():
                tbl_cols = list(cols)
                # Include x_col if available in this table
                if x_col and x_col not in tbl_cols and tbl in ts_tables:
                    tbl_cols = [x_col] + tbl_cols
                col_names, rows = splitter.fetch_columns(self._conn, tbl, tbl_cols)
                if not rows:
                    continue
                min_rows = min(min_rows, len(rows))
                for i, c in enumerate(col_names):
                    prefixed = f"{tbl}.{c}"
                    all_col_names.append(prefixed)
                    all_columns.append([row[i] for row in rows])

            if not all_columns or min_rows == float("inf"):
                return [], []

            # Truncate all columns to shortest table length
            min_rows = int(min_rows)
            combined_rows = [
                tuple(col[r] for col in all_columns)
                for r in range(min_rows)
            ]
            if non_joinable and joinable:
                self._set_status(
                    f"Row-aligned {len(fetch_signals)} tables "
                    f"(truncated to {min_rows} rows)"
                )
            return all_col_names, combined_rows

    def _apply_filters(
        self, data: np.ndarray, col_idx: dict[str, int], x_key: str | None
    ) -> tuple[np.ndarray, int]:
        """Apply sidebar filters to data. Returns (filtered_data, excluded_count)."""
        n_before = len(data)
        mask = np.ones(n_before, dtype=bool)

        # --- Range filter (from / to) ---
        def _parse_float(widget: QLineEdit) -> float | None:
            txt = widget.text().strip()
            if not txt:
                return None
            try:
                return float(txt)
            except ValueError:
                return None

        range_from = _parse_float(self._range_from)
        range_to = _parse_float(self._range_to)

        if range_from is not None or range_to is not None:
            if x_key is not None and x_key in col_idx:
                x_vals = data[:, col_idx[x_key]]
            else:
                x_vals = np.arange(n_before, dtype=float)
            if range_from is not None:
                mask &= x_vals >= range_from
            if range_to is not None:
                mask &= x_vals <= range_to

        # --- Determine y-column indices ---
        y_indices = [i for name, i in col_idx.items() if name != x_key]

        if y_indices:
            y_data = data[:, y_indices]

            # --- Value clamp (min / max) ---
            # Use nanmin/nanmax so NaN-only rows pass through (caught by NaN filter)
            val_min = _parse_float(self._val_min)
            val_max = _parse_float(self._val_max)
            all_nan_rows = np.all(np.isnan(y_data), axis=1)
            if val_min is not None:
                with np.errstate(invalid="ignore"):
                    row_mins = np.nanmin(y_data, axis=1)
                mask &= (row_mins >= val_min) | all_nan_rows
            if val_max is not None:
                with np.errstate(invalid="ignore"):
                    row_maxs = np.nanmax(y_data, axis=1)
                mask &= (row_maxs <= val_max) | all_nan_rows

            # --- Exclude NaN ---
            if self._exclude_nan_cb.isChecked():
                mask &= ~np.any(np.isnan(y_data), axis=1)

            # --- Exclude zeros ---
            if self._exclude_zeros_cb.isChecked():
                mask &= ~np.any(y_data == 0, axis=1)

        filtered = data[mask]
        return filtered, n_before - len(filtered)

    def _style_legend(self) -> None:
        for leg in [a.get_legend() for a in self._fig.get_axes() if a.get_legend()]:
            leg.get_frame().set_facecolor("#242424")
            leg.get_frame().set_edgecolor("#3a3a3a")
            for t in leg.get_texts():
                t.set_color("#d4d4d4")

    # ── Main plot dispatch ──

    def _plot(self) -> None:
        if not self._conn:
            self._set_status("No database connection")
            return

        plot_type = self._type_combo.currentText()

        # Correlation Finder and Track Map use all tables, no manual selection needed
        if plot_type == "Correlation Finder":
            self._fig.clear()
            self._plot_correlation_finder()
            self._canvas.draw()
            return

        if plot_type == "Track Map":
            self._fig.clear()
            self._plot_track_map(self._get_selected_signals())
            self._canvas.draw()
            return

        signals = self._get_selected_signals()
        if not signals:
            self._set_status("Select at least one signal")
            return

        x_choice = self._x_combo.currentText()
        use_index = x_choice == "(row index)"
        x_col = None if use_index else x_choice
        normalize = self._normalize_cb.isChecked()

        col_names, rows = self._fetch_data(signals, x_col)
        if not rows:
            self._set_status("No data returned")
            return

        # Build numpy arrays
        data = np.array([[_to_float(v) for v in row] for row in rows])
        col_idx = {c: i for i, c in enumerate(col_names)}

        # X data — resolve x_key before filtering so range filter can use it
        if use_index:
            x_label = "Row Index"
            x_key = None
        else:
            # Find the ts / x column (may be prefixed with table name)
            x_key = None
            for c in col_names:
                if c == x_col or c.endswith(f".{x_col}"):
                    x_key = c
                    break
            if x_key is None:
                x_label = "Row Index"
                x_key = None
                self._set_status(f"'{x_col}' not in selected table(s), using row index")
            else:
                x_label = x_col

        # Apply filters
        data, excluded = self._apply_filters(data, col_idx, x_key)
        if len(data) == 0:
            self._set_status("All data excluded by filters")
            return

        # X data (after filtering)
        if x_key is None:
            x_data = np.arange(len(data))
        else:
            x_data = data[:, col_idx[x_key]]

        # Bug 2 fix: build y_arrays from what col_idx actually contains,
        # not from the original signals dict (which may reference tables
        # that were filtered out during the join).
        y_arrays: dict[str, np.ndarray] = {}
        for col_name in col_names:
            if col_name == x_key:
                continue
            arr = data[:, col_idx[col_name]]
            if normalize:
                mn, mx = np.nanmin(arr), np.nanmax(arr)
                if mx - mn > 0:
                    arr = (arr - mn) / (mx - mn)
            y_arrays[col_name] = arr

        if not y_arrays:
            self._set_status("No plottable signals after filtering")
            return

        self._fig.clear()

        if plot_type == "Cross-Correlation":
            keys = list(y_arrays.keys())
            if len(keys) != 2:
                self._set_status("Select exactly 2 signals for Cross-Correlation")
                ax = self._fig.add_subplot(111)
                ax.text(0.5, 0.5, "Select exactly 2 signals for Cross-Correlation",
                        transform=ax.transAxes, ha="center", va="center",
                        color="#d4d4d4", fontsize=12)
                apply_plot_theme(self._fig, ax)
            else:
                self._plot_cross_correlation(
                    y_arrays[keys[0]], y_arrays[keys[1]], keys[0], keys[1]
                )
                self._set_status(f"Plotted cross-correlation ({len(data)} points, {excluded} excluded)")
        elif plot_type == "Correlation Matrix":
            self._plot_correlation(y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(data)} points, {excluded} excluded)")
        elif plot_type == "Histogram":
            self._plot_histogram(y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(data)} points, {excluded} excluded)")
        elif plot_type == "Scatter":
            self._plot_scatter(x_data, x_label, y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(data)} points, {excluded} excluded)")
        else:
            self._plot_line(x_data, x_label, y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(data)} points, {excluded} excluded)")

        self._canvas.draw()

    # ── Plot methods ──

    def _plot_line(self, x: np.ndarray, x_label: str, y_arrays: dict[str, np.ndarray]) -> None:
        cols = list(y_arrays.keys())

        # Dual y-axis: when exactly 2 vars with ranges differing >10x
        use_twin = False
        if len(cols) == 2:
            r0 = np.nanmax(y_arrays[cols[0]]) - np.nanmin(y_arrays[cols[0]])
            r1 = np.nanmax(y_arrays[cols[1]]) - np.nanmin(y_arrays[cols[1]])
            if r0 > 0 and r1 > 0:
                ratio = max(r0, r1) / min(r0, r1)
                use_twin = ratio > 10

        ax = self._fig.add_subplot(111)
        ax.set_xlabel(x_label)

        if use_twin:
            c0, c1 = PLOT_COLORS[0], PLOT_COLORS[1]
            ax.plot(x, y_arrays[cols[0]], color=c0, label=cols[0], linewidth=1)
            ax.set_ylabel(cols[0], color=c0)
            ax.tick_params(axis="y", labelcolor=c0)

            ax2 = ax.twinx()
            ax2.plot(x, y_arrays[cols[1]], color=c1, label=cols[1], linewidth=1)
            ax2.set_ylabel(cols[1], color=c1)
            ax2.tick_params(axis="y", labelcolor=c1)

            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
        else:
            for i, (name, arr) in enumerate(y_arrays.items()):
                color = PLOT_COLORS[i % len(PLOT_COLORS)]
                ax.plot(x, arr, color=color, label=name, linewidth=1)
            ax.legend(loc="upper left", fontsize=8)

        apply_plot_theme(self._fig, ax)
        self._style_legend()

    def _plot_scatter(self, x: np.ndarray, x_label: str, y_arrays: dict[str, np.ndarray]) -> None:
        ax = self._fig.add_subplot(111)
        ax.set_xlabel(x_label)
        for i, (name, arr) in enumerate(y_arrays.items()):
            color = PLOT_COLORS[i % len(PLOT_COLORS)]
            ax.scatter(x, arr, c=color, label=name, s=4, alpha=0.7)
        ax.legend(loc="upper left", fontsize=8)
        apply_plot_theme(self._fig, ax)
        self._style_legend()

    def _plot_histogram(self, y_arrays: dict[str, np.ndarray]) -> None:
        ax = self._fig.add_subplot(111)
        for i, (name, arr) in enumerate(y_arrays.items()):
            color = PLOT_COLORS[i % len(PLOT_COLORS)]
            ax.hist(arr[~np.isnan(arr)], bins=50, color=color, label=name, alpha=0.6)
        ax.legend(loc="upper right", fontsize=8)
        apply_plot_theme(self._fig, ax)
        self._style_legend()

    def _plot_correlation(self, y_arrays: dict[str, np.ndarray]) -> None:
        names = list(y_arrays.keys())
        matrix = np.column_stack([y_arrays[n] for n in names])
        mask = ~np.isnan(matrix).any(axis=1)
        matrix = matrix[mask]
        if len(matrix) < 2:
            self._set_status("Not enough data for correlation matrix")
            return

        corr = np.corrcoef(matrix, rowvar=False)

        ax = self._fig.add_subplot(111)
        im = ax.imshow(corr, vmin=-1, vmax=1, cmap="RdYlGn", aspect="auto")
        self._fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

        ax.set_xticks(range(len(names)))
        ax.set_yticks(range(len(names)))
        ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
        ax.set_yticklabels(names, fontsize=8)

        for i in range(len(names)):
            for j in range(len(names)):
                ax.text(j, i, f"{corr[i, j]:.2f}", ha="center", va="center",
                        color="black" if abs(corr[i, j]) < 0.7 else "white", fontsize=8)

        apply_plot_theme(self._fig, ax)

    def _plot_cross_correlation(
        self, signal_a: np.ndarray, signal_b: np.ndarray, name_a: str, name_b: str
    ) -> None:
        from scipy.signal import correlate

        # Drop NaN — use pairwise valid
        valid = ~(np.isnan(signal_a) | np.isnan(signal_b))
        a = signal_a[valid]
        b = signal_b[valid]
        if len(a) < 2:
            self._set_status("Not enough valid data for cross-correlation")
            return

        # Normalize to zero mean, unit variance for meaningful coefficients
        a = (a - np.mean(a)) / (np.std(a) + 1e-12)
        b = (b - np.mean(b)) / (np.std(b) + 1e-12)

        corr = correlate(a, b, mode="full") / len(a)
        lags = np.arange(-len(b) + 1, len(a))

        ax = self._fig.add_subplot(111)
        ax.plot(lags, corr, color=PLOT_COLORS[0], linewidth=1)
        ax.set_xlabel("Lag (samples)")
        ax.set_ylabel("Correlation")
        ax.set_title(f"Cross-Correlation: {name_a} vs {name_b}", fontsize=10)

        # Mark peak
        peak_idx = np.argmax(np.abs(corr))
        peak_lag = lags[peak_idx]
        peak_val = corr[peak_idx]
        ax.axvline(peak_lag, color=PLOT_COLORS[3], linestyle="--", linewidth=1, alpha=0.8)
        ax.annotate(
            f"peak lag={peak_lag}\nr={peak_val:.3f}",
            xy=(peak_lag, peak_val),
            xytext=(peak_lag + len(a) * 0.05, peak_val * 0.9),
            fontsize=9,
            color="#d4d4d4",
            arrowprops=dict(arrowstyle="->", color="#888888"),
        )

        apply_plot_theme(self._fig, ax)

    def _plot_correlation_finder(self) -> None:
        if not self._conn or not self._tables:
            self._set_status("No tables loaded")
            return

        from scipy.stats import spearmanr

        all_cols = splitter.all_numeric_columns(self._conn, self._tables)

        # Build table_columns requesting all numeric cols (exclude ts)
        table_columns: dict[str, list[str]] = {}
        for tbl, cols in all_cols.items():
            non_ts = [c for c in cols if c != "ts"]
            if non_ts:
                table_columns[tbl] = non_ts

        if len(table_columns) < 2:
            self._set_status("Need at least 2 tables with numeric columns")
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "Need at least 2 tables with numeric columns",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#d4d4d4", fontsize=12)
            apply_plot_theme(self._fig, ax)
            return

        # Try ts-join first; fall back to row-aligned independent fetches
        ts_tables = getattr(self, "_tables_with_ts", set())
        joinable = {t: c for t, c in table_columns.items() if t in ts_tables}

        col_names: list[str] = []
        rows: list[tuple] = []

        if len(joinable) >= 2:
            try:
                col_names, rows = splitter.fetch_joined_columns(self._conn, joinable, on="ts")
            except Exception:
                pass

        if not rows:
            # Fetch each table independently, align by row index
            all_col_names: list[str] = []
            all_columns: list[list] = []
            min_rows = float("inf")
            for tbl, cols in table_columns.items():
                cnames, trows = splitter.fetch_columns(self._conn, tbl, cols)
                if not trows:
                    continue
                min_rows = min(min_rows, len(trows))
                for i, c in enumerate(cnames):
                    all_col_names.append(f"{tbl}.{c}")
                    all_columns.append([row[i] for row in trows])
            if all_columns and min_rows != float("inf"):
                min_rows = int(min_rows)
                col_names = all_col_names
                rows = [
                    tuple(col[r] for col in all_columns)
                    for r in range(min_rows)
                ]

        if not rows or len(col_names) < 2:
            self._set_status("No data returned")
            return

        data = np.array([[_to_float(v) for v in row] for row in rows])

        signal_cols = [c for c in col_names if c != "ts"]
        if len(signal_cols) < 2:
            self._set_status("Not enough signal columns")
            return

        # Compute pairwise correlations
        pairs: list[tuple[str, str, float, float]] = []
        for i in range(len(signal_cols)):
            for j in range(i + 1, len(signal_cols)):
                ci, cj = signal_cols[i], signal_cols[j]
                idx_i = col_names.index(ci)
                idx_j = col_names.index(cj)
                a = data[:, idx_i]
                b = data[:, idx_j]
                valid = ~(np.isnan(a) | np.isnan(b))
                a_v, b_v = a[valid], b[valid]
                if len(a_v) < 3:
                    continue
                pearson = np.corrcoef(a_v, b_v)[0, 1]
                spear, _ = spearmanr(a_v, b_v)
                pairs.append((ci, cj, float(pearson), float(spear)))

        if not pairs:
            self._set_status("No valid correlation pairs found")
            return

        # Sort by absolute Pearson, take top 20
        pairs.sort(key=lambda p: abs(p[2]), reverse=True)
        top = pairs[:20]

        labels = [f"{a} vs {b}" for a, b, _, _ in top]
        pearson_vals = [p for _, _, p, _ in top]
        colors = ["#27ae60" if v >= 0 else "#d63031" for v in pearson_vals]

        ax = self._fig.add_subplot(111)
        y_pos = np.arange(len(top))
        ax.barh(y_pos, pearson_vals, color=colors, height=0.7)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=7)
        ax.set_xlabel("Pearson r")
        ax.set_title("Top Correlations Across Tables", fontsize=10)
        ax.invert_yaxis()
        ax.axvline(0, color="#3a3a3a", linewidth=0.5)

        # Annotate bars with r-values
        for i, (_, _, r, sr) in enumerate(top):
            ax.text(
                r + (0.02 if r >= 0 else -0.02),
                i,
                f"r={r:.2f} ρ={sr:.2f}",
                va="center",
                ha="left" if r >= 0 else "right",
                fontsize=7,
                color="#d4d4d4",
            )

        self._set_status(f"Found {len(pairs)} correlation pairs ({len(rows)} rows)")
        apply_plot_theme(self._fig, ax)

    # ── Track Map ──

    def _find_gps_tables(self) -> tuple[str | None, str | None, str | None]:
        """Search tables by name for lat, lon, and optionally speed.

        Returns (lat_table, lon_table, speed_table). Any may be None.
        """
        lat_table = lon_table = speed_table = None
        for tbl in self._tables:
            tbl_lower = tbl.lower().strip()
            if tbl_lower in _LAT_TABLE_NAMES and lat_table is None:
                lat_table = tbl
            elif tbl_lower in _LON_TABLE_NAMES and lon_table is None:
                lon_table = tbl
            elif tbl_lower in _SPEED_TABLE_NAMES and speed_table is None:
                speed_table = tbl
        return lat_table, lon_table, speed_table

    def _plot_track_map(self, signals: dict[str, list[str]] | None = None) -> None:
        if not self._conn:
            self._set_status("No database connection")
            return

        lat_table, lon_table, _ = self._find_gps_tables()
        if not lat_table or not lon_table:
            missing = []
            if not lat_table:
                missing.append("latitude")
            if not lon_table:
                missing.append("longitude")
            self._set_status(f"No table found for: {', '.join(missing)}")
            ax = self._fig.add_subplot(111)
            ax.text(
                0.5, 0.5,
                f"Need tables named latitude & longitude\n(found: {', '.join(t for t in self._tables)})",
                transform=ax.transAxes, ha="center", va="center",
                color="#d4d4d4", fontsize=11,
            )
            apply_plot_theme(self._fig, ax)
            return

        # Fetch value column from a table
        def _fetch_value(tbl: str) -> np.ndarray | None:
            schema = splitter.table_schema(self._conn, tbl)
            col_names_in_tbl = [col["name"] for col in schema]
            val_col = None
            if "value" in col_names_in_tbl:
                val_col = "value"
            else:
                numeric = splitter.numeric_columns(self._conn, tbl)
                non_ts = [c for c in numeric if c != "ts"]
                if non_ts:
                    val_col = non_ts[0]
            if val_col is None:
                return None
            _, rows = splitter.fetch_columns(self._conn, tbl, [val_col])
            if not rows:
                return None
            return np.array([_to_float(r[0]) for r in rows])

        lat = _fetch_value(lat_table)
        lon = _fetch_value(lon_table)
        if lat is None or lon is None:
            self._set_status("Could not read value column from GPS tables")
            return

        # Align to shortest length
        n = min(len(lat), len(lon))
        lat = lat[:n]
        lon = lon[:n]

        # Drop NaN or zero (uninitialised GPS)
        valid = ~(np.isnan(lat) | np.isnan(lon) | ((lat == 0) & (lon == 0)))
        lat = lat[valid]
        lon = lon[valid]

        if len(lat) < 2:
            self._set_status("Not enough valid GPS points")
            return

        # Colour by selected signal (first checked signal wins)
        color_data = None
        color_label = None
        if signals:
            for tbl, cols in signals.items():
                # Skip the lat/lon tables themselves
                if tbl in (lat_table, lon_table):
                    continue
                if cols:
                    raw = _fetch_value(tbl)
                    if raw is not None:
                        raw = raw[:n][valid]
                        if len(raw) == len(lat) and not np.all(np.isnan(raw)):
                            color_data = raw
                            color_label = tbl
                    break

        # Apply sidebar filters to track map data
        if color_data is not None:
            track_data = np.column_stack([lat, lon, color_data])
            track_cols = {"lat": 0, "lon": 1, "color": 2}
        else:
            track_data = np.column_stack([lat, lon])
            track_cols = {"lat": 0, "lon": 1}
        track_data, track_excluded = self._apply_filters(track_data, track_cols, x_key=None)
        if len(track_data) < 2:
            self._set_status("Not enough points after filtering")
            return
        lat = track_data[:, 0]
        lon = track_data[:, 1]
        if color_data is not None:
            color_data = track_data[:, 2]

        ax = self._fig.add_subplot(111)

        if color_data is not None:
            from matplotlib.collections import LineCollection

            points = np.column_stack([lon, lat])
            segments = np.stack([points[:-1], points[1:]], axis=1)
            seg_colors = (color_data[:-1] + color_data[1:]) / 2.0
            vmin, vmax = np.nanmin(seg_colors), np.nanmax(seg_colors)
            norm = plt_Normalize(vmin, vmax) if vmax > vmin else None

            lc = LineCollection(segments, cmap="plasma", norm=norm, linewidth=2)
            lc.set_array(seg_colors)
            ax.add_collection(lc)
            ax.autoscale_view()
            cb = self._fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
            cb.set_label(color_label, color="#d4d4d4", fontsize=9)
            cb.ax.yaxis.set_tick_params(color="#d4d4d4")
            for label in cb.ax.yaxis.get_ticklabels():
                label.set_color("#d4d4d4")
        else:
            ax.plot(lon, lat, color=PLOT_COLORS[0], linewidth=1.5, alpha=0.9)

        # Mark start / finish
        ax.plot(lon[0], lat[0], "o", color="#27ae60", markersize=8, zorder=5, label="Start")
        ax.plot(lon[-1], lat[-1], "s", color="#d63031", markersize=8, zorder=5, label="Finish")

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        title = f"Track Map — colour: {color_label}" if color_label else "Track Map"
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        ax.legend(loc="upper left", fontsize=8)

        apply_plot_theme(self._fig, ax)
        self._style_legend()
        status = f"Track map: {len(lat)} points, {track_excluded} excluded"
        if color_label:
            status += f" (colour: {color_label})"
        self._set_status(status)
