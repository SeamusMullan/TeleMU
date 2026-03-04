"""Application configuration via environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """TeleMU backend settings.

    All values can be overridden via environment variables prefixed with TELEMU_.
    """

    model_config = {"env_prefix": "TELEMU_"}

    host: str = "127.0.0.1"
    port: int = 8000
    reload: bool = False

    # Telemetry reader
    poll_ms: int = 16  # ~60Hz
    demo_mode: bool = False  # generate simulated data when LMU is not running

    # Data directory for .duckdb and .tmu files
    data_dir: Path = Path.home() / "Documents" / "TeleMU"

    # WebSocket
    ws_max_fps: int = 60

    # Lovense integration
    lovense_domain: str | None = None
    lovense_https_port: int = 30010
    lovense_verify_tls: bool = False
    lovense_timeout_sec: float = 5.0

    # CORS (for development; Electron doesn't need this)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


settings = Settings()
