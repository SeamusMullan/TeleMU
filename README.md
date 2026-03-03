# TeleMU

**Telemetry Analysis Platform for Le Mans Ultimate**

TeleMU is a telemetry analysis platform for [Le Mans Ultimate](https://www.lemansvirtual.com/). It reads live telemetry from LMU's shared memory, provides real-time dashboards, records sessions, analyses post-session data via DuckDB, and streams telemetry to a remote race engineer over LAN.

> **v2 Rewrite** — The original PySide6 desktop app is archived on the `v1-archive` branch. v2 uses a Python/FastAPI backend + React/TypeScript/Electron frontend.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, FastAPI, uvicorn, WebSocket |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS |
| Desktop | Electron |
| Data | DuckDB (read-only `.duckdb` files) |
| Analysis | NumPy, SciPy |
| Charting | ECharts |
| Live Telemetry | ctypes shared memory (LMU `SharedMemoryInterface`) |
| State | Zustand |

## Project Structure

```
TeleMU/
├── backend/                # Python FastAPI backend (uv project)
│   ├── telemu/
│   │   ├── main.py         # FastAPI app, lifespan, CORS
│   │   ├── config.py       # Pydantic Settings
│   │   ├── reader.py       # Async telemetry reader (~60Hz)
│   │   ├── models.py       # Pydantic models (API + WebSocket)
│   │   ├── sharedmem/      # LMU shared memory (from v1)
│   │   ├── ws/             # WebSocket manager + protocol
│   │   ├── api/            # REST endpoints
│   │   ├── db/             # DuckDB gateway
│   │   ├── recording/      # .tmu recording (planned)
│   │   ├── streaming/      # LAN streaming (planned)
│   │   └── engineer/       # Race engineer tools (planned)
│   └── tests/
├── frontend/               # React + TypeScript + Electron
│   ├── src/
│   │   ├── api/            # REST + WebSocket clients
│   │   ├── stores/         # Zustand state management
│   │   ├── pages/          # Dashboard, Explorer, Analyzer, Settings
│   │   ├── components/     # Gauges, sparklines, charts
│   │   └── hooks/          # useTelemetry, useSession
│   └── electron/           # Electron main process
└── docs/                   # MkDocs documentation
```

## Getting Started

### Backend

```bash
cd backend
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

### Electron

```bash
cd frontend
npm run electron:dev
```

### Tests

```bash
cd backend && uv run pytest
cd frontend && npm run test
```

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
