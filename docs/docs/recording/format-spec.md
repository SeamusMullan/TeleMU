# .tmu Binary File Format Specification

!!! info "Format Version 1"
    This document specifies version **1** of the TeleMU binary recording format.
    The magic bytes `TMU\x01` distinguish file data from the streaming protocol
    (which uses `TMU\x02`).

## Overview

The `.tmu` format is a binary file format for recording telemetry sessions from
Le Mans Ultimate. It is designed for:

- **Sequential writes** — frames are appended during recording
- **Streaming reads** — header and channel definitions can be read once, then
  frames consumed one at a time
- **Random access** — a frame index in the footer enables seeking by timestamp
- **Forward compatibility** — a version field in the header allows future
  extensions

All multi-byte integers and floats are stored in **little-endian** byte order.
There is **no padding or alignment** between fields; values are packed
contiguously.

## File Layout

```
┌──────────────────────────────────────┐
│  Header (fixed 183 bytes)            │
├──────────────────────────────────────┤
│  Metadata JSON (variable length)     │
├──────────────────────────────────────┤
│  Channel Definition Table            │
│    (channel_count × 51 bytes)        │
├──────────────────────────────────────┤
│  Frame Data                          │
│    frame 0: timestamp + values       │
│    frame 1: timestamp + values       │
│    …                                 │
│    frame N-1: timestamp + values     │
├──────────────────────────────────────┤
│  Frame Index                         │
│    offset[0] … offset[N-1]           │
│    (N × 8 bytes, uint64 each)        │
├──────────────────────────────────────┤
│  Footer (fixed 20 bytes)             │
└──────────────────────────────────────┘
```

## Header (183 bytes, fixed)

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 4 | bytes | `magic` | `b"TMU\x01"` — identifies the file as `.tmu` v1 |
| 4 | 2 | uint16 | `version` | Format version (currently `1`) |
| 6 | 8 | float64 | `created_at` | Unix timestamp (seconds since epoch) |
| 14 | 64 | char[64] | `track_name` | UTF-8, null-padded |
| 78 | 64 | char[64] | `vehicle_name` | UTF-8, null-padded |
| 142 | 32 | char[32] | `driver_name` | UTF-8, null-padded |
| 174 | 1 | uint8 | `session_type` | LMU session type (`mSession` value) |
| 175 | 2 | uint16 | `sample_rate_hz` | Nominal capture rate (e.g. `60`) |
| 177 | 2 | uint16 | `channel_count` | Number of channel definitions |
| 179 | 4 | uint32 | `metadata_len` | Byte length of the JSON metadata block |

**struct format** (Python): `<4sHd64s64s32sBHHI`

Immediately after the 183-byte fixed header, `metadata_len` bytes of UTF-8
JSON follow. This block holds arbitrary session metadata (weather, setup,
notes, etc.). A minimal valid metadata block is `{}` (2 bytes).

## Channel Definition Table

Starts at offset `183 + metadata_len`. Contains `channel_count` entries of 51
bytes each.

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 32 | char[32] | `name` | Channel name, UTF-8, null-padded |
| 32 | 1 | uint8 | `type` | Data type tag (see table below) |
| 33 | 16 | char[16] | `unit` | Unit string, UTF-8, null-padded |
| 49 | 2 | uint16 | `byte_offset` | Byte offset within the frame payload |

**struct format** (Python): `<32sB16sH`

### Channel Type Tags

| Value | Name | Size | struct char | Description |
|-------|------|------|-------------|-------------|
| `0` | FLOAT64 | 8 | `d` | 64-bit IEEE 754 float |
| `1` | FLOAT32 | 4 | `f` | 32-bit IEEE 754 float |
| `2` | INT32 | 4 | `i` | 32-bit signed integer |
| `3` | UINT16 | 2 | `H` | 16-bit unsigned integer |
| `4` | BOOL | 1 | `?` | Boolean (0 or 1) |

The `byte_offset` field gives each channel's position within the **frame
payload** (the region after the 8-byte timestamp). Offsets are assigned
sequentially with no padding; the first channel is at offset 0.

## Frame Data

Each frame has a fixed size determined by the channel definitions:

```
frame_size = 8 (timestamp) + sum(channel[i].type.size for all channels)
```

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 8 | float64 | `timestamp` | `mElapsedTime` from LMU telemetry |
| 8 | varies | varies | channel values | Packed in channel-definition order |

All frames in a file have the same size. The frame count can be recovered from
the footer.

## Frame Index

Located at the byte offset stored in the footer's `index_offset` field.
Contains one `uint64` (8-byte little-endian) per frame, giving the absolute
file offset of each frame. This enables O(1) seeking to any frame.

## Footer (20 bytes, fixed)

Written after all frames and the frame index.

| Offset | Size | Type | Field | Description |
|--------|------|------|-------|-------------|
| 0 | 8 | uint64 | `frame_count` | Total number of frames |
| 8 | 8 | uint64 | `index_offset` | Absolute file offset of the frame index |
| 16 | 4 | uint32 | `checksum` | CRC-32 of all bytes before the footer |

**struct format** (Python): `<QQI`

The footer is always the last 20 bytes of the file.

## Reference Python Definitions

The reference implementation lives in
[`backend/telemu/recording/tmu_format.py`](../../backend/telemu/recording/tmu_format.py).

### Key constants

```python
MAGIC = b"TMU\x01"
FORMAT_VERSION = 1

HEADER_FMT      = "<4sHd64s64s32sBHHI"  # 183 bytes
CHANNEL_DEF_FMT = "<32sB16sH"           # 51 bytes
FRAME_HEADER_FMT = "<d"                 # 8 bytes (timestamp)
FOOTER_FMT      = "<QQI"               # 20 bytes
```

### Struct dataclasses

```python
@dataclass
class TMUHeader:
    track_name: str
    vehicle_name: str
    driver_name: str
    session_type: int = 0
    sample_rate_hz: int = 60
    created_at: float = field(default_factory=time.time)
    metadata_json: bytes = b"{}"
    channel_count: int = 0
    version: int = FORMAT_VERSION

@dataclass
class ChannelDef:
    name: str              # e.g. "speed"
    channel_type: ChannelType   # e.g. ChannelType.FLOAT64
    unit: str              # e.g. "km/h"
    byte_offset: int       # offset within frame payload

@dataclass
class TMUFooter:
    frame_count: int
    index_offset: int
    checksum: int          # CRC-32
```

## Example: Minimal Valid File

A minimal `.tmu` file with three channels (`speed`, `rpm`, `gear`) and two
frames. Created at `2025-01-15T12:00:00Z` (Unix ts `1736942400.0`), track
"Monza", vehicle "Porsche 963", driver "Player".

**Channels:**

| # | Name | Type | Unit | Offset |
|---|------|------|------|--------|
| 0 | speed | FLOAT64 | km/h | 0 |
| 1 | rpm | FLOAT64 | rpm | 8 |
| 2 | gear | INT32 | (none) | 16 |

Frame payload size: `8 + 8 + 4 = 20 bytes`; total frame size: `8 + 20 = 28 bytes`.

**Frame values:**

| Frame | Timestamp | speed | rpm | gear |
|-------|-----------|-------|-----|------|
| 0 | 0.000 | 0.0 | 800.0 | 0 |
| 1 | 0.016 | 42.5 | 3500.0 | 1 |

**File size:** 430 bytes

### Hex Dump

```
         ┌─ Header (183 bytes) ────────────────────────────────────────
00000000  54 4d 55 01 01 00 00 00  00 d0 e8 e1 d9 41 4d 6f  |TMU..........AMo|
00000010  6e 7a 61 00 00 00 00 00  00 00 00 00 00 00 00 00  |nza.............|
00000020  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000030  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000040  00 00 00 00 00 00 00 00  00 00 00 00 00 00 50 6f  |..............Po|
00000050  72 73 63 68 65 20 39 36  33 00 00 00 00 00 00 00  |rsche 963.......|
00000060  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000070  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000080  00 00 00 00 00 00 00 00  00 00 00 00 00 00 50 6c  |..............Pl|
00000090  61 79 65 72 00 00 00 00  00 00 00 00 00 00 00 00  |ayer............|
000000a0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 3c  |...............<|
         ├─ Metadata JSON (2 bytes: "{}") ─────────────────────────────
000000b0  00 03 00 02 00 00 00 7b  7d                       |.......{}       |
         ├─ Channel Definition Table (3 × 51 = 153 bytes) ────────────
                                      73 70 65 65 64 00 00  |         speed..|
000000c0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
000000d0  00 00 00 00 00 00 00 00  00 00 6b 6d 2f 68 00 00  |..........km/h..|
000000e0  00 00 00 00 00 00 00 00  00 00 00 00              |............    |
                                               72 70 6d 00  |            rpm.|
000000f0  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000100  00 00 00 00 00 00 00 00  00 00 00 00 00 72 70 6d  |.............rpm|
00000110  00 00 00 00 00 00 00 00  00 00 00 00 00 08 00     |...............  |
                                                        67  |               g|
00000120  65 61 72 00 00 00 00 00  00 00 00 00 00 00 00 00  |ear.............|
00000130  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 02  |................|
00000140  00 00 00 00 00 00 00 00  00 00 00 00 00 00 00 00  |................|
00000150  10 00                                             |..              |
         ├─ Frame 0 (28 bytes): ts=0.0, speed=0.0, rpm=800.0, gear=0 ─
               00 00 00 00 00 00  00 00 00 00 00 00 00 00  |  ..............|
00000160  00 00 00 00 00 00 00 00  89 40 00 00 00 00        |.........@....  |
         ├─ Frame 1 (28 bytes): ts=0.016, speed=42.5, rpm=3500.0, gear=1
                                                     fc a9  |              ..|
00000170  f1 d2 4d 62 90 3f 00 00  00 00 00 40 45 40 00 00  |..Mb.?.....@E@..|
00000180  00 00 00 58 ab 40 01 00  00 00                    |...X.@....      |
         ├─ Frame Index (2 × 8 = 16 bytes) ────────────────────────────
                                        52 01 00 00 00 00   |          R.....|
00000190  00 00 6e 01 00 00 00 00  00 00                    |..n.......      |
         ├─ Footer (20 bytes) ─────────────────────────────────────────
                                        02 00 00 00 00 00   |          ......|
000001a0  00 00 8a 01 00 00 00 00  00 00 f7 9d 3e 2c        |............>,  |
```

### Key Byte Annotations

| Offset | Bytes | Meaning |
|--------|-------|---------|
| `0x00` | `54 4d 55 01` | Magic: `TMU\x01` |
| `0x04` | `01 00` | Version: `1` (uint16 LE) |
| `0x06` | `00 00 00 d0 e8 e1 d9 41` | Created at: `1736942400.0` (float64 LE) |
| `0x0e` | `4d 6f 6e 7a 61 00…` | Track: `"Monza"` (64 bytes, null-padded) |
| `0x4e` | `50 6f 72 73 63 68 65…` | Vehicle: `"Porsche 963"` (64 bytes) |
| `0x8e` | `50 6c 61 79 65 72 00…` | Driver: `"Player"` (32 bytes) |
| `0xae` | `00` | Session type: `0` |
| `0xaf` | `3c 00` | Sample rate: `60` Hz (uint16 LE) |
| `0xb1` | `03 00` | Channel count: `3` (uint16 LE) |
| `0xb3` | `02 00 00 00` | Metadata length: `2` (uint32 LE) |
| `0xb7` | `7b 7d` | Metadata JSON: `"{}"` |
| `0xb9` | Channel def for `speed` | 51 bytes |
| `0xec` | Channel def for `rpm` | 51 bytes |
| `0x11f` | Channel def for `gear` | 51 bytes |
| `0x152` | Frame 0 | 28 bytes |
| `0x16e` | Frame 1 | 28 bytes |
| `0x18a` | Frame index | 2 × uint64 offsets |
| `0x19a` | Footer | `frame_count=2`, `index_offset=0x18a`, CRC-32 |

## Reading Algorithm

1. Read 183 bytes → parse the fixed header; validate magic bytes.
2. Read `metadata_len` bytes → decode as UTF-8 JSON.
3. Read `channel_count × 51` bytes → parse channel definitions.
4. Seek to end − 20 → read footer → get `frame_count` and `index_offset`.
5. Optionally verify CRC-32 over bytes `[0, file_size − 20)`.
6. To stream: read frames sequentially from current position.
7. To seek: read the frame index at `index_offset`, pick the desired offset,
   seek there, and read one frame.

## Writing Algorithm

1. Write the fixed header + metadata JSON.
2. Write the channel definition table.
3. For each telemetry sample, pack and append one frame.
4. After the last frame, write the frame index (one uint64 per frame).
5. Compute CRC-32 over everything written so far.
6. Write the footer.

## Design Rationale

| Decision | Reason |
|----------|--------|
| Little-endian | Matches x86/ARM hosts and LMU shared memory layout |
| No alignment padding | Simpler parsing; file size is predictable |
| Fixed-size string fields | Enables O(1) header parsing without length prefixes |
| JSON metadata block | Extensible without format version bumps |
| Frame index at end | Allows sequential write during recording |
| CRC-32 in footer | Cheap integrity check; not cryptographic |
| Channel type tags | Supports mixed-type telemetry (floats, ints, bools) |
| Separate from streaming | File format (`\x01`) vs. wire protocol (`\x02`) |

## Versioning

The `version` field in the header enables forward compatibility. Readers
**must** reject files whose version is higher than what they support. When
adding new fields to the header, increment the version and append new fields
after the existing ones (never reorder).
