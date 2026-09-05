"""Shared scalar and sequence validation for passive stage evidence records.

This module validates values only and owns no execution or storage authority.
"""
from __future__ import annotations

from collections.abc import Mapping


class StageEvidenceContractError(ValueError):
    """A stage evidence record is malformed or internally inconsistent."""


def unique_texts(values: object, name: str) -> tuple[str, ...]:
    """Validate a direct sequence of unique, trimmed, non-empty strings."""
    if isinstance(values, (str, bytes)):
        raise StageEvidenceContractError(
            f"{name} must be a sequence of strings, not one string")
    try:
        result = tuple(values or ())  # type: ignore[arg-type]
    except TypeError as exc:
        raise StageEvidenceContractError(
            f"{name} must be a sequence of strings") from exc
    if any(not isinstance(item, str) or not item.strip() for item in result):
        raise StageEvidenceContractError(
            f"{name} must contain only non-empty strings")
    if any(item != item.strip() for item in result):
        raise StageEvidenceContractError(
            f"{name} values must not have surrounding whitespace")
    if len(result) != len(set(result)):
        raise StageEvidenceContractError(
            f"{name} must contain unique references")
    return result


def stored_texts(values: object, name: str) -> tuple[str, ...]:
    """Read a serialized sequence without turning one string into characters."""
    if isinstance(values, (str, bytes, Mapping)):
        raise StageEvidenceContractError(
            f"{name} must be a JSON array of strings")
    try:
        return unique_texts(tuple(values or ()), name)  # type: ignore[arg-type]
    except TypeError as exc:
        raise StageEvidenceContractError(
            f"{name} must be a JSON array of strings") from exc


__all__ = ("StageEvidenceContractError", "stored_texts", "unique_texts")
