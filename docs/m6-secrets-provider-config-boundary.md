# M6 — Secrets and Provider-Config Boundary Preparation

M6 prepares provider config and secret boundaries for future real adapters while keeping real execution disabled.

## Provider config contracts

Defined provider config objects:
- `BlobProviderConfig` (`backend`, `provider`, `bucket`, `region`, `endpoint_url`, `access_key_ref`, `secret_key_ref`)
- `AttestationProviderConfig` (`backend`, `rpc_url`, `chain_id`, `contract_address`, `signer_key_ref`)
- `ProviderConfigBoundary` containing both configs, secret source policy, execute-required field lists, validation, and redaction.

## Secret source policy

Allowed source policy is `env_ref` only.

Forbidden plaintext env keys:
- `BLOB_ACCESS_KEY`
- `BLOB_SECRET_KEY`
- `ATTESTATION_SIGNER_KEY`

If any forbidden plaintext key is present, startup/config validation fails.

## Redaction rules

`/v1/config` and `/v1/capabilities` only expose redacted provider config:
- raw secret values are never present
- `*_REF` fields are shown only as `<redacted:set>` when configured
- non-secret operational fields (e.g., `bucket`, `region`, `rpc_url`, `chain_id`) may be shown

## Startup validation rules

For real-like backends in dry-run mode, config completeness is required:
- blob backend != `in_memory` requires: `provider`, `bucket`, `region`
- attestation backend != `fake` requires: `rpc_url`, `chain_id`

Future execute-required fields are defined but execute remains forbidden by M5.1 policy.

## Remaining blockers before real execution

- real secret manager integration
- real provider clients (object storage + chain submission)
- auth and encryption runtime
- DB/distributed coordination
