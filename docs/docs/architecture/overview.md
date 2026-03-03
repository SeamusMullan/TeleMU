# Architecture Overview

TeleMU is a single Python desktop application that combines post-session analysis with live telemetry access, session recording, LAN streaming, and race engineering tools.

## C4 System Context

```mermaid
C4Context
    title TeleMU — System Context

    Person(driver, "Driver", "Drives in LMU on the driver PC")
    Person(engineer, "Race Engineer", "Monitors telemetry on a separate PC")

    System(telemu, "TeleMU", "Python desktop app — analysis, live dashboard, recording, streaming")
    System_Ext(lmu, "Le Mans Ultimate", "Racing simulator, exposes shared memory")

    Rel(lmu, telemu, "Shared memory (LMU_Data)")
    Rel(driver, lmu, "Drives")
    Rel(driver, telemu, "Opens .duckdb files, views live dashboard")
    Rel(telemu, engineer, "Streams telemetry over LAN")

    UpdateLayoutConfig($c4ShapeInRow="3", $c4BoundaryInRow="1")
```

## C4 Container Diagram

```mermaid
C4Container
    title TeleMU — Containers

    Person(driver, "Driver")
    Person(engineer, "Race Engineer")
    System_Ext(lmu, "LMU Game", "Shared memory: LMU_Data")

    System_Boundary(app, "TeleMU Application") {
        Container(mainwindow, "MainWindow", "PySide6", "app.py — shell, tab host, menus")
        Container(splitter, "Splitter", "DuckDB", "splitter.py — sole SQL gateway")
        Container(explorer, "ExplorerTab", "PySide6", "widgets.py — browse data, schema, stats")
        Container(sql, "SqlTab", "PySide6", "widgets.py — arbitrary SQL queries")
        Container(analyzer, "SignalAnalyzer", "Matplotlib", "analyzer.py — 6 plot types")
        Container(track, "TrackViewer", "Matplotlib", "track_viewer.py — GPS map")
        Container(advanced, "AdvancedAnalysis", "SciPy", "advanced.py — FFT, lap compare, etc.")
        Container(dashboard, "LiveDashboard", "QPainter", "dashboard.py — gauges, sparklines")
        Container(reader, "TelemetryReader", "QThread", "telemetry_reader.py — polls shared memory")
        Container(sharedmem, "SharedMem Layer", "ctypes/mmap", "sharedmem/ — LMU struct mapping")

        Container(recorder, "TelemetryRecorder", "QThread", "recorder.py — writes .tmu files")
        Container(streamer, "TelemetryStreamer", "UDP/TCP", "streamer.py — LAN broadcast")
        Container(strategy, "Strategy Engine", "Python", "strategy/ — fuel, tyres, gaps, stints")
    }

    Rel(lmu, sharedmem, "mmap read")
    Rel(sharedmem, reader, "ctypes structs")
    Rel(reader, dashboard, "push(channel, value)")
    Rel(reader, recorder, "frame data")
    Rel(reader, streamer, "frame data")
    Rel(streamer, engineer, "UDP/TCP over LAN")

    Rel(driver, mainwindow, "Opens .duckdb, views tabs")
    Rel(mainwindow, splitter, "SQL queries")
    Rel(splitter, explorer, "query results")
    Rel(splitter, sql, "query results")
    Rel(splitter, analyzer, "column data")
    Rel(splitter, track, "GPS data")
    Rel(splitter, advanced, "column data")

    Rel(strategy, dashboard, "strategy overlays")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="1")
```

!!! info "Status Legend"
    - **Solid borders** = implemented and working
    - Recorder, Streamer, and Strategy Engine are **planned** subsystems (see dashed references in diagrams elsewhere)

## Design Principles

1. **Single app** — everything runs in one PySide6 process; no separate frontend/backend
2. **Splitter is the SQL gateway** — all DuckDB queries go through `splitter.py`, no other module opens connections
3. **Push-based live data** — `TelemetryReader` pushes values to consumers (dashboard, recorder, streamer) via Qt signals
4. **QThread for background work** — any I/O or polling runs on a QThread, never on the GUI thread
5. **Read-only analysis** — `.duckdb` files are opened read-only; analysis never mutates source data
6. **Modular tabs** — each tab is a self-contained QWidget; MainWindow only wires connections

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| UI Framework | PySide6 / Qt6 | Dark theme via `theme.py` |
| Data Engine | DuckDB | Read-only, accessed only via `splitter.py` |
| Analysis | NumPy, SciPy | FFT, rolling stats, cross-correlation |
| Plotting | Matplotlib | Embedded in Qt via `FigureCanvasQTAgg` |
| Live Gauges | QPainter | Custom `GaugeWidget`, `SparkStripWidget` |
| Shared Memory | ctypes + mmap | Maps LMU's `SharedMemoryInterface.hpp` |
| Package Manager | uv | `pyproject.toml` in `LMUPI/` |

## Agent Notes

- The C4 container diagram is the canonical reference for how modules connect
- When adding a new subsystem (recorder, streamer, strategy), create it as a module under `LMUPI/lmupi/` and wire it into `app.py`
- Follow the push-based pattern: `TelemetryReader` emits signals, new consumers connect to those signals
- All DuckDB access must go through `splitter.py` — never import `duckdb` directly in other modules
- Related issues: see project issue tracker for recording (#), streaming (#), and strategy (#) features
