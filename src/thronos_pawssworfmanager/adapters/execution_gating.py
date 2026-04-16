"""Execution gating model for controlled real execution enablement."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ExecutionGateStatus:
    requested: bool
    execution_mode_is_execute: bool
    policy_allows: bool
    provider_config_complete: bool
    secrets_boundary_satisfied: bool
    execution_ready: bool
    execution_enabled: bool
    denial_reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def evaluate_execution_gates(
    enable_real_execution: bool,
    execution_mode: str,
    policy_allows: bool,
    provider_config_complete: bool,
    secrets_boundary_satisfied: bool,
) -> ExecutionGateStatus:
    execution_mode_is_execute = execution_mode == "execute"
    denial_reasons: list[str] = []

    if not execution_mode_is_execute:
        denial_reasons.append("execution_mode_not_execute")
    if not policy_allows:
        denial_reasons.append("execution_policy_not_allowed")
    if not provider_config_complete:
        denial_reasons.append("provider_config_incomplete")
    if not secrets_boundary_satisfied:
        denial_reasons.append("secrets_boundary_unsatisfied")

    execution_ready = not denial_reasons
    execution_enabled = enable_real_execution and execution_ready

    if enable_real_execution and not execution_ready:
        denial_reasons.insert(0, "enable_requested_but_gates_failed")

    return ExecutionGateStatus(
        requested=enable_real_execution,
        execution_mode_is_execute=execution_mode_is_execute,
        policy_allows=policy_allows,
        provider_config_complete=provider_config_complete,
        secrets_boundary_satisfied=secrets_boundary_satisfied,
        execution_ready=execution_ready,
        execution_enabled=execution_enabled,
        denial_reasons=tuple(denial_reasons),
    )
