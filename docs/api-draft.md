# API Draft (Non-final)

Base path: `/v1`

All mutating endpoints require authenticated caller context and vault ownership authorization.

## 1) Create vault

`POST /vaults`

Request:
- `owner_ref`
- optional client capability metadata

Response:
- `vault_id`
- `current_version=0`

## 2) Upload encrypted version

`POST /vaults/{vault_id}/versions`

Request:
- `expected_previous_version`
- `version`
- `ciphertext_blob` (or pre-signed upload reference)
- `ciphertext_hash`
- `vault_state_hash`

Behavior:
- Reject if version is non-monotonic.
- Persist ciphertext + metadata off-chain.
- Enqueue/perform Thronos attestation.

Response:
- `vault_id`
- `version`
- `attestation_status`
- `attestation_tx_id` (if available)

## 3) Get version metadata

`GET /vaults/{vault_id}/versions/{version}`

Response:
- `vault_id`
- `version`
- `blob_uri` (or temporary download link)
- `ciphertext_hash`
- `vault_state_hash`
- `attestation_record`

## 4) Verify latest attested state

`GET /vaults/{vault_id}/verify`

Response:
- `latest_version`
- `latest_vault_state_hash`
- `attested_tx_id`
- `attested_block_height`
- `verification_status`

## 5) List attestation history

`GET /vaults/{vault_id}/attestations`

Response:
- ordered list of (`version`, `vault_state_hash`, `tx_id`, `status`, `timestamp`)

## Error model (draft)

- `409_VERSION_CONFLICT`
- `422_HASH_MISMATCH`
- `401_UNAUTHORIZED`
- `403_FORBIDDEN`
- `503_ATTESTATION_UNAVAILABLE`

## Explicit exclusions

- Plaintext secret CRUD endpoints
- Password generation endpoints
- Sharing/recovery endpoints
