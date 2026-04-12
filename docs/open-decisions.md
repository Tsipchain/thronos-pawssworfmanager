# Open Decisions (Engineer-Reviewable Matrix)

This document converts open design questions into review-ready decision entries with recommended defaults.

Blocking level definitions:
- **High**: must be resolved before related implementation begins.
- **Medium**: may begin with stubs/interfaces, but must be resolved before integration hardening.
- **Low**: can be deferred to later hardening phases.

---

## OD-01 — Canonical state encoding for `vault_state_hash`

- **Problem statement:** We need one deterministic byte representation of logical vault state so independent clients always produce the same hash.
- **Allowed options:**
  1. JCS canonical JSON
  2. Protobuf canonical bytes
  3. Custom merkleized canonical format
- **Recommended default:** **JCS canonical JSON (v1)**.
- **Rationale:** Fastest path to human-auditable, language-agnostic deterministic hashing with lower implementation complexity for first secure baseline.
- **Tradeoffs:**
  - Pros: readability, easier cross-language debugging.
  - Cons: potential performance overhead and stricter canonicalization pitfalls if not rigorously tested.
- **Implementation impact:** Locks hash input contract used by clients, API metadata validation, and attestation payload generation.
- **Blocking level:** **High**.

## OD-02 — Symmetric encryption profile for vault blobs

- **Problem statement:** We need one baseline AEAD cipher profile for client-side encryption compatibility and security guarantees.
- **Allowed options:**
  1. AES-256-GCM
  2. XChaCha20-Poly1305
- **Recommended default:** **XChaCha20-Poly1305 (v1 profile)**.
- **Rationale:** Strong nonce-misuse resilience characteristics for distributed clients and simple safe-default ergonomics.
- **Tradeoffs:**
  - Pros: safer nonce handling margin, modern misuse-resilience posture.
  - Cons: hardware acceleration may be less ubiquitous than AES on some platforms.
- **Implementation impact:** Defines ciphertext format envelope, metadata schema expectations, and compatibility requirements for future SDKs.
- **Blocking level:** **High**.

## OD-03 — KDF and parameter policy

- **Problem statement:** We need a standard key derivation baseline to resist offline guessing while remaining deployable on common client hardware.
- **Allowed options:**
  1. Argon2id baseline
  2. scrypt baseline
  3. PBKDF2 compatibility fallback only
- **Recommended default:** **Argon2id baseline with documented minimum memory/time parameters**.
- **Rationale:** Best-practice memory-hard defense profile for modern password-derived key workflows.
- **Tradeoffs:**
  - Pros: stronger offline attack cost amplification.
  - Cons: tuning burden across low-power devices.
- **Implementation impact:** Determines key-derivation metadata fields and client compatibility policy.
- **Blocking level:** **High**.

## OD-04 — Version commitment structure

- **Problem statement:** We need to detect rollback/fork scenarios in version history with clear deterministic linkage.
- **Allowed options:**
  1. Monotonic `version + vault_state_hash` only
  2. Hash-chain (`parent_hash` linkage per version)
- **Recommended default:** **Hash-chain linkage (`parent_hash`) + monotonic version**.
- **Rationale:** Stronger tamper and fork evidence with minimal additional metadata.
- **Tradeoffs:**
  - Pros: explicit historical continuity proofs.
  - Cons: slightly more complex conflict/recovery handling.
- **Implementation impact:** Affects data model fields, verification routines, and attestation payload semantics.
- **Blocking level:** **High**.

## OD-05 — Attestation submission strategy

- **Problem statement:** We need to define whether attestation happens inline with write requests or asynchronously.
- **Allowed options:**
  1. Synchronous submission in write path
  2. Async queue/worker submission
- **Recommended default:** **Async queue/worker with explicit `pending/confirmed/failed` states**.
- **Rationale:** Better reliability and latency isolation from chain/RPC variability.
- **Tradeoffs:**
  - Pros: decouples API latency from chain conditions.
  - Cons: introduces eventual consistency complexity.
- **Implementation impact:** Requires attestation lifecycle state model and retry policy design.
- **Blocking level:** **Medium**.

## OD-06 — Thronos contract/event shape

- **Problem statement:** We need a stable on-chain commitment schema for long-term verification compatibility.
- **Allowed options:**
  1. Event-only attestation log
  2. Stateful contract tracking latest version/hash
- **Recommended default:** **Event-only log for v1**.
- **Rationale:** Minimal chain footprint and lower contract-state complexity while preserving auditability.
- **Tradeoffs:**
  - Pros: simpler chain-side logic and upgrade path.
  - Cons: client/server verification queries may need more indexing work.
- **Implementation impact:** Defines attestation adapter payload and verification index expectations.
- **Blocking level:** **Medium**.

## OD-07 — Identity binding for write operations

- **Problem statement:** We need a trust-minimized but practical authorization binding model for vault mutations.
- **Allowed options:**
  1. Wallet signature only
  2. Hybrid service token + wallet signature
- **Recommended default:** **Hybrid token + wallet signature for high-risk mutations**.
- **Rationale:** Balances operational control (session handling/revocation) with cryptographic user intent proof.
- **Tradeoffs:**
  - Pros: stronger layered control and revocation ergonomics.
  - Cons: more moving parts and auth complexity.
- **Implementation impact:** Impacts request signing contract, auth middleware design, and audit model.
- **Blocking level:** **High (for auth implementation only)**.

## OD-08 — Metadata leakage minimization

- **Problem statement:** We need a posture on side-channel leakage through ciphertext size/timing patterns.
- **Allowed options:**
  1. No padding (documented leakage)
  2. Fixed-size bucket padding
  3. Batch windows / delayed commit patterns
- **Recommended default:** **No padding in v1 with explicit leakage documentation and future optional padding mode**.
- **Rationale:** Keeps initial system simple while making leakage explicit and reviewable.
- **Tradeoffs:**
  - Pros: lower complexity and cost.
  - Cons: traffic analysis risk remains.
- **Implementation impact:** Influences storage format policy and future privacy hardening roadmap.
- **Blocking level:** **Low**.

## OD-09 — Deletion semantics for ciphertext

- **Problem statement:** We need clear deletion behavior that balances compliance, auditability, and integrity history.
- **Allowed options:**
  1. Hard delete
  2. Tombstone + retention policy
- **Recommended default:** **Tombstone metadata + retention policy; never rewrite prior on-chain attestations**.
- **Rationale:** Preserves audit continuity while allowing controlled data lifecycle operations.
- **Tradeoffs:**
  - Pros: better forensic/compliance posture.
  - Cons: storage and policy complexity.
- **Implementation impact:** Affects storage lifecycle state machine and legal/compliance docs.
- **Blocking level:** **Medium (for storage implementation)**.

## OD-10 — Verification responsibility split

- **Problem statement:** We need to define minimum trust posture for validating attested state continuity.
- **Allowed options:**
  1. Server verification endpoint only
  2. Mandatory independent client verification path
- **Recommended default:** **Server endpoint + mandatory independent client verification capability in protocol docs**.
- **Rationale:** Provides practical interoperability while preserving trust-minimized validation path.
- **Tradeoffs:**
  - Pros: compatibility for thin clients and stronger independent assurance.
  - Cons: requires additional client/SDK verification logic over time.
- **Implementation impact:** Shapes API guarantees and SDK/protocol conformance requirements.
- **Blocking level:** **Medium**.

## OD-11 — Multi-device key portability boundary

- **Problem statement:** We need a policy for multi-device use that does not violate self-custody assumptions.
- **Allowed options:**
  1. Client export/import only
  2. Optional encrypted key-wrap artifact
- **Recommended default:** **Client export/import only in early phases**.
- **Rationale:** Minimizes server-side key-risk surface until stronger threat-reviewed design is complete.
- **Tradeoffs:**
  - Pros: strict self-custody posture.
  - Cons: weaker usability for multi-device onboarding.
- **Implementation impact:** Defers server-managed portability features and keeps custody boundary strict.
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

## Phase-1 true blockers

For Phase 1 deterministic foundation work, the true blockers are:
- **OD-01** canonical encoding
- **OD-02** AEAD baseline
- **OD-03** KDF policy
- **OD-04** version commitment structure
