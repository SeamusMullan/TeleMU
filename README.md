# TeleMU

[![Release](https://img.shields.io/github/v/release/SeamusMullan/TeleMU?label=release)](https://github.com/SeamusMullan/TeleMU/releases/latest)
[![CI](https://github.com/SeamusMullan/TeleMU/actions/workflows/ci.yml/badge.svg)](https://github.com/SeamusMullan/TeleMU/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/SeamusMullan/TeleMU)](LICENSE)

**Telemetry Analysis Platform for Le Mans Ultimate**

TeleMU is a telemetry analysis platform for [Le Mans Ultimate](https://www.lemansvirtual.com/). It reads live telemetry from LMU's shared memory, provides real-time dashboards, records sessions, analyses post-session data via DuckDB, and streams telemetry to a remote race engineer over LAN.

> **v2 Rewrite** — The original PySide6 desktop app is archived on the `v1-archive` branch. v2 uses a Python/FastAPI backend + React/TypeScript/Electron frontend.

## Installation (Windows — pre-built)

Download the latest installer executable from the [Releases page](https://github.com/SeamusMullan/TeleMU/releases/latest) and run it directly — no Python installation required.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, uvicorn, WebSocket |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Desktop | Tauri 2 |
| Data | DuckDB (read-only `.duckdb` files) |
| Analysis | NumPy, SciPy |
| Charting | ECharts |
| Live Telemetry | ctypes shared memory (LMU `SharedMemoryInterface`) |
| State | Zustand |


## Getting Started

### Backend

```bash
# Clone
git clone https://github.com/SeamusMullan/TeleMU.git
cd TeleMU/LMUPI

# Install dependencies (requires uv)
uv sync
uv run uvicorn telemu.main:app --reload --port 8000
```

For demo mode (simulated telemetry without LMU running):
```bash
TELEMU_DEMO_MODE=true uv run uvicorn telemu.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173). The Vite dev server proxies `/api` and `/ws` to the backend at `:8000`.

## Documentation

Full docs are built with MkDocs Material:

```bash
cd docs
uv run mkdocs serve
```

Key sections:
- [Architecture Overview](docs/docs/architecture/overview.md)
- [Shared Memory](docs/docs/shared-memory/overview.md)
- [Recording](docs/docs/recording/overview.md)
- [Streaming](docs/docs/streaming/overview.md)
- [Race Engineer](docs/docs/race-engineer/overview.md)

## License

See [LICENSE](LICENSE) for details.
