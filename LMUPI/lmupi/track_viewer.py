"""Track Viewer — standalone GPS track map plotting widget."""

from __future__ import annotations

import duckdb
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize as plt_Normalize
from matplotlib.figure import Figure
from PySide6.QtCore import Qt, QTimer
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
from lmupi.analyzer import _to_float
from lmupi.theme import PLOT_COLORS, apply_plot_theme

_LAT_TABLE_NAMES = {"latitude", "lat", "gps_lat", "gps latitude", "gpslat", "gps_latitude"}
_LON_TABLE_NAMES = {"longitude", "lon", "lng", "gps_lon", "gps longitude", "gpslon", "gpslng", "gps_longitude"}
_SPEED_TABLE_NAMES = {"speed", "gps speed", "gps_speed", "gpsspeed", "velocity"}

_COLORSCALES = ["plasma", "viridis", "turbo", "hot", "cividis"]


class _PillBar(QWidget):
    """Horizontal row of signal pills with click-to-activate."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 2, 4, 2)
        self._layout.setSpacing(4)
        self._pills: list[QPushButton] = []
        self._active: str | None = None
        self._on_click: callable | None = None
        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #888888; font-size: 10px;")
        self._layout.addStretch()
        self._layout.addWidget(self._stats_label)

    def set_callback(self, cb: callable) -> None:
        self._on_click = cb

    def set_signals(self, names: list[str], active: str | None) -> None:
        # Remove old pills
        for pill in self._pills:
            self._layout.removeWidget(pill)
            pill.deleteLater()
        self._pills.clear()

        self._active = active
        for idx, name in enumerate(names):
            color = PLOT_COLORS[idx % len(PLOT_COLORS)]
            pill = QPushButton(name)
            pill.setFixedHeight(22)
            pill.setCursor(Qt.CursorShape.PointingHandCursor)
            is_active = name == active
            if is_active:
                pill.setStyleSheet(
                    f"QPushButton {{ background-color: {color}; color: white; "
                    f"border: none; border-radius: 10px; padding: 2px 10px; font-size: 11px; font-weight: 600; "
                    f"box-shadow: 0 0 0 2px {color}; }}"
                )
            else:
                pill.setStyleSheet(
                    "QPushButton { background-color: #2e2e2e; color: #888888; "
                    "border: 1px solid #3a3a3a; border-radius: 10px; padding: 2px 10px; font-size: 11px; }"
                    "QPushButton:hover { color: #d4d4d4; border-color: #4a4a4a; }"
                )
            pill.clicked.connect(lambda checked=False, n=name: self._on_click and self._on_click(n))
            # Insert before the stretch
            self._layout.insertWidget(len(self._pills), pill)
            self._pills.append(pill)

    def set_stats(self, min_v: float, max_v: float, mean_v: float) -> None:
        self._stats_label.setText(f"min: {min_v:.2f} | max: {max_v:.2f} | mean: {mean_v:.2f}")

    def clear_stats(self) -> None:
        self._stats_label.setText("")


class TrackViewer(QWidget):
    """Standalone GPS track map viewer with multi-signal overlay support."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._tables: list[str] = []
        self._auto_plotted = False

        # Cached data
        self._signal_cache: dict[str, np.ndarray] = {}
        self._gps_lat: np.ndarray | None = None
        self._gps_lon: np.ndarray | None = None
        self._gps_valid_indices: np.ndarray | None = None
        self._gps_n: int = 0
        self._gps_excluded: int = 0
        self._active_signal: str | None = None

        # Hover sync
        self._hover_idx: int | None = None

        # Figures: main track + sparklines
        self._fig = Figure(tight_layout=True)
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._toolbar = NavigationToolbar2QT(self._canvas, self)

        self._spark_fig = Figure(tight_layout=True)
        self._spark_canvas = FigureCanvasQTAgg(self._spark_fig)

        # Connect hover events
        self._canvas.mpl_connect("motion_notify_event", self._on_track_hover)
        self._canvas.mpl_connect("axes_leave_event", self._on_track_leave)
        self._spark_canvas.mpl_connect("motion_notify_event", self._on_spark_hover)
        self._spark_canvas.mpl_connect("axes_leave_event", self._on_spark_leave)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter_widget = QSplitter(Qt.Orientation.Horizontal)

        # -- Left sidebar --
        sidebar = QWidget()
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        self._signals_label = QLabel("Overlay Signals")
        sidebar_layout.addWidget(self._signals_label)

        self._signal_tree = QTreeWidget()
        self._signal_tree.setHeaderHidden(True)
        self._signal_tree.itemChanged.connect(self._on_tree_changed)
        sidebar_layout.addWidget(self._signal_tree, stretch=1)

        # Colorscale dropdown
        cs_layout = QHBoxLayout()
        cs_layout.addWidget(QLabel("Colorscale"))
        self._colorscale_combo = QComboBox()
        for cs in _COLORSCALES:
            self._colorscale_combo.addItem(cs.capitalize(), cs)
        self._colorscale_combo.currentIndexChanged.connect(self._on_colorscale_changed)
        cs_layout.addWidget(self._colorscale_combo)
        sidebar_layout.addLayout(cs_layout)

        # Filters group
        filters_box = QGroupBox("Filters")
        filters_layout = QVBoxLayout(filters_box)
        filters_layout.setContentsMargins(4, 4, 4, 4)

        self._exclude_zeros_cb = QCheckBox("Exclude zeros")
        filters_layout.addWidget(self._exclude_zeros_cb)

        self._exclude_nan_cb = QCheckBox("Exclude NaN")
        filters_layout.addWidget(self._exclude_nan_cb)

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

        sidebar.setMinimumWidth(200)

        # -- Right: pill bar + track + sparklines --
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Pill bar
        self._pill_bar = _PillBar()
        self._pill_bar.set_callback(self._on_pill_click)
        right_layout.addWidget(self._pill_bar)

        # Vertical splitter: track (top) + sparklines (bottom)
        self._plot_splitter = QSplitter(Qt.Orientation.Vertical)

        track_area = QWidget()
        track_layout = QVBoxLayout(track_area)
        track_layout.setContentsMargins(0, 0, 0, 0)
        track_layout.addWidget(self._toolbar)
        track_layout.addWidget(self._canvas, stretch=1)

        spark_area = QWidget()
        spark_layout = QVBoxLayout(spark_area)
        spark_layout.setContentsMargins(0, 0, 0, 0)
        spark_layout.addWidget(self._spark_canvas, stretch=1)

        self._plot_splitter.addWidget(track_area)
        self._plot_splitter.addWidget(spark_area)
        self._plot_splitter.setSizes([700, 300])

        right_layout.addWidget(self._plot_splitter, stretch=1)

        splitter_widget.addWidget(sidebar)
        splitter_widget.addWidget(right_widget)
        splitter_widget.setSizes([240, 600])

        layout.addWidget(splitter_widget)

    # -- Public API --

    def set_connection(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def set_tables(self, tables: list[str]) -> None:
        self._tables = tables
        self._signal_cache.clear()
        self._signal_tree.blockSignals(True)
        self._signal_tree.clear()
        if not self._conn:
            self._signal_tree.blockSignals(False)
            return
        all_cols = splitter.all_numeric_columns(self._conn, tables)
        for table, cols in all_cols.items():
            parent = QTreeWidgetItem(self._signal_tree, [table])
            parent.setData(0, Qt.ItemDataRole.UserRole, table)
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            parent.setCheckState(0, Qt.CheckState.Unchecked)
            for col in cols:
                child = QTreeWidgetItem(parent, [col])
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(0, Qt.CheckState.Unchecked)
        self._signal_tree.expandAll()
        self._signal_tree.blockSignals(False)
        self._update_signals_label()

        # Auto-plot
        if not self._auto_plotted:
            self._auto_plotted = True
            self._auto_detect_and_plot()

    # -- Helpers --

    def _auto_detect_and_plot(self) -> None:
        lat_table, lon_table, speed_table = self._find_gps_tables()
        if not lat_table or not lon_table:
            return

        # Pre-select speed signal if available
        if speed_table:
            self._pre_check_signal(speed_table)

        # Delay to let UI settle
        QTimer.singleShot(100, self._plot)

    def _pre_check_signal(self, table_name: str) -> None:
        """Check the first column of a table in the signal tree."""
        root = self._signal_tree.invisibleRootItem()
        self._signal_tree.blockSignals(True)
        for i in range(root.childCount()):
            table_item = root.child(i)
            item_name = table_item.data(0, Qt.ItemDataRole.UserRole) or table_item.text(0)
            if item_name == table_name and table_item.childCount() > 0:
                table_item.child(0).setCheckState(0, Qt.CheckState.Checked)
                break
        self._signal_tree.blockSignals(False)
        self._update_signals_label()

    def _on_tree_changed(self) -> None:
        self._update_signals_label()

    def _on_colorscale_changed(self) -> None:
        # Instant update if we have cached GPS data
        if self._gps_lat is not None:
            self._rebuild_track()
            self._canvas.draw()

    def _on_pill_click(self, signal_name: str) -> None:
        self._active_signal = signal_name
        if self._gps_lat is not None:
            self._rebuild_track()
            self._rebuild_sparklines()
            self._update_pill_bar()
            self._canvas.draw()
            self._spark_canvas.draw()

    def _update_signals_label(self) -> None:
        count = sum(len(cols) for cols in self._get_selected_signals().values())
        self._signals_label.setText(f"Overlay Signals ({count})" if count else "Overlay Signals")

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

    def _selected_signal_names(self) -> list[str]:
        """Return flat list of selected table names (signal identifiers)."""
        lat_table, lon_table, _ = self._find_gps_tables()
        names = []
        for tbl, cols in self._get_selected_signals().items():
            if tbl in (lat_table, lon_table):
                continue
            if cols:
                names.append(tbl)
        return names

    def _style_legend(self) -> None:
        for leg in [a.get_legend() for a in self._fig.get_axes() if a.get_legend()]:
            leg.get_frame().set_facecolor("#242424")
            leg.get_frame().set_edgecolor("#3a3a3a")
            for t in leg.get_texts():
                t.set_color("#d4d4d4")

    def _find_gps_tables(self) -> tuple[str | None, str | None, str | None]:
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

    def _apply_filters(self, data: np.ndarray, col_idx: dict[str, int]) -> tuple[np.ndarray, int]:
        n_before = len(data)
        mask = np.ones(n_before, dtype=bool)

        def _parse_float(widget: QLineEdit) -> float | None:
            txt = widget.text().strip()
            if not txt:
                return None
            try:
                return float(txt)
            except ValueError:
                return None

        y_indices = list(col_idx.values())

        if y_indices:
            y_data = data[:, y_indices]

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

            if self._exclude_nan_cb.isChecked():
                mask &= ~np.any(np.isnan(y_data), axis=1)

            if self._exclude_zeros_cb.isChecked():
                mask &= ~np.any(y_data == 0, axis=1)

        filtered = data[mask]
        return filtered, n_before - len(filtered)

    def _fetch_value(self, tbl: str) -> np.ndarray | None:
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

    # -- Hover synchronization --

    def _on_track_hover(self, event) -> None:
        if event.inaxes is None or self._gps_lon is None:
            return
        # Find nearest point on track
        x, y = event.xdata, event.ydata
        if x is None or y is None:
            return
        dists = (self._gps_lon - x) ** 2 + (self._gps_lat - y) ** 2
        idx = int(np.argmin(dists))
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._rebuild_sparklines()
            self._spark_canvas.draw()

    def _on_track_leave(self, event) -> None:
        if self._hover_idx is not None:
            self._hover_idx = None
            self._rebuild_sparklines()
            self._spark_canvas.draw()

    def _on_spark_hover(self, event) -> None:
        if event.inaxes is None or self._gps_lon is None:
            return
        x = event.xdata
        if x is None:
            return
        idx = max(0, min(int(round(x)), len(self._gps_lon) - 1))
        if idx != self._hover_idx:
            self._hover_idx = idx
            self._rebuild_track()
            self._canvas.draw()

    def _on_spark_leave(self, event) -> None:
        if self._hover_idx is not None:
            self._hover_idx = None
            self._rebuild_track()
            self._canvas.draw()

    # -- Update pill bar --

    def _update_pill_bar(self) -> None:
        names = self._selected_signal_names()
        self._pill_bar.set_signals(names, self._active_signal)

        # Stats for active signal
        if self._active_signal and self._active_signal in self._signal_cache:
            data = self._signal_cache[self._active_signal]
            valid = data[~np.isnan(data)]
            if len(valid) > 0:
                self._pill_bar.set_stats(float(np.min(valid)), float(np.max(valid)), float(np.mean(valid)))
            else:
                self._pill_bar.clear_stats()
        else:
            self._pill_bar.clear_stats()

    # -- Rebuild track from cache (no re-fetch) --

    def _rebuild_track(self) -> None:
        if self._gps_lat is None:
            return

        self._fig.clear()
        ax = self._fig.add_subplot(111)
        lat = self._gps_lat
        lon = self._gps_lon
        colorscale = self._colorscale_combo.currentData() or "plasma"

        # Base track line
        ax.plot(lon, lat, color=PLOT_COLORS[0], linewidth=1.5, alpha=0.9)

        # Color overlay from active signal
        color_data = None
        color_label = None
        if self._active_signal and self._active_signal in self._signal_cache:
            color_data = self._signal_cache[self._active_signal]
            color_label = self._active_signal

        if color_data is not None and len(color_data) >= 2:
            c_n = min(len(color_data), len(lat))
            c_lat = lat[:c_n]
            c_lon = lon[:c_n]
            c_vals = color_data[:c_n]

            points = np.column_stack([c_lon, c_lat])
            segments = np.stack([points[:-1], points[1:]], axis=1)
            seg_colors = (c_vals[:-1] + c_vals[1:]) / 2.0
            vmin, vmax = np.nanmin(seg_colors), np.nanmax(seg_colors)
            norm = plt_Normalize(vmin, vmax) if vmax > vmin else None

            lc = LineCollection(segments, cmap=colorscale, norm=norm, linewidth=2.5)
            lc.set_array(seg_colors)
            ax.add_collection(lc)
            cb = self._fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
            cb.set_label(color_label, color="#d4d4d4", fontsize=9)
            cb.ax.yaxis.set_tick_params(color="#d4d4d4")
            for label in cb.ax.yaxis.get_ticklabels():
                label.set_color("#d4d4d4")

        # Start/Finish
        ax.plot(lon[0], lat[0], "o", color="#27ae60", markersize=8, zorder=5, label="Start")
        ax.plot(lon[-1], lat[-1], "s", color="#d63031", markersize=8, zorder=5, label="Finish")

        # Hover marker on track
        if self._hover_idx is not None and 0 <= self._hover_idx < len(lon):
            ax.plot(
                lon[self._hover_idx], lat[self._hover_idx],
                "x", color="white", markersize=10, markeredgewidth=2, zorder=10,
            )

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        title = f"Track Map \u2014 colour: {color_label}" if color_label else "Track Map"
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        ax.legend(loc="upper left", fontsize=8)

        apply_plot_theme(self._fig, ax)
        self._style_legend()

    # -- Rebuild sparklines from cache --

    def _rebuild_sparklines(self) -> None:
        self._spark_fig.clear()
        names = self._selected_signal_names()
        if not names or self._gps_lat is None:
            self._spark_canvas.draw()
            return

        n_signals = len(names)
        for idx, signal in enumerate(names):
            if signal not in self._signal_cache:
                continue

            data = self._signal_cache[signal]
            color = PLOT_COLORS[idx % len(PLOT_COLORS)]
            valid = data[~np.isnan(data)]
            min_v = float(np.min(valid)) if len(valid) > 0 else 0
            max_v = float(np.max(valid)) if len(valid) > 0 else 0

            ax = self._spark_fig.add_subplot(n_signals, 1, idx + 1)
            x = np.arange(len(data))
            ax.plot(x, data, color=color, linewidth=1)
            ax.set_title(f"{signal}  [{min_v:.1f} \u2013 {max_v:.1f}]", fontsize=9, pad=2)
            ax.tick_params(labelsize=8)
            ax.set_xlim(0, len(data) - 1)

            if idx < n_signals - 1:
                ax.set_xticklabels([])

            # Hover vertical line
            if self._hover_idx is not None and 0 <= self._hover_idx < len(data):
                ax.axvline(self._hover_idx, color="white", linewidth=1, linestyle=":", alpha=0.7)

            apply_plot_theme(self._spark_fig, ax)

        self._spark_fig.tight_layout()

    # -- Plot --

    def _plot(self) -> None:
        if not self._conn:
            self._set_status("No database connection")
            return

        lat_table, lon_table, _ = self._find_gps_tables()
        if not lat_table or not lon_table:
            self._fig.clear()
            ax = self._fig.add_subplot(111)
            missing = []
            if not lat_table:
                missing.append("latitude")
            if not lon_table:
                missing.append("longitude")
            self._set_status(f"No table found for: {', '.join(missing)}")
            ax.text(
                0.5, 0.5,
                f"Need tables named latitude & longitude\n(found: {', '.join(t for t in self._tables)})",
                transform=ax.transAxes, ha="center", va="center",
                color="#d4d4d4", fontsize=11,
            )
            apply_plot_theme(self._fig, ax)
            self._canvas.draw()
            return

        lat = self._fetch_value(lat_table)
        lon = self._fetch_value(lon_table)
        if lat is None or lon is None:
            self._set_status("Could not read value column from GPS tables")
            return

        n = min(len(lat), len(lon))
        lat = lat[:n]
        lon = lon[:n]

        valid = ~(np.isnan(lat) | np.isnan(lon) | ((lat == 0) & (lon == 0)))
        valid_indices = np.where(valid)[0]
        lat = lat[valid]
        lon = lon[valid]

        if len(lat) < 2:
            self._set_status("Not enough valid GPS points")
            return

        # Apply filters
        track_data = np.column_stack([lat, lon])
        track_cols = {"lat": 0, "lon": 1}
        track_data, track_excluded = self._apply_filters(track_data, track_cols)
        if len(track_data) < 2:
            self._set_status("Not enough points after filtering")
            return
        lat = track_data[:, 0]
        lon = track_data[:, 1]

        # Cache GPS base
        self._gps_lat = lat
        self._gps_lon = lon
        self._gps_valid_indices = valid_indices
        self._gps_n = n
        self._gps_excluded = track_excluded

        # Fetch and cache all selected signals
        signal_names = self._selected_signal_names()
        for tbl in signal_names:
            if tbl not in self._signal_cache:
                raw = self._fetch_value(tbl)
                if raw is not None:
                    raw = raw[:n][valid]
                    # Trim to match filtered track length
                    raw = raw[:len(lat)]
                    if len(raw) > 0 and not np.all(np.isnan(raw)):
                        self._signal_cache[tbl] = raw

        # Set active signal if not set
        if self._active_signal not in signal_names:
            self._active_signal = signal_names[0] if signal_names else None

        # Build and draw
        self._rebuild_track()
        self._rebuild_sparklines()
        self._update_pill_bar()
        self._canvas.draw()
        self._spark_canvas.draw()

        # Status
        status = f"Track map: {len(lat)} points, {track_excluded} excluded"
        if self._active_signal and self._active_signal in self._signal_cache:
            cd = self._signal_cache[self._active_signal]
            color_n = int(np.sum(~np.isnan(cd)))
            if color_n < len(lat):
                status += f" (colour: {self._active_signal}, {color_n}/{len(lat)} points)"
            else:
                status += f" (colour: {self._active_signal})"
        self._set_status(status)
