"""Practitioner review mode — interrogate an (input, output) pair before trust.

Owner ask (2026-08-23): a mode that REVIEWS inputs and outputs and asks
interrogatory questions.  Motivating case: a submission scored 0.500 macro-AUC —
the exact score of a coin flip — and the system reported it as a milestone
without saying, in the same breath, "this output is DEGENERATE: constant
predictions, chance-level score."  Review mode says that unprompted.

Two layers, cheap first:

  1. **Deterministic degeneracy detectors** — no model call:
     constant output, empty/missing output, chance-level score for the metric
     (AUC ~0.5, accuracy ~majority prevalence, correlation ~0), and
     too-perfect (>= 0.99, which routes to the adversarial-audit bias).
  2. **The interrogatory battery** — the standing questions asked of every
     reviewed pair (what was the input? what is the output SUPPOSED to be?
     does it answer the objective? what would make it wrong? is the score
     meaningful or degenerate? what is missing?), answered deterministically
     where possible and through the question-engine forms + strict call DAG
     when a model is warranted (injectable, offline-testable).

The verdict vocabulary is closed: pass / pass_with_notes / degenerate / fail.
A degenerate output is not a failure of execution — it is an output that
CARRIES NO INFORMATION, and it must be named as such wherever it appears.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

REVIEW_VERDICTS = ("pass", "pass_with_notes", "degenerate", "fail")

# The standing interrogatories — asked of EVERY reviewed pair, in this order.
INTERROGATORIES = (
    "What was the input, and where did it come from?",
    "What is the output supposed to look like (its contract)?",
    "Is the output degenerate — constant, empty, or chance-level?",
    "Does the output actually answer the objective?",
    "What would make this output wrong?",
    "Is the score meaningful for this metric, or is it the score of doing "
    "nothing?",
    "What is missing from this output?",
)

# Chance floors: what "doing nothing" scores for common metrics.
_CHANCE = {
    "auc": 0.5, "roc_auc": 0.5, "macro_auc": 0.5, "gini": 0.0,
    "correlation": 0.0, "r2": 0.0,
}


@dataclass
class ReviewFinding:
    check: str
    ok: bool
    detail: str = ""


@dataclass
class ReviewReport:
    verdict: str
    findings: list = field(default_factory=list)
    interrogation: list = field(default_factory=list)  # question -> answer rows
    plain_summary: str = ""

    def __post_init__(self):
        if self.verdict not in REVIEW_VERDICTS:
            raise ValueError(f"verdict must be one of {REVIEW_VERDICTS}")

    def receipt(self) -> dict:
        return {"record_type": "practitioner_review/v1",
                "verdict": self.verdict,
                "findings": [{"check": f.check, "ok": f.ok,
                              "detail": f.detail} for f in self.findings],
                "interrogation": self.interrogation,
                "plain_summary": self.plain_summary}


# ---------------------------------------------------------------------------
# Layer 1 — deterministic degeneracy detectors.
# ---------------------------------------------------------------------------


def detect_constant_output(values: Sequence) -> "ReviewFinding":
    vals = list(values)
    if not vals:
        return ReviewFinding("constant_output", False, "output is EMPTY")
    distinct = len({repr(v) for v in vals})
    if distinct == 1:
        return ReviewFinding(
            "constant_output", False,
            f"all {len(vals)} output values are identical ({vals[0]!r}) — a "
            f"constant output carries no ranking information")
    return ReviewFinding("constant_output", True,
                         f"{distinct} distinct values across {len(vals)}")


def detect_chance_level(metric: str, score: float, *,
                        majority_prevalence: "float | None" = None,
                        tolerance: float = 0.02) -> "ReviewFinding":
    """Is this score what DOING NOTHING would earn?  AUC 0.5 is a coin flip;
    accuracy equal to the majority prevalence is the always-say-majority
    score; correlation 0 is noise."""
    m = metric.lower().replace("-", "_").replace(" ", "_")
    floor = _CHANCE.get(m)
    if floor is None and m in ("accuracy", "acc"):
        floor = majority_prevalence
    if floor is None:
        return ReviewFinding("chance_level_score", True,
                             f"no chance floor known for metric {metric!r}")
    if abs(score - floor) <= tolerance:
        return ReviewFinding(
            "chance_level_score", False,
            f"{metric}={score:g} is the score of doing nothing (chance floor "
            f"{floor:g}) — it validates plumbing, never performance")
    if score < floor - tolerance:
        return ReviewFinding(
            "chance_level_score", False,
            f"{metric}={score:g} is BELOW the chance floor {floor:g} — the "
            f"output is anti-correlated or mis-mapped")
    return ReviewFinding("chance_level_score", True,
                         f"{metric}={score:g} clears the chance floor "
                         f"{floor:g}")


def detect_too_perfect(score: float, *, threshold: float = 0.99
                       ) -> "ReviewFinding":
    if score >= threshold:
        return ReviewFinding(
            "too_perfect", False,
            f"score {score:g} >= {threshold} — near-perfect demands a "
            f"leakage/validity audit before trust (bias:"
            f"adversarial_on_perfection)")
    return ReviewFinding("too_perfect", True, f"score {score:g} is plausible")


# ---------------------------------------------------------------------------
# Layer 2 — the review itself.
# ---------------------------------------------------------------------------


def review(*, objective: str, input_summary: str, output_values: Sequence = (),
           output_contract: str = "", metric: str = "",
           score: "float | None" = None,
           majority_prevalence: "float | None" = None,
           ask: "Callable | None" = None,
           models: "Sequence[str] | None" = None) -> ReviewReport:
    """Run review mode over one (input, output) pair.

    Deterministic checks always run.  When ``ask`` is provided (the strict
    call DAG or a stub), the open interrogatories — does it answer the
    objective, what would make it wrong, what is missing — are put to a model
    through the question-engine forms; otherwise they are recorded as OPEN
    questions rather than silently skipped."""
    findings: list = []
    interrogation: list = []

    interrogation.append({"q": INTERROGATORIES[0], "a": input_summary})
    interrogation.append({"q": INTERROGATORIES[1],
                          "a": output_contract or "no contract declared "
                          "(a finding in itself)"})
    if not output_contract:
        findings.append(ReviewFinding("output_contract_declared", False,
                                      "no output contract declared"))

    if output_values is not None and len(list(output_values)) >= 0:
        f_const = detect_constant_output(list(output_values))
        findings.append(f_const)
    if score is not None and metric:
        f_chance = detect_chance_level(metric, score,
                                       majority_prevalence=majority_prevalence)
        findings.append(f_chance)
        findings.append(detect_too_perfect(score))
        interrogation.append({"q": INTERROGATORIES[5],
                              "a": f_chance.detail})
    degenerate_hits = [f for f in findings
                       if not f.ok and f.check in ("constant_output",
                                                   "chance_level_score")]
    interrogation.append({"q": INTERROGATORIES[2],
                          "a": ("; ".join(f.detail for f in degenerate_hits)
                                if degenerate_hits else "no degeneracy "
                                "detected deterministically")})

    # Open interrogatories: model-backed when an ask fn is given.
    open_qs = [INTERROGATORIES[3], INTERROGATORIES[4], INTERROGATORIES[6]]
    if ask is not None:
        from ..static_architecture.model_call import AskSpec
        from ..strings.question_engine import core_forms
        forms = core_forms()
        payload = (f"Objective: {objective}\nInput: {input_summary}\n"
                   f"Output sample: {str(list(output_values)[:8])[:300]}"
                   + (f"\nScore: {metric}={score}" if score is not None
                      else ""))
        for q, form_name in zip(open_qs, ("verify_check", "premortem",
                                          "whats_missing")):
            form = forms[form_name]
            slots = {"task": payload, "candidate": "the output above",
                     "options": "the output above"}
            spec = AskSpec(question=form.render(
                **{k: v for k, v in slots.items() if k in form.slots}))
            if models:
                spec.models = tuple(models)
            res = ask(spec)
            interrogation.append({
                "q": q, "a": (res.text[:400] if getattr(res, "ok", False)
                              else f"ask failed: {getattr(res, 'error', '')}")})
    else:
        for q in open_qs:
            interrogation.append({"q": q, "a": "OPEN — no model review was "
                                  "run; this question remains unanswered"})

    # Verdict.
    hard_fail = any(not f.ok and f.check == "constant_output"
                    and "EMPTY" in f.detail for f in findings)
    if hard_fail:
        verdict = "fail"
        summary = "the output is empty — nothing to trust or score"
    elif degenerate_hits:
        verdict = "degenerate"
        summary = ("the output carries no information: "
                   + "; ".join(f.detail for f in degenerate_hits))
    elif any(not f.ok for f in findings):
        verdict = "pass_with_notes"
        summary = "; ".join(f.detail for f in findings if not f.ok)
    else:
        verdict = "pass"
        summary = "no degeneracy detected; open interrogatories " + \
            ("answered" if ask is not None else "remain open")
    return ReviewReport(verdict=verdict, findings=findings,
                        interrogation=interrogation, plain_summary=summary)


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. THE MOTIVATING CASE: a constant-prediction submission at AUC 0.5 is
    # named DEGENERATE, in plain English, unprompted.
    r = review(objective="rank knee studies by 12 findings",
               input_summary="hidden test studies (images only)",
               output_values=[0.41] * 50, output_contract="submission.csv, "
               "one probability per label per study", metric="macro_auc",
               score=0.500)
    check("a_constant_chance_level_submission_is_named_degenerate",
          r.verdict == "degenerate"
          and "coin" not in r.plain_summary  # plain words, not slang
          and "no ranking information" in r.plain_summary
          and "score of doing nothing" in r.plain_summary,
          r.plain_summary[:120])

    # 2. a below-chance score is flagged as anti-correlated/mis-mapped.
    r2 = review(objective="x", input_summary="i", output_values=[0.1, 0.9],
                output_contract="c", metric="auc", score=0.31)
    check("a_below_chance_score_is_flagged_as_mismapped",
          any("BELOW the chance floor" in f.detail for f in r2.findings)
          and r2.verdict == "degenerate",
          "0.31 AUC means anti-correlation, not mere weakness")

    # 3. a real-variance output clearing chance passes.
    r3 = review(objective="x", input_summary="i",
                output_values=[0.2, 0.7, 0.4, 0.9],
                output_contract="c", metric="auc", score=0.71)
    check("a_real_output_with_a_real_score_passes",
          r3.verdict == "pass" and all(
              f.ok for f in r3.findings),
          "0.71 AUC with varied predictions is reviewable work")

    # 4. too-perfect routes to the adversarial audit.
    r4 = review(objective="x", input_summary="i",
                output_values=[0.2, 0.7, 0.4], output_contract="c",
                metric="auc", score=0.997)
    check("too_perfect_routes_to_the_adversarial_audit",
          r4.verdict == "pass_with_notes"
          and any("adversarial_on_perfection" in f.detail
                  for f in r4.findings),
          "0.997 is a leakage audit, not a celebration")

    # 5. accuracy's chance floor is the majority prevalence.
    r5 = review(objective="x", input_summary="i",
                output_values=[1, 1, 1, 0], output_contract="c",
                metric="accuracy", score=0.78, majority_prevalence=0.78)
    check("accuracy_at_majority_prevalence_is_the_doing_nothing_score",
          r5.verdict == "degenerate",
          "0.78 accuracy when 78% are the majority class = always-say-majority")

    # 6. an empty output is a hard FAIL, distinct from degenerate.
    r6 = review(objective="x", input_summary="i", output_values=[],
                output_contract="c")
    check("an_empty_output_is_a_hard_fail", r6.verdict == "fail",
          "nothing to trust or score")

    # 7. without a model, the open interrogatories are recorded OPEN — never
    # silently skipped; with a stub ask, they are answered.
    r7 = review(objective="x", input_summary="i", output_values=[1, 2],
                output_contract="c")
    open_count = sum(1 for row in r7.interrogation
                     if str(row["a"]).startswith("OPEN"))
    class _A:
        ok = True
        text = "the output answers the objective; risks: overfit"
        error = ""
    r8 = review(objective="x", input_summary="i", output_values=[1, 2],
                output_contract="c", ask=lambda spec: _A())
    answered = sum(1 for row in r8.interrogation
                   if "overfit" in str(row["a"]))
    check("open_interrogatories_are_open_not_skipped_and_answerable",
          open_count == 3 and answered == 3,
          "the battery is honest about what was not asked")

    # 8. every reviewed pair carries the full standing interrogation.
    check("every_review_asks_the_standing_interrogatories",
          len(r.interrogation) >= len(INTERROGATORIES) - 1
          and r.receipt()["record_type"] == "practitioner_review/v1",
          f"{len(r.interrogation)} interrogation rows in the receipt")

    passed = sum(1 for r_ in results if r_["passed"])
    return {"record_type": "review_mode_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
