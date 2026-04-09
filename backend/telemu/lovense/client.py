"""Lovense local desktop LAN API client."""

from __future__ import annotations

import asyncio
import json
import ssl
from dataclasses import dataclass
from urllib import error, request


class LovenseClientError(RuntimeError):
    """Raised when communication with Lovense endpoints fails."""


@dataclass(slots=True)
class LovenseConnection:
    domain: str
    https_port: int = 30010


class LovenseClient:
    """Client for Lovense local desktop APIs."""

    def __init__(self, *, verify_tls: bool = False, timeout_sec: float = 5.0):
        self.verify_tls = verify_tls
        self.timeout_sec = timeout_sec
        self.connection: LovenseConnection | None = None
        self.default_domain = "127-0-0-1.lovense.club"
        self.default_https_port = 30010

    def configure(self, domain: str, https_port: int = 30010) -> None:
        self.connection = LovenseConnection(domain=domain.strip(), https_port=https_port)

    def status(self) -> dict:
        if self.connection is None:
            return {
                "configured": False,
                "domain": None,
                "https_port": None,
                "verify_tls": self.verify_tls,
            }
        return {
            "configured": True,
            "domain": self.connection.domain,
            "https_port": self.connection.https_port,
            "verify_tls": self.verify_tls,
        }

    async def detect_local(self) -> dict:
        result = await asyncio.to_thread(self._get_json, "https://api.lovense-api.com/api/lan/v2/app")
        apps = self._extract_apps(result)
        if apps:
            app = next((a for a in apps if a.get("online") is True), apps[0])
            domain = app.get("domain")
            https_port = app.get("httpsPort", self.default_https_port)
            if isinstance(domain, str) and domain.strip():
                port = self.default_https_port
                if isinstance(https_port, int):
                    port = https_port
                elif isinstance(https_port, str) and https_port.isdigit():
                    port = int(https_port)
                self.configure(domain.strip(), port)
                return {
                    "domain": self.connection.domain,
                    "https_port": self.connection.https_port,
                    "online": bool(app.get("online", True)),
                    "source": "discovery",
                }

        self.configure(self.default_domain, self.default_https_port)
        return {
            "domain": self.connection.domain,
            "https_port": self.connection.https_port,
            "online": True,
            "source": "fallback",
        }

    async def connect_local(self) -> dict:
        info = await self.detect_local()
        await self.get_toys()
        return info

    async def get_toys(self) -> dict:
        return await self._lan_command({"command": "GetToys", "apiVer": 1})

    async def function(
        self,
        *,
        action: str,
        time_sec: int = 0,
        toy: str = "",
        stop_previous: int = 1,
        loop_running_sec: int = 0,
        loop_pause_sec: int = 0,
    ) -> dict:
        payload = {
            "command": "Function",
            "action": action,
            "timeSec": time_sec,
            "toy": toy,
            "stopPrevious": stop_previous,
            "loopRunningSec": loop_running_sec,
            "loopPauseSec": loop_pause_sec,
            "apiVer": 1,
        }
        return await self._lan_command(payload)

    async def stop(self, *, toy: str = "") -> dict:
        return await self.function(action="Stop", toy=toy)

    async def _lan_command(self, payload: dict) -> dict:
        if self.connection is None:
            await self.detect_local()
        url = f"https://{self.connection.domain}:{self.connection.https_port}/command"
        try:
            return await asyncio.to_thread(self._post_json, url, payload)
        except LovenseClientError:
            await self.detect_local()
            retry_url = f"https://{self.connection.domain}:{self.connection.https_port}/command"
            return await asyncio.to_thread(self._post_json, retry_url, payload)

    def _post_json(self, url: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        context: ssl.SSLContext | None = None
        if url.startswith("https://") and not self.verify_tls:
            context = ssl._create_unverified_context()

        try:
            with request.urlopen(req, timeout=self.timeout_sec, context=context) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LovenseClientError(
                f"Lovense HTTP {exc.code} for {url}: {detail or exc.reason}"
            ) from exc
        except error.URLError as exc:
            raise LovenseClientError(f"Lovense connection error for {url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LovenseClientError(f"Lovense request timed out for {url}") from exc
        except json.JSONDecodeError as exc:
            raise LovenseClientError(f"Lovense returned invalid JSON for {url}") from exc

    def _get_json(self, url: str) -> dict:
        req = request.Request(url=url, method="GET")
        context: ssl.SSLContext | None = None
        if url.startswith("https://") and not self.verify_tls:
            context = ssl._create_unverified_context()
        try:
            with request.urlopen(req, timeout=self.timeout_sec, context=context) as resp:
                body = resp.read().decode("utf-8")
                return json.loads(body) if body else {}
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LovenseClientError(
                f"Lovense HTTP {exc.code} for {url}: {detail or exc.reason}"
            ) from exc
        except error.URLError as exc:
            raise LovenseClientError(f"Lovense connection error for {url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise LovenseClientError(f"Lovense request timed out for {url}") from exc
        except json.JSONDecodeError as exc:
            raise LovenseClientError(f"Lovense returned invalid JSON for {url}") from exc

    def _extract_apps(self, payload: dict) -> list[dict]:
        if not isinstance(payload, dict):
            return []
        data = payload.get("data")
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            return [data]
        return []

