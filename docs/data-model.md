# Data Model (Draft)

## Design intent

Model only what is necessary to persist encrypted state off-chain and anchor integrity/version commitments on-chain.

## Entities

## 1) Vault

- `vault_id` (UUID/opaque id)
- `owner_ref` (pseudonymous owner reference)
- `current_version` (int64)
- `created_at`, `updated_at`

No plaintext secret fields are stored.

## 2) VaultBlobVersion

- `vault_id`
- `version` (monotonic integer)
- `blob_uri` (object storage path)
- `ciphertext_hash` (hash of raw encrypted blob)
- `vault_state_hash` (deterministic commitment produced client-side)
- `content_bytes`
- `created_at`

Unique key: (`vault_id`, `version`)

## 3) AttestationRecord

- `vault_id`
- `version`
- `vault_state_hash`
- `chain` (`thronos-mainnet` / `thronos-testnet`)
- `tx_id`
- `block_height` (nullable until confirmed)
- `status` (`pending|confirmed|failed`)
- `attested_at`

## 4) AuditEvent (metadata only)

- `event_id`
- `vault_id`
- `actor_ref`
- `action` (`create|update|attest|verify`)
- `result` (`ok|reject|error`)
- `created_at`

## Suggested canonicalization input (for client hash)

`vault_state_hash = H(canonical(vault_id, version, ciphertext_hash, parent_version_hash?))`

Exact canonicalization algorithm is unresolved and tracked in `docs/open-decisions.md`.

## Data retention principles

- Ciphertext and metadata retained per policy.
- No plaintext secret persistence.
- Soft-delete policy must preserve audit and attestation linkage when legally required.
