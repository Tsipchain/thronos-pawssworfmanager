# M12 — Thronos finality and replay truth layer

M12 extends M11 from polling outcome labels to a truth-layer contract for finality and replay preparation.

## Finality-aware confirmation contract

The attestation receipt now carries:

- `confirmation_status`: poll outcome class (`confirmed`, `still_pending`, `rejected_or_dropped`, `unknown`)
- `finality_status`: finality class (`finalized`, `not_finalized`, `rejected`, `unknown`)
- `confirmation_proof`: provider-shaped proof metadata (`proof_source`, `proof_kind`, `provider_status`)

For Thronos:

- provider status `finalized` => `confirmation_status=confirmed`, `finality_status=finalized`
- provider status `confirmed` => `confirmation_status=confirmed`, `finality_status=not_finalized`
- provider status `pending|submitted` => `still_pending` + `not_finalized`
- provider status `rejected|dropped` => `rejected_or_dropped` + `rejected`

## Replay preparation contract

Without introducing wallet auth or durable storage, reconciliation now prepares replay state via:

- `replay_key`: deterministic SHA-256 of `(submission_id, tx_hash, reconciliation_id)`
- `replay_observation_count`: local observation counter on repeated reconciliation
- `replay_state`:
  - `not_checked`
  - `first_observation`
  - `repeated_observation_consistent`
  - `repeated_observation_mismatch`

## Deterministic reconciliation behavior

For a stable tuple and stable provider response, repeated reconciliation produces:

- identical `confirmation_status`
- identical `finality_status`
- stable `replay_key`
- monotonic `replay_observation_count`
- `replay_state=repeated_observation_consistent`

## Proof/non-proof boundary

After `finality_status=finalized`, the system can prove:

- the adapter observed a Thronos provider finality signal for the reconciliation tuple
- deterministic local replay-key linkage for repeated observations

It still cannot prove:

- independent consensus proofs beyond provider response
- wallet-level nonces/signer-auth replay guarantees
- multi-provider or cross-domain settlement guarantees

## Out of scope

- generic RPC real execution
- wallet auth/signer runtime
- cross-chain payment logic
- encryption runtime
- database integration / distributed coordination
