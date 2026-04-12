# Phase 1 Implementation Checklist (Pre-Execution)

This checklist is for implementation kickoff readiness and scope control.

## Decision freeze verification

- [ ] Confirm OD-01 freeze text is unchanged (JCS canonical JSON).
- [ ] Confirm OD-02 freeze text is unchanged (XChaCha20-Poly1305).
- [ ] Confirm OD-03 freeze text is unchanged (Argon2id).
- [ ] Confirm OD-04 freeze text is unchanged (manifest hash + parent hash + monotonic version).

## Contract definition readiness

- [ ] Canonical JSON schema for manifest input documented.
- [ ] Hash function input-order contract documented with examples.
- [ ] Parent-hash linkage rules documented for genesis and non-genesis versions.
- [ ] Argon2id parameter baseline and acceptable ranges documented.

## Test-vector readiness

- [ ] Canonical encoding vectors drafted.
- [ ] State hashing vectors drafted.
- [ ] Parent-hash chaining vectors drafted.
- [ ] Argon2id parameter validation vectors drafted.

## Scope guardrails before coding

- [ ] No storage backend implementation tasks in sprint scope.
- [ ] No auth implementation tasks in sprint scope.
- [ ] No API runtime tasks in sprint scope.
- [ ] No blockchain write tasks in sprint scope.
- [ ] No UI/sharing/recovery/multi-device tasks in sprint scope.
