# Crypto Model (Foundation Draft)

## Goals

- Ensure plaintext secrecy from server and chain layers.
- Provide deterministic integrity commitments for vault state attestation.
- Keep user master key in self-custody boundary.

## Cryptographic boundaries

### Client side (trusted boundary)

- Secret plaintext creation/editing
- Master key generation and handling
- KDF execution from user credentials/passphrase inputs
- Encryption/decryption of vault payloads
- Computation of deterministic `vault_state_hash`

### Server side (untrusted for confidentiality)

- Receives and stores ciphertext only
- Stores commitment metadata (`ciphertext_hash`, `vault_state_hash`, version)
- Never receives plaintext master key

## Draft primitive roles (selection unresolved)

- **KDF**: derive encryption keys from user material (Argon2id preferred candidate; unresolved)
- **AEAD**: encrypt blob payload and provide integrity (AES-GCM or XChaCha20-Poly1305 unresolved)
- **Hash**: content addressing and state commitment (exact algorithm profile unresolved)

## Required invariants

1. Same logical vault state must produce same canonical input bytes for hashing.
2. Different versions must have non-ambiguous sequence ordering.
3. Ciphertext tampering must be detected before plaintext use.
4. Server compromise must not reveal plaintext secrets without user key material.

## Minimal canonical hash input (current draft)

`vault_state_hash = H(canonical(vault_id, version, ciphertext_hash, parent_hash?))`

Canonicalization format choice is tracked in `docs/open-decisions.md`.

## Out-of-scope in this pass

- Production key storage implementation
- Recovery key protocol
- Hardware-bound key integration
- Formal cryptographic proof artifacts
