# Phase 3.1 Controlled Side-Effects Guarantees

## Guarantees in current implementation

1. **Deterministic command transformation only** before side effects:
   - `command -> manifest -> canonical -> hash -> chain`.
2. **No unstable metadata injection** in command modules:
   - no timestamps,
   - no random IDs,
   - no runtime-generated nondeterministic fields.
3. **`canonical_bytes` response encoding is explicit**:
   - base64-encoded canonical bytes,
   - `canonical_bytes_encoding = "base64"`.
4. **Parent-hash trust boundary hardening**:
   - external `parent_hash` input is rejected,
   - previous chain linkage must come from structured `prev_chain_node`.
5. **Orchestrator idempotency behavior defined**:
   - repeated identical `manifest_hash` writes are treated as duplicates,
   - store disposition returned as `created` or `duplicate`.
6. **Side effects remain controlled and non-sensitive**:
   - fake attestation only,
   - in-memory manifest persistence only,
   - no auth/storage-encryption/blockchain/database runtime execution.

## Non-guarantees (still out of scope)

1. No real blob encryption runtime.
2. No real blob persistence backend.
3. No real blockchain submission/finality.
4. No auth or actor verification.
5. No distributed idempotency across multi-instance deployments.

## Contract notes

- `POST /v1/commands/execute` returns deterministic payload fields plus controlled side-effect metadata.
- Response contract remains enveloped by existing `success_contract`/`error_contract`.
