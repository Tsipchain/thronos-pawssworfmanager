# Phase 1 Implementation Checklist (Deterministic Core)

This checklist is for implementation kickoff readiness and strict scope control.

## Decision freeze verification

- [ ] Confirm OD-01 freeze text is unchanged (JCS canonical JSON).
- [ ] Confirm OD-02 freeze text is unchanged (XChaCha20-Poly1305).
- [ ] Confirm OD-03 freeze text is unchanged (Argon2id).
- [ ] Confirm OD-04 freeze text is unchanged (manifest hash + parent hash + monotonic version).

## Module/interface readiness

- [ ] `canonical_manifest` interfaces approved.
- [ ] `state_hash` interfaces approved.
- [ ] `version_chain` interfaces approved.
- [ ] `argon2id_policy` interfaces approved.
- [ ] `envelope_format_spec` interfaces approved.
- [ ] `deterministic_vectors` interfaces approved.

## Deterministic invariants readiness

- [ ] Canonical bytes determinism invariant documented.
- [ ] Hash determinism and mutation sensitivity invariants documented.
- [ ] Parent-hash + monotonic version invariants documented.
- [ ] Argon2id minimum policy invariants documented.
- [ ] Envelope required-field/version invariants documented.

## Test-vector readiness

- [ ] Canonical encoding pass/failure vectors drafted.
- [ ] State hashing pass/failure vectors drafted.
- [ ] Parent-hash chaining pass/failure vectors drafted.
- [ ] Argon2id pass/failure vectors drafted.
- [ ] Envelope-format pass/failure vectors drafted.

## Scope guardrails before coding

- [ ] No storage backend implementation tasks in sprint scope.
- [ ] No auth implementation tasks in sprint scope.
- [ ] No API runtime tasks in sprint scope.
- [ ] No blockchain write tasks in sprint scope.
- [ ] No database integration tasks in sprint scope.
- [ ] No UI/sharing/recovery/multi-device tasks in sprint scope.
