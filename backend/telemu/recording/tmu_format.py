"""TMU binary file format with integrity verification.

Layout:
    Header → Frame Index → Compressed Frames → Footer

Each compressed frame carries a CRC32 for fast per-chunk validation.
The footer stores a SHA-256 digest of the entire file (excluding the digest itself).
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import zstandard as zstd

# ── Constants ────────────────────────────────────────────────────────────────

MAGIC = b"TMU\x01"
FORMAT_VERSION: int = 1

# struct formats (little-endian)
HEADER_STRUCT = struct.Struct("<4sHd64s64sBI")
# magic(4) + version(2) + created_at(8) + track(64) + vehicle(64) + session_type(1) + metadata_len(4)

CHUNK_HEADER_STRUCT = struct.Struct("<II")
# compressed_size(4) + crc32(4)

FOOTER_STRUCT = struct.Struct("<QQ32s")
# frame_count(8) + index_offset(8) + sha256(32)


# ── Data classes ─────────────────────────────────────────────────────────────


@dataclass
class TMUHeader:
    version: int = FORMAT_VERSION
    created_at: float = 0.0
    track_name: str = ""
    vehicle_name: str = ""
    session_type: int = 0
    metadata: bytes = b"{}"


@dataclass
class TMUFooter:
    frame_count: int = 0
    index_offset: int = 0
    sha256: bytes = b"\x00" * 32


@dataclass
class ChunkInfo:
    offset: int = 0
    compressed_size: int = 0
    crc32: int = 0


@dataclass
class VerifyResult:
    """Result of a verification pass."""

    ok: bool = True
    sha256_ok: bool = True
    chunk_errors: list[int] = field(default_factory=list)
    frame_count: int = 0
    message: str = ""


# ── Writer ───────────────────────────────────────────────────────────────────


class TMUWriter:
    """Write .tmu files with per-chunk CRC32 and file-level SHA-256."""

    def __init__(self, path: Path | str, header: TMUHeader) -> None:
        self._path = Path(path)
        self._header = header
        self._cctx = zstd.ZstdCompressor()
        self._frame_offsets: list[int] = []
        self._fp = open(self._path, "wb")  # noqa: SIM115
        self._write_header()

    # -- public API --

    def write_frame(self, raw_frame: bytes) -> None:
        """Compress *raw_frame* and append with CRC32."""
        compressed = self._cctx.compress(raw_frame)
        crc = zlib.crc32(compressed) & 0xFFFFFFFF
        self._frame_offsets.append(self._fp.tell())
        self._fp.write(CHUNK_HEADER_STRUCT.pack(len(compressed), crc))
        self._fp.write(compressed)

    def close(self) -> None:
        """Write frame index, footer with SHA-256, and close the file."""
        index_offset = self._fp.tell()

        # Frame index: array of uint64 offsets
        for off in self._frame_offsets:
            self._fp.write(struct.pack("<Q", off))

        # Write placeholder footer (sha256 filled after hashing)
        footer_offset = self._fp.tell()
        frame_count = len(self._frame_offsets)
        placeholder_sha = b"\x00" * 32
        self._fp.write(FOOTER_STRUCT.pack(frame_count, index_offset, placeholder_sha))

        # Compute SHA-256 of everything before the sha256 field
        self._fp.flush()
        sha256_offset = footer_offset + FOOTER_STRUCT.size - 32  # where sha256 bytes start
        sha = _sha256_file(self._path, end=sha256_offset)

        # Patch the sha256 field
        self._fp.seek(sha256_offset)
        self._fp.write(sha)
        self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- internal --

    def _write_header(self) -> None:
        h = self._header
        track = h.track_name.encode("utf-8")[:64].ljust(64, b"\x00")
        vehicle = h.vehicle_name.encode("utf-8")[:64].ljust(64, b"\x00")
        meta = h.metadata if isinstance(h.metadata, bytes) else h.metadata.encode("utf-8")
        self._fp.write(
            HEADER_STRUCT.pack(
                MAGIC,
                h.version,
                h.created_at,
                track,
                vehicle,
                h.session_type,
                len(meta),
            )
        )
        self._fp.write(meta)


# ── Reader ───────────────────────────────────────────────────────────────────


class TMUReader:
    """Read .tmu files with optional integrity verification."""

    def __init__(self, path: Path | str, *, verify: bool = True) -> None:
        self._path = Path(path)
        self._dctx = zstd.ZstdDecompressor()
        self._fp = open(self._path, "rb")  # noqa: SIM115
        self.header = self._read_header()
        self.footer = self._read_footer()
        self._frame_offsets = self._read_index()

        if verify:
            result = verify_file(self._path)
            if not result.ok:
                raise TMUCorruptionError(result.message)

    @property
    def frame_count(self) -> int:
        return self.footer.frame_count

    def read_frame(self, index: int) -> bytes:
        """Decompress and return frame *index* (0-based)."""
        if index < 0 or index >= self.footer.frame_count:
            raise IndexError(f"Frame index {index} out of range [0, {self.footer.frame_count})")
        self._fp.seek(self._frame_offsets[index])
        comp_size, stored_crc = CHUNK_HEADER_STRUCT.unpack(
            self._fp.read(CHUNK_HEADER_STRUCT.size)
        )
        compressed = self._fp.read(comp_size)
        actual_crc = zlib.crc32(compressed) & 0xFFFFFFFF
        if actual_crc != stored_crc:
            raise TMUCorruptionError(
                f"CRC32 mismatch on frame {index}: "
                f"expected {stored_crc:#010x}, got {actual_crc:#010x}"
            )
        return self._dctx.decompress(compressed)

    def read_all_frames(self, *, skip_corrupted: bool = False) -> list[bytes]:
        """Read all frames, optionally skipping corrupted chunks."""
        frames: list[bytes] = []
        for i in range(self.footer.frame_count):
            try:
                frames.append(self.read_frame(i))
            except TMUCorruptionError:
                if not skip_corrupted:
                    raise
        return frames

    def close(self) -> None:
        self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    # -- internal --

    def _read_header(self) -> TMUHeader:
        self._fp.seek(0)
        data = self._fp.read(HEADER_STRUCT.size)
        magic, version, created_at, track_raw, vehicle_raw, session_type, meta_len = (
            HEADER_STRUCT.unpack(data)
        )
        if magic != MAGIC:
            raise TMUCorruptionError(f"Bad magic: {magic!r}")
        metadata = self._fp.read(meta_len)
        return TMUHeader(
            version=version,
            created_at=created_at,
            track_name=track_raw.rstrip(b"\x00").decode("utf-8", errors="replace"),
            vehicle_name=vehicle_raw.rstrip(b"\x00").decode("utf-8", errors="replace"),
            session_type=session_type,
            metadata=metadata,
        )

    def _read_footer(self) -> TMUFooter:
        self._fp.seek(-FOOTER_STRUCT.size, 2)
        data = self._fp.read(FOOTER_STRUCT.size)
        frame_count, index_offset, sha256_digest = FOOTER_STRUCT.unpack(data)
        return TMUFooter(
            frame_count=frame_count,
            index_offset=index_offset,
            sha256=sha256_digest,
        )

    def _read_index(self) -> list[int]:
        self._fp.seek(self.footer.index_offset)
        offsets: list[int] = []
        for _ in range(self.footer.frame_count):
            (off,) = struct.unpack("<Q", self._fp.read(8))
            offsets.append(off)
        return offsets


# ── Verification ─────────────────────────────────────────────────────────────


def verify_file(path: Path | str) -> VerifyResult:
    """Verify integrity of a .tmu file.

    Checks:
    1. SHA-256 of the whole file (excluding the stored digest bytes) vs footer.
    2. CRC32 of each compressed chunk.
    """
    path = Path(path)
    result = VerifyResult()

    with open(path, "rb") as fp:
        # -- read header to get metadata length --
        hdr_data = fp.read(HEADER_STRUCT.size)
        if len(hdr_data) < HEADER_STRUCT.size:
            return VerifyResult(ok=False, message="File too small for header")
        magic = hdr_data[:4]
        if magic != MAGIC:
            return VerifyResult(ok=False, message=f"Bad magic: {magic!r}")
        _magic, _ver, _ts, _track, _veh, _sess, meta_len = HEADER_STRUCT.unpack(hdr_data)
        fp.read(meta_len)  # skip metadata

        # -- read footer --
        fp.seek(-FOOTER_STRUCT.size, 2)
        footer_data = fp.read(FOOTER_STRUCT.size)
        frame_count, index_offset, stored_sha = FOOTER_STRUCT.unpack(footer_data)
        result.frame_count = frame_count

        # -- SHA-256 check --
        file_size = path.stat().st_size
        sha256_field_offset = file_size - 32  # last 32 bytes of file are the digest
        computed_sha = _sha256_file(path, end=sha256_field_offset)
        if computed_sha != stored_sha:
            result.sha256_ok = False
            result.ok = False

        # -- read frame index --
        fp.seek(index_offset)
        offsets: list[int] = []
        for _ in range(frame_count):
            (off,) = struct.unpack("<Q", fp.read(8))
            offsets.append(off)

        # -- per-chunk CRC32 --
        for i, off in enumerate(offsets):
            fp.seek(off)
            chunk_hdr = fp.read(CHUNK_HEADER_STRUCT.size)
            if len(chunk_hdr) < CHUNK_HEADER_STRUCT.size:
                result.chunk_errors.append(i)
                result.ok = False
                continue
            comp_size, stored_crc = CHUNK_HEADER_STRUCT.unpack(chunk_hdr)
            compressed = fp.read(comp_size)
            if len(compressed) < comp_size:
                result.chunk_errors.append(i)
                result.ok = False
                continue
            actual_crc = zlib.crc32(compressed) & 0xFFFFFFFF
            if actual_crc != stored_crc:
                result.chunk_errors.append(i)
                result.ok = False

    if result.ok:
        result.message = f"OK — {result.frame_count} frames verified"
    else:
        parts: list[str] = []
        if not result.sha256_ok:
            parts.append("SHA-256 mismatch")
        if result.chunk_errors:
            parts.append(f"CRC32 errors in frames: {result.chunk_errors}")
        result.message = "; ".join(parts)

    return result


def repair_file(
    src: Path | str, dst: Path | str, *, header_override: TMUHeader | None = None
) -> tuple[int, int]:
    """Copy valid frames from *src* to *dst*, skipping corrupted chunks.

    Returns ``(recovered, skipped)`` frame counts.
    """
    src = Path(src)
    dst = Path(dst)

    # Open source with verification disabled (we handle errors ourselves)
    reader = TMUReader(src, verify=False)
    header = header_override or reader.header
    recovered = 0
    skipped = 0

    with TMUWriter(dst, header) as writer:
        for i in range(reader.frame_count):
            try:
                frame = reader.read_frame(i)
                writer.write_frame(frame)
                recovered += 1
            except (TMUCorruptionError, zstd.ZstdError):
                skipped += 1

    reader.close()
    return recovered, skipped


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sha256_file(path: Path | str, *, end: int | None = None) -> bytes:
    """Compute SHA-256 of *path* up to byte offset *end*."""
    h = hashlib.sha256()
    remaining = end
    with open(path, "rb") as fp:
        while True:
            chunk_size = 65536
            if remaining is not None:
                chunk_size = min(chunk_size, remaining)
                if chunk_size <= 0:
                    break
            data = fp.read(chunk_size)
            if not data:
                break
            h.update(data)
            if remaining is not None:
                remaining -= len(data)
    return h.digest()


class TMUCorruptionError(Exception):
    """Raised when a .tmu file fails integrity checks."""
