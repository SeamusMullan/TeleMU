# TeleMU

**Telemetry Analysis Engine for Le Mans Ultimate**

TeleMU is a telemetry analysis toolchain for [Le Mans Ultimate](https://www.lemansvirtual.com/). It ingests `.duckdb` telemetry files exported by LMU, parses and organizes the data via a Python backend, and presents it through an Electrobun desktop application.

## Project Structure

```
TeleMU/
├── LMUPI/          # Python parser & data pipeline (uv project)
├── TeleMU/         # Electrobun desktop frontend
└── docs/           # This documentation (MKDocs + Material)
```

## Components

| Component | Stack | Role |
|-----------|-------|------|
| **LMUPI** | Python, DuckDB, NumPy, SciPy, Matplotlib | Parse `.duckdb` telemetry files, split and organize data |
| **TeleMU** | Electrobun, TypeScript, Tailwind | Desktop UI for viewing parsed telemetry |
| **docs** | MKDocs Material | Project documentation |

## Quick Links

- [Architecture Overview](architecture/overview.md)
- [Data Pipeline](architecture/data-pipeline.md)
- [LMUPI Parser](lmupi/overview.md)
- [TeleMU Frontend](telemu/overview.md)
