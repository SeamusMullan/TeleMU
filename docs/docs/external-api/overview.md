# External API Overview

TeleMU exposes backend REST endpoints under `/api` for integrations that should not be implemented in the frontend.

## Current Integrations

- **Lovense API**: backend module for device discovery and command execution.

## Design Rules

1. External integrations live in dedicated backend modules (for example `telemu/lovense`).
2. Public routes are mounted from `telemu/api/*` under `/api`.
3. Frontend changes are optional and not required for backend integration support.
4. Configuration is provided through `TELEMU_*` environment variables.

## Backend Layout

- `backend/telemu/lovense/client.py`: Lovense API client logic.
- `backend/telemu/lovense/models.py`: request/response models.
- `backend/telemu/api/lovense.py`: REST endpoints for integration operations.
- `backend/telemu/main.py`: app wiring and router registration.

