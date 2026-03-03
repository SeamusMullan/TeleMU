"""Live Dashboard — real-time telemetry gauges and readouts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QPainterPath, QConicalGradient, QBrush
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from lmupi.theme import COLORS, PLOT_COLORS

# Lazy import to avoid hard dependency on sharedmem (Windows-only mmap names)
TelemetryReader = None  # populated on first connect attempt

# Lazy import for streaming client (avoids import at module scope)
StreamingClient = None  # populated on first stream connect attempt

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TelemetryChannel:
    """A single telemetry channel that can be pushed to from any data source."""
    name: str
    unit: str = ""
    min_val: float = 0.0
    max_val: float = 100.0
    warn_low: float | None = None
    warn_high: float | None = None
    history_size: int = 200
    # Internal
    _value: float = 0.0
    _history: list[float] = field(default_factory=list)
    _dirty: bool = True

    @property
    def value(self) -> float:
        return self._value

    def push(self, value: float) -> None:
        """Push a new sample. Called from any data source."""
        self._value = value
        self._history.append(value)
        if len(self._history) > self.history_size:
            self._history = self._history[-self.history_size:]
        self._dirty = True

    @property
    def dirty(self) -> bool:
        return self._dirty

    def mark_clean(self) -> None:
        self._dirty = False

    @property
    def history(self) -> list[float]:
        return self._history

    @property
    def in_warning(self) -> bool:
        if self.warn_low is not None and self._value < self.warn_low:
            return True
        if self.warn_high is not None and self._value > self.warn_high:
            return True
        return False


def _qcolor(hex_str: str) -> QColor:
    return QColor(hex_str)


# ---------------------------------------------------------------------------
# Gauge widget (QPainter radial arc — no matplotlib)
# ---------------------------------------------------------------------------

class GaugeWidget(QWidget):
    """A single radial gauge rendered with QPainter. Fast enough for 60fps."""

    def __init__(self, channel: TelemetryChannel, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._channel = channel
        self._color = _qcolor(color)
        self._color_hex = color

        self.setMinimumSize(140, 140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def update_value(self) -> None:
        if self._channel.dirty:
            self.update()  # schedules a repaint
            self._channel.mark_clean()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        bg = _qcolor(COLORS["bg"])
        p.fillRect(0, 0, w, h, bg)

        ch = self._channel
        frac = 0.0
        rng = ch.max_val - ch.min_val
        if rng > 0:
            frac = max(0.0, min(1.0, (ch.value - ch.min_val) / rng))

        # Gauge geometry: semicircle arc in top portion
        cx, cy = w / 2, h * 0.58
        radius = min(w, h) * 0.38
        arc_width = radius * 0.22

        # Background arc (180 deg, from 180° to 0° i.e. left to right)
        arc_rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        pen = QPen(_qcolor(COLORS["bg_lighter"]), arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
        p.setPen(pen)
        # Qt draws arcs in 1/16th degree units; startAngle=0° is 3 o'clock
        # We want 180° sweep from 9 o'clock (180°) to 3 o'clock (0°)
        p.drawArc(arc_rect, 0 * 16, 180 * 16)

        # Value arc
        if frac > 0.005:
            color = _qcolor(COLORS["red"]) if ch.in_warning else self._color
            pen = QPen(color, arc_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            sweep_deg = frac * 180
            # Start from left (180°), sweep clockwise = negative in Qt
            p.drawArc(arc_rect, int((180 - sweep_deg) * 16), int(sweep_deg * 16))

        # Value text
        p.setPen(Qt.PenStyle.NoPen)
        val_font = QFont("Inter", max(8, int(radius * 0.42)), QFont.Weight.Bold)
        p.setFont(val_font)
        p.setPen(_qcolor(COLORS["text_bright"]))
        val_str = f"{ch.value:.1f}" if ch.max_val >= 10 else f"{ch.value:.2f}"
        p.drawText(QRectF(0, cy - radius * 0.35, w, radius * 0.5), Qt.AlignmentFlag.AlignCenter, val_str)

        # Unit
        unit_font = QFont("Inter", max(6, int(radius * 0.2)))
        p.setFont(unit_font)
        p.setPen(_qcolor(COLORS["text_dim"]))
        p.drawText(QRectF(0, cy + radius * 0.05, w, radius * 0.3), Qt.AlignmentFlag.AlignCenter, ch.unit)

        # Label at top
        label_font = QFont("Inter", max(7, int(radius * 0.22)), QFont.Weight.DemiBold)
        p.setFont(label_font)
        p.setPen(_qcolor(COLORS["text"]))
        p.drawText(QRectF(0, 2, w, radius * 0.4), Qt.AlignmentFlag.AlignCenter, ch.name)

        # Min / Max
        tick_font = QFont("Inter", max(6, int(radius * 0.16)))
        p.setFont(tick_font)
        p.setPen(_qcolor(COLORS["text_dim"]))
        p.drawText(QRectF(cx - radius - arc_width, cy + 2, arc_width * 2, radius * 0.25),
                   Qt.AlignmentFlag.AlignCenter, f"{ch.min_val:.0f}")
        p.drawText(QRectF(cx + radius - arc_width, cy + 2, arc_width * 2, radius * 0.25),
                   Qt.AlignmentFlag.AlignCenter, f"{ch.max_val:.0f}")

        p.end()


# ---------------------------------------------------------------------------
# Sparkline strip widget (QPainter — no matplotlib)
# ---------------------------------------------------------------------------

class SparkStripWidget(QWidget):
    """A horizontal card: label + value + inline QPainter sparkline."""

    def __init__(self, channel: TelemetryChannel, color: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._channel = channel
        self._color = _qcolor(color)
        self._color_hex = color

        self.setStyleSheet(
            f"background-color: {COLORS['bg_light']}; border: 1px solid {COLORS['border']}; border-radius: 4px;"
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 4, 4)
        layout.setSpacing(6)

        # Label + value column
        info = QVBoxLayout()
        info.setSpacing(0)
        self._name_label = QLabel(channel.name)
        self._name_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 11px; font-weight: 600; border: none;")
        info.addWidget(self._name_label)

        self._value_label = QLabel(self._format_value())
        self._value_label.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 16px; font-weight: bold; border: none;")
        info.addWidget(self._value_label)

        self._range_label = QLabel(f"{channel.min_val:.0f} \u2013 {channel.max_val:.0f} {channel.unit}")
        self._range_label.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 9px; border: none;")
        info.addWidget(self._range_label)

        layout.addLayout(info)

        # Sparkline drawn via QPainter
        self._spark_widget = _SparkCanvas(channel, self._color)
        self._spark_widget.setFixedHeight(50)
        layout.addWidget(self._spark_widget, stretch=1)

        self.setFixedHeight(70)

    def _format_value(self) -> str:
        ch = self._channel
        return f"{ch.value:.1f} {ch.unit}"

    def update_value(self) -> None:
        if not self._channel.dirty:
            return
        ch = self._channel
        self._value_label.setText(self._format_value())

        if ch.in_warning:
            self._value_label.setStyleSheet(f"color: {COLORS['red']}; font-size: 16px; font-weight: bold; border: none;")
        else:
            self._value_label.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 16px; font-weight: bold; border: none;")

        self._spark_widget.update()
        ch.mark_clean()


class _SparkCanvas(QWidget):
    """Tiny QPainter-based sparkline."""

    def __init__(self, channel: TelemetryChannel, color: QColor, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._channel = channel
        self._color = color
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        bg = _qcolor(COLORS["bg_light"])
        p.fillRect(0, 0, w, h, bg)

        hist = self._channel.history
        if len(hist) < 2:
            p.end()
            return

        ch = self._channel
        y_min = ch.min_val
        y_max = ch.max_val
        if y_max <= y_min:
            y_min = min(hist)
            y_max = max(hist)
            if y_max <= y_min:
                y_max = y_min + 1

        x_count = max(ch.history_size, len(hist))
        margin = 2

        def to_screen(i: int, val: float) -> QPointF:
            sx = margin + (i / max(x_count - 1, 1)) * (w - 2 * margin)
            sy = h - margin - ((val - y_min) / (y_max - y_min)) * (h - 2 * margin)
            return QPointF(sx, sy)

        # Build path
        path = QPainterPath()
        start = to_screen(0, hist[0])
        path.moveTo(start)
        for i in range(1, len(hist)):
            path.lineTo(to_screen(i, hist[i]))

        # Fill under curve
        fill_color = QColor(self._color)
        fill_color.setAlpha(30)
        fill_path = QPainterPath(path)
        last_pt = to_screen(len(hist) - 1, hist[-1])
        fill_path.lineTo(QPointF(last_pt.x(), h))
        fill_path.lineTo(QPointF(start.x(), h))
        fill_path.closeSubpath()
        p.fillPath(fill_path, fill_color)

        # Draw line
        pen = QPen(self._color, 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawPath(path)

        p.end()


# ---------------------------------------------------------------------------
# Lap info panel
# ---------------------------------------------------------------------------

class LapInfoPanel(QWidget):
    """Displays lap time / sector information in a compact card."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            f"background-color: {COLORS['bg_light']}; border: 1px solid {COLORS['border']}; border-radius: 4px;"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        header = QLabel("Lap Info")
        header.setStyleSheet(f"color: {COLORS['accent']}; font-size: 12px; font-weight: bold; border: none;")
        layout.addWidget(header)

        self._lap_label = QLabel("Lap: --")
        self._lap_label.setStyleSheet(f"color: {COLORS['text_bright']}; font-size: 22px; font-weight: bold; border: none;")
        layout.addWidget(self._lap_label)

        self._time_label = QLabel("Time: --:--.---")
        self._time_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; border: none;")
        layout.addWidget(self._time_label)

        self._best_label = QLabel("Best: --:--.---")
        self._best_label.setStyleSheet(f"color: {COLORS['green']}; font-size: 12px; border: none;")
        layout.addWidget(self._best_label)

        # Sector times
        self._sector_labels: list[QLabel] = []
        for i in range(3):
            lbl = QLabel(f"S{i+1}: --:--.---")
            lbl.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 11px; border: none;")
            layout.addWidget(lbl)
            self._sector_labels.append(lbl)

        layout.addStretch()
        self.setFixedWidth(180)

    def update_lap(self, lap_num: int, lap_time: str, best_time: str,
                   sectors: list[str] | None = None) -> None:
        self._lap_label.setText(f"Lap: {lap_num}")
        self._time_label.setText(f"Time: {lap_time}")
        self._best_label.setText(f"Best: {best_time}")
        if sectors:
            for i, s in enumerate(sectors):
                if i < len(self._sector_labels):
                    self._sector_labels[i].setText(f"S{i+1}: {s}")


# ---------------------------------------------------------------------------
# Status indicator row
# ---------------------------------------------------------------------------

class StatusRow(QWidget):
    """Row of small status indicators (flags, warnings, DRS, pit, etc.)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self._indicators: dict[str, QLabel] = {}
        self._indicator_state: dict[str, tuple[bool, str]] = {}
        for name in ("DRS", "PIT", "FLAG", "TC", "ABS"):
            lbl = QLabel(name)
            lbl.setFixedSize(40, 20)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(self._inactive_style())
            layout.addWidget(lbl)
            self._indicators[name] = lbl
            self._indicator_state[name] = (False, "")

        layout.addStretch()

    @staticmethod
    def _inactive_style() -> str:
        return (
            f"background-color: {COLORS['bg_lighter']}; color: {COLORS['text_dim']}; "
            f"border: 1px solid {COLORS['border']}; border-radius: 3px; font-size: 9px; font-weight: bold;"
        )

    @staticmethod
    def _active_style(color: str) -> str:
        return (
            f"background-color: {color}; color: white; "
            f"border: none; border-radius: 3px; font-size: 9px; font-weight: bold;"
        )

    def set_active(self, name: str, active: bool, color: str = COLORS["accent"]) -> None:
        prev = self._indicator_state.get(name)
        new_state = (active, color if active else "")
        if prev == new_state:
            return  # skip redundant stylesheet updates
        self._indicator_state[name] = new_state
        lbl = self._indicators.get(name)
        if lbl:
            lbl.setStyleSheet(self._active_style(color) if active else self._inactive_style())


# ---------------------------------------------------------------------------
# Main Dashboard widget
# ---------------------------------------------------------------------------

class LiveDashboard(QWidget):
    """Live telemetry dashboard with gauges, sparklines, lap info, and status indicators.

    Design for dynamic data ingestion:
    - Call `register_channel(channel)` to add telemetry channels
    - Call `push(channel_name, value)` to feed new data
    - The dashboard auto-refreshes at `refresh_rate_ms` intervals
    - Connect any data source (UDP listener, file replay, API) to `push()`
    """

    refreshed = Signal()

    def __init__(self, parent: QWidget | None = None, refresh_rate_ms: int = 50) -> None:
        super().__init__(parent)
        self._channels: dict[str, TelemetryChannel] = {}
        self._gauge_widgets: dict[str, GaugeWidget] = {}
        self._spark_widgets: dict[str, SparkStripWidget] = {}
        self._refresh_rate = refresh_rate_ms

        self._build_ui()
        self._setup_placeholder_channels()

        # Refresh timer — only repaints dirty widgets
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(self._refresh_rate)

        # Sparklines refresh at a slower cadence (every 4th tick)
        self._spark_tick = 0
        self._spark_interval = 4  # update sparklines every 4 * 50ms = 200ms

        # Placeholder sim timer
        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self._simulate_data)
        self._sim_t = 0.0

        # Shared memory reader (created on connect)
        self._reader = None

        # Streaming client (created on stream connect)
        self._stream_client = None

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)

        # Top: status row + controls
        top_row = QHBoxLayout()
        self._status_row = StatusRow()
        top_row.addWidget(self._status_row, stretch=1)

        self._connect_btn = QPushButton("Connect LMU")
        self._connect_btn.setObjectName("accent")
        self._connect_btn.setFixedWidth(110)
        self._connect_btn.clicked.connect(self._toggle_connect)
        top_row.addWidget(self._connect_btn)

        self._conn_status = QLabel("Disconnected")
        self._conn_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")
        top_row.addWidget(self._conn_status)

        self._stream_btn = QPushButton("Connect Stream")
        self._stream_btn.setFixedWidth(120)
        self._stream_btn.clicked.connect(self._toggle_stream)
        top_row.addWidget(self._stream_btn)

        self._live_btn = QPushButton("Start Demo")
        self._live_btn.setFixedWidth(100)
        self._live_btn.clicked.connect(self._toggle_sim)
        top_row.addWidget(self._live_btn)

        root.addLayout(top_row)

        # Main area: lap info (left) + gauges + sparklines (right)
        body = QHBoxLayout()
        body.setSpacing(8)

        self._lap_panel = LapInfoPanel()
        body.addWidget(self._lap_panel)

        # Right side: gauges on top, spark strips below
        right = QVBoxLayout()
        right.setSpacing(8)

        # Gauge grid
        gauge_frame = QFrame()
        gauge_frame.setStyleSheet(
            f"background-color: {COLORS['bg']}; border: 1px solid {COLORS['border']}; border-radius: 4px;"
        )
        self._gauge_grid = QGridLayout(gauge_frame)
        self._gauge_grid.setContentsMargins(8, 8, 8, 8)
        self._gauge_grid.setSpacing(8)
        right.addWidget(gauge_frame, stretch=2)

        # Sparkline strips (scrollable)
        spark_scroll = QScrollArea()
        spark_scroll.setWidgetResizable(True)
        spark_scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {COLORS['border']}; border-radius: 4px; background: {COLORS['bg']}; }}"
        )
        self._spark_container = QWidget()
        self._spark_layout = QVBoxLayout(self._spark_container)
        self._spark_layout.setContentsMargins(4, 4, 4, 4)
        self._spark_layout.setSpacing(4)
        self._spark_layout.addStretch()
        spark_scroll.setWidget(self._spark_container)
        right.addWidget(spark_scroll, stretch=1)

        body.addLayout(right, stretch=1)
        root.addLayout(body, stretch=1)

    # -- Visibility-aware timer --

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start(self._refresh_rate)

    def hideEvent(self, event) -> None:
        super().hideEvent(event)
        self._timer.stop()

    # -- Channel management (public API) --

    def register_channel(self, channel: TelemetryChannel, display: str = "gauge") -> None:
        """Register a telemetry channel.

        display: "gauge" puts it in the gauge grid, "spark" puts it in the spark strip area.
        """
        self._channels[channel.name] = channel
        idx = len(self._channels) - 1
        color = PLOT_COLORS[idx % len(PLOT_COLORS)]

        if display == "gauge":
            widget = GaugeWidget(channel, color)
            row = len(self._gauge_widgets) // 3
            col = len(self._gauge_widgets) % 3
            self._gauge_grid.addWidget(widget, row, col)
            self._gauge_widgets[channel.name] = widget
        else:
            widget = SparkStripWidget(channel, color)
            self._spark_layout.insertWidget(self._spark_layout.count() - 1, widget)
            self._spark_widgets[channel.name] = widget

    def push(self, channel_name: str, value: float) -> None:
        """Push a new data point to a channel. Call from any data source."""
        ch = self._channels.get(channel_name)
        if ch:
            ch.push(value)

    def set_refresh_rate(self, ms: int) -> None:
        self._refresh_rate = ms
        self._timer.setInterval(ms)

    # -- Placeholder setup --

    def _setup_placeholder_channels(self) -> None:
        gauges = [
            TelemetryChannel("Speed", "km/h", 0, 340, warn_high=320),
            TelemetryChannel("RPM", "rpm", 0, 9000, warn_high=8500),
            TelemetryChannel("Throttle", "%", 0, 100),
            TelemetryChannel("Brake", "%", 0, 100, warn_high=95),
            TelemetryChannel("Gear", "", 0, 8),
            TelemetryChannel("Steering", "deg", -450, 450),
        ]
        for ch in gauges:
            self.register_channel(ch, display="gauge")

        sparks = [
            TelemetryChannel("Tyre FL", "\u00b0C", 50, 130, warn_high=115),
            TelemetryChannel("Tyre FR", "\u00b0C", 50, 130, warn_high=115),
            TelemetryChannel("Tyre RL", "\u00b0C", 50, 130, warn_high=115),
            TelemetryChannel("Tyre RR", "\u00b0C", 50, 130, warn_high=115),
            TelemetryChannel("Fuel", "L", 0, 110, warn_low=5),
            TelemetryChannel("Brake Temp", "\u00b0C", 100, 900, warn_high=800),
        ]
        for ch in sparks:
            self.register_channel(ch, display="spark")

        self._lap_panel.update_lap(0, "--:--.---", "--:--.---", ["--:--.---"] * 3)

    # -- Refresh --

    def _refresh(self) -> None:
        # Gauges: repaint only dirty ones (QPainter is cheap but skip if unchanged)
        for w in self._gauge_widgets.values():
            w.update_value()

        # Sparklines: update text every tick, but redraw chart at slower cadence
        self._spark_tick += 1
        do_spark_redraw = self._spark_tick >= self._spark_interval
        if do_spark_redraw:
            self._spark_tick = 0

        for w in self._spark_widgets.values():
            if do_spark_redraw:
                w.update_value()
            else:
                # Just update the number, skip sparkline repaint
                ch = w._channel
                if ch.dirty:
                    w._value_label.setText(w._format_value())

        self.refreshed.emit()

    # -- Live telemetry connection --

    def _toggle_connect(self) -> None:
        if self._reader is not None and self._reader.isRunning():
            self._disconnect_lmu()
        else:
            self._connect_lmu()

    def _connect_lmu(self) -> None:
        global TelemetryReader
        if TelemetryReader is None:
            try:
                from lmupi.telemetry_reader import TelemetryReader as _TR
                TelemetryReader = _TR
            except ImportError as exc:
                self._conn_status.setText(f"Import error: {exc}")
                self._conn_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 10px;")
                return

        # Stop demo if running
        if self._sim_timer.isActive():
            self._sim_timer.stop()
            self._live_btn.setText("Start Demo")

        self._reader = TelemetryReader(self, poll_ms=16)
        self._reader.connected.connect(self._on_reader_connected)
        self._reader.disconnected.connect(self._on_reader_disconnected)
        self._reader.error.connect(self._on_reader_error)

        self._conn_status.setText("Connecting...")
        self._conn_status.setStyleSheet(f"color: {COLORS['amber']}; font-size: 10px;")
        self._connect_btn.setText("Disconnect")

        self._reader.start_reading()

    def _disconnect_lmu(self) -> None:
        if self._reader is not None:
            self._reader.stop_reading()
            self._reader = None
        self._connect_btn.setText("Connect LMU")
        self._conn_status.setText("Disconnected")
        self._conn_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")

    def _on_reader_connected(self) -> None:
        self._conn_status.setText("Connected — receiving telemetry")
        self._conn_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 10px;")

    def _on_reader_disconnected(self) -> None:
        self._connect_btn.setText("Connect LMU")
        self._conn_status.setText("Disconnected")
        self._conn_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")

    def _on_reader_error(self, msg: str) -> None:
        self._conn_status.setText(msg)
        self._conn_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 10px;")
        self._connect_btn.setText("Connect LMU")

    # -- Streaming client connection --

    def _toggle_stream(self) -> None:
        if self._stream_client is not None and self._stream_client.isRunning():
            self._disconnect_stream()
        else:
            self._show_stream_dialog()

    def _show_stream_dialog(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Connect to Telemetry Stream")
        form = QFormLayout(dialog)

        host_edit = QLineEdit("127.0.0.1")
        host_edit.setPlaceholderText("Server IP address")
        form.addRow("Host:", host_edit)

        port_spin = QSpinBox()
        port_spin.setRange(1, 65535)
        port_spin.setValue(9100)
        form.addRow("Port:", port_spin)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._connect_stream(host_edit.text().strip(), port_spin.value())

    def _connect_stream(self, host: str, port: int) -> None:
        global StreamingClient
        if StreamingClient is None:
            try:
                from lmupi.streaming_client import StreamingClient as _SC
                StreamingClient = _SC
            except ImportError as exc:
                self._conn_status.setText(f"Import error: {exc}")
                self._conn_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 10px;")
                return

        # Stop demo and LMU reader if running
        if self._sim_timer.isActive():
            self._sim_timer.stop()
            self._live_btn.setText("Start Demo")
        if self._reader is not None and self._reader.isRunning():
            self._disconnect_lmu()

        self._stream_client = StreamingClient(self, host=host, port=port)
        self._stream_client.connected.connect(self._on_stream_connected)
        self._stream_client.disconnected.connect(self._on_stream_disconnected)
        self._stream_client.error.connect(self._on_stream_error)
        self._stream_client.status_changed.connect(self._on_stream_status)
        self._stream_client.channel_map_received.connect(self._on_stream_channels)

        self._conn_status.setText(f"Connecting to {host}:{port}…")
        self._conn_status.setStyleSheet(f"color: {COLORS['amber']}; font-size: 10px;")
        self._stream_btn.setText("Disconnect")

        self._stream_client.start_streaming()

    def _disconnect_stream(self) -> None:
        if self._stream_client is not None:
            self._stream_client.stop_streaming()
            self._stream_client = None
        self._stream_btn.setText("Connect Stream")
        self._conn_status.setText("Disconnected")
        self._conn_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")

    def _on_stream_connected(self) -> None:
        self._conn_status.setText("Stream connected — receiving telemetry")
        self._conn_status.setStyleSheet(f"color: {COLORS['green']}; font-size: 10px;")

    def _on_stream_disconnected(self) -> None:
        self._stream_btn.setText("Connect Stream")
        self._conn_status.setText("Disconnected")
        self._conn_status.setStyleSheet(f"color: {COLORS['text_dim']}; font-size: 10px;")

    def _on_stream_error(self, msg: str) -> None:
        self._conn_status.setText(msg)
        self._conn_status.setStyleSheet(f"color: {COLORS['red']}; font-size: 10px;")

    def _on_stream_status(self, msg: str) -> None:
        self._conn_status.setText(msg)
        self._conn_status.setStyleSheet(f"color: {COLORS['amber']}; font-size: 10px;")

    def _on_stream_channels(self, specs: list) -> None:
        """Register channels from the server's channel map."""
        from lmupi.streaming_client import ChannelSpec
        from lmupi.dashboard import TelemetryChannel
        for spec in specs:
            if spec.name not in self._channels:
                ch = TelemetryChannel(
                    name=spec.name,
                    unit=spec.unit,
                    min_val=spec.min_val,
                    max_val=spec.max_val,
                    warn_low=spec.warn_low,
                    warn_high=spec.warn_high,
                )
                self.register_channel(ch, display=spec.display)

    # -- Simulated data (placeholder) --

    def _toggle_sim(self) -> None:
        if self._sim_timer.isActive():
            self._sim_timer.stop()
            self._live_btn.setText("Start Demo")
        else:
            self._sim_timer.start(self._refresh_rate)
            self._live_btn.setText("Stop Demo")

    def _simulate_data(self) -> None:
        """Generate fake telemetry for demo / testing purposes."""
        t = self._sim_t
        self._sim_t += 0.05

        speed = 180 + 100 * np.sin(t * 0.3) + np.random.normal(0, 3)
        rpm = 3000 + 3000 * abs(np.sin(t * 0.3)) + np.random.normal(0, 100)
        throttle = max(0, min(100, 60 + 40 * np.sin(t * 0.3) + np.random.normal(0, 5)))
        brake = max(0, min(100, 30 * max(0, -np.sin(t * 0.3)) + np.random.normal(0, 2)))
        gear = max(1, min(8, int(4 + 3 * np.sin(t * 0.3))))
        steering = 120 * np.sin(t * 0.7) + np.random.normal(0, 5)

        self.push("Speed", speed)
        self.push("RPM", rpm)
        self.push("Throttle", throttle)
        self.push("Brake", brake)
        self.push("Gear", gear)
        self.push("Steering", steering)

        base_temp = 85 + 15 * abs(np.sin(t * 0.1))
        for i, name in enumerate(["Tyre FL", "Tyre FR", "Tyre RL", "Tyre RR"]):
            temp = base_temp + np.random.normal(0, 2) + (i * 1.5)
            self.push(name, temp)

        fuel = max(0, 90 - t * 0.3)
        self.push("Fuel", fuel)

        brake_temp = 350 + 200 * brake / 100 + np.random.normal(0, 10)
        self.push("Brake Temp", brake_temp)

        self._status_row.set_active("DRS", speed > 250, COLORS["green"])
        self._status_row.set_active("TC", throttle > 90 and speed < 150, COLORS["amber"])
        self._status_row.set_active("ABS", brake > 80, COLORS["amber"])
        self._status_row.set_active("PIT", False)
        self._status_row.set_active("FLAG", False)

        lap_num = int(t / 12) + 1
        lap_progress = t % 12
        if lap_progress < 0.1:
            mins = int(lap_progress) // 60
            secs = lap_progress % 60
            self._lap_panel.update_lap(
                lap_num,
                f"{mins}:{secs:05.3f}",
                "1:42.318",
                ["0:28.441", "0:35.102", "0:38.775"],
            )
