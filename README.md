# Thronos Pawssworf Manager

Thronos Pawssworf Manager is an implementation-focused foundation for a service that is both:

1. a **self-custody encrypted vault**, and
2. a **Thronos-native secret attestation service**.

This repository is intentionally in a design/foundation stage. It does **not** ship end-user features yet.

## Product purpose

Provide a backend protocol/service boundary where users can persist encrypted vault state off-chain while anchoring deterministic integrity/version commitments on Thronos, so clients can independently verify tamper evidence without exposing plaintext secrets.

## Trust model

- **Client is cryptographic trust anchor** for plaintext handling and key operations.
- **Server is untrusted for confidentiality** and trusted only for availability/integrity workflow execution.
- **Thronos chain is integrity witness**, not a secrets datastore.
- **Operators and infrastructure may see metadata** (timing, size, vault identifiers) but must never see plaintext secrets or plaintext master keys.

## Self-custody model

- Master key generation and plaintext handling happen client-side.
- Master key plaintext never leaves the user side.
- Server receives ciphertext and commitment metadata only.
- Any future recovery or multi-device portability must preserve user key sovereignty (currently unresolved and out of scope for implementation).

## Off-chain vs on-chain boundaries

### Off-chain (service-controlled storage)

- Encrypted vault blobs (opaque ciphertext)
- Blob metadata and version index
- Attestation job status / tx linkage
- Audit metadata (non-secret)

### On-chain (Thronos attestations only)

- `vault_id` reference (opaque)
- `vault_state_hash` commitment
- Version/sequence commitment
- Attestation transaction metadata

### Explicitly never on-chain

- Plaintext passwords or secrets
- Raw decrypted vault entries
- User master keys
- Decryption-enabling plaintext material

## Non-goals

This pass and current scope explicitly exclude:

- UI (web, desktop, mobile)
- Browser extension
- Mobile app
- Password-generation UX and convenience features
- Secret sharing/collaboration flows
- Recovery implementation
- Storage engine implementation details
- Blockchain write logic implementation
- Authentication/authorization implementation
- Marketing claims

## Foundation documents

- `docs/architecture.md`
- `docs/threat-model.md`
- `docs/data-model.md`
- `docs/api-draft.md`
- `docs/crypto-model.md`
- `docs/attestation-model.md`
- `docs/build-boundary.md`
- `docs/open-decisions.md`
- `docs/implementation-plan.md`

## Current status

The repository is prepared for disciplined implementation planning and sequencing, not full product delivery.
