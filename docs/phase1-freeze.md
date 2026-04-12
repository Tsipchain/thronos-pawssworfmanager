# Phase 1 Decision Freeze (Preparation Draft)

## Purpose

Define what must be frozen before Phase 1 implementation can begin, and what remains intentionally unfrozen.

## What is now proposed to be frozen (pending approval)

1. **OD-01 Canonical encoding:** JCS canonical JSON.
2. **OD-02 Encryption profile:** XChaCha20-Poly1305.
3. **OD-03 KDF policy:** Argon2id with documented baseline parameters.
4. **OD-04 Version commitment structure:** manifest hash + parent hash + monotonic version.

These four are the true Phase 1 blockers.

## What remains unfrozen after this pass

- OD-05 Attestation submission strategy.
- OD-06 Thronos contract/event shape.
- OD-07 Identity binding for writes.
- OD-08 Metadata leakage minimization.
- OD-09 Deletion semantics.
- OD-10 Verification responsibility split.
- OD-11 Multi-device key portability boundary.

## What implementation may begin only after freeze approval

After approval of OD-01..OD-04, teams may begin only:

- deterministic canonicalization contract documentation-to-test translation,
- crypto-interface contract scaffolding (no production crypto logic),
- version-chain data contract scaffolding,
- Phase 1 validation tests for determinism, version monotonicity, and parent-link continuity.

## What still may NOT begin after this freeze alone

- production cryptographic implementation,
- production storage backend integration,
- production attestation integration/writes,
- production authentication/authorization implementation.

Additional decision closures are required in their respective domains before those implementations start.
