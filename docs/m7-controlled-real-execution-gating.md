# M7 — Controlled Real Execution (Gated)

M7 introduces a strict execution-gating contract for future real execution paths while keeping real execution disabled by default.

## Gating model

Execution uses explicit flag and gate checks:
- `ENABLE_REAL_EXECUTION` (default `false`)
- `execution_mode == execute`
- execution policy allows startup
- provider config is complete
- secrets boundary is satisfied

`execution_ready` means all gates pass.
`execution_enabled` means `execution_ready` **and** `ENABLE_REAL_EXECUTION=true`.

## Safety checks

- If `ENABLE_REAL_EXECUTION=true` and any gate fails, startup is refused (`real_execution_gate_denied:*`).
- Dry-run mode can never become execution-enabled.
- Capability and metadata reporting expose readiness/enabled status without exposing secrets.

## Reporting

- `/v1/capabilities` includes `execution_gates`, `execution_ready`, `execution_enabled`.
- `/v1/config` includes the same gate contract payload.
- `/v1/metadata` includes summary booleans for readiness and enabled state.

## Guarantees

- real execution is disabled by default
- partial gate satisfaction cannot enable execution
- explicit enable request still fails closed if any gate is unsatisfied

## Non-guarantees

- no real blob write implementation
- no real blockchain submission implementation
- no auth/encryption runtime
- no database/distributed coordination
