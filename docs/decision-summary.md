# Decision Summary (Phase 1 Start Readiness)

## A) Frozen Phase 1 blocker decisions (approved)

| OD | Frozen default | Status |
|---|---|---|
| OD-01 | JCS canonical JSON for canonical hash input bytes | **Frozen** |
| OD-02 | XChaCha20-Poly1305 encryption profile | **Frozen** |
| OD-03 | Argon2id with documented minimum parameters | **Frozen** |
| OD-04 | Manifest hash + parent hash + monotonic version | **Frozen** |

## B) Still-open decisions (non-Phase-1-blocking)

| OD | Current favored direction | Blocks which implementation scope |
|---|---|---|
| OD-05 | Async attestation submission lifecycle | Attestation implementation |
| OD-06 | Event-only on-chain attestation log (v1) | Attestation implementation |
| OD-07 | Hybrid token + wallet signature | Auth implementation |
| OD-08 | No padding in v1; document leakage | Privacy hardening |
| OD-09 | Tombstone + retention policy | Storage implementation |
| OD-10 | Server endpoint + independent client verification capability | Attestation verification implementation |
| OD-11 | Client export/import only | Multi-device portability hardening |

## C) Phase 1-start blocker gate (satisfied by freeze)

- OD-01, OD-02, OD-03, OD-04 are frozen and can be used as implementation inputs.

## D) Remaining gate requirements by domain

### Before any storage implementation
- OD-09 (and keep OD-04 applied)

### Before any attestation implementation
- OD-05, OD-06, OD-10 (and keep OD-01/OD-04 applied)

### Before any auth implementation
- OD-07
