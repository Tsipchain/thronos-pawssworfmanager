# Phase 1 Test Vector Planning

## Canonical vector category index

1. Canonical encoding vectors.
2. State hashing vectors.
3. Parent-hash version chaining vectors.
4. Argon2id parameter validation vectors.
5. XChaCha20-Poly1305 envelope-format vectors (metadata-only).

## 1) Canonical encoding vectors (OD-01)

### Pass categories
- Key-order normalization cases.
- Unicode normalization and escaping cases.
- Numeric representation edge cases.
- Null/empty object/empty array cases.

### Failure categories
- Missing required manifest fields.
- Wrong field types.
- Non-canonicalizable value types.
- Fixture mismatch on expected canonical byte output.

## 2) State hashing vectors (OD-01 + OD-04)

### Pass categories
- Deterministic hash reproducibility for identical manifest.
- Sensitivity tests (single-field change flips hash).
- Genesis version hash computation cases.
- Cross-language reproducibility fixtures.

### Failure categories
- Invalid canonical byte input for hashing.
- Unsupported hash-algorithm identifier.
- Expected-hash mismatch against fixture set.

## 3) Parent-hash version chaining vectors (OD-04)

### Pass categories
- Valid linear chain (v1 -> v2 -> v3).
- Valid long-chain continuity checks.

### Failure categories
- Broken parent reference chain.
- Fork attempt with same version and differing parent/hash.
- Rollback attempt serving older head.
- Invalid genesis node constraints.

## 4) Argon2id parameter validation vectors (OD-03)

### Pass categories
- Minimum accepted parameter set.
- Boundary-value accepted parameter sets.
- Profile-version tagging compatibility checks.

### Failure categories
- Rejected weak-parameter set.
- Missing required parameter fields.
- Out-of-range memory/time/parallelism values.
- Unknown profile identifiers.

## 5) XChaCha20-Poly1305 envelope-format vectors (planning)

### Pass categories
- Required header fields present.
- Supported envelope version id.
- Valid declared nonce/tag length metadata.

### Failure categories
- Missing header fields.
- Unsupported envelope version id.
- Invalid nonce/tag length declarations.
