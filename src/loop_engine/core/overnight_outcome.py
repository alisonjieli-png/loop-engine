"""Grade a night's work on what the engineer actually gets from it.

A binary verified/not-verified verdict throws away most of the value. Of the
outcomes a night can reach, only one is "the gate is green" -- but several
of the others save an engineer real time, and one of them ("this does not
reproduce") saves more time than a fix would have.

The previous vocabulary had a black hole called ``attempted``, which meant
both "reproduced the failure, localised it to a function, and ruled out two
explanations" and "did nothing". Those are not the same morning.

THE LADDER
Ordered by what the engineer receives, not by how close the run came to
finishing:

  verified          the gate is green on a branch. Review and merge.
  negative_result   the premise is wrong -- the failure does not reproduce,
                    or the test expectation is wrong rather than the code.
                    Ranked second because it prevents work rather than doing
                    it, and prevented work is the cheapest work there is.
  cause_localised   the gate is still red, but there is a reproduction, a
                    named hypothesis, and the files it lives in. The
                    engineer starts from a diagnosis instead of a symptom.
  blocked_named     a specific missing thing -- a credential, a service, a
                    decision. Usually seconds to clear, and it could not
                    have been cleared at 3am.
  narrowed          a reproduction exists but no cause. Still worth having:
                    the flaky-or-real question is answered.
  no_progress       nothing usable. Say so plainly.
  already_green     the recorded failure no longer reproduces at all.
  skipped           the run declined to start, with a reason.

WHY THIS IS ENGINE-OWNED
Classification reads the structured state and the gate's exit code. It never
asks a step how well it did. A run that graded itself would grade itself
generously, and the whole product is a verdict someone trusts.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Ordered best-first. The order is the product claim: a night that ends at
#: `cause_localised` is a good night, not a failed one.
OUTCOME_ORDER = (
    "verified", "negative_result", "verified_by_test_change",
    "cause_localised", "blocked_named", "narrowed", "no_progress",
    "already_green", "skipped",
)

#: Path fragments that mark a file as a test rather than the thing under
#: test. Deliberately broad: a false positive costs a line in the report,
#: a false negative reports a weakened suite as a clean pass.
TEST_PATH_MARKERS = (
    "test_", "_test.", "/tests/", "tests/", "spec_", "_spec.",
    "/spec/", ".test.", ".spec.", "conftest.py", "__tests__",
)


def _only_tests_changed(files) -> bool:
    """True when every changed file looks like a test."""
    paths = [str(item) for item in (files or []) if str(item).strip()]
    if not paths:
        return False
    return all(any(marker in path for marker in TEST_PATH_MARKERS)
               for path in paths)

#: What the engineer receives, in their words rather than the system's.
OUTCOME_MEANING = {
    "verified": "the gate passes on a branch; review and merge",
    "verified_by_test_change": (
        "the gate passes, but ONLY test files changed -- read the diff "
        "before believing it"),
    "negative_result": "the premise is wrong, and that is the finding",
    "cause_localised": "a diagnosis to start from instead of a symptom",
    "blocked_named": "one specific thing to unblock, usually seconds",
    "narrowed": "a reproduction; the flaky-or-real question is answered",
    "no_progress": "nothing usable from this candidate",
    "already_green": "the recorded failure no longer reproduces",
    "skipped": "the run declined to start, and said why",
}

#: Whether a rung is worth an engineer's attention first thing.
ACTIONABLE = ("verified", "negative_result", "verified_by_test_change",
              "cause_localised", "blocked_named")


class OvernightOutcomeError(ValueError):
    """An outcome could not be graded from the evidence supplied."""


@dataclass(frozen=True)
class Outcome:
    """One candidate's result, and the evidence that graded it."""

    rung: str
    because: str
    evidence: dict

    def __post_init__(self) -> None:
        if self.rung not in OUTCOME_ORDER:
            raise OvernightOutcomeError(
                f"unknown outcome {self.rung!r}; the ladder is "
                f"{', '.join(OUTCOME_ORDER)}")

    @property
    def actionable(self) -> bool:
        return self.rung in ACTIONABLE

    @property
    def meaning(self) -> str:
        return OUTCOME_MEANING[self.rung]

    def to_dict(self) -> dict:
        return {"rung": self.rung, "because": self.because,
                "actionable": self.actionable, "meaning": self.meaning,
                "evidence": dict(self.evidence)}


def _has(state, name) -> bool:
    value = state.get(name) if state is not None else None
    if isinstance(value, (list, tuple)):
        return bool(value)
    return bool(str(value or "").strip())


def classify(*, gate_passed: bool, state=None, gate_before_failed: bool = True,
             skipped_reason: str = "") -> Outcome:
    """Grade one candidate from the gate and the run's structured state.

    Arguments are keyword-only because ``classify(True, state)`` reads as
    plausible in either order, and grading a night backwards is the kind of
    mistake that produces a confident wrong report.
    """
    if skipped_reason:
        return Outcome("skipped", skipped_reason, {})
    if not gate_before_failed:
        return Outcome(
            "already_green",
            "the gate passed before any work; the recorded failure no longer "
            "reproduces", {})
    if gate_passed:
        changed = (state.get("files_changed") if state is not None else []) or []
        if _only_tests_changed(changed):
            # An agent that can edit tests can make ANY gate green. That is
            # not a reason to forbid it -- a wrong test expectation is a
            # real defect and correcting it is a real fix -- but reporting
            # it as an ordinary pass hides the one thing a reviewer must
            # check. Found live: a run "fixed" a failing test by changing
            # `== 11` to `== 10` and reported plain `verified`. The
            # expectation genuinely was wrong, and the report still gave no
            # hint that the suite, not the code, had moved.
            return Outcome(
                "verified_by_test_change",
                "the gate passes, but every changed file is a test; the "
                "suite may have been weakened rather than the code fixed",
                {"files_changed": list(changed)})
        return Outcome(
            "verified", "the project's own gate exits zero on the branch",
            {"files_changed": list(changed)})

    if state is None:
        return Outcome("no_progress", "no state was recorded for this run", {})

    blocked = str(state.get("blocked_on") or "").strip()
    if blocked:
        return Outcome("blocked_named", blocked,
                       {"blocked_on": blocked,
                        "unknowns": state.get("unknowns") or []})

    # A negative result is a claim ABOUT the task, so it is only recognised
    # from an explicit statement in the state, never inferred from silence.
    observed = str(state.get("observed_failure") or "").lower()
    negative_markers = ("does not reproduce", "did not reproduce",
                        "no longer reproduces", "expectation is wrong",
                        "test is wrong", "test expects", "symptom did not occur")
    if any(marker in observed for marker in negative_markers):
        return Outcome(
            "negative_result",
            "the run found the premise wrong rather than the code",
            {"observed_failure": state.get("observed_failure")})

    reproduced = _has(state, "reproduction") or _has(state, "observed_failure")
    diagnosed = _has(state, "hypothesis") and (
        _has(state, "files_examined") or _has(state, "files_changed"))
    if reproduced and diagnosed:
        return Outcome(
            "cause_localised",
            "the gate is still red, but there is a reproduction and a named "
            "cause in named files",
            {"hypothesis": state.get("hypothesis"),
             "files_examined": state.get("files_examined") or [],
             "ruled_out": state.get("ruled_out") or []})
    if reproduced:
        return Outcome(
            "narrowed", "the failure was reproduced but not explained",
            {"observed_failure": state.get("observed_failure")})
    return Outcome(
        "no_progress",
        "nothing was reproduced, explained, or ruled out", {})


def rank(outcomes) -> list:
    """Best rung first, so a morning report leads with what is usable."""
    order = {rung: index for index, rung in enumerate(OUTCOME_ORDER)}
    return sorted(outcomes, key=lambda item: order[item.rung])


def summarise(outcomes) -> dict:
    """One line a person can read before coffee."""
    counts = {}
    for outcome in outcomes:
        counts[outcome.rung] = counts.get(outcome.rung, 0) + 1
    usable = sum(1 for item in outcomes if item.actionable)
    total = len(outcomes)
    if not total:
        headline = ("Nothing unresolved was observed. No work was invented "
                    "to fill the night.")
    elif usable:
        headline = (f"{usable} of {total} candidate(s) came back with "
                    "something you can act on this morning.")
    else:
        headline = (f"{total} candidate(s) attempted, none reached a usable "
                    "result. The failures are on their branches.")
    return {"headline": headline, "counts": counts,
            "actionable": usable, "total": total}


def self_test() -> dict:
    """Prove each rung is reachable and that grading never flatters."""
    tests = []

    def check(name, passed, detail=""):
        tests.append({"test": name, "passed": bool(passed),
                      "detail": str(detail)[:170]})

    from .step_state import StepState

    base = StepState.start("fix the gate", "pytest -q")

    green = classify(gate_passed=True, state=base)
    check("a_passing_gate_is_verified", green.rung == "verified"
          and green.actionable)

    already = classify(gate_passed=True, state=base, gate_before_failed=False)
    check("a_gate_green_before_work_is_not_a_win",
          already.rung == "already_green" and not already.actionable,
          "claiming credit for a failure that stopped reproducing would be "
          "the easiest way to fake a good night")

    blocked = classify(gate_passed=False, state=base.apply(
        {"blocked_on": "needs a database credential"}))
    check("a_named_blocker_is_actionable",
          blocked.rung == "blocked_named" and blocked.actionable
          and "credential" in blocked.because, blocked.because)

    negative = classify(gate_passed=False, state=base.apply(
        {"observed_failure": "Ran the command, exit 0; the reported symptom "
                             "did not occur"}))
    check("a_negative_result_outranks_a_partial_diagnosis",
          negative.rung == "negative_result"
          and OUTCOME_ORDER.index("negative_result")
          < OUTCOME_ORDER.index("cause_localised"),
          "prevented work is the cheapest work there is")

    localised = classify(gate_passed=False, state=base.apply(
        {"observed_failure": "TypeError in summarise",
         "hypothesis": "the denominator counts null rows",
         "files_examined": ["pipeline.py"]}))
    check("a_reproduction_plus_a_named_cause_is_a_diagnosis",
          localised.rung == "cause_localised" and localised.actionable,
          localised.because)

    narrowed = classify(gate_passed=False, state=base.apply(
        {"observed_failure": "TypeError in summarise"}))
    check("a_reproduction_without_a_cause_is_narrowed_not_localised",
          narrowed.rung == "narrowed" and not narrowed.actionable)

    nothing = classify(gate_passed=False, state=base)
    check("an_empty_run_is_no_progress_not_attempted",
          nothing.rung == "no_progress",
          "'attempted' hid the difference between a diagnosis and nothing")

    skipped = classify(gate_passed=False, state=base,
                       skipped_reason="not a git repository")
    check("a_skip_carries_its_reason",
          skipped.rung == "skipped" and "git" in skipped.because)

    test_edit = classify(gate_passed=True, state=base.apply(
        {"files_changed": ["tests/test_clamp.py"]}))
    check("a_pass_from_editing_only_tests_is_flagged_not_hidden",
          test_edit.rung == "verified_by_test_change" and test_edit.actionable
          and "weakened" in test_edit.because,
          "an agent that can edit tests can make any gate green")
    real_fix = classify(gate_passed=True, state=base.apply(
        {"files_changed": ["clamp.py", "tests/test_clamp.py"]}))
    check("a_pass_that_also_changed_source_is_an_ordinary_pass",
          real_fix.rung == "verified",
          "changing a test alongside the code is normal; changing only "
          "tests is the case worth flagging")
    check("test_detection_covers_common_layouts",
          all(_only_tests_changed([p]) for p in
              ("test_x.py", "x_test.go", "tests/a.py", "src/__tests__/a.js",
               "a.spec.ts", "conftest.py")),
          "a false negative reports a weakened suite as a clean pass")

    ordered = rank([nothing, green, localised, blocked])
    check("ranking_leads_with_what_is_usable",
          [item.rung for item in ordered]
          == ["verified", "cause_localised", "blocked_named", "no_progress"],
          str([item.rung for item in ordered]))

    summary = summarise([green, localised, nothing])
    check("the_summary_counts_only_actionable_results",
          summary["actionable"] == 2 and summary["total"] == 3
          and "act on" in summary["headline"], summary["headline"])
    check("an_empty_night_says_so_without_apology",
          "invented" in summarise([])["headline"],
          summarise([])["headline"])

    try:
        Outcome("triumphant", "x", {})
        check("an_unknown_rung_is_refused_by_name", False)
    except OvernightOutcomeError as exc:
        check("an_unknown_rung_is_refused_by_name",
              "verified" in str(exc) and "narrowed" in str(exc), str(exc)[:110])

    return {"module": "core.overnight_outcome", "tests": tests,
            "passed": all(item["passed"] for item in tests)}
