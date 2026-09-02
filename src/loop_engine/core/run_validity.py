"""Whether a run is eligible to be reasoned about, and for which question.

A run that never reached the model cannot tell you anything about prompts. A
run whose provider timed out three times cannot be compared against one whose
provider did not. Using either as evidence about cognition attributes an
infrastructure fault to a strategy, and the conclusion is not merely wrong but
unfalsifiable, because nothing recorded says the experiment did not happen.

On 2026-09-02 six live runs were used to reason about behaviour. Every one had
transport failures. Three had zero completed model calls and were nonetheless
read as evidence about task difficulty. Nothing in the repository said they
were ineligible, so nothing stopped it.

This module is that gate. It reads a finished run and states what the run may
be used to argue:

  INFRASTRUCTURE_INVALID     the intended experiment did not execute
  INFRASTRUCTURE_UNCERTAIN   too little evidence to tell whether it did
  SEMANTICALLY_ANALYZABLE    intact enough to study the model's reasoning
  MIXED_OR_MULTI_CAUSAL      it executed, and infrastructure also interfered

An invalid run is not worthless. It is first-class evidence about
infrastructure, and it is excluded only from the semantic questions it cannot
answer. Exclusions are recorded with their reasons rather than applied
silently, because a filter nobody can see is how a corpus quietly becomes the
runs that happened to agree.

Owns:
    - RunValidity and assess_run_validity(): the classification.
    - eligible_runs(): the split, with every exclusion stated.

Does not own: the run record (core.adaptive_practitioner_result), the terminal
code (core.terminal_layer), or any analysis that consults this gate.
"""
from __future__ import annotations

from dataclasses import dataclass, field

RUN_VALIDITY_RECORD_TYPE = "run_validity_envelope/v1"

INFRASTRUCTURE_INVALID = "INFRASTRUCTURE_INVALID"
INFRASTRUCTURE_UNCERTAIN = "INFRASTRUCTURE_UNCERTAIN"
SEMANTICALLY_ANALYZABLE = "SEMANTICALLY_ANALYZABLE"
MIXED_OR_MULTI_CAUSAL = "MIXED_OR_MULTI_CAUSAL"

#: Event kinds that mean a physical attempt did not deliver the intended
#: request or response. Matched on the event's own typed kind, never on the
#: text of a provider's error message, which differs per provider and version.
TRANSPORT_FAILURE_EVENTS = ("model.step.transport_failed",
                            "model.step.repair_exhausted")
COMPLETED_CALL_EVENT = "model.step.completed"
FORMAT_REPAIR_EVENT = "model.step.output_repaired"


class RunValidityError(ValueError):
    """A validity assessment violated its typed contract."""


@dataclass
class RunValidity:
    """What one run may be used to argue, and why."""

    run_id: str
    classification: str
    completed_calls: int = 0
    transport_failures: int = 0
    format_repairs: int = 0
    reached_execution: bool = False
    reached_verification: bool = False
    contamination: tuple = ()
    exclusion_reasons: tuple = ()
    evidence_missing: tuple = ()

    def __post_init__(self) -> None:
        if self.classification not in (
                INFRASTRUCTURE_INVALID, INFRASTRUCTURE_UNCERTAIN,
                SEMANTICALLY_ANALYZABLE, MIXED_OR_MULTI_CAUSAL):
            raise RunValidityError(
                f"unknown classification {self.classification!r}")

    @property
    def eligible_for_infrastructure_analysis(self) -> bool:
        """Always true. A failed run is evidence about what failed."""
        return True

    @property
    def eligible_for_semantic_analysis(self) -> bool:
        """True when the model was reached and produced something to study."""
        return self.classification in (SEMANTICALLY_ANALYZABLE,
                                       MIXED_OR_MULTI_CAUSAL)

    @property
    def eligible_for_comparison(self) -> bool:
        """True only when nothing interfered.

        Comparing a contaminated run against a clean one measures the
        contamination. This is deliberately the strictest gate in the module.
        """
        return self.classification == SEMANTICALLY_ANALYZABLE

    def to_dict(self) -> dict:
        return {
            "record_type": RUN_VALIDITY_RECORD_TYPE,
            "run_id": self.run_id,
            "classification": self.classification,
            "completed_calls": self.completed_calls,
            "transport_failures": self.transport_failures,
            "format_repairs": self.format_repairs,
            "reached_execution": self.reached_execution,
            "reached_verification": self.reached_verification,
            "contamination": list(self.contamination),
            "exclusion_reasons": list(self.exclusion_reasons),
            "evidence_missing": list(self.evidence_missing),
            "eligible_for_infrastructure_analysis": True,
            "eligible_for_semantic_analysis":
                self.eligible_for_semantic_analysis,
            "eligible_for_comparison": self.eligible_for_comparison,
        }


def _count_events(events, kinds) -> int:
    total = 0
    for event in events or ():
        if not isinstance(event, dict):
            continue
        kind = str(event.get("event_type") or event.get("event") or "")
        if kind in kinds:
            total += 1
    return total


def assess_run_validity(result, events=()) -> RunValidity:
    """Classify one finished run from its own record and event stream.

    The event stream is where physical attempts live; the result carries what
    the run concluded. Both are read, and what neither says is reported as
    missing rather than assumed absent.
    """
    if not isinstance(result, dict):
        raise RunValidityError("assess_run_validity needs a run record")
    events = list(events or ())
    completed = _count_events(events, (COMPLETED_CALL_EVENT,))
    transport = _count_events(events, TRANSPORT_FAILURE_EVENTS)
    repairs = _count_events(events, (FORMAT_REPAIR_EVENT,))
    missing = []
    if not events:
        missing.append("no event stream was supplied; physical attempts and "
                       "transport failures could not be counted")
        completed = int(result.get("model_calls") or 0)

    verification = result.get("verification")
    reached_verification = bool(
        isinstance(verification, dict)
        and (verification.get("verdict") or verification.get("criteria")
             or str(verification.get("method") or "").strip().lower()
             not in ("", "not completed", "none")))
    reached_execution = bool(result.get("project_attempts"))

    contamination, exclusions = [], []
    if transport:
        contamination.append(
            f"{transport} physical attempt(s) failed in transport")
    if repairs:
        contamination.append(
            f"{repairs} response(s) required format repair")

    if completed == 0:
        classification = (INFRASTRUCTURE_UNCERTAIN if missing
                          else INFRASTRUCTURE_INVALID)
        exclusions.append(
            "no model call completed; this run cannot support any claim "
            "about the model, the prompt, the context, or the task")
    elif transport and not missing:
        classification = MIXED_OR_MULTI_CAUSAL
        exclusions.append(
            "transport failures occurred alongside completed calls; this run "
            "may be read for what the model did, but not compared against a "
            "run that had none")
    elif missing:
        classification = INFRASTRUCTURE_UNCERTAIN
        exclusions.append(
            "physical attempt evidence is absent, so interference cannot be "
            "ruled out")
    else:
        classification = SEMANTICALLY_ANALYZABLE

    return RunValidity(
        run_id=str(result.get("run_id") or ""),
        classification=classification, completed_calls=completed,
        transport_failures=transport, format_repairs=repairs,
        reached_execution=reached_execution,
        reached_verification=reached_verification,
        contamination=tuple(contamination),
        exclusion_reasons=tuple(exclusions),
        evidence_missing=tuple(missing))


def eligible_runs(assessments, purpose: str = "comparison") -> dict:
    """Split runs by eligibility, stating every exclusion.

    A corpus is only as honest as its exclusions are visible. This returns
    both halves and the reason each run fell where it did.
    """
    if purpose not in ("comparison", "semantic", "infrastructure"):
        raise RunValidityError(
            "purpose must be comparison, semantic, or infrastructure")
    included, excluded = [], []
    for item in assessments:
        value = item.to_dict() if isinstance(item, RunValidity) else item
        eligible = {
            "comparison": value.get("eligible_for_comparison"),
            "semantic": value.get("eligible_for_semantic_analysis"),
            "infrastructure": True,
        }[purpose]
        (included if eligible else excluded).append(value)
    return {
        "record_type": "run_eligibility_split/v1",
        "purpose": purpose,
        "included": included,
        "excluded": excluded,
        "included_count": len(included),
        "excluded_count": len(excluded),
        "note": ("every excluded run is listed with its reason; a corpus is "
                 "only as honest as its exclusions are visible"),
    }


def self_test() -> dict:
    """Prove each classification, and that exclusions are never silent."""
    tests = []

    def check(name: str, passed: bool, detail: str = "") -> None:
        tests.append({"test": name, "passed": bool(passed), "detail": detail})

    def events(completed=0, transport=0, repairs=0):
        stream = [{"event_type": COMPLETED_CALL_EVENT}] * completed
        stream += [{"event_type": TRANSPORT_FAILURE_EVENTS[0]}] * transport
        stream += [{"event_type": FORMAT_REPAIR_EVENT}] * repairs
        return stream or [{"event_type": "loop_init"}]

    clean = assess_run_validity(
        {"run_id": "clean", "verification": {"verdict": "accept"}},
        events(completed=12))
    check("a_run_with_completed_calls_and_no_interference_is_analyzable",
          clean.classification == SEMANTICALLY_ANALYZABLE
          and clean.eligible_for_comparison,
          clean.classification)

    # The exact shape of tonight's three family runs.
    dead = assess_run_validity({"run_id": "dead"}, events(transport=2))
    check("a_run_that_never_reached_the_model_is_infrastructure_invalid",
          dead.classification == INFRASTRUCTURE_INVALID
          and not dead.eligible_for_semantic_analysis
          and not dead.eligible_for_comparison,
          dead.classification)
    check("an_invalid_run_still_serves_infrastructure_analysis",
          dead.eligible_for_infrastructure_analysis,
          "a failed run is evidence about what failed")

    # The exact shape of tonight's three competition runs.
    mixed = assess_run_validity(
        {"run_id": "mixed", "project_attempts": [{"a": 1}]},
        events(completed=49, transport=3, repairs=6))
    check("a_run_with_calls_and_transport_failures_is_mixed",
          mixed.classification == MIXED_OR_MULTI_CAUSAL
          and mixed.eligible_for_semantic_analysis
          and not mixed.eligible_for_comparison,
          "readable for what the model did, not comparable")

    thin = assess_run_validity({"run_id": "thin", "model_calls": 4})
    check("a_run_with_no_attempt_evidence_is_uncertain_not_assumed_clean",
          thin.classification == INFRASTRUCTURE_UNCERTAIN
          and not thin.eligible_for_comparison
          and thin.evidence_missing,
          "absent evidence is not evidence of absence")

    check("every_ineligible_run_states_why",
          all(item.exclusion_reasons
              for item in (dead, mixed, thin))
          and not clean.exclusion_reasons,
          "a filter nobody can see is how a corpus becomes agreeable")

    split = eligible_runs([clean, dead, mixed, thin], purpose="comparison")
    check("the_split_reports_both_halves_and_every_reason",
          split["included_count"] == 1 and split["excluded_count"] == 3
          and all(row["exclusion_reasons"] for row in split["excluded"]),
          f"{split['included_count']} of 4 comparable")
    infra = eligible_runs([clean, dead, mixed, thin],
                          purpose="infrastructure")
    check("infrastructure_analysis_excludes_nothing",
          infra["included_count"] == 4 and infra["excluded_count"] == 0)

    refused = 0
    for bad in (lambda: RunValidity("x", "MADE_UP"),
                lambda: assess_run_validity("not a record"),
                lambda: eligible_runs([], purpose="whatever")):
        try:
            bad()
        except (RunValidityError, TypeError):
            refused += 1
    check("invalid_assessments_fail_closed", refused == 3, f"{refused}/3")

    passed = sum(1 for item in tests if item["passed"])
    return {"record_type": "run_validity_test/v1", "tests": tests,
            "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
