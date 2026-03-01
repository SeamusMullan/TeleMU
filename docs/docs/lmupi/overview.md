# LMUPI — Parser & Data Pipeline

LMUPI is the Python backend responsible for reading `.duckdb` telemetry files from Le Mans Ultimate and splitting them into organized, consumable data.

## Stack

- Python 3.13+ (managed with uv)
- DuckDB
- NumPy, SciPy
- Matplotlib

## Project Layout

```
LMUPI/
├── main.py             # Application entry point
├── pyproject.toml      # uv project config & dependencies
└── .python-version     # Python version pin
```

## Design

The application logic (`main.py`) and the data splitting/transformation logic are kept separate. This allows the splitting module to be tested and evolved independently from how the app is invoked.

!!! note "TODO"
    Scaffold the splitting module once the `.duckdb` schema is explored.
