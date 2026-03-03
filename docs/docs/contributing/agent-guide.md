# Agent Guide

This guide is for LLM coding agents working on TeleMU. It covers reading order, architectural patterns, naming conventions, and testing expectations.

## Reading Order

Read these docs in order before starting any implementation work:

1. **[Architecture Overview](../architecture/overview.md)** — understand the C4 diagrams and how modules connect
2. **[Data Pipeline](../architecture/data-pipeline.md)** — understand the four data flows
3. **[Shared Memory Overview](../shared-memory/overview.md)** — understand how live data enters the system
4. **The specific subsystem docs** for your task (recording, streaming, race-engineer)
5. **The existing source code** for patterns to follow (see below)

## Key Source Files to Read

| File | Why |
|------|-----|
| `LMUPI/lmupi/app.py` | How modules are wired together, tab creation |
| `LMUPI/lmupi/splitter.py` | The DuckDB gateway pattern — all SQL goes here |
| `LMUPI/lmupi/telemetry_reader.py` | The QThread + push pattern for live data |
| `LMUPI/lmupi/dashboard.py` | How a live data consumer works (push API, refresh timers) |
| `LMUPI/lmupi/sharedmem/lmu_mmap.py` | How shared memory is accessed |
| `LMUPI/lmupi/theme.py` | Dark theme, plot colours, styling conventions |

## Architectural Patterns

### 1. Splitter Pattern (Post-Session Data)

All DuckDB queries go through `splitter.py`. No other module imports `duckdb`.

```python
# CORRECT
from lmupi.splitter import fetch_columns
data = fetch_columns(conn, table, columns)

# WRONG — never do this
import duckdb
conn = duckdb.connect(path)
```

### 2. Push Pattern (Live Data)

`TelemetryReader` pushes data to consumers. Consumers never poll shared memory directly.

```python
# In TelemetryReader._poll_once():
self._dashboard.push("Speed", speed_kmh)

# In dashboard or any consumer:
def push(self, channel_name: str, value: float):
    self._channels[channel_name].history.append(value)
```

### 3. QThread Pattern (Background Work)

Any I/O, polling, or long computation runs on a QThread. The GUI thread only handles rendering.

```python
class MyWorker(QThread):
    result_ready = Signal(object)
    error = Signal(str)

    def run(self):
        try:
            # Do work here (not on GUI thread)
            self.result_ready.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

### 4. Tab Pattern (New UI Components)

Each tab is a self-contained QWidget. `MainWindow` (in `app.py`) creates it and wires connections.

```python
# In app.py:
self._my_tab = MyTab()
self._tabs.addTab(self._my_tab, "My Tab")

# When a DB is loaded:
self._my_tab.set_connection(conn, tables)
```

## File Naming Conventions

| Type | Convention | Example |
|------|-----------|---------|
| Module | `snake_case.py` | `telemetry_reader.py` |
| Class | `PascalCase` | `TelemetryReader` |
| Signal | `snake_case` | `recording_started` |
| Method | `snake_case` | `start_recording()` |
| Private | `_prefix` | `_poll_once()` |
| Constants | `UPPER_SNAKE` | `MAX_MAPPED_VEHICLES` |
| Package dir | `snake_case/` | `sharedmem/` |

## New Module Checklist

When creating a new module:

- [ ] Place it in `LMUPI/lmupi/`
- [ ] Use relative imports within the package
- [ ] Follow the appropriate pattern (splitter, push, QThread, or tab)
- [ ] Wire it into `app.py` if it's a UI component
- [ ] Add any new dependencies to `LMUPI/pyproject.toml`
- [ ] Update docs (the relevant overview + modules reference)

## Testing Patterns

TeleMU doesn't have a formal test suite yet, but follow these patterns:

### Unit Tests

- Test data transformations in isolation (fuel calculations, sector normalisation)
- Use mock data — don't require LMU running
- Place tests in `LMUPI/tests/` with `test_` prefix

### Integration Tests

- For shared memory: use the `test_api()` function in `lmu_mmap.py` as a template
- For recording: round-trip test (write .tmu → read .tmu → verify data matches)
- For streaming: loopback test (stream on 127.0.0.1, verify received data)

### Manual Verification

- Run `uv run lmupi` and verify the UI works
- For docs: run `cd docs && uv run mkdocs serve` and check all pages render

## "Agent Notes" Convention

Every documentation page should end with an **"Agent Notes"** section containing:

1. **Files to create or modify** — exact paths
2. **Interfaces to implement** — class names, method signatures
3. **Existing patterns to follow** — which module to use as a template
4. **Test strategy** — what to test and how
5. **Related GitHub issues** — issue numbers if known

When writing a new doc page, always include this section. When implementing a feature, check the Agent Notes first.

## Common Gotchas

1. **Sector numbering**: LMU uses 0=S3, 1=S1, 2=S2. Always normalise to 1=S1, 2=S2, 3=S3.
2. **Temperature units**: shared memory uses Kelvin for tyre temps. Always convert: `celsius = kelvin - 273.15`.
3. **Vehicle indexing**: use `playerVehicleIdx` to find the player's vehicle, not index 0.
4. **Thread safety**: never access Qt widgets from a QThread. Use signals to communicate.
5. **Copy mode**: always use `access_mode=0` (copy) when reading shared memory from a QThread.
6. **Read-only DuckDB**: all `.duckdb` connections are read-only. Never write to analysis databases.
7. **ts column**: DuckDB tables are JOINed on the `ts` column. Any new table from recording conversion must include `ts`.

## Agent Notes

- This file itself should be updated when new patterns or conventions are established
- When completing a feature, update the relevant doc pages (not just code)
- If you discover a pattern or gotcha not listed here, add it
- The project uses `uv` for package management — use `uv add <package>` to add dependencies
