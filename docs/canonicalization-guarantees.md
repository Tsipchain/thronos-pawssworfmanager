# Canonicalization Guarantees and Limitations (Current Implementation)

## Guarantees (implemented)

1. Deterministic JSON serialization uses sorted object keys.
2. Serialization removes insignificant whitespace.
3. UTF-8 output bytes are stable for identical Python object input.
4. Non-finite numeric values (`NaN`, `Infinity`, `-Infinity`) are rejected.
5. Required manifest schema fields are validated before serialization.

## Non-guarantees (explicit)

1. Full RFC 8785/JCS conformance is **not yet claimed** for every numeric normalization edge case.
2. Cross-language canonical parity is not guaranteed until dedicated cross-runtime fixtures are finalized.
3. Numeric rendering behavior depends on Python JSON encoder semantics for finite floats.

## Current schema guardrails

- `vault_id` must be a non-empty string.
- `version` must be an integer >= 1 and cannot be boolean.
- `entries` must be a list.

## Hardening follow-ups (future)

- Add explicit RFC 8785 conformance test corpus.
- Add cross-language fixture parity checks (at least one non-Python implementation).
- Lock numeric canonicalization policy into versioned protocol text.
