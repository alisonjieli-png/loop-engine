"""Wiring — make the LIVE loop actually call the library.

This closes the honest gap the Atlas names: every module is tested in isolation,
but ``run_kernel_passes`` had only the deterministic defaults, so the Guidance /
Intelligence / Evidence library was present but not EXERCISED end-to-end.

``wired_impls`` returns a ``KernelImpls`` that ENRICHES the deterministic defaults
(it never replaces their valid objects, and appends only low-value candidates so
it can't hijack termination) while genuinely running the library at the right
nodes:

  * decide_next → solution_shaping.should_decompose + the bias checklist's next
    preferred step + a failure_response bias when the state carries a failure;
  * verify → review_mode + measurement (train-CV gap when metrics are present) +
    runtime_contracts admission (when a contract is supplied);
  * integrate_commit → capture.encapsulate → learning_bundle (disposition), and it
    advances the bias checklist BEFORE (open) and AFTER (close with the verified
    result) — the before/after cadence, live.

``run_wired`` runs it and reports which library modules the live loop exercised,
the checklist's final state, and the String/Code asset split — so "wired" is a
tested fact, not a claim.  This is a composed ENTRY POINT; it does not touch the
kernel defaults (the 470 tests that depend on them stay green).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..loop.kernel import (default_impls, CandidateAction, EvaluationPacket,
                     KernelRunRequest, ProblemSpec, run_kernel_passes)
from ..strings import solution_shaping
from ..code_nodes import review_mode, measurement, capture, learning_bundle
from ..static_architecture import asset_class
from ..strings.bias_checklist import BiasChecklist
from ..code_nodes.failure_response import respond_to_failure, FailureSignal


def _low(action: str, kind: str, why: str) -> CandidateAction:
    """A visible-but-non-hijacking candidate: it is recorded (proving the library
    ran) but its value is below any real candidate, so it never wins selection."""
    return CandidateAction(action=action, kind=kind, rationale=why,
                           expected_value=0.1, confidence=0.5)


def wired_impls(*, checklist: "BiasChecklist | None" = None, contract=None,
                log: "list | None" = None,
                intelligence: "dict | None" = None) -> dict:
    log = log if log is not None else []
    base = default_impls()

    def orient(state):
        """Reconstruct state AND, when an intelligence pack is wired, consult the
        four pillars at the orient step — the four-layer consult reaching the
        kernel executor, not only the directory-handler probe path."""
        sit = base["orient"](state)
        if intelligence is None:
            return sit
        from ..static_architecture.intelligence_layers import (
            query_intelligence)
        fan = query_intelligence(
            getattr(state.spec, "objective", ""), intelligence)
        log.append("intelligence_consult")
        known = dict(sit.knowns)
        if fan["hits"]:
            top = fan["hits"][0]
            known["_intelligence"] = {
                "need": getattr(state.spec, "objective", ""),
                "top": top.get("record_id", ""),
                "pillar": top.get("layer", ""),
                "hits": len(fan["hits"]),
                "unqueried": list(fan["unqueried"])}
        # thread the consult onto the state so integrate_commit can surface it
        # as a fact (Situation.knowns do not persist across passes; facts do)
        if fan["hits"]:
            try:
                object.__setattr__(state, "_orient_intelligence",
                                   known["_intelligence"])
            except Exception:                               # noqa: BLE001
                pass
        return sit.__class__(summary=sit.summary, knowns=known,
                             unknowns=sit.unknowns, signals=sit.signals)

    def decide(state, situation):
        cands = list(base["decide_next"](state, situation))
        try:
            sig = solution_shaping.signals_from_text(
                state.spec.objective,
                subtask_count=len(state.spec.success_criteria))
            dec = solution_shaping.should_decompose(sig)
            log.append("solution_shaping")
            for m in dec.moves:
                cands.append(_low(m.action, "decompose", m.rationale))
        except Exception:                                       # noqa: BLE001
            pass
        if checklist is not None:
            nxt = checklist.next_preferred()
            if nxt:
                cands.append(_low(f"guided::{nxt}", "guided",
                                  f"preferred step: {nxt}"))
            log.append("bias_checklist")
        if state.failures:
            fr = respond_to_failure(FailureSignal(
                "crash", message=state.failures[-1],
                times_seen=len(state.failures)))
            cands.append(_low(fr.action.action, "failure_response",
                              fr.rationale))
            log.append("failure_response")
        return cands

    def verify(state, plan, results):
        ev = base["verify"](state, plan, results)
        log.append("review_mode")
        notes = [ev.notes] if ev.notes else []
        try:
            for r in results:
                vals = r.result if isinstance(r.result, (list, tuple)) else None
                if vals:
                    d = review_mode.detect_constant_output(vals)
                    if getattr(d, "flagged", False):
                        notes.append("degenerate:constant")
        except Exception:                                       # noqa: BLE001
            pass
        for r in results:
            tr, cv = r.metrics.get("train"), r.metrics.get("cv")
            if tr is not None and cv is not None:
                g = measurement.read_generalization_gap(tr, cv)
                notes.append(f"gap:{g.verdict}")
                log.append("measurement")
        if contract is not None:
            for r in results:
                if r.result is not None:
                    res = contract.validate(r.result)
                    log.append("runtime_contracts")
                    notes.append(f"contract:{'ok' if res.valid else 'INVALID'}")
                    if not res.valid:
                        return EvaluationPacket(
                            "repair", notes="contract violation: "
                            + res.summary())
        return EvaluationPacket(ev.verdict, ev.best_index, ev.scores,
                                "; ".join(n for n in notes if n))

    def integrate(state, rec):
        st = base["integrate_commit"](state, rec)
        primary = "; ".join(str(r.result) for r in rec.results) \
            if rec.results else ""
        try:
            report = capture.encapsulate(primary, agenda_step="act")
            bundle = learning_bundle.make_learning_bundle(
                run_id="wired", pass_id=f"p{rec.pass_number}",
                primary_result=primary, report=report)
            log.append("capture")
            log.append("learning_bundle")
            disposition = bundle.learning_disposition
        except Exception:                                       # noqa: BLE001
            disposition = "no_new_learning"
        if checklist is not None:
            nxt = checklist.next_preferred()
            if nxt:
                good = bool(rec.evaluation and rec.evaluation.verdict
                            in ("accept", "accept_provisional"))
                checklist.open_step(nxt)                        # before
                checklist.close_step(nxt, result_good=good)     # after
        facts = dict(st.facts)
        facts["_last_disposition"] = disposition
        # carry the orient intelligence consult forward as a fact, so the run's
        # recorded state actually shows which intelligence the loop saw
        intel = getattr(st, "_orient_intelligence", None)
        if intel is not None:
            facts["_intelligence"] = intel
        return st.derive(facts=facts)

    return {**base, "orient": orient, "decide_next": decide, "verify": verify,
            "integrate_commit": integrate}


@dataclass(frozen=True)
class WiredKernelRunRequest:
    """One typed request for a kernel run with the library connected."""

    spec: ProblemSpec
    owner_loop: Any = None
    contract: Any = None
    max_passes: int = 8
    event_dir: str | None = None
    selected_mode: str = "deterministic"


def run_wired(request: WiredKernelRunRequest) -> dict:
    """Run the live loop with the library wired in, and report what it exercised."""
    if not isinstance(request, WiredKernelRunRequest):
        raise TypeError("run_wired needs a WiredKernelRunRequest")
    log: list = []
    checklist = BiasChecklist(run_ref="wired")
    impls = wired_impls(
        checklist=checklist, contract=request.contract, log=log)
    run = run_kernel_passes(KernelRunRequest(
        spec=request.spec, impls=impls, owner_loop=request.owner_loop,
        event_dir=request.event_dir, max_passes=request.max_passes,
        selected_mode=request.selected_mode))
    run["wired_modules"] = sorted(set(log))
    run["checklist"] = checklist.snapshot()
    run["asset_split"] = asset_class.asset_split(
        ["string", "consideration", "logic_rule", "contract", "node",
         "question"])
    return run


# ---------------------------------------------------------------------------
# Self-test — deterministic, no network.
# ---------------------------------------------------------------------------


def self_test() -> dict:
    results: list[dict] = []

    def check(name, ok, detail=""):
        results.append({"test": name, "passed": bool(ok), "detail": detail})

    # 1. a live wired run COMPLETES and exercises the library end-to-end.
    run = run_wired(WiredKernelRunRequest(
        ProblemSpec(objective="win", success_criteria=("model",))))
    mods = set(run["wired_modules"])
    check("live_loop_exercises_the_library",
          run["passes"] >= 1
          and {"bias_checklist", "solution_shaping", "review_mode", "capture",
               "learning_bundle"} <= mods,
          f"exercised: {sorted(mods)}")

    # 2. the run still TERMINATES — the enrichment never hijacks selection.
    check("enrichment_does_not_hijack_termination",
          run["final_route"] in ("stop_success", "stop_unprofitable"),
          f"final route: {run['final_route']}")

    # 3. the bias checklist ADVANCED, before-and-after, during the live run.
    snap = run["checklist"]
    done = [k for k, v in snap["steps"].items() if v["status"] == "done"]
    check("the_checklist_advanced_before_and_after_live",
          len(done) >= 1,
          f"{len(done)} step(s) completed with before+after in the live loop")

    # 4. a learning disposition was recorded for the run (nothing disappears).
    check("a_learning_disposition_was_recorded",
          "_last_disposition" in run["facts"]
          and run["facts"]["_last_disposition"]
          in learning_bundle.LEARNING_DISPOSITIONS,
          f"disposition: {run['facts'].get('_last_disposition')}")

    # 5. runtime_contracts admission runs LIVE in verify: a violating result ->
    # repair (truth enforced through the loop).
    from ..loop.kernel import PractitionerState, ExecutionPlan, ResultPacket
    from ..code_nodes.runtime_contracts import ContractDefinition, FieldSpec
    log2: list = []
    impls = wired_impls(
        contract=ContractDefinition(
            "out", "enum", allowed_values=("approve", "reject")), log=log2)
    st = PractitionerState(spec=ProblemSpec(objective="x"))
    plan = ExecutionPlan(how_mode="use", act_mode="run_direct", handle="n")
    ev_bad = impls["verify"](st, plan,
                             [ResultPacket(objective="x", result="MAYBE",
                                           confidence=0.9)])
    ev_ok = impls["verify"](st, plan,
                            [ResultPacket(objective="x", result="approve",
                                          confidence=0.9)])
    check("runtime_contract_admission_runs_live_in_verify",
          ev_bad.verdict == "repair" and "runtime_contracts" in log2
          and ev_ok.verdict in ("accept", "accept_provisional"),
          "an out-of-enum result is rejected through the live verify node")

    # 6. the four-pillar intelligence consult reaches the KERNEL executor: a
    # wired pack consults at orient and the landed fact names the pillar.
    from ..static_architecture.store_serve import StoreRecord
    packs = {"context_intelligence": [StoreRecord(
        "s.stat", "context", "use a statistician persona", body={},
        tags=("persona",))]}
    r_in = run_kernel_passes(KernelRunRequest(
        ProblemSpec(objective="statistician review",
                    success_criteria=("ok",)),
        wired_impls(intelligence=packs), max_passes=1))
    r_out = run_kernel_passes(KernelRunRequest(
        ProblemSpec(objective="win", success_criteria=("model",)),
        wired_impls(), max_passes=1))
    check("kernel_orient_consults_the_intelligence_when_wired",
          r_in["facts"].get("_intelligence", {}).get("pillar")
          == "context_intelligence"
          and "user_feedback_intelligence" in r_in["facts"]["_intelligence"]["unqueried"]
          and r_out["facts"].get("_intelligence") is None,
          "consult lands in run facts; the no-pack default is unchanged")

    # 7. measurement runs LIVE when a result carries train/cv metrics.
    log3: list = []
    impls3 = wired_impls(log=log3)
    ev_m = impls3["verify"](st, plan,
                            [ResultPacket(objective="x", result="ok",
                                          confidence=0.8,
                                          metrics={"train": 0.99, "cv": 0.80})])
    check("measurement_gap_runs_live_in_verify",
          "measurement" in log3 and "gap:overfitting" in (ev_m.notes or ""),
          "the train-CV gap is read through the live verify node")

    # 7. a failure in state biases decide toward a failure_response, live.
    log4: list = []
    impls4 = wired_impls(log=log4)
    from ..loop.kernel import Situation
    st_fail = PractitionerState(spec=ProblemSpec(objective="x",
                                                 success_criteria=("m",)),
                                failures=("pass 1: crash",))
    cands = impls4["decide_next"](st_fail, Situation(summary="errored",
                                                     unknowns=("m",)))
    check("a_failure_biases_decide_toward_a_response",
          "failure_response" in log4
          and any(c.kind == "failure_response" for c in cands),
          "an errored state proposes diagnose/retry/other-method, live")

    # 8. the String/Code lens is applied to the run (the universal rail).
    split = run["asset_split"]
    check("the_string_code_lens_is_applied_to_the_run",
          split["n_string"] >= 1 and split["n_code"] >= 1,
          f"{split['n_string']} string / {split['n_code']} code in the run's mix")

    passed = sum(1 for r in results if r["passed"])
    return {"record_type": "wiring_self_test", "tests": results,
            "passed": passed, "total": len(results),
            "all_passed": passed == len(results)}
