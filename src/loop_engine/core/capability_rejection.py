"""Typed capability rejections: runtime-owned facts about a refused call.

Architectural role: the vocabulary a deterministic capability uses when it
refuses a model-proposed call. A rejection is passive typed data: the
capability that refused, one closed reason code, the arguments it refused,
the admitted alternatives it knows (bounded), and one runtime-authored repair
hint. The Practitioner records it on the result packet and hands it back to
the model as evidence, so the next decision is made from the runtime's exact
facts rather than from a prose reading of an error string. Nothing here
decides what the model should do next.

Why it exists: a live Kaggle run stalled for twenty passes because the model
re-read a plain-text path rejection as a type error and re-proposed the same
call. The text was exact; the type was missing. With the admitted values on
the rejection, the correct next call is a lookup, not a diagnosis.

Owns:
    - REJECTION_REASON_CODES, CapabilityRejection, CapabilityRejected.
    - bounded_admitted_values(): the one place the admitted list is capped.
    - rejection_from_exception(): the executor_error fallback and the walk
      up an exception chain to a typed rejection.

Does not own: which calls are admitted (each capability), the repeated
action fence (core.action_fence), or the packet projection
(core.practitioner_runtime_facts).
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json

from .adaptive_practitioner_records import AdaptivePractitionerError

#: Closed vocabulary. ``argument_not_admitted`` carries admitted values;
#: ``repeated_identical_failure`` is written only by the action fence.
REJECTION_REASON_CODES = (
    "argument_not_admitted", "argument_type_invalid", "precondition_missing",
    "permission_missing", "repeated_identical_failure", "executor_error")

#: Upper bound on admitted values carried by one rejection. The total is
#: always recorded so a truncated list is never mistaken for the whole set.
ADMITTED_VALUES_LIMIT = 64


def bounded_admitted_values(values, limit: int = ADMITTED_VALUES_LIMIT
                            ) -> tuple[tuple[str, ...], int]:
    """Return (sorted bounded values, total count) for one rejection."""
    ordered = sorted({str(item) for item in values if str(item).strip()})
    return tuple(ordered[:limit]), len(ordered)


@dataclass(frozen=True)
class CapabilityRejection:
    """One refused capability call, described by the runtime."""

    capability_ref: str
    reason_code: str
    message: str
    rejected_arguments: tuple[tuple[str, object], ...] = ()
    admitted_values: tuple[str, ...] = ()
    admitted_values_total: int = 0
    repair_hint: str = ""
    identical_failures: int = 0
    pass_number: int = 0

    def __post_init__(self) -> None:
        if not self.capability_ref.strip():
            raise ValueError("capability rejection needs a capability_ref")
        if self.reason_code not in REJECTION_REASON_CODES:
            raise ValueError(
                f"capability rejection reason_code must be one of "
                f"{REJECTION_REASON_CODES}")
        if not self.message.strip():
            raise ValueError("capability rejection needs a message")
        if len(self.admitted_values) > ADMITTED_VALUES_LIMIT:
            raise ValueError("capability rejection admitted_values exceed "
                             f"{ADMITTED_VALUES_LIMIT}; bound them first")
        if self.admitted_values_total < len(self.admitted_values):
            raise ValueError(
                "admitted_values_total cannot be below the values carried")

    @property
    def digest(self) -> str:
        payload = {"capability_ref": self.capability_ref,
                   "reason_code": self.reason_code,
                   "rejected_arguments": self.rejected_arguments}
        return hashlib.sha256(json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        ).encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "record_type": "capability_rejection/v1",
            "capability_ref": self.capability_ref,
            "reason_code": self.reason_code,
            "message": self.message,
            "rejected_arguments": {
                str(key): value for key, value in self.rejected_arguments},
            "admitted_values": list(self.admitted_values),
            "admitted_values_total": self.admitted_values_total,
            "admitted_values_truncated": (
                self.admitted_values_total > len(self.admitted_values)),
            "repair_hint": self.repair_hint,
            "identical_failures": self.identical_failures,
            "pass_number": self.pass_number,
            "digest": self.digest,
        }


class CapabilityRejected(AdaptivePractitionerError):
    """Raised by a capability that refuses a call; carries the typed record."""

    def __init__(self, rejection: CapabilityRejection) -> None:
        super().__init__(rejection.message)
        self.rejection = rejection


def find_rejection(exc: BaseException) -> CapabilityRejection | None:
    """Return the typed rejection anywhere in an exception chain."""
    seen = 0
    current: BaseException | None = exc
    while current is not None and seen < 16:
        if isinstance(current, CapabilityRejected):
            return current.rejection
        current = current.__cause__ or current.__context__
        seen += 1
    return None


def rejection_from_exception(capability_ref: str, exc: BaseException,
                             *, pass_number: int = 0) -> CapabilityRejection:
    """Typed view of any executor failure; exact when the chain carries one."""
    typed = find_rejection(exc)
    if typed is not None:
        return typed if typed.pass_number == pass_number else \
            CapabilityRejection(**{**typed.__dict__, "pass_number": pass_number})
    return CapabilityRejection(
        capability_ref, "executor_error",
        f"{type(exc).__name__}: {str(exc)[:500]}",
        repair_hint=("the executor failed; change the inputs or the "
                     "capability rather than repeating the identical call"),
        pass_number=pass_number)


def self_test() -> dict:
    """Prove the vocabulary is closed, bounded, and survives wrapping."""
    values, total = bounded_admitted_values(
        [f"data/file-{index:03d}.csv" for index in range(100)])
    rejection = CapabilityRejection(
        "core.source.inspect", "argument_not_admitted",
        "source inspection requested unknown paths ['/abs/dir']",
        rejected_arguments=(("paths", ("/abs/dir",)),),
        admitted_values=values, admitted_values_total=total,
        repair_hint="omit paths to receive the manifest")
    try:
        CapabilityRejection("x", "made_up", "m")
        closed = False
    except ValueError:
        closed = True
    try:
        raise RuntimeError("solution loop wrapper") from CapabilityRejected(
            rejection)
    except RuntimeError as exc:
        recovered = rejection_from_exception("core.source.inspect", exc,
                                             pass_number=4)
    fallback = rejection_from_exception("core.web.get", KeyError("boom"))
    record = rejection.to_dict()
    tests = [{
        "test": "reason_codes_are_a_closed_vocabulary",
        "passed": closed and rejection.reason_code in REJECTION_REASON_CODES,
        "detail": str(REJECTION_REASON_CODES),
    }, {
        "test": "admitted_values_are_bounded_and_the_total_is_kept",
        "passed": (len(values) == ADMITTED_VALUES_LIMIT and total == 100
                   and record["admitted_values_truncated"] is True),
        "detail": f"{len(values)} of {total}",
    }, {
        "test": "a_wrapped_rejection_is_recovered_with_the_pass_number",
        "passed": (recovered.reason_code == "argument_not_admitted"
                   and recovered.admitted_values == values
                   and recovered.pass_number == 4
                   and isinstance(CapabilityRejected(rejection),
                                  AdaptivePractitionerError)),
        "detail": recovered.digest[:12],
    }, {
        "test": "an_untyped_failure_becomes_an_executor_error_rejection",
        "passed": (fallback.reason_code == "executor_error"
                   and fallback.message.startswith("KeyError")
                   and fallback.repair_hint),
        "detail": fallback.message[:60],
    }]
    return {"module": "core.capability_rejection",
            "passed": all(item["passed"] for item in tests), "tests": tests}
