# Phase 1 Deterministic-Core Implementation Plan

## Scope lock (what Phase 1 includes)

1. Canonical encoding.
2. State hashing.
3. Parent-hash version chaining.
4. Argon2id configuration policy validation.
5. XChaCha20-Poly1305 envelope format planning (spec-only, not runtime encryption).

## Out of scope lock (must not be implemented in Phase 1)

- Auth runtime.
- Storage backend.
- Blob service integration.
- Blockchain writes.
- Database integration.
- Export/import runtime.
- UI/client surfaces.

## Deterministic module boundaries

### M1. `canonical_manifest`
Responsibility: normalize manifest input into deterministic canonical bytes.

### M2. `state_hash`
Responsibility: compute deterministic hashes from canonical bytes and produce hash IDs.

### M3. `version_chain`
Responsibility: enforce parent-hash + monotonic-version continuity rules.

### M4. `argon2id_policy`
Responsibility: validate Argon2id parameter profiles against frozen policy.

### M5. `envelope_format_spec`
Responsibility: define XChaCha20-Poly1305 envelope schema and validation constraints (format only).

### M6. `deterministic_vectors`
Responsibility: load and evaluate canonical test vectors and failure fixtures.

## Exact interface definitions (proposed)

### M1: `canonical_manifest`
- `canonicalize_manifest(manifest: Mapping[str, Any]) -> bytes`
- `validate_manifest_schema(manifest: Mapping[str, Any]) -> ValidationResult`

### M2: `state_hash`
- `compute_manifest_hash(canonical_bytes: bytes) -> str`
- `compute_state_hash(manifest: Mapping[str, Any]) -> str`
- `hash_algorithm_id() -> str`

### M3: `version_chain`
- `build_chain_node(version: int, manifest_hash: str, parent_hash: str | None) -> ChainNode`
- `validate_chain_transition(prev: ChainNode | None, curr: ChainNode) -> ValidationResult`
- `verify_chain(nodes: Sequence[ChainNode]) -> ValidationResult`

### M4: `argon2id_policy`
- `validate_argon2id_params(params: Argon2idParams) -> ValidationResult`
- `get_default_argon2id_profile() -> Argon2idParams`
- `profile_id(params: Argon2idParams) -> str`

### M5: `envelope_format_spec`
- `validate_envelope_header(header: EnvelopeHeader) -> ValidationResult`
- `envelope_version_id() -> str`
- `required_envelope_fields() -> Sequence[str]`

### M6: `deterministic_vectors`
- `load_vector_set(name: str) -> list[TestVector]`
- `run_vector_suite(name: str) -> VectorRunResult`
- `list_vector_categories() -> Sequence[str]`

## Deterministic data flow (exact order)

1. Input manifest received by deterministic core.
2. `validate_manifest_schema()` checks required fields and types.
3. `canonicalize_manifest()` emits canonical bytes (JCS).
4. `compute_manifest_hash()` computes manifest hash.
5. `build_chain_node()` composes `(version, manifest_hash, parent_hash)`.
6. `validate_chain_transition()` or `verify_chain()` enforces continuity.
7. Optional: envelope header planning validated via `validate_envelope_header()`.
8. Vector runner verifies determinism/failure behavior against fixtures.

## Exact invariants

1. Same semantic manifest input must produce identical canonical bytes.
2. Same canonical bytes must produce identical manifest hash.
3. Any manifest mutation must change resulting manifest hash (collision-resistance assumption).
4. Version must be strictly monotonic (`curr.version = prev.version + 1`).
5. `curr.parent_hash` must equal `prev.manifest_hash` for non-genesis transitions.
6. Genesis node must have `version=1` and `parent_hash=None`.
7. Argon2id params must satisfy minimum policy thresholds.
8. Envelope header must include required fields and supported version identifier.

## Exact failure cases to test

### Canonical encoding failures
- Missing required manifest fields.
- Type mismatches for required fields.
- Non-canonicalizable values.
- Unicode/escaping normalization mismatch expectation.

### State hashing failures
- Unsupported hash algorithm id.
- Invalid canonical byte input (empty/None when disallowed).
- Hash mismatch versus fixture expected output.

### Version-chain failures
- Non-monotonic version transition.
- Parent hash mismatch.
- Duplicate version with differing manifest hash (fork).
- Invalid genesis node (`version != 1` or non-null parent hash).

### Argon2id policy failures
- Memory cost below minimum.
- Time cost below minimum.
- Parallelism outside allowed range.
- Missing/unknown parameter profile fields.

### Envelope-format planning failures
- Missing required envelope header fields.
- Unsupported envelope version id.
- Invalid nonce/tag length metadata declarations.

## Phase 1 completion criteria (deterministic-core only)

- All invariants encoded as tests with passing deterministic vectors.
- All listed failure categories have explicit failing fixtures.
- No runtime coupling added to auth/storage/db/blockchain subsystems.
