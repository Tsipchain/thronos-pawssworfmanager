# M5 — Real Adapter Wiring (Dry-Run Mode)

This milestone introduces provider-shaped adapter wiring for future real backends while explicitly blocking real side effects.

## Adapter extensions

### Blob storage
- Added a provider-shaped blob adapter (`DryRunBlobStorageProvider`) that accepts real backend identifiers (`s3`, `gcs`, `azure_blob`) but never performs real writes.
- Added adapter capability reporting: backend, provider family, dry-run support, and execution-enabled flag.

### Attestation
- Added a provider-shaped chain adapter (`DryRunChainAttestationAdapter`) for `thronos_chain` backend.
- Adapter supports deterministic dry-run success and optional simulated failure paths (`TimeoutError`) for retry-path testing.
- Capability reporting mirrors blob adapter: backend, provider family, dry-run support, execution-enabled.

## Dry-run behavior definition

- Default execution mode is `dry_run`.
- `ADAPTER_EXECUTION_MODE=execute` is accepted only for current in-memory/fake-safe combinations.
- If real-like providers are selected (`s3`, `gcs`, `azure_blob`, `thronos_chain`) with `execute`, config resolution fails with `real_execution_mode_not_allowed`.
- Even if execute is forced into adapter constructors, provider-shaped adapters hard-stop with runtime errors:
  - `real_blob_write_disabled`
  - `real_attestation_submission_disabled`

## Capability reporting

Runtime capabilities now include:
- `blob_storage` backend
- `execution_mode`
- `dry_run_enabled`
- `blob_capabilities`
- `attestation_capabilities`

## Still blocked before real execution

- Real network client integration for object storage providers.
- Real chain RPC client and signing workflow.
- Secrets/key management for provider auth.
- Encryption runtime and auth runtime.
- Database-backed coordination and distributed idempotency.
