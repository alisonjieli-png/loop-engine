"""Run quality — did the calls help, is the loop stuck, does learning digest?

Architectural role: Code Node system (quality analysis over run histories).

Owns:
    - ModelCallContribution: before/after evaluation per semantic call with an
      explicit ``attribution_confidence`` — temporal association is NEVER
      presented as causal proof (a matched control or ablation is required
      for anything stronger);
    - marginal metrics: quality per call / per 1,000 tokens; calls with zero
      measurable downstream effect;
    - StucknessReport: co-occurring indicators (repeated equivalent work,
      escalation chains, rising tokens without quality gain, oscillation) →
      score + suggested interventions from the failure-response vocabulary;
    - LearningDigestibility: the checklist that answers "can this output
      become reusable memory?", with a low score recommending a structuring
      spawned loop (a recommendation — the caller spawns it).

Does not own:
    - the event store (run_history.py), rollups (run_analytics.py), rendering
      (run_playback.py), or applying any intervention.

Public entry points:
    - call_contributions(run_history_events, evaluations) -> list[dict]
    - stuckness_report(run_history_events) -> dict
    - digestibility(record) -> dict

Key invariants:
    - attribution_confidence ∈ {temporal_association, matched_control,
      ablation}; only the last two may ever ground a causal claim;
    - unknown quality stays unknown — never coerced to zero.

Verification: self_test() (folded into the package suite).
"""
from __future__ import annotations

from collections import Counter

INTERVENTIONS = ("compress_context", "replace_loop_template",
                 "spawn_history_blind_loop", "switch_resolution_mode",
                 "research_the_blocker", "invoke_another_model",
                 "simplify_objective", "revert_to_checkpoint",
                 "retrieve_prior_solution", "stop_branch")

ATTRIBUTION = ("temporal_association", "matched_control", "ablation")


def call_contributions(events, evaluations=()) -> list:
    """One contribution record per semantic invocation.  ``evaluations`` are
    (sequence_number, quality) observations made by the caller's oracle;
    quality before/after a call is the nearest evaluation on each side —
    a temporal association, labeled as exactly that."""
    evals = sorted(evaluations)
    out = []
    for e in events:
        if getattr(e, "event_type", e.get("event_type") if isinstance(e, dict)
                   else "") != "model_invocation":
            continue
        seq = e.sequence_number if not isinstance(e, dict) \
            else e["sequence_number"]
        before = [q for s, q in evals if s < seq]
        after = [q for s, q in evals if s > seq]
        qb = before[-1] if before else None
        qa = after[0] if after else None
        delta = (qa - qb) if (qa is not None and qb is not None) else None
        tok = ((e.prompt_tokens + e.eval_tokens)
               if not isinstance(e, dict)
               else e.get("prompt_tokens", 0) + e.get("eval_tokens", 0))
        out.append({
            "record_type": "model_call_contribution/v1",
            "model_call_seq": seq,
            "quality_before": qb, "quality_after": qa,
            "quality_delta": delta,
            "tokens": tok,
            "gain_per_1k_tokens": (round(delta / tok * 1000, 6)
                                   if delta is not None and tok else None),
            "zero_measurable_effect": (delta is not None
                                       and abs(delta) < 1e-9),
            "attribution_confidence": "temporal_association",
            "note": "temporal association only — a causal claim needs a "
                    "matched control or ablation"})
    return out


def stuckness_report(events) -> dict:
    """Co-occurring stuckness indicators over canonical events."""
    def f(e, k, d=""):
        return getattr(e, k, None) if not isinstance(e, dict) else e.get(k, d)

    step_by_loop: Counter = Counter()
    escalations = deferrals = budget_stops = fallbacks = 0
    outputs: Counter = Counter()
    for e in events:
        et = f(e, "event_type")
        if et == "iteration":
            step_by_loop[(f(e, "loop_id"), f(e, "step"))] += 1
            out = str((f(e, "detail") or {}).get("output", ""))[:120]
            if out:
                outputs[out] += 1
            if f(e, "mode") in ("hybrid", "non_deterministic"):
                escalations += 1
        elif et == "fallback":
            fallbacks += 1
        elif et == "model_boundary_deferred":
            deferrals += 1
        elif et == "budget_stop":
            budget_stops += 1

    indicators = []
    repeated_work = [(k, n) for k, n in step_by_loop.items() if n > 2]
    if repeated_work:
        indicators.append({"indicator": "repeated_equivalent_work",
                           "detail": [f"{l}:{s} x{n}"
                                      for (l, s), n in repeated_work]})
    repeated_out = [(o, n) for o, n in outputs.items() if n > 2]
    if repeated_out:
        indicators.append({"indicator": "repeated_similar_responses",
                           "detail": [f"x{n}: {o[:60]}"
                                      for o, n in repeated_out]})
    if fallbacks + deferrals >= 3:
        indicators.append({"indicator": "escalation_chain",
                           "detail": [f"{fallbacks} fallbacks, "
                                      f"{deferrals} deferrals"]})
    if budget_stops:
        indicators.append({"indicator": "budget_exhaustion",
                           "detail": [f"{budget_stops} budget stop(s)"]})

    score = min(1.0, 0.3 * len(indicators)
                + 0.05 * sum(n - 2 for _, n in repeated_work))
    suggestions = []
    if repeated_work:
        suggestions += ["replace_loop_template", "simplify_objective",
                        "retrieve_prior_solution"]
    if fallbacks + deferrals >= 3:
        suggestions += ["switch_resolution_mode", "invoke_another_model"]
    if budget_stops:
        suggestions += ["compress_context", "stop_branch"]
    return {"record_type": "stuckness_report/v1",
            "stuckness_score": round(score, 3),
            "dominant_indicators": indicators,
            "suggested_interventions": [s for s in dict.fromkeys(suggestions)
                                        if s in INTERVENTIONS],
            "confidence": "heuristic (co-occurrence, not diagnosis)"}


DIGESTIBILITY_CHECKS = (
    "structured_output_valid", "provenance_complete", "categories_assigned",
    "applicability_defined", "confidence_present", "evidence_linked",
    "reusable_question_extracted", "reusable_heuristic_extracted",
    "possible_code_target_identified", "deduplication_status_known",
    "validation_requirements_known")


def digestibility(record: dict) -> dict:
    """Score whether a raw output can become reusable memory.  ``record`` maps
    check names to booleans (absent = failed — fail-closed).  A low score
    RECOMMENDS spawning a structuring spawned loop; it never spawns one."""
    checks = {c: bool(record.get(c)) for c in DIGESTIBILITY_CHECKS}
    score = round(sum(checks.values()) / len(checks), 3)
    failed = [c for c, ok in checks.items() if not ok]
    return {"record_type": "learning_digestibility/v1",
            "checks": checks, "digestibility_score": score,
            "failed": failed,
            "recommendation": (
                "digestible — stage as candidate" if score >= 0.7 else
                "spawn a 'normalize and extract reusable learning' spawned "
                "loop before this output touches shared memory")}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"name": name, "passed": bool(ok), "note": note})

    from ..static_architecture.run_history import RunHistory

    ch = RunHistory("q_run")
    ch.append("run_started")
    ch.append("loop_init", loop_id="loop1", detail={"depth": 0})
    ch.append("evaluation", loop_id="loop1", detail={"quality": 0.80})
    e_eval1 = ch.event_log[-1].sequence_number
    ch.append("model_invocation", loop_id="loop1", step="research",
              mode="hybrid", model="m", prompt_tokens=100, eval_tokens=400)
    call_seq = ch.event_log[-1].sequence_number
    ch.append("evaluation", loop_id="loop1", detail={"quality": 0.83})
    e_eval2 = ch.event_log[-1].sequence_number
    for _ in range(3):
        ch.append("iteration", loop_id="loop1", step="repair", mode="deterministic",
                  detail={"output": "same fix attempt"})
    ch.append("fallback", loop_id="loop1")
    ch.append("fallback", loop_id="loop1")
    ch.append("model_boundary_deferred", loop_id="loop1")
    ch.append("budget_stop", loop_id="loop1")

    # 1. contribution: before/after quality, per-token gain, honest label.
    contrib = call_contributions(ch.event_log,
                                 [(e_eval1, 0.80), (e_eval2, 0.83)])
    c = contrib[0]
    check("call_contribution_quantifies_with_honest_attribution",
          c["model_call_seq"] == call_seq
          and abs(c["quality_delta"] - 0.03) < 1e-9
          and c["tokens"] == 500 and abs(c["gain_per_1k_tokens"] - 0.06) < 1e-6
          and c["attribution_confidence"] == "temporal_association"
          and not c["zero_measurable_effect"],
          f"Δ={c['quality_delta']} over {c['tokens']} tokens — association, "
          "never causation")

    # 2. unknown quality stays unknown (never coerced to zero).
    c2 = call_contributions(ch.event_log, [])[0]
    check("unknown_quality_stays_unknown",
          c2["quality_delta"] is None and c2["gain_per_1k_tokens"] is None)

    # 3. stuckness: co-occurring indicators → score + interventions.
    rep = stuckness_report(ch.event_log)
    inds = {i["indicator"] for i in rep["dominant_indicators"]}
    check("stuckness_report_finds_cooccurring_indicators",
          {"repeated_equivalent_work", "repeated_similar_responses",
           "escalation_chain", "budget_exhaustion"} <= inds
          and rep["stuckness_score"] > 0.5
          and "replace_loop_template" in rep["suggested_interventions"]
          and "stop_branch" in rep["suggested_interventions"],
          f"score {rep['stuckness_score']}; {sorted(inds)}")

    # 4. digestibility: fail-closed checklist; a thin record is sent to a
    # structuring loop, a complete one stages.
    thin = digestibility({"structured_output_valid": True})
    rich = digestibility({c: True for c in DIGESTIBILITY_CHECKS})
    check("digestibility_gates_reusable_memory",
          thin["digestibility_score"] < 0.2
          and "normalize and extract" in thin["recommendation"]
          and rich["digestibility_score"] == 1.0
          and "stage as candidate" in rich["recommendation"],
          f"thin {thin['digestibility_score']} vs rich 1.0")

    passed = sum(1 for r in results if r["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
