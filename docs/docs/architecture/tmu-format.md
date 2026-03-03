# TMU Binary File Format Specification

**Version:** 1.0  
**Status:** Draft  
**Endianness:** Little-endian throughout  
**Alignment:** All multi-byte fields are naturally aligned within their section

## Overview

The `.tmu` file format is a compact binary format for recording TeleMU telemetry sessions.
It is designed for **sequential writes** during recording and **streaming reads** during playback or analysis.

A `.tmu` file is laid out as four contiguous sections:

```
┌──────────────────────┐  offset 0
│     File Header      │  32 bytes (fixed)
├──────────────────────┤  offset 32
│  Session Metadata    │  variable (UTF-8 JSON)
├──────────────────────┤  offset 32 + metadata_length
│ Channel Definitions  │  channel_count × 48 bytes
├──────────────────────┤  offset 32 + metadata_length + channel_count × 48
│     Frame Data       │  frame_count × frame_size bytes
└──────────────────────┘
```

---

## 1. File Header (32 bytes)

| Offset | Size | Type     | Field             | Description |
|--------|------|----------|-------------------|-------------|
| 0      | 4    | `char[4]`  | `magic`           | Magic bytes: `TMU\x1A` (`0x54 0x4D 0x55 0x1A`) |
| 4      | 2    | `uint16` | `version`         | Format version (`major × 256 + minor`, e.g. `0x0100` = v1.0) |
| 6      | 2    | `uint16` | `flags`           | Bit flags (reserved, must be `0` in v1.0) |
| 8      | 2    | `uint16` | `channel_count`   | Number of telemetry channels |
| 10     | 2    | `uint16` | `sample_rate_hz`  | Nominal sample rate in Hz |
| 12     | 4    | `uint32` | `metadata_length` | Length of the session metadata JSON block in bytes |
| 16     | 8    | `uint64` | `frame_count`     | Total number of recorded frames (updated when the file is closed) |
| 24     | 8    | `uint8[8]` | `reserved`      | Reserved for future use (must be `0`) |

!!! note "Forward compatibility"
    Readers **must** ignore unknown flag bits and unknown fields in reserved
    space.  Writers **must** set reserved bytes to zero.

---

## 2. Session Metadata (variable length)

Starts at **offset 32**.  Length is `metadata_length` bytes from the header.

The block is a **UTF-8 encoded JSON object** with no trailing padding.  The
following keys are defined for v1.0.  Readers should ignore unrecognised keys.

```json
{
  "track": "Circuit de Spa-Francorchamps",
  "car": "Porsche 963 LMDh",
  "driver": "John Doe",
  "date": "2026-03-02T00:31:36Z",
  "session_type": "Practice",
  "notes": ""
}
```

| Key            | Type   | Required | Description |
|----------------|--------|----------|-------------|
| `track`        | string | yes      | Track / circuit name |
| `car`          | string | yes      | Vehicle name |
| `driver`       | string | yes      | Driver name |
| `date`         | string | yes      | ISO 8601 UTC timestamp of session start |
| `session_type` | string | no       | e.g. `"Practice"`, `"Qualifying"`, `"Race"` |
| `notes`        | string | no       | Free-form notes |

Additional keys may be added in future versions.

---

## 3. Channel Definitions (48 bytes each)

Starts at **offset `32 + metadata_length`**.  There are `channel_count` entries,
each exactly **48 bytes**.

| Offset | Size | Type       | Field      | Description |
|--------|------|------------|------------|-------------|
| 0      | 32   | `char[32]` | `name`     | Channel name, UTF-8, null-padded |
| 32     | 1    | `uint8`    | `dtype`    | Data type enum (see table below) |
| 33     | 8    | `char[8]`  | `unit`     | Unit label, UTF-8, null-padded |
| 41     | 7    | `uint8[7]` | `reserved` | Reserved (must be `0`) |

### Data type enum (`dtype`)

| Value | Name      | Size (bytes) | Description |
|-------|-----------|-------------|-------------|
| `0`   | `FLOAT64` | 8           | IEEE 754 double-precision float |
| `1`   | `FLOAT32` | 4           | IEEE 754 single-precision float |
| `2`   | `INT32`   | 4           | Signed 32-bit integer |
| `3`   | `INT16`   | 2           | Signed 16-bit integer |
| `4`   | `UINT8`   | 1           | Unsigned 8-bit integer |
| `5`   | `BOOL`    | 1           | Boolean (`0` = false, `1` = true) |

### Computing frame size

The **frame size** in bytes is:

```
frame_size = 8  (timestamp, FLOAT64)
           + sum(dtype_size(channel.dtype) for channel in channels)
```

Channel values appear in the frame **in the same order** as the channel
definition table.

---

## 4. Frame Data

Starts at **offset `32 + metadata_length + channel_count × 48`**.

Each frame has the following layout:

| Field       | Type      | Size    | Description |
|-------------|-----------|---------|-------------|
| `timestamp` | `float64` | 8 bytes | Elapsed session time in seconds |
| `values[0]` | per dtype | varies  | Value of channel 0 |
| `values[1]` | per dtype | varies  | Value of channel 1 |
| …           | …         | …       | … |
| `values[N-1]` | per dtype | varies | Value of channel N-1 |

Frames are written **sequentially** with no padding between them.  The total
number of frames is stored in the header field `frame_count` which is updated
when the recording session ends.

!!! tip "Streaming reads"
    Because the header, metadata, and channel table are written first, a reader
    can begin parsing frames as soon as it has read those sections — even while
    the file is still being written.  The reader simply consumes frames until
    EOF.

---

## 5. Reference Python Struct Definitions

A complete reference implementation is provided in
[`LMUPI/lmupi/tmu_format.py`](../../../LMUPI/lmupi/tmu_format.py).

The core data structures use Python's `struct` module:

```python
import struct, enum, json

# Magic bytes
TMU_MAGIC = b"TMU\x1a"

# Header: magic(4s) version(H) flags(H) channel_count(H)
#          sample_rate_hz(H) metadata_length(I) frame_count(Q) reserved(8s)
HEADER_FORMAT = "<4sHHHHIQ8s"
HEADER_SIZE   = struct.calcsize(HEADER_FORMAT)  # 32

# Channel definition: name(32s) dtype(B) unit(8s) reserved(7s)
CHANNEL_FORMAT = "<32sB8s7s"
CHANNEL_SIZE   = struct.calcsize(CHANNEL_FORMAT)  # 48

class ChannelDtype(enum.IntEnum):
    FLOAT64 = 0
    FLOAT32 = 1
    INT32   = 2
    INT16   = 3
    UINT8   = 4
    BOOL    = 5

DTYPE_STRUCT = {
    ChannelDtype.FLOAT64: "<d",
    ChannelDtype.FLOAT32: "<f",
    ChannelDtype.INT32:   "<i",
    ChannelDtype.INT16:   "<h",
    ChannelDtype.UINT8:   "<B",
    ChannelDtype.BOOL:    "<?",
}
```

---

## 6. Example: Minimal Valid File

A minimal `.tmu` file containing **one channel** (`Speed`, FLOAT64, `m/s`) and
**two frames** at 60 Hz.  Total size: **197 bytes**.

### Session metadata (JSON, 85 bytes)

```json
{"track":"TestTrack","car":"TestCar","driver":"Tester","date":"2026-01-01T00:00:00Z"}
```

### Hex dump

Generated by the reference implementation in
[`LMUPI/lmupi/tmu_format.py`](../../../LMUPI/lmupi/tmu_format.py):

```
Offset    Bytes                                              ASCII
--------  -----------------------------------------------    ----------------
          ---- file header (32 bytes) ----------------------
00000000  54 4D 55 1A 00 01 00 00 01 00 3C 00 55 00 00 00   TMU.......<.U...
00000010  02 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   ................

          ---- session metadata (JSON, 85 bytes) -----------
00000020  7B 22 74 72 61 63 6B 22 3A 22 54 65 73 74 54 72   {"track":"TestTr
00000030  61 63 6B 22 2C 22 63 61 72 22 3A 22 54 65 73 74   ack","car":"Test
00000040  43 61 72 22 2C 22 64 72 69 76 65 72 22 3A 22 54   Car","driver":"T
00000050  65 73 74 65 72 22 2C 22 64 61 74 65 22 3A 22 32   ester","date":"2
00000060  30 32 36 2D 30 31 2D 30 31 54 30 30 3A 30 30 3A   026-01-01T00:00:
00000070  30 30 5A 22 7D                                     00Z"}

          ---- channel definition (1 × 48 bytes) -----------
00000075  53 70 65 65 64 00 00 00 00 00 00 00 00 00 00 00   Speed...........
00000085  00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00   ................
00000095  00 00 00 00 00 6D 2F 73 00 00 00 00 00 00 00 00   .....m/s........
000000A1  00 00 00 00                                        ....

          ---- frame data (2 frames × 16 bytes each) -------
000000A5  00 00 00 00 00 00 00 00 00 00 00 00 00 00 59 40   ..............Y@
000000B5  44 44 44 44 44 44 F0 3F 00 00 00 00 00 80 50 40   DDDDDD.?......P@
```

### Breakdown

| Section          | Offset   | Content |
|------------------|----------|---------|
| Header           | `0x00`   | magic=`TMU\x1A`, version=`1.0`, flags=`0`, channels=`1`, rate=`60`, meta_len=`85`, frames=`2` |
| Metadata         | `0x20`   | `{"track":"TestTrack","car":"TestCar","driver":"Tester","date":"2026-01-01T00:00:00Z"}` |
| Channel 0        | `0x75`   | name=`Speed`, dtype=`FLOAT64(0)`, unit=`m/s` |
| Frame 0          | `0xA5`   | timestamp=`0.0`, Speed=`100.0` |
| Frame 1          | `0xB5`   | timestamp=`1.01666…` (1 + 1/60 s), Speed=`66.0` |

---

## 7. Design Rationale

| Decision | Rationale |
|----------|-----------|
| Little-endian | Matches x86/x64 platforms where LMU runs |
| Fixed-size header | Enables `mmap` and O(1) section lookup |
| JSON metadata | Flexible, human-readable, easy to extend |
| 48-byte channel records | Fixed size enables direct indexing; 32 chars is enough for LMU channel names |
| Frame count in header | Updated on close; readers can use EOF for streaming |
| `\x1A` in magic | Acts as a Ctrl-Z stop byte, preventing accidental text display on Windows |
