"""Retry/failure semantics for adapter boundary layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 1
    retryable_exceptions: tuple[type[Exception], ...] = (TimeoutError, ConnectionError)


def classify_failure(exc: Exception) -> str:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return "transient"
    if isinstance(exc, (ValueError, KeyError, TypeError)):
        return "permanent"
    return "unknown"


def is_retryable(exc: Exception, policy: RetryPolicy) -> bool:
    return isinstance(exc, policy.retryable_exceptions)
