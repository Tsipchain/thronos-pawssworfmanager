# M11 — Thronos finality polling and reconciliation

M11 introduces the first Thronos-specific polling/reconciliation contract on top of submission receipts.

## Polling contract

Adapters expose `poll_attestation(submission_id, tx_hash, reconciliation_id)` and return:

- `confirmation_status`: `confirmed | still_pending | rejected_or_dropped | unknown`
- `lifecycle_state` aligned to confirmation outcome
- `confirmation_id` (optional, when available)

## Confirmation transitions

Allowed transitions:

- `not_polled -> still_pending|confirmed|rejected_or_dropped|unknown`
- `still_pending -> still_pending|confirmed|rejected_or_dropped|unknown`
- `unknown -> still_pending|confirmed|rejected_or_dropped|unknown`
- `confirmed -> confirmed` (terminal)
- `rejected_or_dropped -> rejected_or_dropped` (terminal)

Invalid transitions are fail-closed.

## Reconciliation proof boundary

After reconciliation:

- `confirmed` means provider reports finalized/confirmed state for that submission.
- `still_pending` means no finality signal yet.
- `rejected_or_dropped` means provider indicates rejection/drop.
- `unknown` means status cannot be proven from current response.

## Out of scope

- generic RPC real execution
- wallet auth/cross-chain payment logic
- nonce management and replay protection runtime
- encryption runtime / DB / distributed coordination
