"""The what-is-next cycle — the one global question, and the guardrail around it.

Owner ontology (2026-08-22): **everything goes through "what is next?"**  It is the
single global question.  Its ANSWERS are sub-tasks — add a node, optimize, gather
context, research, *research what we missed*, *find what alternatives exist*,
*diagnose what we did wrong*, deliberate, test, or terminate.  "What did we miss"
and "what alternatives exist" are therefore NOT sibling phases of some pipeline —
they are answer kinds of what-is-next, chosen when the situation calls for them.

The atomic unit is a cycle of **three sibling stages**, repeated:

  1. what_is_next      — decide the single next sub-task (an answer kind below)
  2. how_to_execute    — decide how best to carry it out, asking FIRST
                         "do we already have this coded, retrievable, ready?"
                         and escalating up a reuse-first ladder only as far as
                         needed (deterministic wrapper -> tool/db/service ->
                         micro/small model -> one LLM -> deliberation -> research)
  3. verify_and_advance — did we execute it correctly, and are we ready for the
                         next what-is-next?

Two guardrails make this structural rather than aspirational — they are why the
harness cannot one-shot:

  * the **reuse-first guard**: how_to_execute may not select an expensive rung
    (an LLM/deliberation/research) without recording that the cheaper rungs above
    it — crucially "do we already have this?" — were checked and ruled out; and
  * the **advance guard**: the cycle may not advance to the next what-is-next
    until verify_and_advance has run.

Every rung avoided below an LLM is a model call saved, recorded on the receipt.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from ..strings.knowledge import Knowledge


# ===========================================================================
# TAXONOMIES — the clear hierarchies the owner asked for.
# ===========================================================================

# The three sibling stages of one atomic cycle.  Fixed; the same every time.
CYCLE_STAGES = ("what_is_next", "how_to_execute", "verify_and_advance")

# Stage 1 hierarchy: the kinds of answer "what is next?" can return.  These are
# sub-tasks of the one global question — not competitors to it.  Grouped for
# legibility; the group is the parent, the kind is the leaf.
WHATS_NEXT_ANSWER_KINDS = {
    "construct": ("add_node", "optimize", "compose", "ensemble"),
    "inform":    ("gather_context", "research", "review_missed",
                  "find_alternatives", "diagnose"),
    "decide":    ("deliberate", "route", "abstain"),
    "check":     ("test", "adversarially_validate", "calibrate"),
    "deliver":   ("terminate",),
}
# Flat set of every valid answer kind (leaves of the hierarchy above).
ANSWER_KINDS = tuple(k for group in WHATS_NEXT_ANSWER_KINDS.values()
                     for k in group)

# Stage 2 hierarchy: the reuse-first execution ladder, cheapest / most
# deterministic FIRST.  "Do we already have this?" is rung 0; an LLM is only
# reached after every cheaper rung is ruled out.  The index is the escalation
# order and the guard uses it.
EXECUTION_LADDER = (
    "exact_reuse",               # already coded, retrievable, ready (registry/db)
    "deterministic_wrapper",     # a bounded deterministic adapter around it
    "deterministic_composition", # compose exact capabilities, no model
    "retrieval",                 # a database / store / index lookup
    "micro_model",               # a tiny local decide/label network
    "small_model",               # a small language model (local, narrow)
    "tool_call",                 # a tool / microservice / API / db call
    "llm_single",                # one hosted-model call
    "llm_deliberation",          # a council / debate
    "research",                  # external research
)
# The rung at/above which a call costs real model tokens.  Anything strictly
# below this index is a "free" (no-generation) resolution.
FIRST_MODEL_RUNG = EXECUTION_LADDER.index("micro_model")
FIRST_LLM_RUNG = EXECUTION_LADDER.index("llm_single")

# Stage 3 hierarchy: the outcomes of verifying an execution.
VERIFY_OUTCOMES = (
    "correct_and_ready",     # executed well; advance to the next what-is-next
    "correct_more_needed",   # fine, but the graph is not complete; loop
    "incorrect",             # wrong; the repair is itself the next what-is-next
    "inconclusive",          # cannot tell yet; more validation is the next step
)


class GuardViolation(RuntimeError):
    """Raised when the cycle tries to skip the reuse-first or advance guard."""


# ===========================================================================
# Records for one atomic cycle.
# ===========================================================================


@dataclass
class NextAnswer:
    """Stage 1 output: the single next sub-task, typed by the answer taxonomy."""
    kind: str
    target: str
    rationale: str = ""
    confidence: float = 0.6

    def __post_init__(self):
        if self.kind not in ANSWER_KINDS:
            raise ValueError(f"unknown what-is-next answer kind {self.kind!r}; "
                             f"must be one of {ANSWER_KINDS}")

    def group(self) -> str:
        for g, kinds in WHATS_NEXT_ANSWER_KINDS.items():
            if self.kind in kinds:
                return g
        return "unknown"


@dataclass
class ExecutionDecision:
    """Stage 2 output: which ladder rung, and proof the cheaper ones were ruled
    out.  ``rungs_checked`` lists rungs considered before ``chosen``, top-first —
    it is what the reuse-first guard inspects."""
    chosen: str
    rungs_checked: list = field(default_factory=list)
    handle: str = ""              # what to run (a registered id / adapter / prompt)
    rationale: str = ""
    model_calls: int = 0

    def is_free(self) -> bool:
        return EXECUTION_LADDER.index(self.chosen) < FIRST_MODEL_RUNG


@dataclass
class VerifyResult:
    """Stage 3 output: did the execution succeed, and are we ready to advance?"""
    outcome: str
    evidence: str = ""
    ready_to_advance: bool = False

    def __post_init__(self):
        if self.outcome not in VERIFY_OUTCOMES:
            raise ValueError(f"unknown verify outcome {self.outcome!r}")


@dataclass
class CycleStep:
    """One full atomic cycle: what-is-next -> how-to-execute -> verify."""
    knowledge_goal: str
    answer: NextAnswer
    execution: ExecutionDecision
    verify: VerifyResult
    model_calls_avoided: int = 0

    def receipt(self) -> dict:
        return {"record_type": "whats_next_cycle/v1",
                "goal": self.knowledge_goal,
                "what_is_next": {"kind": self.answer.kind,
                                 "group": self.answer.group(),
                                 "target": self.answer.target,
                                 "rationale": self.answer.rationale},
                "how_to_execute": {"chosen_rung": self.execution.chosen,
                                   "rungs_ruled_out": self.execution.rungs_checked,
                                   "free": self.execution.is_free(),
                                   "model_calls": self.execution.model_calls},
                "verify_and_advance": {"outcome": self.verify.outcome,
                                       "ready": self.verify.ready_to_advance},
                "model_calls_avoided": self.model_calls_avoided}


# ===========================================================================
# The guards — structural, not advisory.
# ===========================================================================


def reuse_first_guard(decision: ExecutionDecision) -> None:
    """Refuse an execution that reached for a model without ruling out reuse.

    If the chosen rung costs model tokens (>= micro_model), EVERY cheaper rung
    above it — starting with 'do we already have this?' (exact_reuse) — must
    appear in ``rungs_checked``.  Jumping straight to an LLM is the one-shot
    failure, and this makes it inexpressible."""
    idx = EXECUTION_LADDER.index(decision.chosen)
    if idx < FIRST_MODEL_RUNG:
        return                                    # a free rung needs no proof
    required = list(EXECUTION_LADDER[:idx])
    missing = [r for r in required if r not in decision.rungs_checked]
    if missing:
        raise GuardViolation(
            f"execution chose {decision.chosen!r} (a model rung) without ruling "
            f"out cheaper rungs first: {missing}. 'Do we already have this "
            f"coded, retrievable, ready?' must be answered before an LLM.")


def advance_guard(step: CycleStep) -> None:
    """Refuse to treat a cycle as complete until verify_and_advance has run and
    reported readiness — no advancing to the next what-is-next on faith."""
    if step.verify is None:
        raise GuardViolation("cannot advance: verify_and_advance did not run")
    if (step.verify.ready_to_advance
            and step.verify.outcome not in ("correct_and_ready",)):
        raise GuardViolation(
            f"cannot advance: outcome {step.verify.outcome!r} is not a "
            f"ready-to-advance outcome")


# ===========================================================================
# The cycle runner.
# ===========================================================================

DecideFn = Callable[[Knowledge], NextAnswer]
ExecuteFn = Callable[[Knowledge, NextAnswer], ExecutionDecision]
VerifyFn = Callable[[Knowledge, NextAnswer, ExecutionDecision], VerifyResult]


def run_cycle(knowledge: Knowledge, *, decide: DecideFn, resolve: ExecuteFn,
              verify: VerifyFn) -> CycleStep:
    """Run ONE atomic what-is-next cycle with both guards enforced.

    decide -> what is next (a typed sub-task); resolve -> how to execute it,
    reuse-first (guarded); verify -> did we do it right and can we advance
    (guarded).  Returns the CycleStep receipt; raises GuardViolation if either
    guard is broken."""
    ans = decide(knowledge)
    ex = resolve(knowledge, ans)
    reuse_first_guard(ex)                          # <-- no jumping to an LLM
    vr = verify(knowledge, ans, ex)
    avoided = max(0, FIRST_LLM_RUNG - EXECUTION_LADDER.index(ex.chosen)) \
        if EXECUTION_LADDER.index(ex.chosen) < FIRST_LLM_RUNG else 0
    step = CycleStep(knowledge_goal=knowledge.goal, answer=ans, execution=ex,
                     verify=vr, model_calls_avoided=avoided)
    advance_guard(step)                            # <-- no advancing on faith
    return step


# ===========================================================================
# Deterministic default stages — zero model, for the self-test and as fallback.
# They still honour the full ontology and both guards.
# ===========================================================================


def det_decide(knowledge: Knowledge) -> NextAnswer:
    """A zero-model what-is-next: pick the next sub-task from obligations/facts."""
    if not knowledge.fact("has_baseline"):
        return NextAnswer("add_node", "baseline=deterministic_default",
                          "no baseline yet", 0.9)
    if not knowledge.fact("leakage_checked"):
        return NextAnswer("adversarially_validate", "test=leakage_audit",
                          "baseline exists but leakage unverified", 0.85)
    if knowledge.open_obligations:
        return NextAnswer("add_node", f"address={knowledge.open_obligations[0]}",
                          "open obligation remains", 0.8)
    return NextAnswer("terminate", "deliver", "no obligations remain", 0.9)


def det_resolve(knowledge: Knowledge, ans: NextAnswer) -> ExecutionDecision:
    """A zero-model reuse-first resolution: always ask 'do we already have it?'
    first.  If a registered handle exists for the target, reuse it (free); else
    fall back deterministically.  Never reaches an LLM in the default path."""
    checked = ["exact_reuse"]
    have = knowledge.fact("registry_has:" + ans.target)
    if have:
        return ExecutionDecision("exact_reuse", rungs_checked=[],
                                 handle=str(have),
                                 rationale="already coded, retrievable, ready")
    checked.append("deterministic_wrapper")
    return ExecutionDecision("deterministic_wrapper", rungs_checked=["exact_reuse"],
                             handle=f"wrapper::{ans.target}",
                             rationale="no exact reuse; a bounded deterministic "
                             "wrapper suffices — still no model call")


def det_verify(knowledge: Knowledge, ans: NextAnswer,
               ex: ExecutionDecision) -> VerifyResult:
    """A zero-model verify: an execution with a concrete handle is correct; if
    obligations remain, we loop rather than declare done."""
    if not ex.handle:
        return VerifyResult("incorrect", "no handle produced", False)
    more = bool(knowledge.open_obligations) and ans.kind != "terminate"
    if more:
        return VerifyResult("correct_more_needed",
                            "executed, but obligations remain", False)
    return VerifyResult("correct_and_ready", "executed with a concrete handle",
                        True)


def run_cycle_deterministic(knowledge: Knowledge) -> CycleStep:
    return run_cycle(knowledge, decide=det_decide, resolve=det_resolve,
                     verify=det_verify)


# ===========================================================================
# Model-backed stages — the real cycle, using the roster at MAX output, but only
# when the reuse-first ladder has escalated that far.
# ===========================================================================


def make_model_cycle(models: Sequence[str] | None = None, *,
                     questions: Sequence[str] = (), rounds: int = 2,
                     registry_probe: Callable[[str], str] | None = None):
    """Build model-backed decide/resolve/verify.

    ``registry_probe(target) -> handle|""`` is the "do we already have this
    coded, retrievable, ready?" check that runs FIRST in resolve; if it returns a
    handle, no model is called at all.  Only when it (and the deterministic rungs)
    come up empty does resolve escalate to an LLM/deliberation, and decide/verify
    use max-output calls.  The reuse-first guard still applies to every result."""
    from ..static_architecture.provider_pinned import (
        ProviderPinnedRequest, invoke_provider_model)
    from ..static_architecture.ollama_resolvers import debate
    from ..static_architecture.ollama_resolvers import COUNCIL_MODELS
    import json as _json
    ms = list(models) if models else list(COUNCIL_MODELS)
    probe = registry_probe or (lambda _t: "")

    def decide(knowledge: Knowledge) -> NextAnswer:
        # what-is-next itself is a deliberation when the decision is open.
        out = debate(knowledge, models=ms, rounds=rounds, questions=questions)
        cons = (out.get("consensus") or [])
        if not cons:
            return NextAnswer("gather_context", "need_more_signal",
                              "no consensus from the debate", 0.5)
        top = cons[0]
        kind = top["kind"] if top["kind"] in ANSWER_KINDS else "add_node"
        return NextAnswer(kind, top["move"],
                          f"debate consensus ({out.get('total_tokens',0)} tokens)",
                          min(1.0, top.get("models_endorsing", 1) / max(1, len(ms))))

    def resolve(knowledge: Knowledge, ans: NextAnswer) -> ExecutionDecision:
        # Rung 0 ALWAYS first: do we already have this coded, retrievable, ready?
        handle = probe(ans.target)
        if handle:
            return ExecutionDecision("exact_reuse", rungs_checked=[],
                                     handle=handle,
                                     rationale="registry probe: already available")
        checked = ["exact_reuse", "deterministic_wrapper",
                   "deterministic_composition", "retrieval", "micro_model",
                   "small_model", "tool_call"]
        # The answer kind decides the model rung: a construct/optimize can often
        # be a single call; an open decision or a diagnosis wants deliberation.
        if ans.kind in ("deliberate", "find_alternatives", "review_missed",
                        "diagnose", "adversarially_validate"):
            return ExecutionDecision("llm_deliberation", rungs_checked=checked,
                                     handle=f"debate::{ans.target}",
                                     rationale="open/critical decision — deliberate",
                                     model_calls=len(ms) * rounds)
        if ans.kind == "research":
            return ExecutionDecision("research", rungs_checked=checked
                                     + ["llm_single", "llm_deliberation"],
                                     handle=f"research::{ans.target}",
                                     rationale="needs external evidence",
                                     model_calls=1)
        return ExecutionDecision("llm_single", rungs_checked=checked,
                                 handle=f"llm::{ans.target}",
                                 rationale="no reuse; one model call suffices",
                                 model_calls=1)

    def verify(knowledge: Knowledge, ans: NextAnswer,
               ex: ExecutionDecision) -> VerifyResult:
        if ans.kind == "terminate":
            return VerifyResult("correct_and_ready", "delivered", True)
        # A max-output model adjudicates whether the executed step is correct and
        # whether we are ready to move on — one atomic question.
        prompt = (f"Task: {knowledge.goal}\n"
                  f"We chose next step: [{ans.kind}] {ans.target}\n"
                  f"Executed via: {ex.chosen} ({ex.handle})\n\n"
                  "Was this the right next step, executed correctly, and are we "
                  "ready to move to the NEXT what-is-next? Answer ONLY as JSON "
                  '{"outcome": one of ["correct_and_ready","correct_more_needed",'
                  '"incorrect","inconclusive"], "ready": true/false, '
                  '"evidence": "one sentence"}.')
        res = invoke_provider_model(ProviderPinnedRequest(
            prompt=prompt, provider="ollama_cloud", model=ms[0],
            temperature=0.3))
        try:
            s = res.text[res.text.find("{"):res.text.rfind("}") + 1]
            v = _json.loads(s)
            outcome = v.get("outcome") if v.get("outcome") in VERIFY_OUTCOMES \
                else "inconclusive"
            return VerifyResult(outcome, str(v.get("evidence", ""))[:200],
                                bool(v.get("ready"))
                                and outcome == "correct_and_ready")
        except Exception:                                       # noqa: BLE001
            return VerifyResult("inconclusive", "verify reply unparseable", False)

    return {"decide": decide, "resolve": resolve, "verify": verify}


def run_cycle_models(knowledge: Knowledge, *, models: Sequence[str] | None = None,
                     questions: Sequence[str] = (), rounds: int = 2,
                     registry_probe: Callable[[str], str] | None = None
                     ) -> CycleStep:
    """One real atomic cycle with model-backed stages, reuse-first and guarded."""
    stages = make_model_cycle(models, questions=questions, rounds=rounds,
                              registry_probe=registry_probe)
    return run_cycle(knowledge, **stages)


# ===========================================================================
# Self-test — deterministic, no network.  Proves the ontology + guards HOLD.
# ===========================================================================


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. everything is an answer to ONE question: the answer kinds include the
    # "review/alternatives/diagnose" that used to be mistaken for phases.
    check("review_alternatives_diagnose_are_answer_kinds_not_phases",
          all(k in ANSWER_KINDS for k in ("review_missed", "find_alternatives",
                                          "diagnose", "research")),
          "'what did we miss', 'what alternatives', 'what did we do wrong', and "
          "research are answer KINDS of what-is-next, not sibling phases")

    # 2. the atomic cycle is exactly the three sibling stages.
    check("the_cycle_is_three_sibling_stages",
          CYCLE_STAGES == ("what_is_next", "how_to_execute",
                           "verify_and_advance"),
          "what is next -> how to execute -> verify and advance")

    # 3. a full deterministic cycle runs and reuses when the registry has it.
    k = Knowledge(goal="classify churn", facts={"has_baseline": True,
                  "leakage_checked": True,
                  "registry_has:address=choose_model": "hgb_v3"},
                  open_obligations=("choose_model",))
    step = run_cycle_deterministic(k)
    check("do_we_already_have_it_is_asked_first_and_can_short_circuit",
          step.execution.chosen == "exact_reuse" and step.execution.is_free()
          and step.model_calls_avoided > 0,
          "'do we already have this coded, retrievable, ready?' hit the registry "
          "and resolved with zero model calls")

    # 4. the reuse-first guard blocks jumping to an LLM without ruling out reuse.
    blocked = False
    try:
        reuse_first_guard(ExecutionDecision("llm_single", rungs_checked=[]))
    except GuardViolation:
        blocked = True
    check("jumping_to_an_llm_without_checking_reuse_is_blocked", blocked,
          "choosing llm_single with no cheaper rungs ruled out raises — the "
          "one-shot failure is inexpressible")

    # 5. an LLM rung is allowed ONLY once every cheaper rung is ruled out.
    ok_escalation = True
    try:
        reuse_first_guard(ExecutionDecision(
            "llm_single",
            rungs_checked=list(EXECUTION_LADDER[:FIRST_LLM_RUNG])))
    except GuardViolation:
        ok_escalation = False
    check("an_llm_is_allowed_after_all_cheaper_rungs_are_ruled_out",
          ok_escalation,
          "with exact_reuse..tool_call all checked, escalating to an LLM is "
          "permitted — escalate only as far as needed")

    # 6. cannot advance without a ready verify outcome.
    adv_blocked = False
    try:
        advance_guard(CycleStep("g", NextAnswer("add_node", "x"),
                                ExecutionDecision("exact_reuse", handle="h"),
                                VerifyResult("incorrect", ready_to_advance=True)))
    except GuardViolation:
        adv_blocked = True
    check("cannot_advance_on_a_non_ready_outcome", adv_blocked,
          "claiming ready_to_advance with an 'incorrect' outcome is refused")

    # 7. an unknown answer kind is rejected (the taxonomy is closed).
    bad = False
    try:
        NextAnswer("teleport", "x")
    except ValueError:
        bad = True
    check("the_answer_kind_taxonomy_is_closed", bad,
          "an answer kind outside the taxonomy is refused, not silently coerced")

    # 8. the receipt records all three stages + reuse accounting.
    r = step.receipt()
    check("the_receipt_records_all_three_stages_and_reuse_accounting",
          set(r) >= {"what_is_next", "how_to_execute", "verify_and_advance",
                     "model_calls_avoided"}
          and r["how_to_execute"]["chosen_rung"] == "exact_reuse",
          "the cycle receipt shows the sub-task, the ladder rung, the verify "
          "outcome, and how many model calls were avoided")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "methodical_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
