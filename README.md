# Thronos Pawssworf Manager

Security-first greenfield service for:

1. **Self-custody encrypted vault storage**
2. **Thronos-native secret attestation**

This repository currently contains only architecture and API drafts plus a minimal service scaffold. It does **not** implement full product functionality.

## Purpose

Build a backend service that accepts and stores **encrypted vault blobs** off-chain while anchoring a **deterministic integrity hash** of vault state on Thronos for tamper evidence and version attestation.

## Non-goals (for this phase and initial product scope)

- UI implementation (web/mobile/browser extension)
- Password UX features (generator, autofill, convenience flows)
- Secret sharing / team collaboration
- Account recovery implementation
- Storing plaintext secrets server-side
- Storing passwords or raw secrets on-chain
- Marketing or comparative security claims

## Trust model

- User devices are trusted to generate and hold plaintext secrets and key material.
- The service is treated as an **untrusted ciphertext host** plus attestation relay.
- Thronos chain is treated as a public integrity ledger for state commitments, not secret storage.
- Operators may observe metadata (timestamps, object sizes, vault identifiers) but cannot decrypt payloads without user-controlled keys.

## Encryption model

- Encryption/decryption happens client-side.
- **Master key never leaves user side in plaintext.**
- Server stores only encrypted blobs and non-sensitive metadata.
- Envelope/key-derivation specifics remain open (see `docs/open-decisions.md`).

## Attestation model

- Each vault update produces a deterministic canonical vault state hash (`vault_state_hash`).
- Only integrity/version commitments are attested on-chain (e.g., hash, version, timestamp, actor id / key fingerprint).
- On-chain data enables tamper evidence and historical verification of committed states.

## Off-chain vs on-chain

### Off-chain (service storage)

- Encrypted vault blobs (ciphertext)
- Blob metadata (vault id, version, hash references, timestamps)
- Optional encrypted key-wrapping material (if enabled later)

### On-chain (Thronos attestation)

- `vault_id` reference
- `vault_state_hash` (deterministic commitment)
- `version` / monotonic sequence
- Attestation transaction metadata

### Never stored on-chain

- Plaintext passwords/secrets
- Raw decrypted vault entries
- User master keys

## Unresolved decisions

See `docs/open-decisions.md` for current design choices that remain intentionally unresolved.

## Repository layout (current)

- `docs/architecture.md`
- `docs/threat-model.md`
- `docs/data-model.md`
- `docs/api-draft.md`
- `docs/open-decisions.md`
- `.env.example`
- `src/thronos_pawssworfmanager/` (minimal scaffold only)
