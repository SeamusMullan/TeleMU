""".tmu file format — binary telemetry recording format.

Format layout:
    4 bytes  : magic  b"TMU\\x01"
    4 bytes  : header length (uint32 little-endian)
    N bytes  : JSON header (session metadata)
    remainder: zstd-compressed payload of newline-delimited JSON frames

Each frame line:
    {"ts": <float>, "channels": {<name>: <float>, ...}}

Lap-marker frames additionally carry:
    {"ts": ..., "channels": {...}, "lap_marker": {
        "lap": <int>, "last_time": <str>, "best_time": <str>,
        "sectors": [<str>, ...]
    }}
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator

import zstandard as zstd

MAGIC = b"TMU\x01"
HEADER_LEN_FMT = "<I"  # uint32 LE


@dataclass
class TmuHeader:
    """Session metadata stored at the start of a .tmu file."""

    track: str = ""
    session_type: str = ""
    driver: str = ""
    vehicle: str = ""
    date: str = ""
    channels: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "track": self.track,
            "session_type": self.session_type,
            "driver": self.driver,
            "vehicle": self.vehicle,
            "date": self.date,
            "channels": self.channels,
        }
        d.update(self.extra)
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> TmuHeader:
        known = {"track", "session_type", "driver", "vehicle", "date", "channels"}
        extra = {k: v for k, v in d.items() if k not in known}
        return cls(
            track=d.get("track", ""),
            session_type=d.get("session_type", ""),
            driver=d.get("driver", ""),
            vehicle=d.get("vehicle", ""),
            date=d.get("date", ""),
            channels=d.get("channels", []),
            extra=extra,
        )


@dataclass
class TmuFrame:
    """One telemetry sample."""

    ts: float
    channels: dict[str, float]
    lap_marker: dict[str, Any] | None = None


def read_tmu(path: Path | str) -> tuple[TmuHeader, list[TmuFrame]]:
    """Read a .tmu file and return (header, frames)."""
    header, frames = None, []
    for item in iter_tmu(path):
        if isinstance(item, TmuHeader):
            header = item
        else:
            frames.append(item)
    if header is None:
        header = TmuHeader()
    return header, frames


def iter_tmu(path: Path | str) -> Generator[TmuHeader | TmuFrame, None, None]:
    """Lazily iterate over a .tmu file yielding the header then frames."""
    path = Path(path)
    with open(path, "rb") as fh:
        magic = fh.read(4)
        if magic != MAGIC:
            raise ValueError(f"Not a .tmu file (bad magic: {magic!r})")

        hdr_len_bytes = fh.read(4)
        if len(hdr_len_bytes) < 4:
            raise ValueError("Truncated .tmu header length")
        (hdr_len,) = struct.unpack(HEADER_LEN_FMT, hdr_len_bytes)

        hdr_json = fh.read(hdr_len)
        if len(hdr_json) < hdr_len:
            raise ValueError("Truncated .tmu header")

        header = TmuHeader.from_dict(json.loads(hdr_json))
        yield header

        compressed = fh.read()

    if not compressed:
        return

    dctx = zstd.ZstdDecompressor()
    payload = dctx.decompress(compressed)

    for line in payload.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        yield TmuFrame(
            ts=obj["ts"],
            channels=obj.get("channels", {}),
            lap_marker=obj.get("lap_marker"),
        )


def write_tmu(
    path: Path | str,
    header: TmuHeader,
    frames: list[TmuFrame],
    compression_level: int = 3,
) -> None:
    """Write a .tmu file."""
    path = Path(path)
    hdr_bytes = json.dumps(header.to_dict(), separators=(",", ":")).encode()

    lines: list[bytes] = []
    for f in frames:
        obj: dict[str, Any] = {"ts": f.ts, "channels": f.channels}
        if f.lap_marker:
            obj["lap_marker"] = f.lap_marker
        lines.append(json.dumps(obj, separators=(",", ":")).encode())
    payload = b"\n".join(lines)

    cctx = zstd.ZstdCompressor(level=compression_level)
    compressed = cctx.compress(payload)

    with open(path, "wb") as fh:
        fh.write(MAGIC)
        fh.write(struct.pack(HEADER_LEN_FMT, len(hdr_bytes)))
        fh.write(hdr_bytes)
        fh.write(compressed)
