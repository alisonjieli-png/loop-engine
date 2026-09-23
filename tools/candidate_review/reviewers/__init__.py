"""The reviewer edge: one prompt and one call allowance in, one ``ReviewerAttempt`` out.

Every reviewer engine answers with the same shape, whatever it runs: a closed
outcome, the answer text (empty unless answered), the usage exactly as it was
reported (unknown stays unknown, never zero), the physical model calls when
known, the pause the provider asked for, the model that answered, and what was
called. The panel reads nothing else from an engine, so replacing an engine
never changes the panel.

Nothing here grants model, network, file, spending or external effect
authority. The panel decides whether a call may happen before it asks an
engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

ANSWERED = "answered"
RATE_LIMITED = "rate_limited"
USAGE_LIMIT_REACHED = "usage_limit_reached"
PROVIDER_UNAVAILABLE = "provider_unavailable"
TIMEOUT = "timeout"
AUTHENTICATION_UNAVAILABLE = "authentication_unavailable"
MODEL_NOT_FOUND = "model_not_found"
REFUSED_BY_ROUTE_POLICY = "refused_by_route_policy"
CONTEXT_WINDOW_EXCEEDED = "context_window_exceeded"
OUTPUT_LIMIT_REACHED = "output_limit_reached"
PROVIDER_FAILED = "provider_failed"
ENGINE_UNAVAILABLE = "engine_unavailable"
MODEL_IDENTITY_MISMATCH = "model_identity_mismatch"
ATTEMPT_OUTCOMES = (ANSWERED, RATE_LIMITED, USAGE_LIMIT_REACHED, PROVIDER_UNAVAILABLE, TIMEOUT,
                    AUTHENTICATION_UNAVAILABLE, MODEL_NOT_FOUND, REFUSED_BY_ROUTE_POLICY, CONTEXT_WINDOW_EXCEEDED,
                    OUTPUT_LIMIT_REACHED, PROVIDER_FAILED, ENGINE_UNAVAILABLE, MODEL_IDENTITY_MISMATCH)
#: Where a usage count came from. A provider's own report, a command line's own report, or nobody.
PROVIDER_REPORTED, COMMAND_LINE_REPORTED, USAGE_UNKNOWN = "provider_reported", "command_line_reported", "unknown"
USAGE_SOURCES = (PROVIDER_REPORTED, COMMAND_LINE_REPORTED, USAGE_UNKNOWN)


@dataclass(frozen=True)
class Usage:
    """Token usage as reported. A missing count is ``None``, which means unknown, never zero."""

    input_tokens: "int | None"
    output_tokens: "int | None"
    reasoning_output_tokens: "int | None" = None
    cached_input_tokens: "int | None" = None
    source: str = USAGE_UNKNOWN

    def __post_init__(self):
        for name in ("input_tokens", "output_tokens", "reasoning_output_tokens", "cached_input_tokens"):
            value = getattr(self, name)
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError(f"{name} is a whole number of zero or more, or unknown")
        if self.source not in USAGE_SOURCES:
            raise ValueError(f"usage source is one of {USAGE_SOURCES}")

    @property
    def complete(self) -> bool:
        return self.input_tokens is not None and self.output_tokens is not None

    @property
    def total(self) -> "int | None":
        return self.input_tokens + self.output_tokens if self.complete else None

    def to_dict(self) -> dict:
        return {"input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
                "reasoning_output_tokens": self.reasoning_output_tokens,
                "cached_input_tokens": self.cached_input_tokens, "source": self.source}


UNKNOWN_USAGE = Usage(None, None)


@dataclass(frozen=True)
class ReviewPrompt:
    """What one reviewer is sent: shared instructions as the system part, the item as the request."""

    system: str
    user: str
    sha256: str
    estimated_input_tokens: int
    identity: str = ""
    body_sha256: str = ""


@dataclass(frozen=True)
class CallAllowance:
    """The bounds of one call: the output allocation, the time allowed and the temperature."""

    max_output_tokens: int
    timeout_seconds: float
    temperature: float


@dataclass(frozen=True)
class Availability:
    """Whether an engine can be asked now, and if not, why, with a closed reason code."""

    available: bool
    reason: str
    engine_version: str
    model_version: Mapping = field(default_factory=dict)
    reason_code: str = ""


@dataclass(frozen=True)
class ReviewerAttempt:
    """One engine call as the panel sees it."""

    outcome: str
    text: str
    usage: Usage
    physical_model_calls: "int | None"
    elapsed_seconds: float
    retry_after_seconds: "float | None"
    reported_model: str
    route_or_command: str
    error_detail: str = ""
    physical_calls_basis: str = ""

    def __post_init__(self):
        if self.outcome not in ATTEMPT_OUTCOMES:
            raise ValueError(f"an attempt outcome is one of {ATTEMPT_OUTCOMES}")
        if self.outcome != ANSWERED and self.text:
            raise ValueError("only an answered attempt carries answer text")


@dataclass
class ReviewerContext:
    """What the panel hands every engine it builds. Every field is optional and read only by its engine kind."""

    provider_adapters: "Mapping | None" = None
    model_listing: "Mapping | None" = None
    fixture_scripts: "Mapping | None" = None


class ReviewerEngine(Protocol):
    """The small surface every reviewer engine implements.

    ``answer_format`` names how the engine's answers arrive (see ``verdicts``), and
    ``output_allocation_tokens`` is the engine's own output allocation, or None
    for the panel policy's."""

    installation: object
    answer_format: str
    output_allocation_tokens: "int | None"

    def availability(self) -> Availability: ...

    def review(self, prompt: ReviewPrompt, allowance: CallAllowance) -> ReviewerAttempt: ...


def failed(outcome: str, route_or_command: str, detail: str = "", *, physical_model_calls: "int | None" = 0,
           elapsed_seconds: float = 0.0, usage: Usage = UNKNOWN_USAGE, retry_after_seconds=None,
           reported_model: str = "") -> ReviewerAttempt:
    """An attempt that produced no answer, with what is known about it."""
    return ReviewerAttempt(outcome, "", usage, physical_model_calls, elapsed_seconds, retry_after_seconds,
                           reported_model, route_or_command, detail[:400])
