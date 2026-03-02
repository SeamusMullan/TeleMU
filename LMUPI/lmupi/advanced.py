"""Advanced Analysis — multi-signal analysis tools for racing telemetry."""

from __future__ import annotations

import duckdb
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
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
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from lmupi import splitter
from lmupi.analyzer import _to_float
from lmupi.theme import PLOT_COLORS, apply_plot_theme

ANALYSIS_TYPES = [
    "Derived Signal",
    "Lap Comparison",
    "FFT / Spectral",
    "Rolling Statistics",
]


class AdvancedAnalysis(QWidget):
    """Advanced multi-signal analysis widget with four analysis types."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._tables: list[str] = []
        self._tables_with_ts: set[str] = set()

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

        sidebar_layout.addWidget(QLabel("Analysis:"))
        self._analysis_combo = QComboBox()
        self._analysis_combo.addItems(ANALYSIS_TYPES)
        self._analysis_combo.currentIndexChanged.connect(self._on_analysis_changed)
        sidebar_layout.addWidget(self._analysis_combo)

        # ── Controls stacked widget ──
        controls_box = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_box)
        controls_layout.setContentsMargins(4, 4, 4, 4)

        self._controls_stack = QStackedWidget()
        self._build_derived_controls()
        self._build_lap_controls()
        self._build_fft_controls()
        self._build_rolling_controls()
        controls_layout.addWidget(self._controls_stack)
        sidebar_layout.addWidget(controls_box)

        # ── Filters group ──
        filters_box = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_box)
        filters_layout.setContentsMargins(4, 4, 4, 4)

        filters_layout.addWidget(QLabel("From:"))
        self._range_from = QLineEdit()
        self._range_from.setPlaceholderText("start")
        filters_layout.addWidget(self._range_from)

        filters_layout.addWidget(QLabel("To:"))
        self._range_to = QLineEdit()
        self._range_to.setPlaceholderText("end")
        filters_layout.addWidget(self._range_to)

        sidebar_layout.addWidget(filters_box)

        self._analyze_btn = QPushButton("Analyze")
        self._analyze_btn.setObjectName("accent")
        self._analyze_btn.clicked.connect(self._analyze)
        sidebar_layout.addWidget(self._analyze_btn)

        self._status_label = QLabel("")
        self._status_label.setWordWrap(True)
        sidebar_layout.addWidget(self._status_label)

        sidebar.setMinimumWidth(200)

        # ── Right plot area ──
        plot_area = QWidget()
        plot_layout = QVBoxLayout(plot_area)
        plot_layout.setContentsMargins(0, 0, 0, 0)
        plot_layout.addWidget(self._toolbar)
        plot_layout.addWidget(self._canvas, stretch=1)

        splitter_widget.addWidget(sidebar)
        splitter_widget.addWidget(plot_area)
        splitter_widget.setSizes([240, 600])

        layout.addWidget(splitter_widget)

    # ── Control panels ──

    def _build_derived_controls(self) -> None:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(QLabel("Signal A:"))
        self._derived_a = QComboBox()
        lay.addWidget(self._derived_a)

        lay.addWidget(QLabel("Operator:"))
        self._derived_op = QComboBox()
        self._derived_op.addItems(["+", "-", "*", "/", "d/dt"])
        self._derived_op.currentTextChanged.connect(self._on_derived_op_changed)
        lay.addWidget(self._derived_op)

        lay.addWidget(QLabel("Signal B:"))
        self._derived_b = QComboBox()
        lay.addWidget(self._derived_b)

        self._derived_plot_original = QCheckBox("Plot original signals too")
        lay.addWidget(self._derived_plot_original)

        lay.addStretch()
        self._controls_stack.addWidget(panel)

    def _build_lap_controls(self) -> None:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(QLabel("Lap Table:"))
        self._lap_marker = QComboBox()
        lay.addWidget(self._lap_marker)

        self._lap_detect_btn = QPushButton("Detect Laps")
        self._lap_detect_btn.clicked.connect(self._detect_laps)
        lay.addWidget(self._lap_detect_btn)

        self._lap_count_label = QLabel("")
        lay.addWidget(self._lap_count_label)

        lay.addWidget(QLabel("Signal to Compare:"))
        self._lap_signal = QComboBox()
        lay.addWidget(self._lap_signal)

        self._lap_normalize = QCheckBox("Normalize lap time (0-1)")
        lay.addWidget(self._lap_normalize)

        lay.addStretch()
        self._controls_stack.addWidget(panel)

        self._lap_edges: list[float] = []

    def _build_fft_controls(self) -> None:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(QLabel("Window:"))
        self._fft_window = QComboBox()
        self._fft_window.addItems(["None", "Hanning", "Hamming", "Blackman"])
        lay.addWidget(self._fft_window)

        self._fft_log = QCheckBox("Log scale (dB)")
        lay.addWidget(self._fft_log)

        lay.addWidget(QLabel("Max frequency (Hz):"))
        self._fft_max_freq = QLineEdit()
        self._fft_max_freq.setPlaceholderText("auto")
        lay.addWidget(self._fft_max_freq)

        lay.addStretch()
        self._controls_stack.addWidget(panel)

    def _build_rolling_controls(self) -> None:
        panel = QWidget()
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)

        lay.addWidget(QLabel("Window size:"))
        self._rolling_window = QSpinBox()
        self._rolling_window.setRange(3, 10000)
        self._rolling_window.setValue(50)
        lay.addWidget(self._rolling_window)

        lay.addWidget(QLabel("Statistic:"))
        self._rolling_stat = QComboBox()
        self._rolling_stat.addItems([
            "Moving Average",
            "Rolling Std Dev",
            "Upper Envelope",
            "Lower Envelope",
            "Median Filter",
        ])
        lay.addWidget(self._rolling_stat)

        self._rolling_show_original = QCheckBox("Show original signal")
        self._rolling_show_original.setChecked(True)
        lay.addWidget(self._rolling_show_original)

        lay.addStretch()
        self._controls_stack.addWidget(panel)

    # ── Public API ──

    def set_connection(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def set_tables(self, tables: list[str]) -> None:
        self._tables = tables
        self._tables_with_ts = set()

        # Build signal tree
        self._signal_tree.blockSignals(True)
        self._signal_tree.clear()
        if not self._conn:
            self._signal_tree.blockSignals(False)
            return

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

        # Populate derived signal combos and lap combos with table names
        self._derived_a.clear()
        self._derived_b.clear()
        self._lap_marker.clear()
        self._lap_signal.clear()

        for tbl in tables:
            self._derived_a.addItem(tbl)
            self._derived_b.addItem(tbl)
            self._lap_signal.addItem(tbl)
            self._lap_marker.addItem(tbl)

    # ── Helpers ──

    def _on_tree_changed(self) -> None:
        self._update_signals_label()

    def _update_signals_label(self) -> None:
        count = sum(len(cols) for cols in self._get_selected_signals().values())
        self._signals_label.setText(f"Signals ({count})" if count else "Signals")

    def _on_analysis_changed(self, idx: int) -> None:
        self._controls_stack.setCurrentIndex(idx)

    def _on_derived_op_changed(self, op: str) -> None:
        self._derived_b.setEnabled(op != "d/dt")

    def _set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def _get_selected_signals(self) -> dict[str, list[str]]:
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

    def _style_legend(self) -> None:
        for leg in [a.get_legend() for a in self._fig.get_axes() if a.get_legend()]:
            leg.get_frame().set_facecolor("#242424")
            leg.get_frame().set_edgecolor("#3a3a3a")
            for t in leg.get_texts():
                t.set_color("#d4d4d4")

    def _fetch_table_data(self, table: str, col: str = "value") -> tuple[np.ndarray, np.ndarray] | None:
        """Fetch ts and value arrays for a single table. Returns (ts, values) or None."""
        if not self._conn:
            return None
        schema = splitter.table_schema(self._conn, table)
        col_names = [c["name"] for c in schema]
        val_col = None
        if col in col_names:
            val_col = col
        elif "value" in col_names:
            val_col = "value"
        else:
            numeric = splitter.numeric_columns(self._conn, table)
            non_ts = [c for c in numeric if c != "ts"]
            if non_ts:
                val_col = non_ts[0]
        if val_col is None:
            return None

        fetch_cols = ["ts", val_col] if "ts" in col_names else [val_col]
        names, rows = splitter.fetch_columns(self._conn, table, fetch_cols)
        if not rows:
            return None

        if "ts" in col_names:
            ts = np.array([_to_float(r[0]) for r in rows])
            vals = np.array([_to_float(r[1]) for r in rows])
        else:
            ts = np.arange(len(rows), dtype=float)
            vals = np.array([_to_float(r[0]) for r in rows])
        return ts, vals

    def _apply_range_filter(self, ts: np.ndarray, *arrays: np.ndarray) -> tuple[np.ndarray, ...]:
        """Apply from/to range filter on ts. Returns filtered (ts, *arrays)."""
        mask = np.ones(len(ts), dtype=bool)

        txt_from = self._range_from.text().strip()
        txt_to = self._range_to.text().strip()

        try:
            if txt_from:
                mask &= ts >= float(txt_from)
        except ValueError:
            pass
        try:
            if txt_to:
                mask &= ts <= float(txt_to)
        except ValueError:
            pass

        return tuple(a[mask] for a in (ts, *arrays))

    # ── Lap detection ──

    def _detect_laps(self) -> None:
        marker_table = self._lap_marker.currentText()
        if not marker_table or not self._conn:
            self._lap_count_label.setText("No marker selected")
            return

        result = self._fetch_table_data(marker_table)
        if result is None:
            self._lap_count_label.setText("Could not read marker data")
            return

        ts, vals = result

        # Remove NaN timestamps
        valid = ~np.isnan(ts)
        ts = ts[valid]
        vals = vals[valid]

        if len(ts) == 0:
            self._lap_count_label.setText("No valid data in lap table")
            return

        # LMU lap format: each row is a lap completion event.
        # ts = time the lap was completed, value = lap number.
        # Sort by ts to ensure chronological order.
        order = np.argsort(ts)
        ts = ts[order]
        vals = vals[order]

        # Deduplicate: keep only rows where the lap number changes
        # (handles duplicate timestamps or repeated entries)
        keep = [0]
        for i in range(1, len(vals)):
            if vals[i] != vals[keep[-1]]:
                keep.append(i)
        ts = ts[keep]
        vals = vals[keep]

        # Each ts is a lap boundary (end of one lap, start of next).
        # Use them directly as edges.
        self._lap_edges = ts.tolist()
        n_laps = max(0, len(self._lap_edges) - 1)
        self._lap_count_label.setText(f"{n_laps} laps detected ({len(self._lap_edges)} boundaries)")

    # ── Analysis dispatch ──

    def _analyze(self) -> None:
        if not self._conn:
            self._set_status("No database connection")
            return

        analysis = self._analysis_combo.currentText()
        self._fig.clear()

        if analysis == "Derived Signal":
            self._analyze_derived()
        elif analysis == "Lap Comparison":
            self._analyze_lap_comparison()
        elif analysis == "FFT / Spectral":
            self._analyze_fft()
        elif analysis == "Rolling Statistics":
            self._analyze_rolling()

        self._canvas.draw()

    # ── Derived Signal ──

    def _analyze_derived(self) -> None:
        table_a = self._derived_a.currentText()
        table_b = self._derived_b.currentText()
        op = self._derived_op.currentText()

        if not table_a:
            self._set_status("Select Signal A")
            return

        result_a = self._fetch_table_data(table_a)
        if result_a is None:
            self._set_status(f"Could not read data from {table_a}")
            return
        ts_a, val_a = result_a

        ax = self._fig.add_subplot(111)

        if op == "d/dt":
            ts_a, val_a = self._apply_range_filter(ts_a, val_a)
            derivative = np.gradient(val_a) / np.gradient(ts_a)
            derivative = np.where(np.isfinite(derivative), derivative, np.nan)

            if self._derived_plot_original.isChecked():
                ax.plot(ts_a, val_a, color=PLOT_COLORS[0], label=table_a, linewidth=1, alpha=0.5)
                ax2 = ax.twinx()
                ax2.plot(ts_a, derivative, color=PLOT_COLORS[1], label=f"d/dt({table_a})", linewidth=1)
                ax2.set_ylabel(f"d/dt({table_a})", color=PLOT_COLORS[1])
                ax2.tick_params(axis="y", labelcolor=PLOT_COLORS[1])
                lines1, labels1 = ax.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=8)
            else:
                ax.plot(ts_a, derivative, color=PLOT_COLORS[1], label=f"d/dt({table_a})", linewidth=1)
                ax.legend(loc="upper left", fontsize=8)

            ax.set_xlabel("ts")
            ax.set_title(f"Derivative of {table_a}", fontsize=10)
            self._set_status(f"d/dt({table_a}): {len(ts_a)} points")
        else:
            if not table_b:
                self._set_status("Select Signal B")
                return
            result_b = self._fetch_table_data(table_b)
            if result_b is None:
                self._set_status(f"Could not read data from {table_b}")
                return
            ts_b, val_b = result_b

            # Join on ts — align to common timestamps
            n = min(len(ts_a), len(ts_b))
            ts = ts_a[:n]
            a = val_a[:n]
            b = val_b[:n]

            ts, a, b = self._apply_range_filter(ts, a, b)

            if op == "+":
                derived = a + b
            elif op == "-":
                derived = a - b
            elif op == "*":
                derived = a * b
            elif op == "/":
                derived = np.where(b != 0, a / b, np.nan)
            else:
                derived = a

            if self._derived_plot_original.isChecked():
                ax.plot(ts, a, color=PLOT_COLORS[0], label=table_a, linewidth=1, alpha=0.5)
                ax.plot(ts, b, color=PLOT_COLORS[1], label=table_b, linewidth=1, alpha=0.5)
            ax.plot(ts, derived, color=PLOT_COLORS[2], label=f"{table_a} {op} {table_b}", linewidth=1)
            ax.set_xlabel("ts")
            ax.set_title(f"{table_a} {op} {table_b}", fontsize=10)
            ax.legend(loc="upper left", fontsize=8)
            self._set_status(f"{table_a} {op} {table_b}: {len(ts)} points")

        apply_plot_theme(self._fig, ax)
        self._style_legend()

    # ── Lap Comparison ──

    def _analyze_lap_comparison(self) -> None:
        if len(self._lap_edges) < 2:
            self._set_status("Detect laps first (need at least 2 markers)")
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "Click 'Detect Laps' first",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#d4d4d4", fontsize=12)
            apply_plot_theme(self._fig, ax)
            return

        signal_table = self._lap_signal.currentText()
        if not signal_table:
            self._set_status("Select a signal to compare")
            return

        result = self._fetch_table_data(signal_table)
        if result is None:
            self._set_status(f"Could not read data from {signal_table}")
            return
        ts, vals = result
        normalize_time = self._lap_normalize.isChecked()

        ax = self._fig.add_subplot(111)

        for i in range(len(self._lap_edges) - 1):
            t_start = self._lap_edges[i]
            t_end = self._lap_edges[i + 1]
            mask = (ts >= t_start) & (ts < t_end)
            lap_ts = ts[mask]
            lap_vals = vals[mask]

            if len(lap_ts) < 2:
                continue

            lap_duration = lap_ts[-1] - lap_ts[0]
            if normalize_time:
                x = (lap_ts - lap_ts[0]) / lap_duration if lap_duration > 0 else lap_ts - lap_ts[0]
            else:
                x = lap_ts - lap_ts[0]

            color = PLOT_COLORS[i % len(PLOT_COLORS)]
            ax.plot(x, lap_vals, color=color,
                    label=f"Lap {i + 1} ({lap_duration:.1f}s)", linewidth=1)

        ax.set_xlabel("Normalized time (0-1)" if normalize_time else "Time from lap start (s)")
        ax.set_ylabel(signal_table)
        ax.set_title(f"Lap Comparison — {signal_table}", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)

        apply_plot_theme(self._fig, ax)
        self._style_legend()
        self._set_status(f"{len(self._lap_edges) - 1} laps overlaid for {signal_table}")

    # ── FFT / Spectral ──

    def _analyze_fft(self) -> None:
        from scipy.fft import rfft, rfftfreq

        signals = self._get_selected_signals()
        total = sum(len(c) for c in signals.values())
        if total != 1:
            self._set_status("Select exactly 1 signal for FFT")
            ax = self._fig.add_subplot(111)
            ax.text(0.5, 0.5, "Select exactly 1 signal for FFT",
                    transform=ax.transAxes, ha="center", va="center",
                    color="#d4d4d4", fontsize=12)
            apply_plot_theme(self._fig, ax)
            return

        table = list(signals.keys())[0]
        result = self._fetch_table_data(table)
        if result is None:
            self._set_status(f"Could not read data from {table}")
            return
        ts, vals = result

        ts, vals = self._apply_range_filter(ts, vals)

        # Remove NaN
        valid = ~(np.isnan(ts) | np.isnan(vals))
        ts = ts[valid]
        vals = vals[valid]

        if len(vals) < 4:
            self._set_status("Not enough data for FFT")
            return

        # Estimate sample rate
        dt = np.median(np.diff(ts))
        if dt <= 0:
            self._set_status("Cannot estimate sample rate (non-monotonic ts)")
            return
        fs = 1.0 / dt

        # Subtract mean
        vals = vals - np.mean(vals)

        # Apply window
        window_name = self._fft_window.currentText()
        if window_name == "Hanning":
            w = np.hanning(len(vals))
        elif window_name == "Hamming":
            w = np.hamming(len(vals))
        elif window_name == "Blackman":
            w = np.blackman(len(vals))
        else:
            w = np.ones(len(vals))
        vals = vals * w

        # FFT
        yf = rfft(vals)
        xf = rfftfreq(len(vals), d=dt)
        magnitude = np.abs(yf) / len(vals) * 2  # single-sided amplitude

        # Max frequency limit
        max_freq_txt = self._fft_max_freq.text().strip()
        if max_freq_txt:
            try:
                max_freq = float(max_freq_txt)
                freq_mask = xf <= max_freq
                xf = xf[freq_mask]
                magnitude = magnitude[freq_mask]
            except ValueError:
                pass

        # Log scale
        use_log = self._fft_log.isChecked()
        if use_log:
            magnitude = 20 * np.log10(magnitude + 1e-12)
            ylabel = "Magnitude (dB)"
        else:
            ylabel = "Magnitude"

        ax = self._fig.add_subplot(111)
        ax.fill_between(xf, magnitude, alpha=0.4, color=PLOT_COLORS[0])
        ax.plot(xf, magnitude, color=PLOT_COLORS[0], linewidth=1)
        ax.set_xlabel("Frequency (Hz)")
        ax.set_ylabel(ylabel)
        ax.set_title(f"FFT — {table}", fontsize=10)

        apply_plot_theme(self._fig, ax)
        self._set_status(f"FFT of {table}: {len(vals)} samples, fs={fs:.1f} Hz")

    # ── Rolling Statistics ──

    def _analyze_rolling(self) -> None:
        from scipy.ndimage import maximum_filter1d, median_filter, minimum_filter1d, uniform_filter1d

        signals = self._get_selected_signals()
        if not signals:
            self._set_status("Select at least one signal")
            return

        window = self._rolling_window.value()
        stat = self._rolling_stat.currentText()
        show_original = self._rolling_show_original.isChecked()

        ax = self._fig.add_subplot(111)
        color_idx = 0

        x_choice = self._x_combo.currentText()
        use_index = x_choice == "(row index)"

        for table, cols in signals.items():
            for col in cols:
                result = self._fetch_table_data(table, col)
                if result is None:
                    continue
                ts, vals = result
                ts, vals = self._apply_range_filter(ts, vals)

                if len(vals) < window:
                    self._set_status(f"Not enough data for window size {window}")
                    continue

                x = np.arange(len(vals)) if use_index else ts
                label = f"{table}.{col}"

                if show_original:
                    ax.plot(x, vals, color=PLOT_COLORS[color_idx % len(PLOT_COLORS)],
                            alpha=0.3, linewidth=1, label=f"{label} (original)")
                    color_idx += 1

                if stat == "Moving Average":
                    result_vals = uniform_filter1d(vals, size=window)
                elif stat == "Rolling Std Dev":
                    mean = uniform_filter1d(vals, size=window)
                    sq_mean = uniform_filter1d(vals ** 2, size=window)
                    result_vals = np.sqrt(np.maximum(sq_mean - mean ** 2, 0))
                elif stat == "Upper Envelope":
                    result_vals = maximum_filter1d(vals, size=window)
                elif stat == "Lower Envelope":
                    result_vals = minimum_filter1d(vals, size=window)
                elif stat == "Median Filter":
                    result_vals = median_filter(vals, size=window)
                else:
                    result_vals = vals

                ax.plot(x, result_vals, color=PLOT_COLORS[color_idx % len(PLOT_COLORS)],
                        linewidth=1.5, label=f"{label} ({stat}, w={window})")
                color_idx += 1

        ax.set_xlabel("Row Index" if use_index else "ts")
        ax.set_title(f"Rolling Statistics — {stat}", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)

        apply_plot_theme(self._fig, ax)
        self._style_legend()
        total = sum(len(c) for c in signals.values())
        self._set_status(f"{stat} on {total} signal(s), window={window}")
