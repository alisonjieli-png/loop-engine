"""Small shared validators for adaptive Practitioner semantic records.

These functions validate bounded model-returned text and route values. They do
not interpret tasks, select capabilities, grant authority, or execute work.
"""
from __future__ import annotations


MODEL_ROUTE_VALUES = (
    "stop_success", "continue", "retry", "repair", "explore_branch",
    "reframe", "soft_reset", "cold_restart", "stop_unprofitable")


def _short_text(value: object, label: str,
                maximum: "int | None" = None) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    if maximum is not None and len(value) > maximum:
        raise ValueError(
            f"{label} must contain at most {maximum} characters")
    return value.strip()


def _short_strings(
        value: object, label: str, maximum: "int | None" = None,
        item_maximum: "int | None" = None) -> tuple[str, ...]:
    if (not isinstance(value, list)
            or any(not isinstance(item, str) or not item.strip()
                   for item in value)):
        raise ValueError(f"{label} must be an array of non-empty text")
    if maximum is not None and len(value) > maximum:
        raise ValueError(f"{label} must contain at most {maximum} items")
    if (item_maximum is not None
            and any(len(item) > item_maximum for item in value)):
        raise ValueError(
            f"{label} items must contain at most {item_maximum} characters")
    return tuple(item.strip() for item in value)
