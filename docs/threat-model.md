# Threat Model (Draft)

## Assets to protect

- Confidentiality of user secrets (plaintext vault entries)
- Integrity of vault history/version sequence
- Authenticity of attested state commitments
- Availability of encrypted blobs and metadata

## Threat actors

- External attacker targeting API/storage
- Malicious or compromised service operator
- Network adversary intercepting traffic
- Malicious client attempting rollback/fork/injection

## Assumptions

- Client endpoint security is out of scope for backend guarantees.
- Thronos chain provides durable public attestation history.
- Cryptographic primitives are properly implemented and audited in later phases.

## Key threats and mitigations

### 1) Server-side data breach
**Threat:** Attacker exfiltrates DB/object store.
**Mitigation:** Store ciphertext only; no plaintext secrets or master keys server-side.

### 2) Tampering with stored vault blobs
**Threat:** Blob replacement, deletion, replay, or reordering.
**Mitigation:** Deterministic `vault_state_hash` + versioned attestations on-chain; client verifies commitment continuity.

### 3) Rollback attacks
**Threat:** Serving stale but valid ciphertext.
**Mitigation:** Monotonic version numbers and latest attested version checks.

### 4) Metadata leakage
**Threat:** Inference from object size/frequency/timestamps.
**Mitigation:** Documented leakage acceptance; future optional padding/batching.

### 5) Unauthorized write/attestation
**Threat:** Attacker submits fake vault version.
**Mitigation:** Strong client authn/authz, signed mutation requests, server-side version constraints.

### 6) On-chain privacy leakage
**Threat:** Correlating user identities through public commitments.
**Mitigation:** Use opaque vault identifiers/pseudonymous references; avoid plaintext descriptors.

## Out of scope (current)

- Endpoint malware on user devices
- Phishing-resistant UX
- Secret sharing and delegated access controls
- Recovery channels and social trust schemes
