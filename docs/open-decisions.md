# Open Decisions Matrix

Status legend:
- **Open**: not yet selected
- **Converging**: narrowed to short list
- **Deferred**: intentionally postponed to later phase

| ID | Decision Area | Options Under Consideration | Security Impact | Delivery Impact | Owner | Target Phase | Status |
|---|---|---|---|---|---|---|---|
| OD-01 | Canonical state encoding for `vault_state_hash` | JCS canonical JSON / protobuf canonical bytes / merkleized custom bytes | Critical for deterministic verification and replay resistance | High (locks API and client compatibility) | Core protocol | Phase 1 | Open |
| OD-02 | Symmetric encryption profile for vault blobs | AES-256-GCM / XChaCha20-Poly1305 | Critical confidentiality/integrity primitive choice | Medium | Crypto lead | Phase 1 | Open |
| OD-03 | KDF and policy profile | Argon2id baseline / compatibility mode for constrained clients | High resistance to offline key-guessing | Medium | Crypto lead | Phase 1 | Open |
| OD-04 | Version commitment structure | Simple monotonic version + hash / hash-chain parent linkage | High rollback and fork detection guarantees | Medium | Core protocol | Phase 1 | Converging |
| OD-05 | Attestation submission strategy | Synchronous API write / async worker queue | Medium consistency and finality semantics | High on reliability/latency | Platform | Phase 2 | Open |
| OD-06 | Thronos contract/event shape | Stateless event-only log / stateful latest-version contract | Medium on-chain audit semantics | High (affects integration code) | Chain integration | Phase 2 | Open |
| OD-07 | Identity binding for writes | Wallet signature only / hybrid service token + signature | High unauthorized mutation risk | High (auth model touches all APIs) | Security + platform | Phase 2 | Deferred |
| OD-08 | Metadata leakage minimization | No padding / fixed-size padding / batch commit windows | Medium traffic analysis exposure | Medium cost/performance tradeoff | Security | Phase 3 | Deferred |
| OD-09 | Deletion semantics for ciphertext | Hard delete / tombstone + retention policy | Medium compliance and recoverability implications | Medium operational complexity | Platform + legal | Phase 3 | Open |
| OD-10 | Verification responsibility split | Server-side verification endpoint only / mandatory independent client verification flow | High trust minimization outcome | Medium SDK/client complexity | Core protocol | Phase 2 | Converging |
| OD-11 | Multi-device key portability boundary | Client export/import only / encrypted key-wrap artifact option | High custody and compromise blast radius | Medium | Security | Phase 3 | Deferred |

## Decisions blocked by explicit non-goals in this pass

- No final auth implementation selection.
- No final blockchain write execution path implementation.
- No storage-engine implementation choice.

## Exit criteria to close matrix

A decision can be marked closed only when:
1. canonical invariants are written in docs,
2. threat-model delta is recorded,
3. API/data model impact is reflected,
4. at least one testable acceptance criterion is added to implementation planning.
