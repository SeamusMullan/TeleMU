# Data Pipeline

TeleMU has four data flows: post-session analysis, live dashboard, session recording, and LAN streaming. All live flows originate from LMU's shared memory; post-session analysis reads `.duckdb` files.

## Full Pipeline Overview

```mermaid
flowchart TD
    subgraph Sources
        LMU["LMU Game<br/>(shared memory)"]
        DDB[".duckdb files<br/>(post-session)"]
    end

    subgraph SharedMem["Shared Memory Layer"]
        mmap["MMapControl<br/>lmu_mmap.py"]
        structs["ctypes Structs<br/>lmu_data.py"]
    end

    subgraph LiveConsumers["Live Data Consumers"]
        reader["TelemetryReader<br/>(QThread, ~60Hz)"]
        dashboard["LiveDashboard<br/>gauges + sparklines"]
        recorder["TelemetryRecorder<br/>.tmu writer"]
        streamer["TelemetryStreamer<br/>UDP/TCP to LAN"]
    end

    subgraph PostSession["Post-Session Analysis"]
        splitter["splitter.py<br/>(DuckDB gateway)"]
        explorer["ExplorerTab"]
        sql["SqlTab"]
        analyzer["SignalAnalyzer"]
        track["TrackViewer"]
        advanced["AdvancedAnalysis"]
    end

    LMU -->|"mmap read"| mmap
    mmap --> structs
    structs --> reader
    reader -->|"push(channel, value)"| dashboard
    reader -->|"frame data"| recorder
    reader -->|"frame data"| streamer

    DDB -->|"read-only open"| splitter
    splitter --> explorer
    splitter --> sql
    splitter --> analyzer
    splitter --> track
    splitter --> advanced

    style recorder stroke-dasharray: 5 5
    style streamer stroke-dasharray: 5 5
```

## Flow 1 — Post-Session Analysis

The original and most mature flow. A driver loads a `.duckdb` file after a session.

```mermaid
sequenceDiagram
    participant User
    participant MainWindow
    participant Splitter as splitter.py
    participant DuckDB
    participant Tab as Any Analysis Tab

    User->>MainWindow: Open .duckdb file (Ctrl+O)
    MainWindow->>Splitter: connect(db_path)
    Splitter->>DuckDB: READ_ONLY connection
    MainWindow->>Splitter: list_tables(conn)
    Splitter-->>MainWindow: table names
    MainWindow->>Tab: set_connection(conn, tables)
    User->>Tab: Select signals / run query
    Tab->>Splitter: fetch_columns() or execute_sql()
    Splitter->>DuckDB: SQL query
    DuckDB-->>Splitter: result set
    Splitter-->>Tab: DataFrame / rows
    Tab->>Tab: Render plot / table
```

**Key details:**

- `splitter.py` is the **only** module that issues SQL
- Tables with a `ts` column are INNER JOINed on `ts` for cross-table queries
- Tables without `ts` are row-aligned and shown with a visual indicator in the UI
- All connections are read-only — analysis never mutates source data

## Flow 2 — Live Dashboard

The driver runs LMU and TeleMU simultaneously. Telemetry flows from shared memory to the dashboard in real time.

```mermaid
sequenceDiagram
    participant LMU as LMU Game
    participant SHM as Shared Memory (LMU_Data)
    participant Reader as TelemetryReader (QThread)
    participant Dashboard as LiveDashboard

    LMU->>SHM: Write telemetry structs (~60Hz)
    loop Every 16ms
        Reader->>SHM: MMapControl.update()
        SHM-->>Reader: LMUObjectOut snapshot
        Reader->>Reader: Extract vehicle telemetry
        Reader->>Dashboard: push("Speed", 287.4)
        Reader->>Dashboard: push("RPM", 8420)
        Reader->>Dashboard: push("TyreFL", 98.2)
        Note over Reader,Dashboard: ~12 channels per poll
    end
    Dashboard->>Dashboard: Refresh gauges (50ms timer)
    Dashboard->>Dashboard: Refresh sparklines (200ms timer)
```

**Key details:**

- `MMapControl` uses **copy mode** by default — snapshots the buffer only when both scoring and telemetry updates are flagged, ensuring consistency
- `TelemetryReader` extracts the player's vehicle using `playerVehicleIdx`
- Speed is computed from `mLocalVel` vector magnitude × 3.6 (m/s → km/h)
- Tyre temps use the centre reading (`mTemperature[1]`) converted from Kelvin
- Status indicators (DRS, PIT, FLAG, TC, ABS) are derived from scoring and telemetry deltas

## Flow 3 — Session Recording (Planned)

Captures live telemetry to a `.tmu` file for later replay or conversion to DuckDB.

```mermaid
flowchart LR
    Reader["TelemetryReader"] -->|"frame data<br/>(Qt signal)"| Recorder["TelemetryRecorder<br/>(QThread)"]
    Recorder -->|"compressed frames"| TMU[".tmu file"]
    TMU -->|"tmu2duckdb"| DDB[".duckdb file"]

    style Recorder stroke-dasharray: 5 5
```

**Design:**

- Recorder runs on its own QThread, receives frame data via Qt signal from `TelemetryReader`
- Writes frames with timestamps and zstd compression
- `.tmu` files can be replayed in the dashboard or converted to `.duckdb` for post-session analysis
- See [Recording Overview](../recording/overview.md) for format spec

## Flow 4 — LAN Streaming (Planned)

Streams telemetry from the driver's PC to a race engineer's PC over the local network.

```mermaid
flowchart LR
    Reader["TelemetryReader"] -->|"frame data"| Streamer["TelemetryStreamer"]
    Streamer -->|"UDP telemetry"| LAN["Local Network"]
    LAN -->|"UDP telemetry"| Client["Engineer's TeleMU"]
    Client --> EngineerDash["Race Engineer UI"]

    Streamer ---|"TCP control"| Client

    style Streamer stroke-dasharray: 5 5
    style Client stroke-dasharray: 5 5
    style EngineerDash stroke-dasharray: 5 5
```

**Design:**

- UDP for high-frequency telemetry (low latency, tolerates drops)
- TCP for control messages (connect, subscribe, session info)
- UDP multicast or broadcast for discovery on LAN
- See [Streaming Overview](../streaming/overview.md) and [Protocol Spec](../streaming/protocol.md)

## Agent Notes

- When implementing a new data consumer, connect to `TelemetryReader`'s Qt signals — do not read shared memory directly
- The post-session flow is stable; the live flow is working; recording and streaming are planned
- Recording should follow the QThread pattern established by `TelemetryReader`
- The `.tmu` → `.duckdb` converter should produce files compatible with the existing `splitter.py` API
- Files to reference: `telemetry_reader.py` (signal definitions), `dashboard.py` (consumer pattern), `splitter.py` (DuckDB schema expectations)
