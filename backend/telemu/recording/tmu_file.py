"""Read and write .tmu file headers with embedded JSON metadata.

The .tmu binary format is documented in docs/docs/recording/overview.md.
This module implements only the header portion (metadata capture), not frame
recording or playback.

Header layout
─────────────
  magic         : 4 bytes   b"TMU\\x01"
  version       : uint16    format version (currently 1)
  created_at    : float64   Unix timestamp
  track_name    : char[64]  track name (UTF-8, null-padded)
  vehicle_name  : char[64]  vehicle name (UTF-8, null-padded)
  session_type  : uint8     raw mSession value
  metadata_len  : uint32    length of JSON metadata blob
  metadata      : bytes     UTF-8 JSON (SessionMetadata)
"""

from __future__ import annotations

import json
import struct
from pathlib import Path

from telemu.models import SessionMetadata
from telemu.recording.metadata import decode_session_type

# Binary constants
MAGIC = b"TMU\x01"
FORMAT_VERSION = 1

# struct format: magic(4s) version(H) created_at(d) track(64s) vehicle(64s) session(B) meta_len(I)
_HEADER_FMT = "<4sHd64s64sBI"
_HEADER_SIZE = struct.calcsize(_HEADER_FMT)  # fixed portion


def _encode_fixed_str(text: str, length: int) -> bytes:
    """Encode a string into a fixed-length null-padded byte field."""
    encoded = text.encode("utf-8", errors="replace")[:length]
    return encoded.ljust(length, b"\x00")


def _decode_fixed_str(data: bytes) -> str:
    """Decode a null-padded byte field into a string."""
    return data.split(b"\x00", 1)[0].decode("utf-8", errors="replace")


def write_header(
    path: Path | str,
    metadata: SessionMetadata,
    *,
    session_type_raw: int = 0,
) -> None:
    """Write a .tmu file header with embedded metadata JSON.

    Parameters
    ----------
    path : Path | str
        Output file path (will be created or overwritten).
    metadata : SessionMetadata
        Session metadata to embed.
    session_type_raw : int
        Raw ``mSession`` value from LMU shared memory.
    """
    import time

    meta_json = metadata.model_dump_json().encode("utf-8")

    header = struct.pack(
        _HEADER_FMT,
        MAGIC,
        FORMAT_VERSION,
        time.time(),
        _encode_fixed_str(metadata.track_name, 64),
        _encode_fixed_str(metadata.car_name, 64),
        session_type_raw,
        len(meta_json),
    )

    with open(path, "wb") as f:
        f.write(header)
        f.write(meta_json)


def read_header(path: Path | str) -> SessionMetadata:
    """Read the metadata JSON block from a .tmu file header.

    Parameters
    ----------
    path : Path | str
        Path to an existing .tmu file.

    Returns
    -------
    SessionMetadata
        Parsed metadata.

    Raises
    ------
    ValueError
        If the file has an invalid magic number or cannot be parsed.
    """
    with open(path, "rb") as f:
        fixed = f.read(_HEADER_SIZE)
        if len(fixed) < _HEADER_SIZE:
            raise ValueError("File too small to contain a valid .tmu header")

        magic, version, created_at, track_raw, vehicle_raw, session_raw, meta_len = (
            struct.unpack(_HEADER_FMT, fixed)
        )

        if magic != MAGIC:
            raise ValueError(f"Invalid magic number: {magic!r}")

        meta_bytes = f.read(meta_len)
        if len(meta_bytes) < meta_len:
            raise ValueError("Truncated metadata block")

    meta_dict = json.loads(meta_bytes.decode("utf-8"))
    return SessionMetadata(**meta_dict)


def update_metadata(
    path: Path | str,
    *,
    notes: str | None = None,
    session_description: str | None = None,
    setup_name: str | None = None,
) -> SessionMetadata:
    """Update user-editable metadata fields in a .tmu file.

    Reads the existing metadata, patches the requested fields, and rewrites
    the header (preserving the fixed-size portion except for metadata_len).

    Parameters
    ----------
    path : Path | str
        Path to the .tmu file.
    notes : str, optional
        New value for the notes field.
    session_description : str, optional
        New value for the session_description field.
    setup_name : str, optional
        New value for the setup_name field.

    Returns
    -------
    SessionMetadata
        Updated metadata.
    """
    path = Path(path)

    with open(path, "rb") as f:
        fixed = f.read(_HEADER_SIZE)
        magic, version, created_at, track_raw, vehicle_raw, session_raw, old_meta_len = (
            struct.unpack(_HEADER_FMT, fixed)
        )
        if magic != MAGIC:
            raise ValueError(f"Invalid magic number: {magic!r}")

        old_meta_bytes = f.read(old_meta_len)
        remaining = f.read()  # everything after the metadata block

    meta_dict = json.loads(old_meta_bytes.decode("utf-8"))
    metadata = SessionMetadata(**meta_dict)

    if notes is not None:
        metadata.notes = notes
    if session_description is not None:
        metadata.session_description = session_description
    if setup_name is not None:
        metadata.setup_name = setup_name

    new_meta_json = metadata.model_dump_json().encode("utf-8")

    new_header = struct.pack(
        _HEADER_FMT,
        MAGIC,
        version,
        created_at,
        track_raw,
        vehicle_raw,
        session_raw,
        len(new_meta_json),
    )

    with open(path, "wb") as f:
        f.write(new_header)
        f.write(new_meta_json)
        f.write(remaining)

    return metadata
