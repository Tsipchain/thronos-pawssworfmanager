"""Argon2id parameter policy validation (no key derivation runtime)."""

from __future__ import annotations

from .types import Argon2idParams, ValidationResult

_MIN_MEMORY_KIB = 64 * 1024
_MIN_TIME_COST = 3
_MIN_PARALLELISM = 1
_MAX_PARALLELISM = 8
_SUPPORTED_PROFILE = "argon2id-v1"


def get_default_argon2id_profile() -> Argon2idParams:
    return Argon2idParams(memory_kib=65536, time_cost=3, parallelism=1)


def profile_id(params: Argon2idParams) -> str:
    return params.profile_version


def validate_argon2id_params(params: Argon2idParams) -> ValidationResult:
    if params.profile_version != _SUPPORTED_PROFILE:
        return ValidationResult(False, "unknown_profile", "unsupported profile version")
    if params.memory_kib < _MIN_MEMORY_KIB:
        return ValidationResult(False, "memory_too_low", "memory_kib below minimum")
    if params.time_cost < _MIN_TIME_COST:
        return ValidationResult(False, "time_cost_too_low", "time_cost below minimum")
    if not (_MIN_PARALLELISM <= params.parallelism <= _MAX_PARALLELISM):
        return ValidationResult(False, "parallelism_out_of_range", "parallelism out of range")
    if params.salt_len < 16:
        return ValidationResult(False, "salt_len_too_low", "salt_len below minimum")
    if params.key_len < 16:
        return ValidationResult(False, "key_len_too_low", "key_len below minimum")
    return ValidationResult(True)
