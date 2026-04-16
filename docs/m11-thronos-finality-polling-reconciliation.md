# M11 — Thronos finality polling and reconciliation

M11 introduces the first Thronos-specific polling/reconciliation contract on top of submission receipts.

## Polling contract

Adapters expose `poll_attestation(submission_id, tx_hash, reconciliation_id)` and return:

- `confirmation_status`: `confirmed | still_pending | rejected_or_dropped | unknown`
- `lifecycle_state` aligned to confirmation outcome
- `confirmation_id` (optional, when available)

JSON-RPC poll result hardening:

- poll envelope must be valid JSON-RPC `2.0`
- `result.status`, when present, must be a string
- `result.confirmation_id`, when present, must be a string

Identity tuple rules for polling:

- `submission_id` is required
- `tx_hash` must be a valid `0x`-prefixed 32-byte hash when provided
- `reconciliation_id` must be `"<network>:<tx_hash>"`
- if only `reconciliation_id` is supplied, `<tx_hash>` is used for polling
- if both `tx_hash` and `reconciliation_id` are supplied, they must match
- reconciliation requests are rejected if `submission_id` is missing
- reconciliation requests are rejected if both `tx_hash` and `reconciliation_id` are missing

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

- `confirmed` means the provider reports finalized/confirmed state for the tuple
  `(submission_id, tx_hash, reconciliation_id)` used during polling.
  This proves backend-observed finality for that tuple and may include a
  `confirmation_id` that can be logged for audit correlation.
- `still_pending` means no finality signal yet.
- `rejected_or_dropped` means provider indicates rejection/drop.
- `unknown` means status cannot be proven from current response.

What this does **not** prove:

- on-chain inclusion proofs outside the provider response boundary
- multi-provider consensus/finality
- replay-protection/nonce guarantees
- cross-domain settlement semantics

## Out of scope

- generic RPC real execution
- wallet auth/cross-chain payment logic
- nonce management and replay protection runtime
- encryption runtime / DB / distributed coordination
- durable background pollers and distributed reconciliation coordination
