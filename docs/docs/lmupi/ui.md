# LMUPI — UI & Tabs Reference

Detailed guide to every tab and UI component in LMUPI.

---

## Application State Machine

```mermaid
stateDiagram-v2
    [*] --> Empty : app launched

    Empty : No Database Loaded
    Empty : Status bar shows help text
    Empty : All tabs visible but inactive

    FileDB : File Database Open
    FileDB : read_only=True DuckDB connection
    FileDB : Table tree populated
    FileDB : All tabs active

    InMemory : In-Memory Database
    InMemory : in-memory DuckDB connection
    InMemory : One or more imported tables
    InMemory : All tabs active

    Empty --> FileDB : Open .duckdb
    Empty --> InMemory : Import CSV or JSON
    FileDB --> FileDB : Open another .duckdb
    FileDB --> InMemory : Import CSV or JSON
    InMemory --> InMemory : Import another file
    InMemory --> FileDB : Open .duckdb
```

---

## Main Window Layout

```
┌───────────────────────────────────────────────────────────────────┐
│  Menu Bar — File                                                  │
├───────────────────────────────────────────────────────────────────┤
│  Toolbar — Open │ Export CSV │ Export JSON │ Import CSV │         │
│            Import JSON │ Run SQL │ Analyze                        │
├──────────────────┬────────────────────────────────────────────────┤
│  Table Tree      │  Tab Widget                                    │
│  (220 px)        │  Explorer │ SQL Query │ Signal Analyzer │      │
│                  │  Track Viewer │ Advanced Analysis              │
│  Filename.duckdb │                                                │
│  ├ speed (12 300)│  [Active tab content]                          │
│  ├ throttle      │                                                │
│  ├ brake         │                                                │
│  └ latitude      │                                                │
├──────────────────┴────────────────────────────────────────────────┤
│  Status Bar — filename.duckdb — 42 tables                         │
└───────────────────────────────────────────────────────────────────┘
```

The main splitter defaults to 220px for the table tree and the remainder for the tab widget. Both panes can be resized by dragging the splitter handle (highlighted in accent orange on hover).

### Table Tree interaction

```mermaid
sequenceDiagram
    participant U as User
    participant Tree as QTreeWidget
    participant MW as MainWindow
    participant ET as ExplorerTab

    U->>Tree: Click table item
    Tree->>MW: itemClicked(item, column)
    MW->>MW: table = item.data(UserRole)
    MW->>ET: load_table(conn, table)
    MW->>ET: select_table(table)
    MW->>MW: tabs.setCurrentWidget(explorer)
    Note over ET: Schema, stats, filter bar,<br/>and data all reload
```

---

## Tab 1 — Explorer

**Class:** `ExplorerTab` (`widgets.py`)

```
┌─────────────────────────────────────┐  ┌────────────┐
│  Table ▾  speed                     │  │  Rows ▾ 100│
└─────────────────────────────────────┘  └────────────┘
┌──────────────────────────────────────────────────────┐
│  Schema  │  Statistics                               │
│──────────┼────────────────────────────────────────── │
│  Column  │  Type    │  Nullable                      │
│  ts      │  DOUBLE  │  NO                            │
│  value   │  FLOAT   │  YES                           │
└──────────────────────────────────────────────────────┘
┌────────────────────────────────────────────┐  ┌──────┐
│  [ ts...filter ] [ value...filter ] [ ... ]│  │Clear │
└────────────────────────────────────────────┘  └──────┘
┌──────────────────────────────────────────────────────┐
│  ts      │  value                                    │
│  0.000   │  87.4                                     │
│  0.016   │  88.1                                     │
│  0.032   │  88.7                                     │
│  ...     │  ...                                      │
└──────────────────────────────────────────────────────┘
```

### Filter pipeline

```mermaid
flowchart LR
    KS(["Keystroke"]) --> DT["FilterBar<br/>debounce timer"]
    DT -->|"reset on<br/>keystroke"| DT
    DT -->|"300ms idle"| EC["filters_changed<br/>emitted"]
    EC --> RL["ExplorerTab<br/>_reload_data()"]
    RL --> FLT["filtered_preview()<br/>ILIKE on each column"]
    FLT --> TBL["_populate_data()<br/>fill QTableWidget"]

    style KS fill:#2e2e2e,color:#d4d4d4,stroke:#555
    style TBL fill:#27ae60,color:#fff,stroke:none
```

### Controls

| Control | Behavior |
|---|---|
| **Table dropdown** | Switches the active table; triggers a full reload |
| **Rows dropdown** | Limits preview to 100 / 500 / 1,000 rows, or All |
| **Schema sub-tab** | Shows column name, DuckDB type, and nullability |
| **Statistics sub-tab** | Shows min, max, avg (numeric only), and null count per column |
| **Filter bar** | One `QLineEdit` per column — text is matched as `%input%` using `ILIKE` |
| **Clear button** | Resets all filters and re-fetches unfiltered data |

!!! tip "Shortcut"
    `Ctrl+F` switches to Explorer and focuses the first filter input from anywhere in the application.

---

## Tab 2 — SQL Query

**Class:** `SqlTab` (`widgets.py`)

```
┌──────────────────────────────────────────────────────┐
│  SELECT ts, value FROM speed                         │
│  WHERE ts BETWEEN 50 AND 100                         │
│  (monospace editor, max 160 px tall)                 │
└──────────────────────────────────────────────────────┘
[ Run (Ctrl+Return) ]   10 rows in 0.003s
┌──────────────────────────────────────────────────────┐
│  ts      │  value                                    │
│  50.000  │  142.3                                    │
│  50.016  │  143.1                                    │
│  ...     │  ...                                      │
└──────────────────────────────────────────────────────┘
```

### Query execution flow

```mermaid
sequenceDiagram
    participant U as User
    participant ST as SqlTab
    participant SP as splitter.py
    participant DB as DuckDB

    U->>ST: Ctrl+Return
    ST->>ST: sql = editor.toPlainText().strip()
    ST->>ST: last_sql = sql
    ST->>ST: t0 = perf_counter()
    ST->>SP: execute_sql(conn, sql)
    SP->>DB: conn.execute(sql)

    alt Success
        DB-->>SP: result (columns + rows)
        SP-->>ST: col_names, rows
        ST->>ST: populate QTableWidget
        ST->>ST: status = "N rows in T.###s"
    else duckdb.Error
        DB-->>SP: raises duckdb.Error
        SP-->>ST: re-raises
        ST->>ST: clear results table
        ST->>ST: status = error message (red)
    end
```

### Export integration

```mermaid
flowchart LR
    EXP(["Ctrl+E"]) --> AC{SQL tab<br/>active?}
    AC -- Yes --> LS{last_sql<br/>not empty?}
    LS -- Yes --> QR["Export query results"]
    LS -- No --> TBL
    AC -- No --> TBL["Export selected table"]

    style QR fill:#e8751a,color:#fff,stroke:none
    style TBL fill:#00bcd4,color:#000,stroke:none
```

### Example queries

```sql
-- Time-windowed slice
SELECT ts, value FROM throttle WHERE ts BETWEEN 50 AND 100

-- Peak values per signal
SELECT MAX(value) AS peak_speed FROM speed

-- Join two signals manually
SELECT s.ts, s.value AS speed, t.value AS throttle
FROM speed s INNER JOIN throttle t ON s.ts = t.ts

-- Lap segment average
SELECT AVG(value) FROM speed WHERE ts > 120 AND ts < 185
```

---

## Tab 3 — Signal Analyzer

**Class:** `SignalAnalyzer` (`analyzer.py`)

### Signal selection tree

```mermaid
graph TD
    Root["Signal tree root"]
    T1["speed (has ts)"]
    T2["throttle (has ts)"]
    T3["gear — no ts (yellow)"]

    C1["value"]
    C2["value"]
    C3["value"]

    Root --> T1 --> C1
    Root --> T2 --> C2
    Root --> T3 --> C3

    style T3 fill:#856404,color:#fff,stroke:none
    style C3 fill:#856404,color:#fff,stroke:none
```

Tables without `ts` are shown in yellow — they can still be plotted, but only via row-alignment, not time-joining.

### X axis mode decision

```mermaid
flowchart LR
    X{X axis<br/>dropdown} -->|ts| JN["Attempt INNER JOIN<br/>on ts across tables"]
    X -->|row index| RA["Row-aligned fetch<br/>np.arange(N) as X"]

    JN --> HAS{All selected tables<br/>have ts?}
    HAS -- Yes --> JOINED["Single joined dataset"]
    HAS -- No --> SKIP["Skip non-ts tables<br/>report in status"]
    SKIP --> JOINED

    style JOINED fill:#e8751a,color:#fff,stroke:none
    style RA fill:#00bcd4,color:#000,stroke:none
```

### Filter composition

```mermaid
flowchart TD
    A["bool mask — ones(N)"] --> RF

    RF["① X-range filter<br/>From <= X <= To"]
    RF --> VC["② Value clamp<br/>Min / Max on Y cols"]
    VC --> EN["③ Exclude NaN rows"]
    EN --> EZ["④ Exclude zero rows"]
    EZ --> Apply["data = data[mask]<br/>excluded = N - N'"]

    style RF fill:#2e2e2e,color:#d4d4d4,stroke:#555
    style Apply fill:#27ae60,color:#fff,stroke:none
```

### Plot type guide

```mermaid
graph LR
    subgraph TS["Time Series"]
        LINE["Line<br/>1+ signals"]
        SCAT["Scatter<br/>1+ signals"]
    end
    subgraph DIST["Distribution"]
        HIST["Histogram<br/>1+ signals"]
    end
    subgraph CORR["Correlation"]
        CMAT["Correlation Matrix<br/>2+ signals"]
        XCOR["Cross-Correlation<br/>exactly 2 signals"]
        CFND["Correlation Finder<br/>auto-discovers"]
    end

    style LINE fill:#e8751a,color:#fff,stroke:none
    style SCAT fill:#f5a623,color:#000,stroke:none
    style HIST fill:#00bcd4,color:#000,stroke:none
    style CMAT fill:#27ae60,color:#fff,stroke:none
    style XCOR fill:#e040fb,color:#fff,stroke:none
    style CFND fill:#d63031,color:#fff,stroke:none
```

| Plot type | Signals needed | Use when |
|---|---|---|
| **Line** | 1+ | Time-series comparison; dual Y-axis for 2 signals with very different ranges |
| **Scatter** | 1+ | Revealing point clouds and non-temporal relationships |
| **Histogram** | 1+ | Comparing value distributions across signals |
| **Correlation Matrix** | 2+ | Finding pairwise linear relationships at a glance |
| **Cross-Correlation** | Exactly 2 | Measuring time delays between two signals |
| **Correlation Finder** | None | Automatic discovery of top correlations across all tables |

### Dual Y-axis logic (Line plot)

```mermaid
flowchart LR
    Two["Exactly 2 signals"] --> Ratio["ratio = max_range / min_range"]
    Ratio --> Check{ratio > 10?}
    Check -- Yes --> Twin["ax.twinx()<br/>A=left · B=right"]
    Check -- No --> Single["Single Y-axis<br/>both overlaid"]

    style Twin fill:#e8751a,color:#fff,stroke:none
```

---

## Tab 4 — Track Viewer

**Class:** `TrackViewer` (`track_viewer.py`)

### GPS name matching

```mermaid
flowchart LR
    TABLES(["Loaded tables"]) --> LOOP["Check each table<br/>(lowercased name)"]
    LOOP --> LAT{In lat set?}
    LOOP --> LON{In lon set?}
    LOOP --> SPD{In speed set?}

    LAT -- Yes --> LATV["lat_table = tbl"]
    LON -- Yes --> LONV["lon_table = tbl"]
    SPD -- Yes --> SPDV["speed_table = tbl"]

    subgraph LatSet["Latitude names"]
        L1["latitude, lat, gps_lat,<br/>gps_latitude, gpslat"]
    end
    subgraph LonSet["Longitude names"]
        L2["longitude, lon, lng,<br/>gps_lon, gps_longitude"]
    end
```

### Colour-by overlay rendering

```mermaid
sequenceDiagram
    participant TV as TrackViewer
    participant SP as splitter.py
    participant MPL as Matplotlib

    TV->>SP: fetch lat values
    TV->>SP: fetch lon values
    TV->>TV: truncate to min(len_lat, len_lon)
    TV->>TV: remove NaN and (0,0) points
    TV->>TV: apply sidebar filters

    alt Colour signal checked
        TV->>SP: fetch colour signal values
        TV->>TV: align to GPS length
        TV->>MPL: LineCollection, cmap=plasma
        TV->>MPL: add colorbar
    end

    TV->>MPL: plot base track (orange)
    TV->>MPL: Start marker (green circle)
    TV->>MPL: Finish marker (red square)
    TV->>MPL: set_aspect("equal")
    TV->>MPL: apply_plot_theme()
```

### Track rendering data flow

```mermaid
flowchart LR
    LAT["lat array"] --> ALIGN["Truncate to<br/>min(len_lat, len_lon)"]
    LON["lon array"] --> ALIGN
    ALIGN --> VALID["Remove NaN<br/>and (0,0) dropouts"]
    VALID --> FILT["Apply sidebar filters"]

    COLSIG["Colour signal"] --> COLALN["Align to GPS length"]
    COLALN --> SEGS["Build GPS segments"]
    FILT --> SEGS
    SEGS --> LC["LineCollection<br/>cmap=plasma"]

    FILT --> BASE["Base track (orange)"]
    LC --> OVERLAY["Colour overlay"]
    BASE & OVERLAY --> MARKERS["Start / Finish markers"]

    style LC fill:#e040fb,color:#fff,stroke:none
    style MARKERS fill:#27ae60,color:#fff,stroke:none
```

!!! tip
    Use **Exclude zeros** to remove GPS dropout points that appear as (0, 0) coordinates.

---

## Tab 5 — Advanced Analysis

**Class:** `AdvancedAnalysis` (`advanced.py`)

### Control panel switching

```mermaid
flowchart LR
    DD["Analysis dropdown"] --> SW["QStackedWidget<br/>setCurrentIndex()"]
    SW -->|0| DS["Derived Signal<br/>A · op · B"]
    SW -->|1| LC["Lap Comparison<br/>Lap Table · Signal"]
    SW -->|2| FF["FFT / Spectral<br/>Window · Log scale"]
    SW -->|3| RS["Rolling Statistics<br/>Window · Statistic"]

    style DS fill:#e8751a,color:#fff,stroke:none
    style LC fill:#f5a623,color:#000,stroke:none
    style FF fill:#00bcd4,color:#000,stroke:none
    style RS fill:#e040fb,color:#fff,stroke:none
```

### Derived Signal — operator reference

```mermaid
flowchart LR
    A["Signal A"] --> OP{Operator}
    B["Signal B"] --> OP

    OP -->|"+"| ADD["A + B"]
    OP -->|"-"| SUB["A - B"]
    OP -->|"*"| MUL["A * B"]
    OP -->|"/"| DIV["A/B (NaN if B=0)"]
    OP -->|"d/dt"| DER["np.gradient(A)<br/>Signal B disabled"]

    ADD & SUB & MUL & DIV & DER --> PLT["Plot derived signal"]
    DER --> TWIN["ax.twinx()<br/>if plot original"]

    style DER fill:#e040fb,color:#fff,stroke:none
    style TWIN fill:#e8751a,color:#fff,stroke:none
```

### Lap Comparison — workflow

```mermaid
sequenceDiagram
    participant U as User
    participant AA as AdvancedAnalysis
    participant SP as splitter.py

    U->>AA: Select Lap Table
    U->>AA: Click "Detect Laps"
    AA->>SP: _fetch_table_data(marker_table)
    SP-->>AA: (ts, vals)
    AA->>AA: Remove NaN timestamps
    AA->>AA: Sort by ts
    AA->>AA: Deduplicate on value changes
    AA->>AA: _lap_edges = boundary ts list
    AA->>AA: Label: "N laps detected"

    U->>AA: Select signal to compare
    U->>AA: Click "Analyze"

    loop For each lap i
        AA->>AA: mask ts to lap range
        alt Normalize
            AA->>AA: x = (ts - t0) / duration
        else Absolute
            AA->>AA: x = ts - t0
        end
        AA->>AA: ax.plot(x, vals, color=PLOT_COLORS[i])
    end
    AA->>AA: canvas.draw()
```

### FFT — window function comparison

```mermaid
graph LR
    R["None / Rectangular<br/>~13 dB"]
    H["Hanning<br/>~32 dB"]
    HA["Hamming<br/>~43 dB"]
    B["Blackman<br/>~74 dB"]

    R -->|"more attenuation"| H --> HA --> B

    style R fill:#d63031,color:#fff,stroke:none
    style H fill:#f5a623,color:#000,stroke:none
    style HA fill:#e8751a,color:#fff,stroke:none
    style B fill:#27ae60,color:#fff,stroke:none
```

| Window | Sidelobe attenuation | Amplitude accuracy | Best for |
|---|---|---|---|
| **None** | ~13 dB | Highest | Sharp edges, known periodic signals |
| **Hanning** | ~32 dB | Good | General purpose (recommended default) |
| **Hamming** | ~43 dB | Good | Slightly better sidelobe than Hanning |
| **Blackman** | ~74 dB | Lower | Maximum leakage suppression |

### Rolling Statistics — visual effect guide

```mermaid
flowchart LR
    SIG["Raw signal"] --> MA["Moving Average<br/>uniform_filter1d"]
    SIG --> SD["Rolling Std Dev<br/>via uniform_filter1d"]
    SIG --> UE["Upper Envelope<br/>maximum_filter1d"]
    SIG --> LE["Lower Envelope<br/>minimum_filter1d"]
    SIG --> MF["Median Filter<br/>edge-preserving"]

    style MA fill:#e8751a,color:#fff,stroke:none
    style SD fill:#f5a623,color:#000,stroke:none
    style UE fill:#27ae60,color:#fff,stroke:none
    style LE fill:#d63031,color:#fff,stroke:none
    style MF fill:#00bcd4,color:#000,stroke:none
```

!!! warning "Window size is in samples, not seconds"
    At 60 Hz data, a window of 60 covers 1 second. At 100 Hz, you need a window of 100 for 1 second of smoothing.

---

## Keyboard Shortcuts Reference

```mermaid
mindmap
  root((LMUPI Shortcuts))
    File
      Ctrl+O Open .duckdb
      Ctrl+I Import CSV
      Ctrl+Shift+I Import JSON
      Ctrl+E Export CSV
      Ctrl+Shift+E Export JSON
      Ctrl+Q Quit
    Navigation
      Ctrl+F Focus filter bar
      Ctrl+G Signal Analyzer tab
    SQL
      Ctrl+Return Run query
```
