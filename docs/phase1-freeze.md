# Phase 1 Decision Freeze (Approved)

## Freeze approval status

Founder approval received for all Phase 1 blocker defaults.

## Frozen decisions (effective for Phase 1)

1. **OD-01:** JCS canonical JSON.
2. **OD-02:** XChaCha20-Poly1305.
3. **OD-03:** Argon2id.
4. **OD-04:** manifest hash + parent hash + monotonic version.

## What is now frozen

- Canonical state encoding contract for deterministic hashing.
- Encryption profile baseline for client-side blob encryption.
- KDF baseline policy family for key derivation.
- Version-chain commitment structure for rollback/fork detection.

## What remains unfrozen

- OD-05 Attestation submission strategy.
- OD-06 Thronos contract/event shape.
- OD-07 Identity binding for writes.
- OD-08 Metadata leakage minimization.
- OD-09 Deletion semantics.
- OD-10 Verification responsibility split.
- OD-11 Multi-device key portability boundary.

## Implementation may begin only within this boundary

Allowed for Phase 1 start:
- deterministic canonicalization and hashing contract implementation,
- version-chain continuity contract implementation,
- Argon2id parameter profile validation harness,
- module/interface scaffolding defined in planning docs.

Still disallowed in this pass and until separately approved:
- storage backend implementation,
- auth implementation,
- API runtime implementation,
- blockchain write implementation,
- UI/sharing/recovery/multi-device feature implementation.
