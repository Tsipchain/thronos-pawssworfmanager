# M4 — Real Adapter Boundary Preparation (No Sensitive Runtime Enablement)

This document defines the contract surface required before any real persistence or attestation backend is enabled.

## 1) Adapter configuration contracts

Configuration is explicit and fail-closed via allowlist-only backend selection:

- `MANIFEST_STORE_BACKEND` -> allowed: `in_memory`
- `ATTESTATION_BACKEND` -> allowed: `fake`
- `IDENTITY_BACKEND` -> allowed: `static`

Unsupported values are rejected with deterministic startup/config errors.

## 2) Backend selection rules

Selection mode is `allowlist` and `fail_closed=true`.
No fallback to unknown providers is allowed.

## 3) Persistence receipt schema

`PersistenceReceipt` contract fields:

- `operation` (`manifest_persist`)
- `status` (`created|duplicate` on success)
- `backend`
- `manifest_hash`
- `attempts`
- `max_attempts`
- `retryable` (false for successful writes)
- `failure_class` (`None` on success)
- `idempotency_scope` (`single_instance_memory`)

## 4) Attestation receipt schema

`AttestationReceipt` contract fields:

- `operation` (`attestation_submit`)
- `status` (`confirmed` on success)
- `backend`
- `attestation_id`
- `attempts`
- `max_attempts`
- `retryable` (false for success)
- `failure_class` (`None` on success)

## 5) Retry / failure semantics

Failure classes are normalized to:

- `transient` -> currently timeout/network category
- `permanent` -> currently input/type/category errors
- `unknown` -> any other exception

`retryable` is policy-driven. Current policy defaults to one attempt (`max_attempts=1`) and optional retries for transient classes when configured.

## 6) Idempotency assumptions and limits

Idempotency scope is explicitly declared as `single_instance_memory`.
This only guarantees duplicate suppression per-process in-memory state; it is not a distributed guarantee.

## 7) Non-goals (still disabled in M4)

- Real blob backend
- Real encryption runtime
- Real blockchain writes
- Auth
- Database integration
- Distributed coordination
