# Architecture (Draft)

## Chosen architecture for initialization phase

A **stateless API service + object storage + Thronos attestation adapter**.

### Components

1. **Client cryptography boundary (outside this repo for now)**
   - Performs encryption/decryption locally.
   - Derives and manages master key material.
   - Produces deterministic canonical state representation for hashing.

2. **Vault API service (this repo, scaffold only)**
   - Accepts encrypted blob uploads.
   - Validates metadata and version progression.
   - Persists ciphertext + metadata off-chain.
   - Submits/records attestation commitments to Thronos.

3. **Off-chain blob storage**
   - Stores opaque ciphertext payloads.
   - Addressed by content hash and vault/version metadata.

4. **Metadata store**
   - Stores vault/version index, content hash references, attestation status.
   - No plaintext secret fields.

5. **Thronos attestation adapter**
   - Writes `vault_state_hash` commitments.
   - Tracks transaction id/finality status.

## Data flow (high-level)

1. Client prepares vault update locally.
2. Client encrypts vault content and computes deterministic `vault_state_hash`.
3. Client sends ciphertext + metadata to API.
4. API stores ciphertext off-chain and metadata in service DB.
5. API (or async worker) submits attestation of `vault_state_hash` to Thronos.
6. API returns version + attestation reference.

## Security boundaries

- Plaintext exists only on client side.
- Master key plaintext is client-side only.
- Server sees ciphertext, hashes, metadata, and signatures/authorization tokens.

## Minimal deployment profile

- One API process
- One relational metadata DB
- One object storage bucket
- One attestation worker loop

## Explicitly deferred

- Multi-region replication
- Advanced key management integrations (HSM/KMS policy variants)
- Recovery/social guardians
- Collaborative sharing
