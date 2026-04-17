# M9 — Chain-agnostic attestation preparation (Thronos-first, RPC-compatible)

This milestone prepares attestation contracts for future real submission without coupling deterministic core or orchestrator to one chain.

## Attestation payload contract

`AttestationPayload` fields:

- `manifest_hash`
- `manifest_version`
- `attestation_schema_version`
- `source_system`
- `target_backend_type`
- `target_network`
- `metadata` (non-secret map only)

### Security boundary

- Payload is manifest-hash based.
- Payload excludes raw manifest, canonical bytes, entry content, and secrets.

## Supported attestation backend types

- `fake`
- `thronos_network` (first-class)
- `rpc_generic` (RPC-compatible shape)

## Provider config shapes

### thronos_network

- `rpc_url`
- `chain_id`
- `contract_address`
- `signer_ref`
- optional `gas_policy_ref`

### rpc_generic

- `rpc_url`
- `chain_id`
- `contract_address`
- `signer_ref`
- optional `backend_label`

## Execution/gating guarantees

- Real attestation remains disabled by default.
- `execute` mode remains forbidden for real-like attestation backends by policy.
- Contradictory/partial provider config is refused at startup.

## Receipt contract (future-facing)

Attestation receipts include:

- `backend`
- `network`
- `status`
- `attestation_id`
- `tx_hash` (optional; currently null)
- `submitted_at` (not implemented; currently null)
- `retryable`
- `failure_class`
- `execution_mode`
- `dry_run`

## Non-goals in M9

- no real transaction submission
- no signer usage
- no wallet auth
- no cross-chain payment logic
