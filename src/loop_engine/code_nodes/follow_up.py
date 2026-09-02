"""Follow-up policies — the scheduler's reactive bias: after X happens, schedule Y.

Owner direction (2026-08-23): beyond the opening checklist (which biases the FIRST
steps), the practitioner needs reactive obligations — after a costly model action
on thin evidence, schedule a "justify why"; after any result, schedule a review;
after an open-ended result that couldn't be structured, schedule a structuring
pass; after repeated non-progress, schedule a reframe.  These are the *after* to
the checklist's *before*, at the control-flow level.

A follow-up policy is DATA, not code: a declarative trigger (conditions over the
pass context) plus the obligation to schedule and an explicit alternative — so an
open-source consumer swaps the scheduling bias without touching the loop, and each
policy can be demoted through the same paired-evidence governance as the standing
biases (see [[biases.py]]).  ``evaluate_policies`` runs them deterministically over
a pass context and returns ``PendingObligation``s; the deterministic router honors
blocking obligations before free choice — bias via the scheduler, never a hidden
model call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

OBLIGATION_KINDS = ("justify_action", "review_result", "structure_learning",
                    "reframe_after_barren", "assess_context_coverage",
                    "validate_candidate", "join_spawned")

# Declarative condition ops — a tiny, safe evaluator (no eval).
_OPS = {
    "eq": lambda a, b: a == b, "ne": lambda a, b: a != b,
    "gt": lambda a, b: _num(a) > _num(b), "gte": lambda a, b: _num(a) >= _num(b),
    "lt": lambda a, b: _num(a) < _num(b), "lte": lambda a, b: _num(a) <= _num(b),
    "in": lambda a, b: a in b, "contains": lambda a, b: b in (a or ""),
}


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float("nan")


def _eval_condition(cond: dict, ctx: dict) -> bool:
    field_name = cond.get("field")
    op = cond.get("op")
    if op == "exists":
        return field_name in ctx and ctx[field_name] not in (None, "", [], {})
    if op == "missing":
        return field_name not in ctx or ctx[field_name] in (None, "", [], {})
    if op not in _OPS:
        raise ValueError(f"unknown op {op!r}; valid: {sorted(_OPS) + ['exists', 'missing']}")
    if field_name not in ctx:
        return False
    return _OPS[op](ctx[field_name], cond.get("value"))


def eval_trigger(trigger: dict, ctx: dict) -> bool:
    """Evaluate a declarative trigger with all/any groups over the context."""
    if "all" in trigger:
        return all(_eval_condition(c, ctx) for c in trigger["all"])
    if "any" in trigger:
        return any(_eval_condition(c, ctx) for c in trigger["any"])
    return _eval_condition(trigger, ctx)


@dataclass
class PendingObligation:
    kind: str
    reason: str
    scheduled_action: str = ""
    priority: int = 50
    blocking: bool = False
    expires_after_passes: int = 5
    from_policy: str = ""

    def __post_init__(self):
        if self.kind not in OBLIGATION_KINDS:
            raise ValueError(f"kind must be one of {OBLIGATION_KINDS}")


@dataclass(frozen=True)
class FollowUpPolicy:
    policy_id: str
    trigger: dict
    kind: str
    scheduled_action: str
    reason: str
    priority: int = 50
    blocking: bool = False
    alternative_action: str = ""

    def fires(self, ctx: dict) -> bool:
        return eval_trigger(self.trigger, ctx)

    def obligation(self) -> PendingObligation:
        return PendingObligation(
            kind=self.kind, reason=self.reason,
            scheduled_action=self.scheduled_action, priority=self.priority,
            blocking=self.blocking, from_policy=self.policy_id)


# The core scheduling biases — DATA, swappable, evidence-demotable.
CORE_FOLLOW_UP_POLICIES = (
    FollowUpPolicy(
        "justify_expensive_model_action",
        {"all": [{"field": "action_origin", "op": "eq", "value": "model"},
                 {"field": "estimated_cost", "op": "gt", "value": 5.0},
                 {"field": "justification_status", "op": "eq",
                  "value": "missing"}]},
        "justify_action", "reason.explain_why_selected_action_is_appropriate",
        "an expensive action chosen on thin evidence must be justified before "
        "it runs", priority=80, blocking=True,
        alternative_action="execute_without_additional_justification"),
    FollowUpPolicy(
        "review_every_result",
        {"field": "result_reviewed", "op": "eq", "value": False},
        "review_result", "evaluate.review_input_output_pair",
        "a produced result must be reviewed before it can update accepted state",
        priority=70, blocking=True,
        alternative_action="accept_without_review"),
    FollowUpPolicy(
        "structure_open_ended_learning",
        {"field": "learning_disposition", "op": "eq",
         "value": "requires_additional_structuring"},
        "structure_learning", "distill.extract_reusable_from_prior_result",
        "an open-ended result that couldn't be encapsulated must be structured "
        "before composing the next step", priority=90, blocking=True),
    FollowUpPolicy(
        "reframe_after_two_barren_passes",
        {"field": "barren_passes", "op": "gte", "value": 2},
        "reframe_after_barren", "route.reset_with_fresh_context",
        "repeated non-progress: reframe the goal or reset the context",
        priority=60, blocking=False,
        alternative_action="continue_current_approach"),
    FollowUpPolicy(
        "assess_coverage_before_composing",
        {"all": [{"field": "about_to_compose", "op": "eq", "value": True},
                 {"field": "context_coverage_assessed", "op": "eq",
                  "value": False}]},
        "assess_context_coverage", "reason.assess_context_coverage_decision",
        "assess whether we understand the problem before composing a solution",
        priority=85, blocking=True,
        alternative_action="proceed_with_existing_context"),
)


def evaluate_policies(ctx: dict,
                      policies: "Sequence[FollowUpPolicy] | None" = None
                      ) -> list:
    """Every obligation the context triggers, most-urgent first (blocking before
    non-blocking, then by priority).  Deterministic — the router consults this."""
    pols = policies if policies is not None else CORE_FOLLOW_UP_POLICIES
    obs = [p.obligation() for p in pols if p.fires(ctx)]
    obs.sort(key=lambda o: (not o.blocking, -o.priority))
    return obs


def next_obligation(obligations: Sequence) -> "PendingObligation | None":
    """The one obligation the router must service next (highest-priority
    blocking, else highest-priority) — or None if the model may choose freely."""
    if not obligations:
        return None
    blocking = [o for o in obligations if o.blocking]
    pool = blocking or list(obligations)
    return max(pool, key=lambda o: o.priority)


def merge_into_candidates(obligations: Sequence, candidates: list) -> list:
    """Bias the decide node: prepend obligation-driven actions so they are
    considered before free candidates.  Blocking obligations lead."""
    from ..loop.kernel import CandidateAction
    lead = []
    for o in sorted(obligations, key=lambda o: (not o.blocking, -o.priority)):
        lead.append(CandidateAction(
            action=o.scheduled_action or f"obligation::{o.kind}",
            kind="obligation", rationale=o.reason,
            expected_value=0.7 if o.blocking else 0.55,
            estimated_cost=1.0, information_gain=0.3))
    return lead + list(candidates)


def policy_records() -> list:
    """Each follow-up policy as a searchable strategy record."""
    from ..core.store_serve import StoreRecord
    recs = []
    for p in CORE_FOLLOW_UP_POLICIES:
        recs.append(StoreRecord(
            record_id=f"followup.{p.policy_id}", kind="strategy",
            title=f"Follow-up: {p.reason}",
            body={"trigger": p.trigger, "kind": p.kind,
                  "scheduled_action": p.scheduled_action,
                  "blocking": p.blocking, "alternative": p.alternative_action},
            tags=("follow_up_policy", "scheduler_bias", p.kind,
                  "step:decide_next", "step:route"), tier="core"))
    return recs


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. an expensive model action on thin evidence schedules a justify pass.
    ctx = {"action_origin": "model", "estimated_cost": 12.0,
           "justification_status": "missing", "result_reviewed": True}
    obs = evaluate_policies(ctx)
    kinds = {o.kind for o in obs}
    check("expensive_action_schedules_a_justify_obligation",
          "justify_action" in kinds
          and any(o.blocking for o in obs if o.kind == "justify_action"),
          f"scheduled: {sorted(kinds)}")

    # 2. an unstructured learning result schedules a blocking structuring pass.
    obs2 = evaluate_policies(
        {"learning_disposition": "requires_additional_structuring",
         "result_reviewed": True})
    nxt = next_obligation(obs2)
    check("unstructured_learning_schedules_a_blocking_structuring_pass",
          nxt is not None and nxt.kind == "structure_learning" and nxt.blocking,
          "the structuring obligation is the next thing the router services")

    # 3. the declarative trigger evaluator is safe and correct (no eval).
    t = {"all": [{"field": "x", "op": "gte", "value": 2},
                 {"field": "y", "op": "eq", "value": "go"}]}
    check("declarative_triggers_evaluate_deterministically",
          eval_trigger(t, {"x": 3, "y": "go"})
          and not eval_trigger(t, {"x": 1, "y": "go"}),
          "conditions over the pass context, evaluated without eval")

    # 4. barren passes schedule a (non-blocking) reframe.
    obs3 = evaluate_policies({"barren_passes": 3, "result_reviewed": True})
    check("repeated_non_progress_schedules_a_reframe",
          any(o.kind == "reframe_after_barren" and not o.blocking
              for o in obs3),
          "two barren passes -> reframe, but it doesn't block")

    # 5. no triggers -> no obligations -> the model may choose freely.
    obs4 = evaluate_policies({"result_reviewed": True})
    check("no_triggers_means_free_choice",
          obs4 == [] and next_obligation(obs4) is None,
          "when nothing fires, there is no scheduler bias")

    # 6. obligations bias the decide node by leading the candidate list.
    from ..loop.kernel import CandidateAction
    base = [CandidateAction(action="explore_freely")]
    merged = merge_into_candidates(obs2, base)
    check("obligations_lead_the_candidate_list",
          merged[0].kind == "obligation"
          and merged[-1].action == "explore_freely",
          "scheduled obligations are considered before free candidates")

    # 7. a blocking policy has an explicit alternative (evidence can demote it).
    jp = next(p for p in CORE_FOLLOW_UP_POLICIES
              if p.policy_id == "justify_expensive_model_action")
    check("policies_carry_an_explicit_alternative",
          jp.alternative_action == "execute_without_additional_justification",
          "each bias names its adversarial alternative for paired trials")

    # 8. follow-up policies are searchable resources.
    from ..core.store_serve import SolverStore
    store = SolverStore(core_records=policy_records())
    hit = store.search("when should we justify an expensive model action",
                       kind="strategy")
    check("follow_up_policies_are_searchable_resources",
          hit["hits"] and any("followup." in h["record_id"]
                              for h in hit["hits"]),
          "a scheduling bias is findable through the one search DAG")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "follow_up_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
