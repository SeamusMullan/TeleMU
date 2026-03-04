"""Tests for live recording REST endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from telemu.main import create_app
from telemu.recording.live_recorder import LiveRecorder


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(tmp_path):
    app = create_app()
    # Attach a fresh recorder wired to the tmp dir
    recorder = LiveRecorder()
    app.state.live_recorder = recorder
    # Override data_dir for tests
    from telemu import config
    config.settings.data_dir = tmp_path

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    # Cleanup: stop recorder if still active
    if recorder.active:
        await recorder.stop()


@pytest.mark.anyio
async def test_status_idle(client):
    resp = await client.get("/api/live-recording/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is False
    assert data["filename"] == ""


@pytest.mark.anyio
async def test_start_and_stop(client, tmp_path):
    # Start
    resp = await client.post(
        "/api/live-recording/start",
        json={"output_dir": str(tmp_path)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is True
    assert data["filename"].endswith(".tmu")

    # Status while recording
    resp = await client.get("/api/live-recording/status")
    assert resp.status_code == 200
    assert resp.json()["active"] is True

    # Stop
    resp = await client.post("/api/live-recording/stop", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] is False
    assert data["filename"].endswith(".tmu")


@pytest.mark.anyio
async def test_start_twice_returns_409(client, tmp_path):
    await client.post(
        "/api/live-recording/start",
        json={"output_dir": str(tmp_path)},
    )
    resp = await client.post(
        "/api/live-recording/start",
        json={"output_dir": str(tmp_path)},
    )
    assert resp.status_code == 409

    # Cleanup
    await client.post("/api/live-recording/stop", json={})


@pytest.mark.anyio
async def test_stop_when_idle_returns_409(client):
    resp = await client.post("/api/live-recording/stop", json={})
    assert resp.status_code == 409
