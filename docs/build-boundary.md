# Build Boundary (What to Build vs Not Build Yet)

## Build in upcoming implementation phases

- Deterministic data contracts for ciphertext metadata and version commitments
- API contract skeleton enforcing non-plaintext payload boundaries
- Internal domain models for vault versions and attestation status lifecycle
- Test harness for canonicalization and version progression invariants

## Explicitly do NOT build yet

- UI interfaces (web/mobile/extension)
- Password UX features
- Real blob/object storage integration
- Real blockchain write path
- Real authentication/authorization stack
- Sharing and recovery protocols

## Acceptance boundary for implementation readiness

Repository is considered implementation-ready when:

1. docs define cryptographic and attestation invariants clearly,
2. open decisions are tracked in matrix form with owners/phases,
3. phased plan exists with non-goal guardrails,
4. scaffold code remains minimal and does not violate trust boundaries.

## Guardrails for contributors

- Never introduce plaintext secret persistence in server models.
- Never introduce on-chain secret storage fields.
- Any new endpoint draft must state confidentiality boundary explicitly.
- Any design change touching trust assumptions must update threat/crypto docs in same PR.
