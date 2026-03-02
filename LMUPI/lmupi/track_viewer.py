"""Track Viewer — standalone GPS track map plotting widget."""

from __future__ import annotations

import duckdb
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize as plt_Normalize
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
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


class TrackViewer(QWidget):
    """Standalone GPS track map viewer with colour-by-signal support."""

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

        self._signals_label = QLabel("Colour-by Signal")
        sidebar_layout.addWidget(self._signals_label)

        self._signal_tree = QTreeWidget()
        self._signal_tree.setHeaderHidden(True)
        self._signal_tree.itemChanged.connect(self._on_tree_changed)
        sidebar_layout.addWidget(self._signal_tree, stretch=1)

        # ── Filters group ──
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

    # ── Helpers ──

    def _on_tree_changed(self) -> None:
        self._update_signals_label()

    def _update_signals_label(self) -> None:
        count = sum(len(cols) for cols in self._get_selected_signals().values())
        self._signals_label.setText(f"Colour-by Signal ({count})" if count else "Colour-by Signal")

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

    def _find_gps_tables(self) -> tuple[str | None, str | None, str | None]:
        """Search tables by name for lat, lon, and optionally speed."""
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
        """Apply sidebar filters to data. Returns (filtered_data, excluded_count)."""
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

    # ── Plot ──

    def _plot(self) -> None:
        if not self._conn:
            self._set_status("No database connection")
            return

        self._fig.clear()
        self._plot_track_map(self._get_selected_signals())
        self._canvas.draw()

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

        n = min(len(lat), len(lon))
        lat = lat[:n]
        lon = lon[:n]

        valid = ~(np.isnan(lat) | np.isnan(lon) | ((lat == 0) & (lon == 0)))
        lat = lat[valid]
        lon = lon[valid]

        if len(lat) < 2:
            self._set_status("Not enough valid GPS points")
            return

        # Colour by selected signal (first checked signal wins)
        color_data = None
        color_label = None
        color_n = 0  # how many GPS points the colour signal covers
        if signals:
            for tbl, cols in signals.items():
                if tbl in (lat_table, lon_table):
                    continue
                if cols:
                    raw = _fetch_value(tbl)
                    if raw is not None:
                        # Align to GPS length before valid-mask, then apply mask
                        raw = raw[:n][valid]
                        if len(raw) > 0 and not np.all(np.isnan(raw)):
                            color_n = len(raw)
                            color_data = raw
                            color_label = tbl
                    break

        # Apply filters to the full track
        track_data = np.column_stack([lat, lon])
        track_cols = {"lat": 0, "lon": 1}
        track_data, track_excluded = self._apply_filters(track_data, track_cols)
        if len(track_data) < 2:
            self._set_status("Not enough points after filtering")
            return
        lat = track_data[:, 0]
        lon = track_data[:, 1]

        # Trim colour data to match filtered track length
        if color_data is not None:
            color_data = color_data[:len(lat)]
            color_n = len(color_data)

        ax = self._fig.add_subplot(111)

        # Always draw the full track in default colour
        ax.plot(lon, lat, color=PLOT_COLORS[0], linewidth=1.5, alpha=0.9)

        # Overlay coloured section on top if we have colour data
        if color_data is not None and color_n >= 2:
            c_lat = lat[:color_n]
            c_lon = lon[:color_n]
            c_vals = color_data[:color_n]

            points = np.column_stack([c_lon, c_lat])
            segments = np.stack([points[:-1], points[1:]], axis=1)
            seg_colors = (c_vals[:-1] + c_vals[1:]) / 2.0
            vmin, vmax = np.nanmin(seg_colors), np.nanmax(seg_colors)
            norm = plt_Normalize(vmin, vmax) if vmax > vmin else None

            lc = LineCollection(segments, cmap="plasma", norm=norm, linewidth=2.5)
            lc.set_array(seg_colors)
            ax.add_collection(lc)
            cb = self._fig.colorbar(lc, ax=ax, fraction=0.046, pad=0.04)
            cb.set_label(color_label, color="#d4d4d4", fontsize=9)
            cb.ax.yaxis.set_tick_params(color="#d4d4d4")
            for label in cb.ax.yaxis.get_ticklabels():
                label.set_color("#d4d4d4")

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
        if color_label and color_data is not None:
            if color_n < len(lat):
                status += f" (colour: {color_label}, {color_n}/{len(lat)} points)"
            else:
                status += f" (colour: {color_label})"
        self._set_status(status)
