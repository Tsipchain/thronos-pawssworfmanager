# Decision Summary (Phase 1 Freeze Prep)

## A) Proposed defaults (Phase 1 blocker candidates)

These are proposed for freeze approval before Phase 1 implementation starts.

| OD | Proposed default | Freeze intent |
|---|---|---|
| OD-01 | JCS canonical JSON for canonical hash input bytes | Freeze candidate |
| OD-02 | XChaCha20-Poly1305 encryption profile | Freeze candidate |
| OD-03 | Argon2id with documented minimum parameters | Freeze candidate |
| OD-04 | Manifest hash + parent hash + monotonic version | Freeze candidate |

## B) Still-open decisions (non-blocking for Phase 1 start)

| OD | Current recommended direction | Blocking scope |
|---|---|---|
| OD-05 | Async attestation submission lifecycle | Attestation implementation |
| OD-06 | Event-only on-chain attestation log (v1) | Attestation implementation |
| OD-07 | Hybrid token + wallet signature | Auth implementation |
| OD-08 | No padding in v1; document leakage | Privacy hardening |
| OD-09 | Tombstone + retention policy | Storage implementation |
| OD-10 | Server endpoint + independent client verification capability | Attestation verification implementation |
| OD-11 | Client export/import only | Multi-device portability hardening |

## C) Resolution gates by implementation domain

### Before any crypto implementation
- OD-01, OD-02, OD-03, OD-04

### Before any storage implementation
- OD-04, OD-09

### Before any attestation implementation
- OD-01, OD-04, OD-05, OD-06, OD-10

### Before any auth implementation
- OD-07

## D) True blockers for Phase 1

- OD-01 canonical encoding
- OD-02 encryption profile
- OD-03 KDF policy
- OD-04 version commitment structure

## E) Approval checklist for freeze

A blocker is freeze-approved when:
1. engineering + security sign off on selected default,
2. alternatives and rejection rationale are documented,
3. impacts are propagated to architecture/data/API docs,
4. acceptance tests are defined for subsequent implementation work.
