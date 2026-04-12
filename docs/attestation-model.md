# Attestation Model (Foundation Draft)

## Purpose

Use Thronos as a public integrity anchor for vault version commitments, not as secret storage.

## Attested unit

Per vault version, the attested payload conceptually includes:

- `vault_id` (opaque reference)
- `version` (monotonic)
- `vault_state_hash` (deterministic commitment)
- optional previous linkage reference (if hash-chain mode is chosen)

## Attestation flow (conceptual)

1. Client computes `vault_state_hash` from canonical vault state representation.
2. Client sends ciphertext + metadata to service.
3. Service persists ciphertext off-chain and indexes metadata.
4. Service submits attestation commitment to Thronos (sync/async still open).
5. Service returns attestation reference data for verification.

## Verification goals

- Detect rollback (older version served as latest)
- Detect fork/inconsistent history
- Detect blob replacement without matching commitment

## Chain data minimization principles

- Commit only integrity data required for verification.
- Exclude plaintext and decryption-enabling material.
- Avoid human-readable secret descriptors.

## Failure semantics (draft)

- If storage succeeds and attestation is pending, state marked `pending_attestation`.
- If attestation fails permanently, state marked `attestation_failed` and requires retry/remediation path.
- Client should verify latest confirmed commitment before trusting as canonical latest.

## Out-of-scope in this pass

- Smart contract implementation
- Transaction fee policy
- Final finality-depth policy
