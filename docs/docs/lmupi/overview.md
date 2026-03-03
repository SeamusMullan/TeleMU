# LMUPI — Le Mans Ultimate Python Interface

LMUPI is a standalone Python desktop application that serves as the primary telemetry analysis tool for Le Mans Ultimate. It reads `.duckdb` telemetry database files, provides interactive exploration of their contents, and exposes a rich set of analysis and visualization tools built on top of DuckDB, NumPy, SciPy, and Matplotlib — all wrapped in a PySide6 Qt GUI.

---

## System Context

```mermaid
C4Context
    title System Context — LMUPI in the LMU Ecosystem

    Person(engineer, "Racing Engineer", "Analyses telemetry to improve car setup and driving")

    System(lmupi, "LMUPI", "Desktop application for interactive telemetry exploration and analysis")

    System_Ext(lmu, "Le Mans Ultimate", "Racing simulator that records session telemetry")
    SystemDb_Ext(db, ".duckdb File", "Telemetry database exported by LMU")
    System_Ext(csv, "CSV / JSON Files", "External data that can be imported into LMUPI")

    Rel(lmu, db, "Exports telemetry to")
    Rel(engineer, lmupi, "Opens files, explores data, plots signals")
    Rel(lmupi, db, "Reads (read-only)")
    Rel(engineer, db, "Provides to LMUPI")
    Rel(engineer, csv, "Provides to LMUPI")
    Rel(lmupi, csv, "Imports via drag-and-drop or menu")
```

---

## Technology Stack

| Library | Version | Role |
|---|---|---|
| **Python** | ≥ 3.13 | Language runtime |
| **PySide6** | ≥ 6.10 | Qt6 GUI framework |
| **DuckDB** | ≥ 1.4 | In-process SQL engine for `.duckdb` files |
| **NumPy** | ≥ 2.4 | Numerical arrays and signal processing primitives |
| **SciPy** | ≥ 1.17 | FFT, cross-correlation, rolling statistics, Spearman r |
| **Matplotlib** | ≥ 3.10 | Embedded plot rendering via Qt backend (`FigureCanvasQTAgg`) |

The project is managed with [uv](https://github.com/astral-sh/uv) and declared in `pyproject.toml`. The entry point script `lmupi` maps to `lmupi.app:run`.

---

## Container Architecture

```mermaid
C4Container
    title Container Diagram — LMUPI Internal Structure

    Person(user, "User", "Racing engineer or analyst")

    System_Boundary(lmupi, "LMUPI Desktop Application") {
        Container(app, "app.py", "PySide6 / Qt6", "MainWindow — application shell, menus, toolbar, drag-and-drop, recent files")
        Container(splitter, "splitter.py", "DuckDB / Python", "Database access layer — the only module that issues SQL queries")
        Container(widgets, "widgets.py", "PySide6 / Qt6", "FilterBar, ExplorerTab (Schema/Stats/Filter/Data), SqlTab")
        Container(analyzer, "analyzer.py", "NumPy / Matplotlib", "SignalAnalyzer — 6 plot types including correlation tools")
        Container(advanced, "advanced.py", "NumPy / SciPy / Matplotlib", "AdvancedAnalysis — Derived Signal, Lap Comparison, FFT, Rolling Stats")
        Container(track, "track_viewer.py", "Matplotlib", "TrackViewer — GPS track map with colour-by-signal overlay")
        Container(dashboard, "dashboard.py", "QPainter / PySide6", "LiveDashboard — real-time gauges, sparklines, lap info, status indicators")
        Container(reader, "telemetry_reader.py", "QThread", "TelemetryReader — polls LMU shared memory at ~60Hz")
        Container(sharedmem, "sharedmem/", "ctypes / mmap", "LMU shared memory mapping — lmu_data.py, lmu_mmap.py, lmu_type.py")
        Container(theme, "theme.py", "PySide6 / Matplotlib", "DARK_STYLESHEET, PLOT_COLORS palette, apply_plot_theme()")
    }

    SystemDb_Ext(db, "DuckDB File", ".duckdb telemetry database (read-only)")
    System_Ext(lmu, "LMU Game", "Shared memory: LMU_Data")

    Rel(user, app, "Interacts with", "Qt events / keyboard shortcuts")
    Rel(app, splitter, "Delegates all DB operations to")
    Rel(app, widgets, "Embeds ExplorerTab + SqlTab")
    Rel(app, analyzer, "Embeds SignalAnalyzer tab")
    Rel(app, advanced, "Embeds AdvancedAnalysis tab")
    Rel(app, track, "Embeds TrackViewer tab")
    Rel(app, dashboard, "Embeds LiveDashboard tab")
    Rel(app, theme, "Applies DARK_STYLESHEET at startup")
    Rel(widgets, splitter, "Queries schema, stats, data through")
    Rel(analyzer, splitter, "Fetches signal data through")
    Rel(advanced, splitter, "Fetches signal data through")
    Rel(track, splitter, "Fetches GPS data through")
    Rel(splitter, db, "Reads (read-only)", "DuckDB SQL")
    Rel(lmu, sharedmem, "Writes telemetry structs")
    Rel(sharedmem, reader, "ctypes structs via MMapControl")
    Rel(reader, dashboard, "push(channel, value)")
```

---

## Project Layout

```
LMUPI/
├── main.py                  # Thin entry point (calls lmupi.app:run)
├── pyproject.toml           # uv project config & dependencies
├── uv.lock                  # Locked dependency tree
├── GUIDE.md                 # End-user keyboard/tab reference
└── lmupi/
    ├── __init__.py          # Empty package marker
    ├── app.py               # MainWindow, run() — application shell
    ├── splitter.py          # Database access layer (all DuckDB calls)
    ├── widgets.py           # Reusable Qt widgets (FilterBar, ExplorerTab, SqlTab)
    ├── analyzer.py          # Signal Analyzer tab (6 plot types)
    ├── advanced.py          # Advanced Analysis tab (4 analysis types)
    ├── track_viewer.py      # Track Viewer tab (GPS map)
    ├── dashboard.py         # Live Dashboard tab (gauges, sparklines, status)
    ├── telemetry_reader.py  # QThread polling LMU shared memory (~60Hz)
    ├── theme.py             # Dark stylesheet, plot color palette, plot theming
    └── sharedmem/           # LMU shared memory layer
        ├── lmu_data.py      # ctypes struct definitions
        ├── lmu_mmap.py      # MMapControl — platform mmap abstraction
        └── lmu_type.py      # Type-annotation stubs for IDE support
```

---

## Module Dependency Graph

```mermaid
graph TD
    main["main.py"]
    app["app.py<br/><b>MainWindow</b>"]
    splitter["splitter.py<br/><b>DB Access Layer</b>"]
    theme["theme.py<br/><b>Dark Theme</b>"]
    widgets["widgets.py<br/><b>ExplorerTab · SqlTab</b>"]
    analyzer["analyzer.py<br/><b>SignalAnalyzer</b>"]
    advanced["advanced.py<br/><b>AdvancedAnalysis</b>"]
    track["track_viewer.py<br/><b>TrackViewer</b>"]
    dashboard["dashboard.py<br/><b>LiveDashboard</b>"]
    reader["telemetry_reader.py<br/><b>TelemetryReader</b>"]
    sharedmem["sharedmem/<br/><b>MMapControl + Structs</b>"]

    main --> app
    app --> splitter
    app --> theme
    app --> widgets
    app --> analyzer
    app --> advanced
    app --> track
    app --> dashboard

    widgets --> splitter
    analyzer --> splitter
    analyzer --> theme
    advanced --> splitter
    advanced --> analyzer
    advanced --> theme
    track --> splitter
    track --> analyzer
    track --> theme

    dashboard --> reader
    reader --> sharedmem

    style splitter fill:#e8751a,color:#fff,stroke:#c05a00
    style theme fill:#2e2e2e,color:#d4d4d4,stroke:#555
    style main fill:#1a1a1a,color:#d4d4d4,stroke:#555
    style dashboard fill:#00bcd4,color:#000,stroke:#008ba3
    style reader fill:#00bcd4,color:#000,stroke:#008ba3
    style sharedmem fill:#00bcd4,color:#000,stroke:#008ba3
```

!!! info ""
    `splitter.py` is the **only** module that directly calls DuckDB. All other modules go through it.

---

## Application Startup Flow

```mermaid
flowchart TD
    A(["lmupi CLI"]) --> B["run()"]
    B --> C["QApplication created"]
    C --> D["DARK_STYLESHEET applied"]
    D --> E["MainWindow()"]

    E --> F["_setup_menu()"]
    E --> G["_setup_toolbar()"]
    E --> H["_setup_ui()"]
    E --> I["_setup_statusbar()"]
    E --> J["_setup_shortcuts()"]

    F --> F1["File / Recent / Export / Import / Quit"]
    G --> G1["Open · Export · Import · Run SQL · Analyze"]
    H --> H1["QSplitter: Tree + Tab Widget<br/>Explorer · SQL · Analyzer · Track · Advanced"]
    I --> I1["Status: 'No database loaded'"]
    J --> J1["Ctrl+F · Ctrl+G"]

    F1 & G1 & H1 & I1 & J1 --> K["window.show()"]
    K --> L(["app.exec() — Qt event loop"])

    style A fill:#e8751a,color:#fff,stroke:none
    style L fill:#27ae60,color:#fff,stroke:none
```

---

## Opening a Database

Databases reach LMUPI through three paths:

```mermaid
flowchart LR
    U(["User"])

    U -->|"Ctrl+O"| D["QFileDialog"]
    U -->|"Drag & drop"| DD["Drop event"]
    U -->|"Recent Files"| R["QSettings<br/>recent files"]

    D --> LoadDB
    R --> LoadDB["_load_db(path)"]
    DD -->|".duckdb"| LoadDB
    DD -->|".csv / .json"| Import["_do_import()"]

    LoadDB --> C1["splitter.connect()<br/>read_only=True"]
    C1 --> C2["list_tables()"]
    C2 --> C3["_populate_tree()"]
    C3 --> C4["set_connection()<br/>set_tables()"]
    C4 --> C5["load_table()<br/>auto-preview"]

    Import --> M1["in-memory<br/>connection"]
    M1 --> M2["import_csv /<br/>import_json()"]
    M2 --> C4

    style LoadDB fill:#e8751a,color:#fff,stroke:none
    style Import fill:#00bcd4,color:#000,stroke:none
```

!!! warning "Read-only access"
    All connections opened from `.duckdb` files use `read_only=True`. The database is **never** modified.

---

## Importing CSV / JSON

Importing creates an **in-memory** DuckDB connection, not a file-backed one. Multiple imports in the same session stack into the same in-memory database:

```mermaid
flowchart TD
    A["_do_import()"] --> B{Existing<br/>in-memory conn?}
    B -- Yes --> C["Reuse connection"]
    B -- No --> D["Create new<br/>in-memory connection"]
    C & D --> E["Derive table name<br/>from path.stem"]
    E --> F{Name already<br/>exists?}
    F -- Yes --> G["Append suffix<br/>name_1, name_2, ..."]
    F -- No --> H["Use original name"]
    G & H --> I["import_csv /<br/>import_json()"]
    I --> J["Update all tabs"]
    J --> K["Show import status"]
```

---

## Key Concept: The `ts` Column

The `ts` (timestamp) column is the central axis in LMUPI. LMU telemetry tables record sample time in seconds in a column named `ts`.

```mermaid
flowchart LR
    subgraph DB["LMU .duckdb Database"]
        T1["speed<br/>(has ts)"]
        T2["throttle<br/>(has ts)"]
        T3["gear<br/>(no ts)"]
    end

    subgraph Rules["Join Strategy"]
        R1["INNER JOIN on ts"]
        R2["Row-aligned<br/>(truncate to shortest)"]
        R3["Track Viewer<br/>name-matched"]
    end

    T1 -- "has ts" --> R1
    T2 -- "has ts" --> R1
    T3 -- "no ts ⚠" --> R2

    style T3 fill:#856404,color:#fff,stroke:none
    style R2 fill:#856404,color:#fff,stroke:none
```

- Tables with `ts` are **INNER JOIN**ed when plotting multiple signals with X = `ts`.
- Tables without `ts` are **row-aligned**: fetched independently and truncated to the shortest table.
- In signal trees, tables without `ts` are rendered in **yellow** as a warning.
- The Track Viewer bypasses this entirely — it discovers GPS tables by name pattern.

---

## UI Tabs

LMUPI has six tabs arranged in a `QTabWidget` on the right side of the main splitter:

```mermaid
graph LR
    MW["MainWindow<br/>QSplitter"]
    TT["Table Tree<br/>220px"]
    TW["Tab Widget"]

    T1["Explorer<br/>ExplorerTab"]
    T2["SQL Query<br/>SqlTab"]
    T3["Signal Analyzer<br/>SignalAnalyzer"]
    T4["Track Viewer<br/>TrackViewer"]
    T5["Advanced Analysis<br/>AdvancedAnalysis"]
    T6["Live Dashboard<br/>LiveDashboard"]

    MW --> TT
    MW --> TW
    TW --> T1
    TW --> T2
    TW --> T3
    TW --> T4
    TW --> T5
    TW --> T6

    style T1 fill:#e8751a,color:#fff,stroke:none
    style T2 fill:#f5a623,color:#000,stroke:none
    style T3 fill:#00bcd4,color:#000,stroke:none
    style T4 fill:#27ae60,color:#fff,stroke:none
    style T5 fill:#e040fb,color:#fff,stroke:none
    style T6 fill:#4fc3f7,color:#000,stroke:none
```

| Tab | Class | Module | Purpose |
|---|---|---|---|
| **Explorer** | `ExplorerTab` | `widgets.py` | Browse raw table data, schema, stats, filters |
| **SQL Query** | `SqlTab` | `widgets.py` | Run arbitrary DuckDB SQL |
| **Signal Analyzer** | `SignalAnalyzer` | `analyzer.py` | Multi-signal comparison with 6 plot types |
| **Track Viewer** | `TrackViewer` | `track_viewer.py` | 2D GPS track map with colour-by-signal |
| **Advanced Analysis** | `AdvancedAnalysis` | `advanced.py` | Derived signals, lap comparison, FFT, rolling statistics |
| **Live Dashboard** | `LiveDashboard` | `dashboard.py` | Real-time gauges, sparklines, lap info, status indicators |

See [UI & Tabs Reference](ui.md) for per-tab documentation.

---

## Export Routing

```mermaid
flowchart TD
    A(["Ctrl+E / Ctrl+Shift+E"]) --> B{Active tab?}
    B -->|"SQL Query tab"| C{Has last_sql?}
    B -->|"Any other tab"| D["Use Explorer's<br/>current table"]
    C -->|Yes| E["Export query results"]
    C -->|No| D
    D --> F{Table selected?}
    F -->|Yes| G["Export full table"]
    F -->|No| H["Warning: no table selected"]

    style E fill:#27ae60,color:#fff,stroke:none
    style G fill:#27ae60,color:#fff,stroke:none
    style H fill:#d63031,color:#fff,stroke:none
```

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open `.duckdb` file |
| `Ctrl+E` | Export CSV |
| `Ctrl+Shift+E` | Export JSON |
| `Ctrl+I` | Import CSV |
| `Ctrl+Shift+I` | Import JSON |
| `Ctrl+F` | Focus Explorer filter bar |
| `Ctrl+G` | Switch to Signal Analyzer tab |
| `Ctrl+Return` | Run SQL query (while in SQL tab) |
| `Ctrl+Q` | Quit |

---

## Agent Notes

- The C4 container diagram above is the canonical reference for LMUPI's internal structure
- `splitter.py` is the **sole DuckDB gateway** — never import `duckdb` in other modules
- `TelemetryReader` pushes data to `LiveDashboard` via `push(channel, value)` — new live-data consumers should follow this pattern
- When adding a new tab, create it as a `QWidget` subclass and wire it in `app.py._setup_ui()`
- The shared memory layer is documented in detail at [Shared Memory Overview](../shared-memory/overview.md)
- See [Architecture Overview](../architecture/overview.md) for how LMUPI fits into the broader TeleMU system
