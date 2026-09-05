"""Pure normalization for provider-reported Run History token usage.

Missing, partial, positive, and real-zero observations remain distinct.
"""
from __future__ import annotations


def optional_token(value: object) -> int | None:
    """Accept an exact non-negative count; absence never becomes zero."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def normalized_model_usage(source: dict) -> dict:
    """Return the versioned positive, partial, zero, or unknown usage fields."""
    prompt = optional_token(source.get("prompt_tokens"))
    output = optional_token(source.get("eval_tokens"))
    total = optional_token(source.get("total_tokens"))
    known = sum(item is not None for item in (prompt, output, total))
    return {
        "prompt_tokens": prompt,
        "eval_tokens": output,
        "total_tokens": total,
        "accounting_complete": prompt is not None and output is not None,
        "usage_state": (
            "unknown" if known == 0 else
            "complete" if known == 3 else "partial"),
        "usage_record_type": "model_usage/v2",
    }


def apply_model_usage(target: dict, source: dict) -> None:
    """Attach normalized usage to one pending Run History event mapping."""
    usage = normalized_model_usage(source)
    target["prompt_tokens"] = usage["prompt_tokens"]
    target["eval_tokens"] = usage["eval_tokens"]
    target["detail"].update(usage)


def prepare_model_event(target: dict) -> None:
    """Make direct model-event omission explicit before event construction."""
    detail = dict(target.get("detail") or {})
    target["detail"] = detail
    apply_model_usage(target, {
        "prompt_tokens": target.get("prompt_tokens"),
        "eval_tokens": target.get("eval_tokens"),
        "total_tokens": detail.get("total_tokens"),
    })


__all__ = (
    "apply_model_usage", "normalized_model_usage", "optional_token",
    "prepare_model_event")
