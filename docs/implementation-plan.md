# Minimal Implementation Plan

## Phase 1 — Deterministic foundation contracts

### Objective
Lock down deterministic contracts and invariants before infrastructure coupling.

### Scope
- Finalize canonical state encoding decision.
- Finalize hash/version linkage format.
- Stabilize API and data model schemas (still mock storage/chain adapters).
- Add tests for canonicalization determinism and monotonic version rules.

### Non-scope
- Real storage backend integration
- Real chain writes
- Real auth stack

## Phase 2 — Service workflow skeleton

### Objective
Implement end-to-end skeleton flow with stub adapters and explicit attestation lifecycle states.

### Scope
- API handlers for create/upload/query/verify (skeleton behavior).
- Stubbed persistence adapter interface and in-memory test double.
- Stubbed Thronos attestation adapter interface and test double.
- State machine for `pending -> confirmed/failed` attestation metadata.

### Non-scope
- Production storage engine
- Production blockchain integration
- Production identity/auth implementation

## Phase 3 — Hardening prep before real integrations

### Objective
Prepare for secure integration by closing critical security decisions and adding adversarial tests.

### Scope
- Resolve remaining high-impact open decisions (crypto profile, submission mode, verification policy).
- Add rollback/fork/tamper simulation tests.
- Define observability/audit event contract.
- Define migration checklist for future production integrations.

### Non-scope
- UI clients
- Sharing/recovery features
- End-user product polish
