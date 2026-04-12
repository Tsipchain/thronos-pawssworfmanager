# Deployment Outline (Dedicated Railway Service, v0)

## Objective

Prepare an isolated Railway service boundary for `thronos-pawssworfmanager` without enabling full product runtime behavior.

## First service shape (v0)

Single dedicated service process responsible for:
- process startup and configuration validation,
- health/readiness signaling,
- local metadata/path boundary validation,
- future integration points for encrypted vault workflows (not implemented in v0).

## Railway allocation assumptions

- 1 dedicated Railway service for this repository.
- 1 attached persistent volume (target size: **50GB**).
- 1 metadata database connection string via managed env secret.

## Deployment topology (v0)

1. **Service container**
   - stateless application process.
   - receives all runtime config from environment variables.

2. **Persistent volume mount**
   - mounted at `/data` (configurable via `SERVICE_DATA_ROOT`).
   - used for local artifacts/log buffers/path validation only in this phase.

3. **External dependencies**
   - metadata DB endpoint configured but not fully exercised for business features.
   - optional object/blob backend configured but no implementation in this pass.
   - Thronos RPC/config values present but no on-chain writes in this pass.

## Health/readiness route guidance (documented only)

- `GET /healthz`
  - returns process liveness only.
  - should not depend on external systems.

- `GET /readyz`
  - returns readiness for traffic.
  - should validate: required env vars present, volume root exists/writable, configuration parse succeeds.
  - should NOT perform blockchain writes, auth checks, or encryption operations.

## Rollout expectations

- v0 deployment success criteria:
  - container starts with isolated env set,
  - health and readiness routes respond,
  - volume path conventions resolvable,
  - no forbidden runtime capabilities enabled.

## Explicitly not in scope for this pass

- blob storage runtime implementation,
- encryption runtime implementation,
- auth runtime implementation,
- blockchain write implementation,
- any UI or client app surface.


## Railway build/start commands

- Build command: `pip install -r requirements.txt`
- Start command: `PYTHONPATH=src gunicorn -w 1 -b 0.0.0.0:${PORT:-8080} thronos_pawssworfmanager.http_service:wsgi_app`

(Equivalent start declaration exists in `Procfile`.)
