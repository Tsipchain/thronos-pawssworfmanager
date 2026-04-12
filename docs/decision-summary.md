# Decision Summary (Review Prep)

This summary is intended for engineering/security review meetings to accelerate closure of open decisions.

## Recommended defaults per OD

| OD | Recommended default | Blocking level |
|---|---|---|
| OD-01 | JCS canonical JSON for `vault_state_hash` input bytes | High |
| OD-02 | XChaCha20-Poly1305 encryption profile | High |
| OD-03 | Argon2id with documented minimum parameters | High |
| OD-04 | Hash-chain with `parent_hash` + monotonic version | High |
| OD-05 | Async attestation submission with explicit lifecycle states | Medium |
| OD-06 | Event-only on-chain attestation log for v1 | Medium |
| OD-07 | Hybrid token + wallet signature for mutation auth | High (auth scope) |
| OD-08 | No padding in v1; document metadata leakage | Low |
| OD-09 | Tombstone + retention policy for deletions | Medium (storage scope) |
| OD-10 | Server verification endpoint + mandatory client-verification capability | Medium |
| OD-11 | Client export/import only for multi-device portability | Low |

## Resolution gates by implementation domain

### Before any crypto implementation
- OD-01, OD-02, OD-03, OD-04

### Before any storage implementation
- OD-04, OD-09

### Before any attestation implementation
- OD-01, OD-04, OD-05, OD-06, OD-10

### Before any auth implementation
- OD-07

## True blockers for Phase 1

Phase 1 should not begin implementation work until these are closed:
- OD-01 canonical encoding
- OD-02 encryption profile
- OD-03 KDF profile
- OD-04 version commitment structure

## Review checklist for closure

A decision is considered review-closed when:
1. selected default is approved by engineering + security reviewers,
2. rejected alternatives and rationale are recorded,
3. impact on architecture/data/API docs is propagated,
4. acceptance tests are identified for implementation phases.
