"""Structural decision biases — standing instincts that must EARN their keep.

Owner rules (2026-08-23): keep the biases, but (a) no ``baseline_first`` —
removed; and (b) biases are not dogma: **learning/training runs adversarially
validate them by trying the alternatives**.  A bias that repeatedly loses to
its own alternative is demoted by evidence, exactly like any other resource —
muscle memory never becomes destiny.

The standing biases (each deterministic, each tagged ``bias:<name>`` in the
candidate rationale so a biased choice is never a mystery):

  1. adversarial_on_perfection — a near-perfect result outranks EVERYTHING
                                 until audited (near-perfect demands leakage
                                 review before trust)
  2. diagnose_after_repeated_failure — two failures of the same shape ->
                                 diagnosing outranks retrying
  3. pilot_before_full         — expensive and unproven -> a cheap pilot twin
                                 is injected ahead of the full run
  4. distill_after_repetition  — the same expensive decision keeps recurring ->
                                 distilling it outranks paying again
  5. simplicity_tiebreak       — among tied candidates the CHEAPER one wins
plus the two wired elsewhere: research_first_on_missing_info and
enrich_first_on_weak_coverage.

**Adversarial validation of the biases themselves**: ``paired_trial`` names the
two arms (bias followed vs bias suppressed); a training run executes both and
``record_paired_outcome`` writes the result to the append-only ``BiasLedger``.
``verdict`` turns accumulated trials into one of: the bias earns its keep, the
bias loses (demote), or insufficient evidence.  ``apply_biases`` consults the
ledger and auto-suppresses demoted biases — retirement by evidence, never by
argument.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Sequence

from ..loop.kernel import CandidateAction, PractitionerState, Situation

# The registry — every standing bias, its trigger, why it exists, and its
# ALTERNATIVE (what the adversarial arm does instead).
BIAS_REGISTRY = {
    "research_first_on_missing_info": {
        "trigger": "situation signals missing_info",
        "why": "with little known, reducing the gap outranks acting blind",
        "alternative": "attempt the task directly with what is known",
        "wired_in": "kernel.default_select_next_action / model impls"},
    "generate_context_first": {
        "trigger": "early in the run (no context generated yet) with work to do",
        "why": "generating domain personas/questions/key phrases as the FIRST "
               "move gives every later step a richer, reusable context bank",
        "alternative": "start solving immediately with the generic banks"},
    "enrich_first_on_weak_coverage": {
        "trigger": "the persona/question banks do not cover the domain",
        "why": "generate context once, store, reuse forever",
        "alternative": "proceed with the generic banks",
        "wired_in": "kernel_model_impls (EnrichmentPolicy)"},
    "blueprint_first": {
        "trigger": "early in a multi-step run with no working blueprint yet",
        "why": "an outline then detailed-outline blueprint grounds a long "
               "(100/1000/10000-step) task so the agent does not drift or rush "
               "at step 40 of 100 — the blueprint is re-fed to context every pass",
        "alternative": "proceed step-by-step with no explicit plan"},
    "adversarial_review_along_the_way": {
        "trigger": "an artifact or built graph exists that has not been "
                   "adversarially reviewed yet",
        "why": "an adversarial reviewer interrogates the graph AT VARIOUS "
               "STEPS — not only at the end — so a flaw is caught while it is "
               "cheap to fix",
        "alternative": "trust each built artifact without interrogation"},
    "adversarial_on_perfection": {
        "trigger": "a near-perfect score fact (>= 0.99)",
        "why": "near-perfect demands a leakage/validity review before trust",
        "alternative": "trust the score and proceed"},
    "diagnose_after_repeated_failure": {
        "trigger": ">= 2 documented failures in the run",
        "why": "work the cause, do not recompute the failing gate",
        "alternative": "retry with adjusted parameters"},
    "pilot_before_full": {
        "trigger": "a candidate is expensive (cost >= 5) and unproven "
                   "(confidence < 0.8)",
        "why": "PILOT before FULL_SWEEP — scale after the small class passes",
        "alternative": "run at full scale immediately"},
    "distill_after_repetition": {
        "trigger": "the same expensive decision recurred >= 3 times",
        "why": "stop paying for a decision the system already knows",
        "alternative": "keep paying the model each time"},
    "simplicity_tiebreak": {
        "trigger": "two candidates tie on value and confidence",
        "why": "a heavier option must earn its complexity",
        "alternative": "break ties toward the more elaborate candidate"},
}

TRIAL_ARMS = ("followed", "alternative")
BIAS_VERDICTS = ("earns_its_keep", "demote", "insufficient_evidence")


def _near_perfect(state: PractitionerState) -> bool:
    for k, v in state.facts.items():
        if k.startswith(("score:", "metric:")):
            try:
                if float(v) >= 0.99:
                    return True
            except (TypeError, ValueError):
                continue
    return bool(state.facts.get("near_perfect_result"))


# ---------------------------------------------------------------------------
# The bias ledger — append-only trial outcomes; verdicts demote by evidence.
# ---------------------------------------------------------------------------


@dataclass
class BiasTrial:
    bias: str
    followed_score: float
    alternative_score: float
    note: str = ""

    @property
    def winner(self) -> str:
        if self.followed_score > self.alternative_score:
            return "followed"
        if self.alternative_score > self.followed_score:
            return "alternative"
        return "tie"


class BiasLedger:
    """Append-only record of paired bias trials (in-memory + optional JSONL)."""

    def __init__(self, path: str | None = None):
        self.path = path
        self._trials: list[BiasTrial] = []
        if path and os.path.exists(path):
            with open(path) as fh:
                for line in fh:
                    try:
                        self._trials.append(BiasTrial(**json.loads(line)))
                    except Exception:                           # noqa: BLE001
                        continue

    def record(self, trial: BiasTrial) -> None:
        if trial.bias not in BIAS_REGISTRY:
            raise ValueError(f"unknown bias {trial.bias!r}")
        self._trials.append(trial)
        if self.path:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            with open(self.path, "a") as fh:
                fh.write(json.dumps(asdict(trial)) + "\n")

    def trials_for(self, bias: str) -> list:
        return [t for t in self._trials if t.bias == bias]

    def verdict(self, bias: str, *, min_trials: int = 4) -> dict:
        """The evidence-driven verdict.  A bias is demoted only when it has
        enough paired trials AND its alternative wins a clear majority — a
        standing instinct is kept until evidence retires it, and 'insufficient
        evidence' is an honest answer, not a default win for either side."""
        ts = self.trials_for(bias)
        f = sum(1 for t in ts if t.winner == "followed")
        a = sum(1 for t in ts if t.winner == "alternative")
        if len(ts) < min_trials:
            v = "insufficient_evidence"
        elif a > f and a >= 0.6 * len(ts):
            v = "demote"
        else:
            v = "earns_its_keep"
        return {"bias": bias, "trials": len(ts), "followed_wins": f,
                "alternative_wins": a, "verdict": v}

    def demoted(self, *, min_trials: int = 4) -> tuple:
        return tuple(b for b in BIAS_REGISTRY
                     if self.verdict(b, min_trials=min_trials)["verdict"]
                     == "demote")


def paired_trial(bias: str) -> dict:
    """The two arms of one adversarial bias validation, for a training run:
    arm A follows the bias (suppress nothing), arm B suppresses exactly it.
    A caller runs BOTH arms on the same problem and records the outcome."""
    if bias not in BIAS_REGISTRY:
        raise ValueError(f"unknown bias {bias!r}")
    return {"bias": bias,
            "followed": {"suppress": ()},
            "alternative": {"suppress": (bias,)},
            "alternative_means": BIAS_REGISTRY[bias]["alternative"]}


def record_paired_outcome(ledger: BiasLedger, bias: str, *,
                          followed_score: float, alternative_score: float,
                          note: str = "") -> dict:
    ledger.record(BiasTrial(bias, followed_score, alternative_score, note))
    return ledger.verdict(bias)


# ---------------------------------------------------------------------------
# Applying the biases — with per-bias suppression and ledger-driven demotion.
# ---------------------------------------------------------------------------


def apply_biases(state: PractitionerState, situation: Situation,
                 candidates: Sequence[CandidateAction], *,
                 suppress: Sequence[str] = (),
                 ledger: "BiasLedger | None" = None) -> list:
    """Apply the standing biases, deterministically.

    ``suppress`` disables named biases for this run (the adversarial arm of a
    training trial); a ``ledger`` additionally auto-suppresses biases the
    evidence has demoted.  Injections carry ``bias:<name>`` rationales; the
    ordering implements the simplicity tie-break unless that bias is off."""
    off = set(suppress)
    if ledger is not None:
        off |= set(ledger.demoted())
    out = list(candidates)
    have = {c.action.lower() for c in out}

    # generate_context_first: early in a run, generating personas/questions/key
    # phrases is the highest-value FIRST move — it enriches every later step.
    early = state.version <= 1
    context_made = any(k.startswith(("enriched:", "context_generated"))
                       for k in state.facts)
    if ("generate_context_first" not in off and early and not context_made
            and any(c.kind not in ("deliver", "enrich") for c in out)
            and not any("generate_context" in a for a in have)):
        out.append(CandidateAction(
            action="generate_context_and_personas", kind="enrich",
            rationale="bias:generate_context_first — build the domain persona/"
            "question/key-phrase bank before solving; generate once, reuse "
            "forever",
            expected_value=0.98, confidence=0.82, information_gain=0.95,
            estimated_cost=1.0))

    # blueprint_first: early in a run, an explicit outline->detailed plan grounds
    # a long-horizon task so the agent never drifts or rushes mid-pipeline.
    made_blueprint = any(k.startswith(("has_blueprint", "blueprint_ready"))
                         for k in state.facts)
    if ("blueprint_first" not in off and state.version <= 2
            and not made_blueprint
            and any(c.kind not in ("deliver", "enrich") for c in out)
            and not any("blueprint" in a for a in have)):
        out.append(CandidateAction(
            action="generate_working_blueprint", kind="task",
            rationale="bias:blueprint_first — outline then detail the whole "
            "solution so a long task stays grounded (re-fed to context each pass)",
            expected_value=0.96, confidence=0.8, information_gain=0.85,
            estimated_cost=1.0))

    # adversarial_review_along_the_way: any unreviewed artifact gets an
    # interrogation candidate injected NOW — reviewers fire at various steps,
    # not only at delivery.
    if "adversarial_review_along_the_way" not in off:
        for name, ref in state.artifacts.items():
            if (not state.facts.get(f"reviewed:{name}")
                    and f"review:{name}".lower() not in have):
                out.append(CandidateAction(
                    action=f"review:{name}", kind="review",
                    rationale="bias:adversarial_review_along_the_way — "
                    "interrogate this artifact (degeneracy, contract, "
                    "'what would make it wrong?') before building on it",
                    expected_value=0.94, confidence=0.85,
                    information_gain=0.7, estimated_cost=0.6))
                break                       # one interrogation per pass

    if ("adversarial_on_perfection" not in off and _near_perfect(state)
            and not state.facts.get("perfection_audited")):
        out.append(CandidateAction(
            action="audit_near_perfect_result", kind="task",
            rationale="bias:adversarial_on_perfection — near-perfect demands "
            "a leakage/validity review before trust",
            expected_value=0.99, confidence=0.9, information_gain=0.9,
            estimated_cost=1.0))

    if ("diagnose_after_repeated_failure" not in off
            and len(state.failures) >= 2
            and not any("diagnose" in a for a in have)):
        out.append(CandidateAction(
            action="diagnose_repeated_failure", kind="task",
            rationale="bias:diagnose_after_repeated_failure — work the cause, "
            "not the retry",
            expected_value=0.96, confidence=0.8, information_gain=0.8,
            estimated_cost=0.8))

    if "pilot_before_full" not in off:
        for c in list(out):
            if (c.estimated_cost >= 5.0 and c.confidence < 0.8
                    and not c.action.startswith("pilot:")
                    and f"pilot:{c.action.lower()}" not in have):
                out.append(CandidateAction(
                    action=f"pilot:{c.action}", kind=c.kind,
                    rationale=f"bias:pilot_before_full — prove {c.action!r} "
                    "small before paying for it at full scale",
                    expected_value=min(1.0, c.expected_value + 0.02),
                    confidence=min(1.0, c.confidence + 0.1),
                    information_gain=0.7, estimated_cost=1.0))

    if ("distill_after_repetition" not in off
            and int(state.facts.get("expensive_decision_repeats", 0) or 0)
            >= 3):
        out.append(CandidateAction(
            action="distill_repeated_decision", kind="task",
            rationale="bias:distill_after_repetition — stop paying for a "
            "decision the system already knows",
            expected_value=0.9, confidence=0.85, estimated_cost=1.5))

    if "simplicity_tiebreak" not in off:
        out.sort(key=lambda c: (-c.expected_value, -c.confidence,
                                c.estimated_cost, c.action))
    else:                       # the adversarial arm: ties favor the ELABORATE
        out.sort(key=lambda c: (-c.expected_value, -c.confidence,
                                -c.estimated_cost, c.action))
    return out


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    from ..loop.kernel import ProblemSpec
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    spec = ProblemSpec(objective="win", success_criteria=("model",))
    sit = Situation(summary="s", unknowns=("model",))

    def top(cands):
        return max(cands, key=lambda c: (c.expected_value, c.confidence))

    # 1. baseline_first is GONE; generate_context_first fires as the biased
    # FIRST action on an early run and outranks the plain task.
    st = PractitionerState(spec=spec)
    cands = apply_biases(st, sit, [CandidateAction(
        "estimator=xgboost", kind="task", expected_value=0.8,
        confidence=0.7)])
    check("baseline_removed_and_generate_context_is_the_biased_first_action",
          "baseline_first" not in BIAS_REGISTRY
          and not any("baseline" in c.action for c in cands)
          and top(cands).action == "generate_context_and_personas"
          and "bias:generate_context_first" in top(cands).rationale,
          "generate context/personas first; then solve with a richer bank")

    # 1b. adversarial reviewers fire ALONG THE WAY: an unreviewed artifact gets
    # an interrogation candidate injected mid-run, not just at the end.
    st_art = PractitionerState(spec=spec, version=3,
                               facts={"has_baseline": True,
                                      "enriched:x": True},
                               artifacts={"nodes/model.py": "nodes/model.py"})
    cands_art = apply_biases(st_art, sit, [CandidateAction(
        "add_next_node", kind="task", expected_value=0.8, confidence=0.7)])
    check("an_adversarial_reviewer_interrogates_artifacts_along_the_way",
          any(c.action == "review:nodes/model.py" and c.kind == "review"
              for c in cands_art),
          "an unreviewed artifact is interrogated mid-run, before more is "
          "built on it")

    # 1c. a reviewed artifact is not re-interrogated.
    st_rev = PractitionerState(spec=spec, version=3,
                               facts={"has_baseline": True, "enriched:x": True,
                                      "reviewed:nodes/model.py": True},
                               artifacts={"nodes/model.py": "nodes/model.py"})
    cands_rev = apply_biases(st_rev, sit, [CandidateAction(
        "add_next_node", kind="task", expected_value=0.8, confidence=0.7)])
    check("a_reviewed_artifact_is_not_re_interrogated",
          not any(c.action.startswith("review:") for c in cands_rev),
          "review fires once per artifact, not every pass")

    # 2. adversarial_on_perfection outranks everything — unless SUPPRESSED
    # (the adversarial arm of its own trial).
    st2 = PractitionerState(spec=spec, version=3,
                            facts={"score:cv_auc": 0.995, "enriched:x": True})
    on = apply_biases(st2, sit, [CandidateAction(
        "submit_now", kind="task", expected_value=0.97, confidence=0.95)])
    off = apply_biases(st2, sit, [CandidateAction(
        "submit_now", kind="task", expected_value=0.97, confidence=0.95)],
        suppress=("adversarial_on_perfection",))
    check("a_bias_can_be_suppressed_for_its_adversarial_arm",
          top(on).action == "audit_near_perfect_result"
          and top(off).action == "submit_now",
          "arm A audits first; arm B (suppressed) trusts the score — the "
          "paired trial can now measure which arm wins")

    # 3. paired_trial names both arms and what the alternative MEANS.
    pt = paired_trial("pilot_before_full")
    check("paired_trial_defines_both_arms_with_the_alternative_meaning",
          pt["followed"]["suppress"] == ()
          and pt["alternative"]["suppress"] == ("pilot_before_full",)
          and "full scale" in pt["alternative_means"],
          "a training run executes both arms on the same problem")

    # 4. the ledger demotes a bias its alternative consistently beats...
    ledger = BiasLedger()
    for _ in range(4):
        record_paired_outcome(ledger, "distill_after_repetition",
                              followed_score=0.6, alternative_score=0.8)
    v = ledger.verdict("distill_after_repetition")
    check("evidence_demotes_a_bias_its_alternative_consistently_beats",
          v["verdict"] == "demote" and v["alternative_wins"] == 4,
          "retirement by evidence, never by argument")

    # 5. ...and apply_biases auto-suppresses the demoted bias.
    st5 = PractitionerState(spec=spec, facts={
        "expensive_decision_repeats": 3})
    with_ledger = apply_biases(st5, sit, [CandidateAction(
        "decide_again", kind="task", expected_value=0.6, confidence=0.6)],
        ledger=ledger)
    check("a_demoted_bias_no_longer_fires",
          not any(c.action == "distill_repeated_decision"
                  for c in with_ledger),
          "the ledger's verdict governs the live path")

    # 6. insufficient evidence keeps a bias ACTIVE (honest third answer).
    ledger2 = BiasLedger()
    record_paired_outcome(ledger2, "pilot_before_full",
                          followed_score=0.4, alternative_score=0.9)
    v2 = ledger2.verdict("pilot_before_full")
    st6 = PractitionerState(spec=spec, version=3,
                            facts={"enriched:x": True})
    still_on = apply_biases(st6, sit, [CandidateAction(
        "full_sweep", kind="task", expected_value=0.9, confidence=0.6,
        estimated_cost=50.0)], ledger=ledger2)
    check("one_trial_is_insufficient_evidence_and_the_bias_stays_active",
          v2["verdict"] == "insufficient_evidence"
          and any(c.action.startswith("pilot:") for c in still_on),
          "a standing instinct is kept until enough paired evidence retires it")

    # 7. the tie-break's adversarial arm deterministically favors elaborate.
    st7 = PractitionerState(spec=spec, version=3,
                            facts={"enriched:x": True})
    tie = [CandidateAction("heavy_stack", kind="task", expected_value=0.8,
                           confidence=0.8, estimated_cost=10.0),
           CandidateAction("single_model", kind="task", expected_value=0.8,
                           confidence=0.8, estimated_cost=1.0)]
    a = apply_biases(st7, sit, tie)
    b = apply_biases(st7, sit, tie, suppress=("simplicity_tiebreak",))
    check("the_tiebreak_arms_are_both_deterministic_and_opposite",
          a[0].action == "single_model" and b[0].action == "heavy_stack",
          "arm A: cheaper wins; arm B: elaborate wins — measurable either way")

    # 8. the ledger persists append-only and reloads.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "bias_trials.jsonl")
        l1 = BiasLedger(p)
        record_paired_outcome(l1, "simplicity_tiebreak",
                              followed_score=0.9, alternative_score=0.4)
        l2 = BiasLedger(p)
        check("bias_trials_persist_append_only_and_reload",
              len(l2.trials_for("simplicity_tiebreak")) == 1,
              "training evidence survives a restart")

    # 9. every registry entry documents trigger, why, AND its alternative.
    check("every_bias_documents_trigger_why_and_alternative",
          all(("trigger" in b and "why" in b and "alternative" in b)
              for b in BIAS_REGISTRY.values())
          and len(BIAS_REGISTRY) == 10,
          f"{len(BIAS_REGISTRY)} standing biases, each with its adversarial "
          f"alternative named")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "biases_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
