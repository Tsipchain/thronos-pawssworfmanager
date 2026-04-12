# Open Decisions (Engineer-Reviewable Matrix)

This document tracks review-ready decisions and their freeze state.

Resolution state definitions:
- **Open:** no proposal yet.
- **Proposed:** recommended default selected, pending review approval.
- **Frozen:** approved and locked for implementation scope.

Blocking level definitions:
- **High:** must be resolved before related implementation begins.
- **Medium:** may begin with stubs/interfaces, but must be resolved before integration hardening.
- **Low:** can be deferred to later hardening phases.

## Current resolution snapshot

| OD | Decision area | Blocking level | Resolution state | Recommended default |
|---|---|---|---|---|
| OD-01 | Canonical encoding | High | **Proposed (Phase 1 Freeze Candidate)** | JCS canonical JSON |
| OD-02 | Encryption profile | High | **Proposed (Phase 1 Freeze Candidate)** | XChaCha20-Poly1305 |
| OD-03 | KDF policy | High | **Proposed (Phase 1 Freeze Candidate)** | Argon2id |
| OD-04 | Version commitment structure | High | **Proposed (Phase 1 Freeze Candidate)** | Manifest hash + parent hash + monotonic version |
| OD-05 | Attestation submission strategy | Medium | Open | Async queue/worker |
| OD-06 | Thronos contract/event shape | Medium | Open | Event-only log (v1) |
| OD-07 | Identity binding for writes | High (auth scope) | Open | Hybrid token + wallet signature |
| OD-08 | Metadata leakage minimization | Low | Open | No padding in v1 |
| OD-09 | Deletion semantics | Medium (storage scope) | Open | Tombstone + retention policy |
| OD-10 | Verification responsibility split | Medium | Open | Server endpoint + independent client verification capability |
| OD-11 | Multi-device key portability | Low | Open | Client export/import only |

---

## OD-01 — Canonical state encoding for `vault_state_hash`
- **Problem statement:** We need one deterministic byte representation of logical vault state so independent clients always produce the same hash.
- **Allowed options:** JCS canonical JSON; protobuf canonical bytes; custom merkleized canonical format.
- **Recommended default:** **JCS canonical JSON (v1)**.
- **Proposed resolution state:** **Proposed (Phase 1 Freeze Candidate)**.
- **Rationale:** Human-auditable, language-agnostic deterministic encoding with lower early-phase complexity.
- **Tradeoffs:** Easier interoperability/debugging vs potential canonicalization edge-case burden.
- **Implementation impact:** Locks hash input contract used by clients, server validation, and attestation payload generation.
- **Blocking level:** **High**.

## OD-02 — Symmetric encryption profile for vault blobs
- **Problem statement:** We need one baseline AEAD cipher profile for compatible and secure client-side encryption.
- **Allowed options:** AES-256-GCM; XChaCha20-Poly1305.
- **Recommended default:** **XChaCha20-Poly1305 (v1 profile)**.
- **Proposed resolution state:** **Proposed (Phase 1 Freeze Candidate)**.
- **Rationale:** Strong nonce-safety posture for distributed clients and safe-default usage patterns.
- **Tradeoffs:** Better misuse resistance margin vs possible lower hardware acceleration prevalence.
- **Implementation impact:** Defines ciphertext envelope metadata and SDK compatibility contract.
- **Blocking level:** **High**.

## OD-03 — KDF and parameter policy
- **Problem statement:** We need a key-derivation baseline that raises offline attack cost while remaining deployable.
- **Allowed options:** Argon2id baseline; scrypt baseline; PBKDF2 compatibility fallback only.
- **Recommended default:** **Argon2id with documented minimum memory/time parameters**.
- **Proposed resolution state:** **Proposed (Phase 1 Freeze Candidate)**.
- **Rationale:** Memory-hard profile aligned with current password-based key derivation best practice.
- **Tradeoffs:** Stronger brute-force resistance vs parameter tuning complexity for low-power devices.
- **Implementation impact:** Defines KDF metadata contract and compatibility policy.
- **Blocking level:** **High**.

## OD-04 — Version commitment structure
- **Problem statement:** We need deterministic continuity checks that detect rollback and forked histories.
- **Allowed options:** Monotonic `version + vault_state_hash` only; hash-linked chain with parent reference.
- **Recommended default:** **Manifest hash + parent hash + monotonic version**.
- **Proposed resolution state:** **Proposed (Phase 1 Freeze Candidate)**.
- **Rationale:** Stronger continuity/tamper evidence with modest metadata overhead.
- **Tradeoffs:** Better fork/rollback detection vs slightly higher state-management complexity.
- **Implementation impact:** Affects data schema, verification logic, and attestation payload shape.
- **Blocking level:** **High**.

## OD-05 — Attestation submission strategy
- **Problem statement:** Decide inline vs asynchronous attestation submission behavior.
- **Allowed options:** Synchronous submission in write path; async queue/worker submission.
- **Recommended default:** **Async queue/worker with explicit `pending/confirmed/failed` states**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Better API latency isolation and retry resilience.
- **Tradeoffs:** Operational resilience vs eventual consistency complexity.
- **Implementation impact:** Requires lifecycle state model and retry/error semantics.
- **Blocking level:** **Medium**.

## OD-06 — Thronos contract/event shape
- **Problem statement:** Choose stable commitment schema for on-chain attestations.
- **Allowed options:** Event-only attestation log; stateful latest-version contract.
- **Recommended default:** **Event-only log for v1**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Lower chain complexity and simpler early integration path.
- **Tradeoffs:** Simpler contract behavior vs more indexing burden off-chain.
- **Implementation impact:** Defines attestation adapter payload and verification index requirements.
- **Blocking level:** **Medium**.

## OD-07 — Identity binding for write operations
- **Problem statement:** Define practical authorization binding for vault mutations.
- **Allowed options:** Wallet signature only; hybrid token + wallet signature.
- **Recommended default:** **Hybrid token + wallet signature for high-risk mutations**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Balances session control/revocation with cryptographic intent proof.
- **Tradeoffs:** Layered control vs increased auth complexity.
- **Implementation impact:** Shapes request auth contract and audit semantics.
- **Blocking level:** **High (for auth scope)**.

## OD-08 — Metadata leakage minimization
- **Problem statement:** Define stance on size/timing side-channel leakage.
- **Allowed options:** No padding; fixed-size bucket padding; batch windows.
- **Recommended default:** **No padding in v1, with explicit documented leakage**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Keeps early system simple and reviewable.
- **Tradeoffs:** Lower complexity vs known traffic-analysis leakage.
- **Implementation impact:** Informs future privacy hardening roadmap.
- **Blocking level:** **Low**.

## OD-09 — Deletion semantics for ciphertext
- **Problem statement:** Define deletion behavior balancing compliance, auditability, and integrity history.
- **Allowed options:** Hard delete; tombstone + retention policy.
- **Recommended default:** **Tombstone metadata + retention policy; preserve historical attestation references**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Maintains audit continuity while allowing lifecycle control.
- **Tradeoffs:** Better compliance posture vs operational/storage complexity.
- **Implementation impact:** Defines lifecycle state machine and policy controls.
- **Blocking level:** **Medium (for storage scope)**.

## OD-10 — Verification responsibility split
- **Problem statement:** Define minimum trust posture for attestation verification.
- **Allowed options:** Server verification endpoint only; mandatory independent client verification capability.
- **Recommended default:** **Server endpoint + independent client verification capability**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Practical interoperability plus trust-minimized verification path.
- **Tradeoffs:** Better assurance vs additional SDK/client complexity.
- **Implementation impact:** Affects verification API guarantees and client conformance requirements.
- **Blocking level:** **Medium**.

## OD-11 — Multi-device key portability boundary
- **Problem statement:** Define multi-device portability while preserving self-custody assumptions.
- **Allowed options:** Client export/import only; optional encrypted key-wrap artifact.
- **Recommended default:** **Client export/import only in early phases**.
- **Proposed resolution state:** **Open**.
- **Rationale:** Minimizes key-risk surface until stronger threat-reviewed portability design exists.
- **Tradeoffs:** Strong custody boundary vs reduced onboarding convenience.
- **Implementation impact:** Defers server-assisted portability mechanisms.
- **Blocking level:** **Low**.

---

## Blocker classification by implementation area

### Must be resolved before any crypto implementation
- **OD-01**, **OD-02**, **OD-03**, **OD-04**

### Must be resolved before any storage implementation
- **OD-04**, **OD-09**

### Must be resolved before any attestation implementation
- **OD-01**, **OD-04**, **OD-05**, **OD-06**, **OD-10**

### Must be resolved before any auth implementation
- **OD-07**

## Phase 1 true blockers
- **OD-01** canonical encoding
- **OD-02** encryption profile
- **OD-03** KDF policy
- **OD-04** version commitment structure
