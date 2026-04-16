# M13 — Generic RPC real attestation preparation

M13 prepares (but does not enable) the generic RPC attestation path with the same contract discipline used for Thronos.

## Generic RPC adapter contract (prepare-only)

`GenericRpcAttestationAdapter` is introduced as a dry-run-only contract adapter:

- accepts existing `AttestationPayload`
- emits existing attestation receipt shape (`submission_id`, `confirmation_status`, `finality_status`, replay/finality-compatible fields)
- exposes generic-RPC readiness capabilities (`rpc_submit_method`, `rpc_poll_method`, `backend_label`)
- fails closed if execution is requested (`rpc_generic_execution_disabled`)

No real generic RPC submission or polling side effects are enabled.

## Provider config shape for `rpc_generic`

`rpc_generic` now requires provider shape completeness:

- `ATTESTATION_TARGET_NETWORK`
- `ATTESTATION_RPC_URL`
- `ATTESTATION_CHAIN_ID`
- `ATTESTATION_SIGNER_REF` (or key ref alias)
- `ATTESTATION_BACKEND_LABEL`
- `ATTESTATION_RPC_SUBMIT_METHOD`

Optional:

- `ATTESTATION_RPC_POLL_METHOD`

## Compatibility with existing contracts

Shared with Thronos path:

- `AttestationPayload` contract
- `AttestationReceipt` core fields and lifecycle/finality/replay fields
- reconciliation readiness shape

Backend-specific to generic RPC prep:

- method metadata (`rpc_submit_method`, `rpc_poll_method`)
- backend label (`backend_label`)
- execute disabled by policy

## Guarantees / non-guarantees

Guaranteed in M13:

- strict dry-run contract compatibility for `rpc_generic`
- provider-shape validation and capability reporting
- fail-closed startup for missing required generic-RPC config fields

Not guaranteed in M13:

- generic RPC real execution
- wallet/signer auth runtime semantics
- cross-chain settlement/payment logic
- encryption runtime or DB/distributed coordination
