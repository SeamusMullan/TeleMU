"""Pydantic models for local Lovense desktop integration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LovenseFunctionRequest(BaseModel):
    action: str = Field(min_length=1, description="Lovense Function action payload")
    time_sec: int = Field(default=0, ge=0, le=3600)
    toy: str = Field(default="", description="Optional toy id")
    stop_previous: int = Field(default=1, ge=0, le=1)
    loop_running_sec: int = Field(default=0, ge=0, le=3600)
    loop_pause_sec: int = Field(default=0, ge=0, le=3600)


class LovenseConnectionStatus(BaseModel):
    configured: bool
    domain: str | None = None
    https_port: int | None = None
    verify_tls: bool


class LovenseLocalAppInfo(BaseModel):
    domain: str
    https_port: int
    online: bool = True
    source: str = "local"

