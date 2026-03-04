"""FastAPI app factory and lifespan management."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from telemu import __version__
from telemu.config import settings
from telemu.lovense import LovenseClient
from telemu.reader import DemoReader, TelemetryFrame, TelemetryReader
from telemu.streaming import StreamingClient
from telemu.ws.manager import ConnectionManager
from telemu.ws.router import manager as ws_manager
from telemu.ws.router import router as ws_router
from telemu.ws import protocol

logger = logging.getLogger(__name__)


async def _on_frame(manager: ConnectionManager, frame: TelemetryFrame) -> None:
    """Bridge telemetry frames to WebSocket broadcasts."""
    await manager.broadcast(
        protocol.TELEMETRY,
        {"type": protocol.TELEMETRY, "ts": frame.ts, "channels": frame.channels},
    )
    await manager.broadcast(
        protocol.STATUS,
        {"type": protocol.STATUS, **frame.status},
    )
    if frame.lap_info:
        # Send lap info as part of telemetry channel
        await manager.broadcast(
            protocol.TELEMETRY,
            {"type": "lap_info", **frame.lap_info},
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    # Create data directory
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Start telemetry reader
    if settings.demo_mode:
        reader = DemoReader(poll_ms=settings.poll_ms)
    else:
        reader = TelemetryReader(poll_ms=settings.poll_ms)

    app.state.reader = reader
    app.state.ws_manager = ws_manager
    app.state.db_conn = None
    app.state.streaming_client = StreamingClient(ws_manager)
    if not hasattr(app.state, "lovense"):
        app.state.lovense = LovenseClient(
            verify_tls=settings.lovense_verify_tls,
            timeout_sec=settings.lovense_timeout_sec,
        )
        if settings.lovense_domain:
            app.state.lovense.configure(settings.lovense_domain, settings.lovense_https_port)

    reader.subscribe(lambda frame: _schedule_broadcast(app, frame))
    await reader.start()

    # Auto-connect streaming client if configured
    if settings.streaming_host:
        await app.state.streaming_client.start(
            settings.streaming_host, settings.streaming_port
        )

    logger.info("TeleMU v%s started (demo=%s)", __version__, settings.demo_mode)

    yield

    await reader.stop()
    await app.state.streaming_client.stop()
    if app.state.db_conn is not None:
        try:
            app.state.db_conn.close()
        except Exception:
            pass
    logger.info("TeleMU shutdown complete")


def _schedule_broadcast(app: FastAPI, frame: TelemetryFrame) -> None:
    """Schedule async broadcast from sync callback."""
    import asyncio

    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_on_frame(app.state.ws_manager, frame))
    except RuntimeError:
        pass


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TeleMU",
        version=__version__,
        lifespan=lifespan,
    )
    app.state.lovense = LovenseClient(
        verify_tls=settings.lovense_verify_tls,
        timeout_sec=settings.lovense_timeout_sec,
    )
    if settings.lovense_domain:
        app.state.lovense.configure(settings.lovense_domain, settings.lovense_https_port)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routers
    from telemu.api.health import router as health_router
    from telemu.api.sessions import router as sessions_router
    from telemu.api.tables import router as tables_router
    from telemu.api.query import router as query_router
    from telemu.api.export import router as export_router
    from telemu.api.convert import router as convert_router
    from telemu.api.recordings import router as recordings_router
    from telemu.api.lovense import router as lovense_router
    from telemu.api.streaming import router as streaming_router

    app.include_router(health_router, prefix="/api")
    app.include_router(sessions_router, prefix="/api")
    app.include_router(tables_router, prefix="/api")
    app.include_router(query_router, prefix="/api")
    app.include_router(export_router, prefix="/api")
    app.include_router(convert_router, prefix="/api")
    app.include_router(recordings_router, prefix="/api")
    app.include_router(lovense_router, prefix="/api")
    app.include_router(streaming_router, prefix="/api")
    app.include_router(ws_router)

    return app


app = create_app()


def cli() -> None:
    """Entry point for `telemu` command."""
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        "telemu.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
