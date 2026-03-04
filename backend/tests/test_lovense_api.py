"""Tests for Lovense API endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from telemu.main import create_app


class FakeLovenseClient:
    def __init__(self):
        self._status = {
            "configured": False,
            "domain": None,
            "https_port": None,
            "verify_tls": False,
        }

    def status(self):
        return self._status

    def configure(self, domain: str, https_port: int = 30010):
        self._status = {
            "configured": True,
            "domain": domain,
            "https_port": https_port,
            "verify_tls": False,
        }

    async def resolve_lan(self, token: str, uid: str):
        return {"code": 200, "message": "OK", "data": {"token": token, "uid": uid}}

    async def get_toys(self):
        return {"code": 200, "message": "OK", "data": {"toys": {}}}

    async def function(self, **kwargs):
        return {"code": 200, "message": "OK", "data": kwargs}

    async def stop(self, *, toy: str = ""):
        return {"code": 200, "message": "OK", "data": {"toy": toy}}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    app = create_app()
    app.state.lovense = FakeLovenseClient()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_lovense_status(client):
    resp = await client.get("/api/lovense/status")
    assert resp.status_code == 200
    assert resp.json()["configured"] is False


@pytest.mark.anyio
async def test_lovense_connect(client):
    resp = await client.post("/api/lovense/connect", json={"domain": "127-0-0-1.lovense.club"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["domain"] == "127-0-0-1.lovense.club"


@pytest.mark.anyio
async def test_lovense_function(client):
    resp = await client.post(
        "/api/lovense/function",
        json={"action": "Vibrate:5", "time_sec": 1},
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 200

