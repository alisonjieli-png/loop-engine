"""Small shared validators for adaptive Practitioner semantic records.

These functions validate bounded model-returned text and route values. They do
not interpret tasks, select capabilities, grant authority, or execute work.
"""
from __future__ import annotations


MODEL_ROUTE_VALUES = (
    "stop_success", "continue", "retry", "repair", "explore_branch",
    "reframe", "soft_reset", "cold_restart", "stop_unprofitable")


def _short_text(value: object, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(
            f"{label} must be non-empty text of at most {maximum} characters")
    return value.strip()


def _short_strings(
        value: object, label: str, maximum: int = 30) -> tuple[str, ...]:
    if (not isinstance(value, list) or len(value) > maximum
            or any(not isinstance(item, str) or not item.strip()
                   or len(item) > 500 for item in value)):
        raise ValueError(
            f"{label} must be an array of at most {maximum} short strings")
    return tuple(item.strip() for item in value)
