# M10 — First real Thronos attestation execution (gated)

M10 introduces the first real attestation submission path for **Thronos Network only**.

## What is enabled

- Real submission adapter: `RealThronosAttestationAdapter`
- Backend scope: `thronos_network` only
- Submission input: `AttestationPayload` only
- Receipt includes future-facing tx fields (`tx_hash`) with execute/dry-run visibility

## Gating guarantees

- If execution is not enabled, real submission does not run.
- If provider config is incomplete for Thronos backend shape, startup fails.
- `rpc_generic` execute remains disabled in this milestone.

## Provider requirements (thronos_network)

- `target_network`
- `rpc_url`
- `chain_id`
- `contract_address`
- `signer_ref`

## Non-goals

- no generic RPC real execution
- no wallet auth
- no cross-chain payment logic
- no encryption runtime
- no DB/distributed coordination
