"""Budget the night, not the call.

Every timeout in the first version of this system was a number I picked:
900 seconds for a step, 600 for a gate, 880 for the whole run. All three
were wrong in the same way. An overnight run has twelve hours; capping one
step at fifteen minutes does not protect the night, it just decides in
advance that a step which needs sixteen fails. And a run killed at its
outer cap explains nothing about which step was slow.

What actually needs protecting is the WHOLE night, and only against one
thing: a single step consuming all of it. So the budget is stated once, in
hours, and each step is granted a share of what REMAINS. Nothing carries a
fixed second-count.

Two properties follow, and both matter more than the numbers:

  * As the night runs down, grants shrink. The last steps do not get the
    same generous allowance as the first, so a slow tail cannot overrun
    morning.
  * A grant is always reported with its reason. "This step may take 42
    minutes because 5.6 hours remain and 8 steps are expected" is a
    sentence a person can disagree with. "timeout=900" is not.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

#: A night. Overridable, but this is what "overnight" means by default:
#: leave at 6pm, read the report at 8am.
DEFAULT_NIGHT_HOURS = 12.0

#: No step is granted less than this, however little of the night is left.
#: Below about a minute a model call cannot finish at all, so a smaller
#: grant does not ration the night, it just guarantees a failure and burns
#: the call anyway.
MINIMUM_GRANT_SECONDS = 90.0

#: No single step may take more than this share of what remains, however
#: few steps are expected. One step is never worth the entire rest of the
#: night, because a run with nothing left cannot report what it observed.
MAXIMUM_REMAINING_SHARE = 0.5


class NightBudgetError(RuntimeError):
    """The night is spent, or a budget was asked for something impossible."""


@dataclass
class NightBudget:
    """Wall-clock budget for one overnight run."""

    hours: float = DEFAULT_NIGHT_HOURS
    started: float = field(default_factory=time.monotonic)
    #: What the run still expects to do. Grants divide the remaining time
    #: by this, so a run that discovers more work automatically gets more
    #: conservative rather than overrunning.
    expected_steps: int = 8
    _spent: dict = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.hours <= 0:
            raise NightBudgetError("a night budget must be positive hours")
        if self.expected_steps < 1:
            raise NightBudgetError("expected_steps must be at least 1")

    @property
    def total_seconds(self) -> float:
        return self.hours * 3600.0

    def elapsed(self) -> float:
        return time.monotonic() - self.started

    def remaining(self) -> float:
        return max(0.0, self.total_seconds - self.elapsed())

    def exhausted(self) -> bool:
        return self.remaining() <= MINIMUM_GRANT_SECONDS

    def grant(self, label: str = "step", *, steps_left: int = 0) -> float:
        """Seconds this step may take, derived from what the night has left."""
        remaining = self.remaining()
        if remaining <= 0:
            raise NightBudgetError(
                f"the night is spent; {label} cannot start. "
                f"{self.hours:.1f}h budget, {self.elapsed() / 3600:.1f}h used")
        divisor = max(1, steps_left or self.expected_steps)
        share = remaining / divisor
        capped = min(share, remaining * MAXIMUM_REMAINING_SHARE)
        return max(MINIMUM_GRANT_SECONDS, capped)

    def explain(self, label: str = "step", *, steps_left: int = 0) -> str:
        """The grant as a sentence someone can disagree with."""
        seconds = self.grant(label, steps_left=steps_left)
        divisor = max(1, steps_left or self.expected_steps)
        return (f"{label} may take {seconds / 60:.0f} min: "
                f"{self.remaining() / 3600:.1f}h of a {self.hours:.0f}h night "
                f"remains, {divisor} step(s) expected")

    def record(self, label: str, seconds: float) -> None:
        self._spent[label] = round(self._spent.get(label, 0.0) + seconds, 1)

    def spent(self) -> dict:
        """Where the night actually went, for the morning report."""
        return dict(sorted(self._spent.items(), key=lambda kv: -kv[1]))


def self_test() -> dict:
    """Prove grants shrink, floors hold, and nothing is a magic number."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    budget = NightBudget(hours=12.0, expected_steps=8)
    first = budget.grant("orient")
    check("a_fresh_night_grants_generously",
          first > 1800, f"{first / 60:.0f} min for the first of 8 steps")
    check("no_grant_exceeds_half_of_what_remains",
          first <= budget.remaining() * MAXIMUM_REMAINING_SHARE + 1,
          "one step is never worth the whole rest of the night")

    # Grants shrink as the night runs down.
    late = NightBudget(hours=12.0, expected_steps=8)
    late.started = time.monotonic() - 11.5 * 3600
    late_grant = late.grant("verify")
    check("grants_shrink_as_the_night_runs_down",
          late_grant < first, f"{late_grant / 60:.0f} min vs {first / 60:.0f}")
    check("a_grant_never_drops_below_a_usable_floor",
          late_grant >= MINIMUM_GRANT_SECONDS,
          "below a minute a call cannot finish, so a smaller grant only "
          "guarantees a failure and burns the call")

    spent = NightBudget(hours=12.0)
    spent.started = time.monotonic() - 12.5 * 3600
    check("an_exhausted_night_says_so", spent.exhausted())
    try:
        spent.grant("implement")
        check("an_exhausted_night_refuses_a_new_step", False)
    except NightBudgetError as exc:
        check("an_exhausted_night_refuses_a_new_step",
              "night is spent" in str(exc), str(exc)[:100])

    check("a_grant_explains_itself",
          "of a 12h night remains" in budget.explain("implement"),
          budget.explain("implement"))

    more = NightBudget(hours=12.0, expected_steps=8)
    check("discovering_more_work_makes_grants_smaller_not_longer",
          more.grant("x", steps_left=40) < more.grant("x", steps_left=4))

    budget.record("implement", 120.5)
    budget.record("implement", 60.0)
    budget.record("orient", 9.0)
    check("spending_is_recorded_for_the_morning_report",
          budget.spent() == {"implement": 180.5, "orient": 9.0},
          str(budget.spent()))

    for bad, why in ((dict(hours=0), "zero hours"),
                     (dict(expected_steps=0), "zero steps")):
        try:
            NightBudget(**bad)
            check(f"refuses_{why.replace(' ', '_')}", False)
        except NightBudgetError:
            check(f"refuses_{why.replace(' ', '_')}", True)

    return {"module": "core.night_budget", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
