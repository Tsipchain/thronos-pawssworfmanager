# M14 — Generic RPC real execution (gated, first pass)

M14 introduces the first real `rpc_generic` attestation submission path behind existing execution gates.

## What is added

- `GenericRpcAttestationAdapter` now supports real submission when `exec_enabled=True`
- submission uses `ATTESTATION_RPC_SUBMIT_METHOD` and validates JSON-RPC envelope/result
- result must include a valid `tx_hash` (`0x` + 32-byte hex)
- receipts remain contract-compatible with existing attestation lifecycle/finality/replay fields

## Gating and policy

- `rpc_generic+execute` is now an allowed policy pair
- real submission still requires global execution gates (`ENABLE_REAL_EXECUTION`, mode/ready/policy)
- capability/metadata reporting includes explicit rpc_generic pair/readiness/enabled semantics

## What this can prove in M14

- adapter submitted via configured generic RPC method and received a structurally valid tx hash response
- receipt lifecycle is `submitted_not_finalized` with finality/replay-compatible fields initialized

## What this cannot prove in M14

- generic-RPC-specific finalized polling semantics beyond existing shared contracts
- wallet/signer auth semantics
- cross-chain payment/settlement semantics
- encryption runtime, database integration, distributed coordination
