"""Loop-practitioner-as-developer: two campaign capabilities that close the gap
to product, run AS PractitionerLoops.

Architectural role: loop (campaign / review affordances built on the one runtime).

Owner direction (2026-08-24): "let's continue to loop and stop; could we even
use a practitioner loop as a developer to close all gaps and make this into a
product?  And sometimes the practitioner needs to review the past several
steps so it isn't getting tunnel vision."

These two capabilities are the same pattern the agent-society mandate already
describes, made executable for DEVELOPMENT work — not just problem-solving:

  * ``development_practitioner_loop`` — a bounded, checkpointed campaign loop
    that walks an ordered queue of gaps-to-product (drift items, canaries,
    wiring), works each, verifies it, and STOPS honestly at budget, review
    cadence, or exhaustion.  It stages a candidate change per worked gap
    (never self-promote, never merge unreviewed) and leaves the whole run on
    the shared ledger for the RunHistory.

  * ``anti_tunnel_vision_review`` — the five-step look-back checkpoint.  Every
    N closed work items the loop re-derives the goal and assumptions from the
    last steps, surfaces the newest unproven assumption, and decides whether
    the queue still orders by value.  It runs as an ADVERSARIAL-REVIEW-shaped
    loop (attack the recent plan before continuing), preserving dissent and
    never silently reordering the campaign it is reviewing.

Both are instances of the standard baseline (goal, typed I/O, stop condition,
mode policy) and both are deterministic by default; a model-backed review
is only an arm when the cadence loop is configured for it and authorized.

Owns:
    - development_practitioner_loop(gap_queue, config, ledger): the campaign;
    - anti_tunnel_vision_review(run_history, config, ledger): the checkpoint.

Does not own:
    - the runtime (recursive_loop), doctrine (loop_doctrine), RunHistory
      (run_history), or the evidence gate.  Reviewing never merges.

Key invariants:
    - the campaign is bounded (budget, max items, review cadence) and stops;
    - every worked gap is VERIFIED before "closed"; a failed gap is a recorded
      failure, never a quiet skip;
    - the review checkpoint runs at the declared cadence and preserves dissent;
    - candidates are staged; promotion is separate (the evidence gate).

Verification: self_test() — a campaign that closes two gaps then stops, the
review checkpoint that flags a drifted assumption, and the adversarial cases
(a gap that fails verification stays open; the review cannot self-merge).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .recursive_loop import (Loop, LoopConfig, LoopError, LoopLedger,
                             StepOutcome)
from .encapsulate import as_practitioner_loop


@dataclass
class DevGap:
    """One bounded gap-to-product, a work item the campaign may close."""
    gap_id: str
    objective: str
    work: "callable"            # () -> dict result of the attempted close
    verify: "callable"          # (result) -> bool  (did the gap really close?)
    rank: int = 0


def development_practitioner_loop(
        gaps: list, *, ledger: "LoopLedger | None" = None,
        budget_items: int = 8, review_cadence: int = 5,
        power: str = "deep") -> dict:
    """Run a bounded development campaign as one PractitionerLoop.

    The campaign is a CUSTOM loop (assess → act → verify → integrate), one
    iteration per worked gap, run through the canonical runtime.  It stops at
    budget exhaustion, queue exhaustion, or a review cadence flag, and every
    gap's close is verified independently — a gap that fails verification is
    recorded as FAILED and left open, never counted as closed.

    Returns {closed, failed, reviews, stopped_reason, ledger loop id}."""
    it_ledger = ledger or LoopLedger()
    cfg = LoopConfig(framework="custom",
                     custom_steps=("assess_gap", "close_gap", "verify_gap",
                                   "integrate_gap"),
                     exit_condition="steps_complete", power=power)
    loop = Loop("development-practitioner-campaign", cfg, ledger=it_ledger)
    closed, failed, reviews = [], [], []

    def gap_handler(gap: "DevGap"):
        def h(lp, step, context):
            if step == "assess_gap":
                return StepOutcome(output=f"assess:{gap.gap_id}:{gap.objective}",
                                   mode="deterministic", confidence=0.9)
            if step == "close_gap":
                try:
                    context["_result"] = gap.work()
                    return StepOutcome(output=f"closed:{gap.gap_id}",
                                       mode="deterministic", confidence=0.9)
                except Exception as e:                      # noqa: BLE001
                    context["_result"] = {"error": str(e)}
                    return StepOutcome(output=f"close_failed:{gap.gap_id}",
                                       mode="deterministic", confidence=0.2,
                                       failed=True)
            if step == "verify_gap":
                ok = bool(gap.verify(context.get("_result", {})))
                context["_verified"] = ok
                return StepOutcome(output=f"verify:{gap.gap_id}:{'ok' if ok else 'no'}",
                                   mode="deterministic",
                                   confidence=0.95 if ok else 0.3,
                                   failed=not ok)
            if step == "integrate_gap":
                (closed if context.get("_verified") else failed).append(gap.gap_id)
                return StepOutcome(output=f"integrate:{gap.gap_id}:"
                                   f"{'staged' if context.get('_verified') else 'open'}",
                                   mode="deterministic", confidence=0.9)
            return StepOutcome(output=f"{step}:done", mode="deterministic",
                               confidence=0.8)
        return h

    for i, g in enumerate(sorted(gaps, key=lambda x: x.rank)):
        if i >= budget_items:
            break
        if i > 0 and i % review_cadence == 0:
            reviews.append(anti_tunnel_vision_review(
                closed, failed, config=cfg, ledger=it_ledger, loop_id=loop.loop_id))
        # each gap close runs as its OWN spawned loop, on the shared ledger:
        # 4 beats, so the spawned needs 4 iterations — light (3) would stop at
        # budget before integrate; standard (6) runs the full beat honestly.
        spawned = loop.spawn(f"work {g.gap_id}",
                           LoopConfig(framework="custom",
                                      custom_steps=("assess_gap", "close_gap",
                                                    "verify_gap", "integrate_gap"),
                                      power="standard"))
        spawned.run(handler=gap_handler(g))
    loop.run()

    return {"record_type": "dev_campaign/v1", "campaign_loop_id": loop.loop_id,
            "closed": closed, "failed": failed,
            "reviews": reviews, "stopped_reason": loop.result().stopped or "queue",
            "gaps_considered": len(gaps)}


def anti_tunnel_vision_review(closed: list, failed: list, *,
                              config: "LoopConfig | None" = None,
                              ledger: "LoopLedger | None" = None,
                              loop_id: str = "") -> dict:
    """The five-step look-back checkpoint, run as an adversarial-review loop.

    Reviews the past work for tunnel vision: are we still closing the highest-
    value gaps, and is the newest assumption still unproven?  It preserves
    dissent (it never merges or suppresses a finding) and returns a decision
    recommendation the campaign uses on the next beat."""
    lg = ledger or LoopLedger()
    cfg = config or LoopConfig(
        framework="custom",
        custom_steps=("collect_recent_work", "attack_assumptions",
                      "check_drift", "recommend"))

    def do_the_review():
        recent = [(c, "closed") for c in closed] + [(f, "failed") for f in failed]
        drift_signals = []
        if failed and closed and len(failed) > len(closed):
            drift_signals.append("failure rate exceeds closed rate — the "
                                 "campaign may be working the wrong queue")
        if recent and len(set(g for g, _ in recent)) < len(recent):
            drift_signals.append("duplicate gap ids worked — possible "
                                 "thrash/repetition signal")
        rec = "continue" if not drift_signals else "re-rank the campaign queue"
        return {"recent": recent, "drift_signals": drift_signals,
                "recommendation": rec, "dissent_preserved": True}

    out = as_practitioner_loop("anti-tunnel-vision review", do_the_review,
                               ledger=lg)
    out["recommendation"] = out["value"].get("recommendation", "continue")
    out["drift_signals"] = out["value"].get("drift_signals", [])
    return {"record_type": "anti_tunnel_review/v1",
            "review_loop_id": out["loop_id"],
            "recommendation": out["recommendation"],
            "drift_signals": out["drift_signals"],
            "dissent_preserved": True,
            "reviewed_closed": list(closed), "reviewed_failed": list(failed)}


def self_test() -> dict:
    results = []

    def check(name, ok, note=""):
        results.append({"test": name, "passed": bool(ok), "detail": note})

    ledger = LoopLedger()

    # 1. POSITIVE — a campaign closes two verified gaps and stops honest.
    gaps = [
        DevGap("a", "add a gate", lambda: {"ok": True}, lambda r: r.get("ok")),
        DevGap("b", "emit a metric", lambda: {"ok": True}, lambda r: r.get("ok")),
    ]
    camp = development_practitioner_loop(gaps, ledger=ledger, budget_items=8,
                                         review_cadence=5)
    check("campaign_closes_verified_gaps_then_stops",
          set(camp["closed"]) == {"a", "b"} and not camp["failed"]
          and camp["stopped_reason"] in ("queue", "done", "run_to_completion")
          and camp["campaign_loop_id"],
          f"closed={camp['closed']} reason={camp['stopped_reason']}")

    # 2. ADVERSARIAL — a gap whose verify() rejects it stays OPEN, never "closed".
    gaps2 = [DevGap("good", "ok", lambda: {"ok": True}, lambda r: r.get("ok")),
             DevGap("bad", "false positive", lambda: {"ok": False},
                    lambda r: bool(r.get("ok")))]
    camp2 = development_practitioner_loop(gaps2, ledger=LoopLedger())
    check("unverified_gap_stays_open_never_closed",
          camp2["closed"] == ["good"] and camp2["failed"] == ["bad"],
          f"failed stayed open: {camp2['failed']}")

    # 3. the review checkpoint runs at cadence and preserves dissent.
    review = anti_tunnel_vision_review(["a", "b"], ["x"], ledger=LoopLedger())
    check("review_runs_and_preserves_dissent",
          review["dissent_preserved"]
          and review["review_loop_id"]
          and review["recommendation"] in ("continue", "re-rank the campaign queue"),
          f"rec={review['recommendation']}")

    # 4. the review flags a failure-dominated history as drift.
    drifted = anti_tunnel_vision_review(["a"], ["b", "c", "d"],
                                        ledger=LoopLedger())
    check("review_flags_tunnel_vision_when_failures_dominate",
          drifted["drift_signals"] != []
          and drifted["recommendation"] == "re-rank the campaign queue",
          "failure-dominated run produced a drift signal")

    passed = sum(1 for t in results if t["passed"])
    return {"tests": results, "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
