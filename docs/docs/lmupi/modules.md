# LMUPI — Modules Reference

Detailed documentation for every Python module in the `lmupi` package.

---

## Class Overview

```mermaid
classDiagram
    class MainWindow {
        +DuckDBPyConnection _conn
        +bool _is_in_memory
        +_load_db(path)
        +_do_import(fmt, path)
        +_export(fmt)
    }

    class ExplorerTab {
        +str current_table
        +FilterBar filter_bar
        +load_table(conn, table)
        +set_tables(tables)
    }

    class FilterBar {
        +Signal filters_changed
        +set_columns(columns)
        +get_filters() dict
        +focus_first()
    }

    class SqlTab {
        +str last_sql
        +set_connection(conn)
        +run_query()
    }

    class SignalAnalyzer {
        +set_tables(tables)
        +_fetch_data(signals, x_col)
        +_apply_filters(data, col_idx, x_key)
    }

    class AdvancedAnalysis {
        +set_tables(tables)
        +_detect_laps()
        +_analyze_fft()
    }

    class TrackViewer {
        +set_tables(tables)
        +_find_gps_tables()
        +_plot_track_map(signals)
    }

    MainWindow *-- ExplorerTab
    MainWindow *-- SqlTab
    MainWindow *-- SignalAnalyzer
    MainWindow *-- AdvancedAnalysis
    MainWindow *-- TrackViewer
    ExplorerTab *-- FilterBar
```

---

## `app.py` — Application Shell

**Class: `MainWindow(QMainWindow)`**

The top-level application window. Owns the DuckDB connection and coordinates all tabs.

### Key attributes

| Attribute | Type | Description |
|---|---|---|
| `_conn` | `duckdb.DuckDBPyConnection \| None` | The active database connection |
| `_db_path` | `Path \| None` | Path to the currently open `.duckdb` file, or `None` for in-memory |
| `_is_in_memory` | `bool` | `True` when the connection is an in-memory import session |
| `_settings` | `QSettings` | Persists recent file list across sessions (`HKCU/LMUPI/TelemetryExplorer`) |
| `_tree` | `QTreeWidget` | Left-panel table browser |
| `_tabs` | `QTabWidget` | Right-panel tab container |

### Initialization sequence

```mermaid
sequenceDiagram
    participant CLI as lmupi (CLI)
    participant run as run()
    participant app as QApplication
    participant mw as MainWindow

    CLI->>run: invoke
    run->>app: QApplication([])
    run->>app: setStyleSheet(DARK_STYLESHEET)
    run->>mw: MainWindow()
    mw->>mw: _setup_menu()
    mw->>mw: _setup_toolbar()
    mw->>mw: _setup_ui()
    Note over mw: Creates QSplitter, tree, QTabWidget<br/>Instantiates all 5 tab widgets
    mw->>mw: _setup_statusbar()
    mw->>mw: _setup_shortcuts()
    run->>mw: window.show()
    run->>app: app.exec()
    Note over app: Qt event loop runs
```

### Database loading sequence

```mermaid
sequenceDiagram
    participant U as User
    participant MW as MainWindow
    participant SP as splitter.py
    participant DB as DuckDB File
    participant Tabs as All Tab Widgets

    U->>MW: Open file (dialog / drag / recent)
    MW->>MW: Close existing connection
    MW->>SP: connect(path, read_only=True)
    SP->>DB: duckdb.connect(path, read_only=True)
    DB-->>SP: DuckDBPyConnection
    SP-->>MW: conn
    MW->>SP: list_tables(conn)
    SP->>DB: SHOW TABLES
    DB-->>SP: table names
    SP-->>MW: ["table1", "table2", ...]
    MW->>MW: _populate_tree(tables, filename)
    Note over MW: Fetches row count per table
    MW->>Tabs: set_connection(conn)
    MW->>Tabs: set_tables(tables)
    MW->>Tabs: explorer.load_table(conn, tables[0])
    MW->>MW: status bar updated
    MW->>MW: _add_recent(path)
```

### Drag and drop

`dragEnterEvent` accepts `.duckdb`, `.csv`, and `.json` URLs. `dropEvent` routes `.duckdb` to `_load_db` and CSV/JSON to `_do_import`.

### Export logic

`_export(fmt)` checks which tab is currently active:
- If the **SQL Query** tab is active and has a previous query (`last_sql`), the query results are exported.
- Otherwise the Explorer's currently selected table is exported.

### `run()` function

```python
def run() -> None:
    app = QApplication([])
    app.setStyleSheet(DARK_STYLESHEET)
    window = MainWindow()
    window.show()
    app.exec()
```

---

## `splitter.py` — Database Access Layer

All DuckDB queries are centralized here. No other module calls DuckDB directly.

```mermaid
mindmap
  root((splitter.py))
    Connection
      connect
      list_tables
    Schema
      table_schema
      table_row_count
      column_stats
      all_column_stats
    Fetching
      preview_table
      filtered_preview
      fetch_columns
      fetch_joined_columns
      all_numeric_columns
      numeric_columns
    SQL
      execute_sql
    Export
      export_csv
      export_json
      export_query_csv
      export_query_json
    Import
      import_csv
      import_json
```

### Connection management

#### `connect(db_path: Path) → duckdb.DuckDBPyConnection`
Opens a **read-only** DuckDB connection to a `.duckdb` file.

```python
return duckdb.connect(str(db_path), read_only=True)
```

#### `list_tables(conn) → list[str]`
Returns all table names via `SHOW TABLES`.

### Schema & statistics

#### `table_schema(conn, table) → list[dict]`
Returns one dict per column:
```python
{"name": str, "type": str, "nullable": bool}
```
Uses `PRAGMA table_info(table)`.

#### `table_row_count(conn, table) → int`
Executes `SELECT COUNT(*) FROM "table"`.

#### `column_stats(conn, table, column, col_type) → dict`

```mermaid
flowchart LR
    A["column_stats()"] --> B["Count nulls<br/>Count distinct values"]
    B --> C{Numeric type?}
    C -- Yes --> D["MIN / MAX / AVG"]
    C -- No --> E["min=None<br/>max=None<br/>avg=None"]
    D & E --> F["Return stats dict"]

    style D fill:#27ae60,color:#fff,stroke:none
    style E fill:#3a3a3a,color:#d4d4d4,stroke:none
```

Numeric detection checks for `INT`, `FLOAT`, `DOUBLE`, `DECIMAL`, `NUMERIC`, `BIGINT`, `SMALL`, `TINY`, `HUGEINT`, `REAL` in the type string (case-insensitive).

### Data fetching

#### `preview_table(conn, table, limit=100) → tuple[list[str], list[tuple]]`
`SELECT * FROM "table" LIMIT {limit}`. Returns `(column_names, rows)`.

#### `filtered_preview(conn, table, filters, limit=100) → tuple[list[str], list[tuple]]`
Applies per-column `ILIKE` filters using parameterized queries (prevents SQL injection):
```sql
SELECT * FROM "table"
WHERE CAST("col1" AS VARCHAR) ILIKE ?
  AND CAST("col2" AS VARCHAR) ILIKE ?
LIMIT {limit}
```
Each pattern is wrapped as `%{pattern}%`. Only non-empty filter values are included.

#### `fetch_joined_columns(conn, table_columns, on="ts") → tuple[list[str], list[tuple]]`

```mermaid
flowchart TD
    A["fetch_joined_columns()"] --> B["Keep only tables<br/>that have the join column"]
    B --> C{Any tables<br/>remain?}
    C -- No --> D(["Return [], []"])
    C -- Yes --> E["Build SELECT:<br/>ts + all requested columns"]
    E --> F["Build INNER JOIN chain<br/>on ts across all tables"]
    F --> G["Execute SQL"]
    G --> H(["Return col_names, rows"])

    style D fill:#d63031,color:#fff,stroke:none
    style H fill:#27ae60,color:#fff,stroke:none
```

Example for `{"Speed": ["value"], "Throttle": ["value"]}`:
```sql
SELECT "Speed"."ts" AS "ts",
       "Speed"."value" AS "Speed.value",
       "Throttle"."value" AS "Throttle.value"
FROM "Speed"
INNER JOIN "Throttle" ON "Speed"."ts" = "Throttle"."ts"
```

### SQL execution

#### `execute_sql(conn, sql) → tuple[list[str], list[tuple]]`
Executes arbitrary SQL. Raises `duckdb.Error` on failure. Returns `([], [])` for non-SELECT statements that return no description.

### Export

| Function | SQL issued |
|---|---|
| `export_csv(conn, table, path)` | `COPY "table" TO 'path' (FORMAT CSV, HEADER)` |
| `export_query_csv(conn, sql, path)` | `COPY (sql) TO 'path' (FORMAT CSV, HEADER)` |
| `export_json(conn, table, path)` | `COPY "table" TO 'path' (FORMAT JSON)` |
| `export_query_json(conn, sql, path)` | `COPY (sql) TO 'path' (FORMAT JSON)` |

### Import

| Function | SQL issued |
|---|---|
| `import_csv(conn, csv_path, table_name)` | `CREATE TABLE "name" AS SELECT * FROM read_csv_auto('path')` |
| `import_json(conn, json_path, table_name)` | `CREATE TABLE "name" AS SELECT * FROM read_json_auto('path')` |

Single-quotes in paths and double-quotes in table names are escaped before interpolation.

---

## `widgets.py` — Reusable Qt Widgets

### `FilterBar(QWidget)`

```mermaid
sequenceDiagram
    participant User
    participant FB as FilterBar
    participant Timer as QTimer (300ms)
    participant ET as ExplorerTab
    participant SP as splitter.py

    User->>FB: types in a filter input
    FB->>Timer: start() / restart()
    Note over Timer: resets on each keystroke
    Timer->>FB: timeout() after 300ms idle
    FB->>FB: _emit_filters()
    FB-->>ET: filters_changed({col: pattern})
    ET->>SP: filtered_preview(conn, table, filters)
    SP-->>ET: columns, rows
    ET->>ET: _populate_data(columns, rows)
```

- `set_columns(columns)` — rebuilds all inputs for the given column list.
- `get_filters() → dict[str, str]` — returns only non-empty inputs.
- `clear_filters()` — clears all inputs and immediately emits `filters_changed({})`.
- `focus_first()` — focuses the first input (used by `Ctrl+F` shortcut).

### `ExplorerTab(QWidget)`

```mermaid
flowchart TD
    A["load_table(conn, table)"] --> B["table_schema()"]
    A --> C["all_column_stats()"]
    A --> D["FilterBar.set_columns()"]
    A --> E["_reload_data()"]
    B --> Schema["Schema sub-tab"]
    C --> Stats["Statistics sub-tab"]
    E --> F{Filters active?}
    F -- Yes --> G["filtered_preview()"]
    F -- No --> H["preview_table()"]
    G & H --> I["_populate_data()<br/>fill QTableWidget"]
```

Key methods:
- `set_tables(tables)` — populates the table dropdown.
- `select_table(table)` — selects a table in the dropdown.
- `_get_limit() → int` — parses the rows dropdown; `"All"` returns `0` (passed as `999_999_999` internally).

### `SqlTab(QWidget)`

```mermaid
sequenceDiagram
    participant User
    participant ST as SqlTab
    participant SP as splitter.py

    User->>ST: Ctrl+Return
    ST->>ST: sql = editor.toPlainText().strip()
    ST->>ST: last_sql = sql
    ST->>ST: t0 = time.perf_counter()
    ST->>SP: execute_sql(conn, sql)
    alt Success
        SP-->>ST: columns, rows
        ST->>ST: populate results QTableWidget
        ST->>ST: status = "N rows in T.###s"
    else duckdb.Error
        SP-->>ST: raises duckdb.Error
        ST->>ST: clear results table
        ST->>ST: status = error message (red)
    end
```

`last_sql` property exposes the last successfully-submitted SQL for use by the export logic in `MainWindow`.

---

## `analyzer.py` — Signal Analyzer

**Class: `SignalAnalyzer(QWidget)` — six plot types for signal comparison and correlation.**

### Data Fetching: `_fetch_data(signals, x_col)`

```mermaid
flowchart TD
    A["_fetch_data()"] --> B{How many<br/>tables?}

    B -->|"1 table"| C["fetch_columns()"]
    C --> C1["Prefix columns as<br/>TableName.col"]

    B -->|"Multiple tables"| D{x_col == ts<br/>AND tables have ts?}

    D -- Yes --> E["fetch_joined_columns()<br/>INNER JOIN on ts"]
    E --> E1{Non-joinable<br/>tables?}
    E1 -- Yes --> E2["Skip, report in status"]
    E1 -- No --> F["Return data"]

    D -- No --> G["Row-aligned fetch"]
    G --> H["Truncate to min(len)"]
    H --> I["Merge rows"]

    C1 & E2 & F & I --> J(["col_names, rows"])

    style E fill:#e8751a,color:#fff,stroke:none
    style G fill:#00bcd4,color:#000,stroke:none
    style J fill:#27ae60,color:#fff,stroke:none
```

### Filter Pipeline: `_apply_filters(data, col_idx, x_key)`

```mermaid
flowchart LR
    Raw["Raw array N×M"] --> RF["① X-range filter"]
    RF --> VC["② Value clamp<br/>Min / Max on Y cols"]
    VC --> EN["③ Exclude NaN"]
    EN --> EZ["④ Exclude zeros"]
    EZ --> Out["Filtered array N'×M"]
    EZ --> Count["excluded = N - N'"]

    style Raw fill:#2e2e2e,color:#d4d4d4,stroke:#555
    style Out fill:#27ae60,color:#fff,stroke:none
```

Filters are composed as a boolean numpy mask (`np.ones(N, dtype=bool)`), ANDed step by step, then applied in one shot.

### Helper: `_to_float(val)`

```mermaid
flowchart LR
    V(["val"]) --> A{None?}
    A -- Yes --> NaN1(["np.nan"])
    A -- No --> B{datetime?}
    B -- Yes --> TS(["val.timestamp()"])
    B -- No --> C["float(val)"]
    C --> D{ValueError<br/>or TypeError?}
    D -- Yes --> NaN2(["np.nan"])
    D -- No --> F(["float"])
```

### Plot Type Decision

```mermaid
flowchart TD
    Plot(["_plot() called"]) --> CF{Plot type ==<br/>Correlation Finder?}
    CF -- Yes --> CFF["_plot_correlation_finder()"]
    CF -- No --> Sig{Signals<br/>selected?}
    Sig -- No --> Err["Show status error"]
    Sig -- Yes --> Fetch["_fetch_data()"]
    Fetch --> ToFloat["Build numpy array"]
    ToFloat --> Filt["_apply_filters()"]
    Filt --> PT{Plot type?}

    PT -->|Line| PL["_plot_line()"]
    PT -->|Scatter| PS["_plot_scatter()"]
    PT -->|Histogram| PH["_plot_histogram()"]
    PT -->|Correlation Matrix| PC["_plot_correlation()"]
    PT -->|Cross-Correlation| PX["_plot_cross_correlation()"]

    style CFF fill:#e040fb,color:#fff,stroke:none
    style PL fill:#e8751a,color:#fff,stroke:none
    style PC fill:#00bcd4,color:#000,stroke:none
    style PX fill:#f5a623,color:#000,stroke:none
```

### Dual Y-axis Trigger (Line plot)

When exactly 2 signals are selected and their value ranges differ by more than 10×, the line plot automatically switches to a dual Y-axis layout:

```mermaid
flowchart LR
    Two["2 signals selected"] --> Ratio["ratio = max_range / min_range"]
    Ratio --> Check{ratio > 10?}
    Check -- Yes --> Twin["ax.twinx()<br/>A=left · B=right"]
    Check -- No --> Single["Single Y-axis<br/>both overlaid"]

    style Twin fill:#e8751a,color:#fff,stroke:none
```

### Correlation Finder Pipeline

```mermaid
flowchart TD
    A["_plot_correlation_finder()"] --> B["all_numeric_columns()<br/>exclude ts"]
    B --> C{Enough data<br/>to correlate?}
    C -- No --> ERR["Error on canvas"]
    C -- Yes --> D{Tables have ts?}
    D -- Yes --> E["fetch_joined_columns()"]
    D -- No --> F["Row-aligned fetch"]
    E --> G{Rows returned?}
    G -- No --> F
    F & G --> H["Build numpy array"]
    H --> I["Pearson + Spearman r<br/>for all column pairs"]
    I --> J["Top 20 by |Pearson r|"]
    J --> K["Horizontal bar chart<br/>green=positive · red=negative"]

    style ERR fill:#d63031,color:#fff,stroke:none
    style K fill:#27ae60,color:#fff,stroke:none
```

---

## `advanced.py` — Advanced Analysis

**Class: `AdvancedAnalysis(QWidget)` — four specialized analysis modes via a `QStackedWidget`.**

### Analysis Mode Dispatch

```mermaid
flowchart LR
    A(["_analyze() called"]) --> B["fig.clear()"]
    B --> C{Analysis mode}
    C -->|"Derived Signal"| D["_analyze_derived()"]
    C -->|"Lap Comparison"| E["_analyze_lap_comparison()"]
    C -->|"FFT / Spectral"| F["_analyze_fft()"]
    C -->|"Rolling Statistics"| G["_analyze_rolling()"]
    D & E & F & G --> H["canvas.draw()"]

    style D fill:#e8751a,color:#fff,stroke:none
    style E fill:#f5a623,color:#000,stroke:none
    style F fill:#00bcd4,color:#000,stroke:none
    style G fill:#e040fb,color:#fff,stroke:none
```

### Helper: `_fetch_table_data(table, col="value")`

```mermaid
flowchart TD
    A["_fetch_table_data()"] --> B["table_schema()"]
    B --> C{col in table?}
    C -- Yes --> UseCol["val_col = col"]
    C -- No --> D{"value in table?"}
    D -- Yes --> UseVal["val_col = 'value'"]
    D -- No --> E["numeric_columns()<br/>first non-ts col"]
    E --> F{Found?}
    F -- No --> Fail(["Return None"])
    UseCol & UseVal & F -- Yes --> G["fetch_columns()<br/>ts + val_col"]
    G --> H{Table has ts?}
    H -- Yes --> J["ts + vals arrays"]
    H -- No --> K["ts = arange(N)<br/>vals array"]
    J & K --> OK(["Return (ts, vals)"])

    style Fail fill:#d63031,color:#fff,stroke:none
    style OK fill:#27ae60,color:#fff,stroke:none
```

### Derived Signal

```mermaid
flowchart TD
    A["_analyze_derived()"] --> B{Operator?}

    B -- d/dt --> DT["Fetch signal A"]
    DT --> DTF["_apply_range_filter()"]
    DTF --> DTD["np.gradient(val) / np.gradient(ts)"]
    DTD --> DTI["Replace inf with NaN"]
    DTI --> DTO{Plot original?}
    DTO -- Yes --> AX2["ax.twinx()<br/>original + d/dt"]
    DTO -- No --> AX1["Plot d/dt only"]

    B -- Binary --> BIN["Fetch signals A and B"]
    BIN --> BINL["Truncate to min length"]
    BINL --> BINF["_apply_range_filter()"]
    BINF --> OP{Operator}
    OP -->|"+"| PA["A + B"]
    OP -->|"-"| PS["A - B"]
    OP -->|"*"| PM["A * B"]
    OP -->|"/"| PD["A/B (NaN if B=0)"]
    PA & PS & PM & PD --> Plot["Plot derived signal"]

    style DT fill:#00bcd4,color:#000,stroke:none
    style BIN fill:#e8751a,color:#fff,stroke:none
```

### Lap Detection

```mermaid
flowchart TD
    A["_detect_laps()"] --> B["Fetch lap marker table"]
    B --> C["Remove NaN timestamps"]
    C --> D["Sort by ts"]
    D --> E["Deduplicate:<br/>keep rows where value changes"]
    E --> F["Store ts as lap boundary edges"]
    F --> G["n_laps = len(edges) - 1"]
    G --> H["Status: N laps detected"]

    style H fill:#27ae60,color:#fff,stroke:none
```

```mermaid
flowchart LR
    subgraph Input["Lap Marker Table"]
        R1["ts=100, val=1"]
        R2["ts=100, val=1"]
        R3["ts=185, val=2"]
        R4["ts=270, val=3"]
    end

    subgraph After["After dedup + sort"]
        E1["boundary: ts=100"]
        E2["boundary: ts=185"]
        E3["boundary: ts=270"]
    end

    subgraph Laps["Detected Laps"]
        L1["Lap 1: 100s to 185s"]
        L2["Lap 2: 185s to 270s"]
    end

    R1 & R2 --> E1
    R3 --> E2
    R4 --> E3
    E1 & E2 --> L1
    E2 & E3 --> L2
```

### FFT — Pre-processing

```mermaid
flowchart TD
    A["_analyze_fft()"] --> A1{Exactly 1<br/>signal?}
    A1 -- No --> ERR["Error: need 1 signal"]
    A1 -- Yes --> B["_fetch_table_data()"]
    B --> C["_apply_range_filter()"]
    C --> D["Remove NaN rows"]
    D --> E{len >= 4?}
    E -- No --> ERR2["Error: not enough data"]
    E -- Yes --> F["Estimate sample rate<br/>fs = 1 / median(diff(ts))"]
    F --> G{dt <= 0?}
    G -- Yes --> ERR3["Error: non-monotonic ts"]
    G -- No --> H["DC removal: vals -= mean(vals)"]
    H --> Win["Apply window function"]

    style ERR fill:#d63031,color:#fff,stroke:none
    style ERR2 fill:#d63031,color:#fff,stroke:none
    style ERR3 fill:#d63031,color:#fff,stroke:none
    style Win fill:#e8751a,color:#fff,stroke:none
```

### FFT — Windowing & Spectral Output

```mermaid
flowchart TD
    Win["DC-removed signal"] --> I{Window function}
    I -->|None| W1["np.ones(N)"]
    I -->|Hanning| W2["np.hanning(N)"]
    I -->|Hamming| W3["np.hamming(N)"]
    I -->|Blackman| W4["np.blackman(N)"]
    W1 & W2 & W3 & W4 --> J["Apply window to signal"]
    J --> K["scipy.fft.rfft()"]
    K --> L["Single-sided amplitude:<br/>|yf| / N * 2"]
    L --> M{Max freq set?}
    M -- Yes --> N["Truncate to max_freq"]
    M -- No --> O{Log scale?}
    N --> O
    O -- Yes --> P["20 * log10(mag + epsilon)"]
    O -- No --> Q["Linear amplitude"]
    P & Q --> R["ax.fill_between() + plot()"]

    style Win fill:#e8751a,color:#fff,stroke:none
    style R fill:#27ae60,color:#fff,stroke:none
```

### Rolling Statistics

```mermaid
flowchart LR
    A["_analyze_rolling()"] --> B["For each signal"]
    B --> C["_fetch_table_data()"]
    C --> D["_apply_range_filter()"]
    D --> E{len >= window?}
    E -- No --> SKIP["Skip: not enough data"]
    E -- Yes --> F{Show original?}
    F -- Yes --> G["Plot raw signal<br/>alpha=0.3"]
    F -- No --> H
    G --> H{Statistic}
    H -->|Moving Avg| MA["Moving Average<br/>uniform_filter1d"]
    H -->|Rolling StdDev| SD["Rolling Std Dev<br/>via uniform_filter1d"]
    H -->|Upper Envelope| UE["Upper Envelope<br/>maximum_filter1d"]
    H -->|Lower Envelope| LE["Lower Envelope<br/>minimum_filter1d"]
    H -->|Median Filter| MF["Median Filter<br/>edge-preserving"]
    MA & SD & UE & LE & MF --> Plot["Plot smoothed signal"]

    style SKIP fill:#856404,color:#fff,stroke:none
    style Plot fill:#27ae60,color:#fff,stroke:none
```

---

## `track_viewer.py` — Track Viewer

**Class: `TrackViewer(QWidget)` — GPS track map with colour-by-signal overlay.**

### GPS Table Discovery

```mermaid
flowchart LR
    A["_find_gps_tables()"] --> B["Check each table name<br/>(lowercased)"]
    B --> C{In latitude set?}
    C -- Yes --> LAT["lat_table = tbl"]
    C -- No --> D{In longitude set?}
    D -- Yes --> LON["lon_table = tbl"]
    D -- No --> E{In speed set?}
    E -- Yes --> SPD["speed_table = tbl"]
    LAT & LON & SPD --> F(["Return lat, lon, speed tables"])

    subgraph lat_names["Latitude names"]
        direction TB
        L1["latitude, lat, gps_lat,<br/>gps_latitude, gpslat"]
    end
    subgraph lon_names["Longitude names"]
        direction TB
        L2["longitude, lon, lng,<br/>gps_lon, gps_longitude"]
    end
```

### Track Rendering Pipeline

```mermaid
flowchart TD
    A["_plot_track_map()"] --> B["_find_gps_tables()"]
    B --> C{lat AND<br/>lon found?}
    C -- No --> ERR["Error: list available tables"]
    C -- Yes --> D["Fetch lat & lon values"]
    D --> E["Truncate to min(len_lat, len_lon)"]
    E --> F["Remove NaN and (0,0) dropouts"]
    F --> G["Apply sidebar filters"]
    G --> H{Colour signal<br/>enabled?}
    H -- Yes --> I["Fetch & align colour signal"]
    H -- No --> J
    I --> K["Build LineCollection<br/>cmap=plasma"]
    K --> L["Add colorbar"]
    L --> J["Plot base track (orange)"]
    J --> M["Start / Finish markers"]
    M --> N["ax.set_aspect('equal')"]
    N --> O["apply_plot_theme()"]

    style ERR fill:#d63031,color:#fff,stroke:none
    style O fill:#27ae60,color:#fff,stroke:none
```

---

## `theme.py` — Dark Theme & Plot Colors

### `PLOT_COLORS` Palette

```mermaid
graph LR
    C0["#e8751a<br/>Orange"]
    C1["#f5a623<br/>Amber"]
    C2["#00bcd4<br/>Cyan"]
    C3["#e040fb<br/>Magenta"]
    C4["#27ae60<br/>Green"]
    C5["#d63031<br/>Red"]
    C6["#4fc3f7<br/>Sky Blue"]
    C7["#ab47bc<br/>Violet"]

    C0 -.-> C1 -.-> C2 -.-> C3 -.-> C4 -.-> C5 -.-> C6 -.-> C7 -.-> C0

    style C0 fill:#e8751a,color:#fff,stroke:none
    style C1 fill:#f5a623,color:#000,stroke:none
    style C2 fill:#00bcd4,color:#000,stroke:none
    style C3 fill:#e040fb,color:#fff,stroke:none
    style C4 fill:#27ae60,color:#fff,stroke:none
    style C5 fill:#d63031,color:#fff,stroke:none
    style C6 fill:#4fc3f7,color:#000,stroke:none
    style C7 fill:#ab47bc,color:#fff,stroke:none
```

Colors cycle via `PLOT_COLORS[i % len(PLOT_COLORS)]` across all plot types.

### `apply_plot_theme(fig, ax)`

Applied at the end of every plot method in every tab widget:

| Element | Value |
|---|---|
| Figure background | `#1a1a1a` |
| Axes background | `#242424` |
| Text / tick labels | `#d4d4d4` |
| Grid color | `#3a3a3a`, alpha 0.5, linewidth 0.5 |
| Spines | `#3a3a3a` |
| Legend frame | `#242424` bg, `#3a3a3a` border, `#d4d4d4` text |

### `DARK_STYLESHEET`

A comprehensive Qt Style Sheet string covering every widget class used in LMUPI. The accent color (`#e8751a` orange) is applied to:

```mermaid
mindmap
  root((Accent Color))
    Active tab border-bottom
    Focused QLineEdit border
    QMenuBar item selected
    QMenu item selected
    Toolbar button hover color
    QPushButton accent background
    QTreeWidget item selected
    QComboBox selection color
    QTableWidget selection color
```
