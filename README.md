# TeleMU

**Telemetry Analysis Platform for Le Mans Ultimate**

TeleMU is a Python-based telemetry analysis platform for [Le Mans Ultimate](https://www.lemansvirtual.com/). It reads live telemetry from LMU's shared memory, records sessions to `.tmu` files, analyses post-session data via DuckDB, and (planned) streams telemetry to a remote race engineer over LAN.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| UI | PySide6 / Qt6 |
| Data | DuckDB (read-only `.duckdb` files) |
| Analysis | NumPy, SciPy, Matplotlib |
| Live Telemetry | ctypes shared memory (LMU `SharedMemoryInterface`) |
| Recording | `.tmu` binary format (planned) |
| Streaming | UDP/TCP over LAN (planned) |

## Project Structure

```
TeleMU/
├── LMUPI/              # Python application (uv project)
│   ├── lmupi/
│   │   ├── app.py              # MainWindow, entry point
│   │   ├── splitter.py         # DuckDB gateway (all SQL here)
│   │   ├── widgets.py          # ExplorerTab, SqlTab, FilterBar
│   │   ├── analyzer.py         # SignalAnalyzer (6 plot types)
│   │   ├── advanced.py         # AdvancedAnalysis (4 analysis types)
│   │   ├── track_viewer.py     # GPS track map
│   │   ├── dashboard.py        # Live telemetry dashboard
│   │   ├── telemetry_reader.py # QThread polling shared memory
│   │   ├── theme.py            # Dark theme, plot colours
│   │   └── sharedmem/          # LMU shared memory layer
│   │       ├── lmu_data.py     # ctypes struct definitions
│   │       ├── lmu_mmap.py     # Platform mmap abstraction
│   │       └── lmu_type.py     # Type annotations
│   └── pyproject.toml
└── docs/               # MkDocs Material documentation
```

## Getting Started

```bash
# Clone
git clone https://github.com/SeamusMullan/TeleMU.git
cd TeleMU/LMUPI

# Install dependencies (requires uv)
uv sync

# Run the app
uv run lmupi
```

## Documentation

Full docs are built with MkDocs Material:

```bash
cd docs
uv run mkdocs serve
```

Then open [http://localhost:8000](http://localhost:8000).

Key sections:

- [Architecture Overview](docs/docs/architecture/overview.md) — C4 diagrams, system design
- [Data Pipeline](docs/docs/architecture/data-pipeline.md) — data flow through all subsystems
- [Shared Memory](docs/docs/shared-memory/overview.md) — LMU shared memory interface
- [Recording](docs/docs/recording/overview.md) — `.tmu` format and session recording
- [Streaming](docs/docs/streaming/overview.md) — LAN telemetry streaming
- [Race Engineer](docs/docs/race-engineer/overview.md) — strategy engine design
- [LMUPI App](docs/docs/lmupi/overview.md) — module reference
- [Agent Guide](docs/docs/contributing/agent-guide.md) — for LLM coding agents

## License

See [LICENSE](LICENSE) for details.
