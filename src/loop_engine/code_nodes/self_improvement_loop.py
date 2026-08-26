"""The canonical Self-Improvement Loop over history and intelligence.

Architectural role: Code Node system for the third public Loop role.

Owns: verified saved-run intake, Intelligence Search and Retrieval, coverage
audit, runtime mining, opportunity ranking, and in-memory candidate staging.

Does not own: scheduling, persistent candidate writes, independent review, or
promotion.

Public entry points: ``run_self_improvement`` and
``load_run_history``.

Verification: ``self_test()`` includes two valid runs and one broken run.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from .housekeeping import TRIGGER_CLASSES, ImprovementCandidate


@dataclass
class SelfImprovementReport:
    """One canonical Self-Improvement Loop result."""
    trigger: str
    run_population: int
    n_runs_reviewed: int
    excluded_runs: tuple
    intelligence_items_reviewed: int
    retrieval_hits: tuple
    candidates: tuple
    classification: dict
    loop_result: object
    ledger: object
    staged_only: bool = True


def audit_intelligence_summary(summary: dict) -> list:
    """Propose classification work from visible catalog gaps."""
    candidates = []
    for layer in summary.get("layers", ()):
        label = layer.get("public_label", layer.get("layer", "layer"))
        incomplete = int(layer.get("incomplete", 0) or 0)
        other = int((layer.get("category_groups") or {}).get("other", 0) or 0)
        if incomplete:
            candidates.append(ImprovementCandidate(
                "intelligence_string",
                f"classify {incomplete} incomplete items in {label}",
                evidence=(f"catalog summary reports {incomplete} incomplete",
                          ), source="intelligence_audit", frequency=incomplete,
                confidence=0.8, job_family="runtime_housekeeping"))
        if other:
            candidates.append(ImprovementCandidate(
                "intelligence_string",
                f"review {other} items in the broad 'other' category of {label}",
                evidence=(f"catalog summary reports other={other}",),
                source="intelligence_audit", frequency=other,
                confidence=0.7, job_family="runtime_housekeeping"))
    return candidates


def load_run_history(runs_dir: str, *, limit: int = 100,
                           ledger=None, parent=None) -> dict:
    """Load an exact verified run population for improvement review."""
    from ..core.run_history import (RunHistory, default_runs_dir,
                                                  as_ledger_events)
    from ..loop.intelligence_loops import serve_historical_intelligence
    from .housekeeping import trace_from_loop_ledger
    root = default_runs_dir(runs_dir)
    present = []
    if os.path.isdir(root):
        present = [name for name in sorted(os.listdir(root))
                   if os.path.isdir(os.path.join(root, name))]
    selected = present[-max(0, int(limit)):]
    runs, excluded = [], []
    for run_id in selected:
        path = os.path.join(root, run_id)
        if not os.path.exists(os.path.join(path, "manifest.json")):
            excluded.append({"run_id": run_id, "reason": "manifest missing"})
            continue
        try:
            served = serve_historical_intelligence(
                f"self-improvement-history:{run_id}",
                lambda run_id=run_id: RunHistory.load(root, run_id),
                ledger=ledger, parent=parent)
            if served.get("error") is not None or served.get("value") is None:
                raise ValueError("saved run history could not be loaded")
            run_history = served["value"]
            chain = run_history.verify_chain()
            if not chain.get("intact"):
                excluded.append({"run_id": run_id,
                                 "reason": "event chain is not intact"})
                continue
            trace = trace_from_loop_ledger(as_ledger_events(run_history.event_log))
            trace["run_id"] = run_id
            trace["events"] = len(run_history.event_log)
            runs.append(trace)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            excluded.append({"run_id": run_id,
                             "reason": f"unreadable: {type(exc).__name__}"})
    return {"root": root, "population": len(present),
            "selected": len(selected), "runs": runs,
            "excluded": excluded, "limit": int(limit)}


def run_self_improvement(*, runs_dir: str = "", layer_records=None,
                         run_limit: int = 100,
                         trigger_class: str = "manual",
                         min_frequency: int = 2,
                         include_candidates: bool = False,
                         ledger=None) -> SelfImprovementReport:
    """Review saved runs and current intelligence through one canonical Loop.

    The result contains staged candidates only. It performs no promotion and
    writes no candidate files.
    """
    from .housekeeping import (guard_improvement_action, mine_runtime,
                               rank_opportunities, classify_intelligence)
    if trigger_class not in TRIGGER_CLASSES:
        raise ValueError(f"trigger_class must be one of {TRIGGER_CLASSES}")
    from ..core.intelligence_layers import (
        build_intelligence_catalog, catalog_summary, query_intelligence)
    from ..loop.loop_templates import TEMPLATE_LIBRARY, config_from_template
    from ..loop.recursive_loop import (Loop, LoopConfig, LoopLedger,
                                       StepOutcome)

    catalog = layer_records if layer_records is not None else (
        build_intelligence_catalog(runs_dir=runs_dir,
                                   include_candidates=include_candidates))
    summary = catalog_summary(catalog)
    template = next(item for item in TEMPLATE_LIBRARY
                    if item["template_id"] == "continuous_improvement")
    base = config_from_template(template, power="deep", max_depth=2)
    config = LoopConfig(
        framework=base.framework, logical_kind=base.logical_kind,
        replay_guarantee=base.replay_guarantee,
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), power=base.power,
        custom_steps=base.custom_steps, max_depth=base.max_depth)
    log = ledger or LoopLedger()
    loop = Loop("review run history and intelligence for improvements",
                config, ledger=log)
    history = load_run_history(runs_dir, limit=run_limit,
                                     ledger=log, parent=loop)
    state = {"candidates": [], "retrieval_hits": []}

    def handler(active_loop, step, context):
        if step == "load_history":
            return StepOutcome(
                output=f"loaded={len(history['runs'])}; "
                       f"excluded={len(history['excluded'])}",
                mode="deterministic", confidence=0.95)
        if step == "audit_intelligence":
            retrieved = query_intelligence(
                "review context method failure and repeated model work",
                catalog, top_n=5, include_candidates=include_candidates,
                ledger=log, parent=active_loop)
            state["retrieval_hits"] = list(retrieved["hits"])
            found = audit_intelligence_summary(summary)
            state["candidates"].extend(found)
            return StepOutcome(output=f"retrieved={len(state['retrieval_hits'])}; "
                                      f"intelligence_gaps={len(found)}",
                               mode="deterministic", confidence=0.9)
        if step == "mine":
            found = mine_runtime(history["runs"],
                                 min_frequency=min_frequency)
            state["candidates"].extend(found)
            return StepOutcome(output=f"runtime_candidates={len(found)}",
                               mode="deterministic", confidence=0.9)
        if step == "rank":
            unique = {}
            for candidate in state["candidates"]:
                unique.setdefault((candidate.kind, candidate.proposal),
                                  candidate)
            state["candidates"] = rank_opportunities(list(unique.values()))
            return StepOutcome(output=f"ranked={len(state['candidates'])}",
                               mode="deterministic", confidence=0.95)
        if step == "engineer_candidate":
            return StepOutcome(output="candidate records prepared",
                               mode="deterministic", confidence=0.9)
        if step == "stage":
            guard_improvement_action(
                "stage_candidate", logical_kind=active_loop.config.logical_kind)
            return StepOutcome(output="staged in memory for independent review",
                               mode="deterministic", confidence=0.95)
        if step == "compare":
            return StepOutcome(
                output=f"candidates={len(state['candidates'])}; promoted=0",
                mode="deterministic", confidence=0.95)
        return StepOutcome(output=f"{step}:done", mode="deterministic",
                           confidence=0.9)

    result = loop.run(handler=handler,
                      max_steps=len(config.custom_steps) + 1)
    candidates = tuple(state["candidates"])
    return SelfImprovementReport(
        trigger=trigger_class, run_population=history["population"],
        n_runs_reviewed=len(history["runs"]),
        excluded_runs=tuple(history["excluded"]),
        intelligence_items_reviewed=summary["total_items"],
        retrieval_hits=tuple(state["retrieval_hits"]),
        candidates=candidates, classification=classify_intelligence(candidates),
        loop_result=result, ledger=log)


def self_test() -> dict:
    import json
    import tempfile
    from ..loop.recursive_loop import Loop, LoopConfig, StepOutcome
    from ..core.run_history import RunHistory
    from ..core.store_serve import StoreRecord

    with tempfile.TemporaryDirectory() as history_root:
        for index in range(2):
            lp = Loop(f"history {index}", LoopConfig(
                framework="custom", custom_steps=("research",),
                allowable_modes=("hybrid",), preferred_modes=("hybrid",),
                power="light"))
            lp.run(handler=lambda loop, step, context: StepOutcome(
                output="research complete", mode="hybrid", confidence=0.9))
            run_history = RunHistory.from_ledger(
                lp.ledger.events, run_id=f"history-{index}")
            run_history.commit(); run_history.save(history_root)
        broken = os.path.join(history_root, "broken-run")
        os.makedirs(broken)
        with open(os.path.join(broken, "manifest.json"), "w") as handle:
            json.dump({"not": "a run_history"}, handle)
        catalog = {
            "context": [StoreRecord(
                "ctx.incomplete", "context", "an uncategorized method",
                body={"role": "method", "category": "method",
                      "maturity": "registered"})],
            "code_intelligence": [], "runtime_history_solution_intelligence": [],
            "user_feedback_intelligence": []}
        report = run_self_improvement(
            runs_dir=history_root, layer_records=catalog, min_frequency=2)
    tests = [{
        "test": "self_improvement_reviews_history_and_intelligence_in_one_loop",
        "passed": bool(report.run_population == 3
        and report.n_runs_reviewed == 2
        and len(report.excluded_runs) == 1
        and report.intelligence_items_reviewed == 1
        and report.retrieval_hits and report.loop_result.stopped == "done"
        and any(candidate.source == "intelligence_audit"
                for candidate in report.candidates)
        and any(candidate.kind == "code_node" for candidate in report.candidates)
        and any(event.get("loop_id") == report.loop_result.loop_id
                and event.get("logical_kind") == "search_improvement"
                for event in report.ledger.events
                if event.get("event") == "init"))
    }]
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
