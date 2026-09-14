"""Pure normalization for provider-reported Run History token usage.

Missing, partial, positive, and real-zero observations remain distinct.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenUsageTotals:
    """Provider observations with unknown totals and separate known subtotals."""

    observations: int = 0
    prompt_known: int = 0
    output_known: int = 0
    prompt_missing: int = 0
    output_missing: int = 0

    def __post_init__(self):
        for value in (self.observations, self.prompt_known, self.output_known,
                      self.prompt_missing, self.output_missing):
            if type(value) is not int or value < 0:
                raise ValueError("usage totals require nonnegative integer counts")
        if max(self.prompt_missing, self.output_missing) > self.observations:
            raise ValueError("missing usage cannot exceed observations")

    @property
    def prompt_tokens(self) -> int | None:
        return None if self.prompt_missing else self.prompt_known

    @property
    def eval_tokens(self) -> int | None:
        return None if self.output_missing else self.output_known

    @property
    def complete(self) -> bool:
        return not (self.prompt_missing or self.output_missing)

    @property
    def total_tokens(self) -> int | None:
        return self.known_subtotal if self.complete else None

    @property
    def known_subtotal(self) -> int:
        return self.prompt_known + self.output_known

    def __add__(self, other):
        if not isinstance(other, TokenUsageTotals):
            return NotImplemented
        return TokenUsageTotals(
            self.observations + other.observations,
            self.prompt_known + other.prompt_known,
            self.output_known + other.output_known,
            self.prompt_missing + other.prompt_missing,
            self.output_missing + other.output_missing)

    def to_dict(self) -> dict:
        return {"record_type": "provider_token_totals/v1",
                "observations": self.observations,
                "prompt_tokens": self.prompt_tokens, "eval_tokens": self.eval_tokens,
                "total_tokens": self.total_tokens,
                "known_prompt_tokens_subtotal": self.prompt_known,
                "known_eval_tokens_subtotal": self.output_known,
                "known_tokens_subtotal": self.known_subtotal,
                "observations_without_prompt_usage": self.prompt_missing,
                "observations_without_output_usage": self.output_missing,
                "accounting_complete": self.complete}


def total_model_usage(observations) -> TokenUsageTotals:
    """Sum selected model observations without estimating absent provider usage."""
    totals = TokenUsageTotals()
    for source in observations:
        prompt = optional_token(source.get("prompt_tokens"))
        output = optional_token(source.get("eval_tokens"))
        totals += TokenUsageTotals(1, prompt or 0, output or 0,
                                   int(prompt is None), int(output is None))
    return totals


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
    "prepare_model_event", "TokenUsageTotals", "total_model_usage")
