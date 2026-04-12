# Phase 1 Test Vector Planning

## 1) Canonical encoding vectors (OD-01)

### Categories
- Key-order normalization cases.
- Unicode normalization and escaping cases.
- Numeric representation edge cases.
- Null/empty object/empty array cases.

### Expected assertions
- Canonical byte output is deterministic for semantically equivalent input.
- Non-equivalent manifests produce different canonical byte streams.

## 2) State hashing vectors (OD-01 + OD-04)

### Categories
- Deterministic hash reproducibility for identical manifest.
- Sensitivity tests (single-field change flips hash).
- Genesis version hash computation cases.
- Cross-language reproducibility fixtures.

### Expected assertions
- Same canonical bytes => same hash.
- Any manifest delta => different hash with high probability.

## 3) Parent-hash version chaining vectors (OD-04)

### Categories
- Valid linear chain (v1 -> v2 -> v3).
- Broken parent reference chain.
- Fork attempt with same version and differing parent/hash.
- Rollback attempt serving older head.

### Expected assertions
- Valid chain verifies end-to-end.
- Broken/forked/rollback chains fail verification deterministically.

## 4) Argon2id parameter validation vectors (OD-03)

### Categories
- Minimum accepted parameter set.
- Rejected weak-parameter set.
- Boundary-value parameter sets (time/memory/parallelism).
- Profile-version tagging and compatibility checks.

### Expected assertions
- Policy-compliant parameter sets are accepted.
- Non-compliant sets are rejected with explicit reason codes.
