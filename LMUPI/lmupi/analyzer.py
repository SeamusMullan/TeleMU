"""Signal Analyzer — multi-table, multi-variable comparison plotting widget."""

from __future__ import annotations

import datetime

import numpy as np
import duckdb
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
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
    "Correlation Matrix",
    "Cross-Correlation",
    "Correlation Finder",
]


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
        if not self._conn:
            self._signal_tree.blockSignals(False)
            return
        all_cols = splitter.all_numeric_columns(self._conn, tables)
        for table, cols in all_cols.items():
            parent = QTreeWidgetItem(self._signal_tree, [table])
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.CheckState.Unchecked)
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
            table_name = table_item.text(0)
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
            # Include x_col for single-table fetches
            if x_col and x_col not in cols:
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
            # Multi-table join on ts
            return splitter.fetch_joined_columns(self._conn, fetch_signals, on="ts")

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

        # Correlation Finder uses all tables, no manual selection needed
        if plot_type == "Correlation Finder":
            self._fig.clear()
            self._plot_correlation_finder()
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

        # X data
        if use_index:
            x_data = np.arange(len(data))
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
                self._set_status(f"X column '{x_col}' not found in results")
                return
            x_data = data[:, col_idx[x_key]]
            x_label = x_col

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
                self._set_status(f"Plotted cross-correlation ({len(rows)} points)")
        elif plot_type == "Correlation Matrix":
            self._plot_correlation(y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(rows)} points)")
        elif plot_type == "Histogram":
            self._plot_histogram(y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(rows)} points)")
        elif plot_type == "Scatter":
            self._plot_scatter(x_data, x_label, y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(rows)} points)")
        else:
            self._plot_line(x_data, x_label, y_arrays)
            self._set_status(f"Plotted {len(y_arrays)} signals ({len(rows)} points)")

        self._canvas.draw()

    # ── Plot methods ──

    def _plot_line(self, x: np.ndarray, x_label: str, y_arrays: dict[str, np.ndarray]) -> None:
        cols = list(y_arrays.keys())

        # Dual y-axis: when exactly 2 vars with ranges differing >10x
        use_twin = False
        if len(cols) == 2:
            r0 = np.nanptp(y_arrays[cols[0]])
            r1 = np.nanptp(y_arrays[cols[1]])
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

        try:
            col_names, rows = splitter.fetch_joined_columns(self._conn, table_columns, on="ts")
        except Exception:
            self._set_status("JOIN failed — tables may not share a 'ts' column")
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "JOIN failed — tables may not share a 'ts' column",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#d4d4d4", fontsize=12)
            apply_plot_theme(self._fig, ax)
            return

        if not rows or len(col_names) < 3:
            self._set_status("No data returned from join")
            return

        data = np.array([[_to_float(v) for v in row] for row in rows])

        # Filter to only non-ts columns
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
