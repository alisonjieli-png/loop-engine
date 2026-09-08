"""Injected step failures, so the failure-handling family has something to survive.

A recovery policy that is never shown a failure cannot be compared with any
other. These produce failures in the shapes that actually occur: one that goes
away on its own, one that never does, one that arrives without warning at a
rate, and one that is not an exception at all but a reply that does not parse.

The last shape matters most and is the one people forget. A step that raises
is easy to see. A step that returns confident nonsense looks like success.
"""
from __future__ import annotations

import random

from port import fixture_reply


class StepFailed(RuntimeError):
    """A step did not produce a usable reply."""


def transient(clears_after: int = 2):
    """Fails the first few attempts at each unit, then works. Retry wins."""
    seen: dict = {}

    def evaluate(prompt: str) -> str:
        key = _unit(prompt)
        seen[key] = seen.get(key, 0) + 1
        if seen[key] <= clears_after:
            raise StepFailed(f"transient failure {seen[key]} on {key}")
        return fixture_reply(prompt)
    return evaluate


def permanent(at_unit: int = 5):
    """One unit never succeeds, however many times it is tried."""
    def evaluate(prompt: str) -> str:
        if _unit(prompt) == at_unit:
            raise StepFailed(f"unit {at_unit} is permanently broken")
        return fixture_reply(prompt)
    return evaluate


def flaky(rate: float = 0.3, seed: int = 5):
    """Fails at a rate, with no pattern. Deterministic under the seed."""
    rng = random.Random(seed)

    def evaluate(prompt: str) -> str:
        if rng.random() < rate:
            raise StepFailed("flaky failure")
        return fixture_reply(prompt)
    return evaluate


def unparseable(at_unit: int = 5, clears_after: int = 2):
    """Returns prose instead of a reply. Not an exception; looks like success.

    A policy that only catches exceptions treats this as a completed step and
    carries on with nothing, which is how a run ends up confidently missing
    part of its work.
    """
    seen: dict = {}

    def evaluate(prompt: str) -> str:
        unit = _unit(prompt)
        if unit != at_unit:
            return fixture_reply(prompt)
        seen[unit] = seen.get(unit, 0) + 1
        if seen[unit] <= clears_after:
            return "I had some trouble with that one, let me think again."
        return fixture_reply(prompt)
    return evaluate


def _unit(prompt: str) -> int:
    """Which unit this prompt is about, from the remaining count."""
    import re
    match = re.search(r"REMAINING_COUNT\s*=\s*(\d+)", prompt)
    return int(match.group(1)) if match else -1


def needs_escalation(at_unit: int = 5):
    """Fails until the prompt says it was escalated, then works.

    This is the shape that separates retrying from escalating. Sending the
    same insufficient prompt again cannot fix it however many times you try,
    and a policy that only retries will spend its whole budget discovering
    that. Something about the request has to change.
    """
    def evaluate(prompt: str) -> str:
        if _unit(prompt) == at_unit and "ESCALATED = true" not in prompt:
            raise StepFailed(f"unit {at_unit} needs a stronger request")
        return fixture_reply(prompt)
    return evaluate


SHAPES = {
    "transient": transient,
    "permanent": permanent,
    "flaky": flaky,
    "unparseable": unparseable,
    "needs_escalation": needs_escalation,
}
#: A policy that recovers from these is doing its job.
RECOVERABLE = ("transient", "flaky", "unparseable", "needs_escalation")
#: Nothing recovers from this one. What separates the policies is whether
#: they say so, and how much they spend finding out.
UNRECOVERABLE = ("permanent",)


def self_check() -> None:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "shared"))

    probe = "REMAINING_COUNT = 5\nCARRIED = {}\nNEXT = none\n"
    clears = transient(clears_after=2)
    for attempt in (1, 2):
        try:
            clears(probe)
            raise AssertionError(f"attempt {attempt} should have failed")
        except StepFailed:
            pass
    assert clears(probe), "a transient failure must clear"

    never = permanent(at_unit=5)
    for _ in range(4):
        try:
            never(probe)
            raise AssertionError("a permanent failure must not clear")
        except StepFailed:
            pass
    assert never("REMAINING_COUNT = 4\nNEXT = none\n"), "only one unit breaks"

    quiet = unparseable(at_unit=5, clears_after=1)
    assert "trouble" in quiet(probe), "this shape must not raise"
    assert quiet(probe).startswith("{"), "and it must clear"
    stronger = needs_escalation(at_unit=5)
    try:
        stronger(probe)
        raise AssertionError("a plain request must fail this shape")
    except StepFailed:
        pass
    assert stronger(probe + "ESCALATED = true\n").startswith("{"), (
        "an escalated request must succeed where a plain one cannot")

    print(f"failure faults self-check: ok "
          f"({len(SHAPES)} shapes, {len(RECOVERABLE)} recoverable)")


if __name__ == "__main__":
    self_check()
