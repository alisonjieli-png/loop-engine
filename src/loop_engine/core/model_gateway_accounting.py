"""Pure accounting helpers for provider-neutral model gateway results.

These functions distinguish physical attempts from effect-free preflight rows
and preserve missing provider usage as unknown. They own no routing or budget
authority and perform no model call.
"""
from __future__ import annotations


def reported_token(value: object) -> int | None:
    """Keep a provider count exact; malformed or missing never becomes zero."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def complete_attempt_sum(attempts, field_name: str) -> int | None:
    """Sum one usage field only across complete physical provider attempts."""
    physical = tuple(attempt for attempt in attempts if attempt.loop_id)
    values = tuple(getattr(attempt, field_name, None) for attempt in physical)
    if not values or any(value is None for value in values):
        return None
    return sum(values)


__all__ = ("complete_attempt_sum", "reported_token")
