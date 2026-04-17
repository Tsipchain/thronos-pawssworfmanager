# M8 — First Real Blob Adapter (Gated)

M8 introduces the first real backend implementation on blob side only, behind existing execution gates.

## Real blob adapter added

- Added `LocalFileBlobStorage` as a filesystem-backed blob adapter.
- Adapter writes are only attempted when orchestrator `execution_enabled=true`.

## Gating behavior

- If `execution_enabled=false`, blob write path is skipped and a `blob_receipt` is returned with `status=skipped_gate`.
- If `execution_enabled=true`, orchestrator attempts blob write and returns `blob_receipt` with `status=written` or `failed`.
- Startup still fails closed when execution is requested and gates are unsatisfied.

## Provider config usage

- `local_fs` backend requires `BLOB_LOCAL_ROOT_PATH`.
- Missing root path causes startup/provider-boundary validation failure.

## Receipt consistency

- Added `BlobWriteReceipt` contract to keep blob-side side-effects explicit and structured.
- Existing persistence and attestation receipts remain unchanged.

## Non-goals / still disabled

- real blockchain submission (attestation remains fake/dry-run)
- auth/encryption runtime
- database/distributed coordination
