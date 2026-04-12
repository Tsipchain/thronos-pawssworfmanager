# Open Design Decisions

1. **Canonical hash format**
   - JSON canonicalization (JCS) vs protobuf canonical bytes vs custom merkleized format.

2. **Cryptographic suite baseline**
   - AES-GCM vs XChaCha20-Poly1305 for blob encryption profile.
   - KDF choice and parameter policy (Argon2id vs scrypt/PBKDF2 compatibility mode).

3. **Version linkage model**
   - Simple monotonic version + hash.
   - Full hash-chain with parent commitment per version.

4. **Attestation write path**
   - Synchronous on request path vs async queue/worker with eventual confirmation.

5. **Identity and authorization binding**
   - Wallet-signature auth only vs hybrid auth with service-issued tokens.

6. **Metadata minimization strategy**
   - Whether to pad blob sizes and batch writes to reduce traffic analysis.

7. **Deletion semantics**
   - Hard delete ciphertext availability vs tombstone with retention guarantees.

8. **Multi-device key handling**
   - Client-managed export/import only vs optional encrypted key-wrapping artifacts.

9. **Attestation contract shape on Thronos**
   - Minimal event log vs stateful contract tracking latest committed version.

10. **Verification policy**
   - Server-provided verification only vs mandatory client independent verification routine.
