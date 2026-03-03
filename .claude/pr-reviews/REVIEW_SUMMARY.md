# TeleMU PR Review Summary — 2026-03-03

## Overview

| PR | Title | Issue | Verdict | Adds | Files | Key Finding |
|----|-------|-------|---------|------|-------|-------------|
| #61 | .tmu file format spec | #1 | **CHANGES NEEDED** | 508 | 16 (3 real + 13 pycache cleanup) | Solid format design. Needs: assert→RuntimeError, version check in reader, magic number constant, context manager |
| #62 | LZ4 compression | #3 | **CHANGES NEEDED** | 643 | 18 (4 real + 14 pycache cleanup) | Good chunk-based design w/ 18 tests. Needs: full struct capture is wasteful (~12MB/s raw), zstd context reuse, crash recovery path |
| #63 | Binary serializer | #2 | **CHANGES NEEDED** | 946 | 4 | 130-channel serializer w/ 20 tests. Needs: extractor=None safety, __init__.py export, version decode test, error messages in encode_frame |
| #64 | TelemetryRecorder | #4 | **CHANGES NEEDED** | 1482 | 23 (7 real + 14 pycache cleanup) | Full QThread recorder w/ ring buffer, 20 tests. Needs: per-frame lambda dict perf fix, chunk_indices mutation bug, duplicate utils extraction, fsync |
| #65 | Recording UI controls | #5 | **CLOSE** | 0 | 0 | Truly empty — no code at all |
| #66 | Streaming protocol spec | #16 | **CHANGES NEEDED** | 223 | 2 | Good spec doc w/ wire diagrams. Needs: byte order spec, fragment timeout policy, payload formats for all message types |
| #67 | Streaming server | #17 | **CHANGES NEEDED** | 1104 | 22 (7 real + 15 pycache cleanup) | Working server w/ select() loop, TCP+UDP, dashboard integration. Needs: pycache separation, race conditions on _available_channels and _bytes_sent, more tests |
| #68 | Streaming client | #18 | **CHANGES NEEDED** | 690 | 8 (3 real + 5 pycache) | Working client w/ jitter buffer, reconnect. Needs: pycache removal, backoff reset bug, thread-safety (push() from worker thread), UDP port binding model |

## Cross-PR Concerns

### 1. __pycache__ committed everywhere
PRs #61, #62, #64, #67, #68 all touch pycache files (mostly deletions/cleanup). This should be a single separate cleanup PR.

### 2. Duplicate code across PRs
- `_speed_from_local_vel` and `_K2C` duplicated between telemetry_reader.py and tmu_serializer.py (#63, #64)
- Header parsing duplicated vs protocol module (#67)

### 3. Thread safety pattern inconsistency
- PR #67 (server): uses QMutex for clients but bare booleans for _running
- PR #68 (client): calls dashboard.push() from worker thread (Qt violation)
- PR #64 (recorder): uses QMutex properly throughout

### 4. No integration tests across PRs
- None of these PRs test interaction with each other
- #64 (recorder) and #61/#62/#63 (format/compression/serializer) overlap significantly but were developed independently

### 5. PR #61 vs #64 format conflict
Both define .tmu format structures independently. If both merged, there would be two competing format implementations. These need reconciliation.

## Merge Order Recommendation

If changes are made:
1. First: Separate pycache cleanup PR
2. #66 (streaming protocol spec) — pure docs, no code conflicts
3. #61 (format spec) OR #64 (recorder) — NOT both without reconciliation
4. #63 (serializer) — depends on format being settled
5. #62 (compression) — depends on format being settled
6. #67 (streaming server) — depends on #66
7. #68 (streaming client) — depends on #66, #67
8. #65 — close, empty

## Per-PR Detailed Issues

### PR #61 — .tmu Format Spec
**Must fix:**
- Replace `assert self._fp is not None` with `RuntimeError` raises (2 locations)
- Add version check in TMUReader.open() — reject unknown major versions
- Replace magic number `self._fp.seek(16)` with named constant FRAME_COUNT_OFFSET
- Add length validation for channel reads in TMUReader.open()
- Handle metadata_length == 0 edge case

**Should fix:**
- Add round-trip test (write → read → verify)
- Add values length validation in write_frame()
- Check _header_written before allowing write_frame()
- Warn on channel name truncation (>32 bytes)

### PR #62 — LZ4 Compression
**Must fix:**
- Full struct capture via ctypes.string_at captures entire LMUObjectOut (~hundreds of KB per frame). Either document as intentional or scope to player vehicle only.

**Should fix:**
- ZstdCompressor recreated per chunk — store and reuse
- comp_size from index table never used in read_chunk() — redundant read
- No crash recovery for files missing index/footer
- zstandard as hard dependency for a fallback feature

### PR #63 — Binary Serializer
**Must fix:**
- ChannelDescriptor.extractor typed as Optional but encode_frame() calls it unconditionally — TypeError if None
- Re-export from sharedmem/__init__.py

**Should fix:**
- Test for unsupported format version in decode_header
- Test for empty channel list
- Test for duplicate channel names
- Better error messages in encode_frame (include channel name)

### PR #64 — TelemetryRecorder
**Must fix:**
- `_read_channel()` rebuilds dict of lambdas every frame — 2,820 objects/sec at 60Hz. Pre-build lookup table in __init__
- chunk_indices property returns shallow copy but recorder mutates through it — fragile
- Duplicate _speed_from_local_vel and _K2C from telemetry_reader.py

**Should fix:**
- No fsync on finalize — data may not reach disk
- stop_recording() timeout is silent on failure
- Ring buffer put() return value ignored — log drops
- No tests for state transitions (start/stop/pause/resume)

### PR #66 — Streaming Protocol Spec
**Must fix:**
- Define byte order (big-endian / little-endian) for all multi-byte fields
- Define fragment reassembly timeout/discard policy
- Define payload formats for SUBSCRIBE, HELLO, CONFIG_ACK, HEARTBEAT, HEARTBEAT_ACK, DISCONNECT
- Clarify UDP port assignment (fixed vs dynamic from CONFIG_ACK)

**Should fix:**
- Sequence number wrapping behavior
- Session ID in UDP packets for reconnection safety
- Max payload length for TCP control messages

### PR #67 — Streaming Server
**Must fix:**
- Separate pycache cleanup into own commit/PR
- Expand .gitignore beyond just __pycache__/
- Race condition on _available_channels (write outside lock)

**Should fix:**
- Tests for heartbeat timeout, channel subscription, GOODBYE
- Header parsing duplication vs protocol module
- threading.Event for _running instead of bare boolean
- Guard _bytes_sent with lock

### PR #68 — Streaming Client
**Must fix:**
- Remove committed .pyc files, update .gitignore
- Backoff never resets after successful connection — doubles indefinitely
- Thread-safety: dashboard.push() called from worker thread (Qt violation — must use signal)

**Should fix:**
- UDP port binding fragile (binds to server-specified port, breaks with NAT/multi-client)
- TCP receive loop relies on server closing connection (should use length-prefixed framing)
- Self-import in dashboard.py (from lmupi.dashboard import TelemetryChannel)
- No tests for StreamingClient lifecycle
