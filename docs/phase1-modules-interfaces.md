# Phase 1 Planned Modules and Interfaces

This is a planning document only. No runtime implementation is included in this pass.

## Module 1: `canonical_manifest`

### Responsibility
Produce deterministic canonical JSON bytes for vault manifest input.

### Planned interface
- `canonicalize_manifest(manifest: Mapping[str, Any]) -> bytes`
- `validate_manifest_schema(manifest: Mapping[str, Any]) -> ValidationResult`

## Module 2: `state_hash`

### Responsibility
Compute deterministic manifest/state hash from canonical bytes.

### Planned interface
- `compute_manifest_hash(canonical_bytes: bytes) -> str`
- `compute_state_hash(manifest: Mapping[str, Any]) -> str`

## Module 3: `version_chain`

### Responsibility
Enforce and verify parent-hash + monotonic-version continuity.

### Planned interface
- `build_chain_node(version: int, manifest_hash: str, parent_hash: str | None) -> ChainNode`
- `validate_chain_transition(prev: ChainNode | None, curr: ChainNode) -> ValidationResult`
- `verify_chain(nodes: Sequence[ChainNode]) -> ValidationResult`

## Module 4: `argon2id_policy`

### Responsibility
Validate Argon2id parameter profiles against frozen Phase 1 policy.

### Planned interface
- `validate_argon2id_params(params: Argon2idParams) -> ValidationResult`
- `get_default_argon2id_profile() -> Argon2idParams`
- `profile_id(params: Argon2idParams) -> str`

## Module 5: `test_vectors`

### Responsibility
Load/validate canonical test fixtures used by Phase 1 deterministic tests.

### Planned interface
- `load_vector_set(name: str) -> list[TestVector]`
- `run_vector_suite(name: str) -> VectorRunResult`

## Explicit non-interfaces for this phase planning pass

- No storage adapter interface.
- No auth interface.
- No API runtime handler interface.
- No blockchain writer interface.
