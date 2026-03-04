# Lovense Integration

TeleMU includes backend-only Lovense support through a dedicated module and API routes.

## What Was Added

- `pylove` dependency in `backend/pyproject.toml` (managed with `uv`).
- `telemu/lovense` package for Lovense API logic.
- `/api/lovense/*` endpoints for integration control.
- backend tests for Lovense API endpoints.

## Configuration

Environment variables:

- `TELEMU_LOVENSE_DOMAIN` (optional): preconfigure LAN domain/host.
- `TELEMU_LOVENSE_HTTPS_PORT` (default: `30010`)
- `TELEMU_LOVENSE_VERIFY_TLS` (default: `false`)
- `TELEMU_LOVENSE_TIMEOUT_SEC` (default: `5.0`)

## API Endpoints

All endpoints are served from the backend (`/api` prefix):

- `GET /api/lovense/status`
  - Returns configured connection status.
- `POST /api/lovense/connect`
  - Sets connection target (`domain`, optional `https_port`).
- `POST /api/lovense/resolve-lan`
  - Resolves user LAN details via Lovense developer API (`token`, `uid`).
- `POST /api/lovense/get-toys`
  - Requests toy/device list from configured Lovense LAN endpoint.
- `POST /api/lovense/function`
  - Sends Function commands (`action`, `time_sec`, optional toy/loop params).
- `POST /api/lovense/stop`
  - Sends a stop command (optional `toy` query param).

## Quick Test Flow

1. Start backend:

```powershell
cd backend
uv run telemu
```

2. Resolve LAN endpoint:

```powershell
curl -X POST http://127.0.0.1:8000/api/lovense/resolve-lan `
  -H "Content-Type: application/json" `
  -d "{\"token\":\"YOUR_TOKEN\",\"uid\":\"YOUR_UID\"}"
```

3. Configure backend connection:

```powershell
curl -X POST http://127.0.0.1:8000/api/lovense/connect `
  -H "Content-Type: application/json" `
  -d "{\"domain\":\"YOUR_DOMAIN\",\"https_port\":30010}"
```

4. Verify toys:

```powershell
curl -X POST http://127.0.0.1:8000/api/lovense/get-toys
```

5. Send command:

```powershell
curl -X POST http://127.0.0.1:8000/api/lovense/function `
  -H "Content-Type: application/json" `
  -d "{\"action\":\"Vibrate:5\",\"time_sec\":2}"
```

## Validation

From `backend/`:

```powershell
uv run pytest
```

This includes `tests/test_lovense_api.py`.

