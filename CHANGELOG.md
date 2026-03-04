# Changelog

All notable changes to TeleMU will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-04

### Added

#### Backend (Python / FastAPI)
- FastAPI application with lifespan management and CORS support (`telemu/main.py`)
- Pydantic Settings-based configuration (`telemu/config.py`)
- Async telemetry reader polling LMU shared memory at ~60 Hz (`telemu/reader.py`)
- Pydantic models for REST API and WebSocket protocol (`telemu/models.py`)
- LMU `SharedMemoryInterface` port from v1 (`telemu/sharedmem/`)
- WebSocket manager and broadcast protocol (`telemu/ws/`)
- REST endpoints:
  - `GET /health` — health check
  - Session listing, querying, and export (`telemu/api/sessions.py`, `query.py`, `export.py`)
  - DuckDB table inspection (`telemu/api/tables.py`)
  - Recording control (`telemu/api/recordings.py`, `live_recording.py`)
  - LAN streaming control (`telemu/api/streaming.py`)
  - Lovense integration stub (`telemu/api/lovense.py`)
  - File conversion utility (`telemu/api/convert.py`)
- DuckDB read-only gateway (`telemu/db/`)
- Recording subsystem with LZ4/Zstandard compression (`telemu/recording/`)
- LAN streaming subsystem skeleton (`telemu/streaming/`)
- Race engineer tooling skeleton (`telemu/engineer/`)
- Demo mode (`TELEMU_DEMO_MODE=true`) for simulated telemetry without LMU running
- `telemu` CLI entry-point and `telemu-verify` recording verification tool
- Full pytest suite with asyncio support and coverage reporting

#### Frontend (React / TypeScript / Electron)
- React 19 + TypeScript + Vite + Tailwind CSS application
- Zustand state management
- Pages: Dashboard, Explorer, Analyzer, Alerts, Streaming, Settings, Convert
- ECharts-based gauges, sparklines, and lap charts
- REST and WebSocket API clients (`src/api/`)
- Electron wrapper for desktop distribution (`electron/`)
- `useTelemetry` and `useSession` hooks
- Vitest test suite with jsdom

#### Infrastructure
- GitHub Actions CI (`ci.yml`):
  - Ubuntu backend tests with coverage
  - Ubuntu frontend lint + build + test
  - Windows backend tests (JUnit XML upload)
  - Windows PyInstaller build (`.exe` artifact upload)
- GitHub Actions Release (`release.yml`):
  - Triggered by `v*` tags
  - Runs Windows tests, builds Windows executable, publishes GitHub Release with the artifact

[0.1.0]: https://github.com/SeamusMullan/TeleMU/releases/tag/v0.1.0
