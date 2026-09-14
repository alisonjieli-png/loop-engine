"""A canonical Practitioner self-improvement task over history and intelligence.

Self-improvement is a Practitioner responsibility, not another runtime role.

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
    ignored_directories: tuple = ()


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


NOT_A_SAVED_RUN = "no manifest; not a saved run or checkpoint store"


def _one_trace_per_observation(runs: list) -> tuple:
    """Keep the earliest projection of each event content; name the rest.

    One ledger projected twice under two run ids is one observation. The
    trace whose first event is earliest (then the lower run id) stays; each
    later copy is excluded with the run it repeats, so the report shows the
    copy rather than a second independent run.
    """
    by_content: dict = {}
    for trace in runs:
        key = trace.get("content_digest") or trace["run_id"]
        by_content.setdefault(key, []).append(trace)
    copies = []
    for traces in by_content.values():
        ordered = sorted(traces, key=lambda t: (t.get("first_event_ts", 0.0),
                                                t["run_id"]))
        for copy in ordered[1:]:
            copies.append({"run_id": copy["run_id"], "reason":
                           f"same event content as run {ordered[0]['run_id']!r}"})
    copied = {entry["run_id"] for entry in copies}
    return [t for t in runs if t["run_id"] not in copied], copies


def load_run_history(runs_dir: str, *, limit: "int | None" = None,
                           ledger=None, parent=None) -> dict:
    """Load an exact verified run population for improvement review.

    The population is every directory holding a manifest: a saved run or an
    append-only checkpoint store, which loads as its latest checkpoint. A
    sibling without one (the artifact directory beside its run) is listed
    under ``ignored`` and takes no place in the limit. Histories with the
    same event content are one observation; see
    ``_one_trace_per_observation``.
    """
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError('history limit must be a nonnegative integer or None')
    import json
    from ..core.run_history import (RunHistory, default_runs_dir,
                                                  as_ledger_events)
    from ..loop.intelligence_loops import serve_historical_intelligence
    from .housekeeping import trace_from_loop_ledger
    root = default_runs_dir(runs_dir)
    present, ignored = [], []
    if os.path.isdir(root):
        for name in sorted(os.listdir(root)):
            if not os.path.isdir(os.path.join(root, name)):
                continue
            if os.path.exists(os.path.join(root, name, "manifest.json")):
                present.append(name)
            else:
                ignored.append({"name": name, "reason": NOT_A_SAVED_RUN})
    selected = present if limit is None else (present[-limit:] if limit else [])
    runs, excluded = [], []
    for run_id in selected:
        path = os.path.join(root, run_id)
        try:
            with open(os.path.join(path, "manifest.json"), encoding="utf-8") as stream:
                record_type = str(json.load(stream).get("record_type", ""))
            loader = (RunHistory.load_checkpoint
                      if record_type == RunHistory.CHECKPOINT_STORE_RECORD_TYPE
                      else RunHistory.load)
            served = serve_historical_intelligence(
                f"self-improvement-history:{run_id}",
                lambda run_id=run_id, loader=loader: loader(root, run_id),
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
            trace["record_type"] = record_type
            trace["events"] = len(run_history.event_log)
            trace["history_digest"] = run_history.event_log[-1].event_digest if run_history.event_log else ''
            trace["content_digest"] = run_history.content_digest()
            trace["first_event_ts"] = (run_history.event_log[0].ts
                                       if run_history.event_log else 0.0)
            runs.append(trace)
        except (OSError, KeyError, TypeError, ValueError) as exc:
            excluded.append({"run_id": run_id,
                             "reason": f"unreadable: {type(exc).__name__}"})
    runs, copies = _one_trace_per_observation(runs)
    excluded.extend(copies)
    return {"root": root, "population": len(present),
            "selected": len(selected), "runs": runs,
            "excluded": excluded, "ignored": ignored, "limit": limit}


def run_self_improvement(*, runs_dir: str = "", layer_records=None,
                         run_limit: "int | None" = 100,
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
    from ..loop.loop_role import LoopRole, LoopRoleIdentity

    catalog = layer_records if layer_records is not None else (
        build_intelligence_catalog(runs_dir=runs_dir,
                                   include_candidates=include_candidates))
    summary = catalog_summary(catalog)
    template = next(item for item in TEMPLATE_LIBRARY
                    if item["template_id"] == "continuous_improvement")
    base = config_from_template(template, power="deep", max_depth=None)
    config = LoopConfig(
        framework=base.framework, logical_kind=base.logical_kind,
        replay_guarantee=base.replay_guarantee,
        allowable_modes=("deterministic",),
        preferred_modes=("deterministic",), power=base.power,
        custom_steps=base.custom_steps, max_depth=base.max_depth)
    log = ledger or LoopLedger()
    loop = Loop("review run history and intelligence for improvements",
                config, ledger=log,
                identity=LoopRoleIdentity(LoopRole.PRACTITIONER, 'practitioner.self_improvement'))
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
            from ..core.intelligence_layers import (
                IntelligenceSearchContext, IntelligenceSearchRequest)
            retrieved = query_intelligence(IntelligenceSearchRequest(
                "review context method failure and repeated model work",
                catalog, top_n=None,
                include_candidates=include_candidates),
                IntelligenceSearchContext(
                    ledger=log, parent=active_loop))
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
        loop_result=result, ledger=log,
        ignored_directories=tuple(history["ignored"]))


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
        # The last ledger projected again under another run id, a third
        # run kept as an append-only checkpoint store, and an artifact
        # directory beside it that sorts last, where a limit of one used
        # to select it and review nothing.
        again = RunHistory.from_ledger(
            lp.ledger.events, run_id="history-1-projected-again")
        again.commit(); again.save(history_root)
        third = Loop("history 2", LoopConfig(
            framework="custom", custom_steps=("research",),
            allowable_modes=("hybrid",), preferred_modes=("hybrid",),
            power="light"))
        third.run(handler=lambda loop, step, context: StepOutcome(
            output="research complete", mode="hybrid", confidence=0.9))
        RunHistory.from_ledger(
            third.ledger.events,
            run_id="history-2-store").append_checkpoint(history_root)
        artifacts = os.path.join(history_root, "history-2-store-artifacts")
        os.makedirs(artifacts)
        with open(os.path.join(artifacts, "output.txt"), "w") as handle:
            handle.write("an artifact beside its run\n")
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
        loaded = load_run_history(history_root, limit=None)
        one_slot = load_run_history(history_root, limit=1)
    copies = [entry for entry in report.excluded_runs
              if entry["run_id"] == "history-1-projected-again"]
    tests = [{
        "test": "self_improvement_reviews_history_and_intelligence_in_one_loop",
        "passed": bool(report.run_population == 5
        and report.n_runs_reviewed == 3
        and len(report.excluded_runs) == 2
        and report.intelligence_items_reviewed == 1
        and report.retrieval_hits and report.loop_result.stopped == "done"
        and any(candidate.source == "intelligence_audit"
                for candidate in report.candidates)
        and not any(candidate.kind in ('code_node', 'logic_rule') for candidate in report.candidates)
        and any(event.get("loop_id") == report.loop_result.loop_id
                and event.get("logical_kind") == "search_improvement"
                for event in report.ledger.events
                if event.get("event") == "init"))
    }, {
        "test": "a_reprojected_ledger_a_checkpoint_store_and_an_artifact_sibling_are_counted_exactly",
        "passed": bool(len(copies) == 1 and "'history-1'" in copies[0]["reason"]
        and [trace["run_id"] for trace in loaded["runs"]]
        == ["history-0", "history-1", "history-2-store"]
        and loaded["runs"][2]["record_type"] == RunHistory.CHECKPOINT_STORE_RECORD_TYPE
        and loaded["runs"][0]["content_digest"] != loaded["runs"][1]["content_digest"]
        and report.ignored_directories == ({"name": "history-2-store-artifacts",
                                            "reason": NOT_A_SAVED_RUN},)
        and one_slot["selected"] == 1
        and [trace["run_id"] for trace in one_slot["runs"]] == ["history-2-store"])
    }]
    with tempfile.TemporaryDirectory() as history_root:
        loop = Loop('history-limit fixture', LoopConfig(framework='custom', custom_steps=('act',)))
        loop.run(handler=lambda *args: StepOutcome('done', 'deterministic', 1.0), max_steps=1)
        history = RunHistory.from_ledger(loop.ledger.events, run_id='limit-fixture')
        history.commit(); history.save(history_root)
        unlimited = load_run_history(history_root, limit=None)
        empty = load_run_history(history_root, limit=0)
        tests.append({'test': 'history_limits_preserve_none_and_zero', 'passed':
            unlimited['limit'] is None and len(unlimited['runs']) == 1
            and empty['selected'] == 0 and not empty['runs']})
        invalid = 0
        for value in (-1, True, '1', 1.5):
            try:
                load_run_history(history_root, limit=value)
            except ValueError:
                invalid += 1
        tests.append({'test': 'invalid_history_limits_are_refused', 'passed': invalid == 4})
    tests.append({'test': 'self_improvement_uses_its_exact_practitioner_profile', 'passed': any(
        event.get('event') == 'init' and event.get('loop_id') == report.loop_result.loop_id
        and event.get('profile_id') == 'practitioner.self_improvement' for event in report.ledger.events)})
    passed = sum(1 for test in tests if test["passed"])
    return {"tests": tests, "passed": passed, "total": len(tests),
            "all_passed": passed == len(tests)}
