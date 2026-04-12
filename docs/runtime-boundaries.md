# Runtime Boundaries (v0 Railway Service)

## What v0 service IS allowed to do

- Load and validate deployment configuration from environment.
- Expose health/readiness endpoints.
- Validate local volume path conventions and directory accessibility.
- Emit operational logs/audit-like service events (non-secret).
- Provide scaffolding boundary for future encrypted vault processing.

## What v0 service is NOT allowed to do

- No blob storage implementation.
- No encryption/decryption runtime.
- No authentication/authorization implementation.
- No blockchain write/attestation execution.
- No UI/browser extension/mobile behavior.
- No sharing/recovery/multi-device sync features.

## Storage categories and intended path conventions

All categories are planning-level only in this pass.

Base data root: `/data` (or `${SERVICE_DATA_ROOT}`)

1. **Encrypted blobs**
   - category intent: opaque encrypted payload files.
   - path convention: `${SERVICE_DATA_ROOT}/blobs/`.

2. **Version manifests**
   - category intent: deterministic manifest artifacts and hash-chain references.
   - path convention: `${SERVICE_DATA_ROOT}/manifests/`.

3. **Tombstones**
   - category intent: deletion markers/retention records.
   - path convention: `${SERVICE_DATA_ROOT}/tombstones/`.

4. **Exports/Imports**
   - category intent: controlled interchange artifacts (future only).
   - path convention: `${SERVICE_DATA_ROOT}/transfers/exports/` and `${SERVICE_DATA_ROOT}/transfers/imports/`.

5. **Logs/Audit artifacts**
   - category intent: non-secret operational traces and audit events.
   - path convention: `${SERVICE_DATA_ROOT}/logs/` and `${SERVICE_DATA_ROOT}/audit/`.

## Volume usage expectation for 50GB allocation

Recommended initial reservation policy (planning only):
- Encrypted blobs: up to 35GB
- Version manifests: up to 5GB
- Tombstones: up to 2GB
- Exports/Imports: up to 5GB
- Logs/Audit artifacts: up to 3GB

Total planned cap: 50GB.

## Readiness checks tied to boundaries

`/readyz` should fail if:
- required env vars are missing,
- `SERVICE_DATA_ROOT` is not writable,
- required category directories cannot be resolved/created by policy.

`/readyz` should NOT validate:
- auth token issuance,
- blob encryption correctness,
- blockchain transaction finality.
